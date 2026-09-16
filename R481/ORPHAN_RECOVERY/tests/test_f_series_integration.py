"""tests/test_f_series_integration.py — CEO FINAL INTEGRATION DIRECTIVE
acceptance suite (Directives 1-10, minus 3 which is the E4 reuse doctrine
already proven by test_dossier_bridge).

Acceptance targets proven here:

    AUTOMATED_DISCOVERY_TO_DOSSIER = PASS
    AUTOMATED_ENGINEERING_SPEC     = PASS
    AUTOMATED_BUYER_PACKAGE        = PASS
    AUTOMATED_ZIP                  = PASS
    1 SURVIVOR  -> 1 COMPLETE PACKAGE
    15 SURVIVORS -> 15 COMPLETE PACKAGES
    0 MATERIAL_TRUNCATION
    0 FABRICATED_FACTS
    0 SOURCE_FACT_PROMOTION
    0 PACKAGE_CROSS_CONTAMINATION
    0 UNTRACEABLE_ENGINEERING_FIELDS

Offline only: fixtures are SYNTHETIC_TEST_ONLY and every generated artifact
carries SYNTHETIC_REHEARSAL=TRUE labels (Art. XXXVII/XXXVIII).
"""
from __future__ import annotations

import hashlib
import importlib
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import adapters as A  # noqa: E402
from discovery_fabric.engine.candidate import (  # noqa: E402
    Candidate, sha256_obj)
from discovery_fabric.engine.domains import (  # noqa: E402
    DOMAIN_TEMPLATES, detect_domain, export_registry_json,
    get_domain_module)
from discovery_fabric.engine.engineering_spec import (  # noqa: E402
    build_engineering_spec)
from discovery_fabric.engine.fields import (  # noqa: E402
    DisplayRegister, build_display_view)
from discovery_fabric.engine.invention_spec import (  # noqa: E402
    SPEC_FIELDS, assert_no_fact_promotion, build_invention_spec)
from discovery_fabric.engine.maturity import (  # noqa: E402
    MATURITY_LADDER, compute_maturity)
from discovery_fabric.engine.package_compiler import (  # noqa: E402
    compile_package)
from discovery_fabric.engine.release import (  # noqa: E402
    ST_RELEASED, ST_HELD_FOR_HUMAN_REVIEW,
    build_discovery_release)
from discovery_fabric.engine.run import EngineRun  # noqa: E402

CTX = {"run_id": "testrun:fseries", "problem_id": "fixture"}

PACKAGE_FILE_SET = [
    "00_PACKAGE_README.pdf",
    "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
    "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
    "03_BUYER_DECISION_CARD.pdf",
    "04_EVIDENCE_SUMMARY.pdf",
    "05_TRANSFER_MANIFEST.pdf",
    "PACKAGE_MANIFEST.json",
    "ENGINEERING_TRACEABILITY.json",
    "MATURITY_BASIS.json",
]


# ----------------------------------------------------------------------
# Fixture machinery: parameterized survivor envelopes across domains
# ----------------------------------------------------------------------
CHAIN_PLAN = [
    ("VERIFY", A.EvidenceVerifyAdapter),
    ("CONTRADICTION", A.ContradictionQueueAdapter),
    ("KILLER_EXPERIMENT", A.KillerExperimentAdapter),
    ("ADJUDICATION", A.AdjudicationAdapter),
    ("CLASSIFY", A.EpistemicClassificationAdapter),
    ("NEXT_BEST_ACTION", A.NextBestActionAdapter),
    ("RANK", A.PortfolioRankingAdapter),
]


def _offline_chain(env: Candidate) -> Candidate:
    for stage, adapter in CHAIN_PLAN:
        env.run_stage(stage, adapter.capability_id, adapter.module_path,
                      adapter.canonical_fn, adapter().execute, env, CTX)
    return env


DOMAIN_PROBES = {
    "fluidics_hydraulic": dict(
        device="CSF shunt system", failure_mode="OBSTRUCTION",
        failure="proximal catheter obstruction by tissue",
        constraint="maintain long-term lumen patency and flow",
        mechanism="porous microstructure resists fluid-path tissue ingrowth",
        intervention="porous titanium proximal catheter tip in the shunt lumen",
        effect="sustained fluid flow through the shunt valve",
        fals="bench shunt flow loop; measure flow decay over 30 days"),
    "optical_photonic": dict(
        device="implantable sensor", failure_mode="POWER_DEPLETION",
        failure="battery depletion ends sensor life early",
        constraint="no battery replacement surgeries allowed",
        mechanism="near-infrared optical power over fiber charges the sensor",
        intervention="laser-driven photovoltaic receiver behind an optical window",
        effect="continuous photovoltaic charge at depth",
        fals="tissue phantom fluence and conversion efficiency mapping"),
    "rf_wireless": dict(
        device="implant telemetry node", failure_mode="LINK_LOSS",
        failure="telemetry link drops at depth",
        constraint="SAR within regulated exposure limits",
        mechanism="adaptive link-budget scheduling maintains telemetry margin",
        intervention="implant antenna array with exposure-aware transmit power",
        effect="reliable wireless data rate at maximum implant depth",
        fals="tissue-equivalent phantom BER vs depth curve"),
    "acoustic": dict(
        device="implant monitor", failure_mode="UNDETECTED_EVENT",
        failure="leak events go undetected in quiet conditions",
        constraint="passive duty; minimal power",
        mechanism="acoustic impedance contrast flags fluid leak pockets",
        intervention="piezoelectric transducer pair with echo detection",
        effect="echo-based leak detection at clinically required depth",
        fals="phantom detection-threshold mapping vs depth"),
    "mri_nmr": dict(
        device="flow sensor", failure_mode="MR_INCOMPATIBLE",
        failure="sensor cannot operate inside MRI scanner",
        constraint="MR-conditional marking required",
        mechanism="larmor-based passive resonance encodes flow without electronics",
        intervention="MR-compatible microcoil resonator with relaxation readout",
        effect="flow quantification under B0 in the scanner bore",
        fals="scanner SNR and flow-quantization accuracy vs reference MRI"),
    "enzyme_biocatalytic": dict(
        device="dialysis circuit", failure_mode="CLOT_PROPAGATION",
        failure="thrombus growth occludes the extracellular circuit",
        constraint="no systemic anticoagulation increase",
        mechanism="immobilized catalytic surface degrades fibrin locally",
        intervention="enzyme-functionalized circuit surface with contact-time control",
        effect="reduced thrombus mass in the flowing circuit",
        fals="residual activity vs time in flowing target fluid assay"),
    "phage_microbio": dict(
        device="urinary catheter", failure_mode="INFECTION",
        failure="biofilm colonization causes catheter-associated infection",
        constraint="no prophylactic systemic antibiotics",
        mechanism="immobilized phage lysing biofilm-forming bacteria on contact",
        intervention="phage-loaded anti-biofilm catheter surface coating",
        effect="reduced CFU biofilm burden on the surface",
        fals="CFU biofilm-prevention challenge assay vs uncoated control"),
    "ml_data": dict(
        device="monitoring dashboard", failure_mode="LATE_WARNING",
        failure="alerts fire too late for intervention",
        constraint="runs on hospital edge hardware",
        mechanism="bayesian predictor with calibrated uncertainty forecasts deterioration",
        intervention="temporal classifier ensemble with distribution-shift monitoring",
        effect="earlier warning at fixed false-alarm budget",
        fals="held-out temporal split with calibration analysis"),
    "mechanical_structural": dict(
        device="steering catheter", failure_mode="KINK",
        failure="shaft buckles during tight-vessel steering",
        constraint="torque transmission through anatomy",
        mechanism="variable-stiffness backbone resists buckling while steering",
        intervention="laser-cut hypotube flexure pattern with fatigue margins",
        effect="kink-free steering across the delivery path",
        fals="buckling margin test across duty cycle and fatigue run-out"),
    "thermal": dict(
        device="wearable patch", failure_mode="OVERHEAT",
        failure="electronics hotspot burns skin during charging",
        constraint="skin-contact temperature ceiling",
        mechanism="conduction spreader lowers hotspot below the safety ceiling",
        intervention="graphite spreading layer with interface resistance control",
        effect="temperature rise within the sourced limit at max duty",
        fals="temperature-rise mapping at maximum duty"),
    "energy_harvesting": dict(
        device="implant stimulator", failure_mode="BATTERY_DEATH",
        failure="battery replacement surgery every recharge cycle",
        constraint="hermetic, MR-conditional packaging",
        mechanism="thermoelectric body-heat harvesting trickle-charges the cell",
        intervention="BiTe thermoelectric stack with power conditioning",
        effect="energy autonomy across the duty profile",
        fals="power vs excitation sweep and endurance run"),
}


