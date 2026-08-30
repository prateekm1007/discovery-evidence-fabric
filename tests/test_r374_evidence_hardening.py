"""
test_r374_evidence_hardening.py — R374 adversarial test suite.

Constitution basis:
  Art. V     — positive AND negative AND metamorphic cases
  Art. VIII  — certification must attack itself
  Art. XVI   — code is a hypothesis; tests are evidence of enforcement
  Art. XVII  — every control has an attempted bypass
  Art. XXX   — never optimize the evaluator: EVERY R374 check must be
               provably able to FAIL when the underlying artifact is wrong

Covers the seven R374 dimensions: traceability truth model, equation
three-level status, source-backed units, diagram element proofs, the
failed-candidate pathway, the forbidden-language rules and the
acceptance-gate wiring. Negative tests tamper COPIES of real data
(never the shipped files — Art. IX).
"""

import copy
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..")))

from premium_package_factory.r371.canonical_source import load_all_packages
from premium_package_factory.r371.equations import build_equation_registry
from premium_package_factory.r372.equation_validation import validate_registry
from premium_package_factory.r374 import (
    equation_status, traceability_truth, diagram_proof, pathway,
)

PACKAGES = load_all_packages()
BY_ID = {p.pkg_id: p for p in PACKAGES}
P01 = BY_ID["P-01"]
PORTFOLIO = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "portfolio"))


def _registry(pid="P-01"):
    p = BY_ID[pid]
    reg = build_equation_registry(p)
    reg["r372_validation"] = validate_registry(reg, p)
    return reg, p


def _shipped_traceability(pid="P-01"):
    folder = BY_ID[pid].folder
    with open(os.path.join(PORTFOLIO, "DOWNLOAD", folder,
                           "ENGINEERING_TRACEABILITY.json"),
              encoding="utf-8") as f:
        return json.load(f)


# ===========================================================================
# R374-2: equation three-level validation status
# ===========================================================================

class TestEquationLevels:

    def test_real_registry_levels_computed(self):
        reg, p = _registry()
        reg = equation_status.attach_r374_status(reg, p)
        st = reg["r374_validation_status"]
        assert st["totals"]["equations"] == len(reg["equations"])
        assert st["totals"]["applicability_validated"] == \
            st["totals"]["equations"]  # metadata complete for all
        # the honest reality: dimensional validation proven for 0
        assert st["totals"]["dimensionally_validated"] == 0
        assert st["totals"]["dimensional_not_evaluable"] + \
            st["totals"]["dimensionally_inconsistent"] == \
            st["totals"]["equations"]

    def test_dimensional_level_never_proven_by_structure(self):
        """An equation whose dimensional state is NOT_EVALUABLE must
        report dimensional_validation.proven == False — the exact
        semantic promotion R374-2 forbids."""
        reg, p = _registry()
        reg = equation_status.attach_r374_status(reg, p)
        for eq in reg["r374_validation_status"]["equations"]:
            state = eq["dimensional_validation"]["state"]
            proven = eq["dimensional_validation"]["proven"]
            assert proven == (state == "DIMENSIONALLY_CONSISTENT"), \
                f"level/state disagreement: {state} vs proven={proven}"

    def test_structural_level_follows_parse(self):
        """Structural proven iff the canonical string parses; a prose
        string is honestly NOT structurally validated."""
        assert equation_status._structural_check(
            "Q = (pi * r^4 * dP) / (8 * eta * L)", None)["proven"] is True
        assert equation_status._structural_check(
            "flow proportional to conductance trend", None)["proven"] \
            is False
        assert equation_status._structural_check(
            "x = 1", "CORRUPTED_CANONICAL_STRING_RENDERED_VERBATIM")[
            "proven"] is False

    def test_level_totals_recompute_identically(self):
        """Metamorphic: attaching twice yields identical totals."""
        reg, p = _registry()
        a = equation_status.attach_r374_status(reg, p)["r374_validation_status"]
        reg2, _ = _registry()
        b = equation_status.attach_r374_status(reg2, p)["r374_validation_status"]
        assert a["totals"] == b["totals"]

    def test_inconsistent_equation_reports_inconsistent(self):
        """A dimensionally inconsistent equation must be reported as
        inconsistent, never as validated at the dimensional level."""
        entry = {"equation_id": "EQ-X", "math_expression": "F = m + a",
                 "variables": []}
        validation = {
            "domain": "d", "operating_regime": ["r"], "assumptions": ["a"],
            "applicability": ["b"], "limitations": ["l"],
            "source": {"origin": "t"},
            "dimensional_check": {
                "state": "DIMENSIONALLY_INCONSISTENT",
                "reason": "test injection"}}
        levels = equation_status.equation_levels(entry, validation)
        assert levels["dimensional_validation"]["proven"] is False
        assert levels["dimensional_validation"]["state"] == \
            "DIMENSIONALLY_INCONSISTENT"
        assert "DIMENSIONAL_VALIDATION" not in levels["levels_proven"]


