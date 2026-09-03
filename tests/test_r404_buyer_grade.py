"""R404 — BUYER-GRADE VERIFICATION TESTS.

Constitutional anchors under attack (Art. XVII):
- Art. III   the recorded VALID claims are not trusted; the geometry
             gates were re-executed on fresh rebuilds
- Art. VI/XXV nothing manufactured; UNKNOWN stays UNKNOWN; the canonical
             buyer figure for P08 is UNKNOWN, not 1050, not 121
- Art. XXVIII no silent promotion: simulation is never measurement
- Art. XXXI  the R403 audit's own error is pinned (so is the frozen
             dossier's wrong lineage narrative — the defect is pinned
             until the release-chain fixes it)
- Art. XI    P14 untouched; history preserved
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPO = Path(__file__).resolve().parents[1]
LP4 = REPO / "LEAD_PORTFOLIO_4"
LEAD = ["P04", "P08", "P11", "P13"]

R403_COMMIT = "135fd74f2506f5456330377fa9557a740f89917b"

CLASSIFICATION_STATES = {
    "P04": "READY_FOR_TECHNICAL_EVALUATION",
    "P08": "REQUIRES_ENGINEERING_REPAIR",
    "P11": "READY_FOR_SPONSORED_VALIDATION",
    "P13": "REQUIRES_EVIDENCE_REPAIR",
}
FIVE_STATES = {
    "READY_FOR_TECHNICAL_EVALUATION", "READY_FOR_SPONSORED_VALIDATION",
    "REQUIRES_EVIDENCE_REPAIR", "REQUIRES_ENGINEERING_REPAIR", "KILLED",
}


def load(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 16), b""):
            h.update(blk)
    return h.hexdigest()


# --------------------------------------------------------------------------
# 1. Independent geometry re-verification (directive item 5)
# --------------------------------------------------------------------------

class TestGeometryReverification(unittest.TestCase):
    def test_evidence_file_and_four_packages(self):
        ev = load(LP4 / "GEOMETRY_REVERIFICATION_EVIDENCE.json")
        self.assertEqual(set(ev["packages"].keys()), set(LEAD))
        for desig in LEAD:
            base = ev["packages"][desig]["base_model"]
            self.assertTrue(base["geometry_validation_valid"],
                            f"{desig} base geometry failed fresh re-run")
            gates = base["gate_statuses"]
            for g, s in gates.items():
                self.assertIn(s, ("SATISFIED", "SUPPORTED", "UNVERIFIABLE"),
                              f"{desig} gate {g}={s} on fresh rebuild")

    def test_p04_kill_reproduces_and_conclusion(self):
        ev = load(LP4 / "GEOMETRY_REVERIFICATION_EVIDENCE.json")
        loop = ev["packages"]["P04"]["improvement_loop_rerun"]
        self.assertEqual(loop["outcome"], "KILLED_GEOMETRY_INVALID")
        self.assertIn("G4", json.dumps(loop.get("child_gate_reasons")))
        block = ev["p04_directive_block"]
        for field in ("FAILED_MUTATION", "CURRENT_GEOMETRY",
                      "GEOMETRY_EVIDENCE", "ENGINEERING_CONCLUSION"):
            self.assertIn(field, block)
        self.assertIn("INDEPENDENTLY CONFIRMED",
                      block["ENGINEERING_CONCLUSION"])
        # the shipped base's measured wall on the fresh rebuild
        self.assertEqual(
            ev["packages"]["P04"]["base_model"]["key_measurements"][
                "dual_lumen_catheter.min_wall_thickness_mm"], 0.2)

    def test_key_measured_quantities_match_records(self):
        ev = load(LP4 / "GEOMETRY_REVERIFICATION_EVIDENCE.json")
        # P08 receiver area: pi*(7/2)^2 = 38.4845 mm2
        area = ev["packages"]["P08"]["improvement_loop_rerun"][
            "kept_child_receiver_area_mm2"]
        self.assertTrue(math.isclose(area, 38.4845, rel_tol=1e-4), area)
        # P11 damping gap mutation 0.3 -> 0.18 (KEEP)
        self.assertIn(
            "0.3 -> 0.18",
            ev["packages"]["P11"]["improvement_loop_rerun"]["outcome_reason"])
        # P13 diaphragm mutation 0.12 -> 0.07 (KEEP)
        self.assertIn(
            "0.12 -> 0.07",
            ev["packages"]["P13"]["improvement_loop_rerun"]["outcome_reason"])

    def test_p04_geometry_separation_references_reverification(self):
        gs = load(LP4 / "P04" / "GEOMETRY_SEPARATION.json")
        self.assertIn("independent_reverification_r404", gs)
        self.assertIn("INDEPENDENTLY CONFIRMED",
                      gs["independent_reverification_r404"]
                      ["ENGINEERING_CONCLUSION"])
        self.assertIn("NOT physical validation",
                      gs["independent_reverification_r404"]
                      ["ENGINEERING_CONCLUSION"])


# --------------------------------------------------------------------------
# 2. P08 verification-evidence restoration + canonical budget (items 2/4)
# --------------------------------------------------------------------------

class TestP08VerificationEvidence(unittest.TestCase):
    def test_provenance_and_hashes(self):
        p = LP4 / "P08" / "VERIFICATION_EVIDENCE"
        prov = load(p / "RESTORATION_PROVENANCE.json")
        self.assertEqual(len(prov["files"]), 5)
        for f in prov["files"]:
            fp = REPO / f["restored_to"]
            self.assertTrue(fp.exists(), f["restored_to"])
            self.assertEqual(sha256_file(fp), f["sha256"],
                             f"sha256 drift in {f['restored_to']}")
        # source commits are real history
        for f in prov["files"]:
            self.assertIn(f["source_commit"],
                          ("e3b6adfd", "35514d0a", "f01ae2d1"))

    def test_preregistration_binding_inside_artifacts(self):
        # the result files cite their preregistrations by sha256-first16;
        # both preregistration files are restored — the hashes must bind
        p = LP4 / "P08" / "VERIFICATION_EVIDENCE"
        r2 = load(p / "R310" / "P-16_VERIF-002_RESULT.json")
        pre2 = sha256_file(p / "R310" / "P-16_VERIF-002_PREREGISTRATION.json")
        self.assertEqual(r2["preregistration_sha256_first16"],
                         pre2[:16])
        r3 = load(p / "R311" / "P-16_VERIF-003_RESULT.json")
        pre3 = sha256_file(p / "R311" / "P-16_VERIF-003_PREREGISTRATION.json")
        self.assertEqual(r3["preregistration_sha256_first16"],
                         pre3[:16])

    def test_the_1050_field_name_records_its_own_assumptions(self):
        r2 = load(LP4 / "P08" / "VERIFICATION_EVIDENCE" / "R310" /
                  "P-16_VERIF-002_RESULT.json")
        self.assertIn("verified_power_output_uW_assuming_1cm2_PV_100pct_"
                      "conversion", r2["converged_result"])
        self.assertTrue(math.isclose(
            r2["converged_result"]
            ["verified_power_output_uW_assuming_1cm2_PV_100pct_conversion"],
            1049.054, rel_tol=1e-4))


class TestCanonicalEnergyBudget(unittest.TestCase):
    def _budget(self):
        return load(LP4 / "P08" / "ENERGY_BUDGET.json")

    def test_every_chain_number_has_the_five_fields(self):
        b = self._budget()
        for stage in b["chain"]:
            for field in ("value", "unit", "source", "evidence_class",
                          "calculation"):
                self.assertIn(field, stage,
                              f"stage '{stage['stage']}' missing {field}")

    def test_canonical_calculation_inputs_and_arithmetic(self):
        b = self._budget()
        cc = b["canonical_calculation"]
        self.assertEqual(cc["formula"],
                         "P_electrical = Phi_det × A_receiver × eta_cell")
        for inp in cc["inputs"]:
            for field in ("symbol", "name", "value", "unit", "source",
                          "evidence_class", "calculation"):
                self.assertIn(field, inp)
        # A_receiver = pi*(3.5)^2 mm2 = 0.384845 cm2
        area = [i for i in cc["inputs"] if i["symbol"] == "A_receiver"][0]
        self.assertTrue(math.isclose(area["value"], 0.384845, rel_tol=1e-6))
        # eta_cell is UNKNOWN (value None)
        eta = [i for i in cc["inputs"] if i["symbol"] == "eta_cell"][0]
        self.assertIsNone(eta["value"])
        # derived conditional values recompute
        for dv in cc["derived_conditional_values"]:
            # parse the condition's Phi from the calculation string
            calc = dv["calculation"]
            phi = float(calc.split("×")[0].strip())
            got = phi * 0.384845 * 0.30 * 1000
            self.assertTrue(math.isclose(got, dv["value"], rel_tol=1e-3),
                            (calc, got, dv["value"]))

    def test_canonical_figure_is_unknown_not_a_number(self):
        b = self._budget()
        fig = b["canonical_calculation"]["canonical_figure_for_buyer_package"]
        self.assertEqual(fig["deliverable_electrical_power"], "UNKNOWN")
        self.assertIn("never as system output", fig["basis"])

    def test_reconciliation_resolves_the_contradiction(self):
        b = self._budget()
        rec = b["canonical_calculation"]["the_reconciliation"]
        self.assertIn("RESOLVED", rec["resolution"])
        self.assertIn("1.0 cm² × 100 %", rec["resolution"])
        self.assertTrue(math.isclose(
            rec["the_reported_1050"]["value"], 1049.054, rel_tol=1e-4))
        self.assertTrue(math.isclose(
            rec["the_reported_121"]["value"], 121.0, rel_tol=1e-2))
        # D1 resolved / D2 open
        d1 = [x for x in b["derived_discrepancies"] if x.startswith("D1")][0]
        self.assertIn("RESOLVED", d1)
        d2 = [x for x in b["derived_discrepancies"] if x.startswith("D2")][0]
        self.assertIn("OPEN", d2)

    def test_fluence_stage_class_corrected_to_archived(self):
        b = self._budget()
        stage3 = [s for s in b["chain"] if s["stage"].startswith("3.")][0]
        self.assertIn("COMPUTATIONAL_RESULT_ARCHIVED", stage3["evidence_class"])
        self.assertNotIn("ASSERTED_NOT_ARCHIVED", stage3["evidence_class"])

    def test_r403_error_disclosed(self):
        b = self._budget()
        self.assertIn("WRONG", b["r403_audit_error_disclosure"])
        self.assertIn("Art. XV/XXXI", b["r403_audit_error_disclosure"])

    def test_p08_dependent_records_agree(self):
        bs = load(LP4 / "P08" / "BUYER_SEQUENCE.json")
        self.assertIn("RECONCILED", bs["sections"]["4_mechanism"])
        self.assertIn("ARCHIVED", bs["sections"]["5_evidence"])
        self.assertIn("121-163", bs["sections"]["5_evidence"])
        ts = load(LP4 / "P08" / "TRANSFER_STATE.json")
        self.assertIn("RESTORED", ts["current_state_basis"])
        self.assertIn("D2", ts["blocking_items_before_SUPPORTED_FOR_VALIDATION"][0])
        voi = load(LP4 / "P08" / "VALUE_OF_INFORMATION.json")
        self.assertIn("RESOLVED", voi["dominant_uncertainty"])


# --------------------------------------------------------------------------
# 3. P13 lineage audit (directive item 7)
# --------------------------------------------------------------------------

class TestP13LineageAudit(unittest.TestCase):
    def test_five_directive_fields(self):
        la = load(LP4 / "P13" / "LINEAGE_AUDIT.json")
        for field in ("predecessor", "failure", "causal_implication",
                      "new_architecture", "remaining_uncertainty"):
            self.assertIn(field, la)

    def test_predecessor_is_p25_not_p27(self):
        la = load(LP4 / "P13" / "LINEAGE_AUDIT.json")
        self.assertIn("P-25", la["predecessor"]["identity"])
        self.assertIn("CAND-002", la["predecessor"]["identity"])

    def test_failure_facts_pinned(self):
        la = load(LP4 / "P13" / "LINEAGE_AUDIT.json")
        joined = json.dumps(la["failure"])
        self.assertIn("3.45", joined)
        self.assertIn("67.8", joined)
        self.assertIn("biofouling", joined.lower())
        self.assertIn("NON-COMMON-MODE", joined)
        self.assertIn("R347", joined)

    def test_governance_gap_disclosed(self):
        la = load(LP4 / "P13" / "LINEAGE_AUDIT.json")
        self.assertIn("GOVERNANCE GAP", la["new_architecture"]["governance_gap"])
        self.assertIn("DC-P-25-001", la["new_architecture"]["governance_gap"])

    def test_frozen_dossier_wrong_narrative_is_pinned(self):
        """The buyer-surface defect is REAL and machine-pinned: the frozen
        dossier still carries the mis-attributed lineage narrative and
        zero biofouling mentions — until the release chain fixes it."""
        from premium_package_factory.r371.canonical_source import load_dossier
        d = load_dossier("P-27-R1")
        s = json.dumps(d, default=str)
        self.assertIn("original P-27 suffered from chronic drift", s)
        self.assertEqual(s.lower().count("biofouling"), 0)
        # ... and the engine-side correction exists
        la = load(LP4 / "P13" / "LINEAGE_AUDIT.json")
        self.assertIn("original P-27 suffered from chronic drift",
                      la["lineage_narrative_mis_attribution"]
                      ["frozen_dossier_claim"])
        self.assertIn("ZERO mentions", la["lineage_narrative_mis_attribution"]
                      ["biofouling_erasure"])

    def test_directive_answer_both_hands(self):
        la = load(LP4 / "P13" / "LINEAGE_AUDIT.json")
        ans = la["directive_answer"]
        self.assertIn("NO", ans["does_the_predecessor_failure_kill_P13"])
        self.assertIn("PARTIALLY disappeared", ans["has_it_disappeared"])


# --------------------------------------------------------------------------
# 4. Claim-evidence matrices + decision chains (items 9/10)
# --------------------------------------------------------------------------

class TestMatricesAndChains(unittest.TestCase):
    def test_matrix_rows_have_all_six_fields(self):
        for desig in LEAD:
            m = load(LP4 / desig / "CLAIM_EVIDENCE_MATRIX.json")
            self.assertGreaterEqual(len(m["rows"]), 6, desig)
            for row in m["rows"]:
                for field in ("claim", "source", "evidence_class",
                              "verification", "unknown", "experiment"):
                    self.assertIn(field, row, (desig, row.get("claim")))

    def test_matrix_unknowns_stay_unknown(self):
        for desig in LEAD:
            m = load(LP4 / desig / "CLAIM_EVIDENCE_MATRIX.json")
            for row in m["rows"]:
                self.assertNotIn("VERIFIED", row["unknown"])
                self.assertNotIn("ESTABLISHED", row["unknown"])

    def test_decision_chain_six_elements(self):
        for desig in LEAD:
            dc = load(LP4 / desig / "DECISION_CHAIN.json")
            for field in ("current_maturity", "next_experiment",
                          "expected_information_gain", "evidence_required",
                          "commercial_state_after_PASS",
                          "commercial_state_after_FAIL"):
                self.assertIn(field, dc["chain"], (desig, field))

    def test_chains_agree_with_classification(self):
        for desig in LEAD:
            dc = load(LP4 / desig / "DECISION_CHAIN.json")
            fc = load(LP4 / "FINAL_CLASSIFICATION.json")
            st = fc["classifications"][desig]["state"]
            # the chain's fail path must never contradict the package
            # being alive (only KILLED packages carry dead fail paths)
            if st != "KILLED":
                self.assertNotIn("cemetery first",
                                 dc["chain"]["commercial_state_after_FAIL"])


# --------------------------------------------------------------------------
# 5. Final classification (item 12) + P14 separation (item 11)
# --------------------------------------------------------------------------

class TestFinalClassification(unittest.TestCase):
    def test_one_of_five_states_per_package(self):
        fc = load(LP4 / "FINAL_CLASSIFICATION.json")
        self.assertEqual(set(fc["classifications"].keys()), set(LEAD))
        for desig, entry in fc["classifications"].items():
            self.assertIn(entry["state"], FIVE_STATES)
            self.assertGreaterEqual(len(entry["deciding_facts"]), 3, desig)

    def test_classification_values_pinned(self):
        fc = load(LP4 / "FINAL_CLASSIFICATION.json")
        for desig, want in CLASSIFICATION_STATES.items():
            self.assertEqual(fc["classifications"][desig]["state"], want)

    def test_manifest_carries_classification(self):
        mf = load(REPO / "LEAD_PORTFOLIO_4_MANIFEST.json")
        for entry in mf["lead_packages"]:
            self.assertEqual(
                entry["final_classification_r404"],
                CLASSIFICATION_STATES[entry["company_designation"]])

    def test_p14_record_unchanged_vs_r403_blob(self):
        p = LP4 / "P14" / "P14_EXTERNAL_DISTRIBUTION_RECORD.json"
        blob = subprocess.run(
            ["git", "-C", str(REPO), "show",
             f"{R403_COMMIT}:LEAD_PORTFOLIO_4/P14/"
             "P14_EXTERNAL_DISTRIBUTION_RECORD.json"],
            capture_output=True, check=True, text=True).stdout.encode()
        self.assertEqual(hashlib.sha256(blob).hexdigest(),
                         sha256_file(p),
                         "P14 record was modified after R403")
        fc = load(LP4 / "FINAL_CLASSIFICATION.json")
        self.assertEqual(fc["p14_separation"]["state"],
                         "NOT_IN_FOUR_LEAD_PORTFOLIO")


# --------------------------------------------------------------------------
# 6. Buyer-surface identity audit (item 8) + forbidden language
# --------------------------------------------------------------------------

class TestBuyerSurfaceIdentity(unittest.TestCase):
    def test_identity_audit_records_current_state_and_path(self):
        ia = load(LP4 / "BUYER_SURFACE_IDENTITY_AUDIT.json")
        self.assertEqual(ia["current_state_measured"]
                         ["buyer_repo_bytes_touched_this_round"], 0)
        self.assertIn("Art. XXXIX", ia["remediation_path"])
        traps = json.dumps(ia["ambiguity_traps_catalogued"])
        self.assertIn("P-13", traps)  # the collision trap is pinned

    def test_registry_and_records_use_commercial_designation(self):
        reg = load(REPO / "LEAD_PORTFOLIO_IDENTITY_REGISTRY.json")
        by_desig = {p["company_designation"]: p
                    for p in reg["lead_packages"]}
        self.assertEqual(set(by_desig), set(LEAD))
        self.assertEqual(by_desig["P04"]["historical_package_id"], "P-07")
        self.assertEqual(by_desig["P08"]["historical_package_id"], "P-16")
        self.assertEqual(by_desig["P11"]["historical_package_id"], "P-24")
        self.assertEqual(by_desig["P13"]["historical_package_id"], "P-27-R1")

    def test_no_forbidden_language_in_new_records(self):
        files = [
            LP4 / "GEOMETRY_REVERIFICATION_EVIDENCE.json",
            LP4 / "FINAL_CLASSIFICATION.json",
            LP4 / "BUYER_SURFACE_IDENTITY_AUDIT.json",
            LP4 / "P13" / "LINEAGE_AUDIT.json",
            LP4 / "P08" / "ENERGY_BUDGET.json",
        ] + [LP4 / d / f for d in LEAD for f in
             ("CLAIM_EVIDENCE_MATRIX.json", "DECISION_CHAIN.json")]
        for f in files:
            text = f.read_text(encoding="utf-8").lower()
            for term in ("drift-free", "self-calibrating", "world class",
                         "world-class"):
                self.assertNotIn(term, text, (f, term))


# --------------------------------------------------------------------------
# 7. Novelty evidence search classification (item 2) — re-verified
# --------------------------------------------------------------------------

class TestNoveltyEvidenceClassification(unittest.TestCase):
    def test_per_package_state_matches_history_search(self):
        """The three-way classification the directive requires:
        Patent-Bear: FOUND for P04/P08/P11; NOT FOUND (reported by
        management, artifact absent) for P13. PatSnap: attempted-
        never-executed everywhere (REPORTED_BUT_UNLOCATED-class)."""
        for desig, expected in [("P04", "SUPPORTED"), ("P08", "SUPPORTED"),
                                ("P11", "SUPPORTED")]:
            na = load(LP4 / desig / "NOVELTY_ASSESSMENT.json")
            self.assertEqual(na["assessment_status"], expected, desig)
            self.assertTrue(na["search_artifacts"], desig)
        na13 = load(LP4 / "P13" / "NOVELTY_ASSESSMENT.json")
        self.assertEqual(na13["assessment_status"], "NOVELTY_SEARCH_REPORTED")
        self.assertIn("SOURCE_ARTIFACT_UNAVAILABLE",
                      na13["assessment_status_detail"])
        # never converted to "never performed"
        self.assertIn("never invented", na13["assessment_status_detail"])

    def test_restored_novelty_hashes_still_bind(self):
        prov = load(REPO / "NOVELTY_EVIDENCE" /
                    "RESTORATION_PROVENANCE.json")
        self.assertEqual(len(prov["files"]), 13)
        for f in prov["files"]:
            fp = REPO / f["restored_to"]
            self.assertTrue(fp.exists())
            self.assertEqual(sha256_file(fp), f["sha256"])


if __name__ == "__main__":
    unittest.main()
