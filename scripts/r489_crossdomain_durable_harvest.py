#!/usr/bin/env python3
"""scripts/r489_crossdomain_durable_harvest.py — R489: harvest the
cross-domain run ts_f0880e025e60 from the DURABLE branch and type the
proof outcome with the COMMITTED R487 logic.

Why a separate script (disclosed in R489/R489_ROUND_RECORD.json):
the committed driver (r487_live_proof_crossdomain.py) resumes via its
local session file (run_id + owner capability). That file was lost
with the parallel session's container (BS-021: the capability never
lands in git — by design there is no recoverable copy). The run API
is owner-gated (enumeration-safe 404 without the capability), so the
result-API step of the committed flow is UNAVAILABLE to this observer.

The DURABLE BRANCH is the authority (the R481 lesson) and it is
git-authenticated (the PAT suffices). This harvest matches the run
dir by SESSION ID VERIFICATION — every EVENT_JOURNAL row must carry
run_id == ts_f0880e025e60 (never a slug heuristic) — then reads the
SAME fields the committed _durable_harvest reads (envelope_SYNTHESIZE,
envelope_VERIFY, envelope_IMPROVE stage_log, final_state.json,
problem.json) plus the attack/survivor-gate artifacts this run
produced, and applies the COMMITTED outcome-typing conditions verbatim:

  LOOP_CLOSED_ADMITTED / LOOP_CLOSED_REKILLED / NO_KILL_EVIDENCE /
  IMPROVE_ABSENT / DURABLE_HARVEST_PENDING / STAGE_*

Observation failure is never a run verdict (Art. LXXIV).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

SESSION_ID = "ts_f0880e025e60"
BRANCH = "origin/runtime-state-hf"
OUT = REPO / "R487" / "LIVE_PROOF_CROSSDOMAIN.json"
R489 = REPO / "R489"

SLUG = "runs/toscanini_ui_ui_flat_faced_cam_follower_rolling_contact_fa_636438"


def _git_show(path: str) -> str:
    return subprocess.run(
        ["git", "show", f"{BRANCH}:{path}"],
        cwd=str(REPO), capture_output=True, text=True,
        timeout=60).stdout


def _j(path: str):
    raw = _git_show(path)
    if not raw.strip():
        return None
    try:
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        return None


def _log(m):
    print(f"[r489-harvest] {m}", flush=True)


def main() -> int:
    # refresh the durable branch
    subprocess.run(
        ["git", "fetch", "origin", "runtime-state-hf"],
        cwd=str(REPO), capture_output=True, timeout=120)

    # SESSION-ID VERIFIED match (never a slug heuristic)
    # the journal is JSONL — parse per line, never as one document
    journal_raw = _git_show(f"{SLUG}/EVENT_JOURNAL.jsonl")
    rows = []
    for line in (journal_raw or "").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except Exception:  # noqa: BLE001
                pass
    n_match = sum(1 for r in rows
                  if r.get("run_id") == SESSION_ID)
    if not rows or n_match != len(rows):
        _log(f"FATAL: session verification failed "
             f"({n_match}/{len(rows)} journal rows carry {SESSION_ID})")
        return 2
    _log(f"session verified: {n_match}/{len(rows)} journal rows carry "
         f"{SESSION_ID}")

    stages = [(r.get("seq"), r.get("kind"), r.get("status"),
               (r.get("timestamp") or "")[11:19]) for r in rows]

    # --- the committed harvest's field extraction, verbatim ---
    out: dict = {}

    raw = _git_show(f"{SLUG}/envelope_SYNTHESIZE.json")
    if raw.strip():
        d = json.loads(raw)
        rc = ((d.get("mechanism_map") or {}).get("raw_candidate") or {})
        se = rc.get("source_evidence") or {}
        out["synthesis_route"] = {
            "provider": rc.get("provider"), "model": rc.get("model"),
            "source_id": se.get("source_id"),
            "source_span_chars": len(se.get("source_span") or "")}

    raw = _git_show(f"{SLUG}/envelope_VERIFY.json")
    if raw.strip():
        ev = ((json.loads(raw).get("adjudication") or {})
              .get("evidence_verification") or {})
        out["verify"] = {"verified": ev.get("verified"),
                         "issues": ev.get("issues")}

    imp_raw = _git_show(f"{SLUG}/envelope_IMPROVE.json")
    improve_entries = []
    mechanism_space = None
    attack_record = None
    if imp_raw.strip():
        d = json.loads(imp_raw)
        sl = d.get("stage_log") or []
        out["improve_entries"] = [
            {k: e.get(k) for k in
             ("stage", "status", "result_meta", "before_envelope_hash",
              "after_envelope_hash", "candidate_delta", "delta_real",
              "started_at", "finished_at")}
            for e in sl if e.get("stage") == "IMPROVE"]
        for e in sl:
            if e.get("stage") == "MECHANISM_SPACE":
                mechanism_space = e.get("result_meta")
            if e.get("stage") == "ATTACK":
                attack_record = e.get("result_meta")

    fs = _j(f"{SLUG}/final_state.json") or {}
    out["final_state"] = {
        k: fs.get(k) for k in
        ("final_status", "epistemic_state", "reason",
         "evidence_verified", "premise_verdict")}
    # the collision execution facts are recorded on the terminal state
    # (the R394 s2 rule text: provider failure never becomes absence)
    cse = fs.get("collision_search_execution") or {}
    out["collision_execution"] = {
        "mandatory_complete": cse.get("mandatory_complete"),
        "n_errors": cse.get("n_errors"),
        "rule": str(cse.get("rule") or "")[:220]}

    pj = _j(f"{SLUG}/problem.json") or {}
    fam = pj.get("canonical_family") or pj.get("domain")
    out["problem_declared_family"] = (
        fam if isinstance(fam, str) else "ABSENT_IN_DURABLE_RECORD")

    sg = _j(f"{SLUG}/SURVIVOR_GATE.json") or {}
    out["survivor_gate"] = {
        "final_status": sg.get("final_status"),
        "resolution": str(sg.get("resolution") or "")[:300]}

    # this run's additional durable artifacts (byte-sourced)
    ar = _j(f"{SLUG}/envelope_ATTACK.json") or {}
    arr = ar.get("attack_results") or {}
    out["attack_stage"] = {
        "overall": arr.get("overall"),
        "killed_count": arr.get("killed_count"),
        "dimensions": arr.get("attacks"),
        "v4_corrections_applied": arr.get("v4_corrections_applied"),
        "transport": {k: (arr.get("transport") or {}).get(k)
                      for k in ("provider", "model", "substituted_from",
                                "status", "latency_ms")},
        "stage_result_meta": attack_record}
    out["mechanism_space"] = mechanism_space
    out["stage_journal"] = stages

    # --- the COMMITTED outcome-typing conditions, verbatim ---
    record: dict = {}
    imp = out.get("improve_entries") or []
    statuses = [((e.get("result_meta") or {}).get("status")
                 or e.get("status")) for e in imp]
    if any(s == "CHILDREN_ADMITTED" for s in statuses if s):
        record["proof_outcome"] = "LOOP_CLOSED_ADMITTED"
    elif any(s == "NO_CHILD_ADMITTED" for s in statuses if s):
        record["proof_outcome"] = "LOOP_CLOSED_REKILLED"
    elif any(s == "NO_KILL_EVIDENCE" for s in statuses if s):
        record["proof_outcome"] = "NO_KILL_EVIDENCE"
    elif out.get("harvested") and not imp:
        record["proof_outcome"] = "IMPROVE_ABSENT"
    elif not imp:
        record["proof_outcome"] = "DURABLE_HARVEST_PENDING"
    else:
        record["proof_outcome"] = "STAGE_" + "_".join(
            str(s) for s in statuses if s)[:60]

    # the cross-domain comparison, REPORTED not asserted (committed text)
    run_family = out.get("problem_declared_family")
    record["cross_domain_comparison"] = {
        "corpus_declared_family": "mechanical",
        "run_declared_family": run_family,
        "prior_closure_families": "thermal/fluid (geothermal scaling)",
        "verdict": (
            "CROSS_DOMAIN_REPEATED" if (
                record["proof_outcome"] == "LOOP_CLOSED_ADMITTED"
                and run_family == "mechanical")
            else "NOT_CROSS_DOMAIN_CLOSURE — the typed outcome above "
                 "and the run's own declared family are the record")}

    record.update({
        "artifact_type": "R487_LIVE_PROOF_CROSSDOMAIN",
        "harvest_method": ("durable-branch git harvest, session-id "
                           "verified (every journal row carries "
                           f"{SESSION_ID}); the owner capability was "
                           "lost with the parallel session's container "
                           "(BS-021: no recoverable copy by design); "
                           "the committed driver's result-API step is "
                           "owner-gated and unavailable — the durable "
                           "branch is the authority (the R481 lesson)"),
        "session_id": SESSION_ID,
        "harvested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                      time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "durable": out,
    })

    R489.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1, default=str))
    (R489 / "CROSSDOMAIN_DURABLE_HARVEST.json").write_text(
        json.dumps(record, indent=1, default=str))
    _log(f"outcome: {record['proof_outcome']}")
    _log(f"comparison: {record['cross_domain_comparison']['verdict']}")
    _log(f"final_status: {out['final_state'].get('final_status')} | "
         f"reason: {str(out['final_state'].get('reason'))[:120]}")
    _log(f"written -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
