#!/usr/bin/env python3
"""r112_d5_sensitivity_recompute.py — completes claim c-0155
(r112-d5-sensitivity-recompute, measurement; the R112 direction 7:
verify the peer's 6-bearing recompute from the REPAIRED HF bytes
landed — it had not, this window completes it under the auditor's
explicit takeover authorization, the takeover typed in the claim).

PURE RECOMPUTE from committed bytes (Art. 29(c)): the repaired-byte
channels are the R111 streaming checkpoint (eval/
r111_p3_fullres_channels.json — every file sha256-checked against the
committed manifest, i.e. the POST-repair bytes); the baseline is the
committed Dir-5 record (eval/r110_d5_xjtu_six_bearings.json, computed
from the PRE-repair zip spans). Per bearing:
  - the RMS delta table (first5/last5 minute deltas, max abs delta);
  - BOTH ratio formulas per bearing (the canonical mean-of-5 per the
    c-0156 unify + the endpoint legacy form, distinct field names);
  - the walk-pair coverage deltas (bolt sliding/static vs the Dir-5
    record's committed values);
  - the coverage-decision stability (no decision flips expected —
    verified, never assumed).
"""
import json
from pathlib import Path

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
BASE = json.loads((REPO / "eval" / "r110_d5_xjtu_six_bearings.json")
                  .read_text())
REPAIRED = json.loads((REPO / "eval" / "r111_p3_fullres_channels.json")
                      .read_text())["channels"]
FULLRES = json.loads((REPO / "eval" / "r111_p3_fullres_15bearings.json")
                     .read_text())["results"]
OUT = REPO / "eval" / "r112_d5_sensitivity_recompute.json"


def ratio_mean_of_5(ch):
    return round(float(ch[-5:].mean() / ch[:5].mean()), 4)


def main():
    table = {}
    flips = []
    for b, base in BASE["results"].items():
        ch = REPAIRED[b]["rms"]
        import numpy as np
        ch = np.asarray(ch, dtype=np.float64)
        # the minute-indexed RMS deltas vs the committed baseline
        first5_d = [round(a - c, 6) for a, c in
                    zip(ch[:5].tolist(), base["rms_first5"])]
        last5_d = [round(a - c, 6) for a, c in
                   zip(ch[-5:].tolist(), base["rms_last5"])]
        max_abs = round(max(max(abs(x) for x in first5_d),
                            max(abs(x) for x in last5_d)), 6)
        r_canon = ratio_mean_of_5(ch)
        r_legacy = round(float(ch[-1] / ch[0]), 4)
        # the walk-pair deltas (bolt, the same committed protocol)
        mine = FULLRES[b]["bolt"]
        base_slide = base["sliding"]["coverage"]
        base_static = base["static"]["coverage"]
        d_slide = round(mine["sliding"]["coverage"] - base_slide, 4)
        d_static = round(mine["static"]["coverage"] - base_static, 4)
        # coverage-decision stability: the >=0.90 bar decision AND the
        # alarm verdict direction (alarms fired vs not) must not flip
        decision_base = base_slide >= 0.90
        decision_mine = mine["sliding"]["coverage"] >= 0.90
        alarm_base = base["sliding"]["alarms"] > 0
        alarm_mine = mine["sliding"]["alarms"] > 0
        stable = (decision_base == decision_mine
                  and alarm_base == alarm_mine)
        if not stable:
            flips.append(b)
        table[b] = {
            "n_points": {"baseline": base["n_points"],
                         "repaired": len(ch)},
            "rows_per_file_range": {
                "baseline": [base["rows_per_file_min"],
                             base["rows_per_file_max"]],
                "repaired": [REPAIRED[b]["rows_min"],
                             REPAIRED[b]["rows_max"]]},
            "rms_delta_first5": first5_d,
            "rms_delta_last5": last5_d,
            "max_abs_rms_delta": max_abs,
            "rms_last_over_first_ratio": r_canon,
            "rms_last_over_first_ratio_endpoint_legacy": r_legacy,
            "sliding_coverage": {
                "baseline": base_slide,
                "repaired": mine["sliding"]["coverage"],
                "delta": d_slide},
            "static_coverage": {
                "baseline": base_static,
                "repaired": mine["static"]["coverage"],
                "delta": d_static},
            "coverage_decision_stable": stable,
        }
    rec = {
        "record": "R112_D5_SENSITIVITY_RECOMPUTE/1.0.0",
        "at": "2026-11-20T15:25:00Z (sandbox clock, TRUE UTC)",
        "executor": "builder-r111s1 (completing the peer's claim "
                    "c-0155 under the auditor R112 direction 7 "
                    "authorization; the takeover typed in the claim)",
        "claim": "c-0155 (legacy alias c-155; "
                 "r112-d5-sensitivity-recompute, measurement)",
        "recompute_only": True,
        "repaired_bytes_provenance": (
            "the R111 streaming checkpoint: every file sha256-checked "
            "vs the committed manifest (the post-repair bytes); the "
            "37 repaired files were all Bearing3_1 (the R110 verdict)"),
        "baseline": "eval/r110_d5_xjtu_six_bearings.json (the "
                    "pre-repair zip-span computation)",
        "per_bearing": table,
        "coverage_decision_stable_all": not flips,
        "coverage_decision_flips": flips,
        "note": ("the full-resolution walk coverages differ from the "
                 "Dir-5 baseline where the ADAPTED-CTX legs apply "
                 "(the r111 run adapts CTX for the sub-212 channels "
                 "exactly as the committed disclosure; the Dir-5 "
                 "record's own adaptation is carried in its "
                 "protocol_adaptation field) — the deltas are typed "
                 "per bearing, not tuned"),
        "no_acceptance_claims": True,
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    for b, v in table.items():
        print(f"{b}: max_abs_rms_delta={v['max_abs_rms_delta']} "
              f"slide {v['sliding_coverage']['baseline']} -> "
              f"{v['sliding_coverage']['repaired']} (d "
              f"{v['sliding_coverage']['delta']}) stable="
              f"{v['coverage_decision_stable']}")
    print("decision flips:", flips or "none")


if __name__ == "__main__":
    main()
