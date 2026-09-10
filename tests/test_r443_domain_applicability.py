"""R443 — domain-to-package semantic integrity (the applicability
boundary). The paired negative/positive controls the audit demands:

  Test A — industrial negative control: the wastewater heat-exchanger
            case must carry industrial requirements; the audit's
            medical list (patient/catheter/neurosurgery/FDA 510(k)/
            PMA/medical tubing/medical-grade silicone) must be absent
            from its buyer requirements — as a MATTER OF CORRECT
            APPLICABILITY, not a forbidden-word filter.
  Test B — medical positive control: a legitimate catheter problem
            keeps its genuinely applicable medical requirements (a
            global deletion strategy would falsely pass A and destroy
            B — the paired control).
  Test C — canonical mapping: every downstream item traces to the
            canonical applicability decision or is explicitly
            UNKNOWN / NOT_APPLICABLE / UNSUPPORTED (no silent defaults).
  Test E — adversarial contamination: the OLD medical template injected
            into the industrial case's package generation must BLOCK
            the release (the boundary, not the happy path).
  Test F — legitimate admission: a valid industrial case still produces
            a package (the fix is not an over-rejector).

Constitutional anchors: Art. X (one authority), Art. XXVIII (no silent
semantic promotion — a medical requirement never silently applies to a
non-medical problem), Art. XXVII (no invented requirements), Art. XVII
(every control must have an attempted bypass — Test E IS the bypass).
"""
from __future__ import annotations

import json
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import adapters as A  # noqa: E402
from discovery_fabric.engine.candidate import Candidate, sha256_obj  # noqa: E402
from discovery_fabric.engine.engineering_spec import build_engineering_spec  # noqa: E402
from discovery_fabric.engine.invention_spec import build_invention_spec  # noqa: E402
from discovery_fabric.engine.package_compiler import compile_package  # noqa: E402
from discovery_fabric.engine.applicability import (  # noqa: E402
    detect_applicability, context_requirements,
    filter_domain_module_content)

CTX = {"run_id": "testrun:r443", "problem_id": "fixture-r443"}

# ---------------------------------------------------------------------------
# The two adversarial cases (the audit's exact pairing)
# ---------------------------------------------------------------------------

INDUSTRIAL_PROBLEM = {
    "problem_id": "fixture-r443-industrial",
    "device": "countercurrent wastewater heat exchanger",
    "failure_mode": "FOULING-DRIVEN HEAT TRANSFER DECAY",
    "failure": ("fouling of the heat transfer surface reduces recovery "
                "efficiency on municipal wastewater treatment plant "
                "effluent streams"),
    "constraint": ("maintain recovery efficiency across the district "
                   "heating utility's operating envelope"),
    "user_text": ("Recover low-grade heat from municipal wastewater "
                  "treatment plant effluent using a countercurrent heat "
                  "exchanger; fouling on the heat transfer surface "
                  "decays recovery; the district heating utility needs "
                  "sustained efficiency without frequent cleaning "
                  "shutdowns."),
}

INDUSTRIAL_MECHANISM = (
    "helical copper coil in a stainless shroud maintains shear-driven "
    "self-cleaning flow while sustaining countercurrent heat transfer. "
    "The proposed intervention realizes this mechanism by placing a "
    "helically coiled heat transfer surface inside a shrouded process "
    "channel at the failure site identified in the problem statement, "
    "where the governing physical effect produces sustained heat "
    "recovery under the stated constraint; the transfer logic follows "
    "from the custodied source observation and its mechanism source "
    "span.")

INDUSTRIAL_INTERVENTION = "helical coil self-cleaning heat exchanger core"

INDUSTRIAL_ABSTRACT = (
    "A pilot study of a 12-month municipal wastewater heat recovery "
    "installation showed that a helically coiled heat exchanger in a "
    "stainless shroud sustained 84 percent of design heat transfer "
    "through two fouling seasons where conventional flat plates decayed "
    "to 55 percent; shear velocity at the coil surface was the "
    "controlling variable for fouling resistance. Industrial heat "
    "recovery from effluent streams recovered 320 MWh annually.")

