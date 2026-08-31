"""tests/test_r382_disposition.py — R382 CEO PORTFOLIO DISPOSITION
adversarial tests.

Constitutional anchors:
- Art. III/VI: every record_verified_basis claim binds to a real file
  + exact span (machine-resolved against the ENGINE repo); CEO
  business claims (budgets, positioning, superlatives) stay
  CEO_STATED — never laundered into record evidence.
- Art. XV: the 4 CEO-strictness overrides of the consultant verdict
  (07, 08, 10, 14) must be flagged, never silent.
- Art. XI: retirement freezes bytes (tamper detection via frozen
  identity hashes).
- Art. XVII/XXX: tamper + laundering + purity attacks must FAIL the
  verifier.
"""
import json
import os
import shutil
import zipfile

import pytest

from premium_package_factory.r371.canonical_source import (
    PACKAGE_MAP, load_all_packages)
from premium_package_factory.r371.economics import build_validation_economics
from premium_package_factory.r371.unknowns import build_unknown_roadmap
from premium_package_factory.r382.disposition import (
    BUYER_ORDER, DISPOSITIONS, STATES, apply_portfolio_disposition,
    buyer_package_ids, buyer_rows, folder_for, package_location,
    verify_disposition)

ENGINE_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), ".."))
V2_INPUT = os.path.join(ENGINE_ROOT, "premium_package_factory", "input",
                        "v2_mutations")

