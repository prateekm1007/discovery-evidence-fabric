"""
test_r407_benchmark_drivers.py — adversarial tests for the benchmark
rubric + the DELIVERY/HONESTY/FIDELITY drivers (rubric 1.0-1.2) and the
MACHINERY/NOVELTY_PRACTICE P2 drivers (rubric 1.3.0, R408 external-audit
instruction 3).

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
import subprocess
import sys
import zipfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..")))

from scripts import r407_benchmark_drivers as drv  # noqa: E402


# ---------------------------------------------------------------------------
# fixtures: a synthetic mini-engine + a synthetic mini-portfolio
#
# R408: the mini-ENGINE fixture (git repo + ENGINE_RELEASE_REGISTRY + the
# registry-NAMED certificate) exists because the D-A/D-C/D-E defect class
# is exactly "the driver compared against convenient engine-side state
# instead of the authority record's own pointers". Hermetic tests must
# control BOTH sides.
# ---------------------------------------------------------------------------

def _sha(path):
    return drv.sha256_file(path)


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True)


def _commit_all(repo, msg):
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=Test", "-c", "user.email=t@t",
         "commit", "-m", msg)
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True).stdout.strip()


def build_mini_engine(tmp_path, *, release_id="R-TEST-1",
                      cert_name="RELEASE_CHAIN_VERIFICATION_R-TEST-1.json",
                      cert_overall="PASS", cert_release_id=None,
                      cert_at_root=True, cert_checks=25,
                      extra_cert=None, honesty_scope=(
                          "This certificate verifies DELIVERY from clean "
                          "clones. It does NOT claim rebuild-from-source "
                          "reproduction of those bytes.")):
    """A minimal well-formed engine authority: a git repo whose
    ENGINE_RELEASE_REGISTRY last release names a certificate that exists
    and is release-consistent."""
    engine = tmp_path / "engine"
    engine.mkdir()
    cert_rel = cert_name if cert_at_root else f"RELEASE_CHAIN/{cert_name}"
    cert_path = engine / cert_rel
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    checks = [{"id": f"E{i+1}", "state": "ENGINE", "status": "PASS",
               "description": "check", "details": []}
              for i in range(cert_checks)]
    if cert_overall != "PASS":
        checks[0]["status"] = "FAIL"
    cert = {
        "artifact": "RELEASE_CHAIN_VERIFICATION",
        "release_id": cert_release_id or release_id,
        "mode": "fresh-clone (authoritative)",
        "overall": cert_overall,
        "checks": checks,
        "states": {
            "engine_head": "b" * 40,
            "portfolio_head": "e" * 40,
            "portfolio_release_commit": "a" * 40,
            "manifest_sha256": "f" * 64,
            "master_zip_sha256": "9" * 64,
        },
        "honesty_scope": honesty_scope,
    }
    cert_path.write_text(json.dumps(cert, indent=1) + "\n")
    if extra_cert:
        # a sort-order-NEWER certificate in RELEASE_CHAIN/ belonging to an
        # OLDER release era — the D-A glob trap: a directory-glob driver
        # would cite this one instead of the registry-named certificate
        ec = dict(cert)
        ec["release_id"] = extra_cert.get("release_id", "R-OLDER-ERA")
        ec["overall"] = extra_cert.get("overall", "PASS")
        ec["states"] = dict(cert["states"])
        ec["states"]["portfolio_release_commit"] = extra_cert.get(
            "portfolio_release_commit", "7" * 40)
        ecp = engine / "RELEASE_CHAIN" / extra_cert["name"]
        ecp.parent.mkdir(parents=True, exist_ok=True)
        ecp.write_text(json.dumps(ec, indent=1) + "\n")
    registry = {
        "registry": "ENGINE_RELEASE_REGISTRY",
        "releases": [{
            "release_id": release_id,
            "portfolio_release_commit": "a" * 40,
            "engine_build_commit": "b" * 40,
            "manifest_sha256": "f" * 64,
            "master_zip_sha256": "9" * 64,
            "status": "SUBMITTED_FOR_CEO_AUDIT (test fixture)",
            "verifications": [{
                "certificate": cert_rel,
                "mode": "fresh-clone (authoritative)",
                "overall": cert_overall,
                "checks_passed": cert_checks if cert_overall == "PASS"
                else cert_checks - 1,
                "checks_total": cert_checks,
                "engine_main_verified": "b" * 40,
                "portfolio_main_verified": "e" * 40,
                "honesty_scope": honesty_scope,
            }],
        }],
    }
    (engine / "ENGINE_RELEASE_REGISTRY.json").write_text(
        json.dumps(registry, indent=1) + "\n")
    _git(engine, "init", "-q")
    record_commit = _commit_all(engine, "mini engine: registry + cert")
    return engine, record_commit


def build_mini_portfolio(tmp_path, *, tamper=None, record_commit=None,
                         release_id="R-TEST-1", include_repro=True):
    """A minimal well-formed portfolio: one package, a fresh identity
    registry, a consistent LATEST_RELEASE (pointing at the mini-engine
    authority), a matching canonical manifest, a matching reproduction
    record. `tamper` injects one defect."""
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
    cert_claims_count = 25
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
        "release_id": release_id,
        "portfolio_release_commit": "a" * 40,
        "engine_build_commit": "b" * 40,
        "engine_chain_record_commit": record_commit,
        "master_zip_sha256": _sha(master_zip),
        "chain_verification": f"{cert_claims_count}"
        f"/{cert_claims_count} PASS from clean clones",
    }
    if tamper == "short_record_commit":
        lr["engine_chain_record_commit"] = str(record_commit)[:8]
    (root / "RELEASE" / "LATEST_RELEASE.json").write_text(
        json.dumps(lr, indent=1) + "\n")

    iq = root / "INTERNAL_QA"
    iq.mkdir()
    if include_repro:
        (iq / "R399_FRESH_CLONE_REPRODUCTION.json").write_text(json.dumps(
            {"all_pass": True, "release_id": release_id,
             "portfolio_release_commit": "a" * 40,
             "portfolio_head": "c" * 40}) + "\n")

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
            {"all_pass": False, "release_id": release_id,
             "portfolio_release_commit": "a" * 40}) + "\n")
    elif tamper == "repro_stale_era":
        # the D-B trap: an OLDER-era PASS record at a phantom commit —
        # first-PASS-wins would have counted it
        (iq / "R399_FRESH_CLONE_REPRODUCTION.json").write_text(json.dumps(
            {"all_pass": True, "portfolio_head": "a73d897eb3ca"}) + "\n")
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

    def test_driver_rubric_version_equals_file_authority(self):
        """The driver's rubric version is READ FROM the rubric file
        (Art. X: one authority). A parallel hardcoded constant drifted
        once — the 1.2.0 bump left the driver emitting '1.1.0' scores
        — and this test makes that divergence structurally impossible:
        whatever the file says, the driver must report exactly that."""
        rubric = self.load()
        assert drv.RUBRIC_VERSION == rubric["rubric_version"]


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

    # -- D-F regression tests (the 3f269c23 driver-bug class, sibling
    #    instance in check_manifest_pins_agree): the real manifest's
    #    package-zip rows carry the pin under the 'zip' key — a driver
    #    reading only the R374-era 'path' form silently skips ALL
    #    package ZIPs (the 931-vs-946 finding) --

    def test_manifest_pins_zip_key_rows_counted(self, tmp_path):
        """The manifest's ACTUAL key form ('zip') must be verified —
        the count must include the package ZIPs, not silently skip
        them (pre-fix: 930+1=931 checked while the manifest carries
        946 pins)."""
        root = build_mini_portfolio(tmp_path)
        mpath = root / "CANONICAL_RELEASE_MANIFEST.json"
        m = json.loads(mpath.read_text())
        # rewrite the package_zips rows in the current (R407-P0 and
        # R408 V3.1) 'zip'-key form — byte-identical semantics
        m["package_zips"] = [
            {"folder": "01_test_pkg", "package_id": "P-01",
             "sha256": row["sha256"], "zip": row["path"]}
            for row in m["package_zips"]]
        mpath.write_text(json.dumps(m, indent=1) + "\n")
        r = drv.check_manifest_pins_agree(root)
        assert r["pass"], r["failures"]
        # 1 buyer-surface file + 1 package zip + 1 master zip = 3
        assert "3 pinned" in r["evidence"], r["evidence"]

    def test_manifest_pins_zip_key_tamper_detected(self, tmp_path):
        """THE FALSIFIER for D-F: a tampered package ZIP pinned under
        the 'zip' key must score RED. The pre-fix driver silently
        skipped the row and scored green with a tampered ZIP on disk
        — the exact defect the 3f269c23 commit found in the sibling
        script."""
        root = build_mini_portfolio(tmp_path)
        mpath = root / "CANONICAL_RELEASE_MANIFEST.json"
        m = json.loads(mpath.read_text())
        m["package_zips"] = [
            {"sha256": "0" * 64, "zip": row["path"]}
            for row in m["package_zips"]]
        mpath.write_text(json.dumps(m, indent=1) + "\n")
        r = drv.check_manifest_pins_agree(root)
        assert not r["pass"]
        assert any("HASH_DRIFT" in f for f in r["failures"])

    def test_manifest_pins_unkeyed_package_row_is_red(self, tmp_path):
        """A package-zip row with neither 'zip' nor 'path' is a
        DISCLOSED problem, never a silent skip (Art. IV: failure of
        the verification mechanism is never evidence for the claim)."""
        root = build_mini_portfolio(tmp_path)
        mpath = root / "CANONICAL_RELEASE_MANIFEST.json"
        m = json.loads(mpath.read_text())
        m["package_zips"] = [{"folder": "01_test_pkg",
                              "sha256": "0" * 64}]
        mpath.write_text(json.dumps(m, indent=1) + "\n")
        r = drv.check_manifest_pins_agree(root)
        assert not r["pass"]
        assert any("NO_PATH_KEY" in f for f in r["failures"])

    def test_manifest_pins_missing_master_pin_is_red(self, tmp_path):
        """A manifest without a master-ZIP pin is broken — RED, not a
        silent skip."""
        root = build_mini_portfolio(tmp_path)
        mpath = root / "CANONICAL_RELEASE_MANIFEST.json"
        m = json.loads(mpath.read_text())
        del m["master_zip"]
        mpath.write_text(json.dumps(m, indent=1) + "\n")
        r = drv.check_manifest_pins_agree(root)
        assert not r["pass"]
        assert any("PIN_ABSENT" in f for f in r["failures"])

    def test_latest_release_consistent_on_matching_fixture(self, tmp_path):
        engine, record_commit = build_mini_engine(tmp_path)
        root = build_mini_portfolio(tmp_path, record_commit=record_commit)
        r = drv.check_latest_release(root, engine)
        assert r["pass"], r["failures"]

    def test_latest_release_count_mismatch_detected(self, tmp_path):
        engine, record_commit = build_mini_engine(tmp_path)
        root = build_mini_portfolio(tmp_path, record_commit=record_commit,
                                    tamper="lr_count")
        r = drv.check_latest_release(root, engine)
        assert not r["pass"]

    def test_latest_release_commit_mismatch_detected(self, tmp_path):
        engine, record_commit = build_mini_engine(tmp_path)
        root = build_mini_portfolio(tmp_path, record_commit=record_commit,
                                    tamper="lr_commit")
        r = drv.check_latest_release(root, engine)
        assert not r["pass"]

    def test_reproduction_evidence_reads_all_pass(self, tmp_path):
        engine, record_commit = build_mini_engine(tmp_path)
        root = build_mini_portfolio(tmp_path, record_commit=record_commit)
        r = drv.check_reproduction_evidence(root, engine)
        assert r["pass"], r["failures"]

    def test_reproduction_evidence_failing_record_detected(self, tmp_path):
        engine, record_commit = build_mini_engine(tmp_path)
        root = build_mini_portfolio(tmp_path, record_commit=record_commit,
                                    tamper="repro_fail")
        r = drv.check_reproduction_evidence(root, engine)
        assert not r["pass"]


# ---------------------------------------------------------------------------
# R408 stale-evidence regressions (findings D-A..D-E + the stale-tag trap)
# ---------------------------------------------------------------------------

class TestR408StaleEvidenceRegressions:
    """The P0-boot audit found the DELIVERY driver citing evidence from the
    wrong era. Each test here reproduces one finding as a hermetic
    negative case (Art. V/VIII: every check must be able to FAIL)."""

    def test_certificate_at_repo_root_is_named(self, tmp_path):
        """D-A/D-C regression: the registry names a certificate at the
        engine ROOT (outside RELEASE_CHAIN/); the driver must resolve and
        name exactly that file — the 1.0.0 RELEASE_CHAIN/ glob missed it
        and cited an older-era certificate instead."""
        engine, _ = build_mini_engine(tmp_path, cert_at_root=True)
        r = drv.check_chain_certificate(engine)
        assert r["pass"], r["failures"]
        assert "RELEASE_CHAIN_VERIFICATION_R-TEST-1.json" in r["evidence"]

    def test_registry_named_certificate_missing_is_red(self, tmp_path):
        """A registry pointer that names a certificate which does not
        resolve is RED — never a fallback to whatever else lies in
        RELEASE_CHAIN/ (Art. IV: no fallback epistemology)."""
        engine, _ = build_mini_engine(tmp_path)
        (engine / "RELEASE_CHAIN_VERIFICATION_R-TEST-1.json").unlink()
        r = drv.check_chain_certificate(engine)
        assert not r["pass"]
        assert "CERTIFICATE_NOT_RESOLVED" in r["failures"]
        assert "does not resolve" in r["evidence"]

    def test_wrong_cert_stale_scores_red(self, tmp_path):
        """The mandated negative case 'wrong-cert-stale': the
        registry-named certificate is FAIL/stale for the scored release
        while a sort-order-newer PASS certificate from an older era sits
        in RELEASE_CHAIN/ — the driver must score RED (a glob would have
        returned PASS)."""
        engine, _ = build_mini_engine(
            tmp_path, cert_overall="FAIL",
            extra_cert={"name": "RELEASE_CHAIN_VERIFICATION_R-ZZZ.json",
                        "release_id": "R-OLDER-ERA", "overall": "PASS"})
        r = drv.check_chain_certificate(engine)
        assert not r["pass"]
        # and the LATEST_RELEASE consistency check must ALSO be red: its
        # claims cannot be confirmed by an authority certificate that
        # is not PASS
        root = build_mini_portfolio(
            tmp_path, record_commit=_head(engine),
            tamper="lr_count")  # claims 26/26 while authority says 24/25
        r2 = drv.check_latest_release(root, engine)
        assert not r2["pass"]
        assert any("AUTHORITY_CERTIFICATE" in f for f in r2["failures"])

    def test_certificate_release_mismatch_is_red(self, tmp_path):
        """The registry-named certificate belongs to a different
        release_id than the registry's last release -> RED."""
        engine, _ = build_mini_engine(
            tmp_path, cert_release_id="R-SOME-OTHER-RELEASE")
        r = drv.check_chain_certificate(engine)
        assert not r["pass"]
        assert any("CERTIFICATE_RELEASE_ID_MISMATCH" in f
                   for f in r["failures"])

    def test_wrong_repro_stale_scores_red(self, tmp_path):
        """The mandated negative case 'wrong-repro-stale': an
        R373-era-style PASS record at a phantom commit exists, but NO
        record matches the release being scored -> the check must be RED
        with the honest N/A state (1.0.0's first-PASS-wins returned
        PASS)."""
        engine, record_commit = build_mini_engine(tmp_path)
        root = build_mini_portfolio(
            tmp_path, record_commit=record_commit,
            tamper="repro_stale_era")
        r = drv.check_reproduction_evidence(root, engine)
        assert not r["pass"]
        assert any("NO_MATCHING_REPRODUCTION_RECORD" in f
                   for f in r["failures"])
        assert "N/A" in r["evidence"]
        # the honesty note carries the certificate's own honesty_scope
        assert "rebuild-from-source" in r["evidence"]

    def test_honest_na_when_no_reproduction_records_exist(self, tmp_path):
        """D-B honest-N/A path: INTERNAL_QA empty -> RED with the N/A
        note carrying the chain certificate's own honesty_scope (never a
        silent pass, never a borrowed older-era record)."""
        engine, record_commit = build_mini_engine(tmp_path)
        root = build_mini_portfolio(tmp_path, record_commit=record_commit,
                                    include_repro=False)
        r = drv.check_reproduction_evidence(root, engine)
        assert not r["pass"]
        assert "N/A" in r["evidence"]

    def test_short_engine_chain_record_commit_is_red(self, tmp_path):
        """D-E: an 8-char engine_chain_record_commit is RED (Art. II
        exactness — the R407 LATEST_RELEASE carried exactly this defect
        with value 'cf2665b6')."""
        engine, record_commit = build_mini_engine(tmp_path)
        root = build_mini_portfolio(
            tmp_path, record_commit=record_commit,
            tamper="short_record_commit")
        r = drv.check_latest_release(root, engine)
        assert not r["pass"]
        assert any("ENGINE_CHAIN_RECORD_COMMIT_NOT_FULL40" in f
                   for f in r["failures"])

    def test_foreign_engine_chain_record_commit_is_red(self, tmp_path):
        """D-E: a full-40 hash that is NOT a registry-record commit is
        RED (a plausible-looking foreign hash must not pass)."""
        engine, _ = build_mini_engine(tmp_path)
        root = build_mini_portfolio(
            tmp_path, record_commit="c" * 40)
        r = drv.check_latest_release(root, engine)
        assert not r["pass"]
        assert any("ENGINE_CHAIN_RECORD_COMMIT_NOT_A_REGISTRY_RECORD_COMMIT"
                   in f for f in r["failures"])

    def test_stale_tag_pointing_backwards_is_red(self, tmp_path):
        """The stale-tag trap: LATEST_RELEASE.git_tag exists but points
        at a commit BEFORE the release commit -> RED (the v1.0.0-3D-edition
        trap: a tag at a superseded release)."""
        engine, record_commit = build_mini_engine(tmp_path)
        root = build_mini_portfolio(tmp_path, record_commit=record_commit)
        # give the portfolio a git history: an OLD root commit, then the
        # release state; tag the OLD root commit (points backwards)
        _git(root, "init", "-q")
        (root / "OLD_MARKER.txt").write_text("old era\n")
        _commit_all(root, "old state (pre-release)")
        old_root = _head(root)
        (root / "OLD_MARKER.txt").unlink()
        _commit_all(root, "release state")
        rel_head = _head(root)
        lr_path = root / "RELEASE" / "LATEST_RELEASE.json"
        lr = json.loads(lr_path.read_text())
        lr["git_tag"] = "v-stale-trap"
        lr["portfolio_release_commit"] = rel_head
        lr_path.write_text(json.dumps(lr, indent=1) + "\n")
        _commit_all(root, "pointer state")
        assert old_root != rel_head
        _git(root, "tag", "v-stale-trap", old_root)
        r = drv.check_latest_release(root, engine)
        assert not r["pass"]
        assert any("TAG_POINTS_BACKWARDS" in f for f in r["failures"])

    def test_tag_at_release_commit_is_green(self, tmp_path):
        """Positive control: a tag at/after the release commit passes the
        tag-agreement check (a universal rejector would fail this)."""
        engine, record_commit = build_mini_engine(tmp_path)
        root = build_mini_portfolio(tmp_path, record_commit=record_commit)
        _git(root, "init", "-q")
        _commit_all(root, "release state")
        rel_head = _head(root)
        lr_path = root / "RELEASE" / "LATEST_RELEASE.json"
        lr = json.loads(lr_path.read_text())
        lr["git_tag"] = "v-current"
        lr["portfolio_release_commit"] = rel_head
        lr_path.write_text(json.dumps(lr, indent=1) + "\n")
        _git(root, "add", "-A")
        _git(root, "-c", "user.name=T", "-c", "user.email=t@t",
             "commit", "-q", "-m", "pointer state")
        _git(root, "tag", "v-current", "HEAD")
        r = drv.check_latest_release(root, engine)
        # the tag check itself must be the ONLY thing standing between
        # red and green here: assert the tag evidence is present and no
        # tag-related failure is recorded
        assert not any("TAG_" in f for f in r["failures"])
        assert "git_tag=v-current" in r["evidence"]