def _survivor_env(domain_id: str, variant: int = 0,
                  chain: bool = True) -> Candidate:
    p = DOMAIN_PROBES[domain_id]
    problem_id = f"fixture:{domain_id}:{variant}"
    problem = {
        "problem_id": problem_id, "device": p["device"],
        "failure_mode": p["failure_mode"], "failure": p["failure"],
        "constraint": p["constraint"],
    }
    env = Candidate(problem=problem, problem_id=problem_id)
    # E15-B content standard: a real LLM synthesis produces a multi-sentence,
    # invention-tied mechanism narrative; the fixture mirrors that shape
    # (the depth evaluator must not be lowered to admit thin fixtures).
    mechanism_rich = (
        f"{p['mechanism']}. The proposed intervention realizes this "
        f"mechanism by placing {p['intervention']} at the failure site "
        f"identified in the problem statement, where the governing "
        f"physical effect produces {p['effect']} under the stated "
        f"constraint ({p['constraint']}); the transfer logic follows from "
        "the custodied source observation and its mechanism source span.")
    ev = {
        "id": f"europepmc:FIXTURE-{domain_id}-{variant}",
        "source_type": "scientific_paper", "source": "EuropePMC",
        "source_id": f"FIX-{domain_id}-{variant}",
        "source_uri": f"https://fixture.invalid/{domain_id}/{variant}",
        "title": f"Fixture study {domain_id} #{variant}",
        "abstract": (f"In a controlled model, the {p['mechanism']} was "
                     f"demonstrated with the {p['intervention']}, producing "
                     f"the reported effect. A long sentence follows to give "
                     f"the abstract realistic length for truncation checks: "
                     + "the measured behavior remained stable across repeated "
                       "trials under varying load conditions. " * 4),
        "doi": f"10.0000/fixture.{variant}", "publication_date": "2021-01-01",
        "content_hash": sha256_obj({"t": f"fixture-{domain_id}-{variant}"}),
    }
    env.evidence = [ev]
    env.evidence_ids = [ev["id"]]
    freeze = {
        "run_id": "testrun:fseries", "problem_id": problem_id,
        "frozen_at": "2026-01-01T00:00:00Z", "evidence_count": 1,
        "custody_records": [{"record_id": ev["id"],
                             "content_hash": ev["content_hash"]}],
        "hash_verification_all_pass": True,
        "_fixture_epistemic_class": "SYNTHETIC_TEST_ONLY"}
    freeze["snapshot_hash"] = sha256_obj(freeze)
    env.provenance = {"evidence_freeze": freeze}
    raw = {
        "candidate_id": f"cand:FIXTURE-{domain_id}-{variant}",
        "falsification_test": p["fals"],
        "mechanism_source_span": p["mechanism"],
        "source_evidence": {"source_id": ev["id"],
                            "source_hash": ev["content_hash"],
                            "source_span": ev["abstract"][:500],
                            "source_title": ev["title"]},
        "mechanism": p["mechanism"],
        "intervention": p["intervention"],
        "expected_effect": p["effect"],
        "_fixture_epistemic_class": "SYNTHETIC_TEST_ONLY",
    }
    env.mechanism_map = {
        "mechanism": mechanism_rich, "intervention": raw["intervention"],
        "expected_effect": raw["expected_effect"],
        "falsification_test": raw["falsification_test"],
        "mechanism_source_span": raw["mechanism_source_span"],
        "raw_candidate": raw}
    attack = {
        "overall": "PASS", "killed_count": 0, "reason": "synthetic pass",
        "attacks": {d: "SURVIVED" for d in (
            "unsupported_mechanism", "weak_transfer", "obvious_combination",
            "prior_art", "contradiction", "boundary_failure",
            "engineering_infeasibility", "regulatory_incompatibility")},
        "invalid_dimensions": [], "v4_corrections_applied": [],
        "prior_art_state": "NO_MATCH_FOUND", "evidence_verified": True,
        "prompt_hash": "0" * 16, "output_hash": "0" * 16,
        "timestamp": "2026-01-01T00:00:00Z",
        "_fixture_epistemic_class": "SYNTHETIC_TEST_ONLY"}
    env.attack_results = attack
    env.prior_art = {"prior_art_status": "NO_MATCH_FOUND",
                     "legacy_status": "NO_MATCHING_EVIDENCE_FOUND",
                     "state_vocabulary": "classify/v4_corrections"}
    env.collision_results = {
        "novelty_risk": "SEARCHED_NO_DIRECT_TITLE_MATCH",
        "patent": {"hits": [], "hit_count": 0, "source_errors": []}}
    if chain:
        _offline_chain(env)
    return env


