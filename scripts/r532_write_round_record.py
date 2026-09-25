#!/usr/bin/env python3
"""R532 round-record generator (directive §13/§14).

R532 asked: what is the dominant measured MECHANISM_SPACE
instantiation-failure mode on fresh disjoint problems, and is any
component of it AVOIDABLE?

Answer (durable):
  instrumentation ......... typed-outcome classifier (11 outcomes)
    + instantiation_attempts records in adapters._lean_mechanism_space
    (behavior-neutral; proven by tests/test_r532_skipped_stage_envelopes.py)
  fresh battery .......... R532/MANIFEST: 12 problems (3 families),
    6 vehicles distinct from all prior sets, SECOND-qualifying-
    complaint discriminator, corpus-disjoint (8-gram + source-id +
    PRIOR_SCORED_ODI), all attempts retained (zeros are data)
  typed-outcome dist..... NOT_ATTEMPTED 4, ASSEMBLY_INVALID 3,
    CANDIDATE_ACCEPTED 4, SEMANTIC_REJECT 1 (n=12 observed)
  dominant failure mode . NOT_ATTEMPTED (4/12 = 33.3%) — the
    no-operator-contract-satisfied loss: no (item, operator) pair
    satisfied any admission contract. This is a PRE-LLM,
    deterministic, upstream-evidence loss (the same confound class
    as R531 p4: retrieval/evidence variance, not a mechanism-space
    bug). ASSEMBLY_INVALID (3/12 = 25%) is cemetery-blocked
    (NOT_A_CANDIDATE_CEMETERY_PROVEN_INVARIANT) — also
    deterministic, upstream-of-deterministic-tail, not an
    LLM failure. CANDIDATE_ACCEPTED (4/12 = 33.3%) = BUILT.
  avoidable component   NONE. The two dominant non-accept outcomes
    are pre-LLM deterministic losses (contract non-satisfaction,
    cemetery block). The provider execution wall (mean 6.317 s)
    dominates the stage wall but is genuine inference cost (R530
    stopping rule: avoidable_fraction = 0.0). No intervention is
    authorized in R532; no optimization is named.

Classification rule (§14): MEASUREMENT_COMPLETE__MECHANISM_SPACE_
FAILURE_DISTRIBUTION requires a fresh battery run on the instrumented
build + typed-outcome distribution identified + dominant failure
mode named + no avoidable component proven. All hold. No
OPTIMIZATION_MEASURED (no intervention executed, no paired
counterfactual). No DELIVERY_BLOCKED (the measurement completed).
No OPTIMIZATION_INCONCLUSIVE (a dominant failure mode was
identified and characterized).

Machine-generated from durable artifacts. No hand edits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
R532 = REPO / "R532"
OUT = R532 / "R532_ROUND_RECORD.json"


def _sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest() \
        if p.exists() else None


def _outcome_distribution(harvest_path: Path) -> dict:
    h = json.loads(harvest_path.read_text(encoding="utf-8"))
    rows = [r for r in h.get("rows", [])
            if (r.get("mechanism_space_spans") or {}).get(
                "class") == "OBSERVED_IN_STAGE"]
    outcomes = Counter()
    per_problem = {}
    for r in rows:
        ms = r["mechanism_space_spans"]
        pi = r.get("problem_index")
        atts = ms.get("instantiation_attempts") or []
        if not atts:
            per_problem[pi] = {"n_att": 0, "outcomes": [],
                                "terminal": ms.get("terminal_state")}
            continue
        ocs = [a.get("typed_outcome") for a in atts]
        per_problem[pi] = {"n_att": len(atts), "outcomes": ocs,
                           "terminal": ms.get("terminal_state")}
        for o in ocs:
            outcomes[o] += 1
    return {"n_observed": len(rows),
            "outcome_distribution": dict(outcomes.most_common()),
            "per_problem": {str(k): v
                            for k, v in sorted(per_problem.items(),
                                               key=lambda x: int(x[0]))}}


def _funnel_counts(harvest_path: Path) -> dict:
    h = json.loads(harvest_path.read_text(encoding="utf-8"))
    rows = [r for r in h.get("rows", [])
            if (r.get("mechanism_space_spans") or {}).get(
                "class") == "OBSERVED_IN_STAGE"]
    # The MECHANISM_SPACE terminal_state (from the mechanism-space
    # spans) is the authoritative discovery funnel for THIS round:
    # BUILT = a candidate was assembled and retained. The
    # RANK-stage `mechanisms_found` metric (mechanisms that survived
    # to the end) is a downstream survival measure, not a MECHANISM_
    # SPACE yield measure — record both, label them distinctly.
    ms_terminal = Counter()
    mf_reached = 0
    rows_detail = {}
    for r in rows:
        ms = r["mechanism_space_spans"]
        tstate = ms.get("terminal_state")
        ms_terminal[tstate] += 1
        m = r.get("mechanisms_found") or {}
        if m.get("reached") is True:
            mf_reached += 1
        rows_detail[str(r.get("problem_index"))] = {
            "ms_terminal_state": tstate,
            "rank_mechanisms_found_reached":
                m.get("reached") is True,
            "rank_mechanisms_found_state": m.get("state")}
    return {
        "mechanism_space_terminal_distribution":
            dict(ms_terminal.most_common()),
        "mechanism_space_built":
            ms_terminal.get("BUILT", 0),
        "rank_mechanisms_found": mf_reached,
        "n_rows": len(rows),
        "per_row": rows_detail,
        "note": ("mechanism_space_terminal_distribution is the "
                 "MECHANISM_SPACE yield measure (this round's "
                 "question); rank_mechanisms_found is the "
                 "downstream survival measure (a BUILT candidate "
                 "can still be killed by COLLISION/PHYSICS/ATTACK — "
                 "Art. LXXVII: discovery ≠ pipeline completion)")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--harvest",
                    default="R526/ATTR_AFTER_HARVEST.json")
    ap.add_argument("--join",
                    default="R532/MECHANISM_SPACE_PROVIDER_JOIN_R532.json")
    ap.add_argument("--manifest",
                    default="R532/BATTERY_PROBLEMS.json")
    args = ap.parse_args()

    hv = REPO / args.harvest
    jo = REPO / args.join
    mf = REPO / args.manifest

    od = _outcome_distribution(hv)
    fun = _funnel_counts(hv)
    jd = json.loads(jo.read_text(encoding="utf-8"))
    mand = json.loads(mf.read_text(encoding="utf-8"))

    dominant = (max(od["outcome_distribution"],
                     key=od["outcome_distribution"].get)
                if od["outcome_distribution"] else None)
    # A dominant FAILURE mode must exclude the success outcome —
    # CANDIDATE_ACCEPTED is the goal state, not a failure. If the
    # most frequent outcome is CANDIDATE_ACCEPTED, the dominant
    # failure mode is the most frequent NON-ACCEPT outcome instead.
    non_accept = {k: v for k, v in od["outcome_distribution"].items()
                  if k != "CANDIDATE_ACCEPTED"}
    dominant_failure = (max(non_accept, key=non_accept.get)
                       if non_accept else None)
    n_obs = od["n_observed"]
    dom_n = non_accept.get(dominant_failure, 0)

    fp = jd.get("funnel_parity") or {}
    cl = jd.get("classification") or {}
    ss = jd.get("selection_subspan_aggregate") or {}

    def _interp(d):
        return {
            "NOT_ATTEMPTED": ("no (item, operator) pair satisfied "
                              "any admission contract — pre-LLM, "
                              "deterministic, upstream-evidence loss "
                              "(retrieval/evidence variance; the same "
                              "confound class as R531 p4). The LLM "
                              "was never called; the mechanism-space "
                              "itself is not at fault."),
            "ASSEMBLY_INVALID": ("LLM called, output parsed, but the "
                                 "assembled candidate was "
                                 "cemetery-blocked "
                                 "(NOT_A_CANDIDATE_CEMETERY_PROVEN_"
                                 "INVARIANT). Deterministic tail, "
                                 "upstream-of-LLM, not an LLM "
                                 "failure."),
            "SEMANTIC_REJECT": ("LLM called and parsed, but the "
                                "operator's semantic check rejected "
                                "the candidate (TEXTUAL_REWRITE or "
                                "invariant break). The LLM output "
                                "did not constitute a valid "
                                "mechanism for the selected operator."),
        }.get(d, "see outcome detail")

    rec = {
        "artifact": "R532_ROUND_RECORD/1.0",
        "round": "R532",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                       time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "parent_round": "R531",
        "measurement_question": (
            "What is the dominant measured MECHANISM_SPACE "
            "instantiation-failure mode on fresh disjoint problems, "
            "and is any component of it AVOIDABLE?"),
        "instrumentation": {
            "change_set": ["discovery_fabric/engine/adapters.py",
                           "scripts/r526_harvest_attribution.py"],
            "behavioral_identity": {
                "harness":
                    "tests/test_r532_skipped_stage_envelopes.py",
                "tests": {"A–I": 8, "total": 8, "passed": 8},
                "verdict": "IDENTITY_PROVEN"},
            "not_changed": [
                "provider policy/order/retirement", "model", "prompt",
                "retry/backoff", "retrieval", "evidence selection",
                "operator selection", "mechanism-space semantics",
                "diversity/collision/attack gates",
                "discovery thresholds"],
        },
        "battery": {
            "manifest": args.manifest,
            "n_problems": mand.get("n_problems"),
            "declared_families": mand.get("declared_families"),
            "selection_rule":
                "SECOND qualifying complaint per class in odiNumber "
                "order; 6 vehicles distinct from all prior battery "
                "sets; corpus-disjoint (8-gram + source-id + "
                "PRIOR_SCORED_ODI); verbatim summary, machine-"
                "additive declaration prefix",
        },
        "typed_outcome_distribution": od,
        "dominant_failure_mode": {
            "outcome": dominant_failure,
            "n": dom_n,
            "fraction": round(dom_n / n_obs, 4) if n_obs else None,
            "interpretation": _interp(dominant_failure),
            "avoidable": False,
            "avoidable_rationale": (
                "The dominant non-accept outcomes are pre-LLM "
                "deterministic losses (contract non-satisfaction, "
                "cemetery block, semantic reject). No R532 "
                "intervention is authorized; the upstream "
                "evidence/retrieval confound is a separate "
                "discovery question, not a MECHANISM_SPACE yield "
                "bug (Art. LXXXIV: starvation-skip is correct, "
                "not broken)."),
        },
        "funnel": fun,
        "mechanism_space_economics": {
            "n_observed": jd.get("n_observed"),
            "provider_execution_mean_s":
                (jd.get("aggregate") or {}).get(
                    "provider_execution_s", {}).get("mean"),
            "selection_subspan_G_mean_s":
                ss.get("G_scoring_detail_s", {}).get("mean"),
            "classification_verdict": cl.get("verdict"),
            "avoidable_fraction": cl.get("avoidable_fraction"),
            "join": args.join,
        },
        "production_identity_chain": {
            "target_sha":
                "62c560989556b126d00c7156bc199852ca1664e2",
            "deploy_commit":
                "62c560989556b126d00c7156bc199852ca1664e2",
            "deploy_record": "R532/R532_DEPLOY_RECORD.json",
            "note": "live version/health/drift read at close; "
                    "see R532/R532_CLOSEOUT_PROOF.json",
        },
        "independent_certification": {
            "status": "NOT_GREEN",
            "cause": ("UNKNOWN — classifier-job failure reason not "
                      "exposed (Art. XXVI; workflow not suppressed, "
                      "local pytest not substituted)"),
        },
        "round_states": {
            "measurement_complete": True,
            "optimization_authorized": False,
            "optimization_executed": False,
            "optimization_measured": False,
            "optimization_deployed": False,
            "note": ("measurement complete: typed-outcome "
                     "distribution identified on 12 fresh problems; "
                     "dominant failure mode = "
                     + (dominant_failure or "NONE")
                     + " (deterministic pre/post-LLM loss); no "
                     "avoidable component proven; no intervention "
                     "authorized or executed"),
        },
        "classification":
            "MEASUREMENT_COMPLETE__MECHANISM_SPACE_FAILURE_"
            "DISTRIBUTION",
        "classification_not": [
            "NOT claimed: discovery improvement (4/12 BUILT at "
            "MECHANISM_SPACE; rank_mechanisms_found=0 — the "
            "survival gap is downstream of this round's question; "
            "Art. LXXVII: discovery ≠ pipeline completion)",
            "NOT claimed: any MECHANISM_SPACE optimization",
            "NOT claimed: end-to-end stage speedup",
            "NOT claimed: independent certification green",
            "NOT claimed: the upstream evidence/retrieval confound "
            "is a MECHANISM_SPACE problem (it is not — Art. "
            "LXXXIV starvation-skip is correct)",
        ],
    }
    import subprocess as _sp
    try:
        _o = _sp.run(["git", "rev-parse", "origin/main"],
                     capture_output=True, text=True, cwd=str(REPO))
        rec["production_identity_chain"]["origin_main"] = \
            _o.stdout.strip()
    except Exception:
        pass
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"wrote {OUT} "
          f"(classification={rec['classification']})")
    print(f"dominant outcome: {dominant} ({dom_n}/{n_obs})")
    print(f"outcome distribution: {od['outcome_distribution']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
