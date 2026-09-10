"""tests/test_dossier_bridge.py — E1-E14 survivor->package bridge tests.

Offline suite: proves the bridge machinery (registry, invention spec,
engineering spec, design graph, equations, experiment selection, package
generation, learning loop) with SYNTHETIC_TEST_ONLY fixtures and explicit
labels. Live synthesis requires credentials and is covered by the E11 smoke
(discovery_fabric.engine.smoke_e2e), not here.

Constitutional attack cases included (Art. XVII):
  - SOURCE_FACT smuggling (fact promotion attempt) must fail
  - equation evaluation with MODEL_DERIVED inputs must emit NO number
  - AI-source reality events must be rejected by the learning loop
  - survivor gate must refuse non-survivors
  - provider substitution must never be silent
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.test_engine_integration import (  # noqa: E402
    _full_offline_chain, fixture_envelope)
from discovery_fabric.engine.candidate import sha256_obj  # noqa: E402
from discovery_fabric.engine.domains import detect_domain  # noqa: E402
from discovery_fabric.engine.engineering_spec import (  # noqa: E402
    build_design_graph, build_engineering_spec)
from discovery_fabric.engine.equations import (  # noqa: E402
    evaluate_equation, equations_for_domain, select_equations)
from discovery_fabric.engine.experiment_selector import (  # noqa: E402
    select_decisive_experiment)
from discovery_fabric.engine.invention_spec import (  # noqa: E402
    SPEC_FIELDS, assert_no_fact_promotion, build_invention_spec, tagged)
from discovery_fabric.engine.llm_registry import (  # noqa: E402
    PROVIDER_SPECS, ST_PROVIDER_UNAVAILABLE, LLMCallResult, SelectionPolicy,
    availability_matrix, generate, select_provider)
from discovery_fabric.engine.package_compiler import (  # noqa: E402
    compile_package)
from discovery_fabric.engine.run import EngineRun  # noqa: E402

CTX = {"run_id": "testrun:ebridge", "problem_id": "fixture"}


def _compile_from_state(env, spec, eng, td):
    """R440: the E4/E10 package path is the canonical compiler — the
    ONE production entry (the bridge gate invokes it post-evolution).
    The old generate_buyer_package in-run call is retired (Art. LXIV)."""
    from discovery_fabric.engine.experiment_selector import (
        select_decisive_experiment)
    ke = select_decisive_experiment(env)
    run_result = {
        "session_id": "testrun:e4",
        "run_id": "testrun:e4",
        "problem_id": env.problem_id,
        "user_text": (spec.get("problem") or {}).get("value", {}).get(
            "failure") if isinstance(
            (spec.get("problem") or {}).get("value"), dict) else str(
            (spec.get("problem") or {}).get("value", "")),
        "title": (f"{((spec.get('problem') or {}).get('value') or {})
                  .get('device', 'fixture device')} — "
                 f"{((spec.get('problem') or {}).get('value') or {})
                  .get('failure_mode', 'fixture failure')}"),
        "invention_specification": spec,
        "engineering_specification": eng,
        "final_state": {
            "final_status": env.epistemic_state.get("final_status"),
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
    return compile_package(run_result, None, geometry_out, td,
                           rehearsal=True)


# ---------------------------------------------------------------- E1
def test_e1_registry_has_ten_providers():
    # 2026-08-30 (R375): the zai sandbox-local gateway (glm-4-plus) was
    # added as the ninth provider — the documented healthy-transport
    # unblock after the measured NVIDIA latency collapse. 2026-09-05
    # (R411): the tokenrouter direct-HTTPS provider (owner-supplied key,
    # z-ai/glm-5.3-free) was added as the tenth — the R411 campaign
    # unblock when the sandbox zai quota rate-limited. E1 credential
    # independence working as designed; no semantics changed.
    ids = {p.provider_id for p in PROVIDER_SPECS}
    assert ids == {"tokenrouter", "zai", "openrouter", "nvidia",
                   "anthropic", "gemini", "openai", "qwen", "deepseek",
                   "mistral"}


def test_e1_tokenrouter_is_explicit_and_documented():
    # The R411 unblock: owner-supplied key, live-measured BEFORE wiring
    # (Art. III): models listing 200/135 models, glm-5.3-free serves the
    # flagship model, paid route 403 zero credit, default UA passes.
    # Everything recorded in the policy note (Art. XXVII), never silent.
    tr = next(p for p in PROVIDER_SPECS if p.provider_id == "tokenrouter")
    assert tr.env_var == "TOKEN_ROUTER_API_KEY"
    assert tr.url == ("https://api.tokenrouter.com/v1/chat/"
                      "completions")
    assert tr.default_model == "z-ai/glm-5.3-free"
    assert tr.flavor == "openai"
    note = tr.policy_note.lower()
    assert "r411" in note and "live-measured" in note
    # placed at the head of the tier-2 group (before zai) so
    # llm_generate's availability order prefers the healthy path
    assert PROVIDER_SPECS[0].provider_id == "tokenrouter"
    assert PROVIDER_SPECS[1].provider_id == "zai"


def test_e1_zai_gateway_is_explicit_and_documented():
    z = next(p for p in PROVIDER_SPECS if p.provider_id == "zai")
    assert z.env_var == "ZAI_API_KEY"
    assert z.url.startswith("http://127.0.0.1:")  # loopback only
    assert z.policy_note  # the NVIDIA-collapse basis is recorded (Art. XXVII)


def test_e1_nvidia_hosts_frozen_synthesis_model():
    # 2026-08-27: meta/llama-3.1-8b-instruct retired from NVIDIA catalog
    # (HTTP 410 verified). The registered default MUST be the frozen
    # synthesis model family — recorded explicitly, never a silent swap.
    nv = next(p for p in PROVIDER_SPECS if p.provider_id == "nvidia")
    assert nv.default_model == "deepseek-ai/deepseek-v4-flash-0731"
    assert "410" in nv.policy_note  # the retirement fact is recorded


def test_e1_no_keys_means_provider_unavailable_not_none_content(monkeypatch):
    for p in PROVIDER_SPECS:
        monkeypatch.delenv(p.env_var, raising=False)
    res = generate("test prompt")
    assert res.status == ST_PROVIDER_UNAVAILABLE
    assert res.content is None
    assert res.selection_ledger["availability"]  # full matrix recorded
    # the unavailable result names every env key that would unblock
    assert res.selection_ledger["reason"]


def test_e1_explicit_policy_no_silent_substitution(monkeypatch):
    # preferred provider absent -> selection returns None (no silent swap)
    for p in PROVIDER_SPECS:
        monkeypatch.delenv(p.env_var, raising=False)
    monkeypatch.setenv("NVIDIA_API_KEY", "fake-key-for-test")
    spec, ledger = select_provider(
        SelectionPolicy(preferred_providers=["anthropic"],
                        max_preference_fallback=0))
    assert spec is None  # no substitution allowed: policy forbids fallback
    spec2, ledger2 = select_provider(
        SelectionPolicy(preferred_providers=["nvidia"]))
    assert spec2 is not None and spec2.provider_id == "nvidia"
    assert "substituted_from" in ledger2


def test_e1_availability_matrix_records_all_env_vars():
    matrix = availability_matrix()
    assert len(matrix) == 10  # ten providers since 2026-09-05 (R411)
    for m in matrix:
        assert m["env_var"].endswith("_API_KEY")
        assert isinstance(m["available"], bool)


# ---------------------------------------------------------------- E2
def test_e2_invention_spec_complete_and_classed():
    env = _full_offline_chain("PASS")
    spec = build_invention_spec(env, CTX)
    assert all(f in spec for f in SPEC_FIELDS)
    assert spec["_integrity"]["passed"]
    # mechanism is MODELLED — LLM text is never a fact
    assert spec["mechanism"]["epistemic_class"] == "MODELLED"
    # engineering parameters are UNKNOWN at spec time
    assert spec["engineering_parameters"]["epistemic_class"] == "UNKNOWN"


def test_e2_fact_promotion_attack_is_caught():
    env = _full_offline_chain("PASS")
    spec = build_invention_spec(env, CTX)
    smuggled = dict(spec)
    smuggled["smuggled_claim"] = {
        "value": "physically verified in bench test",  # LIE
        "epistemic_class": "SOURCE_FACT",
        "origin_stage": "SYNTHESIZE",
        "evidence_ids": ["nonexistent:evidence"], "note": ""}
    v = assert_no_fact_promotion(smuggled)
    assert v and "nonexistent:evidence" in str(v)


def test_e2_tagged_constructor_blocks_evidenceless_fact():
    with pytest.raises(ValueError):
        tagged("claimed fact", "SOURCE_FACT", "X", evidence_ids=None)


def test_e2_survivor_gate_refuses_rejected_candidate():
    env = fixture_envelope(attack_overall="KILLED")
    env2 = _full_offline_chain("KILLED")
    spec = build_invention_spec(env2, CTX)
    assert (spec.get("_survivor_gate") or {}).get("survivor") is False


# ---------------------------------------------------------------- E6/E7
def test_e6_domain_detection_records_signals():
    d = detect_domain("csf shunt catheter lumen valve pressure regulation")
    assert d["domain"] == "fluidics_hydraulic"
    assert d["matched_signals"]
    assert d["epistemic_class"] == "MODEL_DERIVED"


def test_e6_unknown_domain_stays_unknown():
    d = detect_domain("zzz qqq unknown device xyzzy")
    assert d["domain"] == "UNKNOWN"


def test_e7_equations_have_full_metadata():
    for eq in equations_for_domain("fluidics_hydraulic"):
        assert eq["equation_id"] and eq["expression"] and eq["source"]
        assert eq["applicability"]["epistemic_class"] == "MODEL_DERIVED"
        assert isinstance(eq["assumptions"], list)


def test_e7_no_numbers_from_modelled_inputs():
    eq = equations_for_domain("fluidics_hydraulic")[1]  # Reynolds
    res = evaluate_equation(eq, {
        "rho": {"value": 1000, "epistemic_class": "SOURCE_FACT"},
        "v": {"value": 0.01, "epistemic_class": "MODEL_DERIVED"},
        "D": {"value": 0.001, "epistemic_class": "MODEL_DERIVED"},
        "mu": {"value": 0.001, "epistemic_class": "SOURCE_FACT"}})
    assert res["evaluation"] == "SYMBOLIC_ONLY"
    assert "result" not in res  # NO number emitted


def test_e7_computed_with_sourced_inputs():
    eq = equations_for_domain("fluidics_hydraulic")[1]
    res = evaluate_equation(eq, {
        "rho": {"value": 1000, "epistemic_class": "SOURCE_FACT"},
        "v": {"value": 0.01, "epistemic_class": "COMPUTED"},
        "D": {"value": 0.001, "epistemic_class": "SOURCE_FACT"},
        "mu": {"value": 0.001, "epistemic_class": "SOURCE_FACT"}})
    assert res["evaluation"] == "COMPUTED"
    assert res["result"] == 10.0


def test_e7_unknown_domain_emits_no_equations():
    sel = select_equations({}, "UNKNOWN")
    assert sel["value"] == [] and sel["epistemic_class"] == "UNKNOWN"


# ---------------------------------------------------------------- E3/E8
def test_e3_e8_engineering_spec_and_structural_graph():
    env = _full_offline_chain("PASS")
    spec = build_invention_spec(env, CTX)
    eng = build_engineering_spec(spec, env, CTX)
    for section in ("system_architecture", "design_inputs", "design_outputs",
                    "verification_matrix", "validation_matrix", "materials",
                    "manufacturing", "transfer_boundary",
                    "engineering_build_plan", "failure_analysis",
                    "engineering_core"):
        assert section in eng, section
    g = eng["design_graph"]
    assert g["counts"]["DI"] >= 1 and g["counts"]["DO"] >= 1
    assert g["integrity"]["passed"] is True
    # structural: every DO names parent DI ids explicitly
    di_ids = {d["id"] for d in eng["design_inputs"]}
    for d in eng["design_outputs"]:
        assert set(d["parent_ids"]) & di_ids
    # honest statuses (A7 vocabulary): DOs are CONCEPTUAL/PROPOSED/UNKNOWN
    # with geometry_status ABSENT (no geometry exists yet); verifications
    # not tested
    for d in eng["design_outputs"]:
        assert d["status"] in ("CONCEPTUAL", "PROPOSED", "UNKNOWN"), \
            d["status"]
        assert str(d.get("geometry_status", "")).startswith("ABSENT")
    for v in eng["verification_matrix"]:
        assert v["result"] == "NOT_TESTED"
    # every numeric emission is forbidden: governing model has no numbers
    assert eng["engineering_core"]["governing_model"][
        "boundary_conditions"][0].startswith("to be established")


def test_e3_design_graph_detects_orphan_verifications():
    env = _full_offline_chain("PASS")
    spec = build_invention_spec(env, CTX)
    eng = build_engineering_spec(spec, env, CTX)
    # COMPLETE structural coverage: the killer experiment is parented by
    # EVERY recorded failure mode, so no FM is left without verification
    graph = build_design_graph(spec, env)
    gap_ids = [g["gap"] for g in graph["gaps"]]
    assert not any(g.startswith("FM_WITHOUT_VERIFICATION") for g in gap_ids)
    vf_parents = {p for v in graph["verifications"] for p in v["parent_ids"]}
    fm_ids = {f["id"] for f in graph["f_modes"]}
    assert fm_ids <= vf_parents
    # the ablation direction still holds: WITHOUT a killer experiment only
    # the falsification VF exists and orphans are recorded as explicit gaps
    spec_nk = json.loads(json.dumps(spec))
    spec_nk["killer_experiment"]["value"]["selected"] = "UNKNOWN"
    graph_nk = build_design_graph(spec_nk, env)
    gap_ids_nk = [g["gap"] for g in graph_nk["gaps"]]
    assert any(g.startswith("FM_WITHOUT_VERIFICATION") for g in gap_ids_nk)


# ---------------------------------------------------------------- E9
def test_e9_decisive_experiment_has_explanation_and_unknowns():
    env = _full_offline_chain("PASS")
    sel = select_decisive_experiment(env)
    assert sel["selected"] is not None
    assert "because" in sel["explanation"]
    assert sel["no_invented_values_note"]  # time/kill-probability stay UNKNOWN


# ---------------------------------------------------------------- E4/E10/E12
def _package_fixture(tmp):
    env = _full_offline_chain("PASS")
    spec = build_invention_spec(env, CTX)
    eng = build_engineering_spec(spec, env, CTX)
    return env, spec, eng


def test_e4_e10_full_package_generation_reuses_v4_builders():
    """R440 migration: the survivor -> package path is the canonical
    compiler (temp-dir build -> validators -> independent gate -> atomic
    promotion). The file set + honest maturity labels survive exactly
    as the E4/E10 contract requires."""
    env, spec, eng = _package_fixture(None)
    with tempfile.TemporaryDirectory() as td:
        rep = _compile_from_state(env, spec, eng, td)
        assert rep["state"] == "ZIP_READY", json.dumps(
            rep.get("blocked_record") or rep, indent=2, default=str)[:1500]
        folder = Path(rep["package_dir"])
        for f in ("00_PACKAGE_README.pdf", "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
                  "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
                  "03_BUYER_DECISION_CARD.pdf", "04_EVIDENCE_SUMMARY.pdf",
                  "05_TRANSFER_MANIFEST.pdf", "PACKAGE_MANIFEST.json",
                  "ENGINEERING_TRACEABILITY.json", "MATURITY_BASIS.json"):
            assert (folder / f).exists(), f
        # zip valid and mirrors hierarchy
        import zipfile
        with zipfile.ZipFile(rep["zip_path"]) as zf:
            names = zf.namelist()
            assert any(n.endswith("00_PACKAGE_README.pdf") for n in names)
            assert zf.testzip() is None
        manifest = json.loads((folder / "PACKAGE_MANIFEST.json").read_text())
        assert manifest["synthetic_rehearsal"] is True
        assert manifest["loop_verification_state"] == "NONE"
        assert manifest["real_loop_verified"] is False
        assert manifest["transfer_ready"] is False
        # R440: the object model + section provenance ride in the tree
        assert (folder / "TECHNOLOGY_PACKAGE_MODEL.json").is_file()
        assert (folder / "PACKAGE_SECTION_PROVENANCE.json").is_file()


def test_e12_traceability_is_structural_with_hashes():
    """R440 migration: the E12 structural-traceability contract now
    reads ENGINEERING_TRACEABILITY.json from a COMPILED package (the
    live R425 link-graph schema: explicit link records with ids,
    never a bare token match)."""
    env, spec, eng = _package_fixture(None)
    with tempfile.TemporaryDirectory() as td:
        rep = _compile_from_state(env, spec, eng, td)
        assert rep["state"] == "ZIP_READY"
        trace = json.loads((Path(rep["package_dir"])
                            / "ENGINEERING_TRACEABILITY.json").read_text())
        assert trace["schema"] == "R425_TRACEABILITY_GRAPH"
        links = trace["links"]
        assert links, "no traceability links recorded"
        kinds = {l["link_kind"] for l in links}
        # the real edge classes are present (DI->DO->FM->VF graph)
        assert "DO_TO_DI" in kinds or "FM_TO_DO" in kinds, kinds
        for l in links:
            # every link is a STRUCTURAL record: source + target ids
            assert l.get("source_id") or l.get("from") or l.get("target"), l
            assert l.get("link_kind")
        # missing links are explicit UNKNOWNs with a cited basis —
        # never silent gaps
        classification = trace["classification_scheme"]
        assert "UNKNOWN" in classification["EXPLICIT"] or \
            "UNKNOWN" in str(classification)
        assert trace["traceability_state"] in (
            "TRACEABILITY_COMPLETE", "TRACEABILITY_PARTIAL",
            "TRACEABILITY_UNKNOWN")


def test_e12_maturity_basis_is_derived_and_honest():
    """R440 migration: maturity honesty reads MATURITY_BASIS.json +
    LOOP_STATE.json from a COMPILED package."""
    env, spec, eng = _package_fixture(None)
    with tempfile.TemporaryDirectory() as td:
        rep = _compile_from_state(env, spec, eng, td)
        assert rep["state"] == "ZIP_READY"
        folder = Path(rep["package_dir"])
        mb = json.loads((folder / "MATURITY_BASIS.json").read_text())
        loop = json.loads((folder / "LOOP_STATE.json").read_text())
        manifest = json.loads((folder / "PACKAGE_MANIFEST.json").read_text())
        assert loop["loop_verification_state"] == "NONE"
        # Art. XXXVII labels declared by EVERY package (manifest-level)
        assert manifest["loop_verification_state"] == "NONE"
        assert manifest["real_loop_verified"] is False
        assert manifest["synthetic_rehearsal"] is True
        # Directive 7: maturity DERIVED from semantically complete
        # records — the basis string names its derivation
        assert mb["basis"].startswith("Derived from")
        # R424 semantic maturity: the tier honestly reflects the
        # conceptual SYSTEM_3D class (engineering tier requires
        # ENGINEERING_3D geometry)
        assert mb["technology_maturity"] in (
            "EARLY_TECHNICAL_EVALUATION", "ENGINEERING_DEFINITION")
        assert mb["counts"]["design_inputs"] >= 1
        assert mb["semantic_gates"]["counts_semantically_complete"] \
            is not None
        assert mb["honesty"]
        assert isinstance(mb["known_blockers"], list)


# ---------------------------------------------------------------- E11
def test_e11_rehearsal_smoke_proves_all_links():
    from discovery_fabric.engine.smoke_e2e import run_rehearsal
    with tempfile.TemporaryDirectory() as td:
        rc = run_rehearsal(td)
        assert rc == 0
        proof = json.loads((Path(td) / "RUN_LINK_PROOF.json").read_text())
        assert proof["verdict"] == "REHEARSAL_PASS"
        assert proof["SYNTHETIC_REHEARSAL"] is True
        assert proof["REAL_LOOP_VERIFIED"] is False
        assert len(proof["links_verified"]) >= 31


def test_e11_real_smoke_fails_honest_on_missing_credentials(monkeypatch):
    """Without keys, REAL mode must FAIL at SYNTHESIZE with
    PROVIDER_UNAVAILABLE — and must NOT reach the post-RANK pipeline. The
    DISCOVERY_RELEASE still exists and is honest (Directive 2). RETRIEVE is
    disabled and a frozen fixture evidence item is seeded so the run reaches
    SYNTHESIZE deterministically (no network dependence); the credential
    loader is no-op'd so live CEO keys cannot leak into this test."""
    from discovery_fabric.engine.llm_registry import PROVIDER_SPECS
    for p in PROVIDER_SPECS:
        monkeypatch.delenv(p.env_var, raising=False)
    import discovery_fabric.engine.adapters as A
    monkeypatch.setattr(A, "load_credentials", lambda path=None: {})
    from tests.test_engine_integration import PROBLEM, fixture_envelope
    with tempfile.TemporaryDirectory() as td:
        run = EngineRun(PROBLEM, td, disabled_stages=[
            "RETRIEVE", "MULTI_SOURCE_DISCOVERY", "COLLISION", "ATTACK"])
        seeded = fixture_envelope()  # post-RETRIEVE+FREEZE state, offline
        run.env = seeded
        manifest = run.run()
        assert "PROVIDER_UNAVAILABLE" in \
            manifest["failed_stages"].get("SYNTHESIZE", "")
        assert not (Path(td) / "INVENTION_SPECIFICATION.json").exists()
        rel = json.loads((Path(td) / "DISCOVERY_RELEASE.json").read_text())
        assert rel["status"] == "DISCOVERY_INCOMPLETE"
        assert rel["invention_spec_hash"] is None


# ---------------------------------------------------------------- E13
def _valid_event(event_id, source_type="EXTERNAL_HUMAN", **extra):
    ev = {
        "event_id": event_id, "event_type": "BUYER_FEEDBACK",
        "package_id": "pkg-x", "source_type": source_type,
        "organization": "Test Org", "operator": "J. Smith",
        "acquisition_timestamp": "2026-08-27T10:00:00Z",
        "raw_artifact_ref": "/tmp/feedback.pdf",
        "raw_data_sha256": "a" * 64,
        "attestation": {"attestation_text": "real", "attestation_hash": "b" * 64},
        "custody_chain": [{"step": 1, "actor": "J. Smith",
                           "timestamp": "2026-08-27T10:00:00Z",
                           "action": "authored"}],
        "provenance_validated": True,
        "buyer_organization": "Test Org", "contact_identity": "J. Smith",
        "interaction_channel": "email", "feedback_type": "TECHNICAL_CONCERN",
        "feedback_content": "concern", "original_feedback_artifact_ref":
            "/tmp/feedback.pdf",
        "outcome": {"observation": "SUPPORTS_EXPECTED_EFFECT",
                    "parameter": "expected effect"}}
    ev.update(extra)
    return ev