def _compile_post_run(env, spec, eng, run_dir: Path, run_id: str):
    """R440.2: the production package sequence — the run DEFERS the
    package (PACKAGE_DEFERRED.json); the canonical compiler compiles
    from the FINAL persisted state (the bridge gate's exact contract).
    SYNTHETIC_REHEARSAL rides in the manifest (Art. XXXVII)."""
    from discovery_fabric.engine.experiment_selector import (
        select_decisive_experiment)
    ke = select_decisive_experiment(env)
    problem = env.problem
    run_result = {
        "session_id": run_id,
        "run_id": run_id,
        "problem_id": env.problem_id,
        "user_text": problem.get("failure") or problem.get(
            "failure_mode"),
        "title": (f"{problem.get('device', 'fixture device')} — "
                 f"{problem.get('failure_mode', 'fixture failure')}"),
        "domain": (eng.get("why_this_domain") or {}).get("domain")
        or eng.get("technology_domain"),
        "invention_specification": spec,
        "engineering_specification": eng,
        "final_state": {
            "final_status": (env.epistemic_state or {}).get(
                "final_status"),
            "final_envelope_hash": env.envelope_hash(),
        },
        "decisive_experiment": ke,
    }
    from discovery_fabric.engine.invention_bridge import \
        conceptual_geometry
    arch = (eng.get("system_architecture") or {}).get("subsystems") or []
    subs = [s.get("name", f"subsystem {i+1}") if isinstance(s, dict)
            else str(s) for i, s in enumerate(arch)] or [
        "subsystem 1", "subsystem 2", "subsystem 3"]
    built = conceptual_geometry.build_system_architecture(
        subs, (eng.get("why_this_domain") or {}).get("domain", ""))
    geometry_out = {
        "visualizability_class": "SYSTEM_3D",
        "glb_bytes": built["glb_bytes"],
        "glb_sha256": built.get("glb_sha256"),
        "components": built.get("components") or [],
        "domain_family": built.get("domain_family"),
        "renders": {"status": "SKIPPED"},
    }
    return compile_package(run_result, None, geometry_out, str(run_dir),
                           rehearsal=True)


def _drive_automatic_pipeline(env: Candidate, out: Path,
                              package_number: str, run_id: str):
    """Directive 1 under test (R440 order contract): the conductor's
    post-RANK path DEFERS the package to the canonical compiler; this
    driver then runs the bridge gate's exact post-run compile sequence
    and binds the release by hash. rehearsal=True because these
    fixtures are SYNTHETIC_TEST_ONLY — every artifact carries the label
    (Art. XXXVII)."""
    run = EngineRun(env.problem, str(out), run_id=run_id,
                    package_number=package_number)
    run.env = env
    run.rehearsal = True
    run._post_rank_pipeline({"run_id": run_id})
    # R440.2: the deferral is recorded, never silent
    assert (out / "PACKAGE_DEFERRED.json").is_file() or \
        (out / "PACKAGE_FAILED.json").is_file()
    pkg = _compile_post_run(env, run._spec, run._eng, out, run_id)
    assert pkg["state"] == "ZIP_READY", json.dumps(
        pkg.get("blocked_record"), indent=1, default=str)[:1200]
    run.package_report = pkg
    # the release binds the compiled artifact by hash (Directive 2)
    release = build_discovery_release(
        out, run_id=run_id, problem_id=env.problem_id, env=env,
        spec=run._spec, eng=run._eng,
        package_report={"complete": True,
                        "folder": pkg["package_dir"],
                        "zip": pkg["zip_path"]},
        failure_reason=run.package_failure)
    from discovery_fabric.engine.release import write_discovery_release
    write_discovery_release(out, release)
    return run, release


# ----------------------------------------------------------------------
# Directive 1 — package generation is AUTOMATIC
# ----------------------------------------------------------------------
def test_d1_survivor_automatically_produces_full_package():
    """R440.2 migration: the survivor's package is produced by the
    canonical compiler POST-run (never a pre-evolution snapshot); the
    independent quality gate verdict replaces the old in-run E16-H
    release gate (a PASS verdict is recorded in the compile output)."""
    env = _survivor_env("fluidics_hydraulic")
    with tempfile.TemporaryDirectory() as td:
        run, release = _drive_automatic_pipeline(
            env, Path(td), "90", "testrun:d1")
        # the automatic chain wrote every stage artifact
        for f in ("INVENTION_SPECIFICATION.json",
                  "ENGINEERING_SPECIFICATION.json",
                  "DECISIVE_EXPERIMENT.json",
                  "DISCOVERY_RELEASE.json",
                  "PACKAGE_DEFERRED.json"):
            assert (Path(td) / f).exists(), f
        # the run never generated the buyer package in-run (R440.2)
        assert run.package_report is None or \
            run.package_report.get("state") == "ZIP_READY"
        pkg = run.package_report
        assert pkg["state"] == "ZIP_READY"
        assert pkg["quality_gate"]["package_quality"] == "PASS"
        assert Path(pkg["zip_path"]).exists()
        # the deferral record declares the order contract
        rec = json.loads((Path(td) / "PACKAGE_DEFERRED.json").read_text())
        assert "EVOLUTION" in rec["order_contract"]
        assert release["status"] == ST_HELD_FOR_HUMAN_REVIEW
        assert release["buyer_package_hash"] == pkg["zip_sha256"]


def test_d1_default_is_automatic_and_optout_is_explicit_test_flag():
    import inspect
    sig = inspect.signature(EngineRun.__init__)
    assert sig.parameters["with_package"].default is True, \
        "production default MUST be with_package=True (Directive 1)"
    src = inspect.getsource(EngineRun.__init__)
    assert "--with-package" not in src
    cli = (REPO / "discovery_fabric" / "engine" / "run.py").read_text()
    assert "--no-package" in cli and '"--with-package"' not in cli


def test_d1_no_package_optout_produces_no_package_but_honest_release():
    env = _survivor_env("optical_photonic")
    with tempfile.TemporaryDirectory() as td:
        run = EngineRun(env.problem, td, with_package=False,
                        run_id="testrun:d1-optout")
        run.env = env
        run.release = build_discovery_release(
            Path(td), run_id=run.run_id, problem_id=env.problem_id,
            env=env, spec=None, eng=None, package_report=None,
            disabled_by_config=True)
        assert run.release["status"] == "DISABLED_BY_CONFIG"
        assert not (Path(td) / "INVENTION_SPECIFICATION.json").exists()


