#!/usr/bin/env python3
"""R529 round-record generator (directive §11).

R529 delivered: the MECHANISM_SPACE provider-ledger join (v1.1,
corrected semantics), the R527 closure repair, and the
machine-refreshed architecture metadata. No optimization was
named, executed, or measured in R529.

The five round-states are recorded EXPLICITLY:
  measurement_complete ..... True (the v1.1 join is durable)
  optimization_authorized .. False (no causal avoidable component
                             proven; the withdrawn 19.5% figure is
                             not a finding)
  optimization_executed .... False
  optimization_measured .... False
  optimization_deployed .... False

The record carries:
  - the corrected causal reading (SELECTION_ORCHESTRATION ≠
    FALLBACK_ROUTING; the R529 19.5% avoidable fraction WITHDRAWN)
  - the per-component aggregate means from the durable join
  - the independent-certification status (UNKNOWN cause, NOT green —
    local gates are not a substitute, Art. XXVI)
  - the metadata-chain validation result
  - the R530 handoff: the open question (what is inside the
    ~1.9 s selection wall) + the instrument that will answer it
    (gen_spans/1.0 selection_subspans A–I)

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
R529 = REPO / "R529"
R526 = REPO / "R526"
OUT = R529 / "R529_ROUND_RECORD.json"


def _sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest() \
        if p.exists() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--join", default="R529/MECHANISM_SPACE_PROVIDER_JOIN.json",
                    help="provider-ledger join artifact (repo-relative)")
    args = ap.parse_args()

    jpath = REPO / args.join
    join = json.loads(jpath.read_text(encoding="utf-8")) \
        if jpath.exists() else {}
    agg = join.get("aggregate") or {}
    cls = join.get("classification") or {}

    # metadata-chain validation (repo-side, via the refresh script)
    meta_chain = {}
    try:
        sys.path.insert(0, str(REPO / "scripts"))
        import r529_refresh_metadata as _rm
        g = json.loads((REPO / "ACTIVE_DISCOVERY_GRAPH.json")
                       .read_text(encoding="utf-8"))
        meta_chain = _rm.validate_metadata_chain(
            g.get("generated_from_commit") or "")
    except Exception as _e:  # noqa: BLE001 — recorded, never hidden
        meta_chain = {"chain_ok": False,
                      "error": f"{type(_e).__name__}: {str(_e)[:120]}"}

    # R527 closure state (the repaired record)
    r527 = {}
    try:
        r527 = json.loads((REPO / "R527" / "R527_ROUND_RECORD.json")
                          .read_text(encoding="utf-8"))
    except Exception:
        r527 = {}

    rec = {
        "artifact": "R529_ROUND_RECORD/1.0",
        "round": "R529",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                       time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "parent_round": "R528",
        "measurement": {
            "join_artifact": args.join,
            "join_sha256": _sha(jpath),
            "join_version": join.get("artifact"),
            "harvest": join.get("harvest"),
            "n_observed": join.get("n_observed"),
            "aggregate": {
                "selection_orchestration_s":
                    (agg.get("selection_orchestration_s") or {}).get(
                        "mean"),
                "failed_hop_admission_s":
                    (agg.get("failed_hop_admission_s") or {}).get(
                        "mean"),
                "inter_rung_fallback_s":
                    (agg.get("inter_rung_fallback_s") or {}).get(
                        "mean"),
                "provider_execution_s":
                    (agg.get("provider_execution_s") or {}).get(
                        "mean"),
            },
            "fallback_auth_failure":
                join.get("fallback_auth_failure"),
            "classification": cls,
        },
        "causal_correction": {
            "withdrawn": ("R529 v1.0 'C_fallback_routing_overhead_s "
                          "= selection_ordering_s = ~1.869 s' with a "
                          "19.5% avoidable fraction"),
            "reason": ("selection_ordering_s is a PRE-CALL span "
                       "(closes before message construction and "
                       "before any rung is attempted); it contains "
                       "availability_matrix, chain construction, "
                       "retirement/cost filters, ladder build, and "
                       "capability snapshot — NOT post-failure "
                       "fallback overhead"),
            "corrected_split": ("pre-call selection/ordering cost "
                                "+ failed-hop admission cost + "
                                "actual inter-rung fallback cost + "
                                "provider execution cost + unknown "
                                "remainder"),
            "status": ("SELECTION_ORCHESTRATION ≠ FALLBACK_ROUTING; "
                       "anything not directly measured remains "
                       "UNKNOWN (Art. XXV)"),
        },
        "r527_closure": {
            "record": "R527/R527_ROUND_RECORD.json",
            "classification": r527.get("classification"),
            "round_states": r527.get("round_states"),
            "baseline_mechanisms_found": (
                (r527.get("arms") or {}).get("baseline", {}).get(
                    "mechanisms_found", {}).get("mechanisms_found")),
            "after_mechanisms_found": (
                (r527.get("arms") or {}).get("after", {}).get(
                    "mechanisms_found", {}).get("mechanisms_found")),
        },
        "metadata_chain": meta_chain,
        "independent_certification": {
            "status": "NOT_GREEN",
            "cause": ("UNKNOWN — the Epistemic Certification "
                      "classifier-job failure reason could not be "
                      "retrieved from the available interface "
                      "(runs #1105, #1106)"),
            "rule": ("local gates green ≠ independent certification "
                     "green (Art. XXVI). The workflow is NOT "
                     "suppressed and local pytest is NOT cited as "
                     "a substitute."),
        },
        "round_states": {
            "measurement_complete": True,
            "optimization_authorized": False,
            "optimization_executed": False,
            "optimization_measured": False,
            "optimization_deployed": False,
            "note": ("R529 is a measurement round: the corrected "
                     "join + the R527 closure repair + the metadata "
                     "refresh are durable. No causal avoidable "
                     "component is proven (the 19.5% figure is "
                     "withdrawn), so no optimization is named, "
                     "executed, measured, or deployed."),
        },
        "classification": "MEASUREMENT_ONLY__NO_OPTIMIZATION_NAMED",
        "classification_not": [
            "NOT claimed: a 19.5% avoidable fraction (withdrawn — "
            "the selection span is pre-call orchestration, not "
            "fallback overhead)",
            "NOT claimed: independent certification green (the "
            "classifier-job failure cause is UNKNOWN)",
            "NOT claimed: any end-to-end speedup",
            "NOT claimed: any stage is removable (0 stages "
            "removable on current evidence)",
        ],
        "r530_handoff": {
            "open_question": ("what exactly is inside the current "
                              "MECHANISM_SPACE selection-ordering "
                              "wall (~1.9 s mean)?"),
            "instrument": ("gen_spans/1.0 selection_subspans A–I + "
                           "selection_diag counts (R530 §3)"),
            "allowed_outcomes": ["REAL_REQUIRED_ROUTING_WORK",
                                 "ONE_MEASURED_AVOIDABLE_LOCAL_COMPONENT"],
        },
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"wrote {OUT} "
          f"(classification={rec['classification']})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
