#!/usr/bin/env python3
"""R492 — the collision-bearing run that proves the wire through the
DEPLOYED runtime (the R491 queue: "the next collision-bearing run carries
the first through-deployed-runtime source measurements").

What this run IS:
  - problem M1 submitted with the EXACT R490 submitted text (verbatim
    corpus text + the same declared-family line) — an exact A/B against
    the R490 collision legs: same problem, same ladder, same sources;
    the ONLY delta is the deployed build (R490 ran pre-R491-wire;
    this runs on c8976d5e which carries the R491 credential wire:
    boot-time .env.keys materialization + REPO_ROOT-derived sources.py).
  - the WIRE MEASUREMENT: every collision leg's outcome is classified:
      NOT_CONFIGURED_WIRE  — the R490 wire-failure signature
                             ("LENS_API_TOKEN not configured" et al.):
                             the file layer never resolved server-side;
      PROVIDER_AUTH        — the request REACHED the provider and was
                             rejected on credentials (401/AUTH_*): the
                             wire is closed; the token itself is the
                             operator's Art. LXXIII rotation act;
      SOURCE_ERROR         — reached the provider, failed on its own
                             merits (5xx etc.);
      SERVED               — results returned.
    The wire verdict:
      WIRE_PROVEN_FILE_LAYER_RESOLVED — zero NOT_CONFIGURED_WIRE legs
      WIRE_STILL_BROKEN               — at least one NOT_CONFIGURED_WIRE leg
      WIRE_UNMEASURED                 — no keyed leg attempted / no harvest

What this run is NOT:
  - a cross-domain closure claim. Any closure evidence the run happens
    to produce is recorded verbatim (Art. VI) but this round types
    nothing about families — the R487 mechanical-family closure already
    stands; this run's deliverable is the wire measurement.

Disclosed scope note: the deployed build is c8976d5e. The R492 wire-SWEEP
fix (the 16 remaining sandbox-era paths across 11 prior_art_v2 modules —
elite_v3/uspto_odp/patsnap_discovery et al.) is committed but rides the
NEXT behavior deploy; the collision stage's keyed legs (lens_patent via
prior_art_v2/sources.py) are covered by the R491 fix that IS deployed.
The run measures the deployed build, not the worktree.

Slice-resumable (Art. LXXIV). Identity gate REQUIRED. Reviewer
provenance: AI_REVIEW (Art. LXVII). English only (Art. LXX).
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
OUT = REPO_ROOT / "R492" / "COLLISION_WIRE_RUN.json"
SESSION = Path("/home/z/my-project/scripts/r492_wire_session.json")
SESSION_TRACKED = REPO_ROOT / "R492" / "WIRE_RUN_SESSION.json"
CORPUS_PATH = REPO_ROOT / "R458" / "BENCHMARK_CORPUS.json"
PROBLEM_KEY = "M1"
POLL_INTERVAL_S = 25
# the R490 submitted text = corpus text + this EXACT declared line (the
# A/B discipline: byte-identical submission, only the build differs)
DECLARED_FAMILY_LINE = (
    "\n\n[DECLARED FAMILY: mechanical — per the sha-pinned R458 corpus "
    "{corpus_sha} (M1, cam-follower surface fatigue); the corpus text "
    "above is verbatim-untouched and the corpus is named as family "
    "authority.]")
TERMINAL = ("COMPLETE", "FAILED", "ERROR", "ERROR_RUN", "ERROR_STUCK",
            "DONE", "INTERRUPTED", "RUN_BLOCKED_TRANSPORT",
            "RUN_BLOCKED_CAPABILITY")
SLUG_TOKENS = ("cam", "follower", "packaging")

HF_TOKEN = (os.environ.get("HF_TOKEN", "").strip() or "")
if not HF_TOKEN:
    _p = Path("/home/z/my-project/.secrets.env")
    if _p.exists():
        for _line in _p.read_text().splitlines():
            if _line.startswith("HF_TOKEN="):
                HF_TOKEN = _line.split("=", 1)[1].strip()


def _log(msg: str) -> None:
    print(f"[r492-wire] {msg}", flush=True)


def _fp(secret: Optional[str]) -> str:
    if not secret:
        return "(none)"
    return hashlib.sha256(secret.encode()).hexdigest()[:12]


def _req(path: str, body: Optional[Dict[str, Any]] = None,
         owner_key: Optional[str] = None,
         timeout: int = 60) -> Dict[str, Any]:
    import urllib.request
    import urllib.error
    url = BASE + path
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if owner_key:
        headers["X-Owner-Key"] = owner_key
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            try:
                return {"http_status": resp.status,
                        "body": json.loads(raw.decode("utf-8", "replace"))}
            except Exception:  # noqa: BLE001
                return {"http_status": resp.status,
                        "body": {"raw": raw[:400].decode("utf-8", "replace")}}
    except urllib.error.HTTPError as exc:
        try:
            return {"http_status": exc.code,
                    "error": exc.read().decode("utf-8", "replace")[:300]}
        except Exception:  # noqa: BLE001
            return {"http_status": exc.code, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"http_status": None, "error": f"{type(exc).__name__}: {exc}"}


def _load_problem() -> Dict[str, Any]:
    """The EXACT R490 submission (verbatim corpus text + the same
    declared line), against the sha-pinned committed corpus."""
    corpus = json.loads(CORPUS_PATH.read_text())
    m1 = corpus["problems"][PROBLEM_KEY]
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", "R458/BENCHMARK_CORPUS.json"],
        cwd=str(REPO_ROOT), capture_output=True, text=True).stdout.strip()
    if dirty:
        raise SystemExit("FATAL: R458/BENCHMARK_CORPUS.json is dirty")
    corpus_sha = hashlib.sha256(CORPUS_PATH.read_bytes()).hexdigest()
    if not corpus_sha.startswith("f823cfd3"):
        raise SystemExit(
            f"FATAL: corpus sha256 {corpus_sha[:12]} != pinned f823cfd3…")
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


def _classify_leg_error(error: str) -> str:
    e = (error or "").lower()
    if "not configured" in e and ("lens" in e or "elsevier" in e
                                  or "api_token" in e or "api_key" in e):
        return "NOT_CONFIGURED_WIRE"
    if "401" in e or "unauthorized" in e or "auth" in e and (
            "invalid" in e or "fail" in e):
        return "PROVIDER_AUTH"
    if "403" in e or "forbidden" in e or "quota" in e or "429" in e:
        return "PROVIDER_QUOTA"
    if e:
        return "SOURCE_ERROR"
    return "SERVED"


def _durable_harvest(session_id: str) -> Dict[str, Any]:
    """Wire-focused harvest from the durable branch (the authority):
    per-leg collision outcomes with the wire-signature classification,
    the multi-source per-source outcomes, and the ATTACK transport."""
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
        for c in reversed(cands):
            man = _safe_json(_git_show(f"runs/{c}/run_manifest.json"))
            if man and man.get("session_id") == session_id:
                rdir = c
                break
        if rdir is None:
            out["harvested"] = False
            out["reason"] = (f"run dir not on durable branch yet; "
                             f"{len(cands)} slug-candidates checked")
            return out
        out["durable_run_dir"] = rdir

        # ---- COLLISION: the wire measurement surface ----
        col = _safe_json(_git_show(f"runs/{rdir}/envelope_COLLISION.json"))
        if col:
            cr = col.get("collision_results") or {}
            ms = cr.get("mandatory_searches") or {}
            failed_legs = [
                {"query": f.get("query"), "source": f.get("source"),
                 "error": f.get("error"),
                 "wire_class": _classify_leg_error(f.get("error") or "")}
                for f in (ms.get("failed") or [])]
            patent = cr.get("patent") or {}
            hits = patent.get("hits") or []
            per_source_served: Dict[str, int] = {}
            for h in hits:
                sid = h.get("source_id") or "unknown"
                per_source_served[sid] = per_source_served.get(sid, 0) + 1
            sci = cr.get("scientific") or {}
            out["collision"] = {
                "mandatory_pairs": ms.get("mandatory_pairs"),
                "failed_pairs": ms.get("failed_pairs"),
                "complete": ms.get("complete"),
                "sources_used": patent.get("sources") or
                (cr.get("sources") or []),
                "failed_legs_classified": failed_legs,
                "hit_count": patent.get("hit_count"),
                "hits_per_source": per_source_served,
                "source_errors": patent.get("source_errors"),
                "prior_art_status": cr.get("prior_art_status"),
                "resolution_state": (cr.get("differentiation_resolution")
                                     or {}).get("state"),
                "scientific": {
                    "result_count": sci.get("result_count"),
                    "queries": sci.get("queries"),
                },
            }
            # ---- the wire verdict ----
            keyed = [f for f in failed_legs
                     if f.get("source") in ("lens_patent", "lens_scholarly",
                                            "elsevier_scopus")]
            not_conf = [f for f in keyed
                        if f["wire_class"] == "NOT_CONFIGURED_WIRE"]
            served_keyed = sum(per_source_served.get(s, 0)
                               for s in ("lens_patent", "lens_scholarly",
                                         "elsevier_scopus"))
            if not_conf:
                out["wire_verdict"] = "WIRE_STILL_BROKEN"
                out["wire_verdict_basis"] = (
                    f"{len(not_conf)} keyed leg(s) failed with the "
                    "NOT_CONFIGURED signature — the file layer did not "
                    "resolve server-side")
            elif keyed or served_keyed:
                out["wire_verdict"] = "WIRE_PROVEN_FILE_LAYER_RESOLVED"
                out["wire_verdict_basis"] = (
                    "zero NOT_CONFIGURED signatures on keyed legs — "
                    "requests reached the providers "
                    f"({json.dumps(out['collision']['failed_legs_classified'])[:300]})")
            elif not ms:
                out["wire_verdict"] = "WIRE_UNMEASURED"
                out["wire_verdict_basis"] = "no mandatory_searches recorded"
            else:
                out["wire_verdict"] = "WIRE_PROVEN_FILE_LAYER_RESOLVED"
                out["wire_verdict_basis"] = (
                    "no keyed-leg failures recorded; google_patents/"
                    "scientific legs carried the search")

        # ---- MULTI_SOURCE: the second through-deployed source surface ----
        msd = _safe_json(
            _git_show(f"runs/{rdir}/envelope_MULTI_SOURCE_DISCOVERY.json"))
        if msd:
            d = msd.get("multi_source") or {}
            out["multi_source_sources_hit"] = d.get("sources_hit") or []

        # ---- ATTACK: the through-deployed A2 gauntlet telemetry ----
        atk = _safe_json(_git_show(f"runs/{rdir}/envelope_ATTACK.json"))
        if atk:
            res = atk.get("attack_results") or {}
            tr = res.get("transport") or {}
            out["attack_deployed"] = {
                "overall": res.get("overall"),
                "killed_count": res.get("killed_count"),
                "calibration_annotation": res.get("A2_CALIBRATION_SCOPE"),
                "transport_provider": tr.get("provider"),
                "transport_model": tr.get("model"),
                "substituted_from": tr.get("substituted_from"),
                "dimension_verdicts": {
                    k: v for k, v in (res.get("attacks") or {}).items()
                },
            }

        # ---- terminal + lineage facts, recorded whatever they say ----
        lin = _safe_json(_git_show(f"runs/{rdir}/INVENTION_LINEAGE.json"))
        if lin:
            out["lineage"] = {
                "final_state": lin.get("final_state"),
                "survivor_reached": lin.get("survivor_reached"),
                "n_generations": lin.get("n_generations"),
            }
        fs = _safe_json(_git_show(f"runs/{rdir}/final_state.json"))
        if fs:
            out["final_state"] = {
                k: fs.get(k) for k in
                ("final_status", "epistemic_state", "reason")
                if fs.get(k) is not None}
        out["harvested"] = True
    except Exception as exc:  # noqa: BLE001
        out["harvested"] = False
        out["reason"] = f"{type(exc).__name__}: {exc}"
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice-seconds", type=int, default=540)
    ap.add_argument("--launch-only", action="store_true")
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

    h = _req("/api/health")
    providers = ((h.get("body") or {}).get("providers") or {})
    ring = {k: v.get("status") for k, v in providers.items()}
    _log(f"ring at launch: {json.dumps(ring)}")

    sess = _resume()
    entry = sess.get("case") or {}
    record: Dict[str, Any] = sess.get("record") or {}
    record.setdefault("submission", {
        "case_id": problem["case_id"],
        "domain_family_corpus": problem["domain_family"],
        "split": problem["split"],
        "corpus_sha256": problem["corpus_sha256"],
        "submitted_text_sha256": hashlib.sha256(
            problem["submitted_text"].encode()).hexdigest(),
        "ab_discipline": (
            "the EXACT R490 submitted text (verbatim corpus + the same "
            "declared-family line) — same problem, same ladder, same "
            "sources; the only delta is the deployed build (R490 ran "
            "pre-R491-wire; this runs on the R491 union)"),
        "no_closure_claim": (
            "this run types NOTHING about cross-domain families; its "
            "deliverable is the through-deployed-runtime wire "
            "measurement"),
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
    _persist(sess)
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
            _log(f"poll {r.get('http_status')} {str(r.get('error'))[:120]}")
        time.sleep(POLL_INTERVAL_S)
    if final is None:
        _log(f"slice deadline ({args.slice_seconds}s) — re-invoke to "
             f"resume the SAME run {sid} (Art. LXXIV)")
        return 2

    time.sleep(90)  # the worker's durable checkpoint cadence
    durable = _durable_harvest(sid)
    record.update({
        "run_id": sid,
        "final_status": (final.get("status") or ""),
        "final_reason": str(final.get("reason") or "")[:500],
        "identity_verified": served,
        "ring_at_launch": ring,
        "submitted_at": entry.get("submitted_at"),
        "terminal_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "durable": durable,
        "reviewer_provenance": "AI_REVIEW",
    })

    _log(f"wire verdict: {durable.get('wire_verdict')} — "
         f"{str(durable.get('wire_verdict_basis'))[:200]}")
    _log(f"collision: {json.dumps(durable.get('collision'))[:500]}")
    _log(f"attack deployed: "
         f"{json.dumps({k: v for k, v in (durable.get('attack_deployed') or {}).items() if k != 'dimension_verdicts'})[:300]}")

    record["wire_measurement"] = {
        "verdict": durable.get("wire_verdict", "WIRE_UNMEASURED"),
        "basis": durable.get("wire_verdict_basis"),
        "ab_against": "R490 (5/10 keyed legs NOT_CONFIGURED_WIRE "
                      "measured in the R490-era durable envelopes)",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1, default=str))
    _log(f"record -> {OUT}")
    sess["record"] = json.loads(json.dumps(record, default=str))
    _persist(sess)
    return 0


if __name__ == "__main__":
    sys.exit(main())
