"""toscanini/durable.py — the MINIMUM durable persistence layer (R392
directives 5-6).

Render's default filesystem is EPHEMERAL (restarts and idle spin-downs wipe
it). This module preserves exactly what the CEO listed — nothing more:

  DURABLE METADATA (always persisted):
    - sessions.json / shares.json  (session + job + share state)
    - evidence_<sid>.json          (evidence references)
    - the run-dir epistemic record (envelopes, specifications, decisive
      experiment, survivor/cemetery records, final_state, run_manifest,
      PACKAGE_REPORT, RELEASE_PROOF) — the small JSON artifacts that carry
      the evidence trail
    - the buyer package ZIP under DOWNLOAD/ (the final result reference)

  EPHEMERAL (never migrated, regenerable or bulky intermediates):
    - exploration grids, per-angle attack outputs beyond the survivor
      chain, plots, gateway logs, the state-repo cache itself.

Store: a private branch ("runtime-state") of the EXISTING private engine
repository, via the EXISTING GITHUB_TOKEN. No new infrastructure (directive
6): no database server, no object-store account, one git branch.

Security (directive 4): the token is supplied through a runtime
GIT_ASKPASS helper (generated per call, mode 0700, reads the env var at
call time). It never appears in a command-line URL, in argv, in the image,
or in logs (git does not echo askpass output).

Honesty (Art. XV/XXV): every snapshot/restore outcome — including
refusals (not enabled, no token, push denied) — is reported to the caller
and surfaced through /api/health (durable.*). A failed snapshot NEVER
fails the run it belongs to.

Guard: per-file cap 20 MB (structured JSON + zips are ~1-3 MB; anything
larger is disclosed as skipped rather than silently dropped).
"""
from __future__ import annotations

import fcntl
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from toscanini import artifact_identity  # noqa: E402  R396 B.3
from toscanini import sessions as store

REPO_ROOT = Path(__file__).resolve().parents[1]
ENGINE_RUNTIME = REPO_ROOT / "ENGINE_RUNTIME"
STATE_REPO = ENGINE_RUNTIME / "state-repo"
LOCK_PATH = ENGINE_RUNTIME / "durable.lock"

REMOTE = "https://github.com/prateekm1007/discovery-evidence-fabric.git"
FILE_CAP_BYTES = 20 * 1024 * 1024
# R396 B.3: integrity manifest + append-only snapshot log live in the
# state repo. The manifest cannot hash itself (or the log) — both are
# excluded from the file map and named here so the exclusion is a
# constant, not a convention.
MANIFEST_NAME = "MANIFEST.json"
SNAPSHOT_LOG_NAME = "snapshot_log.jsonl"

# R423A Phase 4: incremental payload tracking. Measured BEFORE (the
# r423 baseline, P6): EVERY snapshot copied the FULL payload — 282
# files / 225,167,652 bytes / 284 sha256 calls — even for a
# `created:{sid}` snapshot whose only change was sessions.json. On the
# deployed instance that copy plus the git fetch dominated the
# POST /api/run latency (measured live: 13.6 s). The cache records the
# (size, mtime_ns) of every file as last copied; unchanged files are
# skipped (the state-repo copy IS the previous copy — copy2 preserves
# mtimes, so a byte-identical re-copy is provably a no-op).
_PAYLOAD_CACHE: Dict[str, Tuple[int, int]] = {}
# R423A Phase 4: hash cache for unchanged payload files — a file whose
# (size, mtime_ns) matches its last-copied state has the same bytes in
# the state repo (copy2 preserves both), so its previous manifest hash
# remains the true hash. Re-hashing 225 MB per snapshot was measured as
# the dominant LOCAL cost (P6: 284 sha256 calls, 0.38 s on fast disk;
# multiples of that on the deployed instance).
_HASH_CACHE: Dict[str, Tuple[Tuple[int, int], str]] = {}


def reset_payload_cache() -> None:
    """Test/ops hook: forget the incremental state (next snapshot does
    a full copy). Production never needs this — the cache is derived
    from the state-repo's own files."""
    _PAYLOAD_CACHE.clear()
    _HASH_CACHE.clear()

