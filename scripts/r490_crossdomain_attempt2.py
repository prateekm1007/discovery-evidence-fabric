#!/usr/bin/env python3
"""R490 — the HEALTHY-RING cross-domain attempt (the R489 directive:
"family carried in the submission, atria serving, collision searches
completing") BEFORE the gauntlet is scored.

What is different from the R487/R489 attempt (ts_f0880e025e60, typed
NOT_CROSS_DOMAIN_CLOSURE):
  1. FAMILY CARRIED IN THE SUBMISSION — the R489 record's
     submission_path_note named two remedies; this driver takes the
     first: the submitted problem text ENDS with a declared-family
     line naming the sha256-pinned corpus record as the family
     authority. The line rides verbatim into the run's durable
     problem.json (user_text) — byte-checkable at harvest. The corpus
     text itself stays verbatim-untouched ahead of that line.
  2. OWNER CAPABILITY PRESERVED — BS-021 killed R489's observation
     into a durable-branch harvest. This driver persists run_id +
     owner_key to the UNTRACKED session file the moment the launch
     response lands (never printed in full; fingerprint only).
  3. HEALTHY-RING OBSERVATION — the ring is a server-side runtime
     property; this driver OBSERVES it per stage from the durable
     envelopes (provider/model/substituted_from on synthesis and
     attack, collision mandatory-search completion) and records
     whatever it says. Ring health is never assumed.

Identity gate: this proof runs on the deployed instrument build
(EXPECTED_IDENTITY, REQUIRED) — the same discipline as R487/R489.

Slice-resumable (Art. LXXIV): each invocation polls at most
--slice-seconds and exits cleanly; re-invocation resumes the SAME run.
Observation failure is never a run verdict.

Typed proof outcomes (the record, whatever it says — Art. VI):
  LOOP_CLOSED_ADMITTED / LOOP_CLOSED_REKILLED / NO_KILL_EVIDENCE /
  IMPROVE_ABSENT / DURABLE_HARVEST_PENDING / STAGE_*

Reviewer provenance: AI_REVIEW (Art. LXVII). English only (Art. LXX).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
OUT = REPO_ROOT / "R490" / "CROSSDOMAIN_ATTEMPT2.json"
SESSION = Path("/home/z/my-project/scripts/r490_crossdomain_session.json")
SESSION_TRACKED = REPO_ROOT / "R490" / "CROSSDOMAIN_SESSION.json"
CORPUS_PATH = REPO_ROOT / "R458" / "BENCHMARK_CORPUS.json"
PROBLEM_KEY = "M1"
POLL_INTERVAL_S = 25
# the r484 terminal vocabulary + the store's typed ERROR_* statuses
TERMINAL = ("COMPLETE", "FAILED", "ERROR", "ERROR_RUN", "ERROR_STUCK",
            "DONE", "INTERRUPTED", "RUN_BLOCKED_TRANSPORT",
            "RUN_BLOCKED_CAPABILITY")
# slug tokens that identify THIS problem's run dirs on the durable
# branch (matched case-insensitively; the manifest session_id is the
# exact verifier)
SLUG_TOKENS = ("cam", "follower", "packaging")

HF_TOKEN = (os.environ.get("HF_TOKEN", "").strip() or "")
if not HF_TOKEN:
    _p = Path("/home/z/my-project/.secrets.env")
    if _p.exists():
        for _line in _p.read_text().splitlines():
            if _line.startswith("HF_TOKEN="):
                HF_TOKEN = _line.split("=", 1)[1].strip()


def _log(msg: str) -> None:
    print(f"[r490-xdom] {msg}", flush=True)


def _fp(secret: Optional[str]) -> str:
    """BS-021 fingerprint: never the value."""
    if not secret:
        return "(absent)"
    return f"len={len(secret)} head={secret[:6]}…"


def _req(path: str, body: Optional[Dict[str, Any]] = None,
         timeout: int = 120, owner_key: Optional[str] = None):
    import urllib.error
    import urllib.request
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json",
               "Authorization": f"Bearer {HF_TOKEN}"}
    if owner_key:
        headers["X-Tosca-Owner"] = owner_key
    req = urllib.request.Request(BASE + path, data=data, headers=headers,
                                 method="POST" if data is not None
                                 else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"http_status": r.status,
                    "body": json.loads(r.read() or b"{}")}
    except urllib.error.HTTPError as e:
        try:
            txt = e.read()[:300].decode(errors="replace")
        except Exception:  # noqa: BLE001
            txt = ""
        return {"http_status": e.code, "error": txt}
    except Exception as exc:  # noqa: BLE001
        return {"http_status": None,
                "error": f"{type(exc).__name__}: {exc}"}


DECLARED_FAMILY_LINE = (
    "\n\nDeclared at submission — canonical domain family: mechanical "
    "(family authority: R458/BENCHMARK_CORPUS.json sha256 "
    "{corpus_sha}, case r458-m1-cam-follower-surface-fatigue, "
    "split DEV).")


def _load_problem() -> Dict[str, Any]:
    """The durable M1 extraction (the R487 discipline): read from the
    committed corpus, assert it is clean in the worktree, pin its
    sha256. The submission text = the corpus text VERBATIM + the
    declared-family line (the R489 submission-path remedy, disclosed:
    the delta is exactly this line, byte-recorded in the session)."""
    corpus = json.loads(CORPUS_PATH.read_text())
    m1 = corpus["problems"][PROBLEM_KEY]
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", "R458/BENCHMARK_CORPUS.json"],
        cwd=str(REPO_ROOT), capture_output=True, text=True).stdout.strip()
    if dirty:
        raise SystemExit("FATAL: R458/BENCHMARK_CORPUS.json is dirty in "
                         "the worktree — the corpus must be the frozen "
                         "committed bytes")
    corpus_sha = hashlib.sha256(CORPUS_PATH.read_bytes()).hexdigest()
    if not corpus_sha.startswith("f823cfd3"):
        raise SystemExit(
            f"FATAL: corpus sha256 {corpus_sha[:12]} does not match the "
            "R489-pinned corpus (f823cfd3…) — refusing to submit against "
            "a drifted corpus")
    base_text = m1["text"]
    declared = DECLARED_FAMILY_LINE.format(corpus_sha=corpus_sha)
    return {
        "case_id": m1["case_id"],
        "domain_family": m1["domain_family"],
        "split": m1.get("split"),
        "base_text": base_text,
        "submitted_text": base_text + declared,
        "declared_line": declared.strip(),
        "corpus_sha256": corpus_sha,
    }


def _resume() -> Dict[str, Any]:
    if SESSION.exists():
        try:
            return json.loads(SESSION.read_text())
        except Exception:  # noqa: BLE001
            pass
    return {}


def _persist(sess: Dict[str, Any]) -> None:
    SESSION.parent.mkdir(parents=True, exist_ok=True)
    SESSION.write_text(json.dumps(sess, indent=1, default=str))
    red = json.loads(json.dumps(sess, default=str))
    if red.get("case", {}).get("owner_key"):
        red["case"]["owner_key"] = "(redacted, BS-021)"
    SESSION_TRACKED.parent.mkdir(parents=True, exist_ok=True)
    SESSION_TRACKED.write_text(json.dumps(red, indent=1, default=str))


def _git_show(path: str) -> Optional[str]:
    p = subprocess.run(
        ["git", "show", f"origin/runtime-state-hf:{path}"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60)
    return p.stdout if p.returncode == 0 else None


def _safe_json(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        return None


def _route(env_json: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Per-stage transport provenance: provider/model/subscription —
    the healthy-ring observation, read the same way R489 read it."""
    if not env_json:
        return None
    rc = (env_json.get("mechanism_map") or {}).get("raw_candidate") or {}
    if not rc:
        rc = env_json.get("raw_candidate") or {}
    se = rc.get("source_evidence") or {}
    route = {
        "provider": rc.get("provider"),
        "model": rc.get("model"),
        "substituted_from": rc.get("substituted_from"),
    }
    if se:
        route["source_id"] = se.get("source_id")
        route["source_span_chars"] = len(se.get("source_span") or "")
    return {k: v for k, v in route.items() if v is not None} or None