MEDICAL_PROBLEM = {
    "problem_id": "fixture-r443-medical",
    "device": "CSF shunt system",
    "failure_mode": "OBSTRUCTION",
    "failure": "proximal catheter obstruction by choroid plexus ingrowth",
    "constraint": ("maintain patency for the implanted device lifetime "
                   "without revision surgery"),
    "user_text": ("Keep minimum CSF drainage when the primary lumen of a "
                  "ventriculoperitoneal shunt catheter obstructs in "
                  "hydrocephalus patients; the implanted device must "
                  "protect the patient; neurosurgery needs a passive "
                  "safety floor."),
}

MEDICAL_MECHANISM = (
    "porous titanium microstructure resists choroid plexus tissue "
    "ingrowth at the proximal catheter tip. The proposed intervention "
    "realizes this mechanism by placing a porous titanium proximal "
    "catheter tip at the failure site identified in the problem "
    "statement, where the governing physical effect produces reduced "
    "proximal obstruction at 90 days under the stated constraint; the "
    "transfer logic follows from the custodied source observation and "
    "its mechanism source span.")

MEDICAL_INTERVENTION = "porous titanium proximal catheter tip"

MEDICAL_ABSTRACT = (
    "In a canine model of communicating hydrocephalus, a porous "
    "titanium microstructure maintained patency for 90 days while "
    "reducing proximal shunt obstruction rates by 40 percent compared "
    "to standard silicone catheters. Inflammatory response was graded "
    "mild at 6 months in the implanted animals.")

ATTACK_PASS = {
    "overall": "PASS", "killed_count": 0, "reason": "synthetic pass",
    "attacks": {d: "SURVIVED" for d in (
        "unsupported_mechanism", "weak_transfer", "obvious_combination",
        "prior_art", "contradiction", "boundary_failure",
        "engineering_infeasibility", "regulatory_incompatibility")},
    "invalid_dimensions": [], "v4_corrections_applied": [],
    "prior_art_state": "NO_MATCH_FOUND", "evidence_verified": True,
    "prompt_hash": "0" * 16, "output_hash": "0" * 16,
    "timestamp": "2026-01-01T00:00:00Z",
    "_fixture_epistemic_class": "SYNTHETIC_TEST_ONLY",
}


_INDUSTRIAL_FALSIFICATION = (
    "Bench fouling-loop test with municipal secondary effluent analog: "
    "measure heat transfer decay over 30 days of the helical coil "
    "versus a conventional flat-plate control exchanger at matched "
    "flow and temperature conditions.")

_MEDICAL_FALSIFICATION = (
    "Bench shunt loop with choroid plexus tissue analog; measure flow "
    "decay over 30 days vs silicone control catheter.")


def _case_envelope(problem, abstract, mechanism, intervention,
                   falsification):
    env = Candidate(problem=problem, problem_id=problem["problem_id"])
    ev = {
        "id": "europepmc:R443FIX", "source_type": "scientific_paper",
        "source": "EuropePMC", "source_id": "R443FIX",
        "source_uri": "https://fixture.invalid/r443",
        "title": "R443 fixture study", "abstract": abstract,
        "doi": "10.0000/r443fixture", "publication_date": "2020-01-01",
        "content_hash": sha256_obj({"t": "r443-fixture-evidence"}),
    }
    env.evidence = [ev]
    env.evidence_ids = [ev["id"]]
    freeze = {
        "run_id": CTX["run_id"], "problem_id": problem["problem_id"],
        "frozen_at": "2026-01-01T00:00:00Z", "evidence_count": 1,
        "custody_records": [{
            "record_id": ev["id"], "content_hash": ev["content_hash"],
            "source": ev["source"], "evidence_class":
                "SCIENTIFIC_ABSTRACT"}],
        "hash_verification_all_pass": True,
        "_fixture_epistemic_class": "SYNTHETIC_TEST_ONLY",
    }
    freeze["snapshot_hash"] = sha256_obj(freeze)
    env.provenance = {"evidence_freeze": freeze}
    raw = {
        "candidate_id": "cand:R443",
        "falsification_test": falsification,
        "mechanism_source_span": abstract[:500],
        "source_evidence": {
            "source_id": ev["id"], "source_hash": ev["content_hash"],
            "source_span": abstract[:500], "source_title": ev["title"],
        },
        "mechanism": mechanism,
        "intervention": intervention,
        "expected_effect": "improved governing metric vs control",
        "_fixture_epistemic_class": "SYNTHETIC_TEST_ONLY",
    }
    env.mechanism_map = {
        "mechanism": mechanism,
        "intervention": intervention,
        "expected_effect": raw["expected_effect"],
        "falsification_test": raw["falsification_test"],
        "mechanism_source_span": abstract[:500],
        "raw_candidate": raw,
    }
    env.attack_results = json.loads(json.dumps(ATTACK_PASS))
    env.prior_art = {
        "prior_art_status": "NO_MATCH_FOUND",
        "legacy_status": "NO_MATCHING_EVIDENCE_FOUND",
    }
    return env