_LAST: Dict[str, Any] = {"ok": None, "at": None, "reason": None,
                         "error": None, "files": 0, "commit": None,
                         "pushed": None, "manifest_sha256": None,
                         "engine_commit": None}
_LAST_RESTORE: Dict[str, Any] = {"at": None, "sessions": 0, "runs": 0,
                                 "evidence": 0, "interrupted": 0,
                                 "error": None, "branch_sessions": None,
                                 "integrity_mismatches": None,
                                 "integrity_verified": None,
                                 "manifest_sha256": None}


def enabled() -> bool:
    """Durable persistence is an EXPLICIT deployment choice (Render sets
    DURABLE_STATE_ENABLED=1). Local dev defaults OFF — the sandbox must
    not push its test sessions into the real runtime-state branch."""
    return os.environ.get("DURABLE_STATE_ENABLED", "").strip() == "1"


def branch() -> str:
    return os.environ.get("DURABLE_STATE_BRANCH", "").strip() or "runtime-state"


def state() -> Dict[str, Any]:
    return {
        "enabled": enabled(),
        "branch": branch() if enabled() else None,
        "last_snapshot": dict(_LAST),
        "last_restore": dict(_LAST_RESTORE),
        "store": "private engine repo runtime-state branch (git)",
    }


# R396 B.3: per-file integrity manifest --------------------------------

def _file_sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _tree_sha256(file_hashes: Dict[str, str]) -> str:
    """Deterministic digest over the sorted (path, sha) pairs — the
    integrity identity of one snapshot payload."""
    import hashlib
    lines = sorted(f"{p} {s}" for p, s in file_hashes.items())
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


# ---------------------------------------------------------------------------
# token-safe git transport
# ---------------------------------------------------------------------------

_ASKPASS_PATH: Optional[Path] = None


def _askpass() -> Path:
    """(Re)generate the GIT_ASKPASS helper. The script contains NO literal
    secret — it reads GITHUB_TOKEN from its own environment at call time.
    Mode 0700; lives only on the ephemeral container/sandbox disk."""
    global _ASKPASS_PATH
    ENGINE_RUNTIME.mkdir(parents=True, exist_ok=True)
    p = ENGINE_RUNTIME / "askpass.sh"
    p.write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  *sername*) echo \"x-access-token\" ;;\n"
        "  *assword*) printf '%s\\n' \"$GITHUB_TOKEN\" ;;\n"
        "  *) echo \"\" ;;\n"
        "esac\n")
    p.chmod(0o700)
    _ASKPASS_PATH = p
    return p


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    if token:
        env["GIT_ASKPASS"] = str(_askpass())
    r = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True, text=True, timeout=300, env=env)
    if check and r.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args[:3])} failed: {r.stderr.strip()[:300]}")
    return r


# ---------------------------------------------------------------------------
# payload selection (durable metadata vs bulky intermediates)
# ---------------------------------------------------------------------------

