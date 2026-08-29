"""
test_r373_independent_audit.py — R373 adversarial test suite.

Constitution basis:
  Art. V     — positive AND negative AND metamorphic cases
  Art. VIII  — certification must attack itself
  Art. XVI   — code is a hypothesis; tests are evidence of enforcement
  Art. XVII  — every control has an attempted bypass
  Art. XXX   — never optimize the evaluator: EVERY audit check must be
               provably able to FAIL when the underlying artifact is wrong

Covers the seven R373 audit dimensions. Each negative test tampers a copy
of real data (never the shipped files — Art. IX observational discipline)
and asserts the audit catches it.
"""

import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..")))

from premium_package_factory.r371.canonical_source import load_all_packages
from premium_package_factory.r373 import (
    audit_diagrams, audit_traceability, audit_equations,
    audit_unknowns, audit_v2_propagation, state_ladder,
)

PACKAGES = load_all_packages()
BY_ID = {p.pkg_id: p for p in PACKAGES}
P01 = BY_ID["P-01"]


class _FakeRecording:
    """Minimal stand-in for the diagram recording harness."""

    def __init__(self, labels, arrows):
        self._labels = labels
        self.arrows = arrows

    def labels(self):
        return list(self._labels)


def _real_recording(pid):
    import tempfile
    from premium_package_factory.diagrams import factory as df
    from premium_package_factory.r372.diagram_adequacy import record_diagram
    df.OUTPUT_DIR = tempfile.mkdtemp()
    return record_diagram(lambda: _funcs()[pid]())


_FUNCS = None


def _funcs():
    global _FUNCS
    if _FUNCS is None:
        from premium_package_factory.diagrams import factory as df
        _FUNCS = {
            "P-01": df.diagram_P01, "P-02": df.diagram_P02,
            "P-04": df.diagram_P04, "P-07": df.diagram_P07,
            "P-11": df.diagram_P11, "P-13": df.diagram_P13,
            "P-15-R1": df.diagram_P15R1, "P-16": df.diagram_P16,
            "P-21-R1": df.diagram_P21R1, "P-22-R1": df.diagram_P22R1,
            "P-24": df.diagram_P24, "P-26": df.diagram_P26,
            "P-27-R1": df.diagram_P27R1, "P-28": df.diagram_P28,
            "P-29": df.diagram_P29,
        }
    return _FUNCS


def _headline(pid):
    h = json.load(open(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "premium_package_factory", "input", "headlines_r371.json"),
        encoding="utf-8"))
    return next(r for r in h["packages"] if r["package_id"] == pid)


_FREQ = None


def _freq():
    global _FREQ
    if _FREQ is None:
        _FREQ = audit_diagrams.portfolio_token_frequencies(PACKAGES)
    return _FREQ


# ---------------------------------------------------------------------------
# R373-1 mechanism diagram semantic audit — positive + negatives
# ---------------------------------------------------------------------------