class TestBareValidatedLanguage:

    def test_the_r372_defect_phrase_is_caught(self):
        """The exact defect R374-2 corrects: the old R372 gate label."""
        text = ("66/66 equation validation (66 validated, "
                "0 inconsistent)")
        assert equation_status.bare_validated_claims(text), \
            "the old unqualified claim must be flagged"

    def test_level_qualified_claim_passes(self):
        text = ("66/66 equation validation records complete: STRUCTURAL "
                "52, APPLICABILITY 66, DIMENSIONAL 0 — levels reported "
                "separately")
        assert equation_status.bare_validated_claims(text) == []

    def test_schema_identifiers_do_not_trigger(self):
        text = ('"schema": "R372_EQUATION_VALIDATION", '
                '"dimensional_state_counts": {...}')
        assert equation_status.bare_validated_claims(text) == []

    def test_bare_count_claim_caught(self):
        assert "66 validated" in equation_status.bare_validated_claims(
            "the run finished with 66 validated and 0 problems")


# ===========================================================================
# R374-3: source-backed units
# ===========================================================================

class TestUnitStatus:

    def test_units_split_source_backed_vs_unknown(self):
        reg, p = _registry()
        reg = equation_status.attach_r374_status(reg, p)
        statuses = set()
        for e in reg["equations"]:
            for row in e["r374_unit_status"]:
                statuses.add(row["unit_status"])
                if row["unit_status"] == "SOURCE_BACKED":
                    assert row["unit_source"]["recorded_parameter"]
                    assert row["unit"]
                else:
                    assert row["resolution_path"]
                    assert row["unit"] is None
        assert statuses <= {"SOURCE_BACKED", "UNKNOWN"}
        # P-01 honestly carries both classes
        assert statuses == {"SOURCE_BACKED", "UNKNOWN"}

    def test_source_backed_unit_exists_in_canonical_record(self):
        """No invented units: every SOURCE_BACKED unit string must be a
        recorded critical-parameter unit of the package."""
        reg, p = _registry()
        reg = equation_status.attach_r374_status(reg, p)
        recorded = {cp.get("unit") for cp in p.critical_parameters
                    if cp.get("unit")}
        for e in reg["equations"]:
            for row in e["r374_unit_status"]:
                if row["unit_status"] == "SOURCE_BACKED":
                    assert row["unit"] in recorded, \
                        f"invented unit {row['unit']!r}"

    def test_unrecorded_symbol_is_unknown_not_guessed(self):
        """Standard-symbol conventions are never used (Art. VI): a
        symbol with no recorded unit stays UNKNOWN even when its
        conventional unit is 'obvious' (eta -> Pa*s)."""
        reg, p = _registry()
        reg = equation_status.attach_r374_status(reg, p)
        eta_rows = [row for e in reg["equations"]
                    for row in e["r374_unit_status"]
                    if row["symbol"] in ("eta", "Q", "dP")]
        assert eta_rows
        for row in eta_rows:
            if not any(cp.get("unit") and row["symbol"] in
                       (cp.get("name") or "")
                       for cp in p.critical_parameters):
                assert row["unit_status"] == "UNKNOWN"
                assert "eta" not in (row.get("unit") or "")

    def test_unknown_resolution_path_names_the_symbol(self):
        reg, p = _registry()
        reg = equation_status.attach_r374_status(reg, p)
        for e in reg["equations"]:
            for row in e.get("r374_unit_status", []):
                if row["unit_status"] == "UNKNOWN":
                    assert row["symbol"] in row["resolution_path"]
                    assert "critical_parameters" in row["resolution_path"]


# ===========================================================================
# R374-1: traceability truth model
# ===========================================================================

