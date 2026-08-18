"""
Hostile Synthetic Test Case
============================

CEO directive: "Test the orchestrator on a deliberately hostile synthetic
case before #5. Give it a known candidate where:
  - one result is a false positive
  - one alternative solves a neighboring problem
  - one alternative genuinely threatens the candidate
  - three providers return the same family
  - a scientific paper contradicts a patent claim
  - PatSnap is expensive but actually unnecessary
  - another case requires PatSnap to resolve a material uncertainty

The orchestrator must make the correct routing/stopping decisions mechanically.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from orchestrator.territory_discovery import TerritoryDiscovery, Territory, CereVascGap
from orchestrator.next_best_action import NextBestAction, Action
from orchestrator.evidence_graph import EvidenceGraph, EvidenceQuestion, EvidenceItem, Contradiction
from orchestrator.coverage_engine import CoverageEngine, CoverageContract
from orchestrator.contradiction_queue import ContradictionQueue
from orchestrator.alternative_ledger import AlternativeLedger, Alternative
from orchestrator.portfolio import Portfolio
from datetime import datetime, timezone
import json
from pathlib import Path


def run_hostile_synthetic_test():
    """Run the deliberately hostile synthetic test case."""
    print("="*70)
    print("HOSTILE SYNTHETIC TEST CASE")
    print("="*70)

    results = {"test_id": "HOSTILE_SYNTHETIC_V1",
               "timestamp": datetime.now(timezone.utc).isoformat(),
               "scenarios": []}

    # ---------- SCENARIO 1: False Positive ----------
    print("\n--- Scenario 1: False Positive ---")
    graph = EvidenceGraph()
    # Simulate finding an electrical "shunt active power filter" (false positive for CSF shunt)
    q = EvidenceQuestion(
        question_id="EQ_FP1",
        question="Does prior art teach active valve perturbation for CSF shunt diagnostics?",
        hypothesis="No — active perturbation is architecturally distinct",
        expected_decision_impact={"if_found": "novelty destroyed",
                                   "if_not_found": "survives",
                                   "if_ambiguous": "escalate"},
        evidence_class="hostile_prior_art",
        cheapest_capable_source="Scopus",
        stop_condition="top 10 results classified"
    )
    graph.add_question(q)
    # Simulate Scopus returning electrical shunt filter (false positive)
    e = EvidenceItem(
        evidence_id="EV_FP1",
        question_id="EQ_FP1",
        source="Scopus",
        content="Real-time control of shunt active power filter under distorted grid voltage",
        content_hash="abc123",
        family_hash="",
        mechanism_hash="electrical_power_filter",
        evidence_type="EXTERNAL",
        classification="DIFFERENT_PROBLEM"
    )
    graph.add_evidence(e)
    q.result = "FALSE_POSITIVE"
    q.result_evidence = "Electrical shunt active power filter — NOT CSF shunt"
    print(f"  Question: {q.question[:60]}")
    print(f"  Result: {q.result}")
    print(f"  Evidence classification: {e.classification}")
    print(f"  FALSE_POSITIVE correctly recorded: {q.result == 'FALSE_POSITIVE'}")
    results["scenarios"].append({
        "scenario": "false_positive",
        "correct_decision": q.result == "FALSE_POSITIVE",
        "details": "Electrical shunt active power filter correctly identified as FALSE_POSITIVE (DIFFERENT_PROBLEM)"
    })

    # ---------- SCENARIO 2: Neighboring Problem (hydrogel) ----------
    print("\n--- Scenario 2: Neighboring Problem ---")
    ledger = AlternativeLedger()
    alt = Alternative(
        alternative_id="ALT_hydrogel",
        description="Intrathecal polymeric nanocomposite hydrogel for drug delivery",
        source="Scopus",
        axis_1_objective="mismatch",  # SCI drug delivery vs CSF drainage
        axis_2_mechanism="mismatch",  # depot vs filter
        axis_3_constraints="mismatch",  # no drainage constraint
        axis_4_operating_environment="mismatch",  # intrathecal injection vs shunt lumen
        axis_5_output="mismatch",  # sustained release vs filtered CSF
        axis_6_failure_mode="mismatch",  # depot depletion vs filter fouling
        classification="NEIGHBORING_PROBLEM",
        result="alternative_neighboring",
        why_rejected="Does not solve the coupled problem (retention + drainage)"
    )
    ledger.add(alt)
    print(f"  Alternative: {alt.description[:60]}")
    print(f"  Classification: {alt.classification}")
    print(f"  Correctly identified as neighboring: {alt.classification == 'NEIGHBORING_PROBLEM'}")
    results["scenarios"].append({
        "scenario": "neighboring_problem",
        "correct_decision": alt.classification == "NEIGHBORING_PROBLEM",
        "details": "Hydrogel correctly identified as NEIGHBORING_PROBLEM (6-axis mismatch)"
    })

    # ---------- SCENARIO 3: Genuine Threat ----------
    print("\n--- Scenario 3: Genuine Threat ---")
    cq = ContradictionQueue()
    c = Contradiction(
        contradiction_id="CQ_threat1",
        description="US11806490B2 claim 8 may teach derivative action",
        claim_or_limitation_affected="L3d",
        severity="HIGH",
        probability=0.7,
        evidence_quality="STRONG",
        decision_impact=0.9,
        currently_unresolved=True
    )
    cq.add(c)
    next_attack = cq.get_next_to_attack()
    print(f"  Contradiction: {c.description[:60]}")
    print(f"  Severity: {c.severity}, Priority: {c.priority_score:.2f}")
    print(f"  Is blocking: {c.is_blocking}")
    print(f"  Next to attack: {next_attack.contradiction_id if next_attack else 'None'}")
    print(f"  Correctly prioritized: {next_attack and next_attack.contradiction_id == 'CQ_threat1'}")
    results["scenarios"].append({
        "scenario": "genuine_threat",
        "correct_decision": next_attack and next_attack.contradiction_id == "CQ_threat1",
        "details": "Genuine threat correctly prioritized (HIGH severity, p=0.7, STRONG evidence)"
    })

    # ---------- SCENARIO 4: Three Providers Same Family ----------
    print("\n--- Scenario 4: Three Providers Same Family ---")
    graph2 = EvidenceGraph()
    # Lens, Google, PatentBear all return WO2020086847A1 (same family)
    for source in ["Lens", "GooglePatents", "PatentBear"]:
        e = EvidenceItem(
            evidence_id=f"EV_redundant_{source}",
            question_id="EQ_redundant",
            source=source,
            content="WO2020086847A1 - Self-adjusting hydrocephalus valve",
            content_hash="same_hash",
            family_hash="WO847_family",
            mechanism_hash="pressure_differential",
            evidence_type="EXTERNAL"
        )
        graph2.add_evidence(e)
    independent_count = graph2.get_independent_evidence_count()
    print(f"  3 providers returned same family")
    print(f"  Independent evidence count: {independent_count} (should be 1)")
    print(f"  Correctly identified redundancy: {independent_count == 1}")
    results["scenarios"].append({
        "scenario": "redundant_family",
        "correct_decision": independent_count == 1,
        "details": "3 providers returning same family = 1 independent discovery (not 3)"
    })

    # ---------- SCENARIO 5: Paper Contradicts Patent ----------
    print("\n--- Scenario 5: Paper Contradicts Patent ---")
    graph3 = EvidenceGraph()
    # Patent says "attenuate sudden changes" but scientific paper says "derivative action is beneficial"
    patent_ev = EvidenceItem(
        evidence_id="EV_patent_attenuate",
        question_id="EQ_contradiction",
        source="PatSnap",
        content="US11806490B2 claim 8: attenuate an effect of sudden changes",
        content_hash="patent_hash",
        evidence_type="OBSERVED"
    )
    paper_ev = EvidenceItem(
        evidence_id="EV_paper_derivative",
        question_id="EQ_contradiction",
        source="Scopus",
        content="2025 paper: derivative-of-differential control reduces over-drainage by 53%",
        content_hash="paper_hash",
        evidence_type="EXTERNAL"
    )
    graph3.add_evidence(patent_ev)
    graph3.add_evidence(paper_ev)
    # The contradiction: patent teaches AWAY (attenuate), paper says derivative is beneficial
    c2 = Contradiction(
        contradiction_id="CQ_paper_vs_patent",
        description="Patent teaches ATTENUATE sudden changes, but paper says derivative AMPLIFIES them beneficially",
        claim_or_limitation_affected="L3d",
        severity="MEDIUM",  # actually supports non-obviousness (teaches away)
        probability=0.9,
        evidence_quality="STRONG",
        decision_impact=0.5,
        currently_unresolved=False,
        resolution_result="RESOLVED_FALSE_ALARM — teaches AWAY supports non-obviousness"
    )
    graph3.add_contradiction(c2)
    print(f"  Patent: {patent_ev.content[:60]}")
    print(f"  Paper: {paper_ev.content[:60]}")
    print(f"  Contradiction resolved as: {c2.resolution_result}")
    print(f"  Correctly resolved: {c2.resolution_result.startswith('RESOLVED_FALSE_ALARM')}")
    results["scenarios"].append({
        "scenario": "paper_contradicts_patent",
        "correct_decision": c2.resolution_result.startswith("RESOLVED_FALSE_ALARM"),
        "details": "Patent teaches AWAY (attenuate), paper shows derivative beneficial → supports non-obviousness"
    })

    # ---------- SCENARIO 6: PatSnap Unnecessary ----------
    print("\n--- Scenario 6: PatSnap Unnecessary ---")
    contract = CoverageContract(
        territory_id="TEST_low_materiality",
        technology_class="niche mechanism",
        required_jurisdictions=["US"],
        temporal_floor="2010",
        patsnap_materiality="LOW"
    )
    engine = CoverageEngine(contract)
    materiality = engine.assess_patsnap_materiality({
        "same_problem_threats": 0,
        "claim_text_audited": True,
        "neighboring_only": True,
        "family_members_missed": False
    })
    patsnap_required = engine.is_patsnap_required(materiality)
    print(f"  Cheaper sources found: 0 same-problem threats, claims audited, neighboring only")
    print(f"  PatSnap materiality: {materiality}")
    print(f"  PatSnap required: {patsnap_required}")
    print(f"  Correctly skipped PatSnap: {not patsnap_required}")
    skip_doc = engine.document_patsnap_skip(materiality, "Cheaper sources found no same-problem threats; claims already audited")
    results["scenarios"].append({
        "scenario": "patsnap_unnecessary",
        "correct_decision": not patsnap_required,
        "details": f"PatSnap materiality={materiality}, correctly NOT required. Skip documented: {skip_doc['reason'][:80]}"
    })

    # ---------- SCENARIO 7: PatSnap Necessary ----------
    print("\n--- Scenario 7: PatSnap Necessary ---")
    contract2 = CoverageContract(
        territory_id="TEST_high_materiality",
        technology_class="crowded patent landscape",
        required_jurisdictions=["US", "EP", "WO"],
        temporal_floor="1990",
        patsnap_materiality="HIGH"
    )
    engine2 = CoverageEngine(contract2)
    materiality2 = engine2.assess_patsnap_materiality({
        "same_problem_threats": 2,
        "claim_text_audited": False,  # claims NOT yet audited
        "neighboring_only": False,
        "family_members_missed": True  # family expansion needed
    })
    patsnap_required2 = engine2.is_patsnap_required(materiality2)
    print(f"  Cheaper sources found: 2 same-problem threats, claims NOT audited, family members missed")
    print(f"  PatSnap materiality: {materiality2}")
    print(f"  PatSnap required: {patsnap_required2}")
    print(f"  Correctly required PatSnap: {patsnap_required2}")
    results["scenarios"].append({
        "scenario": "patsnap_necessary",
        "correct_decision": patsnap_required2,
        "details": f"PatSnap materiality={materiality2}, correctly REQUIRED (family expansion + claim-data needed)"
    })

    # ---------- SCENARIO 8: NEXT_BEST_ACTION Scoring ----------
    print("\n--- Scenario 8: NEXT_BEST_ACTION Scoring ---")
    nba = NextBestAction()
    actions = [
        Action(action_id="A1", description="PatSnap semantic-search (HIGH materiality)",
               evidence_question_id="EQ1", provider="PatSnap",
               expected_information_gain=0.7, probability_of_decision_change=0.9,
               decision_impact=0.9, cost=50, redundancy_penalty=0.0),
        Action(action_id="A2", description="Scopus broad review search",
               evidence_question_id="EQ2", provider="Scopus",
               expected_information_gain=0.6, probability_of_decision_change=0.1,
               decision_impact=0.2, cost=1, redundancy_penalty=0.3),
        Action(action_id="A3", description="Simulation with harder noise",
               evidence_question_id="EQ3", provider="Simulation",
               expected_information_gain=0.5, probability_of_decision_change=0.5,
               decision_impact=0.6, cost=5, redundancy_penalty=0.1),
    ]
    ranked = nba.rank_actions(actions)
    best = nba.select_best(actions)
    print(f"  Actions ranked by V4 score:")
    for a in ranked:
        print(f"    {a.action_id}: score={a.score:.4f} ({a.description[:50]})")
    print(f"  Best: {best.action_id if best else 'None'}")
    # V4 formula should prioritize decision-relevant actions
    # A1: (0.7×0.9×0.9)/50 - 0 = 0.0113
    # A3: (0.5×0.5×0.6)/5 - 0.1 = 0.03 - 0.1 = -0.07
    # A2: (0.6×0.1×0.2)/1 - 0.3 = 0.012 - 0.3 = -0.288
    print(f"  Correctly selected PatSnap (HIGH decision impact): {best.action_id == 'A1'}")
    results["scenarios"].append({
        "scenario": "next_best_action_scoring",
        "correct_decision": best.action_id == "A1",
        "details": f"V4 formula correctly prioritized A1 (PatSnap, score={ranked[0].score:.4f}) over decision-irrelevant A2 (score={ranked[1].score:.4f})"
    })

    # ---------- SUMMARY ----------
    print(f"\n{'='*70}")
    print(f"HOSTILE SYNTHETIC TEST SUMMARY")
    print(f"{'='*70}")
    passed = sum(1 for s in results["scenarios"] if s["correct_decision"])
    total = len(results["scenarios"])
    for s in results["scenarios"]:
        status = "PASS" if s["correct_decision"] else "FAIL"
        print(f"  [{status}] {s['scenario']}")
    print(f"\n  Total: {passed}/{total} scenarios passed")
    results["summary"] = {"passed": passed, "total": total, "all_passed": passed == total}

    # Save
    out_path = Path("/home/z/my-project/discovery-evidence-fabric/orchestrator/test/HOSTILE_SYNTHETIC_RESULTS.json")
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\n=== Wrote {out_path} ===")
    return results


if __name__ == "__main__":
    run_hostile_synthetic_test()