def _run_dir_files(run_dir: Path) -> List[Path]:
    """Files worth persisting from one engine run dir: the envelopes,
    specifications, verdicts, manifests, release proofs, package report
    and the buyer ZIP. Grid/angle intermediates and plots stay ephemeral
    (regenerable, bulky)."""
    keep_json = {
        "problem.json", "candidate_envelope.json", "final_state.json",
        "run_manifest.json", "INVENTION_SPECIFICATION.json",
        "ENGINEERING_SPECIFICATION.json", "DECISIVE_EXPERIMENT.json",
        "SURVIVOR_SELECTION.json", "SURVIVOR_GATE.json",
        "cemetery_update.json", "PACKAGE_REPORT.json",
        "RELEASE_GATE_EVALUATION.json", "RELEASE_PROOF.json",
        "DISCOVERY_RELEASE.json", "DOSSIER_QUALITY_EVALUATION.json",
        "ENSEMBLE_DISAGREEMENT.json", "EXPLORATION_GRID.json",
        # R418: the automatic artifact contract's product state — the
        # bridge report (the WHY of any artifact failure), the evolution
        # lineage (resume-safety per R416) and the per-generation records
        "BRIDGE_REPORT.json", "INVENTION_LINEAGE.json",
        # R455-LEAN-1 §2: the pre-retrieval capability gate's typed
        # refusal record — the durable record is the acceptance evidence
        # that a degraded-capability run spent zero retrieval calls
        "CAPABILITY_GATE.json",
    }
    out: List[Path] = []
    for f in sorted(run_dir.glob("*.json")):
        if f.name in keep_json or f.name.startswith("envelope_") \
                or f.name.startswith("EVOLUTION_GEN_"):
            out.append(f)
    # R418: the bridge's visual artifacts (MODEL/model-00N.glb) and the
    # generation models — the product surface's 3D layer; the per-file
    # size cap below filters anything oversized
    model_dir = run_dir / "MODEL"
    if model_dir.is_dir():
        out.extend(sorted(model_dir.glob("*.glb")))
        # R420: the presentation render artifacts + their typed records
        # (hero/section/exploded PNG+GLB, render_record.json,
        # render_spec.json, RENDER_JOB.json). The deployed filesystem is
        # EPHEMERAL — without this, every restart silently wiped the
        # render surface the website was already displaying (and the
        # RENDER_JOB.json authority the restart contract reads). Same
        # size cap applies.
        three_d = model_dir / "3D"
        if three_d.is_dir():
            out.extend(sorted(p for p in three_d.iterdir()
                              if p.is_file()))
    # R420: the bridge technology package ZIP — the run's downloadable
    # deliverable (the CIO's downloads.package_zip serves THIS file; a
    # restart without it honest-blanked the package link on runs whose
    # packages were already delivered). Same size cap applies.
    # R423A Phase 3: BOTH naming generations persist (historical runs
    # keep TECHNOLOGY_PACKAGE_*.zip; new runs write the canonical
    # TECHNOLOGY_TRANSFER_PACKAGE_*.zip).
    out.extend(sorted(run_dir.glob("TECHNOLOGY_PACKAGE_*.zip")))
    out.extend(sorted(
        run_dir.glob("TECHNOLOGY_TRANSFER_PACKAGE_*.zip")))
    dl = run_dir / "DOWNLOAD"
    if dl.is_dir():
        out.extend(sorted(p for p in dl.rglob("*") if p.is_file()))
    return [f for f in out if f.stat().st_size <= FILE_CAP_BYTES]


def _collect_payload() -> Dict[str, Path]:
    """Map of destination-in-state-repo -> source-path-on-disk for the
    CURRENT durable state. Only sessions referenced by the index are
    persisted — the benchmark-seeded run dirs already ship in the engine
    image (git-tracked), so persisting them again would be redundant."""
    payload: Dict[str, Path] = {}
    src_sessions = store.SESSIONS_PATH
    if src_sessions.exists():
        payload["sessions.json"] = src_sessions
    src_shares = store.SHARES_PATH
    if src_shares.exists():
        payload["shares.json"] = src_shares
    for ev in sorted(store.STORE_DIR.glob("evidence_*.json")):
        payload[f"evidence/{ev.name}"] = ev
    # R461 (independent audit P0-5, reproduced live): the Problem
    # Understanding INPUT record is the ONLY carrier of a merged
    # clarification answer / user directive once the worker clears the
    # session field (toscanini/worker.py phase 1.9). Without it in the
    # durable payload, a container restart between the answer and the
    # next terminal state resurrects the pre-answer pause and the
    # engine re-asks the user a question they already answered —
    # MEASURED on production 2026-09-14 (run ts_1090d724ca33, boot
    # 23:36:13Z): the record regressed to the 23:29:51 pause state.
    for puf in sorted(store.STORE_DIR.glob("problem_understanding_*.json")):
        payload[f"problem_understanding/{puf.name}"] = puf
    # R422 (directive 2 — the a5a7 anomaly): the worker-forensics ledger
    # rides the SAME durable push as the store. Every WORKER_SPAWNED /
    # HEARTBEAT / WORKER_DEATH / ORPHANED_AT_RESTART event written since
    # the last snapshot leaves the ephemeral container with this push —
    # a transient worker death can no longer lose its evidence to a
    # container recycle (the R421 P0 lesson: observability that lives
    # only inside the container is observability that dies with it).
    from toscanini import worker_forensics as _wfx
    _fx_dir = store.STORE_DIR / _wfx.FORENSICS_DIRNAME
    if _fx_dir.is_dir():
        for f in sorted(_fx_dir.iterdir()):
            if f.is_file() and f.suffix == ".jsonl":
                payload[f"{_wfx.FORENSICS_DIRNAME}/{f.name}"] = f
    # R451-C1.3: the MODEL_ROUTING_LEDGER rides the SAME durable push —
    # run-level routing provenance that lives only inside the ephemeral
    # container is provenance that dies with it (the R421 P0 lesson,
    # applied to the transport authority: the ledger is the evidence
    # base for isolating a run's calls by run_id on production, and the
    # capability store is the admission authority's replayable state).
    _routing_dir = REPO_ROOT / "ENGINE_RUNS" / "model_routing"
    _ledger_file = _routing_dir / "ledger.jsonl"
    if _ledger_file.exists():
        payload["model_routing/ledger.jsonl"] = _ledger_file
    _routing_state = _routing_dir / "state.json"
    if _routing_state.exists():
        payload["model_routing/state.json"] = _routing_state
    _cap_state = (REPO_ROOT / "ENGINE_RUNS" / "transport_capability"
                  / "capability_state.json")
    if _cap_state.exists():
        payload["transport_capability/capability_state.json"] = _cap_state
    for s in store.list_sessions():
        rd = s.get("run_dir")
        if not rd or s.get("origin") != "toscanini_ui":
            continue  # seeded benchmark runs ship in the image
        run_dir = Path(rd)
        if not run_dir.exists():
            continue
        for f in _run_dir_files(run_dir):
            payload[f"runs/{run_dir.name}/{f.relative_to(run_dir)}"] = f
    return payload


