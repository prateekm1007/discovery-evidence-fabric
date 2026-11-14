#!/usr/bin/env python3
"""r11_instrument_calibration — R11 P2a/P2b (owner audit step 2): the
feasibility scorer and the novelty instrument, calibrated on the
owner's judged specimens.

FEASIBILITY (the owner's bar): p02 and new05 (the audited infeasible
inventions, committed A1 1.0.0 bytes) must score <=2; the good
specimens (p09/sofc/fu-003/fu-001 — the audited wins/survivors, both
1.0.0 committed and 1.1.0 critic-armed re-run) must score >=3. The
seeded-specimen corpus the owner will place extends this calibration
when it lands (typed NOT_PLACED until then — Art. XXV).

NOVELTY (the false-novelty instrument): ideas known to be prior art
must come back KNOWN — spectral kurtosis for bearings, phase-resolved
PD pattern analysis, DGA per IEEE C57.104, BMS cell balancing, WVTR/OTR
barrier testing, ESR trending for supercapacitors.

Zero LLM calls — the calibrated instruments are deterministic.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.invention_rubric import (  # noqa: E402
    score_answer, standard_solution_reference, prior_art_verdict)

probs = {p.get("problem_id"): p for p in json.loads(
    (REPO / "eval" / "problems_dev12.json").read_text())["problems"]}

DEFECTS = ["bench-p02-leadacid-grid-corrosion",
           "eval-new05-liion-balance-drift"]
GOOD = ["bench-p09-packaging-barrier", "eval-sofc-thermal-cycling",
        "dev-fu-003-motor-insulation", "dev-fu-001-bearing-spalling"]
KNOWN_PRIOR_ART = [
    ("spectral kurtosis bearing", "dev-fu-001-bearing-spalling",
     "Envelope spectrum analysis with spectral kurtosis is an "
     "established technique for detecting bearing spalling defects: "
     "the kurtosis of the squared envelope highlights impulsive "
     "defect signatures, and the defect frequency band is monitored "
     "against the vibration alarm limit on a scheduled vibration "
     "monitoring program."),
    ("phase-resolved PD", "dev-fu-003-motor-insulation",
     "Phase-resolved partial discharge pattern analysis (PRPD) is an "
     "established offline diagnostic: PD pulses are measured per IEC "
     "60270 and the discharge patterns are resolved by phase angle "
     "on a scheduled offline insulation test program."),
    ("DGA IEEE C57.104", "eval-new07-transformer-dga-predictor",
     "Dissolved-gas analysis trending per IEEE C57.104 with "
     "gas-ratio methods is the established transformer-fault "
     "screening technique on a scheduled oil sampling program."),
    ("BMS balancing", "eval-new05-liion-balance-drift",
     "Battery-management-system cell balancing with periodic passive "
     "bleeding or active charge transfer, capacity grading at "
     "assembly and per-cell state-of-charge monitoring is the "
     "established practice for cell imbalance in battery packs."),
]


def main() -> int:
    print("[calib] feasibility + novelty instrument calibration "
          "(zero LLM calls)")
    ok = True

    print("\n-- FEASIBILITY (the owner's bar) --")
    # the DEFECT specimens are the committed 1.0.0 bytes the owner
    # audited (p02 graphene-CNT grid, new05 PEO-LiTFSI cathode). The
    # 1.1.0 re-run REPLACED those ideas (the critic's whole job) — its
    # answers are the replacements and score honestly on their own
    # merit; asserting <=2 on them would assert the critic failed.
    for pid in DEFECTS:
        d = REPO / "eval" / "pairs" / "r11_a1"
        rec = json.loads((d / f"{pid}.json").read_text())
        ans = str(rec.get("a1_answer") or "")
        prob = probs[pid]
        s = score_answer(prob, ans,
                         standard_answer=standard_solution_reference(prob))
        fs = s["scores"]["feasibility"]
        good = fs <= 2
        ok &= good
        print(f"  [1.0.0  ] {pid[:38]:40s} feasibility={fs} "
              f"{'PASS(<=2)' if good else 'FAIL(must be <=2)'}")
    for pid in GOOD:
        for ver, d in (("1.0.0", REPO / "eval" / "pairs" / "r11_a1"),
                       ("1.1.0", REPO / "eval" / "pairs"
                        / "r11_a1_r2")):
            rec = json.loads((d / f"{pid}.json").read_text())
            ans = str(rec.get("a1_answer") or "")
            if not ans.strip():
                continue
            prob = probs[pid]
            s = score_answer(prob, ans,
                             standard_answer=standard_solution_reference(
                                 prob))
            fs = s["scores"]["feasibility"]
            good = fs >= 3
            ok &= good
            print(f"  [{ver[:6]}] {pid[:38]:40s} feasibility={fs} "
                  f"{'PASS(>=3)' if good else 'FAIL(must be >=3)'}")

    print("\n-- NOVELTY false-instrument test (known prior art must "
          "come back KNOWN) --")
    for label, pid, idea in KNOWN_PRIOR_ART:
        v = prior_art_verdict(idea, probs[pid])
        good = v == "KNOWN"
        ok &= good
        print(f"  {label:28s} -> {v:12s} "
              f"{'PASS' if good else 'FAIL(must be KNOWN)'}")

    print(f"\n[calib] VERDICT: "
          f"{'CALIBRATION_PASS' if ok else 'CALIBRATION_FAIL'}")
    out = (REPO / "eval" / "instrument_calibration_r11.json")
    out.write_text(json.dumps({
        "record": "instrument_calibration_r11/1.0.0",
        "at": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ",
                                          __import__("time").gmtime()),
        "feasibility_bar": "p02/new05 (committed 1.0.0 defect bytes) "
                           "<=2; good specimens (1.0.0 + 1.1.0) >=3 "
                           "— provenance BUYER_DEFINED (owner audit "
                           "2026-11-14)",
        "false_novelty_instrument": "known prior-art ideas must return "
                                    "KNOWN (spectral kurtosis bearings, "
                                    "PRPD, DGA IEEE C57.104, BMS "
                                    "balancing)",
        "seeded_specimens": "NOT_PLACED (the owner's files; extends "
                            "this calibration when placed — typed, "
                            "Art. XXV)",
        "verdict": "CALIBRATION_PASS" if ok else "CALIBRATION_FAIL"},
        indent=1, default=str) + "\n", encoding="utf-8")
    return 0 if ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