class TestTruthModel:

    def test_real_shipped_file_passes(self):
        shipped = _shipped_traceability()
        assert traceability_truth.audit_truth_model(
            shipped, P01)["ok"] is True

    def test_every_chain_carries_four_state_and_reason(self):
        shipped = _shipped_traceability()
        for chain in shipped["chains"]:
            assert chain["chain_state_r374"] in (
                "EXPLICIT", "PARTIAL", "UNKNOWN", "NOT_APPLICABLE")
            assert chain["chain_state_reason_r374"]

    def test_unknown_chain_never_counts_as_explicit(self):
        """UNKNOWN is not verified traceability: a file with 10 UNKNOWN
        chains must report 10 UNKNOWN — never folded into EXPLICIT."""
        shipped = _shipped_traceability()
        counts = shipped["truth_model"]["chain_state_counts_r374"]
        assert counts["UNKNOWN"] + counts["PARTIAL"] + \
            counts["EXPLICIT"] + counts["NOT_APPLICABLE"] == \
            len(shipped["chains"])
        assert shipped["truth_model"][
            "unknown_is_not_verified_traceability"] is True

    def test_missing_truth_model_block_fails(self):
        shipped = _shipped_traceability()
        del shipped["truth_model"]
        r = traceability_truth.audit_truth_model(shipped, P01)
        assert not r["ok"]
        assert any(f["check"] == "TRUTH_MODEL_BLOCK_MISSING"
                   for f in r["failures"])

    def test_tampered_counts_fail(self):
        shipped = _shipped_traceability()
        shipped["truth_model"]["chain_state_counts_r374"]["UNKNOWN"] = 0
        r = traceability_truth.audit_truth_model(shipped, P01)
        assert any(f["check"] == "TRUTH_MODEL_COUNT_MISMATCH"
                   for f in r["failures"])

    def test_unjustified_unknown_slot_fails(self):
        shipped = _shipped_traceability()
        for chain in shipped["chains"]:
            if chain["chain_state_r374"] == "UNKNOWN":
                del chain["slots"]["design_output"]["justification"]
                break
        r = traceability_truth.audit_truth_model(shipped, P01)
        assert any(f["check"] == "NON_EXPLICIT_SLOT_WITHOUT_JUSTIFICATION"
                   for f in r["failures"])

    def test_release_gate_overclaim_fails(self):
        shipped = _shipped_traceability()
        shipped["release_gate"]["reason"] = (
            "All design inputs are traced; the graph is fully traceable "
            "and complete.")
        r = traceability_truth.audit_truth_model(shipped, P01)
        assert any(f["check"] == "RELEASE_GATE_OVERCLAIM"
                   for f in r["failures"])

    def test_overclaim_scan_catches_and_negation_passes(self):
        assert traceability_truth.traceability_overclaims(
            "The portfolio is fully traceable across all packages.")
        assert traceability_truth.traceability_overclaims(
            "complete traceability of every chain")
        assert not traceability_truth.traceability_overclaims(
            "The portfolio is NOT fully traceable; 10 chains are UNKNOWN.")
        assert not traceability_truth.traceability_overclaims(
            "Traceability is incomplete by honest classification.")


# ===========================================================================
# R374-4: diagram element proofs
# ===========================================================================