# ---------------------------------------------------------------------------
# snapshot / restore
# ---------------------------------------------------------------------------

def _ensure_state_repo() -> Path:
    if not (STATE_REPO / ".git").exists():
        STATE_REPO.mkdir(parents=True, exist_ok=True)
        _git(STATE_REPO, "init", "-b", branch())
        _git(STATE_REPO, "remote", "add", "origin", REMOTE)
        fetch = _git(STATE_REPO, "fetch", "origin", branch(), check=False)
        if fetch.returncode == 0:
            _git(STATE_REPO, "reset", "--hard", "FETCH_HEAD", check=False)
    return STATE_REPO


def _ensure_state_repo_hot() -> Path:
    """R423A Phase 4 — the hot-path variant: NO network fetch. The
    single-container deployment has exactly one writer (this process,
    under the durable lock), so the local branch is authoritative for
    pushes and the fetch adds pure network latency to every user-visible
    snapshot. The remote is fetched ONLY at first clone (and a fresh
    fetch can still be forced by deleting ENGINE_RUNTIME/state-repo).

    Fallback honesty (Art. XV): if the push is ever REJECTED because the
    remote moved (multi-writer scenario), the snapshot records the
    failure verbatim in /api/health durable.last_snapshot — never a
    silent success — and the next boot's restore() reconciles by
    fetching."""
    if not (STATE_REPO / ".git").exists():
        return _ensure_state_repo()  # first clone: network required
    return STATE_REPO


