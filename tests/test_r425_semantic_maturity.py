"""tests/test_r425_semantic_maturity.py — R425 §3 regression.

Maturity is SEMANTIC, not count-based:
  * deterministic content-quality gates per category (DI/DO/FM/VF/WP);
  * low-information records can NEVER upgrade the maturity level;
  * EXPERIMENT_READY requires an actual discriminating experiment
    contract, never the mere presence of a hypotheses array.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine.invention_bridge import (
    elite_package as _elite)
from discovery_fabric.engine.invention_bridge import epistemics as _ep

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "r418"


def _solar() -> dict:
    return json.loads((FIXTURES / "solar_result.json").read_text())


def _eng_proj(**over) -> dict:
    run = {
        "session_id": "ts_r425_sem",
        "final_state": {"final_status": "EVOLVED_INVENTION_CANDIDATE"},
        "engineering_specification": {
            "design_inputs": over.get("dis", [
                {"id": f"DI-{i:03d}", "input": f"input {i}",
                 "value": f"v{i}", "evidence_class": "MODELLED",
                 "evidence_refs": ["engineering_core"]}
                for i in range(1, 7)]),
            "design_outputs": over.get("dos", [
                {"id": f"DO-{i:03d}", "parent_ids": [f"DI-{i:03d}"],
                 "description": f"output {i}",
                 "missing_inputs": []} for i in range(1, 4)]),
            "failure_analysis": over.get("fms", [
                {"graph_id": f"FM-{i:03d}",
                 "failure_mode": f"mode {i}",
                 "severity": f"UNKNOWN (basis {i})",
                 "verification": f"VF-{i:03d}"}
                for i in range(1, 5)]),
            "verification_matrix": over.get("vfs", [
                {"id": f"VF-{i:03d}", "requirement": f"req {i}",
                 "method": f"method {i}", "result": "NOT_TESTED",
                 "acceptance": f"rule {i}",
                 "invention_tie": {"linkage_kind": "domain_check",
                                   "targets": [f"FM-{i:03d}"]}}
                for i in range(1, 5)]),
            "engineering_build_plan": over.get("wps", [
                {"work_package": f"WP-{i:02d}",
                 "test_article": f"article {i}",
                 "design_work": f"design {i}",
                 "equipment": f"equipment {i}"}
                for i in range(1, 6)]),
            "engineering_core": over.get("core", {}),
        },
        "invention_specification": over.get("inv", {
            "killer_experiment": {"value": {}}}),
        "run_state": {"generations": {"generations": []}},
        "decisive_experiment": over.get("de", {}),
    }
    return _elite.derive_engineering_projection(run), run


class TestSemanticGates:
    def test_complete_records_pass_their_gates(self):
        proj, _ = _eng_proj()
        sem = _elite.semantic_completeness(proj)
        for cat in ("design_inputs", "failure_modes",
                    "verification", "build_plan"):
            assert sem[cat]["low_information_excluded"] == 0, (cat, sem)

    def test_low_information_records_are_excluded_by_name(self):
        proj, _ = _eng_proj(
            dis=[{"id": f"DI-{i:03d}"} for i in range(1, 9)],
            fms=[{"graph_id": f"FM-{i:03d}",
                  "failure_mode": f"mode {i}"} for i in range(1, 9)],
            wps=[{"work_package": f"WP-{i:02d}"} for i in range(1, 9)])
        sem = _elite.semantic_completeness(proj)
        # every low-information record is excluded and the violation
        # is named — never a silent discount
        assert sem["design_inputs"][
            "records_semantically_complete"] == 0
        assert sem["failure_modes"]["records_semantically_complete"] == 0
        assert sem["build_plan"]["records_semantically_complete"] == 0
        for entry in sem["design_inputs"]["failed_records"][:3]:
            assert entry["violation"]
        assert sem["failure_modes"]["failed_records"][0][
            "violation"] == "no affected function/output and no " \
                            "explicit UNKNOWN"
        assert sem["build_plan"]["failed_records"][0][
            "violation"] == "no action"

    def test_duplicate_ids_fail_uniqueness(self):
        proj, _ = _eng_proj(
            fms=[{"graph_id": "FM-DUP", "failure_mode": "m",
                  "severity": "UNKNOWN (x)", "verification": "VF-1"},
                 {"graph_id": "FM-DUP", "failure_mode": "m",
                  "severity": "UNKNOWN (x)", "verification": "VF-1"}])
        sem = _elite.semantic_completeness(proj)
        assert sem["failure_modes"]["records_semantically_complete"] == 1
        assert any(f["violation"] == "duplicate id"
                   for f in sem["failure_modes"]["failed_records"])


class TestSemanticMaturity:
    def test_low_information_quantity_cannot_upgrade(self):
        """R425 §3's central clause: an arbitrary quantity of
        low-information records must not upgrade maturity. 8 bare DIs +
        8 bare FMs + 8 bare WPs with ENGINEERING class still EARLY."""
        proj, _ = _eng_proj(
            dis=[{"id": f"DI-{i:03d}"} for i in range(1, 9)],
            fms=[{"graph_id": f"FM-{i:03d}",
                  "failure_mode": f"mode {i}"} for i in range(1, 9)],
            wps=[{"work_package": f"WP-{i:02d}"} for i in range(1, 9)])
        assert _elite.build_maturity(proj, True) == \
            _ep.PACKAGE_MATURITY_EARLY

    def test_complete_records_earn_engineering_definition(self):
        proj, _ = _eng_proj()
        assert _elite.build_maturity(proj, True) == \
            _ep.PACKAGE_MATURITY_ENGINEERING

    def test_solar_record_stays_early(self):
        proj = _elite.derive_engineering_projection(_solar())
        assert _elite.build_maturity(proj, False) == \
            _ep.PACKAGE_MATURITY_EARLY


class TestExperimentContract:
    def _contract_proj(self, ke_hyps=None, vf_acceptance=True,
                       selected_by_loop=True):
        vfs = [{
            "id": "VF-001", "requirement": "req",
            "method": "compare against baseline",
            "result": "NOT_TESTED",
            "acceptance": ("pre-registered margin from the measured "
                           "baseline") if vf_acceptance else None,
            "invention_tie": {"linkage_kind": "falsification_test",
                              "targets": ["FM-001"]}}]
        ke = {"selected": "falsification_test",
              "definition": "bench experiment",
              "hypotheses": ke_hyps if ke_hyps is not None else [
                  {"name": "H_effect_holds", "description": "holds",
                   "prior_probability": 0.6},
                  {"name": "H_effect_fails", "description": "fails",
                   "prior_probability": 0.4}]}
        proj, run = _eng_proj(vfs=vfs, inv={"killer_experiment":
                                            {"value": ke}})
        if not selected_by_loop:
            run = dict(run)
            run["decisive_experiment"] = {}
        proj = _elite.derive_engineering_projection(run)
        return proj, run

    def test_full_contract_grants_experiment_ready(self):
        proj, run = self._contract_proj()
        assert _elite.build_maturity(proj, True, run) == \
            "EXPERIMENT_READY"

    def test_hypotheses_array_alone_does_not_grant_ready(self):
        """R425 §3: EXPERIMENT_READY requires an actual discriminating
        contract, NOT merely the presence of a hypotheses array."""
        proj, run = self._contract_proj(vf_acceptance=False)
        level = _elite.build_maturity(proj, True, run)
        assert level == _ep.PACKAGE_MATURITY_ENGINEERING
        contract = _elite.experiment_contract_assessment(proj, run)
        assert contract["requirements"][
            "pre_registered_decision_rule"] is False
        assert contract["discriminating"] is False

    def test_priors_missing_blocks_ready(self):
        proj, run = self._contract_proj(ke_hyps=[
            {"name": "H_effect_holds", "description": "holds"},
            {"name": "H_effect_fails", "description": "fails"}])
        contract = _elite.experiment_contract_assessment(proj, run)
        assert contract["requirements"][
            "at_least_two_hypothesis_arms_with_priors"] is False
        assert _elite.build_maturity(proj, True, run) == \
            _ep.PACKAGE_MATURITY_ENGINEERING

    def test_unresolved_target_blocks_ready(self):
        # the VF targets an FM id that does not exist in the record
        proj, run = self._contract_proj()
        for v in proj["verification"]:
            v["invention_tie"]["targets"] = ["FM-NOPE"]
        contract = _elite.experiment_contract_assessment(proj, run)
        assert contract["requirements"]["target_resolves_in_record"] \
            is False
        assert _elite.build_maturity(proj, True, run) == \
            _ep.PACKAGE_MATURITY_ENGINEERING

    def test_basis_is_recorded_per_requirement(self):
        proj, run = self._contract_proj()
        contract = _elite.experiment_contract_assessment(proj, run)
        for name, ok in contract["requirements"].items():
            assert isinstance(ok, bool), name
        assert contract["hypothesis_arms"]
        assert contract["decision_rule"]["source"].startswith(
            "verification_matrix")


class TestMaturityBasisCarriesSemantics:
    def _contract_proj(self):
        vfs = [{
            "id": "VF-001", "requirement": "req",
            "method": "compare against baseline",
            "result": "NOT_TESTED",
            "acceptance": "pre-registered margin from the measured "
                          "baseline",
            "invention_tie": {"linkage_kind": "falsification_test",
                              "targets": ["FM-001"]}}]
        ke = {"selected": "falsification_test",
              "definition": "bench experiment",
              "hypotheses": [
                  {"name": "H_effect_holds", "description": "holds",
                   "prior_probability": 0.6},
                  {"name": "H_effect_fails", "description": "fails",
                   "prior_probability": 0.4}]}
        proj, run = _eng_proj(vfs=vfs, inv={"killer_experiment":
                                            {"value": ke}})
        proj = _elite.derive_engineering_projection(run)
        return proj, run

    def test_basis_records_the_semantic_report(self):
        proj, run = self._contract_proj()
        mb = _elite.build_maturity_basis(
            proj, "x", "EXPERIMENT_READY", run)
        assert mb["semantic_gates"]["counts_semantically_complete"]
        assert mb["semantic_gates"]["categories"]
        assert mb["experiment_contract"]["discriminating"] is True
        assert "discriminating experiment contract" in mb["honesty"]

    def test_solar_basis_lists_low_information_exclusions(self):
        proj = _elite.derive_engineering_projection(_solar())
        mb = _elite.build_maturity_basis(
            proj, "x", _ep.PACKAGE_MATURITY_EARLY)
        cats = mb["semantic_gates"]["categories"]
        assert cats["design_inputs"]["records_total"] >= 10
        # the report is honest about whatever it found
        assert (cats["design_inputs"]["records_semantically_complete"]
                + cats["design_inputs"]["low_information_excluded"]
                == cats["design_inputs"]["records_total"])