def _case_chain(problem, abstract, mechanism, intervention,
                falsification):
    env = _case_envelope(problem, abstract, mechanism, intervention,
                         falsification)
    plan = [("VERIFY", A.EvidenceVerifyAdapter),
            ("CONTRADICTION", A.ContradictionQueueAdapter),
            ("KILLER_EXPERIMENT", A.KillerExperimentAdapter),
            ("ADJUDICATION", A.AdjudicationAdapter),
            ("CLASSIFY", A.EpistemicClassificationAdapter),
            ("NEXT_BEST_ACTION", A.NextBestActionAdapter),
            ("RANK", A.PortfolioRankingAdapter)]
    for stage, adapter in plan:
        env.run_stage(stage, adapter.capability_id, adapter.module_path,
                      adapter.canonical_fn, adapter().execute, env, CTX)
    return env


def _case_run_result(problem, abstract, mechanism, intervention,
                    falsification):
    env = _case_chain(problem, abstract, mechanism, intervention,
                      falsification)
    spec = build_invention_spec(env, CTX)
    eng = build_engineering_spec(spec, env, CTX)
    from discovery_fabric.engine.experiment_selector import (
        select_decisive_experiment)
    ke = select_decisive_experiment(env)
    return {
        "decisive_experiment": ke,
        "session_id": f"testrun:r443:{problem['problem_id']}",
        "run_id": f"testrun:r443:{problem['problem_id']}",
        "problem_id": problem["problem_id"],
        "user_text": problem.get("user_text"),
        "title": (f"{problem.get('device')} — "
                  f"{problem.get('failure_mode')}"),
        "invention_specification": spec,
        "engineering_specification": eng,
        "final_state": {
            "final_status": env.epistemic_state.get("final_status"),
            "evidence_classification_counts": getattr(
                env, "classification_counts", {}) or {},
            "final_envelope_hash": env.envelope_hash(),
        },
        "_fixture_epistemic_class": "SYNTHETIC_TEST_ONLY",
    }


def _conceptual_geometry(eng):
    from discovery_fabric.engine.invention_bridge import \
        conceptual_geometry
    arch = eng.get("system_architecture") or {}
    subsystems = [s.get("name", f"subsystem {i + 1}")
                  if isinstance(s, dict) else str(s)
                  for i, s in enumerate(arch.get("subsystems") or [])] \
        or ["subsystem 1", "subsystem 2", "subsystem 3"]
    built = conceptual_geometry.build_system_architecture(
        subsystems, (eng.get("why_this_domain") or {}).get("domain", ""))
    return {
        "visualizability_class": "SYSTEM_3D",
        "glb_bytes": built["glb_bytes"],
        "glb_sha256": built.get("glb_sha256"),
        "components": built.get("components") or [],
        "domain_family": built.get("domain_family"),
        "renders": {"status": "SKIPPED"},
    }


def _industrial_run():
    return _case_run_result(INDUSTRIAL_PROBLEM, INDUSTRIAL_ABSTRACT,
                            INDUSTRIAL_MECHANISM, INDUSTRIAL_INTERVENTION,
                            _INDUSTRIAL_FALSIFICATION)


def _medical_run():
    return _case_run_result(MEDICAL_PROBLEM, MEDICAL_ABSTRACT,
                             MEDICAL_MECHANISM, MEDICAL_INTERVENTION,
                            _MEDICAL_FALSIFICATION)


