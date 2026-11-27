#!/usr/bin/env python3
"""r175_cmb_smoke.py — the WIRING smoke for the DIR-2 harness (claim
c-0276; prereg: 'a synthetic-problem wiring smoke precedes the run and
is excluded from the tally').

Runs ONE synthetic problem (NOT in eval/problems_dev12.json) through
every phase of scripts/r175_cmb_run.py with a REDUCED baseline budget
(N=2 draws — typed SMOKE_REDUCED_BUDGET; the smoke validates wiring,
never a measurement): pipeline -> baseline -> dominance -> one judge
leg per live seat. Writes eval/r175_cmb_smoke/ (never the measured
eval/r175_cmb_run/). Zero tally claims.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r175_cmb_run as R  # noqa: E402

SMOKE_OUT = REPO / "eval" / "r175_cmb_smoke"
SMOKE_OUT.mkdir(parents=True, exist_ok=True)
R.OUT = SMOKE_OUT
R.SCRATCH = REPO / "ENGINE_RUNS" / "r175_cmb_smoke"

SYNTH = {
    "problem_id": "r175-smoke-synthetic-01",
    "device": "lab-scale shell-and-tube heat exchanger",
    "failure": "mineral scale fouling on the tube-side wall raises "
               "thermal resistance until outlet temperature misses "
               "specification",
    "failure_mode": "fouling",
    "constraint": "no chemical cleaning agents permitted (food-grade "
                  "duty); downtime windows are 30 minutes per month",
    "domain": "thermal-fluid-process",
    "question_type": "intervention-proposal",
    "question": "What engineering change, intervention, or design "
                "would prevent or mitigate the stated failure under "
                "the stated constraint, and what concrete test would "
                "falsify the proposed approach?",
    "user_variables": [
        "tube-side velocity currently 0.6 m/s (laminar regime)",
        "outlet temperature spec 63.0 +/- 0.5 C",
        "downtime windows 30 minutes per month"],
    "clarification_answer": None,
    "split": "SMOKE",
}


def main() -> int:
    t0 = time.monotonic()
    rec = {"record": "R175_CMB_SMOKE/1.0.0", "pid": SYNTH["problem_id"],
           "budget": "SMOKE_REDUCED_BUDGET (N=2 draws; wiring only)",
           "phases": {}}

    # 1) seat probes (fail-closed info only; the panel needs >=2)
    try:
        probe = R.seat_probe()
        rec["phases"]["probe"] = {"ok": True,
                                  "live_families":
                                      probe.get("_live_families")}
    except Exception as e:  # noqa: BLE001
        rec["phases"]["probe"] = {"ok": False,
                                  "error": f"{type(e).__name__}: "
                                           f"{str(e)[:200]}"}

    # 2) pipeline (full EngineRun; the real budget shape)
    pipe = R.phase_pipeline(SYNTH)
    rec["phases"]["pipeline"] = {"state": pipe.get("state"),
                                 "K_i": pipe.get("K_i"),
                                 "final_status":
                                     pipe.get("final_status")}

    # 3) baseline, REDUCED N=2 (wiring only — never a measurement)
    if pipe.get("state") == "OK":
        pipe["K_i"] = 2  # typed smoke reduction
        base = R.phase_baseline(SYNTH, pipe)
        rec["phases"]["baseline"] = {
            "state": base.get("state"),
            "n_draws": base.get("N_draws"),
            "rule": base.get("selection_rule_applied"),
            "best_draw": base.get("baseline_best_draw"),
            "best_defects": base.get("baseline_best_defects")}

        # 4) dominance compose
        if base.get("state") == "OK":
            pair = R.phase_dominance(SYNTH, pipe, base)
            rec["phases"]["dominance"] = {
                "state": pair.get("state"),
                "composer_state": pair.get("composer_state"),
                "pool": pair.get("dominance_pool_ids"),
                "calls": pair.get("call_accounting")}
            rec["pipeline_answer_chars"] = len(
                pair.get("pipeline_answer") or "")
            rec["baseline_answer_chars"] = len(
                base.get("baseline_best") or "")

            # 5) one judge leg per live seat on the smoke pair
            amap = {"pairs": {SYNTH["problem_id"]:
                              {"A": "pipeline", "B": "baseline"}}}
            (SMOKE_OUT / "ab_map.json").write_text(
                json.dumps(amap, indent=1) + "\n", encoding="utf-8")
            probe = json.loads((SMOKE_OUT / "seat_probe.json")
                               .read_text(encoding="utf-8"))
            live = {t for t in R.SEATS
                    if probe.get(t, {}).get("live")}
            ce = json.loads(
                (R.SCRATCH / f"pipe_{SYNTH['problem_id']}"
                 / "candidate_envelope.json").read_text(
                    encoding="utf-8"))
            packet_text = R._packet_text(ce.get("evidence") or [])
            texts = {"pipeline": pair.get("pipeline_answer"),
                     "baseline": base.get("baseline_best")}
            judge = {}
            for tag in sorted(live):
                seat = R.SEATS[tag]
                prompt = R.JUDGE_TASK.format(
                    device=SYNTH["device"], failure=SYNTH["failure"],
                    failure_mode=SYNTH["failure_mode"],
                    constraint=SYNTH["constraint"],
                    packet_block=packet_text,
                    first_label="ANSWER A",
                    first_text=texts["pipeline"],
                    second_label="ANSWER B",
                    second_text=texts["baseline"])
                leg = R._seat_leg(seat, prompt)
                judge[tag] = {"outcome": leg["outcome"],
                              "verdict": leg["verdict"]}
                time.sleep(seat["pace"])
            rec["phases"]["judge"] = judge
    rec["wall_s"] = round(time.monotonic() - t0, 1)
    rec["verdict"] = ("WIRING_OK" if all([
        rec["phases"].get("pipeline", {}).get("state") == "OK",
        rec["phases"].get("baseline", {}).get("state") == "OK",
        rec["phases"].get("dominance", {}).get("state") == "OK",
        any(j.get("outcome") == "VALID"
            for j in rec["phases"].get("judge", {}).values())])
        else "WIRING_DEFECT")
    (SMOKE_OUT / "smoke.json").write_text(
        json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(json.dumps(rec, indent=1, ensure_ascii=False))
    return 0 if rec["verdict"] == "WIRING_OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