class TestDiagramProofs:

    @staticmethod
    def _mech_audit(**over):
        base = {
            "mechanism_identity_coverage":
                {"headline_mechanism": 1.0, "system_description": 0.8},
            "subsystems_depicted": 4,
            "subsystems_not_depicted_disclosed": [],
            "mechanism_central_omitted": [],
            "directional_arrows": 18,
            "critical_parameter_labels": 24,
            "untraced_labels": [],
        }
        base.update(over)
        return base

    @staticmethod
    def _spec():
        return {
            "diagram_elements": ["Comp A", "Comp B", "Comp C", "Comp D"],
            "relationships": [
                "Comp A -> Comp B (flow)",
                "Comp B -> Comp C (signal)",
                "Comp C -> Comp D (feedback)",
            ],
        }

    def _proof(self, **over):
        return diagram_proof.mechanism_diagram_proof(
            P01, None, {"mechanism": "m"},
            self._mech_audit(**over), self._spec())

    def test_all_five_elements_proven_on_wellformed_spec(self):
        r = self._proof()
        assert r["all_elements_proven"] is True
        assert set(r["proofs"]) == {"canonical_mechanism", "components",
                                    "interfaces", "directionality",
                                    "critical_parameters"}

    def test_dropped_relationship_kills_interfaces(self):
        spec = self._spec()
        spec["relationships"] = spec["relationships"][:2]  # 2 interfaces
        r = diagram_proof.mechanism_diagram_proof(
            P01, None, {"mechanism": "m"}, self._mech_audit(), spec)
        assert r["proofs"]["interfaces"]["proven"] is False
        assert r["all_elements_proven"] is False

    def test_chain_relationship_counts_as_interfaces(self):
        """A single chain A -> B -> C -> D carries 3 interfaces."""
        spec = self._spec()
        spec["relationships"] = ["Comp A -> Comp B -> Comp C -> Comp D"]
        r = diagram_proof.mechanism_diagram_proof(
            P01, None, {"mechanism": "m"}, self._mech_audit(), spec)
        assert r["proofs"]["interfaces"]["proven"] is True

    def test_abbreviated_segment_names_map(self):
        spec = {
            "diagram_elements": ["Passive RFID tag (catheter tip)",
                                 "External wearable reader",
                                 "Clinical display"],
            "relationships": [
                "RFID tag -> Wearable reader (backscatter)",
                "Reader -> Clinical display (position)",
            ],
        }
        pairs = diagram_proof._interface_pairs(
            spec["relationships"], spec["diagram_elements"])
        assert len(pairs) >= 2

    def test_mechanism_central_omission_kills_components(self):
        r = self._proof(mechanism_central_omitted=["Bayesian predictor"])
        assert r["proofs"]["components"]["proven"] is False

    def test_untraced_label_kills_critical_parameters(self):
        r = self._proof(untraced_labels=["made up 42 mmHg"])
        assert r["proofs"]["critical_parameters"]["proven"] is False

    def test_low_identity_coverage_kills_canonical_mechanism(self):
        r = self._proof(mechanism_identity_coverage={
            "headline_mechanism": 0.3, "system_description": 0.2})
        assert r["proofs"]["canonical_mechanism"]["proven"] is False

    def test_missing_arrows_kill_directionality(self):
        r = self._proof(directional_arrows=1)
        assert r["proofs"]["directionality"]["proven"] is False


class TestExperimentProofs:

    @staticmethod
    def _audit(roles):
        return {
            "expected_roles": roles,
            "failures": [],
            "ok": True,
        }

    ROLES = {
        "test_article": "V0 bench prototype",
        "stimulus": "obstruction scenarios",
        "control_variables": "recorded critical parameters",
        "instrumentation": "flow loop + sensors",
        "measured_outputs": "per-segment flow + ICP",
        "decision_criterion": "prediction lead time >= 24h",
        "decision_consequence": "IF ACCEPTANCE MET -> deliver; IF KILL "
                                "CONDITION MET -> stop",
        "kill_condition": "dual-invariant falsified",
    }

    def test_seven_elements_plus_kill_condition(self):
        r = diagram_proof.experiment_diagram_proof(
            P01, {}, self._audit(self.ROLES))
        assert r["all_elements_proven"] is True
        assert len(r["elements_required"]) == 7

    def test_tampered_role_kills_its_element(self):
        audit = self._audit(self.ROLES)
        audit["failures"] = [{"check": "ROLE_NOT_CANONICAL:test_article",
                              "detail": "mismatch"}]
        r = diagram_proof.experiment_diagram_proof(P01, {}, audit)
        assert r["proofs"]["test_article"]["proven"] is False
        assert "test_article" in r["unproven_elements"]

    def test_missing_kill_condition_disclosed(self):
        roles = dict(self.ROLES)
        roles["kill_condition"] = ""
        r = diagram_proof.experiment_diagram_proof(
            P01, {}, self._audit(roles))
        assert r["proofs"]["kill_condition_(pathway_R374_6)"][
            "proven"] is False


# ===========================================================================
# R374-6: failed-candidate pathway
# ===========================================================================