#: the audit's exact contamination list (Test A)
AUDIT_MEDICAL_LIST = (
    "patient", "catheter", "neurosurgery", "clinical validation",
    "FDA 510(k)", "FDA PMA", "510(k)", "medical tubing",
    "medical-grade silicone",
)


# ---------------------------------------------------------------------------
# Unit layer: the applicability authority
# ---------------------------------------------------------------------------

class TestApplicabilityAuthority:
    def test_industrial_problem_classifies_industrial(self):
        app = detect_applicability(
            INDUSTRIAL_PROBLEM["user_text"],
            " ".join(str(INDUSTRIAL_PROBLEM.get(k, "")) for k in
                     ("device", "failure", "constraint")),
            INDUSTRIAL_MECHANISM)
        assert app["context_class"] == "INDUSTRIAL_PROCESS"
        assert app["deterministic"] is True
        assert app["score_table"], "the score table must be recorded"

    def test_medical_problem_classifies_medical(self):
        app = detect_applicability(
            MEDICAL_PROBLEM["user_text"],
            " ".join(str(MEDICAL_PROBLEM.get(k, "")) for k in
                     ("device", "failure", "constraint")),
            MEDICAL_MECHANISM)
        assert app["context_class"] == "MEDICAL_IN_VIVO"

    def test_deterministic_repeated(self):
        a = detect_applicability(INDUSTRIAL_PROBLEM["user_text"])
        b = detect_applicability(INDUSTRIAL_PROBLEM["user_text"])
        assert a == b

    def test_unknown_context_honest(self):
        app = detect_applicability("a generic thing happens sometimes")
        assert app["context_class"] == "UNKNOWN"
        reqs = context_requirements("UNKNOWN")
        for key in ("buyer_type", "engineering_capability",
                    "manufacturing_capability", "regulatory",
                    "market_channels"):
            node = reqs[key]
            nodes = node if isinstance(node, list) else [node]
            for n in nodes:
                assert n.get("applicability") in (
                    "UNKNOWN", "NOT_APPLICABLE", "UNSUPPORTED",
                    None) or n.get("epistemic_class") == "UNKNOWN"

    def test_domain_content_filter_excludes_and_records(self):
        from discovery_fabric.engine.domains import get_domain_module
        mod = get_domain_module("fluidics_hydraulic")
        out = filter_domain_module_content(mod, "INDUSTRIAL_PROCESS")
        blocks = " ".join(out["architecture_blocks"]).lower()
        assert "patient" not in blocks and "reservoir" not in blocks
        mats = " ".join(str(m.get("material")) for m in
                        out["materials_candidates"]).lower()
        assert "medical-grade silicone" not in mats
        # medical content RETAINED for medical context (paired control)
        out_med = filter_domain_module_content(mod, "MEDICAL_IN_VIVO")
        blocks_med = " ".join(out_med["architecture_blocks"]).lower()
        assert "patient" in blocks_med
        mats_med = " ".join(str(m.get("material")) for m in
                            out_med["materials_candidates"]).lower()
        assert "medical-grade silicone" in mats_med
        # exclusions recorded with reasons (never silent)
        assert out["excluded_context_mismatch"], (
            "the industrial filter must RECORD what it excluded")
        for e in out["excluded_context_mismatch"]:
            assert e.get("reason")


# ---------------------------------------------------------------------------
# Test C — canonical mapping (both cases)
# ---------------------------------------------------------------------------