class TestMechanismDiagramAudit:
    def test_real_p01_passes(self):
        rec = _real_recording("P-01")
        r = audit_diagrams.audit_mechanism_diagram(
            P01, rec, _headline("P-01"), _freq(), set())
        assert r["ok"], r["failures"]

    def test_alien_token_fails(self):
        """A label carrying another package's signature mechanism
        vocabulary (the RFID-in-the-UWB-diagram class) must fail."""
        rec = _real_recording("P-01")
        alien_labels = list(rec.labels()) + ["RFID backscatter uplink"]
        fake = _FakeRecording(alien_labels, rec.arrows)
        r = audit_diagrams.audit_mechanism_diagram(
            P01, fake, _headline("P-01"), _freq(), {"rfid"})
        assert not r["ok"]
        assert any(f["check"] == "ALIEN_MECHANISM" for f in r["failures"])

    def test_untraced_label_fails(self):
        rec = _FakeRecording(
            ["Multi-segment catheter", "Bayesian occlusion predictor",
             "Alpha controller", "Per-segment flow sensors",
             "Zorpatron manifold assembly"],
            [((0, 0), (1, 0)), ((1, 0), (2, 0)), ((2, 0), (3, 0))])
        r = audit_diagrams.audit_mechanism_diagram(
            P01, rec, _headline("P-01"), _freq(), set())
        assert any(f["check"] == "LABEL_PROVENANCE" for f in r["failures"])

    def test_invented_number_fails(self):
        rec = _FakeRecording(
            ["Multi-segment catheter", "Bayesian occlusion predictor",
             "Alpha controller", "Per-segment flow sensors",
             "Achievable flow rate: 9999.5 mL/min"],
            [((0, 0), (1, 0)), ((1, 0), (2, 0)), ((2, 0), (3, 0))])
        r = audit_diagrams.audit_mechanism_diagram(
            P01, rec, _headline("P-01"), _freq(), set())
        assert any(f["check"] == "NO_INVENTED_NUMBERS" for f in r["failures"])

    def test_missing_mechanism_statement_fails(self):
        """A diagram that never states the canonical mechanism must fail
        the identity check."""
        rec = _FakeRecording(
            ["Block A", "Block B", "Block C", "Sensor X", "Param Y"],
            [((0, 0), (1, 0)), ((1, 0), (2, 0)), ((2, 0), (3, 0))])
        r = audit_diagrams.audit_mechanism_diagram(
            P01, rec, _headline("P-01"), _freq(), set())
        assert any(f["check"] == "MECHANISM_IDENTITY" for f in r["failures"])

    def test_too_few_subsystems_fails(self):
        rec = _FakeRecording(
            ["Multi-segment catheter", "Q_prod", "P_ICP"],
            [((0, 0), (1, 0)), ((1, 0), (2, 0)), ((2, 0), (3, 0))])
        r = audit_diagrams.audit_mechanism_diagram(
            P01, rec, _headline("P-01"), _freq(), set())
        assert any(f["check"] == "SUBSYSTEMS_DEPICTED" for f in r["failures"])

    def test_too_few_directional_arrows_fails(self):
        rec = _FakeRecording(
            ["Multi-segment catheter", "Bayesian occlusion predictor",
             "Alpha controller", "Per-segment flow sensors"],
            [((0, 0), (0, 0)), ((1, 0), (1, 0))])
        r = audit_diagrams.audit_mechanism_diagram(
            P01, rec, _headline("P-01"), _freq(), set())
        assert any(f["check"] == "INTERFACES_DIRECTIONALITY"
                   for f in r["failures"])


# ---------------------------------------------------------------------------
# R373-2 experiment diagram audit
# ---------------------------------------------------------------------------

class TestExperimentDiagramAudit:
    def _spec(self, pkg):
        from premium_package_factory.r372.diagram_adequacy import (
            experiment_diagram_spec)
        return experiment_diagram_spec(pkg, _headline(pkg.pkg_id))

    def test_real_specs_pass(self):
        for p in PACKAGES:
            r = audit_diagrams.audit_experiment_spec(
                self._spec(p), p, _headline(p.pkg_id))
            assert r["ok"], (p.pkg_id, r["failures"])

    def test_tampered_test_article_fails(self):
        spec = json.loads(json.dumps(self._spec(P01)))
        spec["roles"]["test_article"]["content"] = "Invented test article"
        r = audit_diagrams.audit_experiment_spec(
            spec, P01, _headline("P-01"))
        assert any("ROLE_NOT_CANONICAL:test_article" in f["check"]
                   for f in r["failures"])

    def test_missing_decision_consequence_fails(self):
        spec = json.loads(json.dumps(self._spec(P01)))
        del spec["roles"]["decision_consequence"]
        r = audit_diagrams.audit_experiment_spec(
            spec, P01, _headline("P-01"))
        assert any("decision_consequence" in f["check"]
                   for f in r["failures"])

    def test_proposed_marker_is_canonical_form(self):
        """A package whose WP-01 has no next step must carry the explicit
        PROPOSED marker — the CEO's 'or be explicitly PROPOSED' rule."""
        spec = audit_diagrams.expected_experiment_roles(P01, _headline("P-01"))
        assert "IF ACCEPTANCE MET" in spec["decision_consequence"]
        assert "IF KILL CONDITION MET" in spec["decision_consequence"]