# ----------------------------------------------------------------------
# Directive 2 — canonical DISCOVERY_RELEASE.json
# ----------------------------------------------------------------------
REQUIRED_RELEASE_FIELDS = [
    "run_id", "candidate_id", "invention_id", "problem_id",
    "evidence_hash", "candidate_hash", "invention_spec_hash",
    "engineering_spec_hash", "dossier_manifest_hash", "buyer_package_hash",
    "status"]


def test_d2_release_binds_discovery_to_transfer_artifact_by_hash():
    env = _survivor_env("rf_wireless")
    with tempfile.TemporaryDirectory() as td:
        run, release = _drive_automatic_pipeline(
            env, Path(td), "90", "testrun:d2")
        for k in REQUIRED_RELEASE_FIELDS:
            assert k in release, k
            assert release[k] is not None, f"{k} must be bound, not null"
        # every hash is REAL and reproducible from the artifacts on disk
        assert release["candidate_hash"] == env.envelope_hash()
        assert release["invention_spec_hash"] == run._spec["_spec_hash"]
        pm = Path(release["package_folder"]) / "PACKAGE_MANIFEST.json"
        h = hashlib.sha256(pm.read_bytes()).hexdigest()
        assert release["dossier_manifest_hash"] == h
        zp = Path(release["package_zip"])
        hz = hashlib.sha256(zp.read_bytes()).hexdigest()
        assert release["buyer_package_hash"] == hz
        assert release["status"] in (ST_RELEASED, ST_HELD_FOR_HUMAN_REVIEW)


def test_d2_release_record_reproducible_from_run_dir_alone():
    env = _survivor_env("acoustic")
    with tempfile.TemporaryDirectory() as td:
        _drive_automatic_pipeline(env, Path(td), "90", "testrun:d2b")
        rel = json.loads((Path(td) / "DISCOVERY_RELEASE.json").read_text())
        zp = Path(rel["package_zip"])
        assert hashlib.sha256(zp.read_bytes()).hexdigest() == \
            rel["buyer_package_hash"]


# ----------------------------------------------------------------------
# Directive 4 — canonical ENGINEERING_DOMAIN_REGISTRY + domain-adaptive depth
# ----------------------------------------------------------------------
def test_d4_registry_artifact_exists_and_is_in_sync():
    reg = export_registry_json()
    reg.pop("exported_at", None)
    committed = json.loads((REPO / "ENGINEERING_DOMAIN_REGISTRY.json")
                           .read_text())
    assert committed == reg, \
        "ENGINEERING_DOMAIN_REGISTRY.json drifted from domains.py — " \
        "regenerate the artifact (single code authority)"


def test_d4_registry_covers_all_directive_domains_with_full_modules():
    reg = json.loads((REPO / "ENGINEERING_DOMAIN_REGISTRY.json").read_text())
    required = {"governing_models", "critical_parameters", "failure_modes",
                "design_input_patterns", "design_output_patterns",
                "verification_methods", "validation_methods",
                "manufacturing_patterns"}
    ceo_domains = {"fluidics_hydraulic": "fluidics",
                   "optical_photonic": "optics",
                   "rf_wireless": "RF",
                   "acoustic": "acoustics",
                   "mri_nmr": "MRI/NMR",
                   "phage_microbio": "microbiology",
                   "enzyme_biocatalytic": "enzyme kinetics",
                   "ml_data": "machine learning",
                   "mechanical_structural": "mechanical structures",
                   "energy_harvesting": "energy harvesting"}
    for domain_id, ceo_name in ceo_domains.items():
        assert domain_id in reg["domains"], ceo_name
        mod = reg["domains"][domain_id]
        missing = required - set(mod)
        assert not missing, f"{domain_id} missing {missing}"
        for k in required:
            assert mod[k], f"{domain_id}.{k} empty"
        assert mod["signals"], f"{domain_id} must map characteristics"
    # UNKNOWN stays honestly generic, never fabricated depth
    unk = reg["domains"]["UNKNOWN"]
    assert unk["critical_parameters"] == [] and unk["failure_modes"] == []


def test_d4_engineering_depth_is_domain_adaptive():
    probes = {}
    for domain_id in ("fluidics_hydraulic", "ml_data", "rf_wireless"):
        env = _survivor_env(domain_id)
        spec = build_invention_spec(env, CTX)
        eng = build_engineering_spec(spec, env, CTX)
        assert eng["technology_domain"] == domain_id
        probes[domain_id] = eng
    f = probes["fluidics_hydraulic"]
    assert any("lumen" in p["parameter"] for p in
               f["engineering_core"]["critical_parameters"])
    assert any("Poiseuille" in m["model"] for m in
               f["engineering_core"]["governing_model"]
               ["domain_governing_models"])
    ml = probes["ml_data"]
    assert any("distribution-shift" in p["parameter"] for p in
               ml["engineering_core"]["critical_parameters"])
    rf = probes["rf_wireless"]
    assert any("SAR" in p["parameter"] for p in
               rf["engineering_core"]["critical_parameters"])
    # domain candidate failure modes are appended and classed.
    # E15-D upgrade: an adversarial row may be ENRICHED with a domain
    # mechanism (cross-reference) — it keeps its COMPUTED class but MUST
    # carry mechanism_provenance; pure domain candidate rows stay
    # ENGINEERING_PROPOSED. Either way the domain-sourced content is
    # explicitly classed and provenance-carrying.
    for eng in probes.values():
        dom_fms = [fm for fm in eng["failure_analysis"]
                   if "domain registry" in fm["evidence"]]
        assert dom_fms
        for fm in dom_fms:
            if fm["epistemic_class"] == "ENGINEERING_PROPOSED":
                continue
            assert fm.get("mechanism_provenance"), \
                f"{fm['graph_id']}: cross-referenced row lacks provenance"
            assert fm.get("invention_applicability", {}).get("verdict") \
                == "TIED"
            assert fm.get("content_class") == "PHYSICAL_MECHANISM"


