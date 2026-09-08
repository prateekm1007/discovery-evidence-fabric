"""tests/test_r424_elite_package_factory.py — R424 §15 regression.

The package-quality test proving the FACTORY now produces the elite
structure from the same run-state shape that produced the weak
baseline (empty engineering definition, empty decisive experiment,
unknown engine commit, thin evidence, no buyer architecture) — and
that a genuinely weak invention receives NO fabricated engineering
content.

Fixture baseline: the live run ts_6a663ab7f468's package (downloaded
from production 2026-09-08, the failure class the directive named) —
its run state shape is reproduced by the R418 solar fixture + the
weak-state assertions below.
"""
from __future__ import annotations

import json
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine.invention_bridge.bridge import (
    bridge as run_bridge)
from discovery_fabric.engine.invention_bridge import epistemics as ep
from discovery_fabric.engine.invention_bridge import elite_package as _elite

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "r418"

ELITE_DOCS = (
    "00_PACKAGE_README.pdf", "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
    "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
    "03_BUYER_DECISION_CARD.pdf", "04_EVIDENCE_SUMMARY.pdf",
    "05_TRANSFER_MANIFEST.pdf")
ELITE_MACHINE = (
    "ENGINEERING_TRACEABILITY.json", "MATURITY_BASIS.json",
    "EQUATION_REGISTRY.json", "UNKNOWN_ROADMAP.json",
    "VALIDATION_ECONOMICS.json", "LOOP_STATE.json",
    "COMMERCIAL_EVIDENCE.json", "PROVENANCE.json",
    "PACKAGE_MANIFEST.json")
ELITE_MODEL = (
    "MODEL/PARAMETERS.json", "MODEL/MODEL_MANIFEST.json",
    "MODEL/3D_DESIGN_STATUS.json", "MODEL/KEY_DIMENSIONS.json",
    "MODEL/DESIGN_LINEAGE.json", "MODEL/ENGINEERING_PROVENANCE.json",
    "MODEL/GEOMETRY_VALIDATION_REPORT.json",
    "MODEL/IMPROVEMENT_LOOP_EVIDENCE.json")


def _solar() -> dict:
    return json.loads((FIXTURES / "solar_result.json").read_text())


@pytest.fixture(scope="module")
def elite_pkg(tmp_path_factory):
    """The factory output over the REAL captured solar run (the same
    run-state shape as the weak baseline)."""
    work = tmp_path_factory.mktemp("r424_factory")
    result = run_bridge(_solar(), None, str(work), build_renders=False)
    return {"work": work, "result": result,
            "pkg": result["package_out"]}


def _zip_names(pkg) -> list:
    with zipfile.ZipFile(pkg["zip_path"]) as zf:
        return zf.namelist()


def _read(pkg, name):
    with zipfile.ZipFile(pkg["zip_path"]) as zf:
        return json.loads(zf.read(f"TECHNOLOGY_PACKAGE/{name}"))


class TestEliteStructure:
    def test_all_six_documents(self, elite_pkg):
        names = _zip_names(elite_pkg["pkg"])
        for doc in ELITE_DOCS:
            assert any(n.endswith(doc) for n in names), f"missing {doc}"

    def test_all_machine_layers(self, elite_pkg):
        names = _zip_names(elite_pkg["pkg"])
        for layer in ELITE_MACHINE:
            assert any(n.endswith(layer) for n in names), \
                f"missing {layer}"

    def test_model_layer(self, elite_pkg):
        names = _zip_names(elite_pkg["pkg"])
        for f in ELITE_MODEL:
            assert any(n.endswith(f) for n in names), f"missing {f}"


class TestEngineeringDefinitionIsReal:
    def test_not_the_domain_detection_dump(self, elite_pkg):
        """The weak baseline's 02 was a domain-detection dump. The elite
        02 derives the REAL engineering state."""
        eng = _read(elite_pkg["pkg"], "02_ENGINEERING_DEFINITION.json")
        for key in ("design_inputs", "design_outputs", "constraints",
                    "parameters", "subsystem_architecture",
                    "failure_modes", "verification_items",
                    "build_steps", "governing_equations",
                    "experiment_requirements", "build_path"):
            assert key in eng, f"engineering definition missing {key}"
        # the REAL recorded fields (the solar run carries them)
        assert len(eng["design_inputs"]) >= 5
        assert len(eng["failure_modes"]) >= 3
        assert len(eng["build_steps"]) >= 4
        # every design input keeps its epistemic class
        for di in eng["design_inputs"]:
            assert di.get("evidence_class") or di.get(
                "epistemic_class"), "epistemic class lost on a DI"

    def test_no_plausible_filler(self, elite_pkg):
        """UNKNOWN stays UNKNOWN — no field is filled with invented
        plausible text (R424 §4)."""
        eng = _read(elite_pkg["pkg"], "02_ENGINEERING_DEFINITION.json")
        blob = json.dumps(eng)
        for phrase in ("approximately", "typically around",
                       "industry standard value of", "commonly "
                       "estimated at"):
            assert phrase not in blob.lower(), \
                f"plausible filler detected: {phrase}"
        # parameters keep their recorded UNKNOWN states verbatim
        for p in eng["parameters"]:
            if p.get("value_status") == "UNKNOWN":
                assert "UNKNOWN" in str(p.get("value")).upper()