# ---------------------------------------------------------------------------
# R373-3 traceability recomputation
# ---------------------------------------------------------------------------

class TestTraceabilityAudit:
    def _shipped(self, pid):
        fp = os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))),
            "portfolio", "DOWNLOAD",
            f"{_folder(pid)}", "ENGINEERING_TRACEABILITY.json")
        return json.load(open(fp, encoding="utf-8"))

    def test_real_all_pass(self):
        for p in PACKAGES:
            r = audit_traceability.audit_package(p, self._shipped(p.pkg_id))
            assert r["ok"], (p.pkg_id, r["failures"])

    def test_dropped_justification_fails(self):
        """linked=false + passed=true without explanation is the
        forbidden state: stripping a justification must fail the audit."""
        shipped = json.loads(json.dumps(self._shipped("P-01")))
        for c in shipped["chains"]:
            for slot in c["slots"].values():
                if slot.get("justification"):
                    slot["justification"]["data_basis"] = None
        r = audit_traceability.audit_package(P01, shipped)
        assert any(f["check"] == "UNJUSTIFIED_INCOMPLETE_SLOT"
                   for f in r["failures"])

    def test_summary_drift_fails(self):
        shipped = json.loads(json.dumps(self._shipped("P-01")))
        shipped["summary"]["explicitly_linked"] = 99
        r = audit_traceability.audit_package(P01, shipped)
        assert any(f["check"] == "SUMMARY_DRIFT" for f in r["failures"])

    def test_gate_without_explanation_fails(self):
        shipped = json.loads(json.dumps(self._shipped("P-01")))
        shipped["release_gate"]["incomplete_parts_explicitly_justified"] = \
            False
        r = audit_traceability.audit_package(P01, shipped)
        assert any(f["check"] == "PASSED_WITHOUT_EXPLANATION"
                   for f in r["failures"])

    def test_legacy_unmarked_fails(self):
        shipped = json.loads(json.dumps(self._shipped("P-01")))
        if shipped.get("legacy_r370_record"):
            shipped["legacy_r370_record"]["legacy_note"] = None
            r = audit_traceability.audit_package(P01, shipped)
            assert any(f["check"] == "LEGACY_NOT_MARKED_SUPERSEDED"
                       for f in r["failures"])


def _folder(pid):
    return {p.pkg_id: p.folder for p in PACKAGES}[pid]


# ---------------------------------------------------------------------------
# R373-4 equation audit + adversarial injections
# ---------------------------------------------------------------------------