def _head(repo):
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True).stdout.strip()


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


# ---------------------------------------------------------------------------
# rubric 1.3.0 — the P2 driver wiring (R408 external-audit instruction 3)
# ---------------------------------------------------------------------------

class TestP2DriverWiring:
    def load(self):
        return json.loads(drv.RUBRIC_PATH.read_text(encoding="utf-8"))

    def test_machinery_and_novelty_drivers_wired(self):
        """The two P2 families are BUILT_IN (executable drivers, live
        measurement) — no family may claim a driver it does not have."""
        rubric = self.load()
        for fam in ("MACHINERY", "NOVELTY_PRACTICE"):
            meta = rubric["families"][fam]
            assert meta["driver_status"] == "BUILT_IN_P2", fam
            assert "r407_benchmark_drivers.py" in meta["measured_by"], fam

    def test_rubric_version_bumped_for_new_tables(self):
        """Rubric rule_7: driver changes require a new rubric version;
        the 1.3.0 entry records the NEW-table scope (no threshold moved
        on any measured family)."""
        rubric = self.load()
        assert rubric["rubric_version"] == "1.3.0"
        entry = rubric["rubric_change_record"][-1]
        assert entry["version"] == "1.3.0"
        assert entry["deduction_tables_changed"] is True
        assert "NEW tables ONLY" in entry[
            "deduction_tables_changed_scope"]
        assert entry["no_threshold_moved"] is True

    def test_planned_stub_families_drop_to_five(self):
        """The planned-stub writer now covers exactly the five families
        that still have no driver (rule_2: 0 until measured)."""
        rubric = self.load()
        planned = {fam for fam, meta in rubric["families"].items()
                   if str(meta.get("driver_status", "")).startswith(
                       "PLANNED")}
        assert planned == {"ADVERSARIAL", "DOSSIER_QUALITY",
                           "INDEPENDENCE", "LOOP", "REALITY_FED"}

    def test_new_deduction_weights_follow_the_bar_text(self):
        """The weights ENCODE the rubric's own bars, they do not invent
        thresholds: every bar_9 component's failure drops below 9; the
        bar_10 delta checks (F-series, custody) carry 1.0 so their
        failure alone leaves the 9-bar intact."""
        bar9_machinery = ("e15_series_green", "e16_series_green",
                          "a_series_green", "a12_capstone_record_intact")
        for name in bar9_machinery:
            assert drv.MACHINERY_DEDUCTIONS[name] >= 2.0, name
        assert drv.MACHINERY_DEDUCTIONS["f_series_green"] == 1.0
        bar9_novelty = ("search_neutrality_enforced",
                        "collision_stage_registered_and_live",
                        "zero_results_not_novelty_enforced")
        for name in bar9_novelty:
            assert drv.NOVELTY_PRACTICE_DEDUCTIONS[name] >= 2.0, name
        assert drv.NOVELTY_PRACTICE_DEDUCTIONS[
            "prior_art_hunt_custody_on_survivors"] == 1.0
        for name, w in drv.MACHINERY_DEDUCTIONS.items():
            assert w > 0, name
        for name, w in drv.NOVELTY_PRACTICE_DEDUCTIONS.items():
            assert w > 0, name


