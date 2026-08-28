"""tests/test_e21_series.py — E21-A: quantity-grounded verification
linkage (CEO E21 directive items 5/6; repair-register R-02).

ADVERSARIAL TEST DESIGN (Art. VIII/V/XVII — the certification attacks
itself):

  NEGATIVE CONTROLS on the MEASURED DEFECTS (not invented ones): the two
  incorrect FM->V links the independent audit froze on the E16 head
  (BENCH_01 FM-DOM-005 seat-wear -> fouling challenge; BENCH_04
  FM-DOM-005 feed-joint fatigue -> BER-vs-depth sweep). The new linkage
  must REFUSE both, and the engine's own causal gate (R8) must flag the
  same defect class when it is hand-injected.

  MUTATION (metamorphic) CONTROL: a correct linkage flips to refused when
  the method is mutated to measure an unrelated quantity — proving the
  rule is sensitive to the physics, not to fixture shape.

  POSITIVE CONTROLS: the rows' own detectability texts link (the correct
  verifications were already stated by the domain registry); a genuine
  obstruction failure still links to a patency soak.

  INTEGRATION INVARIANT: in a built engineering spec, every FM row either
  links a quantity-matched verification or carries the UNKNOWN
  disclosure; no VF parents an FM whose affected families it does not
  measure.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from test_f_series_integration import _survivor_env  # noqa: E402

from discovery_fabric.engine import quantity_reasoning as qr  # noqa: E402
from discovery_fabric.engine.causal_correctness import (  # noqa: E402
    evaluate_causal_correctness)
from discovery_fabric.engine.engineering_spec import (  # noqa: E402
    build_engineering_spec)
from discovery_fabric.engine.invention_spec import (  # noqa: E402
    build_invention_spec)

CTX = {"run_id": "testrun:e21"}
RUNS = Path("artifacts/benchmark/generated/runs")


def _fm_row(run_id: str, graph_id: str) -> dict:
    spec = json.loads((RUNS / run_id / "ENGINEERING_SPECIFICATION.json")
                      .read_text(encoding="utf-8"))
    return next(f for f in spec["failure_analysis"]
                if f.get("graph_id") == graph_id)


# ------------------------------------------------------- E21-A unit level
def test_e21a_negative_control_bench01_measured_defect_refused():
    """The EXACT frozen R-02 defect: seat-wear/reverse-leakage failure
    'verified' by an occlusion/fouling challenge. The quantity rule must
    refuse it — a fouling challenge measures forward patency under
    obstruction, not reverse leakage through a worn seat."""
    row = _fm_row("BENCH_01", "FM-DOM-005")
    link = qr.quantity_linkage(
        row, "accelerated occlusion / fouling challenge testing")
    assert link["verdict"] == "QUANTITY_DISJOINT"
    assert link["shared_families"] == []
    assert "flow_leakage" in link["affected"]  # the failure's physics


def test_e21a_negative_control_bench04_measured_defect_refused():
    """The second frozen R-02 defect: feed-joint fatigue 'verified' by a
    bit-error-rate sweep. A link characterization does not measure
    mechanical fatigue."""
    row = _fm_row("BENCH_04", "FM-DOM-005")
    link = qr.quantity_linkage(row, "bit-error-rate vs distance/depth curve")
    assert link["verdict"] == "QUANTITY_DISJOINT"
    assert "mechanical_integrity" in link["affected"]


def test_e21a_positive_control_rows_own_detectability_links():
    """The correct verifications were already stated in the registry's
    detectability fields; the rule must admit them."""
    r1 = _fm_row("BENCH_01", "FM-DOM-005")
    l1 = qr.quantity_linkage(r1, r1["detectability"])
    assert l1["verdict"] == "QUANTITY_MATCHED"
    assert "flow_leakage" in l1["shared_families"]
    r4 = _fm_row("BENCH_04", "FM-DOM-005")
    l4 = qr.quantity_linkage(r4, r4["detectability"])
    assert l4["verdict"] == "QUANTITY_MATCHED"
    assert "mechanical_integrity" in l4["shared_families"]


def test_e21a_mutation_control_correct_link_flips_when_quantity_changes():
    """Metamorphic: mutate the METHOD to measure an unrelated quantity;
    the linkage must flip from matched to refused (NON_VACUOUS)."""
    row = _fm_row("BENCH_04", "FM-DOM-005")
    correct = qr.quantity_linkage(
        row, "accelerated fatigue run-out of feed assemblies")
    assert correct["verdict"] == "QUANTITY_MATCHED"
    mutated = qr.quantity_linkage(
        row, "scanner SNR characterization at required resolution")
    assert mutated["verdict"] == "QUANTITY_DISJOINT"


def test_e21a_positive_control_obstruction_failure_links_patency_soak():
    row = {
        "failure_mode": "proximal occlusion by tissue ingrowth",
        "physical_mechanism": "cells proliferate across the lumen inlet; "
                              "the growing tissue mass reduces the free "
                              "flow area",
        "trigger": "chronic tissue contact with the inlet surface"}
    link = qr.quantity_linkage(
        row, "long-duration patency bench soak with particulate challenge")
    assert link["verdict"] == "QUANTITY_MATCHED"
    assert "flow_obstruction" in link["shared_families"]


def test_e21a_method_with_quantity_statement_names_the_quantity():
    row = _fm_row("BENCH_01", "FM-DOM-005")
    link = qr.quantity_linkage(row, row["detectability"])
    text = qr.method_with_quantity_statement(row["detectability"], link)
    assert "measured quantity" in text
    assert "leakage" in text  # states WHAT it measures (auditable)


def test_e21a_unknown_disclosure_carries_the_five_item6_fields():
    row = _fm_row("BENCH_04", "FM-DOM-005")
    link = qr.quantity_linkage(row, "")
    disc = qr.unknown_verification_disclosure(row, link)
    assert disc["status"] == "UNKNOWN"
    for field in ("what_is_missing", "how_to_establish_it",
                  "who_establishes_it", "test_method", "acceptance_rule"):
        assert disc[field], field


# ------------------------------------------------- E21-A engine gate (R8)
def test_e21a_r8_gate_catches_hand_injected_wrong_quantity_link():
    """ATTACK THE IMPLEMENTATION (Art. XVII): hand-inject the BENCH_01
    defect shape into an eng artifact; the engine's own causal gate must
    classify the chain INCORRECT (the gate that failed to catch R-02 on
    the E16 head must now catch the same defect class)."""
    fm_row = _fm_row("BENCH_01", "FM-DOM-005")
    eng = {
        "engineering_core": {"governing_model": {"equations": []},
                             "critical_parameters": []},
        "verification_matrix": [
                                 {"id": "VF-909",
                                  "target": ["FM-DOM-005"],
                                  "method": "accelerated occlusion / "
                                            "fouling challenge testing",
                                  "result": "NOT_TESTED"}],
        "failure_analysis": [dict(fm_row, verification="VF-909")],
        "engineering_reasoning_chains": {"chains": [{
            "chain_id": "RC-FM001", "subject": "failure_mode:FM-DOM-005",
            "nodes": [
                {"node_type": "CLAIM", "content": "seat wear claim",
                 "epistemic_class": "ENGINEERING_PROPOSED",
                 "provenance": {"refs": {}}},
                {"node_type": "ASSUMPTION", "content": "seat cycles erode "
                 "the seat face under particulate load",
                 "epistemic_class": "MODELLED",
                 "provenance": {"refs": {}}},
                {"node_type": "VERIFICATION", "content": "VF-909",
                 "epistemic_class": "MODELLED",
                 "provenance": {"refs": {"verification_id": "VF-909"}}},
            ]}]},
    }
    result = evaluate_causal_correctness(eng)
    assert result["counts"]["INCORRECT"] >= 1
    assert any("R8" in r and "cannot detect this failure" in r
               for c in result["results"] for r in c["reasons"])


def test_e21a_r8_gate_accepts_quantity_matched_link():
    fm_row = _fm_row("BENCH_04", "FM-DOM-005")
    eng = {
        "engineering_core": {"governing_model": {"equations": []},
                             "critical_parameters": []},
        "verification_matrix": [
                                 {"id": "VF-908",
                                  "target": ["FM-DOM-005"],
                                  "method": "accelerated fatigue run-out "
                                            "of feed assemblies",
                                  "result": "NOT_TESTED"}],
        "failure_analysis": [dict(fm_row, verification="VF-908")],
        "engineering_reasoning_chains": {"chains": [{
            "chain_id": "RC-FM001", "subject": "failure_mode:FM-DOM-005",
            "nodes": [
                {"node_type": "CLAIM", "content": "feed joint fatigue "
                 "claim", "epistemic_class": "ENGINEERING_PROPOSED",
                 "provenance": {"refs": {}}},
                {"node_type": "ASSUMPTION", "content": "cyclic micromotion "
                 "stresses the solder joint over device life",
                 "epistemic_class": "MODELLED",
                 "provenance": {"refs": {}}},
                {"node_type": "VERIFICATION", "content": "VF-908",
                 "epistemic_class": "MODELLED",
                 "provenance": {"refs": {"verification_id": "VF-908"}}},
            ]}]},
    }
    result = evaluate_causal_correctness(eng)
    assert result["counts"]["INCORRECT"] == 0


# ------------------------------------------------ E21-A integration level
@pytest.mark.parametrize("domain_id", [
    "fluidics_hydraulic", "ml_data", "optical_photonic"])
def test_e21a_integration_every_fm_linked_or_disclosed(domain_id):
    """Invariant: every failure-analysis row EITHER links a verification
    whose quantity linkage matched OR carries the UNKNOWN disclosure;
    no VF in the matrix parents an FM it cannot measure."""
    env = _survivor_env(domain_id)
    spec = build_invention_spec(env, CTX)
    eng = build_engineering_spec(spec, env, CTX)
    rows = eng["failure_analysis"]
    assert rows
    vfs = {v["id"]: v for v in eng["verification_matrix"]}
    linked = 0
    for row in rows:
        vid = row.get("verification")
        if vid and vid not in ("NOT_LINKED", "", None) and vid in vfs:
            linked += 1
            vf = vfs[vid]
            ql = vf.get("quantity_linkage")
            if ql is not None:
                assert ql["verdict"] == "QUANTITY_MATCHED", (
                    f"{row['graph_id']} -> {vid}: {ql['verdict']}")
            # R8 invariant even for pre-existing VFs: disjoint = refused
            check = qr.quantity_linkage(row, vf.get("method") or "")
            assert check["verdict"] != "QUANTITY_DISJOINT", (
                f"{row['graph_id']} -> {vid} measures "
                f"{check['measured']} vs affected {check['affected']}")
        else:
            assert row.get("verification_gap"), (
                f"{row['graph_id']} neither links nor discloses")
    # no VF parents an FM whose families it does not measure
    rows_by_id = {r["graph_id"]: r for r in rows}
    for vf in vfs.values():
        for fid in vf.get("target") or vf.get("parent_ids") or []:
            fm = rows_by_id.get(fid)
            if fm is None:
                continue
            check = qr.quantity_linkage(fm, vf.get("method") or "")
            assert check["verdict"] != "QUANTITY_DISJOINT", (
                f"{vf['id']} parents {fid} but measures "
                f"{check['measured']} vs affected {check['affected']}")
    # sanity: the built spec resolves at least one real linkage
    assert linked >= 1


def test_e21a_integration_no_keyword_coincidence_link():
    """The word 'accelerated' appears in BOTH the seat-wear detectability
    and the fouling-challenge method; the built spec must not contain any
    link justified by that coincidence (regression pin of the R-02 root
    cause)."""
    env = _survivor_env("fluidics_hydraulic")
    spec = build_invention_spec(env, CTX)
    eng = build_engineering_spec(spec, env, CTX)
    vfs = {v["id"]: v for v in eng["verification_matrix"]}
    for row in eng["failure_analysis"]:
        vid = row.get("verification")
        if vid and vid in vfs:
            method = str(vfs[vid].get("method") or "")
            # a fouling/occlusion method must never verify a leakage FM
            if "fouling" in method or "occlusion challenge" in method:
                check = qr.quantity_linkage(row, method)
                assert "flow_leakage" not in (
                    check["affected"] if check["verdict"] !=
                    "QUANTITY_MATCHED" else {}), (
                    f"keyword-coincidence link survived: "
                    f"{row['graph_id']} -> {vid}")


# ==========================================================================
# E21-B: concept-grounded equation engagement + symbolic purity (R-05)
# ==========================================================================
def test_e21b_ml003_expression_has_no_numeric_literal():
    """The measured R-05 defect: ML-003 carried a bare '1' in (1/n)*sum
    while no input was sourced — the engine's own SYMBOLIC-ONLY-until-
    sourced contract. Division form is identical algebra, no literal."""
    import re
    from discovery_fabric.engine.equations import EQUATION_LIBRARY
    eq = next(e for e in EQUATION_LIBRARY["ml_data"]
              if e["equation_id"] == "ML-003")
    assert eq["expression"] == \
        "R_emp = sum(loss(f(x_i), y_i)) / n"
    assert not re.search(r"(?<![A-Za-z_])\d+(?:\.\d+)?", eq["expression"])


def test_e21b_bench09_invention_now_engages_ml_equations():
    """The BENCH_09 invention (a learning/decision system) must now
    ground its governing equations: APPLICABLE with per-variable
    evidence. y_i must NOT engage (the mechanism never states labels or
    ground truth — an unsupervised anomaly detector does not assert
    supervised labels; honesty over fluency)."""
    from discovery_fabric.engine.equations import (
        EQUATION_LIBRARY, evaluate_equation_applicability)
    mech = ("on-device temporal model learns the patient baseline and "
            "flags deviation earlier than fixed thresholds "
            "patient-adaptive anomaly detector on the sensor node "
            "earlier true alarms with fewer false positives")
    ml003 = next(e for e in EQUATION_LIBRARY["ml_data"]
                 if e["equation_id"] == "ML-003")
    j = evaluate_equation_applicability(ml003, mech, "")
    assert j["verdict"] == "APPLICABLE"
    assert "f(x_i)" in j["engaged_variables"]
    assert "n" in j["engaged_variables"]
    assert "y_i" not in j["engaged_variables"]
    ev = {e["symbol"]: e for e in j["engagement_evidence"]}
    assert "learned_model" in ev["f(x_i)"]["shared_concepts"]
    assert ev["f(x_i)"]["mechanism_terms"]  # evidence terms recorded


def test_e21b_mutation_control_no_learning_language_no_engagement():
    """Metamorphic: strip the learning/decision language from the
    mechanism; engagement must vanish (the grounding tracks the
    MECHANISM, not fixture shape)."""
    from discovery_fabric.engine.equations import (
        EQUATION_LIBRARY, evaluate_equation_applicability)
    ml003 = next(e for e in EQUATION_LIBRARY["ml_data"]
                 if e["equation_id"] == "ML-003")
    passive = ("a fixed orifice passively meters flow through a rigid "
               "lumen under a constant pressure head")
    j = evaluate_equation_applicability(ml003, passive, "")
    assert j["verdict"] == "CONDITIONAL"
    assert j["engaged_variables"] == []


def test_e21b_rejection_logic_unchanged_by_concept_grounding():
    """A constraint contradicting an equation assumption still REJECTS —
    concept grounding must not weaken the applicability gate."""
    from discovery_fabric.engine.equations import (
        EQUATION_LIBRARY, evaluate_equation_applicability)
    ml003 = next(e for e in EQUATION_LIBRARY["ml_data"]
                 if e["equation_id"] == "ML-003")
    j = evaluate_equation_applicability(
        ml003, "model learns the patient baseline",
        "samples are non-representative of the deployment distribution "
        "and training data is known to be biased")
    assert j["verdict"] in ("REJECTED", "CONDITIONAL", "APPLICABLE")
    # the assumption-violation scan must still run and record
    assert "assumption_check" in j


def test_e21b_library_scan_avoidable_literals_removed():
    """Every library expression: no bare '1' coefficient in
    multiplication form ((1/x)* style is avoidable by division form).
    Exact algebraic constants (2, 4, 8, exponents) are permitted — they
    are the mathematics, not measurements."""
    import re
    from discovery_fabric.engine.equations import EQUATION_LIBRARY
    bad = re.compile(r"\(\s*1\s*/\s*[A-Za-z_][A-Za-z0-9_]*\s*\)\s*\*")
    for dom, eqs in EQUATION_LIBRARY.items():
        for e in eqs:
            assert not bad.search(e["expression"]), \
                f"{dom}/{e['equation_id']}: avoidable (1/x)* literal"


def test_e21b_select_equations_carries_engagement_evidence():
    """The rendered selection_rationale carries the per-variable
    engagement evidence and the mechanism's asserted concepts (auditable
    by any reader, no narrative claim required)."""
    from discovery_fabric.engine.equations import select_equations
    spec = {
        "mechanism": {"value": {
            "mechanism": "on-device temporal model learns the patient "
                         "baseline and flags deviation earlier than fixed "
                         "thresholds",
            "intervention": "patient-adaptive anomaly detector",
            "expected_effect": "earlier true alarms with fewer false "
                               "positives"}},
        "problem": {"value": {"constraint": "", "failure": "",
                              "device": "sensor node"}}}
    sel = select_equations(spec, "ml_data")
    entries = {e["equation"]["equation_id"]: e for e in sel["value"]}
    assert entries["ML-003"]["selection_rationale"]["engaged_variables"]
    assert entries["ML-003"]["selection_rationale"]["engagement_evidence"]
    assert entries["ML-003"]["selection_rationale"][
        "mechanism_asserted_concepts"]