class TestEquationAudit:
    def _shipped(self, pid):
        fp = os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))),
            "portfolio", "DOWNLOAD", _folder(pid), "EQUATION_REGISTRY.json")
        return json.load(open(fp, encoding="utf-8"))

    def test_real_all_pass(self):
        for p in PACKAGES:
            r = audit_equations.audit_registry(p, self._shipped(p.pkg_id))
            assert r["ok"], (p.pkg_id, r["failures"])

    def test_wrong_regime_injection_caught(self):
        """A fabricated operating regime must be flagged by the
        verbatim-canonical comparison (run through audit_registry)."""
        inj = audit_equations.adversarial_injections(PACKAGES)
        assert inj["wrong_regime"]["caught"]

    def test_wrong_variable_injection_caught(self):
        inj = audit_equations.adversarial_injections(PACKAGES)
        assert inj["wrong_variable"]["caught"]
        assert inj["wrong_variable"]["validator_state"] == \
            "NOT_EVALUABLE_UNITS_UNRECORDED"

    def test_wrong_unit_injection_caught(self):
        """A dimension-changing wrong unit on a consistent baseline must
        flip the validator out of CONSISTENT (synthetic fixture is
        disclosed because 0/66 real equations carry complete units)."""
        inj = audit_equations.adversarial_injections(PACKAGES)
        assert inj["wrong_unit_all_caught"]
        syn = [r for r in inj["wrong_unit_probes"]
               if r["baseline"] == "SYNTHETIC"]
        assert syn and syn[0]["baseline_state"] == "DIMENSIONALLY_CONSISTENT"
        assert syn[0]["wrong_unit"]["tampered_state"] == \
            "DIMENSIONALLY_INCONSISTENT"

    def test_tampered_dimensional_state_fails(self):
        shipped = json.loads(json.dumps(self._shipped("P-01")))
        shipped["r372_validation"]["validations"][0]["dimensional_check"][
            "state"] = "DIMENSIONALLY_CONSISTENT"
        r = audit_equations.audit_registry(P01, shipped)
        assert any("DIMENSIONAL_STATE_DRIFT" in f["check"]
                   for f in r["failures"])

    def test_invented_variable_declaration_fails(self):
        shipped = json.loads(json.dumps(self._shipped("P-01")))
        shipped["equations"][0]["variables"].append(
            {"symbol": "Zq9", "recorded_name": "invented", "unit": "mm"})
        r = audit_equations.audit_registry(P01, shipped)
        assert any("VARIABLES_NOT_THE_RECORDED_UNIVERSE" in f["check"]
                   for f in r["failures"])


# ---------------------------------------------------------------------------
# R373-6 unknowns audit
# ---------------------------------------------------------------------------

class TestUnknownsAudit:
    def _shipped(self, pid):
        fp = os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))),
            "portfolio", "DOWNLOAD", _folder(pid), "UNKNOWN_ROADMAP.json")
        return json.load(open(fp, encoding="utf-8"))

    def test_real_all_pass(self):
        for p in PACKAGES:
            r = audit_unknowns.audit_unknowns(p, self._shipped(p.pkg_id))
            assert r["ok"], (p.pkg_id, r["failures"])

    def test_dropped_unknown_fails(self):
        """UNKNOWNs may never be reduced to increase the release score."""
        shipped = json.loads(json.dumps(self._shipped("P-01")))
        shipped["unknowns"] = shipped["unknowns"][:-1]
        r = audit_unknowns.audit_unknowns(P01, shipped)
        assert any(f["check"] in ("COUNT_NOT_PRESERVED", "UNKNOWN_DROPPED")
                   for f in r["failures"])

    def test_missing_field_fails(self):
        shipped = json.loads(json.dumps(self._shipped("P-01")))
        shipped["unknowns"][0].pop("why_unknown")
        r = audit_unknowns.audit_unknowns(P01, shipped)
        assert any(f["check"] == "FIELD_MISSING" for f in r["failures"])

    def test_classification_inflation_fails(self):
        """Converting an unresolved unknown to an easier class to inflate
        the release score must be caught by mechanical re-derivation."""
        shipped = json.loads(json.dumps(self._shipped("P-01")))
        for u in shipped["unknowns"]:
            if u["classification"] == "FUNDAMENTALLY_UNRESOLVED":
                u["classification"] = "LITERATURE_RESOLVABLE"
                break
        r = audit_unknowns.audit_unknowns(P01, shipped)
        assert any(f["check"] == "CLASSIFICATION_DRIFT"
                   for f in r["failures"])


# ---------------------------------------------------------------------------
# R373-8 state ladder — six separate states, never collapsed
# ---------------------------------------------------------------------------