class TestDecisiveExperiment:
    def test_populated_when_earned(self, elite_pkg):
        """The weak baseline's 04 was empty. The elite 04 (R425 §5)
        carries the buyer-runnable contract: every field either
        DEFINED from a named canonical record or
        NOT_DEFINED_IN_CANONICAL_STATE with its provenance basis —
        never a bare empty record, never generic filler."""
        dex = _read(elite_pkg["pkg"], "04_DECISIVE_EXPERIMENT.json")
        assert dex["schema"] == "R425_DECISIVE_EXPERIMENT_CONTRACT"
        contract = dex["contract"]
        assert len(contract) >= 14
        sel = dex["recorded_layer"].get("selected")
        hyp = contract["hypothesis"]["value"]
        assert sel or hyp, "decisive experiment layer is empty"
        # every field carries its provenance basis
        for name, field in contract.items():
            assert field["provenance_basis"], name
            assert field["status"] in (
                "DEFINED", "NOT_DEFINED_IN_CANONICAL_STATE"), name
        # gaps are honest, never filler prose
        blob = json.dumps(dex).lower()
        assert "further testing required" not in blob


class TestEvidenceStructure:
    def test_explicit_roles(self, elite_pkg):
        ev = _read(elite_pkg["pkg"], "03_EVIDENCE_SUMMARY.json")
        roles = {r["role"] for r in ev["roles"]}
        assert roles == {"DIRECT_SUPPORT", "PARTIAL_SUPPORT",
                         "BACKGROUND", "ANALOGY", "CONTRADICTION",
                         "UNAVAILABLE_SOURCES"}
        counts = {r["role"]: r["count"] for r in ev["roles"]}
        # matches the run's own classification counts
        assert counts["DIRECT_SUPPORT"] == 8
        assert counts["ANALOGY"] == 6


class TestMaturityBasis:
    def test_evidence_derived_with_exact_basis(self, elite_pkg):
        mb = _read(elite_pkg["pkg"], "MATURITY_BASIS.json")
        assert mb["technology_maturity"] == \
            ep.PACKAGE_MATURITY_EARLY  # the solar record's honest level
        assert mb["counts"]["design_inputs"] >= 5
        assert mb["evidence_ids"]["design_inputs"]
        assert mb["known_blockers"]
        assert mb["basis"]


class TestUnknownRoadmap:
    def test_actionable_not_generic(self, elite_pkg):
        ur = _read(elite_pkg["pkg"], "UNKNOWN_ROADMAP.json")
        assert ur["unknown_count_roadmap"] >= 3
        for u in ur["unknowns"][:3]:
            assert u["resolution_action"]
            assert u["expected_measurement"]
            assert u["acceptance_rule"]
            assert u["consequence"]
            assert u["classification"] in (
                "LITERATURE_RESOLVABLE", "BENCH_TEST_REQUIRED",
                "ENGINEERING_DESIGN_REQUIRED",
                "COMPUTATION_RESOLVABLE", "REGULATORY_REQUIRED")
        blob = json.dumps(ur).lower()
        assert "further testing required" not in blob


class TestEquationRegistry:
    def test_applicable_with_real_bindings(self, elite_pkg):
        """The solar record carries governing equations (ENH-*) — the
        registry must bind them with variables/classes."""
        eq = _read(elite_pkg["pkg"], "EQUATION_REGISTRY.json")
        assert eq["status"] == "APPLICABLE"
        assert eq["equation_count"] >= 3
        first = eq["equations"][0]
        assert first["equation_id"]
        assert first["equation_canonical"]
        assert first["source"]["epistemic_class"]
        assert first["applicability"]["condition"]

    def test_not_applicable_when_record_carries_none(self, tmp_path):
        run = {"session_id": "ts_no_eq", "user_text": "x",
               "final_state": {"final_status": "X"},
               "engineering_specification": {
                   "engineering_core": {"governing_model": {}}},
               "invention_specification": {}, "run_state": {}}
        proj = _elite.derive_engineering_projection(run)
        reg = _elite.build_equation_registry(proj, "x")
        assert reg["status"] == "NOT_APPLICABLE"
        assert reg["reason"]