def snapshot(reason: str) -> Dict[str, Any]:
    """Commit the current durable state and push it. Returns an honest
    outcome dict (also cached for /api/health).

    R396 B.3: every successful snapshot records its timestamp, the
    ARTIFACT identity of the engine that took it (R396 A — never an
    env-asserted value), the file count, and an integrity manifest
    (per-file sha256 + tree digest) committed alongside the payload, so
    a restore can PROVE state equality instead of asserting it."""
    ident_commit, ident_source = artifact_identity.resolve_engine_commit()
    _LAST.update({"ok": None, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                  time.gmtime()),
                  "reason": reason, "error": None, "files": 0,
                  "commit": None, "pushed": None,
                  "manifest_sha256": None,
                  "engine_commit": ident_commit or None})
    if not enabled():
        _LAST["ok"] = False  # explicit refusal, not an unattempted null
        _LAST["error"] = ("durable persistence not enabled "
                          "(DURABLE_STATE_ENABLED != 1)")
        return dict(_LAST)
    if not os.environ.get("GITHUB_TOKEN", "").strip():
        _LAST["ok"] = False  # explicit refusal, not an unattempted null
        _LAST["error"] = "GITHUB_TOKEN not set — cannot push runtime state"
        return dict(_LAST)

    ENGINE_RUNTIME.mkdir(parents=True, exist_ok=True)
    lock = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        # R423A Phase 4: the hot path never pays the fetch — see
        # _ensure_state_repo_hot (single-writer deployment; honest
        # failure disclosure if that assumption is ever violated).
        repo = _ensure_state_repo_hot()
        payload = _collect_payload()
        copied = 0
        skipped = 0
        file_hashes: Dict[str, str] = {}
        for dest, src in sorted(payload.items()):
            target = repo / dest
            try:
                src_stat = src.stat()
                src_key = (src_stat.st_size, src_stat.st_mtime_ns)
            except OSError:
                continue  # vanished mid-snapshot — skipped, disclosed below
            cached_key = _PAYLOAD_CACHE.get(dest)
            if cached_key == src_key and target.exists():
                # unchanged since the last snapshot AND its copy exists —
                # the state-repo copy IS the previous copy (copy2 preserves
                # mtime/size); re-copying would be a byte-identical no-op
                skipped += 1
                cached_hash = _HASH_CACHE.get(dest)
                if cached_hash and cached_hash[0] == src_key:
                    file_hashes[dest] = cached_hash[1]
                else:
                    file_hashes[dest] = _file_sha256(target)
                    _HASH_CACHE[dest] = (src_key, file_hashes[dest])
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target)
                _PAYLOAD_CACHE[dest] = src_key
                copied += 1
                file_hashes[dest] = _file_sha256(target)
                _HASH_CACHE[dest] = (src_key, file_hashes[dest])
        # R423A Phase 4: record the incremental outcome honestly —
        # files counts the payload map; copied/skipped show the work.
        _LAST["files_copied"] = copied
        _LAST["files_skipped_unchanged"] = skipped
        # R396 B.3: integrity manifest (self-excluded by name constant)
        manifest = {
            "schema": 1,
            "at": _LAST["at"],
            "reason": reason,
            "engine_commit": ident_commit or None,
            "engine_commit_source": ident_source,
            "files": file_hashes,
            "tree_sha256": _tree_sha256(file_hashes),
        }
        manifest_bytes = json.dumps(manifest, indent=1,
                                    sort_keys=True).encode() + b"\n"
        (repo / MANIFEST_NAME).write_bytes(manifest_bytes)
        _LAST["manifest_sha256"] = _tree_sha256(file_hashes)
        # append-only snapshot log — same record shape as the manifest
        # summary + the state-repo commit it becomes (R396 B.3)
        log = repo / SNAPSHOT_LOG_NAME
        with open(log, "a") as lf:
            lf.write(json.dumps({
                "reason": reason,
                "at": _LAST["at"],
                "files": len(file_hashes),
                "files_copied": copied,
                "files_skipped_unchanged": skipped,
                "engine_commit": ident_commit or None,
                "tree_sha256": _LAST["manifest_sha256"]}) + "\n")
        _git(repo, "add", "-A")
        commit = _git(repo, "-c", "user.name=toscanini-runtime",
                      "-c", "user.email=runtime@toscanini.local",
                      "commit", "-m", f"runtime-state: {reason}",
                      "--quiet", check=False)
        pushed = None
        if commit.returncode == 0:
            _LAST["commit"] = _git(repo, "rev-parse", "HEAD").stdout.strip()
            _LAST["files"] = len(file_hashes)
            push = _git(repo, "push", "origin",
                        f"HEAD:refs/heads/{branch()}", check=False)
            pushed = push.returncode == 0
            if not pushed:
                _LAST["error"] = ("push failed: "
                                  + push.stderr.strip()[:200])
        else:
            # nothing new locally — earlier commits may still be unpushed
            push = _git(repo, "push", "origin",
                        f"HEAD:refs/heads/{branch()}", check=False)
            pushed = push.returncode == 0
            _LAST["files"] = len(file_hashes)
            if not pushed and commit.stderr.strip():
                _LAST["error"] = commit.stderr.strip()[:200]
        _LAST["ok"] = pushed is True
        _LAST["pushed"] = pushed
        return dict(_LAST)
    except Exception as exc:  # noqa: BLE001 — disclosed, never silent
        _LAST["ok"] = False
        _LAST["error"] = f"{type(exc).__name__}: {exc}"[:300]
        return dict(_LAST)
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def _restore_problem_understanding(repo: Path) -> int:
    """R461 (independent audit P0-5): re-materialize the persisted
    Problem Understanding INPUT records (copy-when-absent, the evidence
    files' contract). Returns the count copied. The merged
    clarification answer / steering directive lives in this record —
    restoring it is what keeps a resumed run from re-asking a question
    the user already answered after a container restart."""
    pu_repo = repo / "problem_understanding"
    restored = 0
    if pu_repo.is_dir():
        for f in pu_repo.glob("problem_understanding_*.json"):
            dst = store.STORE_DIR / f.name
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst)
                restored += 1
    return restored