class TestPathway:

    @pytest.fixture()
    def cemetery(self):
        with open(os.path.join(
                os.path.dirname(__file__), "..",
                "MECHANISM_CEMETERY", "CEMETERY.json"),
                encoding="utf-8") as f:
            return json.load(f)

    def test_legacy_migration_completes_all_entries(self, cemetery):
        cem = copy.deepcopy(cemetery)
        pathway.migrate_cemetery(cem)
        for e in cem["entries"]:
            r = pathway.audit_entry_pathway(e)
            assert r["complete"], f"{e['entry_id']}: {r['problems']}"

    def test_migration_preserves_original_fields(self, cemetery):
        cem = copy.deepcopy(cemetery)
        before = copy.deepcopy(cem["entries"])
        pathway.migrate_cemetery(cem)
        for old, new in zip(before, cem["entries"]):
            for k, v in old.items():
                assert new[k] == v, f"{old['entry_id']}.{k} changed"

    def test_migration_is_idempotent(self, cemetery):
        cem1 = copy.deepcopy(cemetery)
        pathway.migrate_cemetery(cem1)
        snap = json.dumps(cem1, sort_keys=True)
        pathway.migrate_cemetery(cem1)
        assert json.dumps(cem1, sort_keys=True) == snap

    def test_legacy_attack_results_marked_not_structured(self, cemetery):
        """Legacy entries without structured attack results are marked
        NOT_STRUCTURED honestly — never fabricated (Art. VI)."""
        cem = copy.deepcopy(cemetery)
        pathway.migrate_cemetery(cem)
        legacy = next(e for e in cem["entries"]
                      if not e.get("attack_results"))
        ar = legacy["pathway"]["ATTACK_RESULTS"]
        assert ar["state"] == "NOT_STRUCTURED"
        assert "not fabricated" in ar["reason"] or \
            "not restructured" in ar["reason"]

    def test_legacy_kill_condition_marked_derived(self, cemetery):
        cem = copy.deepcopy(cemetery)
        pathway.migrate_cemetery(cem)
        legacy = next(e for e in cem["entries"]
                      if not e.get("kill_condition"))
        kc = legacy["pathway"]["KILL_CONDITION"]
        assert kc["value"]
        assert "re-presented" in kc["derivation"]

    def test_entry_without_kill_condition_fails_audit(self):
        entry = {
            "entry_id": "CE-X", "territory_id": "T-X",
            "mechanism_name": "m", "kill_reason": None,
            "why_it_failed": None, "evidence_sources": [],
            "pathway": pathway.entry_pathway(
                {"entry_id": "CE-X", "territory_id": "T-X",
                 "mechanism_name": "m"}),
        }
        r = pathway.audit_entry_pathway(entry)
        assert not r["complete"]
        assert "KILL_CONDITION absent" in r["problems"]
        assert "EVIDENCE absent" in r["problems"]

    def test_deleted_entry_detected_as_append_only_violation(self):
        """Nothing is deleted: the append-only audit logic flags a
        cemetery that lost an entry between git revisions (removed ids
        non-empty -> nothing_deleted False -> audit not ok). Functional
        core exercised through audit_cemetery on a temp engine root
        with real git history (engine repo has one)."""
        engine_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), ".."))
        with open(os.path.join(engine_root, "MECHANISM_CEMETERY",
                               "CEMETERY.json"), encoding="utf-8") as f:
            real = json.load(f)
        cur = copy.deepcopy(real)
        cur["entries"] = cur["entries"][:-1]  # simulate a deletion
        pathway.migrate_cemetery(cur)  # must NOT re-chain (laundering-safe)
        audit = pathway.audit_cemetery(cur, engine_root)
        # 2026-08-30 STRENGTHENED (Art. XXXI, machinery reference:
        # pathway._chain_backfill/_chain_verify — internal hash chain):
        # git-count comparison could not detect deletion of UNCOMMITTED
        # entries (found live when the 6-domain benchmark legitimately
        # grew the cemetery between commits); the internal chain detects
        # ANY deletion regardless of growth or commit state.
        assert audit["append_only"]["internal_chain"]["valid"] is False
        assert audit["append_only"]["nothing_deleted"] is False
        assert audit["ok"] is False

    def test_new_pathway_entry_is_structurally_complete(self):
        e = pathway.new_pathway_entry(
            entry_id="CE-TEST", territory_id="T", mechanism_name="m",
            proposed_version="V1", kill_reason="PHYSICS_CEILING",
            why_it_failed=["x"],
            evidence_sources=["EV.json"],
            attack_results={"state": "STRUCTURED", "value": {"a": 1}},
            kill_condition="dead if X")
        r = pathway.audit_entry_pathway(e)
        assert r["complete"], r["problems"]
        assert e["pathway"]["ATTACK_RESULTS"]["state"] == "STRUCTURED"
        assert e["pathway"]["KILL_CONDITION"][
            "derivation"] == "recorded structured field"

    def test_all_six_elements_defined(self):
        assert set(pathway.PATHWAY_ELEMENTS) == {
            "CANDIDATE", "FAILURE_REASON", "EVIDENCE", "ATTACK_RESULTS",
            "KILL_CONDITION", "CEMETERY"}


