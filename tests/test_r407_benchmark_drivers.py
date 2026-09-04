"""
test_r407_benchmark_drivers.py — adversarial tests for the P0 benchmark
rubric + the DELIVERY/HONESTY/FIDELITY drivers.

Constitution basis:
  Art. V      — positive AND negative cases (every check must be able to
                FAIL: tamper fixtures prove it)
  Art. VIII   — certification must attack itself
  Art. XVII   — every control has an attempted bypass
  Art. XXV    — missing instrument = honest 0, never a silent pass
  Art. XXX    — never optimize the evaluator: tampering must flip checks
  R407 rubric rules — score without driver output rejected; missing
                instrument scores 0; relabeling ceiling<->defect is a
                HONESTY failure.

Hermetic: the tests build synthetic mini-portfolios in tmp_path and call
the driver's individual check functions. No network, no real clones.
"""

import json
import os
import sys
import zipfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..")))

from scripts import r407_benchmark_drivers as drv  # noqa: E402


# ---------------------------------------------------------------------------
# fixtures: a synthetic mini-portfolio
# ---------------------------------------------------------------------------

def _sha(path):
    return drv.sha256_file(path)


def build_mini_portfolio(tmp_path, *, tamper=None):
    """A minimal well-formed portfolio: one package, a fresh identity
    registry, a consistent LATEST_RELEASE, a matching canonical manifest,
    a passing reproduction record. `tamper` injects one defect."""
    root = tmp_path / "portfolio"
    pkg = root / "DOWNLOAD" / "01_test_pkg"
    pkg.mkdir(parents=True)
    for fn in ("00_PACKAGE_README.pdf", "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
               "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
               "03_BUYER_DECISION_CARD.pdf", "04_EVIDENCE_SUMMARY.pdf",
               "05_TRANSFER_MANIFEST.pdf"):
        (pkg / fn).write_bytes(b"%PDF-1.4 fake " + fn.encode())
    (pkg / "PACKAGE_MANIFEST.json").write_text(json.dumps(
        {"files": [{"file": "00_PACKAGE_README.pdf",
                    "sha256": _sha(pkg / "00_PACKAGE_README.pdf")}]},
        indent=1) + "\n")
    with zipfile.ZipFile(root / "DOWNLOAD" / "01_test_pkg.zip", "w") as zf:
        zf.write(pkg / "00_PACKAGE_README.pdf", "00_PACKAGE_README.pdf")
        zf.write(pkg / "PACKAGE_MANIFEST.json", "PACKAGE_MANIFEST.json")

    reg = {
        "registry": "PORTFOLIO_IDENTITY_REGISTRY", "version": "2.1",
        "packages": [{
            "portfolio_number": "01",
            "historical_package_id": "P-01",
            "technology_name": "Test Technology",
            "folder_name": "01_test_pkg",
            "dossier_hash": _sha(pkg / "02_ENGINEERING_TECHNOLOGY_"
                                       "TRANSFER_DOSSIER.pdf"),
            "package_zip_hash": _sha(root / "DOWNLOAD" /
                                     "01_test_pkg.zip"),
            "manifest_hash": _sha(pkg / "PACKAGE_MANIFEST.json"),
            "status": "V2"}]}
    (root / "PORTFOLIO_IDENTITY_REGISTRY.json").write_text(
        json.dumps(reg, indent=2) + "\n")

    master_zip = root / "DOWNLOAD" / "technology-transfer-portfolio-15.zip"
    with zipfile.ZipFile(master_zip, "w") as zf:
        zf.write(pkg / "00_PACKAGE_README.pdf",
                 "DOWNLOAD/01_test_pkg/00_PACKAGE_README.pdf")
    manifest = {
        "manifest_type": "CANONICAL_RELEASE_MANIFEST",
        "buyer_surface": {
            "files": {"DOWNLOAD/01_test_pkg/00_PACKAGE_README.pdf":
                      _sha(pkg / "00_PACKAGE_README.pdf")}},
        "package_zips": [{"path": "DOWNLOAD/01_test_pkg.zip",
                          "sha256": _sha(root / "DOWNLOAD" /
                                         "01_test_pkg.zip")}],
        "master_zip": {"path": str(master_zip.relative_to(root)),
                       "sha256": _sha(master_zip)},
    }
    (root / "CANONICAL_RELEASE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=1) + "\n")

    (root / "RELEASE").mkdir()
    lr = {
        "artifact": "LATEST_RELEASE",
        "release_id": "R-TEST-1",
        "git_tag": "v-test",
        "portfolio_release_commit": "a" * 40,
        "engine_build_commit": "b" * 40,
        "master_zip_sha256": _sha(master_zip),
        "chain_verification": "25/25 PASS from clean clones",
    }
    (root / "RELEASE" / "LATEST_RELEASE.json").write_text(
        json.dumps(lr, indent=1) + "\n")

    iq = root / "INTERNAL_QA"
    iq.mkdir()
    (iq / "R399_FRESH_CLONE_REPRODUCTION.json").write_text(json.dumps(
        {"all_pass": True, "portfolio_head": "c" * 40}) + "\n")

    if tamper == "identity_hash":
        reg["packages"][0]["package_zip_hash"] = "0" * 64
        (root / "PORTFOLIO_IDENTITY_REGISTRY.json").write_text(
            json.dumps(reg, indent=2) + "\n")
    elif tamper == "manifest_pin":
        manifest["buyer_surface"]["files"][
            "DOWNLOAD/01_test_pkg/00_PACKAGE_README.pdf"] = "0" * 64
        (root / "CANONICAL_RELEASE_MANIFEST.json").write_text(
            json.dumps(manifest, indent=1) + "\n")
    elif tamper == "lr_count":
        lr["chain_verification"] = "26/26 PASS from clean clones"
        (root / "RELEASE" / "LATEST_RELEASE.json").write_text(
            json.dumps(lr, indent=1) + "\n")
    elif tamper == "lr_commit":
        lr["portfolio_release_commit"] = "d" * 40
        (root / "RELEASE" / "LATEST_RELEASE.json").write_text(
            json.dumps(lr, indent=1) + "\n")
    elif tamper == "repro_fail":
        (iq / "R399_FRESH_CLONE_REPRODUCTION.json").write_text(json.dumps(
            {"all_pass": False}) + "\n")
    return root


# ---------------------------------------------------------------------------
# rubric contract
# ---------------------------------------------------------------------------

class TestRubricContract:
    def load(self):
        return json.loads(drv.RUBRIC_PATH.read_text(encoding="utf-8"))

    def test_ten_families_defined(self):
        rubric = self.load()
        fams = set(rubric["families"])
        assert fams == {"DELIVERY", "HONESTY", "FIDELITY", "MACHINERY",
                        "ADVERSARIAL", "NOVELTY_PRACTICE", "INDEPENDENCE",
                        "DOSSIER_QUALITY", "LOOP", "REALITY_FED"}

    def test_every_family_carries_bars_and_driver(self):
        rubric = self.load()
        for fam, meta in rubric["families"].items():
            assert meta.get("bar_9"), fam
            assert meta.get("measured_by"), fam
            assert "auditor_estimate_r407" in meta, fam
            assert "reaches_9_in" in meta, fam

    def test_dossier_quality_has_twelve_dimensions(self):
        rubric = self.load()
        dims = rubric["dossier_quality_dimensions"]["dimensions"]
        assert len(dims) == 12
        reality_fed = [d for d, m in dims.items() if m.get("reality_fed")]
        assert {"baseline_strength", "physical_validation",
                "commercial_transferability", "closed_loop_maturity"} == \
            set(reality_fed)

    def test_defect_and_ceiling_ledgers_disjoint(self):
        """Rubric rule_4: relabeling ceiling<->defect is a HONESTY
        failure — the two lists must stay disjoint by construction."""
        rubric = self.load()
        ledger = rubric["defect_and_ceiling_ledger"]
        defects = set(ledger["p0_defects"])
        ceilings = set(ledger["honest_ceilings"])
        assert not (defects & ceilings)
        assert defects and ceilings

    def test_scoring_rules_non_negotiable_present(self):
        rubric = self.load()
        rules = rubric["scoring_rules_non_negotiable"]
        for i in range(1, 9):
            assert any(k.startswith(f"rule_{i}_") for k in rules), i


# ---------------------------------------------------------------------------
# driver check functions: positive + tampered negative cases
# ---------------------------------------------------------------------------

class TestDeliveryChecks:
    def test_identity_registry_fresh_passes_on_fresh_fixture(self,
                                                              tmp_path):
        root = build_mini_portfolio(tmp_path)
        r = drv.check_identity_registry(root)
        assert r["pass"], r["failures"]

    def test_identity_registry_tamper_detected(self, tmp_path):
        root = build_mini_portfolio(tmp_path, tamper="identity_hash")
        r = drv.check_identity_registry(root)
        assert not r["pass"]
        assert any("package_zip_hash" in f for f in r["failures"])

    def test_manifest_pins_drift_detected(self, tmp_path):
        root = build_mini_portfolio(tmp_path, tamper="manifest_pin")
        r = drv.check_manifest_pins_agree(root)
        assert not r["pass"]
        assert any("HASH_DRIFT" in f for f in r["failures"])

    def test_manifest_pins_pass_on_consistent_fixture(self, tmp_path):
        root = build_mini_portfolio(tmp_path)
        r = drv.check_manifest_pins_agree(root)
        assert r["pass"], r["failures"]

    def test_latest_release_count_mismatch_detected(self, tmp_path):
        # the mini fixture has no authority certificate in the engine
        # RELEASE_CHAIN for R-TEST-1; the pointer's 25/25 claim cannot
        # be confirmed -> the check must fail (fail-closed, Art. IV)
        root = build_mini_portfolio(tmp_path, tamper="lr_count")
        r = drv.check_latest_release(root, drv.ENGINE_ROOT)
        assert not r["pass"]

    def test_latest_release_commit_mismatch_detected(self, tmp_path):
        root = build_mini_portfolio(tmp_path, tamper="lr_commit")
        r = drv.check_latest_release(root, drv.ENGINE_ROOT)
        assert not r["pass"]

    def test_reproduction_evidence_reads_all_pass(self, tmp_path):
        root = build_mini_portfolio(tmp_path)
        r = drv.check_reproduction_evidence(root)
        assert r["pass"], r["failures"]

    def test_reproduction_evidence_failing_record_detected(self, tmp_path):
        root = build_mini_portfolio(tmp_path, tamper="repro_fail")
        r = drv.check_reproduction_evidence(root)
        assert not r["pass"]


class TestHonestyChecks:
    def _portfolio_with_loop_state(self, tmp_path, state):
        root = build_mini_portfolio(tmp_path)
        pkg = root / "DOWNLOAD" / "01_test_pkg"
        (pkg / "LOOP_STATE.json").write_text(json.dumps(
            {"loop_verification_state": state}) + "\n")
        return root

    def test_synthetic_loop_state_passes(self, tmp_path):
        root = self._portfolio_with_loop_state(tmp_path,
                                               "SYNTHETIC_LOOP_VERIFIED")
        r = drv.check_no_semantic_promotion(root)
        assert r["pass"], r["failures"]

    def test_real_loop_verified_claim_detected(self, tmp_path):
        """A promoted REAL_LOOP_VERIFIED state in a shipped file must be
        flagged (Art. XXXVII/XXXVIII — the state is derived, never
        asserted)."""
        root = self._portfolio_with_loop_state(tmp_path, "REAL_LOOP_VERIFIED")
        r = drv.check_no_semantic_promotion(root)
        assert not r["pass"]
        assert any("REAL_LOOP_VERIFIED" in f for f in r["failures"])

    def test_numeric_rows_without_source_flagged(self, tmp_path):
        root = build_mini_portfolio(tmp_path)
        pkg = root / "DOWNLOAD" / "01_test_pkg"
        (pkg / "COMMERCIAL_EVIDENCE.json").write_text(json.dumps(
            [{"estimate": "$1B", "market_definition": "x"}]) + "\n")
        r = drv.check_numeric_assertions_sourced(root)
        assert not r["pass"]
        assert any("no-source" in f for f in r["failures"])


class TestFidelityChecks:
    def test_corpus_pins_guard_passes_on_real_engine(self):
        r = drv.check_frozen_corpus_hash_guard(drv.ENGINE_ROOT)
        assert r["pass"], r["failures"]

    def test_stale_path_census_flags_placeholder(self, tmp_path):
        root = build_mini_portfolio(tmp_path)
        (root / "RELEASE" / "X_CERT.json").write_text(json.dumps(
            {"zips": "DOWNLOAD/NN_folder_name.zip"}) + "\n")
        r = drv.check_stale_path_census(root, drv.ENGINE_ROOT)
        assert not r["pass"]
        assert any("NN_folder_name" in f for f in r["failures"])

    def test_stale_path_census_excludes_preserved_history(self, tmp_path):
        """Art. XI — preserved history artifacts are never edited; their
        stale refs are disclosed, not counted against the current bar."""
        root = build_mini_portfolio(tmp_path)
        hist = root / "RELEASE" / "history_r370"
        hist.mkdir()
        (hist / "OLD_CERT.json").write_text(json.dumps(
            {"zips": "DOWNLOAD/NN_folder_name.zip",
             "old": "CONSULTANT_FINDING_REGISTRY.json"}) + "\n")
        r = drv.check_stale_path_census(root, drv.ENGINE_ROOT)
        assert r["pass"], r["failures"]
        assert "preserved history" in r["evidence"]

    def test_not_measurable_census_clean_fixture(self, tmp_path):
        root = build_mini_portfolio(tmp_path)
        r = drv.check_not_measurable_census(root, drv.ENGINE_ROOT)
        assert r["pass"], r["failures"]


# ---------------------------------------------------------------------------
# scoring semantics
# ---------------------------------------------------------------------------

class TestScoringSemantics:
    def test_missing_instrument_scores_zero(self):
        """Rubric rule_2: no portfolio -> INSTRUMENT_UNAVAILABLE, score
        0 — never a silent pass, never a carry-forward."""
        result = drv.measure_family("delivery", None)
        assert result["score"] == 0
        assert result["instrument_state"] == "INSTRUMENT_UNAVAILABLE"
        assert result["defects_named"]

    def test_failing_check_never_scores_ten(self):
        """Floor semantics: any failed check costs at least one point —
        0.5-deduction failures must not round back to 10."""
        checks = [drv._check("stale_path_census", False, "test",
                             ["one-failure"]),
                  drv._check("frozen_corpus_hash_guard", True, "test")]
        table = dict(drv.FIDELITY_DEDUCTIONS)
        table = drv._apply_per_instance_caps(checks, table)
        score, _ = drv._score_from_checks(checks, table)
        assert score < 10

    def test_all_pass_scores_ten(self):
        checks = [drv._check("frozen_corpus_hash_guard", True, "t"),
                  drv._check("stale_path_census", True, "t"),
                  drv._check("not_measurable_census", True, "t"),
                  drv._check("semantic_genericness_live", True, "t")]
        score, total = drv._score_from_checks(checks,
                                              dict(drv.FIDELITY_DEDUCTIONS))
        assert score == 10 and total == 0

    def test_estimate_never_used_for_score(self):
        """Rubric rule_5: auditor estimates are recorded as estimates;
        the score comes only from measured checks."""
        result = drv.measure_family("fidelity", None)
        assert result["estimate_is_not_the_score"] is True
        assert result["score"] == 0  # instrument unavailable, not estimate