class TestStateLadder:
    def test_six_states_present_and_separate(self):
        lad = state_ladder.build_ladder(
            P01, document_complete=True, engineering_evaluable=True,
            transfer_evaluable=True)
        assert set(lad["states"].keys()) == {
            "DOCUMENT_COMPLETE", "ENGINEERING_EVALUABLE",
            "TRANSFER_EVALUABLE", "PHYSICALLY_VALIDATED",
            "EXTERNALLY_VALIDATED", "TRANSFER_READY"}
        # no WORLD_CLASS collapse
        assert "WORLD_CLASS" not in json.dumps(lad)

    def test_artifact_gate_passes_without_physical(self):
        lad = state_ladder.build_ladder(
            P01, document_complete=True, engineering_evaluable=True,
            transfer_evaluable=True)
        assert lad["release_gate"] == "PASS"
        assert not lad["states"]["PHYSICALLY_VALIDATED"]["met"]
        assert not lad["states"]["EXTERNALLY_VALIDATED"]["met"]
        assert not lad["states"]["TRANSFER_READY"]["met"]

    def test_physical_state_is_derived_not_asserted(self):
        """PHYSICALLY_VALIDATED derives from PHYSICAL_OBSERVATION
        evidence origins only (Art. XXXVIII)."""
        class _FakeClaims:
            pass

        fake = type("FakePkg", (), {})()
        fake.pkg_id, fake.num = "P-TEST", "00"
        fake.claims = [{"evidence_origin": "SOURCE_NATIVE"},
                       {"evidence_origin": "PHYSICAL_OBSERVATION"}]
        n = state_ladder.physical_observation_count(fake)
        assert n == 1
        fake.claims = [{"evidence_origin": "SOURCE_NATIVE"},
                       {"evidence_origin": "COMPUTATIONALLY_GENERATED"}]
        assert state_ladder.physical_observation_count(fake) == 0

    def test_failed_artifact_states_fail_gate(self):
        lad = state_ladder.build_ladder(
            P01, document_complete=True, engineering_evaluable=False,
            transfer_evaluable=True)
        assert lad["release_gate"] == "FAIL"


# ---------------------------------------------------------------------------
# R373-5 V2 propagation — v1-source classification unit rules
# ---------------------------------------------------------------------------

class TestV1SourceClassification:
    def test_verbatim_canonical(self):
        src = audit_v2_propagation.classify_v1_source(
            "Catheter obstruction causes 30-50% of shunt failures",
            "x Catheter obstruction causes 30-50% of shunt failures y", "")
        assert src["v1_source_type"] == "VERBATIM_CANONICAL"

    def test_verbatim_v1_release(self):
        src = audit_v2_propagation.classify_v1_source(
            "No real failure dataset exists to train the model",
            "", "y No real failure dataset exists to train the model z")
        assert src["v1_source_type"] == "VERBATIM_V1_RELEASE"

    def test_additive_placeholder(self):
        src = audit_v2_propagation.classify_v1_source(
            "(No explicit feasibility risk disclosure in V1 dossier)", "", "")
        assert src["v1_source_type"] == "ADDITIVE_PLACEHOLDER"

    def test_untraceable_fails(self):
        src = audit_v2_propagation.classify_v1_source(
            "Completely invented v1 text", "", "")
        assert src["v1_source_type"] == "V1_SOURCE_UNTRACEABLE"


# ---------------------------------------------------------------------------
# full-runner positive case (slow; runs the real audit)
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestFullRunner:
    def test_r373_audit_all_pass_on_real_release(self):
        from premium_package_factory.r373 import run_r373_audit
        root = os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))), "portfolio")
        if not os.path.isdir(root):
            pytest.skip("portfolio repo not present")
        audit = run_r373_audit.run_r373_audit(root)
        for pid, r in audit["packages"].items():
            assert r["state_ladder"]["release_gate"] == "PASS", pid
        assert audit["adversarial_injections"]["all_caught"]
        assert audit["totals"]["physically_validated"] == 0
        assert audit["totals"]["transfer_ready"] == 0