# ===========================================================================
# R374-2/3 wiring: registry audit cross-check
# ===========================================================================

class TestEquationStatusAudit:

    def test_real_shipped_registry_passes(self):
        from premium_package_factory.r374.run_r374_audit import \
            audit_equation_status
        with open(os.path.join(PORTFOLIO, "DOWNLOAD", P01.folder,
                               "EQUATION_REGISTRY.json"),
                  encoding="utf-8") as f:
            shipped = json.load(f)
        r = audit_equation_status(P01, shipped)
        assert r["ok"], r["failures"]

    def test_tampered_totals_detected(self):
        from premium_package_factory.r374.run_r374_audit import \
            audit_equation_status
        with open(os.path.join(PORTFOLIO, "DOWNLOAD", P01.folder,
                               "EQUATION_REGISTRY.json"),
                  encoding="utf-8") as f:
            shipped = json.load(f)
        shipped["r374_validation_status"]["totals"][
            "dimensionally_validated"] = 4  # the over-claim injection
        r = audit_equation_status(P01, shipped)
        assert not r["ok"]
        assert any(f["check"] == "TOTALS_MISMATCH" for f in r["failures"])

    def test_removed_unit_table_detected(self):
        from premium_package_factory.r374.run_r374_audit import \
            audit_equation_status
        with open(os.path.join(PORTFOLIO, "DOWNLOAD", P01.folder,
                               "EQUATION_REGISTRY.json"),
                  encoding="utf-8") as f:
            shipped = json.load(f)
        shipped["equations"][0]["r374_unit_status"] = []
        r = audit_equation_status(P01, shipped)
        assert not r["ok"]

    def test_missing_status_block_detected(self):
        from premium_package_factory.r374.run_r374_audit import \
            audit_equation_status
        with open(os.path.join(PORTFOLIO, "DOWNLOAD", P01.folder,
                               "EQUATION_REGISTRY.json"),
                  encoding="utf-8") as f:
            shipped = json.load(f)
        del shipped["r374_validation_status"]
        r = audit_equation_status(P01, shipped)
        assert not r["ok"]
        assert r["failures"][0]["check"] == "R374_STATUS_MISSING"


# ===========================================================================
# R374-5: deterministic ZIP containers
# ===========================================================================

class TestDeterministicZips:

    def test_zip_reproducible_across_mtime_changes(self, tmp_path):
        """The R374-5 defect: zipfile's default embeds file mtimes, so
        identical content produced ZIPs with different bytes. Fixed
        epoch entries must reproduce byte-identically even when the
        source file mtimes change between builds."""
        import time
        import zipfile as zf_mod
        from premium_package_factory.r371.build_v5 import _zip_add
        src = tmp_path / "a.txt"
        src.write_text("identical content")
        z1, z2 = tmp_path / "one.zip", tmp_path / "two.zip"
        with zf_mod.ZipFile(z1, "w", zf_mod.ZIP_DEFLATED) as zf:
            _zip_add(zf, str(src), "a.txt")
        # change the source mtime (simulating a rebuild at another time)
        later = time.time() + 3600
        os.utime(src, (later, later))
        with zf_mod.ZipFile(z2, "w", zf_mod.ZIP_DEFLATED) as zf:
            _zip_add(zf, str(src), "a.txt")
        assert z1.read_bytes() == z2.read_bytes(), \
            "ZIP container not byte-reproducible across mtime changes"

    def test_default_zipfile_write_is_non_deterministic_control(self, tmp_path):
        """Negative control proving the test above is meaningful: the
        DEFAULT zf.write() path IS mtime-dependent (the defect class)."""
        import time
        import zipfile as zf_mod
        src = tmp_path / "a.txt"
        src.write_text("identical content")
        z1, z2 = tmp_path / "one.zip", tmp_path / "two.zip"
        with zf_mod.ZipFile(z1, "w", zf_mod.ZIP_DEFLATED) as zf:
            zf.write(str(src), "a.txt")
        later = time.time() + 3600
        os.utime(src, (later, later))
        with zf_mod.ZipFile(z2, "w", zf_mod.ZIP_DEFLATED) as zf:
            zf.write(str(src), "a.txt")
        assert z1.read_bytes() != z2.read_bytes()