class TestMachineryChecks:
    def _mini_engine_with_a12(self, tmp_path, **overrides):
        """A git repo carrying a well-formed A_SERIES_ACCEPTANCE.json
        whose code_commit points at a real commit in that repo (unless
        a code_commit override is given, which must stick)."""
        engine = tmp_path / "mach_engine"
        engine.mkdir()
        good = {
            "A12_reader_readiness": {
                "contract": "A12 READER-READINESS (the 9 questions)",
                "checks": {f"Q{i}": "answered" for i in range(1, 10)},
                "invention_id": "inv:test:1",
                "passed": True},
            "release_status": "RELEASED",
            "run_id": "A12_CAPSTONE_test",
            "code_commit": "0" * 40,
            "final_status": "AUTOMATED_INVENTION_CANDIDATE",
        }
        good.update(overrides)
        (engine / "A_SERIES_ACCEPTANCE.json").write_text(
            json.dumps(good, indent=1) + "\n")
        _git(engine, "init", "-q")
        _git(engine, "config", "user.name", "T")
        _git(engine, "config", "user.email", "t@t")
        # the record's code_commit points at the FIRST commit (the
        # check verifies the pointer RESOLVES in history — the record
        # itself is committed afterwards with that pointer)
        first_cc = _commit_all(engine, "a12 record fixture")
        if "code_commit" not in overrides:
            good["code_commit"] = first_cc
            (engine / "A_SERIES_ACCEPTANCE.json").write_text(
                json.dumps(good, indent=1) + "\n")
            _commit_all(engine, "a12 record with resolvable pointer")
        return engine

    def test_a12_record_live_repo_measures_honest_na(self):
        """The LIVE repo's A12 record carries a code_commit that is
        unreachable from the current object store (the run pre-dates
        the history rewrites). Per the D-B honest-N/A precedent the
        check FAILS with the PROVENANCE_INCOMPLETE disclosure — never
        a silent pass, never a fabricated pointer."""
        r = drv.check_a12_capstone_record(drv.ENGINE_ROOT)
        assert not r["pass"]
        assert "A12_CODE_COMMIT_DOES_NOT_RESOLVE" in r["failures"]
        assert "PROVENANCE_INCOMPLETE" in r["evidence"]
        assert "not re-executed for this score" in r["evidence"]

    def test_a12_record_passes_on_wellformed_fixture(self, tmp_path):
        engine = self._mini_engine_with_a12(tmp_path)
        r = drv.check_a12_capstone_record(engine)
        assert r["pass"], r["failures"]

    def test_a12_record_tamper_missing_questions(self, tmp_path):
        engine = self._mini_engine_with_a12(
            tmp_path, A12_reader_readiness={"contract": "x",
                                            "checks": {"Q1": "y"}})
        r = drv.check_a12_capstone_record(engine)
        assert not r["pass"]
        assert any("A12_QUESTIONS_INCOMPLETE" in f for f in r["failures"])

    def test_a12_record_tamper_short_commit(self, tmp_path):
        engine = self._mini_engine_with_a12(tmp_path, code_commit="162ca5d")
        r = drv.check_a12_capstone_record(engine)
        assert not r["pass"]
        assert any("A12_CODE_COMMIT_NOT_FULL40" in f
                   for f in r["failures"])

    def test_a12_record_tamper_not_released(self, tmp_path):
        engine = self._mini_engine_with_a12(
            tmp_path, release_status="PENDING")
        r = drv.check_a12_capstone_record(engine)
        assert not r["pass"]
        assert any("A12_RELEASE_STATUS" in f for f in r["failures"])

    def test_a12_record_missing_file_is_red(self, tmp_path):
        engine = tmp_path / "empty_engine"
        engine.mkdir()
        r = drv.check_a12_capstone_record(engine)
        assert not r["pass"]
        assert "A12_RECORD_MISSING" in r["failures"]

    def test_suite_check_fails_on_missing_target(self, tmp_path):
        r = drv.run_pytest_suite(tmp_path, ["tests/nope_missing.py"],
                                 "e15_series_green")
        assert not r["pass"]
        assert "SUITE_TARGET_MISSING" in r["failures"]

    def test_suite_check_fails_on_failing_suite(self, tmp_path,
                                                monkeypatch):
        """A red suite is RED — never a silent pass (rule_8)."""
        class FakeProc:
            returncode = 1
            stdout = "FF.\n2 failed, 1 passed in 0.01s\n"
            stderr = ""
        monkeypatch.setattr(drv.subprocess, "run",
                            lambda *a, **k: FakeProc())
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "fake.py").write_text("")
        r = drv.run_pytest_suite(tmp_path, ["tests/fake.py"],
                                 "e15_series_green")
        assert not r["pass"]
        assert any("failed" in f for f in r["failures"])

    def test_suite_check_passes_on_green_suite(self, tmp_path,
                                               monkeypatch):
        class FakeProc:
            returncode = 0
            stdout = "...\n3 passed in 0.01s\n"
            stderr = ""
        monkeypatch.setattr(drv.subprocess, "run",
                            lambda *a, **k: FakeProc())
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "fake.py").write_text("")
        r = drv.run_pytest_suite(tmp_path, ["tests/fake.py"],
                                 "e15_series_green")
        assert r["pass"], r["failures"]

    def test_machinery_family_measured_on_live_repo(self):
        """The MACHINERY family measurement executes the real suites
        (slow: ~4 min live run) and scores from checks only."""
        result = drv.measure_family("machinery", None)
        assert result["instrument_state"] == "MEASURED"
        names = [c["name"] for c in result["checks"]]
        assert names == ["e15_series_green", "e16_series_green",
                         "a_series_green", "a12_capstone_record_intact",
                         "f_series_green"]


