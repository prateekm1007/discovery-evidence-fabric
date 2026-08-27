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
from discovery_fabric.engine.package_factory import (  # noqa: E402
    build_maturity_basis, build_traceability, generate_buyer_package)
from discovery_fabric.engine.run import EngineRun  # noqa: E402

CTX = {"run_id": "testrun:ebridge", "problem_id": "fixture"}


# ---------------------------------------------------------------- E1
def test_e1_registry_has_eight_providers():
    ids = {p.provider_id for p in PROVIDER_SPECS}
    assert ids == {"openrouter", "nvidia", "anthropic", "gemini", "openai",
                   "qwen", "deepseek", "mistral"}


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
    assert len(matrix) == 8
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
    # honest statuses: DOs absent, verifications not tested
    for d in eng["design_outputs"]:
        assert d["status"] == "ABSENT"
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
    env, spec, eng = _package_fixture(None)
    with tempfile.TemporaryDirectory() as td:
        rep = generate_buyer_package(td, spec, eng, env,
                                     {"run_id": "t", "package_number": "90"},
                                     rehearsal=True)
        assert rep["complete"] is True
        assert rep["missing_links"] == []
        assert rep["traceability_passed"] is True
        folder = Path(rep["folder"])
        for f in ("00_PACKAGE_README.pdf", "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
                  "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
                  "03_BUYER_DECISION_CARD.pdf", "04_EVIDENCE_SUMMARY.pdf",
                  "05_TRANSFER_MANIFEST.pdf", "PACKAGE_MANIFEST.json",
                  "ENGINEERING_TRACEABILITY.json", "MATURITY_BASIS.json"):
            assert (folder / f).exists(), f
        # zip valid and mirrors hierarchy
        import zipfile
        with zipfile.ZipFile(rep["zip"]) as zf:
            names = zf.namelist()
            assert any(n.endswith("00_PACKAGE_README.pdf") for n in names)
            assert zf.testzip() is None
        manifest = json.loads((folder / "PACKAGE_MANIFEST.json").read_text())
        assert manifest["synthetic_rehearsal"] is True
        assert manifest["loop_verification_state"] == "NONE"
        assert manifest["real_loop_verified"] is False
        assert manifest["transfer_ready"] is False


def test_e12_traceability_is_structural_with_hashes():
    env, spec, eng = _package_fixture(None)
    pkg = {"pi": {"pkg_id": spec["invention_id"]["value"]},
           "external_sources": []}
    trace = build_traceability(spec, eng, pkg, env)
    assert trace["passed"] is True
    chains = trace["traceability_chains"]
    assert chains
    by_type = {}
    for c in chains:
        by_type.setdefault(c["chain_type"], []).append(c)
    for t in ("DESIGN_INPUT", "DESIGN_OUTPUT", "FAILURE_MODE",
              "VERIFICATION"):
        assert t in by_type, t
    for c in chains:
        assert c["hash"]  # every chain node carries a content hash
    assert trace["di_do_consistency"]["method"].startswith("structural")
    assert trace["number_provenance"]["violations"] == []


def test_e12_maturity_basis_is_derived_and_honest():
    env, spec, eng = _package_fixture(None)
    mb = build_maturity_basis(spec, eng, {"maturity": "EARLY_CONCEPT"},
                              env=env)
    assert mb["loop_verification_state"] == "NONE"
    assert mb["real_loop_verified"] is False
    assert mb["transfer_ready"] is False
    # Directive 7: maturity COMPUTED from artifact state, blockers are the
    # evaluated unsatisfied conditions of the next rung — no injected list
    assert mb["basis"].startswith("computed")
    assert mb["technology_maturity"] == "ENGINEERING_DEFINITION"
    assert mb["next_rung"] == "PROTOTYPE_DESIGN_READY"
    assert mb["known_blockers"] and all(
        {"condition_id", "condition", "evidence"} <= set(b)
        for b in mb["known_blockers"])
    assert any("geometry" in b["condition"].lower()
               for b in mb["known_blockers"])
    assert mb["counts"]["verifications_tested"] == 0
    assert mb["counts"]["validations_performed"] == 0


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


def test_e13_reality_boundary_ai_source_rejected():
    from discovery_fabric.engine.learning_loop import ingest_external_event
    with tempfile.TemporaryDirectory() as td:
        rec = ingest_external_event(
            _valid_event("evt:ai:1", source_type="AI"),
            {"package_id": "pkg-x"}, td)
        assert rec["action"] == "REJECTED_INVALID_EVENT"
        assert rec["belief_changed"] is False


def test_e13_incomplete_event_rejected_no_belief_change():
    from discovery_fabric.engine.learning_loop import ingest_external_event
    with tempfile.TemporaryDirectory() as td:
        rec = ingest_external_event({"event_id": "evt:x", "event_type":
                                     "BUYER_FEEDBACK"}, {"package_id": "p"}, td)
        assert rec["action"] == "REJECTED_INVALID_EVENT"


def test_e13_valid_event_updates_belief_and_mutates_candidate():
    from discovery_fabric.engine.learning_loop import (REFUTES,
                                                       ingest_external_event)
    env, spec, eng = _package_fixture(None)
    ev = _valid_event("evt:ok:1")
    ev["outcome"] = {"observation": REFUTES, "parameter": "expected effect"}
    with tempfile.TemporaryDirectory() as td:
        ledger = str(Path(td) / "TEST_ONLY_REALITY_LEDGER.jsonl")
        rec = ingest_external_event(
            ev, {"package_id": spec["invention_id"]["value"],
                 "invention_spec": spec, "engineering_spec": eng,
                 "prior_belief": 0.6,
                 "candidate_envelope_hash": env.envelope_hash(),
                 "run_id": "t", "package_number": "91"}, td,
            ledger_path=ledger)
        assert rec["ledger_path_used"] == ledger
        # the CANONICAL ledger was NOT touched by this test (Art. VI)
        from discovery_fabric.engine.learning_loop import _load_r370g
        assert _load_r370g().REALITY_EVENT_LEDGER_PATH.endswith(
            "REALITY_EVENT_LEDGER.jsonl")
        assert rec["final_action"] == "PROCESSED"
        assert rec["belief_update"]["posterior"] < 0.6
        assert rec["belief_update"]["prior_epistemic_class"] == "MODEL_DERIVED"
        assert rec["belief_update"]["observation_epistemic_class"] == \
            "EXPERIMENTALLY_ESTIMATED"
        mut = rec["candidate_mutation"]
        for k in ("before_hash", "after_hash", "trigger_event_id", "reason",
                  "timestamp"):
            assert k in mut  # Art. XXXVIII causal mutation fields
        assert rec["dossier_v2"]["complete"] is True
        addendum = rec["dossier_v2"]["addendum"]
        assert addendum["real_loop_verified"] is False  # derived, never assigned
        assert (Path(td) / "LEARNING_CONSTRAINTS.jsonl").exists()