class TestCanonicalMapping:
    def test_industrial_spec_carries_canonical_applicability(self):
        rr = _industrial_run()
        eng = rr["engineering_specification"]
        app = eng.get("applicability") or {}
        assert app.get("context_class") == "INDUSTRIAL_PROCESS"
        # the requirements projection is the canonical one (traced)
        reqs = app.get("requirements") or {}
        assert reqs.get("buyer_type", {}).get("statement", "").startswith(
            "industrial process-equipment")
        # exclusions recorded
        assert app.get("domain_content_exclusions"), (
            "the engineering spec must record what medical content was "
            "excluded and why")
        # component roles: no patient/reservoir interfaces
        subsystems = " ".join(
            s.get("name", "") for s in
            (eng.get("system_architecture") or {}).get("subsystems")
            or []).lower()
        assert "patient" not in subsystems
        assert "reservoir" not in subsystems
        # materials: no medical-grade silicone / medical extrusion
        materials = json.dumps(eng.get("materials") or []).lower()
        assert "medical-grade silicone" not in materials
        manuf = json.dumps(
            (eng.get("manufacturing") or {}).get("candidate_processes")
            or []).lower()
        assert "medical extrusion" not in manuf

    def test_medical_spec_keeps_medical_content(self):
        rr = _medical_run()
        eng = rr["engineering_specification"]
        app = eng.get("applicability") or {}
        assert app.get("context_class") == "MEDICAL_IN_VIVO"
        reqs = app.get("requirements") or {}
        assert "medical device company" in reqs.get(
            "buyer_type", {}).get("statement", "")
        # the patient/reservoir interface is present for the medical case
        subsystems = " ".join(
            s.get("name", "") for s in
            (eng.get("system_architecture") or {}).get("subsystems")
            or [])
        assert "patient" in subsystems.lower()
        materials = json.dumps(eng.get("materials") or []).lower()
        assert "medical-grade silicone" in materials

    def test_every_requirement_traces_or_is_honest(self):
        for rr in (_industrial_run(), _medical_run()):
            app = (rr["engineering_specification"]
                   .get("applicability") or {})
            reqs = app.get("requirements") or {}
            for key in ("buyer_type", "engineering_capability",
                        "manufacturing_capability", "regulatory",
                        "market_channels"):
                node = reqs.get(key)
                nodes = node if isinstance(node, list) else [node]
                for n in nodes:
                    assert isinstance(n, dict) and n.get("basis"), (
                        f"{key} item carries no basis — silent default")
                    assert n.get("applicability") in (
                        "APPLICABLE", "UNKNOWN", "NOT_APPLICABLE",
                        "UNSUPPORTED"), key
                    assert n.get("epistemic_class") in (
                        "MODELLED", "UNKNOWN"), key


# ---------------------------------------------------------------------------
# Tests A + B + F — the paired package controls (compile the ZIPs)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def industrial_package():
    rr = _industrial_run()
    geo = _conceptual_geometry(rr["engineering_specification"])
    with tempfile.TemporaryDirectory() as td:
        out = compile_package(rr, None, geo, td)
        yield out, rr


@pytest.fixture(scope="module")
def medical_package():
    rr = _medical_run()
    geo = _conceptual_geometry(rr["engineering_specification"])
    with tempfile.TemporaryDirectory() as td:
        out = compile_package(rr, None, geo, td)
        yield out, rr


def _pdf_text(pkg_dir):
    import fitz
    texts = []
    for p in sorted(Path(pkg_dir).glob("*.pdf")):
        doc = fitz.open(p)
        texts.append("\n".join(page.get_text() for page in doc))
        doc.close()
    return "\n".join(texts)


def _requirement_statements(model):
    reqs = model.get("requirements") or {}

    def walk(node, path="requirements"):
        if isinstance(node, dict):
            appl = str(node.get("applicability") or "")
            stmt = node.get("statement")
            if isinstance(stmt, str) and appl != "NOT_APPLICABLE":
                yield path, stmt
            for k, v in node.items():
                if k != "statement":
                    yield from walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                yield from walk(v, f"{path}[{i}]")
    yield from walk(reqs)


