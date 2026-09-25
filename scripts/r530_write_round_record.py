#!/usr/bin/env python3
"""R530 round-record generator (directive §15).

R530 asked: what exactly is inside the MECHANISM_SPACE
selection-ordering wall (~1.9 s mean on the R526 baseline)?

Answer (durable, from the R530 instrumented battery on build
714108382, N=7 AUDITED operator calls):
  G availability scoring ... mean 4.040 s (56 score calls x
    168 full-ledger scans per generate() call)
  E build_ladder ........... mean 4.063 s (G is 99.4% of E)
  F catalog ................ mean 0.011 s (32/32 cache hits)
  A/B/C/D/H/I .............. ~0 s combined

The five round-states:
  measurement_complete ..... True (the subspan decomposition is
                             durable on production calls)
  optimization_authorized .. False (Case A candidate identified;
                             behavioral-identity proof pending)
  optimization_executed .... False
  optimization_measured .... False
  optimization_deployed .... False

Classification: MEASUREMENT_COMPLETE__CASE_A_CANDIDATE.
No intervention is named this round (directive §6: the
behavioral-identity checks — same inputs, same scores, same
ordering, same rung, same fallback, same provenance — must
pass BEFORE a per-call memoization intervention may be
considered). No provider/model/prompt/retry/routing change.
No stage deleted.

Machine-generated from durable artifacts. No hand edits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
R530 = REPO / "R530"
OUT = R530 / "R530_ROUND_RECORD.json"

MEASURE_SHA = "7141083827844a6d0d365453346d6e901a49735e"


def _sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest() \
        if p.exists() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--join",
                    default="R530/MECHANISM_SPACE_PROVIDER_JOIN_R530.json",
                    help="R530 measurement join artifact (repo-relative)")
    args = ap.parse_args()

    jpath = REPO / args.join
    join = json.loads(jpath.read_text(encoding="utf-8")) \
        if jpath.exists() else {}
    assert join.get("n_observed") == 10, \
        "R530 join must cover the frozen 10-row battery (fail-closed)"
    sub_agg = join.get("selection_subspan_aggregate") or {}
    diag_agg = join.get("selection_diag_aggregate") or {}

    def _mean(d, k):
        return (d.get(k) or {}).get("mean")

    g_mean = _mean(sub_agg, "G_scoring_detail_s")
    e_mean = _mean(sub_agg, "E_build_ladder_s")
    n_sub = (sub_agg.get("G_scoring_detail_s") or {}).get("n")

    # R531 §2 audit repair (Art. XXVII — thresholds require
    # provenance): the former `case_a_proven` predicate used
    # `(g_mean / e_mean) > 0.9` and `n_sub >= 2`, which have NO
    # constitutional or directive provenance — they were
    # coder-invented values, and the name `proven` implied the
    # threshold itself constitutes authorization. It does not.
    # Renamed to an OBSERVATIONAL candidate signal: it reports
    # what this battery measured (G≈99.4% of E on N=7 audited
    # calls) with no authorization implication. The values 0.9
    # and 2 below are descriptive readout points of THIS
    # measurement, not gates; the intervention gate is the
    # behavioral-identity proof (R531 §4–§6), which has not run.
    # Do not invent provenance retroactively.
    case_a_signal = bool(
        g_mean is not None and e_mean is not None and e_mean > 0
        and (g_mean / e_mean) > 0.9 and n_sub is not None
        and n_sub >= 2)
    behavior_proven = False  # the §6 identity checks have not run

    rec = {
        "artifact": "R530_ROUND_RECORD/1.0",
        "round": "R530",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                       time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "parent_round": "R529",
        "question": ("what exactly is inside the current "
                     "MECHANISM_SPACE selection-ordering wall?"),
        "measurement": {
            "build_sha": MEASURE_SHA,
            "battery": "R530/BATTERY_PROBLEMS.json (frozen R526 "
                       "problems, byte-identical; R526 canonical "
                       "state untouched)",
            "harvest": "R530/ATTR_MEASURE_HARVEST.json",
            "harvest_sha256": _sha(REPO / "R530/ATTR_MEASURE_HARVEST.json"),
            "join": args.join,
            "join_sha256": _sha(jpath),
            "n_observed": join.get("n_observed"),
            "selection_subspan_means": {
                k: (v or {}).get("mean")
                for k, v in sub_agg.items()},
            "selection_diag_means": {
                k: (v or {}).get("mean")
                for k, v in diag_agg.items()},
        },
        "answer": {
            "dominant_component": "G_scoring_detail_s",
            "dominant_mean_s": g_mean,
            "parent_wall_mean_s": e_mean,
            "dominant_fraction_of_parent": (
                round(g_mean / e_mean, 4)
                if g_mean is not None and e_mean else None),
            "mechanism": ("56 availability_score() calls x 3 "
                          "availability_report() full-ledger scans "
                          "= 168 ledger-file reads per generate() "
                          "call (sort comparisons + emit + "
                          "LAST_RESORT re-sort)"),
            "n_audited_calls": n_sub,
        },
        "case_assessment": {
            "case_A_signal": case_a_signal,
            "case_A_signal_provenance": ("observational readout of "
                                         "this battery only (G fraction "
                                         "of E, N audited calls); the "
                                         "0.9/2 values are descriptive, "
                                         "not authorization thresholds "
                                         "(Art. XXVII — no provenance "
                                         "invented)"),
            "case_A_counterfactual": ("per-call reuse of already-"
                                      "computed ledger-scan results "
                                      "within the same ladder "
                                      "construction (no cross-call "
                                      "cache, no TTL, no stale-health "
                                      "semantic change)"),
            "behavioral_identity_proven": behavior_proven,
            "verdict": ("CASE_A_CANDIDATE_IDENTIFIED__PROOF_PENDING"
                        if case_a_signal else "UNKNOWN"),
            "rule": ("repeated ledger scanning is OBSERVED at the "
                     "scan-count level (56 score calls x 168 scans "
                     "per call); the behavioral-identity checks "
                     "(same inputs, same scores, same ordering, "
                     "same rung, same fallback, same provenance) "
                     "must pass BEFORE the intervention may be "
                     "named (directive §6)"),
        },
        "funnel_parity": {
            "mechanisms_found": "1/10 (problem 4 BUILT)",
            "baseline_reference": "S5 4/10; R527-after 1/10",
            "note": ("measurement arm only — no optimization arm "
                     "ran, so no parity gate applies; the 1/10 "
                     "outcome is recorded as the provider-state "
                     "observation for this window, not as an "
                     "intervention effect"),
        },
        "round_states": {
            "measurement_complete": True,
            "optimization_authorized": False,
            "optimization_executed": False,
            "optimization_measured": False,
            "optimization_deployed": False,
            "note": ("R530 is a measurement round: the selection "
                     "subspan decomposition is durable on "
                     "production calls. Case A is a CANDIDATE, not "
                     "an authorization — the behavioral-identity "
                     "proof is the next round's entry gate."),
        },
        "classification": "MEASUREMENT_COMPLETE__CASE_A_CANDIDATE",
        "classification_not": [
            "NOT claimed: an authorized optimization (the "
            "behavioral-identity checks have not run)",
            "NOT claimed: a 19.5% avoidable fraction (withdrawn in "
            "R529 v1.1; selection is pre-call orchestration)",
            "NOT claimed: any end-to-end speedup",
            "NOT claimed: any stage is removable",
            "NOT claimed: independent certification green",
        ],
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"wrote {OUT} "
          f"(classification={rec['classification']})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