# ----------------------------------------------------------------------
# Directive 5 — no fabricated depth; classes survive PDF generation
# ----------------------------------------------------------------------
def test_d5_epistemic_classes_survive_pdf_generation():
    """R440 migration: epistemic classes survive into the package — the
    buyer dossier carries the engineering-class vocabulary as humanized
    prose (R440.6), the machine layers carry the exact class tokens
    (a naked assertion never survives anywhere)."""
    env = _survivor_env("fluidics_hydraulic", variant=7)
    with tempfile.TemporaryDirectory() as td:
        run, release = _drive_automatic_pipeline(
            env, Path(td), "90", "testrun:d5")
        folder = Path(release["package_folder"])
        dossier_pdf = folder / "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf"
        import pypdf
        text = "\n".join(
            page.extract_text() or "" for page in
            pypdf.PdfReader(str(dossier_pdf)).pages)
        for marker in ("MODELLED", "ENGINEERING_PROPOSED",
                       "UNKNOWN", "ABSENT", "NOT ESTABLISHED"):
            assert marker in text, \
                f"epistemic marker {marker!r} did not survive PDF generation"
        # the exact class tokens survive in the machine layers (the
        # PDFs humanize, the machine layer keeps the canonical classes)
        eng_def = json.loads(
            (folder / "02_ENGINEERING_DEFINITION.json").read_text())
        blob = json.dumps(eng_def)
        for token in ("SOURCE_FACT", "NOT_TESTED", "NOT_PERFORMED"):
            assert token in blob, \
                f"class token {token!r} lost in the machine layer"
        # UNKNOWN is legal content: the validation matrix honestly reports
        # NOT_PERFORMED (physical observation has not happened)
        assert "NOT_PERFORMED" in blob


def test_d5_no_fabricated_values_anywhere():
    env = _survivor_env("enzyme_biocatalytic")
    spec = build_invention_spec(env, CTX)
    eng = build_engineering_spec(spec, env, CTX)
    assert assert_no_fact_promotion(spec) == []
    cps = eng["engineering_core"]["critical_parameters"]
    assert cps and all("UNKNOWN" in str(p["value"]) for p in cps)
    vm = eng["verification_matrix"]
    assert all(v["result"] == "NOT_TESTED" for v in vm)
    valm = eng["validation_matrix"]
    assert all(v["result"] == "NOT_PERFORMED" for v in valm)


# ----------------------------------------------------------------------
# Directive 6 — zero material truncation
# ----------------------------------------------------------------------
D6_SOURCE_FILES = [
    "discovery_fabric/engine/invention_spec.py",
    "discovery_fabric/engine/engineering_spec.py",
    "discovery_fabric/engine/maturity.py",
    "discovery_fabric/engine/release.py",
    "discovery_fabric/engine/fields.py",
    # A-series authoritative-content modules (CEO A2-A7) — same rule
    "discovery_fabric/engine/reasoning_chain.py",
    "discovery_fabric/engine/design_outputs.py",
    "discovery_fabric/engine/depth_contract.py",
    "discovery_fabric/engine/package_registry.py",
    # E15 authoritative-content modules (CEO E15-A/B/F/G) — same rule
    "discovery_fabric/engine/engineering_attack.py",
    "discovery_fabric/engine/dossier_quality.py",
    # R455: benchmark_corpus.py + benchmark_dossiers.py archived to
    # archive/r455-lean/ (unreachable from production); removed from the
    # authoritative-source list — archived modules are not authoritative.
]
SLICE_RE = re.compile(r"\[:\d+\]")