class TestIndustrialNegativeControl:
    """Test A — the wastewater heat-exchanger case (the audit's fresh
    production defect, reproduced at the package boundary)."""

    def test_package_compiles(self, industrial_package):
        out, _ = industrial_package
        assert out["state"] == "ZIP_READY", json.dumps(
            out.get("blocked_record") or out.get("quality_gate"),
            indent=2)[:2500]

    def test_no_audit_medical_terms_in_buyer_pdfs(self,
                                                  industrial_package):
        out, _ = industrial_package
        text = _pdf_text(out["package_dir"]).lower()
        found = [m for m in AUDIT_MEDICAL_LIST if m.lower() in text]
        # the honest NOT_APPLICABLE statement names the medical regime it
        # exempts — that sentence is REQUIRED, not contamination. What
        # must be absent is any AFFIRMATIVE medical requirement.
        assert not found or all(
            _only_not_applicable(text, m) for m in found), (
            f"industrial package carries affirmative medical content: "
            f"{found}")

    def test_requirements_dimension_is_industrial(self,
                                                  industrial_package):
        out, _ = industrial_package
        model = json.loads((Path(out["package_dir"])
                            / "TECHNOLOGY_PACKAGE_MODEL.json").read_text())
        reqs = model.get("requirements") or {}
        assert reqs.get("context_class") == "INDUSTRIAL_PROCESS"
        assert "industrial process-equipment" in reqs.get(
            "buyer_type", {}).get("statement", "")
        reg = reqs.get("regulatory") or {}
        assert reg.get("applicability") == "UNKNOWN"
        assert (reg.get("medical_not_applicable") or {}
                .get("applicability") == "NOT_APPLICABLE")

    def test_gate_W_passes_industrial(self, industrial_package):
        out, _ = industrial_package
        qg = out.get("quality_gate") or {}
        assert qg.get("package_quality") == "PASS"
        assert "W" not in (qg.get("failed_gates") or [])
        # the full verdict (persisted in the run tree) carries the W
        # record; the independent contamination check is ALSO exercised
        # directly below (the gate's own verdict on the built tree)
        full = out.get("quality_gate_full") or {}
        wg = (full.get("gates") or {}).get("W") or {}
        assert wg.get("verdict") in ("PASS", "WARN"), json.dumps(wg)[:900]
        assert not [f for f in (wg.get("findings") or [])
                    if f.get("severity") == "FAIL"]


class TestMedicalPositiveControl:
    """Test B — the legitimate catheter problem keeps its genuinely
    applicable medical requirements."""

    def test_package_compiles(self, medical_package):
        out, _ = medical_package
        assert out["state"] == "ZIP_READY", json.dumps(
            out.get("blocked_record") or out.get("quality_gate"),
            indent=2)[:2500]

    def test_medical_requirements_remain(self, medical_package):
        out, _ = medical_package
        model = json.loads((Path(out["package_dir"])
                            / "TECHNOLOGY_PACKAGE_MODEL.json").read_text())
        reqs = model.get("requirements") or {}
        assert reqs.get("context_class") == "MEDICAL_IN_VIVO"
        bt = reqs.get("buyer_type", {}).get("statement", "")
        assert "medical device company" in bt
        reg = reqs.get("regulatory") or {}
        assert reg.get("applicability") == "APPLICABLE"
        assert "510(k)" in reg.get("statement", "")

    def test_medical_pdfs_carry_medical_requirements(self,
                                                     medical_package):
        out, _ = medical_package
        text = _pdf_text(out["package_dir"]).lower()
        assert "medical" in text
        assert "fda" in text or "510(k)" in text

    def test_gate_W_passes_medical(self, medical_package):
        out, _ = medical_package
        qg = out.get("quality_gate") or {}
        assert qg.get("package_quality") == "PASS"
        assert "W" not in (qg.get("failed_gates") or [])
        full = out.get("quality_gate_full") or {}
        wg = (full.get("gates") or {}).get("W") or {}
        assert wg.get("verdict") in ("PASS", "WARN"), json.dumps(wg)[:900]


class TestLegitimateAdmission:
    """Test F — a valid industrial case still produces a package; the
    fix is not an over-rejector."""

    def test_industrial_zip_is_real(self, industrial_package):
        out, _ = industrial_package
        zp = Path(out["zip_path"])
        assert zp.is_file() and zp.stat().st_size > 1000
        with zipfile.ZipFile(zp) as zf:
            assert zf.testzip() is None
            names = zf.namelist()
        assert any(n.endswith("03_BUYER_DECISION_CARD.pdf")
                   for n in names)
        assert any(n.endswith("TECHNOLOGY_PACKAGE_MODEL.json")
                   for n in names)


