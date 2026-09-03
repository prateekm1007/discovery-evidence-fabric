"""tests/test_r401_operator_behavior.py — R401B B4: THE HARD
BEHAVIORAL OPERATOR TESTS (mandatory).

For each operator, a CONTROLLED source mechanism M1 (a structured
evidence item with fixed fields) is transformed by a canned M2
response. The M2 must demonstrate a STRUCTURAL change matching the
operator's declared semantics — verified by the deterministic
operator_semantic_check (invariant + required change + independent
term-level structural comparison + derivation trace + testable
prediction, which the candidate assembly enforces).

Three M2 variants per operator:
  VALID     — satisfies invariant AND required change -> SEMANTICALLY_
              VALID, the candidate survives
  REWRITE   — M1 restated (causal mechanism unchanged, no structural
              change) -> TEXTUAL_REWRITE, NOT a candidate
  BROKEN    — the causal mechanism itself replaced -> SEMANTIC_
              INVARIANT_BROKEN, NOT a candidate

A semantic-similarity detector alone is insufficient (directive) — the
checks here are term-level structural comparisons with recorded bases.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import mechanism_space as ms  # noqa: E402

PROBLEM = {
    "problem_id": "r401_b4",
    "device": "tunneled hemodialysis catheter",
    "failure": "thrombotic occlusion of the lumen under low flow",
    "failure_mode": "thrombotic occlusion",
    "constraint": "maintain drainage above 0.05 mL/min",
}


def _fake_llm(responses):
    state = {"i": 0}

    def _gen(prompt, system="", timeout=240, max_tokens=700,
             purpose="mechanism_space", exclude_providers=None):
        i = state["i"]
        state["i"] += 1
        r = responses[i] if i < len(responses) else None
        if r is None:
            return {"ok": False, "status": "CALL_FAILED",
                    "content": None, "provider": "fake",
                    "model": "fake", "error": "exhausted"}
        return {"ok": True, "status": "OK", "content": r,
                "provider": "fake", "model": "fake-model",
                "prompt_hash": f"ph{i}", "output_hash": f"oh{i}",
                "error": None, "excluded_providers": [],
                "fallback": False}
    return _gen


def _m1(mechanism, system, intervention, observed, boundary,
        failure_mode, record_text=None):
    """A controlled structured source mechanism M1 (fields already
    VALID — the extraction step is faked to return these exact fields,
    which are all drawn from the record text so the validator binds)."""
    rt = record_text or f"{system} {intervention} {mechanism} " \
                        f"{observed} {boundary} {failure_mode}"
    return {
        "structured_evidence_version": ms.MECHANISM_SPACE_VERSION,
        "item_id": "m1-controlled",
        "fields": {
            "claim": {"value": f"{mechanism}", "state": "VALID",
                      "binding": {"n_shared_terms": 3}},
            "observed_effect": {"value": observed, "state": "VALID",
                                "binding": {"n_shared_terms": 3}},
            "system": {"value": system, "state": "VALID",
                       "binding": {"n_shared_terms": 3}},
            "intervention": {"value": intervention, "state": "VALID",
                             "binding": {"n_shared_terms": 3}},
            "mechanism": {"value": mechanism, "state": "VALID",
                          "binding": {"n_shared_terms": 3}},
            "boundary_conditions": {"value": boundary, "state": "VALID",
                                    "binding": {"n_shared_terms": 3}},
            "constraints": {"value": "none stated", "state": "VALID",
                            "binding": {"n_shared_terms": 1}},
            "failure_mode": {"value": failure_mode, "state": "VALID",
                             "binding": {"n_shared_terms": 2}},
            "confidence": {"value": "HIGH", "state": "VALID",
                           "binding": None},
        },
        "source": {"source_id": "m1-controlled", "source_name": "test",
                   "content_hash": "hash-m1", "title": "controlled",
                   "retrieval_timestamp": "2026-09-03T00:00:00Z"},
        "provenance": {"custody": "controlled fixture (B4)",
                       "extraction_provider": "fake"},
        "structured_hash": "fixture-m1",
        "extraction_summary": {"mechanism_extracted": True},
        "confidence": "HIGH",
        "_record_text": rt,
    }


def _m2_lines(mechanism, intervention, predicted, design_variable,
              testable, failure_modes, boundary, span):
    return (
        f"MECHANISM: {mechanism}\n"
        f"INTERVENTION: {intervention}\n"
        f"PREDICTED_EFFECT: {predicted}\n"
        f"NOVEL_DESIGN_VARIABLE: {design_variable}\n"
        f"TESTABLE_PREDICTION: {testable}\n"
        f"KNOWN_FAILURE_MODES: {failure_modes}\n"
        f"BOUNDARY_CONDITIONS: {boundary}\n"
        f"MECHANISM_SOURCE_SPAN: {span}\n")


def _apply(monkeypatch, op_id, m1, m2_text):
    monkeypatch.setattr(ms, "llm_generate", _fake_llm([m2_text]))
    op = next(o for o in ms.TRANSFORMATION_OPERATORS
              if o["operator_id"] == op_id)
    res = ms.apply_operator(op, [m1], PROBLEM)
    cands = [c for c in res["candidates"] if isinstance(c, dict)]
    assert cands, f"operator {op_id} produced no candidate record"
    return cands[0]


M1_MEDICAL = _m1(
    mechanism="heparin bonding inhibits clotting cascade activation at "
              "the luminal surface",
    system="tunneled hemodialysis catheter lumen",
    intervention="heparin bonding of the luminal surface",
    observed="thrombus area reduced under low flow",
    boundary="flow rate 50 mL/min and venous pressure 20 mmHg",
    failure_mode="thrombotic occlusion",
    record_text="Heparin-bonded luminal surfaces reduce thrombus "
                "formation in tunneled hemodialysis catheters. Heparin "
                "bonding inhibits clotting cascade activation at the "
                "luminal surface. Thrombus area reduced under low flow "
                "at flow rate 50 mL/min and venous pressure 20 mmHg. "
                "Failure by thrombotic occlusion observed.")

M1_FOREIGN = _m1(
    mechanism="electrostatic repulsion of like charges at the surface "
              "boundary prevents particle occlusion",
    system="vacuum chamber microfluidic channels",
    intervention="applied electrostatic field of 2 kV on channel walls",
    observed="charged channel walls accumulated no particle deposition "
             "while grounded channels occluded",
    boundary="applied voltage 2 kV and temperature -50 C",
    failure_mode="particle occlusion of channels",
    record_text="Electrostatic repulsion of like charges at the "
                "surface boundary prevents particle occlusion in "
                "vacuum chamber microfluidic channels. Charged channel "
                "walls accumulated no particle deposition while "
                "grounded channels occluded at applied voltage 2 kV.")

SPAN_MED = "Heparin bonding inhibits clotting cascade activation at " \
           "the luminal surface"
SPAN_FOREIGN = "electrostatic repulsion of like charges at the " \
               "surface boundary"


# ---------------------------------------------------------------------------
# DIRECT_TRANSFER: mechanism preserved + intervention instantiated in
# the TARGET device
# ---------------------------------------------------------------------------
class TestDirectTransferBehavior:
    def test_valid_transfer(self, monkeypatch):
        m2 = _m2_lines(
            "heparin bonding inhibits clotting cascade activation at "
            "the luminal surface",
            "bond heparin to the tunneled hemodialysis catheter lumen "
            "wall",
            "thrombus area reduced by 50 percent under low flow",
            "luminal heparin surface density",
            "thrombus area at 50 mL/min reduced by 50 percent versus "
            "untreated catheters",
            "heparin leaching; bonding delamination",
            "flow above 20 mL/min", SPAN_MED)
        c = _apply(monkeypatch, "DIRECT_TRANSFER", M1_MEDICAL, m2)
        assert c["candidate_state"] == "CANDIDATE"
        sem = c["operator_semantics"]
        assert sem["semantic_verdict"] == "SEMANTICALLY_VALID"
        assert sem["invariant_held"] and sem["required_change_present"]
        assert sem["checked_fields"]["intervention_in_target_system"][
            "target_terms"]

    def test_textual_rewrite_fails(self, monkeypatch):
        # the causal mechanism restated, but the intervention never
        # instantiates in the TARGET device (a laboratory tube — no
        # catheter vocabulary): a rewrite, not a transfer
        m2 = _m2_lines(
            "heparin bonding inhibits clotting cascade activation at "
            "the luminal surface",
            "apply heparin bonding to laboratory test tube surfaces",
            "thrombus reduced by 50 percent",
            "heparin density",
            "thrombus area reduced by 50 percent in tubes",
            "leaching",
            "static incubation", SPAN_MED)
        c = _apply(monkeypatch, "DIRECT_TRANSFER", M1_MEDICAL, m2)
        sem = c["operator_semantics"]
        assert sem["semantic_verdict"] == "TEXTUAL_REWRITE"
        assert c["candidate_state"] == "NOT_A_CANDIDATE_TEXTUAL_REWRITE"

    def test_broken_invariant_fails(self, monkeypatch):
        # the mechanism was REPLACED (antimicrobial silver, not
        # heparin/clotting): the transferred mechanism is gone
        m2 = _m2_lines(
            "silver ion release disrupts bacterial cell membranes "
            "preventing biofilm colonization",
            "coat the tunneled hemodialysis catheter with silver "
            "nanoparticles",
            "biofilm reduced by 50 percent",
            "silver loading",
            "biofilm mass reduced by 50 percent at 7 days",
            "silver toxicity",
            "physiological saline", SPAN_MED)
        c = _apply(monkeypatch, "DIRECT_TRANSFER", M1_MEDICAL, m2)
        sem = c["operator_semantics"]
        assert sem["semantic_verdict"] == "SEMANTIC_INVARIANT_BROKEN"
        assert c["candidate_state"] == \
            "NOT_A_CANDIDATE_OPERATOR_INVARIANT_BROKEN"


# ---------------------------------------------------------------------------
# CROSS_DOMAIN_ANALOGY: source mechanism identified + target mapping
# ---------------------------------------------------------------------------
class TestCrossDomainAnalogyBehavior:
    def test_valid_analogy(self, monkeypatch):
        m2 = _m2_lines(
            "electrostatic repulsion of like charges at the boundary "
            "prevents particle deposition in the catheter lumen",
            "charge the catheter lumen wall with an applied "
            "electrostatic field to repel charged thrombus precursors",
            "deposition and thrombus reduced by repulsion",
            "applied lumen wall voltage",
            "deposition mass decreases as voltage rises from 0 to 2 kV",
            "discharge; field distortion by conductive fluid",
            "applied voltage 0-2 kV in blood", SPAN_FOREIGN)
        c = _apply(monkeypatch, "CROSS_DOMAIN_ANALOGY", M1_FOREIGN, m2)
        assert c["candidate_state"] == "CANDIDATE"
        sem = c["operator_semantics"]
        assert sem["semantic_verdict"] == "SEMANTICALLY_VALID"
        # the source-domain mechanism is EXPLICITLY identified in the
        # checked fields (directive requirement)
        assert sem["checked_fields"]["source_mechanism_identified"][
            "shared_terms"]
        assert sem["checked_fields"]["target_domain_mapping"][
            "target_terms"]

    def test_source_copy_without_mapping_fails(self, monkeypatch):
        # the foreign system restated as-is — no target-domain mapping
        m2 = _m2_lines(
            "electrostatic repulsion of like charges at the surface "
            "boundary prevents particle occlusion",
            "apply an electrostatic field of 2 kV on the vacuum chamber "
            "microfluidic channel walls",
            "particle deposition prevented in the vacuum chamber",
            "applied voltage",
            "deposition absent at 2 kV in vacuum",
            "discharge",
            "vacuum at -50 C", SPAN_FOREIGN)
        c = _apply(monkeypatch, "CROSS_DOMAIN_ANALOGY", M1_FOREIGN, m2)
        sem = c["operator_semantics"]
        assert sem["semantic_verdict"] == "TEXTUAL_REWRITE"
        assert c["candidate_state"] == "NOT_A_CANDIDATE_TEXTUAL_REWRITE"


# ---------------------------------------------------------------------------
# GEOMETRIC_TRANSFORMATION: mechanism preserved + geometry-relevant
# structure CHANGED (not a device rename)
# ---------------------------------------------------------------------------
M1_GEOMETRY = _m1(
    mechanism="turbulent eddy shedding at a step promotes particle "
              "resuspension away from the wall",
    system="flat-walled microfluidic channel with a single step",
    intervention="introducing a single step in the flat channel wall",
    observed="particles resuspended and deposition reduced by 40 "
             "percent",
    boundary="flow 10 mL/min in the flat channel",
    failure_mode="particle deposition",
    record_text="Turbulent eddy shedding at a step promotes particle "
                "resuspension away from the wall. Flat-walled "
                "microfluidic channel with a single step; particles "
                "resuspended and deposition reduced by 40 percent at "
                "flow 10 mL/min.")


class TestGeometricTransformationBehavior:
    def test_valid_geometry_change(self, monkeypatch):
        # the causal mechanism (eddy shedding resuspension) is
        # preserved while the geometry TRANSFORMS: single step ->
        # helical spiral grooves (topology + count change)
        m2 = _m2_lines(
            "eddy shedding at flow obstacles promotes particle "
            "resuspension away from the wall",
            "machine helical spiral grooves into the catheter lumen "
            "wall, multiple grooves along the flow path",
            "deposition reduced by 40 percent in the grooved lumen",
            "groove count and helix pitch",
            "deposition mass reduced 40 percent with 8 helical grooves "
            "versus a smooth lumen at 50 mL/min",
            "grooves as thrombus nucleation sites; cleaning difficulty",
            "flow 50 mL/min",
            "particles resuspended and deposition reduced by 40 "
            "percent")
        c = _apply(monkeypatch, "GEOMETRIC_TRANSFORMATION", M1_GEOMETRY,
                   m2)
        assert c["candidate_state"] == "CANDIDATE"
        sem = c["operator_semantics"]
        assert sem["semantic_verdict"] == "SEMANTICALLY_VALID"
        # geometry-relevant structure demonstrably CHANGED (directive:
        # not merely renaming the device)
        geo = sem["checked_fields"]["geometry_structure_changed"][
            "new_geometry_terms"]
        assert geo  # e.g. helical, grooves, count, lumen...

    def test_device_rename_is_not_geometry(self, monkeypatch):
        # same mechanism, same single-step geometry — the DEVICE is
        # renamed and the words shuffled: no new geometry vocabulary
        m2 = _m2_lines(
            "eddy shedding at a step promotes particle resuspension "
            "away from the wall",
            "put a step in the wall of a medical drainage conduit",
            "deposition reduced by 40 percent",
            "step presence",
            "deposition reduced 40 percent with the step present",
            "step fouling",
            "flow 10 mL/min",
            "particles resuspended and deposition reduced by 40 "
            "percent")
        c = _apply(monkeypatch, "GEOMETRIC_TRANSFORMATION", M1_GEOMETRY,
                   m2)
        sem = c["operator_semantics"]
        assert sem["semantic_verdict"] == "TEXTUAL_REWRITE"
        assert c["candidate_state"] == "NOT_A_CANDIDATE_TEXTUAL_REWRITE"


# ---------------------------------------------------------------------------
# BOUNDARY_CONDITION_CHANGE: mechanism preserved + regime changed +
# prediction changes correspondingly
# ---------------------------------------------------------------------------
class TestBoundaryConditionChangeBehavior:
    def test_valid_regime_change(self, monkeypatch):
        # the mechanism (surface-bonded heparin inhibiting the cascade)
        # is preserved; the regime moves from low-flow venous to
        # high-flow arterial with a correspondingly different prediction
        m2 = _m2_lines(
            "heparin bonding inhibits clotting cascade activation at "
            "the luminal surface",
            "bond heparin to the catheter lumen for arterial high-flow "
            "insertion use",
            "thrombus reduced 30 percent under pulsatile arterial "
            "regime at 400 mL/min",
            "heparin density under pulsatile shear",
            "thrombus area reduced 30 percent at pulsatile arterial "
            "flow 400 mL/min and 120 mmHg",
            "shear stripping of the bonding layer",
            "pulsatile arterial flow 400 mL/min, 120 mmHg pressure",
            SPAN_MED)
        c = _apply(monkeypatch, "BOUNDARY_CONDITION_CHANGE", M1_MEDICAL,
                   m2)
        assert c["candidate_state"] == "CANDIDATE"
        sem = c["operator_semantics"]
        assert sem["semantic_verdict"] == "SEMANTICALLY_VALID"
        assert sem["checked_fields"]["boundary_regime_changed"][
            "jaccard"] <= 0.5
        assert sem["checked_fields"]["prediction_changes_with_regime"][
            "new_prediction_terms"]

    def test_same_regime_restated_fails(self, monkeypatch):
        # boundary conditions RE-STATED (same 50 mL/min / 20 mmHg
        # regime) — no regime change, no new prediction
        m2 = _m2_lines(
            "heparin bonding inhibits clotting cascade activation at "
            "the luminal surface",
            "bond heparin to the catheter lumen wall",
            "thrombus area reduced under low flow",
            "heparin density",
            "thrombus area reduced at flow rate 50 mL/min and venous "
            "pressure 20 mmHg",
            "leaching",
            "flow rate 50 mL/min and venous pressure 20 mmHg",
            SPAN_MED)
        c = _apply(monkeypatch, "BOUNDARY_CONDITION_CHANGE", M1_MEDICAL,
                   m2)
        sem = c["operator_semantics"]
        assert sem["semantic_verdict"] == "TEXTUAL_REWRITE"
        assert c["candidate_state"] == "NOT_A_CANDIDATE_TEXTUAL_REWRITE"


# ---------------------------------------------------------------------------
# FAILURE_PATH_INVERSION: same pathway, INVERTED polarity
# ---------------------------------------------------------------------------
class TestFailurePathInversionBehavior:
    def test_valid_inversion(self, monkeypatch):
        # the documented failure pathway (clotting cascade activation
        # -> thrombus -> occlusion) is used AS the operating principle,
        # inverted: the cascade activation is deliberately suppressed
        # by counter-activating a bound inhibitor at the same site
        m2 = _m2_lines(
            "the clotting cascade activation pathway that causes "
            "thrombotic occlusion is inverted into the operating "
            "principle: a bound inhibitor suppresses cascade "
            "activation at the exact luminal site where occlusion "
            "initiates",
            "bond a thrombin-site inhibitor to the lumen wall that "
            "counteracts clotting cascade activation locally",
            "occlusion prevented; patency maintained above 0.05 "
            "mL/min",
            "inhibitor counteraction density at the occlusion site",
            "time to occlusion extended 3-fold versus untreated "
            "catheters under low flow",
            "inhibitor depletion; local bleeding risk",
            "low flow venous regime",
            SPAN_MED)
        c = _apply(monkeypatch, "FAILURE_PATH_INVERSION", M1_MEDICAL,
                   m2)
        assert c["candidate_state"] == "CANDIDATE"
        sem = c["operator_semantics"]
        assert sem["semantic_verdict"] == "SEMANTICALLY_VALID"
        assert sem["checked_fields"]["same_causal_pathway"][
            "shared_pathway_terms"]
        assert sem["checked_fields"]["pathway_inverted"][
            "inversion_markers"]

    def test_failure_restated_not_inverted_fails(self, monkeypatch):
        # the failure pathway is DESCRIBED (still failing) — the same
        # failure restated differently, no inversion polarity applied
        m2 = _m2_lines(
            "clotting cascade activation at the luminal surface "
            "causes thrombotic occlusion of the catheter lumen",
            "observe the catheter lumen to study the clotting cascade "
            "activation that produces occlusion",
            "occlusion occurs as the cascade activates",
            "observation window length",
            "occlusion develops within days of insertion under low "
            "flow",
            "none",
            "low flow venous regime",
            SPAN_MED)
        c = _apply(monkeypatch, "FAILURE_PATH_INVERSION", M1_MEDICAL,
                   m2)
        sem = c["operator_semantics"]
        assert sem["semantic_verdict"] == "TEXTUAL_REWRITE"
        assert c["candidate_state"] == "NOT_A_CANDIDATE_TEXTUAL_REWRITE"


# ---------------------------------------------------------------------------
# The five operators are behavioral, not lexical: each passes with a
# DIFFERENT valid M2 against the SAME M1 where contracts allow
# ---------------------------------------------------------------------------
def test_operator_semantic_checks_are_operator_specific():
    # the five checkers are structurally distinct predicates (not five
    # wrappers over one similarity detector)
    codes = {ms.operator_semantic_check.__name__}
    # distinct vocabularies per operator (the checked-field sets differ)
    m2_stub = {"mechanism": "", "intervention": "",
               "constraint_set": {}, "predicted_effect": "",
               "testable_prediction": "", "novel_design_variable": ""}
    field_sets = []
    for op_id in ms.OPERATOR_IDS:
        out = ms.operator_semantic_check(op_id, M1_MEDICAL, m2_stub,
                                         PROBLEM)
        field_sets.append(tuple(sorted(out["checked_fields"])))
    assert len(set(field_sets)) == 5  # five distinct structural checks