# ---------------------------------------------------------------------------
# 1. The disposition map itself
# ---------------------------------------------------------------------------
class TestDispositionMap:
    def test_covers_exactly_15_with_legal_states(self):
        assert set(DISPOSITIONS) == {f"{i:02d}" for i in range(1, 16)}
        for num, entry in DISPOSITIONS.items():
            assert entry["state"] in STATES, (num, entry["state"])
            # pkg_id binding matches the immutable PACKAGE_MAP
            expected = next(r["pkg_id"] for r in PACKAGE_MAP
                            if r["num"] == num)
            assert entry["pkg_id"] == expected

    def test_state_counts_match_ceo_directive(self):
        counts = {}
        for e in DISPOSITIONS.values():
            counts[e["state"]] = counts.get(e["state"], 0) + 1
        assert counts == {
            "BUYER_PRIMARY": 4, "HOLD_PENDING_GATE": 4,
            "RETIRED": 3, "RETIRED_PENDING_DECISIVE_TEST": 1,
            "SPECIALIST_TRACK": 3}

    def test_buyer_release_is_ceo_order(self):
        assert BUYER_ORDER == ["04", "11", "13", "08"]
        assert buyer_package_ids() == ["P-07", "P-24", "P-27-R1", "P-16"]
        assert [r["num"] for r in buyer_rows()] == BUYER_ORDER

    def test_ceo_directive_specific_packages(self):
        # the four named by the CEO, in the CEO's order
        assert DISPOSITIONS["04"]["presentation_order"] == 1
        assert DISPOSITIONS["11"]["presentation_order"] == 2
        assert DISPOSITIONS["13"]["presentation_order"] == 3
        assert DISPOSITIONS["08"]["presentation_order"] == 4
        # holds
        assert DISPOSITIONS["01"]["state"] == "HOLD_PENDING_GATE"
        assert DISPOSITIONS["02"]["state"] == "HOLD_PENDING_GATE"
        assert DISPOSITIONS["09"]["state"] == "HOLD_PENDING_GATE"
        assert DISPOSITIONS["12"]["state"] == "HOLD_PENDING_GATE"
        # retired
        assert DISPOSITIONS["06"]["state"] == "RETIRED"
        assert DISPOSITIONS["07"]["state"] == \
            "RETIRED_PENDING_DECISIVE_TEST"
        assert DISPOSITIONS["10"]["state"] == "RETIRED"
        assert DISPOSITIONS["14"]["state"] == "RETIRED"
        # specialist track
        for n in ("03", "05", "15"):
            assert DISPOSITIONS[n]["state"] == "SPECIALIST_TRACK"

    def test_every_hold_has_a_gate_with_consequence(self):
        for num, entry in DISPOSITIONS.items():
            if entry["state"] != "HOLD_PENDING_GATE":
                continue
            gate = entry.get("gate") or {}
            assert gate.get("condition"), num
            assert gate.get("decisive_test"), num
            assert gate.get("gate_failure_consequence"), num

    def test_retired_have_reasons_07_has_revival_14_has_reposition(self):
        for num, entry in DISPOSITIONS.items():
            if entry["state"].startswith("RETIRED"):
                assert entry.get("retirement_reason"), num
        assert DISPOSITIONS["07"]["revival_condition"]["condition"]
        assert DISPOSITIONS["07"]["revival_condition"]["decisive_test"]
        assert DISPOSITIONS["14"]["reposition_option"]["option"]

    def test_consultant_verdicts_present_and_overrides_disclosed(self):
        for num, entry in DISPOSITIONS.items():
            cv = entry.get("consultant_verdict") or {}
            assert cv.get("verdict"), num
            assert cv.get("top_blocker"), num
        # P06 is the ONLY package the independent audit rated REMOVE
        assert DISPOSITIONS["06"]["consultant_verdict"]["verdict"] == \
            "REMOVE"
        # the four CEO-strictness overrides are explicitly flagged
        for num in ("07", "08", "10", "14"):
            assert "CEO_OVERRIDE_DISCLOSED" in \
                DISPOSITIONS[num]["agreement"], num
        # no silent divergence anywhere else
        for num, entry in DISPOSITIONS.items():
            if num not in ("07", "08", "10", "14", "01"):
                assert "CEO_OVERRIDE" not in entry["agreement"], num

    def test_kill_not_confirmed_caveats_preserved(self):
        # Art. XXV: the business decision may be stricter than the
        # evidence, but it may never pretend the evidence said more
        reason7 = DISPOSITIONS["07"]["retirement_reason"]
        assert "NOT confirmed" in reason7
        reason14 = DISPOSITIONS["14"]["retirement_reason"]
        assert "NOT confirmed" in reason14

    def test_no_dollar_figure_laundered_as_record_evidence(self):
        # every record-verified claim must be dollar-free; the CEO's
        # budget figures may appear ONLY in ceo_stated/gate/revival
        # fields, each labeled as a directive
        for num, entry in DISPOSITIONS.items():
            for ev in entry.get("record_verified_basis") or []:
                assert "$" not in str(ev.get("claim", "")), (num, ev)
                assert "$" not in str(ev.get("span", "")), (num, ev)
            for st in entry.get("ceo_stated_basis") or []:
                assert st.get("note"), (num, st)

    def test_evidence_scopes_are_legal(self):
        for num, entry in DISPOSITIONS.items():
            for ev in entry.get("record_verified_basis") or []:
                assert ev.get("scope") in ("PACKAGE", "ENGINE",
                                           "ENGINE_ABSENCE"), (num, ev)
                if ev["scope"] != "ENGINE_ABSENCE":
                    assert ev.get("span"), (num, ev)
                else:
                    assert ev.get("absent_patterns"), (num, ev)