def _durable_harvest(session_id: str) -> Dict[str, Any]:
    """The durable branch is the authority (the R481 lesson). Dirs are
    matched by slug tokens, then VERIFIED by the manifest session_id —
    the exact run, never a heuristic pick. Best-effort and honest."""
    out: Dict[str, Any] = {}
    try:
        subprocess.run(["git", "fetch", "origin", "runtime-state-hf"],
                       cwd=REPO_ROOT, capture_output=True, timeout=180,
                       env={**os.environ,
                            "GIT_ASKPASS": "/home/z/my-project/scripts/"
                                           "git_askpass.sh"})
        tree = subprocess.run(
            ["git", "ls-tree", "--name-only",
             "origin/runtime-state-hf:runs"],
            cwd=REPO_ROOT, capture_output=True, text=True,
            timeout=60).stdout.split()
        low = [t.lower() for t in tree]
        cands = [t for t, lt in zip(tree, low)
                 if any(tok in lt for tok in SLUG_TOKENS)]
        rdir = None
        for c in reversed(cands):  # newest first
            man = _safe_json(_git_show(f"runs/{c}/run_manifest.json"))
            if man and man.get("session_id") == session_id:
                rdir = c
                break
        if rdir is None:
            out["harvested"] = False
            out["reason"] = ("this session's run dir not on the durable "
                             "branch yet (or still running); "
                             f"{len(cands)} slug-candidate dirs checked "
                             "by session_id")
            return out
        out["durable_run_dir"] = rdir

        # the journal: session-id verification + timeline (the R489
        # discipline, kept verbatim)
        raw = _git_show(f"runs/{rdir}/EVENT_JOURNAL.jsonl")
        if raw:
            rows = [json.loads(l) for l in raw.splitlines() if l.strip()]
            ok = all(r.get("run_id") == session_id for r in rows)
            out["journal"] = {
                "rows": len(rows),
                "all_rows_carry_session_id": ok,
                "first_ts": rows[0].get("timestamp") if rows else None,
                "last_ts": rows[-1].get("timestamp") if rows else None,
                "stages": [r.get("stage") for r in rows],
            }

        # SYNTHESIZE — the route that served the candidate
        syn = _safe_json(_git_show(f"runs/{rdir}/envelope_SYNTHESIZE.json"))
        out["synthesis_route"] = _route(syn)

        # VERIFY — evidence verification
        ver = _safe_json(_git_show(f"runs/{rdir}/envelope_VERIFY.json"))
        if ver:
            ev = (ver.get("adjudication") or {}).get(
                "evidence_verification") or {}
            out["verify"] = {"verified": ev.get("verified"),
                             "issues": ev.get("issues")}

        # PREMISE GATE
        pg = _safe_json(_git_show(f"runs/{rdir}/envelope_PREMISE_GATE.json"))
        if pg:
            g = pg.get("premise_gate") or {}
            out["premise_gate"] = {"verdict": g.get("verdict"),
                                   "n_rules_checked": g.get("n_rules_checked")}

        # COLLISION — the "collision searches completing" condition,
        # observed whatever it says
        col = _safe_json(_git_show(f"runs/{rdir}/envelope_COLLISION.json"))
        if col:
            cr = col.get("collision_results") or {}
            ms = cr.get("mandatory_searches") or {}
            out["collision"] = {
                "mandatory_pairs": ms.get("mandatory_pairs"),
                "failed_pairs": ms.get("failed_pairs"),
                "complete": ms.get("complete"),
                "failed": [{"query": f.get("query"),
                            "source": f.get("source"),
                            "error": f.get("error")}
                           for f in (ms.get("failed") or [])],
                "prior_art_status": cr.get("prior_art_status"),
                "resolution_state": (cr.get("differentiation_resolution")
                                     or {}).get("state"),
            }

        # ATTACK + CLASSIFY — the terminal rejection authority path
        # (the A2 gauntlet), recorded with its transport provenance
        atk = _safe_json(_git_show(f"runs/{rdir}/envelope_ATTACK.json"))
        if atk:
            out["attack"] = _route(atk) or {}
            dims = atk.get("attack") or atk.get("adversarial") or {}
            if isinstance(dims, dict):
                out["attack"]["dimension_summary"] = {
                    k: (v.get("verdict") if isinstance(v, dict) else v)
                    for k, v in list(dims.items())[:12]
                    if not isinstance(v, (list, dict)) or
                    isinstance(v, dict)}
        cls = _safe_json(_git_show(f"runs/{rdir}/envelope_CLASSIFY.json"))
        if cls:
            c = cls.get("classification") or cls
            out["classify"] = {
                k: c.get(k) for k in
                ("attack_overall", "killed", "kill_dimensions",
                 "classification", "reason")
                if c.get(k) is not None}

        # IMPROVE — the closure evidence
        imp = _safe_json(_git_show(f"runs/{rdir}/envelope_IMPROVE.json"))
        if imp:
            sl = imp.get("stage_log") or []
            out["improve_entries"] = [
                {k: e.get(k) for k in
                 ("stage", "status", "result_meta", "before_envelope_hash",
                  "after_envelope_hash", "candidate_delta", "delta_real",
                  "started_at", "finished_at")}
                for e in sl if e.get("stage") == "IMPROVE"]

        # SURVIVOR_SELECTION / lineage — post-admission facts if reached
        ss = _safe_json(_git_show(f"runs/{rdir}/SURVIVOR_SELECTION.json"))
        if ss:
            out["survivor_selection"] = {
                "selected": ss.get("selected"),
                "n_ranked": len(ss.get("ranked") or []),
                "ranked": [{k: r.get(k) for k in
                            ("candidate_id", "killed", "attack_overall",
                             "quality_verdict", "repaired")}
                           for r in (ss.get("ranked") or [])]}
        lin = _safe_json(_git_show(f"runs/{rdir}/INVENTION_LINEAGE.json"))
        if lin:
            out["lineage"] = {
                "n_generations": lin.get("n_generations"),
                "n_evolution_generations": lin.get("n_evolution_generations"),
                "survivor_reached": lin.get("survivor_reached"),
                "final_state": lin.get("final_state"),
            }

        # terminal facts + the family channels
        fs = _safe_json(_git_show(f"runs/{rdir}/final_state.json"))
        if fs:
            out["final_state"] = {
                k: fs.get(k) for k in
                ("final_status", "epistemic_state", "reason",
                 "evidence_verified", "premise_verdict")}
        pj = _safe_json(_git_show(f"runs/{rdir}/problem.json"))
        if pj:
            fam = pj.get("canonical_family")
            out["problem_declared_family"] = fam if isinstance(fam, str) \
                else ("ABSENT (canonical_family null — the "
                      "text-only submission path still does not "
                      "populate the field; the family travels in the "
                      "declared line instead)")
            ut = pj.get("user_text") or ""
            out["submission_family_carried"] = {
                "user_text_chars": len(ut),
                "declared_line_verbatim_suffix": ut.endswith(
                    DECLARED_FAMILY_LINE.format(
                        corpus_sha=hashlib.sha256(
                            CORPUS_PATH.read_bytes()).hexdigest())
                    .strip()),
                "base_text_verbatim_prefix": ut.startswith(
                    json.loads(CORPUS_PATH.read_text())
                    ["problems"][PROBLEM_KEY]["text"]),
            }
        out["harvested"] = True
    except Exception as exc:  # noqa: BLE001 — honest harvest failure
        out["harvested"] = False
        out["reason"] = f"{type(exc).__name__}: {exc}"
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice-seconds", type=int, default=540,
                    help="max polling seconds this invocation (clean "
                         "foreground slice; re-invoke to resume)")
    ap.add_argument("--launch-only", action="store_true",
                    help="submit (if needed) and exit without polling")
    args = ap.parse_args()

    problem = _load_problem()
    expected = os.environ.get("EXPECTED_IDENTITY", "").strip()
    if not expected:
        _log("FATAL: EXPECTED_IDENTITY (env) is REQUIRED")
        return 2
    v = _req("/api/version")
    served = (v.get("body") or {}).get("engine_commit", "")
    if served != expected:
        _log(f"identity gate: production serves {served[:12] or '(none)'}, "
             f"expected {expected[:12]}")
        return 2
    _log(f"identity verified: {served[:12]}")

    sess = _resume()
    entry = sess.get("case") or {}
    record: Dict[str, Any] = sess.get("record") or {}
    record.setdefault("submission", {
        "case_id": problem["case_id"],
        "domain_family_corpus": problem["domain_family"],
        "split": problem["split"],
        "corpus_sha256": problem["corpus_sha256"],
        "base_text_chars": len(problem["base_text"]),
        "submitted_text_chars": len(problem["submitted_text"]),
        "submitted_text_sha256": hashlib.sha256(
            problem["submitted_text"].encode()).hexdigest(),
        "declared_family_line": problem["declared_line"],
        "family_carriage": (
            "the R489 submission-path remedy (option 1): the family is "
            "carried IN the submission as a disclosed trailing line "
            "naming the sha-pinned corpus as authority; the corpus text "
            "ahead of it is verbatim-untouched; the delta is exactly "
            "this line"),
        "prior_closures_families": (
            "attempt-5 geothermal calcite/silica + the cyclone-variant "
            "line — thermal/fluid territory; the R489 attempt-6 run "
            "(ts_f0880e025e60) died pre-loop on a degraded ring; THIS "
            "is the mechanical-family repetition on a fresh ring "
            "observation"),
    })

    if not entry.get("run_id"):
        r = _req("/api/run", body={"text": problem["submitted_text"]},
                 timeout=180)
        if r.get("http_status") not in (200, 202):
            _log(f"submit failed {r.get('http_status')} "
                 f"{str(r.get('error'))[:200]}")
            return 1
        b = r.get("body") or {}
        entry = {"run_id": b.get("session_id") or b.get("run_id"),
                 "owner_key": b.get("owner_key"),
                 "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                               time.gmtime())}
        _log(f"submitted {entry['run_id']} owner {_fp(entry['owner_key'])}")
    else:
        _log(f"resuming {entry['run_id']} owner {_fp(entry.get('owner_key'))}")
    sess["case"] = entry
    sess["record"] = record
    _persist(sess)  # owner capability durable from this moment (BS-021)
    if args.launch_only:
        _log("launch-only slice: exiting; re-invoke to poll")
        return 0

    sid, owner = entry["run_id"], entry.get("owner_key")

    t0 = time.time()
    final = None
    while time.time() - t0 < args.slice_seconds:
        r = _req(f"/api/run/{sid}/result", owner_key=owner, timeout=90)
        if r.get("http_status") == 200:
            body = r.get("body") or {}
            st = str(body.get("status") or "").upper()
            if st in TERMINAL:
                final = body
                _log(f"terminal: {st}")
                break
            if st:
                _log(f"... {st}")
        elif r.get("http_status") not in (200, 404):
            _log(f"poll {r.get('http_status')} "
                 f"{str(r.get('error'))[:120]}")
        time.sleep(POLL_INTERVAL_S)
    if final is None:
        _log(f"slice deadline ({args.slice_seconds}s) — re-invoke to "
             f"resume the SAME run {sid} (Art. LXXIV: observation is "
             "not execution)")
        return 2

    # the durable harvest (the authority for stage_log + provenance)
    time.sleep(90)  # the worker's durable checkpoint cadence
    durable = _durable_harvest(sid)
    record.update({
        "run_id": sid,
        "final_status": (final.get("status") or ""),
        "final_reason": str(final.get("reason") or "")[:500],
        "identity_verified": served,
        "submitted_at": entry.get("submitted_at"),
        "terminal_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "durable": durable,
        "reviewer_provenance": "AI_REVIEW",
    })

    imp = durable.get("improve_entries") or []
    statuses = [((e.get("result_meta") or {}).get("status")
                 or e.get("status")) for e in imp]
    _log(f"IMPROVE result statuses: {statuses}")
    _log(f"synthesis route: "
         f"{json.dumps(durable.get('synthesis_route'))[:240]}")
    _log(f"collision: {json.dumps(durable.get('collision'))[:400]}")
    _log(f"submission family carried: "
         f"{json.dumps(durable.get('submission_family_carried'))}")

    if any(s == "CHILDREN_ADMITTED" for s in statuses if s):
        record["proof_outcome"] = "LOOP_CLOSED_ADMITTED"
        code = 0
    elif any(s == "NO_CHILD_ADMITTED" for s in statuses if s):
        record["proof_outcome"] = "LOOP_CLOSED_REKILLED"
        code = 0
    elif any(s == "NO_KILL_EVIDENCE" for s in statuses if s):
        record["proof_outcome"] = "NO_KILL_EVIDENCE"
        code = 0
    elif durable.get("harvested") and not imp:
        record["proof_outcome"] = "IMPROVE_ABSENT"
        code = 3
    elif not durable.get("harvested"):
        record["proof_outcome"] = "DURABLE_HARVEST_PENDING"
        code = 3
    else:
        record["proof_outcome"] = "STAGE_" + "_".join(
            str(s) for s in statuses if s)[:60]
        code = 3

    # the cross-domain comparison — all family channels recorded, the
    # condition used is named, nothing asserted (Art. XV/XXV)
    sub_fam = (durable.get("submission_family_carried") or {}) \
        .get("declared_line_verbatim_suffix")
    run_family = durable.get("problem_declared_family")
    fam_ok = (run_family == "mechanical") or (
        sub_fam is True and run_family != "mechanical")
    record["cross_domain_comparison"] = {
        "corpus_declared_family": problem["domain_family"],
        "submission_declared_family": (
            "mechanical — carried verbatim in the submitted text and "
            "verified byte-present in the durable problem.json"
            if sub_fam is True else
            f"NOT verified in the durable record (suffix check {sub_fam})"),
        "run_declared_family": run_family,
        "engine_resolved_family_local": (
            "mechanical — the committed resolver "
            "(discovery_fabric.engine.domains.resolve_canonical_family) "
            "resolves the corpus M1 text to mechanical deterministically "
            "(score 5 >= min 3), measured locally pre-launch; see "
            "scripts/r490_family_resolution_check.py output"),
        "family_condition_used": (
            "LOOP_CLOSED_ADMITTED AND (run_declared_family == "
            "'mechanical' OR the submission-carried declared line is "
            "verified byte-present with the sha-pinned corpus named as "
            "authority — the R489 submission-path remedy, disclosed "
            "as carriage, never asserted as engine derivation)"),
        "prior_closure_families": "thermal/fluid (geothermal scaling)",
        "verdict": (
            "CROSS_DOMAIN_REPEATED" if (
                record["proof_outcome"] == "LOOP_CLOSED_ADMITTED"
                and fam_ok)
            else "NOT_CROSS_DOMAIN_CLOSURE — the typed outcome above "
                 "and the family channels are the record"),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1, default=str))
    _log(f"outcome: {record['proof_outcome']} | "
         f"comparison: {record['cross_domain_comparison']['verdict'][:80]}"
         f" -> {OUT}")
    sess["record"] = json.loads(json.dumps(record, default=str))
    _persist(sess)
    return code


if __name__ == "__main__":
    sys.exit(main())