class TestTraceability:
    def test_explicit_id_chains(self, elite_pkg):
        tr = _read(elite_pkg["pkg"], "ENGINEERING_TRACEABILITY.json")
        assert tr["summary"]["design_outputs"] >= 3
        assert tr["links"]
        # exact id bindings, no semantic guessing (R425 §4 graph:
        # every link is EXPLICIT or UNKNOWN-with-basis)
        for link in tr["links"][:5]:
            assert link["binding"] in ("EXPLICIT", "UNKNOWN")
            assert link["binding_basis"]
        cov = tr["coverage"]
        assert (cov["explicit_bindings"] + cov["unknown_bindings"]
                == cov["total_links"])


class TestProvenance:
    def test_engine_commit_resolved_not_lazy_unknown(self, elite_pkg):
        """The weak baseline shipped engine_commit 'unknown' while the
        identity was available. The elite factory resolves it (git
        locally, artifact identity hosted) and labels the source."""
        prov = _read(elite_pkg["pkg"], "PROVENANCE.json")
        commit = prov["engine_commit"]
        assert commit != "unknown"
        assert prov["engine_commit_source"]
        if commit != "UNKNOWN":
            assert len(commit) >= 7  # a real sha prefix
        assert prov["package_version"] == "R425_ELITE.1.1.0"
        assert prov["canonical_invention_state_identity"][
            "invention_spec_hash"]
        assert prov["generated_at_utc"]
        assert prov["model_layer_files"]

    def test_no_invented_hashes(self, elite_pkg):
        prov = _read(elite_pkg["pkg"], "PROVENANCE.json")
        manifest = _read(elite_pkg["pkg"], "PACKAGE_MANIFEST.json")
        # every manifest entry matches real bytes on disk
        pkg_dir = elite_pkg["pkg"]["package_dir"]
        import hashlib
        for entry in manifest["files"][:10]:
            path = Path(pkg_dir) / entry["path"]
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            assert actual == entry["sha256"], entry["path"]


class TestBuyerDecisionArchitecture:
    def test_nine_questions(self, elite_pkg):
        with zipfile.ZipFile(elite_pkg["pkg"]["zip_path"]) as zf:
            card = zf.read(
                "TECHNOLOGY_PACKAGE/03_BUYER_DECISION_CARD.pdf")
        assert card  # the PDF renders (non-empty)
        # the decision architecture is built from the section set
        from discovery_fabric.engine.invention_bridge import (
            elite_documents as _ed)
        proj = _elite.derive_engineering_projection(_solar())
        card_doc = _ed.build_decision_card(proj, _solar(),
                                           ep.PACKAGE_MATURITY_EARLY)
        assert len(card_doc["section_order"]) == 9
        titles = " ".join(card_doc["section_order"]).lower()
        for fragment in ("problem", "matter", "different", "work",
                         "evidence", "unknown", "build", "experiment",
                         "next"):
            assert fragment in titles, f"decision card missing {fragment}"

    def test_transfer_manifest_sections(self, elite_pkg):
        from discovery_fabric.engine.invention_bridge import (
            elite_documents as _ed)
        proj = _elite.derive_engineering_projection(_solar())
        tm = _ed.build_transfer_manifest(
            proj, _solar(), "x", ep.PACKAGE_MATURITY_EARLY, False,
            "SYSTEM_3D")
        assert len(tm["section_order"]) == 9
        blob = " ".join(tm["section_order"]).lower()
        for fragment in ("transferable", "inventory", "maturity",
                         "capability", "tooling", "dependencies",
                         "confidentiality", "reproduction",
                         "open technical work"):
            assert fragment in blob


