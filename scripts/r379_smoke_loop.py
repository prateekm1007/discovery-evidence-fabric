"""Smoke test for the R379 technical loop (mocked proposers, hermetic)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] if False else "."))

from discovery_fabric.engine import technical_improvement_engine as tie
from discovery_fabric.engine import technical_state as ts
from discovery_fabric.engine.evaluator_contract import CandidateContext

EV_TEXT = ("Water-glycol coolant flow rates of 0.01-1.0 mL/min were "
           "tested in a lithium battery module; peak cell temperature "
           "fell from 55 to 42 degrees C at the highest flow. Pump "
           "noise at flow above 0.6 mL/min exceeded cabin limits.")
EV = [{"id": "ev:1", "title": "Cooling study", "text": EV_TEXT}]

STATE_PROPOSAL = {
    "parameters": [
        {"param_id": "coolant_flow", "name": "coolant flow rate",
         "category": "OPERATING_CONDITIONS", "unit": "mL/min",
         "value": 0.2, "value_class": "MODELLED",
         "range_min": 0.01, "range_max": 1.0,
         "range_span": "flow rates of 0.01-1.0 mL/min",
         "range_evidence_id": "ev:1",
         "role": "convective heat removal"},
        {"param_id": "peak_temp", "name": "peak cell temperature",
         "category": "PARAMETERS", "unit": "degC",
         "value": 55.0, "value_class": "EXTRACTED",
         "value_span": "fell from 55 to 42", "value_evidence_id": "ev:1",
         "range_min": 42.0, "range_max": 55.0,
         "range_span": "fell from 55 to 42", "range_evidence_id": "ev:1",
         "role": "thermal safety metric"},
    ],
    "constraints": [
        {"constraint_id": "c1", "target": "peak_temp", "bound": "<=",
         "limit": 60.0, "unit": "degC", "limit_class": "MODELLED",
         "justification": "cell safety threshold from problem constraint"},
        {"constraint_id": "c2", "target": "coolant_flow", "bound": "<=",
         "limit": 0.6, "unit": "mL/min", "limit_class": "MODELLED",
         "justification": "pump noise cabin limit at 0.6 mL/min from evidence narrative"},
    ],
    "objectives": [
        {"objective_id": "o1", "target": "peak_temp",
         "direction": "MINIMIZE",
         "basis": "battery thermal event containment failure requires peak temperature minimized"}],
    "dependencies": [
        {"relation_id": "r1", "cause": "coolant_flow", "effect": "peak_temp",
         "direction": "DECREASES",
         "statement": "higher coolant flow removes more heat",
         "relation_class": "MODELLED"}],
}

SPEC = {
    "invention_id": {"value": "smoke-1"},
    "mechanism": {"value": {
        "mechanism": "Convective cooling of the battery module by water-glycol coolant loop",
        "intervention": "Battery module with coolant loop at flow 0.2 mL/min",
        "expected_effect": "Peak cell temperature stays below the safety threshold",
        "falsification_test": "Measure temperature at operating load",
        "mechanism_source_span": "peak cell temperature",
    }},
    "distinguishing_features": {"value": {}},
    "prior_art": {"value": {}},
    "novelty_hypothesis": {"value": {}},
}
PROBLEM = {"device": "aircraft onboard lithium battery installation",
           "failure_mode": "battery thermal event containment failure",
           "failure": "thermal event", "constraint": "containment"}


class _Rec:
    def __init__(self, fields=None, status="OK"):
        self.fields = fields or {}
        self.status = status


def main():
    # 1) extraction with a mocked proposal
    def fake_propose_state(problem, spec, ev_items, provider=None, feedback=None):
        return {"proposal_id": "tsp:fake", "provider": "mock", "model": "mock",
                "status": "OK", "prompt_hash": "ph", "output_hash": "oh",
                "latency_ms": 1, "error": None, "proposal": STATE_PROPOSAL}
    orig_state = tie.propose_technical_state
    tie.propose_technical_state = fake_propose_state

    ctx = CandidateContext(spec=SPEC, decisive=None, problem=PROBLEM,
                           evidence_items=EV, collision=None, attack=None)

    # 2) mutation proposals: iteration 1 -> flow 0.5; iteration 2 -> flow 0.58
    mutations = [
        {"MUTATION_KIND": "OPERATING_CONDITION_CHANGE",
         "TARGET_PARAM": "coolant_flow", "NEW_VALUE": "0.5",
         "DIRECTION": "INCREASE", "VALUE_CLASS": "MODELLED",
         "VALUE_SPAN": "NONE", "VALUE_EVIDENCE_ID": "NONE",
         "RATIONALE": "more flow removes more heat, lowering peak temperature",
         "MECHANISM_DELTA": "coolant flow rate increased to 0.5 mL/min within the evidence envelope for convective heat removal",
         "INTERVENTION_DELTA": "the battery module coolant loop operates at 0.5 mL/min"},
        {"MUTATION_KIND": "OPERATING_CONDITION_CHANGE",
         "TARGET_PARAM": "coolant_flow", "NEW_VALUE": "0.58",
         "DIRECTION": "INCREASE", "VALUE_CLASS": "MODELLED",
         "VALUE_SPAN": "NONE", "VALUE_EVIDENCE_ID": "NONE",
         "RATIONALE": "further flow increase lowers temperature further",
         "MECHANISM_DELTA": "coolant flow rate increased to 0.58 mL/min for additional convective heat removal",
         "INTERVENTION_DELTA": "the battery module coolant loop operates at 0.58 mL/min"},
    ]
    calls = {"n": 0}
    def fake_propose_mutation(ctx, evaluation, provider=None, feedback=None):
        i = calls["n"]; calls["n"] += 1
        m = mutations[min(i, len(mutations) - 1)]
        return {"proposal_id": f"tmp:{i}", "provider": "mock", "model": "mock",
                "status": "OK", "prompt_hash": "ph", "output_hash": "oh",
                "latency_ms": 1, "error": None, "fields": m}
    tie.propose_technical_mutation = fake_propose_mutation

    ledger = tie.improve_candidate_technical(
        ctx, max_iterations=2, max_proposals=3, collision_mode="REPLAY_CACHE")

    tie.propose_technical_state = orig_state

    print("OUTCOME:", ledger["outcome"])
    print("REASON:", ledger["outcome_reason"])
    for it in ledger["iterations"]:
        d = it.get("decision") or {}
        print(f"  iter {it['iteration']}: target="
              f"{(it['diagnosis'].get('limiting_variable') or {}).get('param_id')} "
              f"decision={d.get('action')}")
        print(f"    technical_objective: {(d.get('checks') or {}).get('technical_objective')}")
        att = it.get("attribution")
        if att:
            print(f"    ATTRIBUTION: {att['changed_variable']} {att['from_value']} -> {att['to_value']} "
                  f"({att['value_class']}) dir={att['direction']}")
            print(f"      evaluated: {att['evaluated_result']}")
    print("summary:", {k: v for k, v in ledger["outcome_summary"].items()
                       if k != "attributions"})
    final_ctx = ledger.get("current_ctx")
    ts_final = (final_ctx.spec.get("technical_state") or {}).get("value") if final_ctx else None
    if ts_final:
        p = [x for x in ts_final["parameters"] if x["param_id"] == "coolant_flow"][0]
        print("final flow:", p["value"], p["value_class"], "history:", p.get("mutation_history"))
    return 0 if ledger["outcome"] == "TECHNICALLY_IMPROVED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