def test_d6_no_slice_transformations_in_authoritative_sources():
    # hash-derived identifier shortening (sha256/envelope_hash -> short id)
    # is NOT content truncation; anything else sliced is a violation
    allowed = (re.compile(r"sha256_obj\([^)]*\)\[:\d+\]"),
               re.compile(r"envelope_hash\(\)\[:\d+\]"),
               re.compile(r"\.hexdigest\(\)\[:\d+\]"),
               # identifier built from a hash VARIABLE (e.g. candidate_hash[:12])
               re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*hash\[:\d+\]"))
    for rel in D6_SOURCE_FILES:
        bad = []
        for ln in (REPO / rel).read_text().splitlines():
            if not SLICE_RE.search(ln):
                continue
            s = ln
            for pat in allowed:
                s = pat.sub("", s)
            if SLICE_RE.search(s):
                bad.append(ln.strip())
        assert not bad, f"{rel} contains slice truncation: {bad}"


def test_d6_package_compiler_slice_only_in_label_namer():
    """R440 migration: the old package_factory slice discipline now
    applies to the canonical compiler + its rendering library."""
    # R440 scope: the canonical COMPILER must never slice authoritative
    # content. (The R424 rendering library invention_bridge/package.py
    # produces bounded SUMMARY machine layers by settled design — the
    # full authoritative records live in the engine spec, traceability,
    # and PDFs; bounded summaries of a canonical source are not content
    # truncation.)
    for rel in ("discovery_fabric/engine/package_compiler.py",):
        src = (REPO / rel).read_text()
        lines = src.splitlines()
        bad = []
        for i, l in enumerate(lines):
            if not SLICE_RE.search(l):
                continue
            s = l
            for pat in (re.compile(r"sha256[^\]]*\]"),
                        re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*hash\[:\d+\]"),
                        re.compile(r"run_id\[:\d+\]"),
                        re.compile(r"\[:12\]"),
                        # exception-message bounding in failure records is
                        # not authoritative-content truncation
                        re.compile(r"str\([^)]*\)\[:\d+\]")):
                s = pat.sub("", s)
            if SLICE_RE.search(s):
                bad.append(l.strip())
        assert not bad, f"{rel} slices content: {bad}"


def test_d6_long_authoritative_text_survives_end_to_end():
    long_constraint = ("the device must satisfy this extremely long "
                       "engineering constraint without truncation: " +
                       "and the constraint continues with quantitative "
                       "context that must remain verbatim " * 10 +
                       "[END-OF-CONSTRAINT-MARKER]")
    env = _survivor_env("mechanical_structural", variant=3)
    env.problem["constraint"] = long_constraint
    spec = build_invention_spec(env, CTX)
    eng = build_engineering_spec(spec, env, CTX)
    # authoritative spec keeps the FULL text
    assert long_constraint == spec["constraints"]["value"]["stated_constraint"]
    assert long_constraint in eng["design_inputs"][0]["value"]
    assert eng["design_inputs"][0]["value"].endswith(
        "[END-OF-CONSTRAINT-MARKER]")
    with tempfile.TemporaryDirectory() as td:
        rep = _compile_post_run(env, spec, eng, Path(td), "testrun:d6")
        folder = Path(rep["package_dir"])
        manifest = json.loads((folder / "PACKAGE_MANIFEST.json").read_text())
        # the full constraint text survives into the compiled package's
        # engineering machine layer (02) — zero silent material truncation
        eng_def = json.loads(
            (folder / "02_ENGINEERING_DEFINITION.json").read_text())
        blob = json.dumps(eng_def, ensure_ascii=False)
        marker_idx = blob.find("[END-OF-CONSTRAINT-MARKER]")
        assert marker_idx > 0, \
            "the long authoritative constraint did not survive into the " \
            "compiled engineering layer"
        # every manifest entry hashes real bytes (nothing truncated)
        for entry in manifest["files"]:
            assert hashlib.sha256(
                (folder / entry["path"]).read_bytes()).hexdigest() == \
                entry["sha256"], entry["path"]


def test_d6_display_register_class_mechanics():
    r = DisplayRegister()
    full = "x" * 500 + "[MARKER]"
    d = r.display("test.path", full, 100)
    assert d.endswith("...") and len(d) == 100
    assert r.violations() == []
    j = r.to_json()
    assert j["entries"][0]["full"] == full  # preserved EXACTLY
    # a tampered register must be detected
    j["entries"][0]["full"] = "tampered"
    r2 = DisplayRegister()
    r2.display("p", "short value", 100)
    r2._entries[0]["display"] = "different value!"
    assert r2.violations()


# ----------------------------------------------------------------------
# Directive 7 — maturity computed from artifact state
# ----------------------------------------------------------------------
def test_d7_maturity_is_computed_not_injected():
    env = _survivor_env("fluidics_hydraulic", variant=5)
    spec = build_invention_spec(env, CTX)
    eng = build_engineering_spec(spec, env, CTX)
    m = compute_maturity(spec, eng, env=env)
    assert m["technology_maturity"] == "ENGINEERING_DEFINITION"
    assert m["next_rung"] == "PROTOTYPE_DESIGN_READY"
    assert [r["rung"] for r in m["rung_evaluations"]] == MATURITY_LADDER
    blockers = m["known_blockers"]
    assert blockers and all({"condition_id", "condition", "evidence"}
                            <= set(b) for b in blockers)
    # the old injected generic blocker strings are GONE
    texts = json.dumps(blockers)
    assert "no physical prototype exists" not in texts
    assert "no regulatory pathway established" not in texts
    # each blocker cites an actual artifact location
    for b in blockers:
        assert b["evidence"], b


def test_d7_maturity_climbs_only_with_real_artifact_state():
    env = _survivor_env("fluidics_hydraulic", variant=6)
    spec = build_invention_spec(env, CTX)
    eng = build_engineering_spec(spec, env, CTX)
    base = compute_maturity(spec, eng, env=env)
    assert base["technology_maturity"] == "ENGINEERING_DEFINITION"
    # simulate completed design work on the actual artifacts
    for d in eng["design_outputs"]:
        d["geometry_status"] = "COMPLETE (design work recorded)"
    for p in eng["engineering_core"]["critical_parameters"]:
        p["value"] = "sourced example value"
        p["status"] = "SOURCE_FACT"
        p["value_status"] = "SOURCE_FACT"
    for b in eng["bom"]:
        b["qty"] = "100"
    better = compute_maturity(spec, eng, env=env)
    assert better["technology_maturity"] == "PROTOTYPE_DESIGN_READY"
    # and no amount of prose can reach TRANSFER_READY without reality
    assert better["transfer_ready"] is False
    assert better["loop_verification_state"] == "NONE"


def test_d7_below_ladder_when_concept_conditions_fail():
    env = _survivor_env("ml_data")
    spec = build_invention_spec(env, CTX)
    eng = build_engineering_spec(spec, env, CTX)
    broken = dict(spec)
    broken["_integrity"] = {"passed": False,
                            "no_fact_promotion_violations": ["x"]}
    m = compute_maturity(broken, eng, env=env)
    assert m["technology_maturity"] == "BELOW_LADDER"


# ----------------------------------------------------------------------
# Directive 8 — the automatic package test (fixture -> everything)
# ----------------------------------------------------------------------
def test_d8_automatic_survivor_to_complete_package_with_hashes():
    env = _survivor_env("fluidics_hydraulic", variant=9)
    with tempfile.TemporaryDirectory() as td:
        run, release = _drive_automatic_pipeline(
            env, Path(td), "90", "testrun:d8")
        folder = Path(release["package_folder"])
        for f in PACKAGE_FILE_SET:
            assert (folder / f).exists() and \
                (folder / f).stat().st_size > 0, f
        assert Path(release["package_zip"]).exists()
        with zipfile.ZipFile(release["package_zip"]) as zf:
            assert zf.testzip() is None
            for f in PACKAGE_FILE_SET:
                assert any(n.endswith(f"/{f}") for n in zf.namelist()), f
        manifest = json.loads((folder / "PACKAGE_MANIFEST.json").read_text())
        # R424 semantic maturity: the engineering tier additionally
        # requires ENGINEERING_3D geometry; the fixture's conceptual
        # SYSTEM_3D package honestly derives the early tier
        assert manifest["package_maturity"] in (
            "EARLY_TECHNICAL_EVALUATION", "ENGINEERING_DEFINITION")
        mb2 = json.loads((folder / "MATURITY_BASIS.json").read_text())
        assert mb2["basis"].startswith("Derived from")
        assert manifest["synthetic_rehearsal"] is True
        assert manifest["loop_verification_state"] == "NONE"
        trace = json.loads(
            (folder / "ENGINEERING_TRACEABILITY.json").read_text())
        assert trace["traceability_state"] in (
            "TRACEABILITY_COMPLETE", "TRACEABILITY_PARTIAL")
        assert release["status"] in (ST_RELEASED, ST_HELD_FOR_HUMAN_REVIEW)


# ----------------------------------------------------------------------
# Directive 9 — scale: 1, 3 and 15 survivors
# ----------------------------------------------------------------------
def test_d9_scale_1_3_15_survivors_zero_cross_contamination():
    domain_ids = list(DOMAIN_PROBES)
    assert len(domain_ids) == 11
    plan = [domain_ids[i % len(domain_ids)] for i in range(15)]
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        releases = []
        seen_invention_ids, seen_spec_hashes, seen_zips = set(), set(), set()
        for i, domain_id in enumerate(plan):
            variant = i // len(domain_ids)
            env = _survivor_env(domain_id, variant=variant)
            run_dir = td / f"run{i+1:02d}"
            run, release = _drive_automatic_pipeline(
                env, run_dir, "9" + f"{i+1:02d}", f"testrun:scale:{i}")
            releases.append((domain_id, run, release, run_dir))
        # --- count checks at 1, 3 and 15 ---
        for n in (1, 3, 15):
            sub = releases[:n]
            for domain_id, run, release, run_dir in sub:
                assert (run_dir / "INVENTION_SPECIFICATION.json").exists()
                assert (run_dir / "ENGINEERING_SPECIFICATION.json").exists()
                assert Path(release["package_zip"]).exists()
                folder = Path(release["package_folder"])
                for f in PACKAGE_FILE_SET:
                    assert (folder / f).exists(), (n, f)
        # --- 15 full counts + uniqueness + zero cross-contamination ---
        for domain_id, run, release, run_dir in releases:
            spec = run._spec
            inv_id = spec["invention_id"]["value"]
            assert inv_id not in seen_invention_ids, \
                f"duplicate invention_id {inv_id}"
            seen_invention_ids.add(inv_id)
            sh = spec["_spec_hash"]
            assert sh not in seen_spec_hashes, "duplicate spec hash"
            seen_spec_hashes.add(sh)
            zp = Path(release["package_zip"])
            zh = release["buyer_package_hash"]
            assert zh not in seen_zips, "duplicate package hash"
            seen_zips.add(zh)
            manifest = json.loads(
                (Path(release["package_folder"]) /
                 "PACKAGE_MANIFEST.json").read_text())
            # each package manifest references ONLY its own run
            assert manifest["run_id"] == release["run_id"]
            assert manifest["invention_id"] == inv_id
            assert manifest["synthetic_rehearsal"] is True
            rel = json.loads((run_dir / "DISCOVERY_RELEASE.json").read_text())
            assert rel["status"] in (ST_RELEASED, ST_HELD_FOR_HUMAN_REVIEW)
            assert rel["invention_id"] == inv_id
            # 02 dossier domain matches the survivor domain (domain-adaptive)
            eng = run._eng
            assert eng["technology_domain"] == domain_id
        assert len(seen_invention_ids) == 15
        assert len(seen_zips) == 15


def test_d9_15_packages_openable_and_each_zip_self_consistent():
    domain_ids = list(DOMAIN_PROBES)
    plan = [domain_ids[i % len(domain_ids)] for i in range(15)]
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for i, domain_id in enumerate(plan):
            env = _survivor_env(domain_id, variant=10 + i)
            run_dir = td / f"ziprun{i+1:02d}"
            _, release = _drive_automatic_pipeline(
                env, run_dir, "8" + f"{i+1:02d}", f"testrun:zip:{i}")
            folder = Path(release["package_folder"])
            with zipfile.ZipFile(release["package_zip"]) as zf:
                assert zf.testzip() is None
                # zip members mirror the folder exactly (hierarchy
                # equality, recursive: the tree carries MODEL/ layers)
                folder_files = {p.name for p in folder.rglob("*")
                                if p.is_file()}
                zip_files = {Path(n).name for n in zf.namelist()}
                assert zip_files == folder_files, domain_id


# ----------------------------------------------------------------------
# Directive 10 — ablation: downstream artifacts change where they should
# ----------------------------------------------------------------------
def _chain_without(stage_to_skip: str, domain_id: str, variant: int = 0):
    env = _survivor_env(domain_id, variant)
    # re-run a fresh envelope but skip one stage
    env = _survivor_env(domain_id, variant)
    plan = [(s, a) for s, a in CHAIN_PLAN if s != stage_to_skip]
    for stg, ad in plan:
        env.run_stage(stg, ad.capability_id, ad.module_path,
                      ad.canonical_fn, ad().execute, env, CTX)
    return env


def test_d10_ablation_each_module_changes_its_downstream_artifact():
    domain_id = "fluidics_hydraulic"
    base_env = _survivor_env(domain_id, variant=42)
    base_spec = build_invention_spec(base_env, CTX)
    base_eng = build_engineering_spec(base_spec, base_env, CTX)
    base_spec_h = base_spec["_spec_hash"]
    base_eng_h = sha256_obj(
        {k: v for k, v in base_eng.items() if not k.startswith("_")})

    def chained_without(stage_to_skip: str) -> Candidate:
        env = _survivor_env(domain_id, 42, chain=False)
        for stg, ad in CHAIN_PLAN:
            if stg == stage_to_skip:
                continue
            env.run_stage(stg, ad.capability_id, ad.module_path,
                          ad.canonical_fn, ad().execute, env, CTX)
        return env

    # COLLISION off -> novelty/prior-art fields change in the SPEC
    env2 = _survivor_env(domain_id, 42, chain=False)
    env2.collision_results = {}
    for stg, ad in CHAIN_PLAN:
        env2.run_stage(stg, ad.capability_id, ad.module_path,
                       ad.canonical_fn, ad().execute, env2, CTX)
    spec2 = build_invention_spec(env2, CTX)
    assert spec2["_spec_hash"] != base_spec_h
    nh = spec2["novelty_hypothesis"]["value"]
    assert nh["collision_novelty_risk"] is None
    assert base_spec["novelty_hypothesis"]["value"][
        "collision_novelty_risk"] is not None

    # ATTACK off -> failure_modes and engineering content change
    env3 = chained_without("CONTRADICTION")
    env3.attack_results = {}
    spec3 = build_invention_spec(env3, CTX)
    assert spec3["_spec_hash"] != base_spec_h
    eng3 = build_engineering_spec(spec3, env3, CTX)
    eng3_h = sha256_obj({k: v for k, v in eng3.items()
                         if not k.startswith("_")})
    assert eng3_h != base_eng_h
    base_fm_modes = {f["mode"] for f in base_eng["failure_analysis"]}
    eng3_fm_modes = {f["mode"] for f in eng3["failure_analysis"]}
    base_findings = {f["finding"]
                     for f in base_eng["adversarial_findings"]["findings"]}
    assert any("adversarial dimension" in m
               for m in base_findings | base_fm_modes)
    assert not any("adversarial dimension" in m for m in eng3_fm_modes)

    # KILLER_EXPERIMENT off -> build plan loses WP-01 and the killer VF
    env4 = chained_without("KILLER_EXPERIMENT")
    spec4 = build_invention_spec(env4, CTX)
    eng4 = build_engineering_spec(spec4, env4, CTX)
    base_wps = [w["work_package"] for w in
                base_eng["engineering_build_plan"]]
    wps4 = [w["work_package"] for w in eng4["engineering_build_plan"]]
    assert len(wps4) < len(base_wps)
    assert "WP-01" in base_wps and "WP-01" in wps4  # renumbered but shorter
    ke4 = spec4["killer_experiment"]["value"]
    assert ke4["selected"] in ("UNKNOWN", "") or not ke4["selected"]
    base_methods = " ".join(v["method"] for v in
                            base_eng["verification_matrix"])
    methods4 = " ".join(v["method"] for v in eng4["verification_matrix"])
    assert "killer experiment" in base_methods
    assert "killer experiment" not in methods4

    # NEXT_BEST_ACTION off -> the RUN record changes (its downstream
    # artifact is the run state; the ranking formula legitimately does not
    # consume NBA content — declared dependency, no score coupling)
    env5 = chained_without("NEXT_BEST_ACTION")
    assert not env5.next_best_action
    assert base_env.next_best_action
    assert base_env.next_best_action.get("ranked_actions")
    # and the stage log proves NBA ran only in the baseline
    assert "NEXT_BEST_ACTION" in [e["stage"] for e in base_env.stage_log]
    assert "NEXT_BEST_ACTION" not in [e["stage"] for e in env5.stage_log]


def test_d10_ablation_domain_module_changes_engineering_and_package():
    domain_id = "rf_wireless"
    base_env = _survivor_env(domain_id)
    base_spec = build_invention_spec(base_env, CTX)
    base_eng = build_engineering_spec(base_spec, base_env, CTX)

    # disable the engineering domain module: detection returns UNKNOWN.
    # engineering_spec imports detect_domain_reasoned by name (E21-D
    # mechanism-driven domain reasoning), so patch THERE.
    import discovery_fabric.engine.engineering_spec as es_mod
    dd = importlib.import_module("discovery_fabric.engine.domains")
    original = es_mod.detect_domain_reasoned
    try:
        es_mod.detect_domain_reasoned = (
            lambda mech, wrapper="", **kw: {
                "domain": "UNKNOWN",
                "template": dd.GENERIC_TEMPLATE,
                "matched_signals": [],
                "epistemic_class": "MODEL_DERIVED",
                "note": "ABLATION: domain module disabled"})
        eng2 = build_engineering_spec(base_spec, base_env, CTX)
    finally:
        es_mod.detect_domain_reasoned = original
    assert base_eng["technology_domain"] == domain_id
    assert eng2["technology_domain"] == "NOT ESTABLISHED"
    h1 = sha256_obj({k: v for k, v in base_eng.items()
                     if not k.startswith("_")})
    h2 = sha256_obj({k: v for k, v in eng2.items()
                     if not k.startswith("_")})
    assert h1 != h2
    # registry-sourced critical parameters exist only with the module ON;
    # with the module OFF only the DO-response placeholders remain
    assert any(not p["parameter"].startswith("DO response for")
               for p in base_eng["engineering_core"]["critical_parameters"])
    assert all(p["parameter"].startswith("DO response for")
               for p in eng2["engineering_core"]["critical_parameters"])
    assert not eng2["domain_validation_methods"]
    assert base_eng["domain_validation_methods"]


# ----------------------------------------------------------------------
# Resume: an interrupted REAL run continues from persisted snapshots
# ----------------------------------------------------------------------
def test_d1_resume_continues_killed_run_without_rerunning_stages():
    env = _survivor_env("thermal", variant=11)   # full offline chain
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # phase 1: simulate a REAL run killed right after RANK but BEFORE
        # the automatic post-RANK pipeline could run (sandbox kill, crash...)
        run1 = EngineRun(env.problem, str(td), run_id="testrun:resume",
                         package_number="90")
        run1.env = env
        run1._persist("problem.json", run1.problem)
        for stage, _ in CHAIN_PLAN:
            run1._persist_envelope(stage)
        done_before = len(run1.env.stage_log)
        assert not (td / "INVENTION_SPECIFICATION.json").exists()

        # phase 2: resume — completed stages are NOT re-run; the fixture
        # stands in for the pre-chain stages (RETRIEVE..ATTACK are provided
        # by the fixture itself, so the resumed conductor marks them
        # DISABLED_BY_CONFIG); the automatic pipeline + release complete
        run2 = EngineRun.from_run_dir(
            str(td), disabled_stages=["RETRIEVE", "FREEZE", "SYNTHESIZE",
                                      "MULTI_SOURCE_DISCOVERY", "COLLISION",
                                      "ATTACK"])
        assert run2.resume is True
        manifest = run2.run()
        assert manifest.get("resumed") is True
        assert manifest.get("resumed_from_stage") == "RANK"
        # the restored stage log contains the ORIGINAL entries (no reruns):
        # exactly one entry per executed chain stage
        stages = [e["stage"] for e in run2.env.stage_log]
        for stg, _ in CHAIN_PLAN:
            assert stages.count(stg) == 1, stg
        # +6 DISABLED entries + 1 for the R394 PREMISE_GATE stage + 1
        # for the R397 PHYSICS stage (neither is in the disabled list,
        # so the resumed conductor EXECUTES both — the fixture problem
        # is premise-coherent and the physics stage is deterministic
        # offline: it evaluates the envelope mechanism honestly, an
        # out-of-domain verdict completes OK without fabricating a
        # comparison). R401: the MECHANISM_SPACE stage also executes
        # (or honestly skips with zero verified evidence) on the resume
        # path — the chain is 17 stages since R481. IMPROVE contributes
        # TWO entries on this path: the loop position's typed
        # DEFERRED_TO_KILL_POINT deferral (+1) AND the Directive-1
        # pipeline's kill-point execution (NO_KILL_EVIDENCE in this
        # fixture — nothing died; +1) — the total is +11 vs the R401
        # count of +9.
        assert len(run2.env.stage_log) == done_before + 11
        # the automatic survivor -> package pipeline ran in phase 2
        assert (td / "INVENTION_SPECIFICATION.json").exists()
        assert (td / "ENGINEERING_SPECIFICATION.json").exists()
        assert (td / "DISCOVERY_RELEASE.json").exists()
        rel = json.loads((td / "DISCOVERY_RELEASE.json").read_text())
        # R440.2: the resumed run DEFERS the package (never a pre-evolution
        # snapshot); the post-run compile completes it from final state
        assert rel["status"] in (ST_RELEASED, ST_HELD_FOR_HUMAN_REVIEW,
                                 "PACKAGE_DEFERRED_TO_COMPILER")
        assert (td / "PACKAGE_DEFERRED.json").is_file() or \
            (td / "INVENTION_LINEAGE.json").is_file()
        pkg = _compile_post_run(run2.env, run2._spec or (json.loads(
            (td / "INVENTION_SPECIFICATION.json").read_text())),
            run2._eng or (json.loads(
                (td / "ENGINEERING_SPECIFICATION.json").read_text())),
            td, "testrun:resume")
        assert pkg["state"] == "ZIP_READY"
        assert Path(pkg["zip_path"]).is_file()
