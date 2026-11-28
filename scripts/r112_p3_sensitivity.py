#!/usr/bin/env python3
"""r112_p3_sensitivity.py — the R112 direction 6: the P3 alarm-rule /
conformal-window sensitivity on the FULL-RESOLUTION channels, typed,
NO gate tuning (the committed protocol is unchanged; this table
informs the NEXT prereg, not the current gates).

Design (honest decomposition):
  - the SLIDING-WALK COVERAGE depends on the conformal window k (the
    K=100 sliding-quantile buffer) and the CONF, NOT on N_CONSEC —
    N_CONSEC shapes the ALARM RULE (the consecutive-breach streak);
  - so the sensitivity is measured along BOTH axes independently:
      k in {50, 100, 200} -> coverage + alarms (N_CONSEC=3 fixed);
      N_CONSEC in {1, 2, 3, 5} -> alarms (k=100 fixed);
  - the bearings: the seven protocol-floor-eligible channels
    (n >= 212, the committed CTX=96 floor) — the full-resolution
    length class the direction names (the walk windows are 10-20x
    longer than the sampled courses);
  - the arm: Bolt (the committed p3s2.BoltArm) — the fastest arm, the
    same arm the committed protocol rows used.
"""
import json
import sys
import time
from pathlib import Path

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

import numpy as np  # noqa: E402

s5 = json.loads((REPO / "eval" / "r111_p3_fullres_15bearings.json")
                .read_text())  # noqa: E402
_channels = json.loads((REPO / "eval" / "r111_p3_fullres_channels.json")
                       .read_text())["channels"]

import importlib.util  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


s5mod = _load("s5mod_r112", REPO / "scripts" / "r105s2_p3_stage5_xjtu.py")
p3s3 = s5mod.p3s3
p3s2 = s5mod.p3s2
OUT = REPO / "eval" / "r112_p3_sensitivity.json"

CONF, K, NCC = p3s3.CONF, p3s3.K_SLIDE, p3s3.N_CONSEC
BEARINGS = [b for b, v in s5["results"].items()
            if v["protocol_status"] == "typed_protocol_ran_as_committed"]


def main():
    arm = p3s2.BoltArm()
    table = {}
    for b in BEARINGS:
        ch = np.asarray(_channels[b]["rms"], dtype=np.float64)
        n = len(ch)
        row = {"n_points": n}
        # axis 1: the conformal window k (coverage + alarms)
        for k in (50, 100, 200):
            p3s3.K_SLIDE = k
            pair = s5mod.walk_pair(ch, arm, f"{b}/k{k}")
            row[f"k{k}"] = {
                "coverage": pair["sliding"]["coverage"],
                "alarms": pair["sliding"]["alarms"],
                "alarms_per_1000": pair["sliding"]["alarms_per_1000"],
                "static_coverage": pair["static"]["coverage"],
            }
        # axis 2: the alarm rule N_CONSEC (k=100; the coverage is
        # k-dependent only — recompute the alarms from the breaches
        # the sliding walk exposes: rerun the walk and re-derive the
        # alarm rule on the SAME breaches for N_CONSEC in {1, 2, 5}
        p3s3.K_SLIDE = K
        pair100 = s5mod.walk_pair(ch, arm, f"{b}/ncc")
        # the sliding walk exposes no breach list, so measure N_CONSEC
        # by re-running the walk with the rule varied in the module
        base_alarms = pair100["sliding"]["alarms"]
        ncc_axis = {"3": base_alarms}
        import p3s2 as _p2  # noqa: F401
        for ncc in (1, 2, 5):
            p3s3.N_CONSEC = ncc
            pr = s5mod.walk_pair(ch, arm, f"{b}/ncc{ncc}")
            ncc_axis[str(ncc)] = pr["sliding"]["alarms"]
        p3s3.N_CONSEC = NCC
        row["n_consec_axis_alarms_k100"] = ncc_axis
        table[b] = row
        print(f"[{b}] n={n} k50 cov {row['k50']['coverage']} "
              f"k100 cov {row['k100']['coverage']} k200 cov "
              f"{row['k200']['coverage']} | alarms ncc "
              f"{ncc_axis}", flush=True)
    # restore the module constants (the committed protocol untouched)
    p3s3.K_SLIDE, p3s3.N_CONSEC = K, NCC
    rec = {
        "record": "R112_P3_SENSITIVITY/1.0.0",
        "at": "2026-11-20T16:20:00Z (sandbox clock, TRUE UTC)",
        "executor": "builder-r111s1",
        "direction": "the R112 direction 6 (typed sensitivity, NO gate "
                     "tuning — the committed protocol constants are "
                     "restored and unchanged)",
        "arm": "chronos-bolt-base (the committed p3s2.BoltArm)",
        "bearings": BEARINGS,
        "axes": {
            "k_conformal_window": [50, 100, 200],
            "n_consec_alarm_rule": [1, 2, 3, 5],
        },
        "per_bearing": table,
        "no_acceptance_claims": True,
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
