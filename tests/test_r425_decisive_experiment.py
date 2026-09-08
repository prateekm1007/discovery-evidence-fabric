"""tests/test_r425_decisive_experiment.py — R425 §5 regression.

The package's decisive-experiment layer is a BUYER-RUNNABLE contract:
14 fields, each either derived from the canonical state or emitted as
NOT_DEFINED_IN_CANONICAL_STATE with the exact provenance basis — never
invented values, never generic filler such as 'further testing
required'.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine.invention_bridge import (
    elite_package as _elite)
from discovery_fabric.engine.invention_bridge import (
    package as _pkg)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "r418"

FIELDS = ("experiment_id", "hypothesis", "intervention",
          "baseline_control", "test_article", "measurable_variables",
          "apparatus_instrumentation", "procedure", "acceptance_rule",
          "falsification_rule", "expected_discriminating_outcomes",
          "dependencies", "safety_operational_constraints",
          "decision_mapping", "next_technical_state_transition")


def _solar() -> dict:
    return json.loads((FIXTURES / "solar_result.json").read_text())


def _layer(run=None):
    run = run or _solar()
    proj = _elite.derive_engineering_projection(run)
    return _pkg._decisive_experiment_layer(
        proj, run.get("session_id", "ts_x"), run)


class TestContractShape:
    def test_all_fields_present_with_basis(self):
        layer = _layer()
        assert layer["schema"] == "R425_DECISIVE_EXPERIMENT_CONTRACT"
        contract = layer["contract"]
        for f in FIELDS:
            assert f in contract, f"missing contract field {f}"
            entry = contract[f]
            assert entry["status"] in (
                "DEFINED", "NOT_DEFINED_IN_CANONICAL_STATE"), f
            assert entry["provenance_basis"], f

    def test_defined_fields_carry_canonical_values(self):
        run = _solar()
        layer = _layer(run)
        c = layer["contract"]
        eng = run.get("engineering_specification") or {}
        wp = (eng.get("engineering_build_plan") or [])[0]
        # test article is the RECORDED work-package article, verbatim
        assert c["test_article"]["value"] == wp["test_article"]
        assert c["test_article"]["provenance_basis"].startswith(
            "engineering_build_plan")
        # hypotheses carry the recorded arms
        hyps = c["hypothesis"]["value"]
        names = {h["name"] for h in hyps}
        assert "H_effect_holds" in names and "H_effect_fails" in names
        # measurable variables are the recorded critical parameters
        cps = (eng.get("engineering_core") or {}).get(
            "critical_parameters") or []
        assert c["measurable_variables"]["value"][0][
            "parameter_id"] == cps[0]["parameter_id"]

    def test_gap_field_is_not_defined_with_exact_basis(self):
        layer = _layer()
        bc = layer["contract"]["baseline_control"]
        assert bc["value"] == "NOT_DEFINED_IN_CANONICAL_STATE"
        assert bc["status"] == "NOT_DEFINED_IN_CANONICAL_STATE"
        # the basis names the record inspected (VF prose, no structured
        # arm field) — the exact provenance basis the directive demands
        assert "verification_matrix" in bc["provenance_basis"]
        assert "no structured baseline_arm" in bc["provenance_basis"]

    def test_no_generic_filler_prose(self):
        blob = json.dumps(_layer()).lower()
        for phrase in ("further testing required",
                       "additional studies needed",
                       "more research is required"):
            assert phrase not in blob

    def test_decision_mapping_uses_recorded_action(self):
        run = _solar()
        layer = _layer(run)
        dm = layer["contract"]["decision_mapping"]["value"]
        assert dm["next_best_action"] == \
            run["final_state"]["next_best_action"]

    def test_next_state_transition_from_record(self):
        run = _solar()
        layer = _layer(run)
        nt = layer["contract"]["next_technical_state_transition"][
            "value"]
        assert nt["current_state"] == run["final_state"]["evolution"][
            "current_invention"]["state"]

    def test_completeness_accounting(self):
        layer = _layer()
        cc = layer["contract_completeness"]
        assert cc["fields_total"] == len(FIELDS)
        assert (cc["fields_defined_in_canonical_state"]
                + cc["fields_not_defined"] == cc["fields_total"])
        assert "baseline_control" in cc["not_defined_fields"]


class TestWeakRecordHonesty:
    def test_empty_record_all_gaps_typed(self):
        """A record with nothing experiment-shaped yields ALL fields
        NOT_DEFINED_IN_CANONICAL_STATE — each still carrying its
        provenance basis; nothing is invented (the honest weak case)."""
        run = {
            "session_id": "ts_weak",
            "final_state": {},
            "engineering_specification": {},
            "invention_specification": {},
            "decisive_experiment": {},
        }
        layer = _layer(run)
        for f in FIELDS:
            entry = layer["contract"][f]
            assert entry["value"] in (
                "NOT_DEFINED_IN_CANONICAL_STATE",
                None), f
            assert entry["provenance_basis"], f
        assert layer["contract_completeness"][
            "fields_defined_in_canonical_state"] == 0

    def test_killer_experiment_values_never_invented(self):
        """Kill probability stays the recorded UNKNOWN string; the
        falsification arm is the recorded H_effect_fails hypothesis."""
        run = _solar()
        layer = _layer(run)
        fr = layer["contract"]["falsification_rule"]["value"]
        assert fr["kill_arm"]["name"] == "H_effect_fails"
        sel = run["decisive_experiment"]["selected"]
        assert fr["kill_probability"] == sel["kill_probability"]
        assert "UNKNOWN" in str(fr["kill_probability"])