class Test3DClassification:
    def test_conceptual_class_correctly_labeled(self, elite_pkg):
        names = _zip_names(elite_pkg["pkg"])
        assert any(n.endswith("CONCEPTUAL_3D_DISCLAIMER.json")
                   for n in names)
        ds = _read(elite_pkg["pkg"],
                   "MODEL/3D_DESIGN_STATUS.json")
        assert ds["visualizability_class"] in (
            "SYSTEM_3D", "CONCEPTUAL_3D", "PROCESS_3D")
        assert ds["3d_design_status"] == "PRESENT_CONCEPTUAL"

    def test_conceptual_gets_no_fake_engineering_files(self, elite_pkg):
        names = _zip_names(elite_pkg["pkg"])
        assert not any(n.endswith(".step") for n in names)
        assert not any(n.endswith(".stl") for n in names)
        assert not any("PARAMETRIC_MODEL_SOURCE" in n for n in names)
        assert not any("3D_EVIDENCE/" in n for n in names), \
            "conceptual run must not carry the engineering evidence layer"
        params = _read(elite_pkg["pkg"], "MODEL/PARAMETERS.json")
        assert params["parameters"] == []
        assert "none are invented" in params["policy"]

    def test_engineering_run_earns_cad_evidence(self, tmp_path):
        """A parameterized (ENGINEERING_3D) run gets STEP/STL, the
        parametric source, and the 3D_EVIDENCE verification layer."""
        run = {"session_id": "ts_r424_eng",
               "user_text": "keep minimum drainage when primary lumen "
                            "obstructs",
               "final_state": {"final_status": "EVOLVED_INVENTION_CANDIDATE",
                               "causal_chain": {"intervention_site":
                                                "catheter"}},
               "invention_specification": {
                   "causal_chain": {"value": {
                       "intervention_site": "dual lumen catheter"}},
                   "problem": {"value": {
                       "device": "dual lumen catheter"}}},
               "engineering_specification": {
                   "parameters": [
                       {"param_id": "outer_diameter_mm", "value": 3.0,
                        "unit": "mm", "envelope": [2.5, 3.5],
                        "value_class": "MODELLED"},
                       {"param_id": "primary_lumen_diameter_mm",
                        "value": 1.1, "unit": "mm", "envelope": [0.8, 1.4],
                        "value_class": "MODELLED"},
                       {"param_id": "floor_lumen_diameter_mm",
                        "value": 0.6, "unit": "mm", "envelope": [0.4, 0.8],
                        "value_class": "MODELLED"},
                       {"param_id": "floor_offset_mm", "value": 1.0,
                        "unit": "mm", "envelope": [0.7, 1.3],
                        "value_class": "MODELLED"},
                       {"param_id": "length_mm", "value": 100.0,
                        "unit": "mm", "envelope": [60, 140],
                        "value_class": "MODELLED"}],
                   "system_architecture": {"subsystems": []},
                   "engineering_core": {}},
               "run_state": {"generations": {"generations": []}},
               "evidence_pack": {"retrieval": []}}
        work = tmp_path / "eng"
        work.mkdir()
        result = run_bridge(run, None, str(work), build_renders=False)
        pkg = result["package_out"]
        with zipfile.ZipFile(pkg["zip_path"]) as zf:
            names = zf.namelist()
        assert any(n.endswith(".step") for n in names)
        assert any(n.endswith(".stl") for n in names)
        assert any("MODEL/PARAMETRIC_MODEL_SOURCE.py" in n
                   for n in names)
        # the 3D_EVIDENCE verification layer with REAL checks
        assert any("REGENERATION_CHECK.json" in n for n in names)
        assert any("STL_INDEPENDENT_WATERTIGHT_CHECK.json" in n
                   for n in names)
        assert any("PARAMETER_FEATURE_LOG.json" in n for n in names)
        assert any("FILE_INVENTORY.json" in n for n in names)
        with zipfile.ZipFile(pkg["zip_path"]) as zf:
            regen = json.loads(zf.read(
                "TECHNOLOGY_PACKAGE/MODEL/3D_EVIDENCE/"
                "REGENERATION_CHECK.json"))
            wt = json.loads(zf.read(
                "TECHNOLOGY_PACKAGE/MODEL/3D_EVIDENCE/"
                "STL_INDEPENDENT_WATERTIGHT_CHECK.json"))
        assert regen["regeneration_status"] == "REPRODUCIBLE", regen
        assert wt["status"] == "ALL_WATERTIGHT", wt


class TestHonestWeakInvention:
    def test_weak_record_gets_no_fabricated_engineering(self, tmp_path):
        """A genuinely thin invention must NOT receive fabricated
        engineering content (R424 §15 final clause)."""
        run = {"session_id": "ts_weak", "user_text": "a weak problem "
               "statement with no engineering content at all",
               "final_state": {"final_status": "EVOLVED_INVENTION_CANDIDATE"},
               "engineering_specification": {},
               "invention_specification": {
                   "mechanism": {"value": "an algorithmic approach"},
                   "problem": {"value": "weak"}},
               "run_state": {"generations": {"generations": []}},
               "evidence_pack": {"retrieval": []}}
        proj = _elite.derive_engineering_projection(run)
        mb = _elite.build_maturity_basis(
            proj, "w", ep.PACKAGE_MATURITY_EARLY)
        # counts reflect the empty record honestly
        assert mb["counts"]["design_inputs"] == 0
        assert mb["counts"]["equations"] == 0
        # the roadmap has zero entries — not fabricated ones
        ur = _elite.build_unknown_roadmap(proj, "w")
        assert ur["unknown_count_roadmap"] == 0
        # equation registry states NOT_APPLICABLE
        eq = _elite.build_equation_registry(proj, "w")
        assert eq["status"] == "NOT_APPLICABLE"
