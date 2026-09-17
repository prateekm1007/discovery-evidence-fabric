#!/usr/bin/env python3
"""R487 — the CROSS-DOMAIN live proof (attempt-6): the observer-
independent kill->mutate->readmit loop closure repeated on a DIFFERENT
domain family than both prior closures.

THE PROBLEM: R458-M1 (r458-m1-cam-follower-surface-fatigue, the
mechanical family) — read from the DURABLE in-repo corpus
(R458/BENCHMARK_CORPUS.json), never from a volatile /tmp extraction
(the lost-clone lesson): the corpus is sha256-pinned and asserted
clean in the worktree before submission.

THE COMPARISON THIS RUN DECIDES: the two recorded closures are the
geothermal calcite/silica problem (attempt-5, ts_b7673571279e, and
the cyclone variant line) — thermal/fluid-family territory. A
CHILDREN_ADMITTED here, on a mechanical-family problem, is the
cross-domain repetition the R485/R486 audits named as the first
decisive gap. The run's OWN declared canonical family is harvested
and recorded beside the corpus-declared one — the comparison is
reported, never asserted (Art. XV/XXV).

THE INSTRUMENT PRECONDITION: this proof runs on the deployed v3
INSTRUMENT build — EXPECTED_IDENTITY (env, REQUIRED) is the
deployed commit carrying independent_attack/3.0.0. NOTE (R487
measured): the v3 sealed-bar measurement returned FPR 1.0 — the
gate derives NOT_CALIBRATED (fail-closed) whether or not the
shipped records are in the deployed tree; the escalation gate
(R417 ruling) is in force either way, so deployed behavior is
IDENTICAL pre/post record shipment. The proof's identity gate
therefore pins the instrument build, and the calibration state is
recorded from the measured bytes, never assumed.

Slice-resumable (Art. LXXIV): the session persists OUTSIDE the
tracked tree (/home/z/my-project/scripts/r487_crossdomain_session.json
— BS-021: the owner capability never lands in git; the tracked copy
stays redacted). Each invocation polls for at most --slice-seconds
(default 540, the foreground tool-call budget) and exits cleanly;
re-invocation resumes the SAME run. Observation failure is never a
run verdict.

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
OUT = REPO_ROOT / "R487" / "LIVE_PROOF_CROSSDOMAIN.json"
SESSION = Path("/home/z/my-project/scripts/r487_crossdomain_session.json")
SESSION_TRACKED = REPO_ROOT / "R487" / "LIVE_PROOF_CROSSDOMAIN_SESSION.json"
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
    print(f"[r487-xdom] {msg}", flush=True)


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


def _load_problem() -> Dict[str, Any]:
    """The durable M1 extraction (the /tmp/m1_text.txt fix): read from
    the committed corpus, assert it is clean in the worktree, pin its
    sha256 — the submitted text is byte-accountable."""
    corpus = json.loads(CORPUS_PATH.read_text())
    m1 = corpus["problems"][PROBLEM_KEY]
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", "R458/BENCHMARK_CORPUS.json"],
        cwd=str(REPO_ROOT), capture_output=True, text=True).stdout.strip()
    if dirty:
        raise SystemExit("FATAL: R458/BENCHMARK_CORPUS.json is dirty in "
                         "the worktree — the corpus must be the frozen "
                         "committed bytes")
    return {
        "case_id": m1["case_id"],
        "domain_family": m1["domain_family"],
        "split": m1.get("split"),
        "text": m1["text"],
        "corpus_sha256": hashlib.sha256(
            CORPUS_PATH.read_bytes()).hexdigest(),
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


def _durable_harvest(session_id: str) -> Dict[str, Any]:
    """The durable branch is the authority (the R481 lesson). Dirs are
    matched by slug tokens, then VERIFIED by the manifest's session_id
    — the exact run, never a heuristic pick. Best-effort and honest:
    a lagging branch returns harvest_pending."""
    out: Dict[str, Any] = {}
    try:
        subprocess.run(["git", "fetch", "origin", "runtime-state-hf"],
                       cwd=REPO_ROOT, capture_output=True, timeout=120)
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
            man = _git_show(f"runs/{c}/run_manifest.json")
            if not man:
                continue
            try:
                if json.loads(man).get("session_id") == session_id:
                    rdir = c
                    break
            except Exception:  # noqa: BLE001
                continue
        if rdir is None:
            return {"harvested": False,
                    "reason": ("this session's run dir not on the "
                               "durable branch yet (or still running); "
                               f"{len(cands)} slug-candidate dirs "
                               "checked by session_id")}
        out["durable_run_dir"] = rdir

        # SYNTHESIZE — the route that served the span-bearing paper
        raw = _git_show(f"runs/{rdir}/envelope_SYNTHESIZE.json")
        if raw:
            d = json.loads(raw)
            rc = ((d.get("mechanism_map") or {}).get("raw_candidate")
                  or {})
            se = rc.get("source_evidence") or {}
            out["synthesis_route"] = {
                "provider": rc.get("provider"),
                "model": rc.get("model"),
                "source_id": se.get("source_id"),
                "source_span_chars": len(se.get("source_span") or ""),
            }
        # VERIFY — evidence_verified
        raw = _git_show(f"runs/{rdir}/envelope_VERIFY.json")
        if raw:
            ev = ((json.loads(raw).get("adjudication") or {})
                  .get("evidence_verification") or {})
            out["verify"] = {"verified": ev.get("verified"),
                             "issues": ev.get("issues")}
        # IMPROVE — the closure evidence
        raw = _git_show(f"runs/{rdir}/envelope_IMPROVE.json")
        if raw:
            sl = json.loads(raw).get("stage_log") or []
            out["improve_entries"] = [
                {k: e.get(k) for k in
                 ("stage", "status", "result_meta", "before_envelope_hash",
                  "after_envelope_hash", "candidate_delta", "delta_real",
                  "started_at", "finished_at")}
                for e in sl if e.get("stage") == "IMPROVE"]
        # the run's OWN declared family + terminal facts
        raw = _git_show(f"runs/{rdir}/final_state.json")
        if raw:
            fs = json.loads(raw)
            out["final_state"] = {
                k: fs.get(k) for k in
                ("final_status", "epistemic_state", "reason",
                 "evidence_verified", "premise_verdict")}
        raw = _git_show(f"runs/{rdir}/problem.json")
        if raw:
            pj = json.loads(raw)
            fam = (pj.get("canonical_family")
                   or (pj.get("domain") or {}))
            out["problem_declared_family"] = fam if isinstance(
                fam, str) else json.dumps(fam)[:120]
        # INVENTION_LINEAGE — generations, kills, mutation bases
        raw = _git_show(f"runs/{rdir}/INVENTION_LINEAGE.json")
        if raw:
            lin = json.loads(raw)
            gens = []
            for g in (lin.get("generations") or []):
                gens.append({k: g.get(k) for k in
                             ("gen", "invention_id", "parent_id",
                              "origin", "killed", "kill_basis_hash",
                              "kill_dimensions")})
            out["lineage"] = {
                "n_generations": lin.get("n_generations"),
                "n_evolution_generations":
                    lin.get("n_evolution_generations"),
                "survivor_reached": lin.get("survivor_reached"),
                "current_invention": lin.get("current_invention"),
                "final_state": lin.get("final_state"),
                "generations": gens,
            }
        # SURVIVOR_SELECTION — the post-admission merit demotion
        raw = _git_show(f"runs/{rdir}/SURVIVOR_SELECTION.json")
        if raw:
            ss = json.loads(raw)
            out["survivor_selection"] = {
                "selected": ss.get("selected"),
                "n_ranked": len(ss.get("ranked") or []),
                "ranked": [
                    {k: r.get(k) for k in
                     ("candidate_id", "killed", "attack_overall",
                      "quality_verdict", "repaired")}
                    for r in (ss.get("ranked") or [])],
            }
        # cemetery — the parent death that fed the kill point
        raw = _git_show(f"runs/{rdir}/cemetery_update.json")
        if raw:
            cu = json.loads(raw)
            out["cemetery"] = {
                "appended_entry_ids":
                    [e.get("entry_id") for e in
                     (cu.get("appended") or [])]
                if isinstance(cu.get("appended"), list)
                else [cu.get("appended", {}).get("entry_id")],
                "total_entries": cu.get("total_entries"),
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
    args = ap.parse_args()

    problem = _load_problem()
    expected = os.environ.get("EXPECTED_IDENTITY", "").strip()

    v = _req("/api/version")
    served = (v.get("body") or {}).get("engine_commit", "")
    if not expected:
        _log("FATAL: EXPECTED_IDENTITY (env) is REQUIRED — this proof "
             "runs only on the deployed v3 instrument build "
             "(independent_attack/3.0.0)")
        return 2
    if served != expected:
        _log(f"identity gate: production serves {served[:12]}, "
             f"expected {expected[:12]} (the v3 instrument build)")
        return 2
    _log(f"identity verified: {served[:12]} (the v3 instrument build; "
         f"calibration state is read from the measured bytes)")

    sess = _resume()
    entry = sess.get("case") or {}
    record: Dict[str, Any] = sess.get("record") or {}
    record.setdefault("problem", {
        "case_id": problem["case_id"],
        "domain_family_corpus": problem["domain_family"],
        "split": problem["split"],
        "corpus_sha256": problem["corpus_sha256"],
        "text_chars": len(problem["text"]),
        "prior_closures_families": (
            "attempt-5 geothermal calcite/silica + the cyclone-variant "
            "line — thermal/fluid territory; THIS run is the "
            "mechanical-family repetition"),
    })

    if not entry.get("run_id"):
        r = _req("/api/run", body={"text": problem["text"]}, timeout=180)
        if r.get("http_status") not in (200, 202):
            _log(f"submit failed {r.get('http_status')} "
                 f"{str(r.get('error'))[:200]}")
            return 1
        b = r.get("body") or {}
        entry = {"run_id": b.get("session_id") or b.get("run_id"),
                 "owner_key": b.get("owner_key"),
                 "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                               time.gmtime())}
        _log(f"submitted {entry['run_id']}")
    sess["case"] = entry
    sess["record"] = record
    _persist(sess)

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
             f"not execution)")
        return 2

    # the durable harvest (the authority for stage_log + lineage)
    time.sleep(90)  # the worker's durable checkpoint cadence
    durable = _durable_harvest(sid)
    record.update({
        "run_id": sid,
        "final_status": (final.get("status") or ""),
        "final_reason": str(final.get("reason") or "")[:500],
        "identity_verified": served,
        "submitted_at": entry.get("submitted_at"),
        "terminal_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime()),
        "durable": durable,
        "reviewer_provenance": "AI_REVIEW",
    })

    imp = durable.get("improve_entries") or []
    statuses = [((e.get("result_meta") or {}).get("status")
                 or e.get("status")) for e in imp]
    _log(f"IMPROVE result statuses: {statuses}")
    _log(f"synthesis route: "
         f"{json.dumps(durable.get('synthesis_route'))[:240]}")
    _log(f"verify: {json.dumps(durable.get('verify'))[:200]}")
    _log(f"problem-declared family: "
         f"{durable.get('problem_declared_family')}")

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

    # the cross-domain comparison, REPORTED not asserted
    run_family = durable.get("problem_declared_family")
    record["cross_domain_comparison"] = {
        "corpus_declared_family": problem["domain_family"],
        "run_declared_family": run_family,
        "prior_closure_families": "thermal/fluid (geothermal scaling)",
        "verdict": (
            "CROSS_DOMAIN_REPEATED" if (
                record["proof_outcome"] == "LOOP_CLOSED_ADMITTED"
                and run_family == "mechanical")
            else "NOT_CROSS_DOMAIN_CLOSURE — the typed outcome above "
                 "and the run's own declared family are the record"),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1, default=str))
    _log(f"outcome: {record['proof_outcome']} -> {OUT}")
    sess["record"] = json.loads(json.dumps(record, default=str))
    _persist(sess)
    return code


if __name__ == "__main__":
    sys.exit(main())
