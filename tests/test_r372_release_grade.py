"""
test_r372_release_grade.py — R372 adversarial test suite.

Constitution basis:
  Art. V     — positive AND negative AND metamorphic cases
  Art. XVI   — code is a hypothesis; tests are evidence of enforcement
  Art. XVII  — every control has an attempted bypass
  Art. XXX   — never optimize the evaluator: each check must FAIL when the
               underlying artifact is wrong

Covers the seven R372 directives:
  R372-1 traceability semantics (explicit classification + justifications)
  R372-2 diagram technical adequacy (mechanism label provenance,
        experiment spec roles)
  R372-3 equation validation (metadata + dimensional consistency)
  R372-4 commercial-evidence schema (10 fields + 8-step workflow)
  R372-5 buyer five-decision-criticals rendering
  R372-6 V2 mutation propagation (adversarial: tampered PDF must fail)
  R372-7 repository boundary (adversarial: leaked file must fail)
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..")))

from premium_package_factory.r371.canonical_source import load_all_packages
from premium_package_factory.r371.commercial import (
    build_commercial_evidence, count_unsourced_claims)
from premium_package_factory.r372 import boundary_guard
from premium_package_factory.r372.diagram_adequacy import (
    experiment_diagram_spec, validate_experiment_spec,
    record_diagram, validate_mechanism_diagram)
from premium_package_factory.r372.equation_validation import (
    dimensional_check, validate_registry, validation_complete)
from premium_package_factory.r372.traceability_semantics import (
    classify_package)
from premium_package_factory.r371.equations import build_equation_registry

PACKAGES = load_all_packages()
BY_ID = {p.pkg_id: p for p in PACKAGES}


# ---------------------------------------------------------------------------
# R372-1 traceability semantics
# ---------------------------------------------------------------------------

class TestTraceabilitySemantics:
    def test_every_package_classified_with_full_summary(self):
        for p in PACKAGES:
            r = classify_package(p)
            s = r["summary"]
            assert s["total_DIs"] == len(p.design_inputs)
            for k in ("critical_DIs", "explicitly_linked", "partially_linked",
                      "unknown", "not_applicable", "orphan_DOs",
                      "orphan_FMs"):
                assert k in s
            assert r["release_gate"]["traceability_state"] in (
                "TRACEABILITY_COMPLETE", "TRACEABILITY_PARTIAL",
                "TRACEABILITY_UNKNOWN", "TRACEABILITY_NOT_APPLICABLE")

    def test_real_packages_all_justified(self):
        """Positive: the 15 real packages pass with record-cited
        justifications on every non-explicit slot."""
        for p in PACKAGES:
            r = classify_package(p)
            assert r["release_gate"]["incomplete_parts_explicitly_justified"], \
                p.pkg_id

    def test_p01_known_explicit_links(self):
        """Metamorphic anchor: P-01 DI-003 (performance acceptance) is
        explicitly linked to a verification requirement; DI-007 (prediction
        lead time) is explicitly linked to a failure mode."""
        r = classify_package(BY_ID["P-01"])
        by_di = {c["design_input_id"]: c for c in r["chains"]}
        assert by_di["DI-003"]["slots"]["verification"]["state"] == "EXPLICIT"
        assert by_di["DI-007"]["slots"]["failure_mode"]["state"] == "EXPLICIT"
        assert by_di["DI-003"]["chain_state"] == "TRACEABILITY_PARTIAL"

    def test_no_ambiguous_passed_flag(self):
        """The shipped file carries release_gate with an explicit state and
        a reason — never a bare boolean pass."""
        r = classify_package(BY_ID["P-01"])
        assert "passed" not in r
        assert "supersedes_legacy_passed_flag" in r["release_gate"]
        assert r["release_gate"]["reason"]

    def test_unjustified_slot_fails_gate(self):
        """NEGATIVE: a DI whose value is UNKNOWN with no resolution plan and
        NO recorded verification makes the package fail the pass rule."""

        class FakePkg:
            pkg_id = "P-XX"
            num = "99"
            design_inputs = [{
                "id": "DI-001", "input": "Broken input",
                "value": "UNKNOWN",
            }]
            design_outputs = []
            failure_analysis = []
            verification = []

        r = classify_package(FakePkg())
        assert r["release_gate"]["incomplete_parts_explicitly_justified"] \
            is False
        assert "DI-001.verification" in r["release_gate"]["unjustified_slots"]

    def test_orphan_outputs_justified_from_status(self):
        """Orphan design outputs carry their recorded status as the
        justification basis."""
        r = classify_package(BY_ID["P-01"])
        for orphan in r["orphan_design_outputs"]:
            assert orphan["justified"] is True
            assert orphan["justification"]["data_basis"]


# ---------------------------------------------------------------------------
# R372-2 diagram technical adequacy
# ---------------------------------------------------------------------------

class TestExperimentDiagramAdequacy:
    def test_all_15_specs_valid(self):
        headlines = {r["package_id"]: r for r in json.load(open(
            "premium_package_factory/input/headlines_r371.json",
            encoding="utf-8"))["packages"]}
        for p in PACKAGES:
            spec = experiment_diagram_spec(p, headlines[p.pkg_id])
            check = validate_experiment_spec(spec, p, headlines[p.pkg_id])
            assert check["ok"], (p.pkg_id, check["failures"])

    def test_spec_roles_present(self):
        headlines = {r["package_id"]: r for r in json.load(open(
            "premium_package_factory/input/headlines_r371.json",
            encoding="utf-8"))["packages"]}
        spec = experiment_diagram_spec(BY_ID["P-01"], headlines["P-01"])
        for role in ("test_article", "stimulus", "instrumentation",
                     "measured_outputs", "control_variables",
                     "decision_criterion", "kill_condition"):
            assert role in spec["roles"]
            assert spec["roles"][role]["content"]

    def test_control_variables_honesty_marker(self):
        headlines = {r["package_id"]: r for r in json.load(open(
            "premium_package_factory/input/headlines_r371.json",
            encoding="utf-8"))["packages"]}
        spec = experiment_diagram_spec(BY_ID["P-01"], headlines["P-01"])
        assert spec["roles"]["control_variables"]["content"].startswith(
            "NOT_SEPARATELY_RECORDED")

    def test_negative_invented_control_variables_fail(self):
        """NEGATIVE: presenting an invented control list (no marker) fails."""
        headlines = {r["package_id"]: r for r in json.load(open(
            "premium_package_factory/input/headlines_r371.json",
            encoding="utf-8"))["packages"]}
        spec = experiment_diagram_spec(BY_ID["P-01"], headlines["P-01"])
        spec["roles"]["control_variables"]["content"] = "37C, pH 7.4"
        check = validate_experiment_spec(spec, BY_ID["P-01"],
                                         headlines["P-01"])
        failed = {f["check"] for f in check["failures"]}
        assert "CONTROL_VARIABLES_INVENTED" in failed

    def test_negative_drifted_kill_condition_fails(self):
        headlines = {r["package_id"]: r for r in json.load(open(
            "premium_package_factory/input/headlines_r371.json",
            encoding="utf-8"))["packages"]}
        spec = experiment_diagram_spec(BY_ID["P-01"], headlines["P-01"])
        spec["roles"]["kill_condition"]["content"] = "nothing would kill it"
        check = validate_experiment_spec(spec, BY_ID["P-01"],
                                         headlines["P-01"])
        failed = {f["check"] for f in check["failures"]}
        assert "KILL_CONDITION_DRIFT" in failed

    def test_negative_nonverbatim_test_article_fails(self):
        headlines = {r["package_id"]: r for r in json.load(open(
            "premium_package_factory/input/headlines_r371.json",
            encoding="utf-8"))["packages"]}
        spec = experiment_diagram_spec(BY_ID["P-01"], headlines["P-01"])
        spec["roles"]["test_article"]["content"] = "polished titanium widget"
        check = validate_experiment_spec(spec, BY_ID["P-01"],
                                         headlines["P-01"])
        failed = {f["check"] for f in check["failures"]}
        assert "TEST_ARTICLE_NOT_VERBATIM" in failed


class TestMechanismDiagramAdequacy:
    @pytest.fixture(scope="class")
    def headlines(self):
        return {r["package_id"]: r for r in json.load(open(
            "premium_package_factory/input/headlines_r371.json",
            encoding="utf-8"))["packages"]}

    @pytest.fixture(scope="class")
    def recordings(self, headlines):
        from premium_package_factory.diagrams import factory as df
        import tempfile
        tmp = tempfile.mkdtemp()
        df.OUTPUT_DIR = tmp
        FUNCS = {
            "P-01": df.diagram_P01, "P-02": df.diagram_P02,
            "P-04": df.diagram_P04, "P-07": df.diagram_P07,
            "P-11": df.diagram_P11, "P-13": df.diagram_P13,
            "P-15-R1": df.diagram_P15R1, "P-16": df.diagram_P16,
            "P-21-R1": df.diagram_P21R1, "P-22-R1": df.diagram_P22R1,
            "P-24": df.diagram_P24, "P-26": df.diagram_P26,
            "P-27-R1": df.diagram_P27R1, "P-28": df.diagram_P28,
            "P-29": df.diagram_P29,
        }
        out = {}
        for p in PACKAGES:
            out[p.pkg_id] = record_diagram(
                (lambda f: (lambda: f()))(FUNCS[p.pkg_id]))
        return out

    def test_all_15_mechanism_diagrams_adequate(self, headlines, recordings):
        for p in PACKAGES:
            v = validate_mechanism_diagram(p, recordings[p.pkg_id],
                                           headlines[p.pkg_id])
            assert v["ok"], (p.pkg_id, v["failures"])

    def test_label_provenance_classified(self, headlines, recordings):
        v = validate_mechanism_diagram(BY_ID["P-01"],
                                       recordings["P-01"],
                                       headlines["P-01"])
        counts = v["label_provenance_counts"]
        assert counts.get("R370Q_EXPORT", 0) >= 3
        assert counts.get("UNTRACED", 0) == 0

    def test_arrows_recorded_with_direction(self, recordings):
        for p in PACKAGES:
            assert len(recordings[p.pkg_id].arrows) >= 3, p.pkg_id
            for (a, b) in recordings[p.pkg_id].arrows:
                assert a[:2] != b[:2] or a != b

    def test_negative_invented_number_fails(self, headlines, recordings):
        """NEGATIVE (Art. XVII): a label carrying a number absent from every
        recorded source must fail NO_INVENTED_NUMBERS."""
        rec = recordings["P-01"]

        class TamperedRecording:
            labels = lambda self: rec.labels() + ["magic 7.77 parameter"]
            arrows = rec.arrows
            boxes = rec.boxes

        v = validate_mechanism_diagram(BY_ID["P-01"], TamperedRecording(),
                                       headlines["P-01"])
        failed = {f["check"] for f in v["failures"]}
        assert "NO_INVENTED_NUMBERS" in failed or "LABEL_PROVENANCE" in failed

    def test_negative_untraced_label_fails(self, headlines, recordings):
        rec = recordings["P-01"]

        class TamperedRecording:
            labels = lambda self: rec.labels() + ["Flux Capacitor Mk II"]
            arrows = rec.arrows
            boxes = rec.boxes

        v = validate_mechanism_diagram(BY_ID["P-01"], TamperedRecording(),
                                       headlines["P-01"])
        failed = {f["check"] for f in v["failures"]}
        assert "LABEL_PROVENANCE" in failed

    def test_p21r1_depicts_canonical_uwb_not_rfid(self, recordings):
        """The P-21-R1 diagram must depict the canonical UWB/TOA/SAR-bounded
        architecture (the R370-era RFID depiction contradicted the record)."""
        labels = " | ".join(recordings["P-21-R1"].labels())
        assert "UWB" in labels
        assert "868" not in labels
        assert "TOA" in labels


# ---------------------------------------------------------------------------
# R372-3 equation validation
# ---------------------------------------------------------------------------

class TestEquationValidation:
    def test_dimensional_consistent_detected(self):
        cps = [
            {"name": "Flow rate Q", "unit": "mL/min"},
            {"name": "Pressure dP", "unit": "mmHg"},
            {"name": "Conductance G", "unit": "mL/min/mmHg"},
        ]
        r = dimensional_check("Q = dP * G", cps)
        assert r["state"] == "DIMENSIONALLY_CONSISTENT"

    def test_dimensional_inconsistent_detected(self):
        cps = [
            {"name": "Flow rate Q", "unit": "mL/min"},
            {"name": "Pressure dP", "unit": "mmHg"},
        ]
        r = dimensional_check("Q = dP * dP", cps)
        assert r["state"] == "DIMENSIONALLY_INCONSISTENT"

    def test_dimension_mixing_in_addition_is_inconsistent(self):
        cps = [
            {"name": "Flow rate Q", "unit": "mL/min"},
            {"name": "Pressure dP", "unit": "mmHg"},
            {"name": "Conductance G", "unit": "mL/min/mmHg"},
        ]
        r = dimensional_check("Q = dP + G", cps)
        assert r["state"] == "DIMENSIONALLY_INCONSISTENT"

    def test_missing_units_not_evaluable_never_guessed(self):
        """Art. VI/XXV: symbols without recorded units give an explicit
        NOT_EVALUABLE — never a guessed standard unit."""
        cps = [{"name": "Flow rate Q", "unit": "mL/min"}]
        r = dimensional_check("Q = r^4 * dP", cps)
        assert r["state"] == "NOT_EVALUABLE_UNITS_UNRECORDED"
        assert "r" in r["symbols_without_recorded_units"]

    def test_no_equality_not_evaluable(self):
        r = dimensional_check("P(occlude_i | F_obs)", [])
        assert r["state"] == "NOT_EVALUABLE_NO_EQUALITY"

    def test_all_66_equations_validated(self):
        total = 0
        for p in PACKAGES:
            reg = build_equation_registry(p)
            val = validate_registry(reg, p)
            total += val["equation_count"]
            for v in val["validations"]:
                assert validation_complete(v), (p.pkg_id, v["equation_id"])
                for field in ("variables", "variable_units", "domain",
                              "operating_regime", "assumptions",
                              "applicability", "limitations"):
                    assert field in v
        assert total == 66

    def test_portfolio_has_zero_inconsistent(self):
        for p in PACKAGES:
            reg = build_equation_registry(p)
            val = validate_registry(reg, p)
            assert val["inconsistent_equations"] == [], p.pkg_id

    def test_negative_incomplete_validation_rejected(self):
        v = {"variables": [], "dimensional_check": {"state": "WEIRD"}}
        assert validation_complete(v) is False


# ---------------------------------------------------------------------------
# R372-4 commercial evidence schema
# ---------------------------------------------------------------------------

class TestCommercialSchema:
    @pytest.fixture(scope="class")
    def evidence(self):
        return build_commercial_evidence(BY_ID["P-01"])

    def test_ten_field_schema(self, evidence):
        market = next(s for s in evidence["commercial_evidence"]
                      if s["section"] == "MARKET_EVIDENCE")
        for field in ("market_definition", "geography", "year",
                      "population_basis", "source", "source_hash",
                      "methodology", "estimate", "uncertainty",
                      "limitations"):
            assert field in market, field

    def test_eight_step_establishment_workflow(self, evidence):
        market = next(s for s in evidence["commercial_evidence"]
                      if s["section"] == "MARKET_EVIDENCE")
        wf = market["establishment_workflow"]
        assert len(wf) == 8
        names = [s["name"] for s in wf]
        assert names[0] == "market definition"
        assert names[1] == "source acquisition"
        assert names[-1] == "uncertainty"
        for step in wf:
            assert step["action"]
            assert "status" in step

    def test_market_definition_from_recorded_domain(self, evidence):
        market = next(s for s in evidence["commercial_evidence"]
                      if s["section"] == "MARKET_EVIDENCE")
        assert market["market_definition"]["device_category"] == \
            BY_ID["P-01"].eng["technology_domain"]

    def test_zero_numeric_market_values(self):
        for p in PACKAGES:
            ev = build_commercial_evidence(p)
            assert count_unsourced_claims(ev) == 0, p.pkg_id

    def test_negative_numeric_value_counted(self):
        ev = build_commercial_evidence(BY_ID["P-01"])
        market = next(s for s in ev["commercial_evidence"]
                      if s["section"] == "MARKET_EVIDENCE")
        market["estimate"][0]["value"] = 2100000000
        assert count_unsourced_claims(ev) == 1


# ---------------------------------------------------------------------------
# R372-6 V2 propagation (adversarial with a tampered PDF)
# ---------------------------------------------------------------------------

class TestV2Propagation:
    @pytest.fixture(scope="class")
    def mini_portfolio(self, tmp_path_factory):
        """Synthetic single-package portfolio with a real (tiny) buyer PDF
        containing V1 and V2 text, for tampering experiments."""
        from reportlab.pdfgen import canvas as pdfcanvas
        root = tmp_path_factory.mktemp("mini_portfolio")
        pkg = BY_ID["P-01"]
        pdir = root / "DOWNLOAD" / pkg.folder
        pdir.mkdir(parents=True)
        addendum = {
            "v2_version": "2.0",
            "mutations": [{
                "mutation_id": "MUT-TEST-001",
                "field_affected": "test field",
                "v1_text": "old defective claim",
                "v2_text": "corrected claim with provenance",
            }],
        }
        (pdir / "V2_MUTATION_ADDENDUM.json").write_text(
            json.dumps(addendum), encoding="utf-8")
        (pdir / "PACKAGE_MUTATION_CERTIFICATE_P-01_V2.json").write_text(
            "{}", encoding="utf-8")
        pm = {"package_version": "2.0"}
        (pdir / "PACKAGE_MANIFEST.json").write_text(
            json.dumps(pm), encoding="utf-8")
        registry = {"packages": [{
            "historical_package_id": "P-01", "status": "V2"}]}
        (root / "PORTFOLIO_IDENTITY_REGISTRY.json").write_text(
            json.dumps(registry), encoding="utf-8")
        # tiny buyer PDFs carrying the V2 (not V1) text
        for name in ("00_PACKAGE_README.pdf",
                     "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
                     "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
                     "03_BUYER_DECISION_CARD.pdf",
                     "04_EVIDENCE_SUMMARY.pdf",
                     "05_TRANSFER_MANIFEST.pdf"):
            c = pdfcanvas.Canvas(str(pdir / name))
            c.drawString(72, 720, "corrected claim with provenance")
            c.save()
        import zipfile
        zpath = root / "DOWNLOAD" / f"{pkg.folder}.zip"
        with zipfile.ZipFile(zpath, "w") as zf:
            for f in sorted(os.listdir(pdir)):
                zf.write(pdir / f, f)
        # engine-side input snapshot (byte-identical)
        input_dir = root / "inputs"
        input_dir.mkdir()
        (input_dir / "V2_MUTATION_ADDENDUM_P-01.json").write_text(
            json.dumps(addendum), encoding="utf-8")
        return {"root": str(root), "pkg": pkg,
                "input_dir": str(input_dir)}

    def test_clean_propagation_passes(self, mini_portfolio):
        from premium_package_factory.r372 import v2_propagation
        r = v2_propagation.verify_package_v2(
            mini_portfolio["root"], mini_portfolio["pkg"],
            os.path.join(mini_portfolio["input_dir"],
                         "V2_MUTATION_ADDENDUM_P-01.json"))
        assert r["all_pass"], [c for c in r["checks"] if c["status"] != "PASS"]

    def test_tampered_pdf_with_v1_text_fails(self, mini_portfolio):
        """NEGATIVE (the R370 defect): a buyer PDF that still contains the
        V1 text must fail V1_ABSENT."""
        from reportlab.pdfgen import canvas as pdfcanvas
        from premium_package_factory.r372 import v2_propagation
        pdir = os.path.join(mini_portfolio["root"], "DOWNLOAD",
                            mini_portfolio["pkg"].folder)
        c = pdfcanvas.Canvas(os.path.join(pdir, "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf"))
        c.drawString(72, 720, "old defective claim")
        c.save()
        r = v2_propagation.verify_package_v2(
            mini_portfolio["root"], mini_portfolio["pkg"],
            os.path.join(mini_portfolio["input_dir"],
                         "V2_MUTATION_ADDENDUM_P-01.json"))
        failed = {c["check"] for c in r["checks"] if c["status"] == "FAIL"}
        assert "V1_ABSENT[MUT-TEST-001]" in failed
        assert r["all_pass"] is False

    def test_tampered_addendum_fails_verbatim(self, mini_portfolio):
        from premium_package_factory.r372 import v2_propagation
        pdir = os.path.join(mini_portfolio["root"], "DOWNLOAD",
                            mini_portfolio["pkg"].folder)
        fp = os.path.join(pdir, "V2_MUTATION_ADDENDUM.json")
        data = json.load(open(fp, encoding="utf-8"))
        data["mutations"][0]["v2_text"] = "sneaky edited text"
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        r = v2_propagation.verify_package_v2(
            mini_portfolio["root"], mini_portfolio["pkg"],
            os.path.join(mini_portfolio["input_dir"],
                         "V2_MUTATION_ADDENDUM_P-01.json"))
        failed = {c["check"] for c in r["checks"] if c["status"] == "FAIL"}
        assert "ADDENDUM_VERBATIM" in failed

    def test_extension_mutation_v1_prefix_allowed(self, mini_portfolio):
        """A V2 that extends V1 (prefix) is acceptable: the V1 occurrence
        must be judged only as part of the V2 rendering."""
        from reportlab.pdfgen import canvas as pdfcanvas
        from premium_package_factory.r372 import v2_propagation
        root = mini_portfolio["root"]
        pkg = mini_portfolio["pkg"]
        pdir = os.path.join(root, "DOWNLOAD", pkg.folder)
        addendum = {
            "v2_version": "2.0",
            "mutations": [{
                "mutation_id": "MUT-EXT-001",
                "field_affected": "disclosure",
                "v1_text": "No dataset exists",
                "v2_text": "No dataset exists. Extended disclosure follows.",
            }],
        }
        with open(os.path.join(pdir, "V2_MUTATION_ADDENDUM.json"), "w",
                  encoding="utf-8") as f:
            json.dump(addendum, f)
        with open(os.path.join(mini_portfolio["input_dir"],
                               "V2_MUTATION_ADDENDUM_P-01.json"), "w",
                  encoding="utf-8") as f:
            json.dump(addendum, f)
        c = pdfcanvas.Canvas(os.path.join(pdir, "04_EVIDENCE_SUMMARY.pdf"))
        c.drawString(72, 720,
                     "No dataset exists. Extended disclosure follows.")
        c.save()
        r = v2_propagation.verify_package_v2(root, pkg,
                                             os.path.join(
                                                 mini_portfolio["input_dir"],
                                                 "V2_MUTATION_ADDENDUM_P-01.json"))
        v1_absent = next(c for c in r["checks"]
                         if c["check"] == "V1_ABSENT[MUT-EXT-001]")
        assert v1_absent["status"] == "PASS"


# ---------------------------------------------------------------------------
# R372-7 repository boundary
# ---------------------------------------------------------------------------

class TestRepoBoundary:
    def _clean_tree(self, tmp_path):
        root = tmp_path / "portfolio"
        (root / "DOWNLOAD").mkdir(parents=True)
        (root / "README.md").write_text("# release\n", encoding="utf-8")
        return str(root)

    def test_clean_tree_passes(self, tmp_path):
        r = boundary_guard.verify_portfolio_boundary(self._clean_tree(tmp_path))
        assert r["ok"], r["problems"]

    def test_python_file_in_release_fails(self, tmp_path):
        root = self._clean_tree(tmp_path)
        with open(os.path.join(root, "DOWNLOAD", "factory.py"), "w") as f:
            f.write("print('engine code leak')")
        r = boundary_guard.verify_portfolio_boundary(root)
        assert not r["ok"]
        assert any("factory.py" in p for p in r["problems"])

    def test_local_path_leak_fails(self, tmp_path):
        root = self._clean_tree(tmp_path)
        with open(os.path.join(root, "DOWNLOAD", "notes.json"), "w") as f:
            json.dump({"built_from": "/home/z/secret/path"}, f)
        r = boundary_guard.verify_portfolio_boundary(root)
        assert not r["ok"]
        assert any("local filesystem path" in p for p in r["problems"])

    def test_local_path_leak_inside_pdf_fails(self, tmp_path):
        """NEGATIVE: a buyer PDF whose TEXT carries a local filesystem path
        must be caught (scan runs on extracted text, not raw bytes — binary
        streams are not false-positive surfaces)."""
        from reportlab.pdfgen import canvas as pdfcanvas
        root = self._clean_tree(tmp_path)
        fp = os.path.join(root, "DOWNLOAD", "01_x", "leak.pdf")
        os.makedirs(os.path.dirname(fp))
        c = pdfcanvas.Canvas(fp)
        c.drawString(72, 720, "generated from /home/z/secret/build")
        c.save()
        r = boundary_guard.verify_portfolio_boundary(root)
        assert not r["ok"]
        assert any("local filesystem path" in p for p in r["problems"])

    def test_cemetery_artifact_fails(self, tmp_path):
        root = self._clean_tree(tmp_path)
        with open(os.path.join(root, "DOWNLOAD", "data.json"), "w") as f:
            json.dump({"cemetery_entry": "CE-804"}, f)
        r = boundary_guard.verify_portfolio_boundary(root)
        assert not r["ok"]

    def test_engine_side_missing_inputs_fails(self, tmp_path):
        r = boundary_guard.verify_engine_boundary(str(tmp_path), str(tmp_path))
        assert not r["ok"]
        assert any("release-input missing" in p for p in r["problems"])

    def test_engine_side_real_engine_passes(self):
        engine_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), ".."))
        r = boundary_guard.verify_engine_boundary(
            engine_root,
            os.path.join(engine_root, "premium_package_factory", "input"))
        assert r["ok"], r["problems"]


# ---------------------------------------------------------------------------
# R372-5 buyer five-decision-criticals (rendered content)
# ---------------------------------------------------------------------------

class TestBuyerCriticals:
    @pytest.fixture(scope="class")
    def built(self, tmp_path_factory):
        """One full build; the buyer card must carry the five criticals."""
        from premium_package_factory.r371 import build_v5
        root = tmp_path_factory.mktemp("r372_build")
        portfolio = root / "portfolio"
        portfolio.mkdir()
        build_v5.build(str(portfolio), work_dir=str(root / "work"))
        return str(portfolio)

    def test_five_criticals_in_every_card(self, built):
        import subprocess
        import re
        for p in PACKAGES:
            fp = os.path.join(built, "DOWNLOAD", p.folder,
                              "03_BUYER_DECISION_CARD.pdf")
            r = subprocess.run(["pdftotext", "-raw", fp, "-"],
                               capture_output=True, text=True)
            txt = re.sub(r"\s+", " ", r.stdout or "")
            for header in ("THE FIVE DECISION CRITICALS",
                           "1. WHAT IS THE INVENTION?",
                           "2. WHAT IS ACTUALLY ESTABLISHED?",
                           "3. WHAT REMAINS UNCERTAIN?",
                           "4. CHEAPEST DECISIVE NEXT EXPERIMENT?",
                           "5. WHAT EVIDENCE WOULD CAUSE THE BUYER TO STOP?"):
                assert header in txt, (p.pkg_id, header)

    def test_nine_question_architecture_retained(self, built):
        import subprocess
        import re
        fp = os.path.join(built, "DOWNLOAD", "01_multisegment_flow_control",
                          "03_BUYER_DECISION_CARD.pdf")
        r = subprocess.run(["pdftotext", "-raw", fp, "-"],
                           capture_output=True, text=True)
        txt = re.sub(r"\s+", " ", r.stdout or "")
        for q in ("1. WHAT IS IT?", "9. WHAT WOULD KILL THE PROJECT?"):
            assert q in txt

    def test_full_r372_gate_passes(self, built):
        from premium_package_factory.r372 import acceptance_r372
        report = acceptance_r372.run_r372_acceptance(built)
        failed = [c for c in report["conditions"] if c["status"] != "PASS"]
        assert not failed, failed
        assert report["all_pass"] is True