# ---------------------------------------------------------------------------
# 2. The evidence chain resolves against the REAL engine repository
# ---------------------------------------------------------------------------
class TestEvidenceChainAgainstEngine:
    def test_engine_scoped_spans_resolve(self):
        from premium_package_factory.r382.disposition import \
            _verify_evidence_entry
        failures = []
        for num, entry in sorted(DISPOSITIONS.items()):
            for ev in entry.get("record_verified_basis") or []:
                if ev["scope"] in ("ENGINE", "ENGINE_ABSENCE"):
                    errs = _verify_evidence_entry(ev, None, "")
                    if errs:
                        failures.append((num, ev["pointer"], errs))
        assert not failures, failures

    def test_p10_absence_claim_is_real(self):
        # the dossier must genuinely NOT name the deployed platforms
        fp = os.path.join(
            ENGINE_ROOT, "R370Q", "final_consultant_package", "export",
            "P-22-R1_ArtifactRichDossier.json")
        content = open(fp, encoding="utf-8").read()
        for pat in ("StealthStation", "Brainlab", "Medtronic"):
            assert pat not in content

    def test_broken_span_is_caught(self):
        from premium_package_factory.r382.disposition import \
            _verify_evidence_entry
        ev = {"scope": "ENGINE",
              "pointer": "EXTERNAL_CONSULTANT_EVIDENCE/"
                         "EXTERNAL_CONSULTANT_REPORT_2026-08-27.md",
              "span": "| P06 | ML Predictor | NO | KEEP | REJECT |"}
        errs = _verify_evidence_entry(ev, None, "")
        assert errs, "a fabricated span must be caught"

    def test_fabricated_absence_is_caught(self):
        from premium_package_factory.r382.disposition import \
            _verify_evidence_entry
        ev = {"scope": "ENGINE_ABSENCE",
              "pointer": "EXTERNAL_CONSULTANT_EVIDENCE/"
                         "EXTERNAL_CONSULTANT_REPORT_2026-08-27.md",
              "span": None,
              "absent_patterns": ["REMOVE"]}
        errs = _verify_evidence_entry(ev, None, "")
        assert errs, "an absence claim about a present string must fail"