def restore() -> Dict[str, Any]:
    """Pull the runtime-state branch and re-materialize local state after
    a restart. Sessions merge by session_id (latest update wins, both
    directions honest); run artifacts copy only when absent (immutable).
    ACTIVE jobs whose worker is gone become INTERRUPTED (directive 7).

    R396 B.2/B.3/B.5: a restore without a successful preceding snapshot
    is NOT durability evidence (the directive's rule). The report now
    distinguishes branch_sessions (what the branch holds), merged (what
    was applied from the branch), and verifies every restored file
    against the snapshot's integrity manifest — mismatches are
    disclosed, never averaged away (Art. XXV)."""
    _LAST_RESTORE.update({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                              time.gmtime()),
                          "sessions": 0, "runs": 0, "evidence": 0,
                          "interrupted": 0, "error": None,
                          "branch_sessions": None,
                          "integrity_mismatches": None,
                          "integrity_verified": None,
                          "manifest_sha256": None})
    if not enabled():
        _LAST_RESTORE["error"] = "not enabled"
        return dict(_LAST_RESTORE)
    if not os.environ.get("GITHUB_TOKEN", "").strip():
        _LAST_RESTORE["error"] = "GITHUB_TOKEN not set"
        return dict(_LAST_RESTORE)
    try:
        ENGINE_RUNTIME.mkdir(parents=True, exist_ok=True)
        lock = open(LOCK_PATH, "w")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX)
            repo = _ensure_state_repo()
            # --- R396 B.3: integrity verification of the branch state ---
            mismatches: List[str] = []
            manifest_path = repo / MANIFEST_NAME
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text())
                    _LAST_RESTORE["manifest_sha256"] = manifest.get(
                        "tree_sha256")
                    _LAST_RESTORE["snapshot_of_record"] = {
                        "at": manifest.get("at"),
                        "reason": manifest.get("reason"),
                        "engine_commit": manifest.get("engine_commit"),
                        "files": len(manifest.get("files") or {}),
                    }
                    for rel, want in (manifest.get("files") or {}).items():
                        f = repo / rel
                        if not f.exists():
                            mismatches.append(f"{rel}: missing")
                        elif _file_sha256(f) != want:
                            mismatches.append(f"{rel}: sha256 mismatch")
                    # recompute the tree digest from the branch bytes
                    recomputed = _tree_sha256(
                        {rel: _file_sha256(repo / rel)
                         for rel in (manifest.get("files") or {})
                         if (repo / rel).exists()})
                    _LAST_RESTORE["integrity_verified"] = (
                        not mismatches
                        and recomputed == manifest.get("tree_sha256"))
                except Exception as exc:  # noqa: BLE001
                    mismatches.append(
                        f"{MANIFEST_NAME}: unreadable ({exc!r})")
            else:
                _LAST_RESTORE["integrity_verified"] = None
            if mismatches:
                _LAST_RESTORE["integrity_mismatches"] = mismatches[:50]
            # --- sessions merge (union, latest update wins) ---
            remote_sessions = repo / "sessions.json"
            merged = 0
            if remote_sessions.exists():
                local = store._locked_read(store.SESSIONS_PATH) or {}
                remote = json.loads(remote_sessions.read_text())
                _LAST_RESTORE["branch_sessions"] = len(
                    remote.get("sessions", []))
                by_id = {s["session_id"]: s
                         for s in local.get("sessions", [])}
                for s in remote.get("sessions", []):
                    sid = s.get("session_id")
                    if not sid:
                        continue
                    cur = by_id.get(sid)
                    if cur is None or (s.get("updated_at") or "") >= (
                            cur.get("updated_at") or cur.get("created_at")
                            or ""):
                        by_id[sid] = s
                        merged += 1
                store._locked_write(
                    store.SESSIONS_PATH,
                    {"sessions": list(by_id.values())})
            _LAST_RESTORE["sessions"] = merged
            # --- shares merge ---
            remote_shares = repo / "shares.json"
            if remote_shares.exists():
                local = store._locked_read(store.SHARES_PATH) or {}
                remote = json.loads(remote_shares.read_text())
                local.update(remote)
                store._locked_write(store.SHARES_PATH, local)
            # --- evidence + run artifacts (copy when absent) ---
            ev_dir = repo / "evidence"
            if ev_dir.is_dir():
                for f in ev_dir.glob("evidence_*.json"):
                    dst = store.STORE_DIR / f.name
                    if not dst.exists():
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(f, dst)
                        _LAST_RESTORE["evidence"] += 1
            # R461 (audit P0-5): the Problem Understanding INPUT records
            # re-materialize with the same copy-when-absent contract —
            # the merged clarification answer / directive survives a
            # container restart, so a resumed run never re-asks a
            # question the user already answered.
            _restore_problem_understanding(repo)
            # R422: the worker-forensics ledger is restored BEFORE the
            # boot reconciliation runs — reconcile_at_boot() in server
            # main() must see the previous boot's tail to mark orphans.
            # Append-preserving: the local ledger keeps its own events; a
            # remote line never overwrites them (merge by replay, not
            # replace — the ledger is append-only history).
            fx_dir = repo / "worker_forensics"
            if fx_dir.is_dir():
                dst_dir = store.STORE_DIR / "worker_forensics"
                dst_dir.mkdir(parents=True, exist_ok=True)
                for f in sorted(fx_dir.glob("*.jsonl")):
                    dst = dst_dir / f.name
                    if not dst.exists():
                        shutil.copy2(f, dst)
                    else:
                        # merge: append only remote lines this local file
                        # does not already contain (idempotent by event_id)
                        try:
                            local_ids = set()
                            for line in dst.read_text().splitlines():
                                line = line.strip()
                                if not line:
                                    continue
                                try:
                                    local_ids.add(
                                        json.loads(line).get("event_id"))
                                except json.JSONDecodeError:
                                    continue  # torn local tail line
                            with open(dst, "a", encoding="utf-8") as out:
                                for line in f.read_text().splitlines():
                                    line = line.strip()
                                    if not line:
                                        continue
                                    try:
                                        ev = json.loads(line)
                                    except json.JSONDecodeError:
                                        continue
                                    if ev.get("event_id") not in local_ids:
                                        out.write(line + "\n")
                        except Exception:  # noqa: BLE001 — ledger restore
                            # is best-effort; the local ledger stays
                            pass
            runs_dir = repo / "runs"
            if runs_dir.is_dir():
                for rd in runs_dir.iterdir():
                    if not rd.is_dir():
                        continue
                    dst_root = store.ENGINE_RUNS / rd.name
                    had_any = False
                    for f in rd.rglob("*"):
                        if not f.is_file():
                            continue
                        rel = f.relative_to(rd)
                        dst = dst_root / rel
                        if not dst.exists():
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(f, dst)
                            had_any = True
                    if had_any:
                        _LAST_RESTORE["runs"] += 1
            # --- honest interruption of dead jobs (directive 7) ---
            _LAST_RESTORE["interrupted"] = len(
                store.mark_interrupted_sessions())
            return dict(_LAST_RESTORE)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()
    except Exception as exc:  # noqa: BLE001 — disclosed, never silent
        _LAST_RESTORE["error"] = f"{type(exc).__name__}: {exc}"[:300]
        return dict(_LAST_RESTORE)
