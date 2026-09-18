#!/usr/bin/env python3
"""scripts/r509_r370g_rehearsal.py — R509 parallel track 10 (coder
directive): the R370G door rehearsal — validate -> ingest -> ledger ->
decide -> learn, end-to-end, with a labeled rehearsal fixture.

REHEARSAL-ONLY (Art. XXXVIII): every fixture event carries
source_type=CONTROLLED_REHEARSAL; the ledger itself types these
reality_class=CONTROLLED_REHEARSAL and counts real_event_count=0; the
adjudicator's records carry counts_as_learning=false. NO REAL packet
exists (no survivor has ever reached a buyer ZIP) and nothing here
promotes anything — this proves the DOOR works, not that reality was
ingested. REAL_LOOP_VERIFIED stays 0 until a REAL packet flows.

Fixture honesty (Art. XXVII): the observation values are DERIVED from
the frozen P04 contract constants (imported, never retyped) so the
expected verdicts are derivable, not asserted.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import reality_ingestion as ri  # noqa: E402
from discovery_fabric.engine import causal_learning as cl    # noqa: E402

OUT = REPO / "R509" / "R370G_REHEARSAL.json"
LEDGER = REPO / "R509" / "r370g_rehearsal_ledger.json"

REHEARSAL_EVENT_BASE = {
    "experiment_id": "REHEARSAL-EXP-001",
    "package_id": "REHEARSAL-PKG-001",
    "apparatus_id": "REHEARSAL-APPARATUS (synthetic)",
    "operator": "REHEARSAL (R509 track 10)",
    "raw_data_hash": hashlib.sha256(b"rehearsal-raw").hexdigest(),
    "processed_data_hash": hashlib.sha256(b"rehearsal-processed").hexdigest(),
    "measurement_units": {"residual_floor_flow": "mL/min", "G_ratio": "ratio"},
    "uncertainty": {"flow": "+/-0.02 mL/min (rehearsal fixture)"},
    "source_type": "CONTROLLED_REHEARSAL",
    "organization": "REHEARSAL (no organization — synthetic fixture)",
    "custody_chain": [
        {"actor": "R509 rehearsal script", "action": "synthetic fixture generation (labeled, never promotable)"},
        {"actor": "R509 rehearsal script", "action": "ingestion through the R407-B validator into the rehearsal ledger"},
    ],
    "attestation": {
        "attestation_text": "REHEARSAL FIXTURE — synthetic values derived from the frozen P04 contract constants; not a physical observation.",
        "attestation_hash": hashlib.sha256(b"rehearsal-attestation").hexdigest(),
    },
    "provenance_validated": True,
    "baseline_result": {"note": "rehearsal baseline (synthetic)"},
    "pre_registered_threshold": {"note": "the frozen P04 contract constants (imported, not restated)"},
}


def candidate_result_for_keep() -> dict:
    """Values DERIVED from the frozen constants: flows above Q_MIN_PASS at
    the required number of heads, G_ratio inside the tolerance band,
    occlusion below the kill channel."""
    heads = [ri.P04_Q_MIN_PASS, ri.P04_Q_MIN_PASS + 0.05,
             ri.P04_Q_MIN_PASS + 0.10][: ri.P04_PASS_HEADS_REQUIRED] \
        if hasattr(ri, "P04_PASS_HEADS_REQUIRED") else \
        [ri.P04_Q_MIN_PASS, ri.P04_Q_MIN_PASS + 0.05]
    flows = {f"head_{i + 1}mmHg": round(v, 3) for i, v in enumerate(heads)}
    return {
        "residual_floor_flow_mL_min_by_head_mmHg": flows,
        "measured_G_ratio": ri.P04_G_RATIO_MODELLED,
        "common_cause_occlusion_rate_pct": 0.0,
        "void_trial_count": 0,
        "valid_trials_total": 6,
        "manufacturing_minwall_all_failed": False,
    }


def candidate_result_for_kill() -> dict:
    """Occlusion at/above the frozen common-cause kill channel."""
    return {
        "residual_floor_flow_mL_min_by_head_mmHg": {"head_1mmHg": 1.0},
        "measured_G_ratio": ri.P04_G_RATIO_MODELLED,
        "common_cause_occlusion_rate_pct": ri.P04_COMMON_CAUSE_KILL_PCT,
        "void_trial_count": 0,
        "valid_trials_total": 6,
        "manufacturing_minwall_all_failed": False,
    }


def main() -> int:
    rec: dict = {"artifact_type": "R509_R370G_DOOR_REHEARSAL",
                 "track": "10 — R370G door rehearsal (rehearsal-only, never promoting)",
                 "door": "validate -> ingest -> ledger -> decide -> learn",
                 "stages": {}}

    # -- 1. VALIDATE (accept path + reject path) --------------------------
    ev_keep = dict(copy.deepcopy(REHEARSAL_EVENT_BASE),
                   event_id="rehearsal-event-keep-001",
                   timestamp="2026-09-18T11:00:00Z",
                   candidate_result=candidate_result_for_keep(),
                   baseline_result={"residual_floor_flow": 0.0})
    ev_keep["decision"] = {"verdict": "KEEP", "basis": "rehearsal fixture"}
    problems_keep = ri.validate_reality_event_v2(ev_keep)
    rec["stages"]["validate"] = {
        "accept_case": {"violations": problems_keep, "valid": not problems_keep}}

    ev_kill = dict(copy.deepcopy(REHEARSAL_EVENT_BASE),
                   event_id="rehearsal-event-kill-001",
                   timestamp="2026-09-18T11:01:00Z",
                   candidate_result=candidate_result_for_kill())
    ev_kill["decision"] = {"verdict": "KILLED", "basis": "rehearsal fixture"}
    problems_kill = ri.validate_reality_event_v2(ev_kill)
    rec["stages"]["validate"]["kill_case"] = {
        "violations": problems_kill, "valid": not problems_kill}

    broken = copy.deepcopy(ev_keep)
    del broken["attestation"]
    problems_broken = ri.validate_reality_event_v2(broken)
    rec["stages"]["validate"]["reject_case"] = {
        "violations": problems_broken,
        "rejected": bool(problems_broken),
        "note": "a missing provenance field is rejected — no observation enters without provenance"}

    # -- 2/3. INGEST + LEDGER ---------------------------------------------
    if LEDGER.exists():
        LEDGER.unlink()  # fresh rehearsal ledger each run (never the real one)
    ing1 = ri.ingest_reality_event(ev_keep, str(LEDGER))
    ing2 = ri.ingest_reality_event(ev_kill, str(LEDGER))
    ing_dup = ri.ingest_reality_event(ev_keep, str(LEDGER))  # double entry
    ing_broken = ri.ingest_reality_event(broken, str(LEDGER))
    ver = ri.verify_ledger(str(LEDGER))
    ledger = json.loads(LEDGER.read_text())
    rec["stages"]["ingest_ledger"] = {
        "ingest_keep": ing1, "ingest_kill": ing2,
        "double_entry_rejected": ing_dup.get("ingested") is False,
        "broken_event_rejected": ing_broken.get("ingested") is False,
        "ledger_verify": ver,
        "entry_count": ledger.get("entry_count"),
        "real_event_count": ledger.get("real_event_count"),
        "reality_classes": [e.get("reality_class") for e in ledger.get("entries", [])],
        "note": "rehearsal ledger at R509/r370g_rehearsal_ledger.json — "
                "NOT the real ledger; real_event_count must be 0",
    }

    # ledger tamper detection (on a copy)
    tampered = copy.deepcopy(ledger)
    tampered["entries"][0]["record"]["operator"] = "TAMPERED"
    tmp = LEDGER.with_suffix(".tampered.json")
    tmp.write_text(json.dumps(tampered, indent=1))
    tamper_ver = ri.verify_ledger(str(tmp))
    tmp.unlink()
    rec["stages"]["ingest_ledger"]["tamper_detected"] = \
        tamper_ver.get("valid") is False

    # -- 4. DECIDE (the frozen contract, both channels) --------------------
    dec_keep = ri.decide_p04(ev_keep["candidate_result"])
    dec_kill = ri.decide_p04(ev_kill["candidate_result"])
    rec["stages"]["decide"] = {
        "keep_case": {"verdict": dec_keep.get("verdict"),
                      "rule_id": dec_keep.get("rule_id"),
                      "expected": "KEEP (fixture derived from the frozen ACCEPT constants)",
                      "match": dec_keep.get("verdict") == "KEEP"},
        "kill_case": {"verdict": dec_kill.get("verdict"),
                      "rule_id": dec_kill.get("rule_id"),
                      "expected": "KILL (occlusion at the frozen channel-a constant)",
                      "match": dec_kill.get("verdict") == "KILL"},
        "thresholds_imported_not_retyped": {
            "P04_Q_MIN_PASS": ri.P04_Q_MIN_PASS,
            "P04_Q_MIN_KILL": ri.P04_Q_MIN_KILL,
            "P04_COMMON_CAUSE_KILL_PCT": ri.P04_COMMON_CAUSE_KILL_PCT,
            "P04_G_RATIO_MODELLED": ri.P04_G_RATIO_MODELLED},
    }

    # -- 5. LEARN (adjudicate + summary + the bounded causal loop) ---------
    adj = ri.adjudicate_learning(
        prediction_before=1.0, actual_measurement=1.1, prediction_after=1.05,
        held_out={"actual": 1.2, "prediction_before": 1.0,
                  "prediction_after": 1.15},
        reality_event=ev_keep, unit="mL/min")
    summary = ri.learning_ledger_summary([adj])
    rec["stages"]["learn_adjudicate"] = {
        "adjudication": adj,
        "counts_as_learning": adj.get("counts_as_learning"),
        "note": "CONTROLLED_REHEARSAL inputs demonstrate the machinery but "
                "carry counts_as_learning=false — never the real count",
        "summary": summary,
    }

    loop_err = None
    try:
        loop = cl.run_causal_learning_loop(
            problem_text=(
                "REHEARSAL (R509 track 10, never promoting): a passive "
                "check-valve lumen must keep residual forward flow above "
                "0.4 mL/min across head pressures 1-10 mmHg while occluding "
                "under common-cause failure; parameters: lumen diameter, "
                "flap stiffness."),
            parent_candidate_id="rehearsal-candidate-001",
            candidate_parameters={
                "lumen_diameter_mm": {"value": 0.8, "unit": "mm"},
                "flap_stiffness_N_per_m": {"value": 12.0, "unit": "N/m"}},
            run_label="r509-r370g-rehearsal")
        rec["stages"]["learn_causal_loop"] = {
            "loop_id": loop.get("loop_id"),
            "stages": [s.get("stage") for s in loop.get("stages", [])],
            "verification_state": loop.get("verification_state"),
            "note": "bounded rehearsal loop — the learn leg of the door",
        }
    except Exception as e:  # noqa: BLE001 — recorded honestly, never hidden
        loop_err = f"{type(e).__name__}: {e}"[:300]
        rec["stages"]["learn_causal_loop"] = {"error": loop_err,
                                              "typed": "REHEARSAL_LOOP_ERROR"}

    # -- verdict ------------------------------------------------------------
    ok = (not problems_keep and not problems_kill and bool(problems_broken)
          and ing1.get("ingested") and ing2.get("ingested")
          and ing_dup.get("ingested") is False
          and ing_broken.get("ingested") is False
          and ver.get("valid") is True
          and ledger.get("real_event_count") == 0
          and rec["stages"]["ingest_ledger"]["tamper_detected"]
          and dec_keep.get("verdict") == "KEEP"
          and dec_kill.get("verdict") == "KILL"
          and adj.get("counts_as_learning") is False)
    rec["door_verdict"] = {
        "DOOR_PROVEN": ok,
        "basis": "validate accepts/rejects correctly; ingest double-entry + "
                 "broken-event guards hold; the hash-chained ledger verifies "
                 "and detects tampering; the frozen decision rule computes "
                 "both KEEP and KILL channels from imported constants; the "
                 "adjudicator demonstrates learning machinery with "
                 "counts_as_learning=false for rehearsal inputs",
        "never_promotes": "every fixture event is CONTROLLED_REHEARSAL; "
                          "real_event_count=0; REAL_LOOP_VERIFIED stays 0 "
                          "until a REAL packet flows (a survivor must exist "
                          "first)",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"DOOR_PROVEN={ok} | real_event_count={ledger.get('real_event_count')} "
          f"| keep={dec_keep.get('verdict')} kill={dec_kill.get('verdict')} "
          f"| counts_as_learning={adj.get('counts_as_learning')}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