def _only_not_applicable(pdf_text_lower: str, marker: str) -> bool:
    """True when every occurrence of the marker sits inside an explicit
    NOT_APPLICABLE statement (the honest negation names what it exempts)."""
    start = 0
    while True:
        idx = pdf_text_lower.find(marker.lower(), start)
        if idx < 0:
            return True
        window = pdf_text_lower[max(0, idx - 300):idx + len(marker) + 300]
        if not any(phrase in window for phrase in (
                "not applicable", "not_applicable", "never applicable",
                "no patient-contact", "outside this problem")):
            return False
        start = idx + len(marker)


# ---------------------------------------------------------------------------
# Test E — adversarial contamination (the boundary, not the happy path)
# ---------------------------------------------------------------------------

class TestAdversarialContamination:
    """Inject the OLD medical template (the hardcoded Licensee
    Capability Fit from build_portfolio_v4: catheter design, medical
    tubing extrusion, FDA 510(k)/PMA, neurosurgery market channels) into
    the industrial case's package generation. The package must REFUSE to
    become releasable (Art. XVII — the attempted bypass)."""

    def test_injected_medical_template_blocks_release(self):
        rr = _industrial_run()
        # the injection: replace the canonical industrial applicability
        # with the OLD medical-template requirements (simulating the
        # reused build_portfolio_v4 path the audit found)
        eng = dict(rr["engineering_specification"])
        app = dict(eng.get("applicability") or {})
        app["requirements"] = {
            "buyer_type": {
                "statement": "Neuroshunt manufacturer (Medtronic, "
                             "Integra, Miethke)",
                "applicability": "APPLICABLE",
                "epistemic_class": "MODELLED",
                "basis": "reused medical template"},
            "engineering_capability": [
                {"statement": "Catheter design, fluid mechanics",
                 "applicability": "APPLICABLE",
                 "epistemic_class": "MODELLED",
                 "basis": "reused medical template"}],
            "manufacturing_capability": [
                {"statement": "Medical tubing extrusion, injection "
                              "molding, cleanroom assembly",
                 "applicability": "APPLICABLE",
                 "epistemic_class": "MODELLED",
                 "basis": "reused medical template"}],
            "regulatory": {
                "statement": "FDA 510(k) or PMA submission experience "
                             "required",
                "applicability": "APPLICABLE",
                "epistemic_class": "MODELLED",
                "basis": "reused medical template"},
            "market_channels": [
                {"statement": "Neurosurgery market channels; hospital "
                              "purchasing relationships",
                 "applicability": "APPLICABLE",
                 "epistemic_class": "MODELLED",
                 "basis": "reused medical template"}],
        }
        app["context_class"] = "MEDICAL_IN_VIVO"  # the template's guess
        eng["applicability"] = app
        rr = dict(rr)
        rr["engineering_specification"] = eng
        geo = _conceptual_geometry(eng)
        with tempfile.TemporaryDirectory() as td:
            out = compile_package(rr, None, geo, td)
            assert out["state"] != "ZIP_READY", (
                "the contaminated package became releasable — the "
                "boundary failed")
            assert out.get("blocked") is True
            full = out.get("quality_gate_full") or {}
            w = (full.get("gates") or {}).get("W") or {}
            failures = [f for f in (w.get("findings") or [])
                        if f.get("severity") == "FAIL"]
            assert failures, (
                "gate W did not catch the injected medical template")
            codes = {f.get("code") for f in failures}
            assert codes & {"W-APPLICABILITY-CONTAMINATION",
                            "W-CONTEXT-VOCAB"}, codes
            # no ZIP exists (Art. V: fail closed)
            assert not out.get("zip_path") or not Path(
                out["zip_path"]).exists()
            # the quarantined tree + blocked record exist
            assert out.get("blocked_record")

    def test_domain_gate_still_independent_second_line(self):
        """The C-gate domain contradiction detector remains the second
        line of defense (defense in depth: W checks applicability, C
        checks cross-domain content)."""
        from discovery_fabric.engine.package_quality_gate.gates import (
            _problem_is_medical)
        assert _problem_is_medical(
            INDUSTRIAL_PROBLEM["user_text"]) is False
        assert _problem_is_medical(
            MEDICAL_PROBLEM["user_text"]) is True


if __name__ == "__main__":
    import unittest
    unittest.main()