class TestNoveltyPracticeChecks:
    def test_neutrality_live_passes(self):
        r = drv.check_search_neutrality_live(drv.ENGINE_ROOT)
        assert r["pass"], r["failures"]
        assert "solution_class_injection" in r["evidence"]

    def test_neutrality_verifier_rejects_injected_class(self):
        out = {"search_space_neutrality": {
            "solution_class_injection": "HARDWARE_COATING"},
            "queries": {"domain": {"text": "pacemaker lead fracture",
                                   "derivation":
                                   "DERIVED_FROM_PROBLEM_FACTS",
                                   "term_sources": {}}}}
        problems = drv._neutrality_contract_violations(out)
        assert any("SOLUTION_CLASS_INJECTED" in p for p in problems)

    def test_neutrality_verifier_rejects_unmarked_derivation(self):
        out = {"search_space_neutrality": {
            "solution_class_injection": "NONE"},
            "queries": {"domain": {"text": "pacemaker lead fracture",
                                   "derivation": "",
                                   "term_sources": {}}}}
        problems = drv._neutrality_contract_violations(out)
        assert any("UNMARKED_DERIVATION" in p for p in problems)

    def test_neutrality_verifier_rejects_solution_class_term(self):
        """THE v1 defect: a 'coating' term entering a query whose
        problem facts carry no coating vocabulary is an injection."""
        out = {"search_space_neutrality": {
            "solution_class_injection": "NONE"},
            "queries": {"domain": {
                "text": "pacemaker lead fracture prevention coating flow",
                "derivation": "DERIVED_FROM_PROBLEM_FACTS",
                "term_sources": {}}}}
        problems = drv._neutrality_contract_violations(out)
        assert any("SOLUTION_CLASS_TERM" in p for p in problems)

    def test_neutrality_verifier_rejects_non_fact_source(self):
        out = {"search_space_neutrality": {
            "solution_class_injection": "NONE"},
            "queries": {"domain": {"text": "pacemaker lead fracture",
                                   "derivation":
                                   "DERIVED_FROM_PROBLEM_FACTS",
                                   "term_sources": {"hypothesis": "x"}}}}
        problems = drv._neutrality_contract_violations(out)
        assert any("NON_FACT_SOURCE" in p for p in problems)

    def test_neutrality_verifier_accepts_wellformed_output(self):
        out = {"search_space_neutrality": {
            "solution_class_injection": "NONE"},
            "queries": {
                "domain": {"text": "pacemaker lead fracture",
                           "derivation": "DERIVED_FROM_PROBLEM_FACTS",
                           "term_sources": {"device": "pacemaker"}},
                "mechanism": {"text": "lead fracture diameter",
                              "derivation": "EXPLORATORY_HYPOTHESIS",
                              "term_sources": {"constraint": "x"}}}}
        assert drv._neutrality_contract_violations(out) == []

    def test_collision_stage_live_passes(self):
        r = drv.check_collision_stage_live(drv.ENGINE_ROOT)
        assert r["pass"], r["failures"]

    def test_collision_stage_absent_is_red(self, tmp_path):
        engine = tmp_path / "g_engine"
        engine.mkdir()
        (engine / "ACTIVE_DISCOVERY_GRAPH.json").write_text(json.dumps(
            {"executable_chain": [
                {"order": 1, "stage": "RETRIEVE",
                 "capability_id": "A2_RETRIEVAL"}]}))
        r = drv.check_collision_stage_live(engine)
        assert not r["pass"]
        assert "COLLISION_STAGE_ABSENT_FROM_CHAIN" in r["failures"]

    def test_zero_results_live_passes(self):
        r = drv.check_zero_results_not_novelty_live(drv.ENGINE_ROOT)
        assert r["pass"], r["failures"]
        assert "UNRESOLVED_NO_RELEVANT_ART" in r["evidence"]

    def test_zero_results_r394_regression_is_red(self, monkeypatch):
        """THE FALSIFIER for the R394 s2 fix: if the state machine
        regresses to the pre-fix behavior (zero hits with a partial
        search failure -> RESOLVED_DIFFERENTIATED, the production
        defect measured on ts_d1ab9fd4d756), the check goes RED."""
        def broken_resolve(families, search_errors,
                           searches_succeeded, search_incomplete):
            return {"state": "RESOLVED_DIFFERENTIATED"}
        monkeypatch.setattr(drv, "_run_resolve", broken_resolve)
        r = drv.check_zero_results_not_novelty_live(drv.ENGINE_ROOT)
        assert not r["pass"]
        assert any("STATE_RESOLVED_DIFFERENTIATED" in f
                   for f in r["failures"])

    def test_novelty_state_machine_admits_a_novelty_state(self,
                                                           monkeypatch):
        """If someone adds a NOVEL* state to the machine's prior-art
        vocabulary (novelty asserted from search), the check goes RED."""
        import discovery_fabric.a2.classify as a2c
        monkeypatch.setattr(a2c, "NON_KILL_STATES",
                            a2c.NON_KILL_STATES | {"NOVEL_DETERMINED"})
        r = drv.check_zero_results_not_novelty_live(drv.ENGINE_ROOT)
        assert not r["pass"]
        assert any("SEARCH_STATE_ASSERTS_NOVELTY" in f
                   for f in r["failures"])

    def test_custody_live_passes(self):
        r = drv.check_prior_art_hunt_custody_on_survivors(drv.ENGINE_ROOT)
        assert r["pass"], r["failures"]
        assert "hash-verified" in r["evidence"]

    def test_custody_tampered_hash_is_red(self, tmp_path, monkeypatch):
        """Tamper a restored artifact byte -> custody check RED (the
        bar_10 hunt is only full custody if the hashes still bind)."""
        import shutil
        engine = tmp_path / "cust_engine"
        engine.mkdir()
        for rel in ("NOVELTY_EVIDENCE", "LEAD_PORTFOLIO_4"):
            shutil.copytree(drv.ENGINE_ROOT / rel, engine / rel)
        # tamper one restored artifact
        target = engine / "NOVELTY_EVIDENCE" / "restored" / "R354" / \
            "patsnap_pipeline" / "PATSNAP_API_STATUS.json"
        if target.exists():
            target.write_text("{}\n")
        r = drv.check_prior_art_hunt_custody_on_survivors(engine)
        assert not r["pass"]
        assert any("HASH_DRIFT" in f for f in r["failures"])

    def test_novelty_practice_family_measured_on_live_repo(self):
        result = drv.measure_family("novelty_practice", None)
        assert result["instrument_state"] == "MEASURED"
        names = [c["name"] for c in result["checks"]]
        assert names == ["search_neutrality_enforced",
                         "collision_stage_registered_and_live",
                         "zero_results_not_novelty_enforced",
                         "prior_art_hunt_custody_on_survivors"]
        # rule_5: the estimate is recorded AS ESTIMATE, never the score
        assert result["estimate_is_not_the_score"] is True