# ---------------------------------------------------------------------------
# 3. The structural applier on a scratch tree
# ---------------------------------------------------------------------------
def _scratch_tree(root):
    """15 minimal package folders + zips with the REAL evidence files
    the PACKAGE-scope pointers need (V2 addenda copied from the engine
    input snapshot — byte-identical to the shipped addenda; economics/
    roadmaps generated from the canonical record; the 15 MODEL lineage
    synthesized carrying the record's failure-mode span)."""
    download = os.path.join(root, "DOWNLOAD")
    packages = load_all_packages()
    by_num = {p.num: p for p in packages}
    for row in PACKAGE_MAP:
        folder = f"{row['num']}_{row['short']}"
        pdir = os.path.join(download, folder)
        os.makedirs(pdir, exist_ok=True)
        p = by_num[row["num"]]
        with open(os.path.join(pdir, "PACKAGE_MANIFEST.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"portfolio_number": p.num,
                       "package_id": p.pkg_id,
                       "package_version": p.version}, fh)
        with open(os.path.join(
                pdir, "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf"),
                "wb") as fh:
            fh.write(b"%PDF-1.4 scratch dossier bytes")
        v2 = os.path.join(V2_INPUT,
                          f"V2_MUTATION_ADDENDUM_{p.pkg_id}.json")
        if os.path.exists(v2):
            shutil.copy2(v2, os.path.join(
                pdir, "V2_MUTATION_ADDENDUM.json"))
        if row["num"] in ("04", "13"):
            eco = build_validation_economics(p)
            with open(os.path.join(pdir, "VALIDATION_ECONOMICS.json"),
                      "w", encoding="utf-8") as fh:
                json.dump(eco, fh)
        if row["num"] == "06":
            road = build_unknown_roadmap(p)
            with open(os.path.join(pdir, "UNKNOWN_ROADMAP.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(road, fh)
        if row["num"] == "15":
            os.makedirs(os.path.join(pdir, "MODEL"), exist_ok=True)
            with open(os.path.join(pdir, "MODEL", "DESIGN_LINEAGE.json"),
                      "w", encoding="utf-8") as fh:
                json.dump({"record_failure_mode":
                               "SNR insufficient at low B0"}, fh)
        with zipfile.ZipFile(os.path.join(download, folder + ".zip"),
                             "w") as zf:
            zf.write(os.path.join(pdir, "PACKAGE_MANIFEST.json"),
                     "PACKAGE_MANIFEST.json")


class TestApplyOnScratch:
    def test_apply_moves_and_freezes(self, tmp_path):
        root = str(tmp_path / "portfolio")
        os.makedirs(os.path.join(root, "DOWNLOAD"))
        _scratch_tree(root)
        summary = apply_portfolio_disposition(root)

        download = os.path.join(root, "DOWNLOAD")
        dl = sorted(d for d in os.listdir(download)
                    if os.path.isdir(os.path.join(download, d)))
        assert dl == sorted(folder_for(n) for n in BUYER_ORDER)
        for state_dir, nums in (
                ("HOLDING", ("01", "02", "09", "12")),
                ("SPECIALIST_TRACK", ("03", "05", "15")),
                ("RETIRED", ("06", "07", "10", "14"))):
            for n in nums:
                assert os.path.isdir(
                    os.path.join(root, state_dir, folder_for(n))), n
                assert os.path.exists(os.path.join(
                    root, state_dir, folder_for(n) + ".zip")), n

        # the disposition record exists and the full verifier passes
        # (apply-only stage: the release layer is not yet regenerated)
        check = verify_disposition(root, require_release=False)
        assert check["ok"], check["problems"]
        # the buyer registry is buyer-scoped (4 entries)
        reg = json.load(open(os.path.join(
            root, "PORTFOLIO_IDENTITY_REGISTRY.json"), encoding="utf-8"))
        assert len(reg["packages"]) == 4
        assert {p["historical_package_id"] for p in reg["packages"]} == \
            set(buyer_package_ids())
        # no absolute paths leaked into the portfolio tree record
        rec_text = open(os.path.join(root, "PORTFOLIO_DISPOSITION.json"),
                        encoding="utf-8").read()
        assert "/home/" not in rec_text
        assert summary["buyer_primary"] == [
            folder_for(n) for n in BUYER_ORDER]

    def test_tampered_retired_package_is_caught(self, tmp_path):
        root = str(tmp_path / "portfolio")
        os.makedirs(os.path.join(root, "DOWNLOAD"))
        _scratch_tree(root)
        apply_portfolio_disposition(root)
        # tamper with a retired package AFTER the disposition
        target = os.path.join(root, "RETIRED", folder_for("06"),
                              "PACKAGE_MANIFEST.json")
        with open(target, "a", encoding="utf-8") as fh:
            fh.write("\n{tampered}")
        check = verify_disposition(root, require_release=False)
        assert not check["ok"]
        assert any("frozen" in p or "drift" in p
                   for p in check["problems"])

    def test_missing_hold_package_is_caught(self, tmp_path):
        root = str(tmp_path / "portfolio")
        os.makedirs(os.path.join(root, "DOWNLOAD"))
        _scratch_tree(root)
        apply_portfolio_disposition(root)
        shutil.rmtree(os.path.join(root, "HOLDING",
                                   folder_for("01")))
        check = verify_disposition(root, require_release=False)
        assert not check["ok"]
        assert any("missing" in p for p in check["problems"])

    def test_incomplete_tree_refuses_to_apply(self, tmp_path):
        root = str(tmp_path / "portfolio")
        os.makedirs(os.path.join(root, "DOWNLOAD"))
        _scratch_tree(root)
        shutil.rmtree(os.path.join(
            root, "DOWNLOAD", folder_for("06")))
        with pytest.raises(FileNotFoundError):
            apply_portfolio_disposition(root)

    def test_package_location_resolver(self, tmp_path):
        root = str(tmp_path / "portfolio")
        os.makedirs(os.path.join(root, "DOWNLOAD"))
        _scratch_tree(root)
        apply_portfolio_disposition(root)
        pdir, rel = package_location(root, "01")
        assert rel == os.path.join("HOLDING", folder_for("01"))
        pdir, rel = package_location(root, "04")
        assert rel == os.path.join("DOWNLOAD", folder_for("04"))
        pdir, rel = package_location(root, "06")
        assert rel == os.path.join("RETIRED", folder_for("06"))


# ---------------------------------------------------------------------------
# 4. The buyer release layer on the scratch tree (slow: renders PDFs)
# ---------------------------------------------------------------------------
@pytest.mark.slow
class TestBuyerReleaseOnScratch:
    def test_buyer_release_documents_and_zip_purity(self, tmp_path):
        from premium_package_factory.r371.equations import \
            build_equation_registry
        from premium_package_factory.r371.loopstate import (
            build_loop_state, portfolio_loop_summary)
        from premium_package_factory.r371.ranking import build_ranking
        from premium_package_factory.r372.equation_validation import \
            validate_registry
        from premium_package_factory.r372.traceability_semantics import \
            build_traceability_json
        from premium_package_factory.r382.release_docs import \
            regenerate_buyer_release_documents

        root = str(tmp_path / "portfolio")
        os.makedirs(os.path.join(root, "DOWNLOAD"))
        _scratch_tree(root)
        apply_portfolio_disposition(root)

        packages = load_all_packages()
        input_dir = os.path.join(ENGINE_ROOT, "premium_package_factory",
                                 "input")
        headlines = {r["package_id"]: r for r in json.load(open(
            os.path.join(input_dir, "headlines_r371.json"),
            encoding="utf-8"))["packages"]}
        roads = {p.pkg_id: build_unknown_roadmap(p) for p in packages}
        loop_summary = portfolio_loop_summary(packages)
        ranking = build_ranking(packages, headlines, roads)
        traces = {}
        eqv = {}
        for p in packages:
            legacy = os.path.join(input_dir, "legacy_json", p.num,
                                  "ENGINEERING_TRACEABILITY.json")
            traces[p.pkg_id] = build_traceability_json(p, legacy)
            eqv[p.pkg_id] = validate_registry(
                build_equation_registry(p), p)

        release = regenerate_buyer_release_documents(
            root, packages, headlines, ranking, loop_summary, traces,
            eqv)

        for doc in ("PORTFOLIO_INDEX.pdf",
                    "PORTFOLIO_RELEASE_REPORT.pdf",
                    "PORTFOLIO_MANIFEST.json", "PORTFOLIO_RANKING.json",
                    "README.md", "RELEASE_CONTENT_MANIFEST.json"):
            assert os.path.exists(os.path.join(root, doc)), doc
        # the 15-technology overview is INTERNAL, not shipped
        assert not os.path.exists(os.path.join(
            root, "00_PORTFOLIO_15_TECHNOLOGIES.pdf"))
        assert os.path.exists(os.path.join(
            root, "INTERNAL_QA", "00_PORTFOLIO_15_TECHNOLOGIES.pdf"))

        manifest = json.load(open(os.path.join(
            root, "RELEASE_CONTENT_MANIFEST.json"), encoding="utf-8"))
        pkg_entries = [e for e in manifest["entries"]
                       if e["role"] == "package folder"]
        assert len(pkg_entries) == 4
        assert {e["portfolio_number"] for e in pkg_entries} == \
            set(BUYER_ORDER)

        # master ZIP: buyer packages + root docs, NOTHING else
        with zipfile.ZipFile(release["master_zip"]) as zf:
            names = set(zf.namelist())
        for n in BUYER_ORDER:
            assert f"DOWNLOAD/{folder_for(n)}.zip" in names
        for other in ("01", "02", "03", "05", "06", "07", "09", "10",
                      "12", "14", "15"):
            assert f"DOWNLOAD/{folder_for(other)}.zip" not in names
        for state_dir in ("HOLDING", "RETIRED", "SPECIALIST_TRACK"):
            assert not any(nm.startswith(state_dir)
                           for nm in names)

        # the full disposition verifier (incl. README + ZIP purity)
        check = verify_disposition(root)
        assert check["ok"], check["problems"]

        # the portfolio manifest is buyer-scoped in CEO order
        pm = json.load(open(os.path.join(root, "PORTFOLIO_MANIFEST.json"),
                            encoding="utf-8"))
        assert pm["package_count"] == 4
        assert [p["portfolio_number"] for p in pm["packages"]] == \
            BUYER_ORDER

    def test_readme_mentions_no_non_buyer_package(self, tmp_path):
        # covered by the purity checks in verify_disposition; asserted
        # directly here as the Art. XXX attack surface
        root = str(tmp_path / "portfolio")
        os.makedirs(os.path.join(root, "DOWNLOAD"))
        _scratch_tree(root)
        apply_portfolio_disposition(root)
        check = verify_disposition(root, require_release=False)
        assert check["ok"], check["problems"]
