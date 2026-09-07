"""tests/test_r416_evolution.py — the honest-causes-evolution battery.

Operator directive R416 (honest-causes-evolution-v1), acceptance
sections C-G:

  Phase C — mandatory invention: every valid query produces at least
             one architecture; the fallback generation is honestly
             labeled GENERATED/AI_PROPOSED (never evidence).
  Phase D — causal evolution: the lineage preserves parent_id /
             child_id / lineage / change_delta / reason_for_change and
             the full causal delta (diagnosed_cause, causal_change,
             new_capability, new_interaction, new_operating_regime,
             predicted_effect, frontier_capability).
  Phase E — the 30-year engine is part of the evolution generation
             (CURRENT -> 2055 EVOLUTION -> REQUIRED CAPABILITY ->
             CAPABILITY BACKCAST -> TODAY'S FRONTIER -> TRANSFER).
  Phase G — the SEALED acceptance fixture: a controlled problem where
             GEN 1 is guaranteed to hit a known structural challenge,
             then the REAL ENGINE EXECUTION PATH demonstrates
             GEN 1 -> CHALLENGE -> DIAGNOSIS -> GEN 2 -> NEW CAUSAL
             DELTA -> FRESH EVIDENCE -> RE-EVALUATION.

Honest-cause acceptance (the R416 root-cause fix):
  - a SYNTHESIZE failure is MECHANISM_GENERATION_FAILED — never
    REJECTED, never described as an adversarial rejection.
  - the product surface never renders the banned dead-end sentences.
  - infrastructure failures stay typed (Art. LXI), maturity labels are
    derived from verification events (Art. LX), nothing is softened
    into a survivor (Art. LXVIII).

Hermetic contract (Art. IX): the LLM transport is a RECORDED SCRIPT
(the sealed fixture — no network, deterministic); retrieval is
fixture-bound; the routing ledger/state/catalog are redirected to tmp
by tests/conftest.py. Production state is never touched.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import evolution as ev  # noqa: E402
from toscanini import run_state as rs  # noqa: E402
from toscanini import user_state as us  # noqa: E402


BANNED_STRINGS = (
    "no defensible invention survived",
    "candidate rejected",
    "not defensible enough to package",
)


# ---------------------------------------------------------------------------
# 1. Unit contracts — diagnosis, maturity, lineage helpers
# ---------------------------------------------------------------------------

class TestDiagnosis:
    def test_synthesize_failure_is_generation_failure_not_rejection(self,
                                                                    tmp_path):
        cause = ev.diagnose_death_cause(
            tmp_path, {"SYNTHESIZE": "LLM failed"}, {})
        assert cause["cause"] == ev.CAUSE_MECHANISM_GENERATION_FAILURE
        assert cause["infrastructure_class"] is False
        assert any("SYNTHESIZE" in b for b in cause["basis"])

    def test_adjudicated_rejection_is_adversarial(self, tmp_path):
        cause = ev.diagnose_death_cause(
            tmp_path, {}, {"final_status": "REJECTED"})
        assert cause["cause"] == ev.CAUSE_ADVERSARIAL_KILL

    def test_retrieve_failure_is_infrastructure(self, tmp_path):
        cause = ev.diagnose_death_cause(
            tmp_path, {"RETRIEVE": "provider down"}, {})
        assert cause["cause"] == ev.CAUSE_EVIDENCE_RETRIEVAL_FAILURE
        assert cause["infrastructure_class"] is True   # Art. LXI

    def test_physics_bound_violation_from_envelope(self, tmp_path):
        (tmp_path / "envelope_PHYSICS.json").write_text(json.dumps({
            "physics": {"lifecycle_verdict":
                        "PLAUSIBILITY_BOUND_VIOLATED"}}))
        cause = ev.diagnose_death_cause(tmp_path, {}, {})
        assert cause["cause"] == ev.CAUSE_PHYSICS_BOUND_VIOLATION

    def test_per_generation_diagnosis_uses_own_record(self):
        gen = {"challenge": {"killed": True,
                             "kill_stage": "ENGINEERING_ATTACK"}}
        cause = ev.diagnose_from_generation(gen)
        assert cause["cause"] == ev.CAUSE_ADVERSARIAL_KILL

    def test_unchallenged_generation_has_no_diagnosis(self):
        assert ev.diagnose_from_generation(
            {"challenge": {"killed": False}}) is None   # Art. XXV

    def test_premise_incoherent_first(self, tmp_path):
        cause = ev.diagnose_death_cause(
            tmp_path, {"PREMISE_GATE": "incoherent",
                       "SYNTHESIZE": "also failed"}, {})
        assert cause["cause"] == ev.CAUSE_PREMISE_INCOHERENT


class TestMaturity:
    def test_generated_default(self):
        assert ev.maturity_for({"challenge": {}}) == ev.MATURITY_GENERATED

    def test_evidence_supported_requires_verification_event(self):
        assert ev.maturity_for({"evidence_verified": True}) == \
            ev.MATURITY_EVIDENCE_SUPPORTED

    def test_simulated_requires_beats_baseline(self):
        assert ev.maturity_for(
            {"challenge": {"physics_lifecycle": "BEATS_BASELINE"}}) == \
            ev.MATURITY_SIMULATED
        assert ev.maturity_for(
            {"challenge": {"physics_lifecycle":
                           "DOES_NOT_BEAT_BASELINE"}}) == \
            ev.MATURITY_GENERATED

    def test_experimentally_verified_never_set_by_engine(self):
        # Art. LIII: reality cannot be simulated into existence — the
        # engine path may NEVER assert experimental verification.
        assert ev.maturity_for({"challenge": {}}) != \
            ev.MATURITY_EXPERIMENTALLY_VERIFIED
        assert ev.maturity_for({"evidence_verified": True,
                                "challenge": {"survived": True}}) != \
            ev.MATURITY_EXPERIMENTALLY_VERIFIED


class TestLineageHelpers:
    def test_lineage_summary_shape(self):
        gens = [{"gen": 1, "invention_id": "a", "state":
                 ev.INVENTION_REJECTED, "maturity":
                 ev.MATURITY_GENERATED},
                {"gen": 2, "invention_id": "b", "state":
                 ev.INVENTION_REQUIRES_EXPERIMENT,
                 "maturity": ev.MATURITY_GENERATED}]
        s = ev.lineage_summary(gens, "SURVIVOR_REACHED", "run1",
                               {"max_evolution_generations": 3})
        assert s["n_generations"] == 2
        assert s["n_evolution_generations"] == 1
        assert s["survivor_reached"] is True
        assert s["survivor_gen"] == 2
        assert s["current_invention"]["gen"] == 2
        assert "honesty_contract" in s

    def test_new_invention_ids_are_stable_and_distinct(self):
        a = ev.new_invention_id("run", 1)
        b = ev.new_invention_id("run", 2)
        assert a != b and a.endswith("gen1") and b.endswith("gen2")

    def test_env_switches(self, monkeypatch):
        monkeypatch.setenv("ENGINE_EVOLUTION", "0")
        assert ev.evolution_enabled() is False
        monkeypatch.setenv("ENGINE_EVOLUTION", "1")
        assert ev.evolution_enabled() is True
        monkeypatch.delenv("ENGINE_EVOLUTION")
        assert ev.evolution_enabled() is True   # default ON
        monkeypatch.setenv("ENGINE_EVOLUTION_MAX_GENERATIONS", "7")
        assert ev.max_evolution_generations() == 7
        monkeypatch.setenv("ENGINE_EVOLUTION_MAX_GENERATIONS", "junk")
        assert ev.max_evolution_generations() == 3


class TestFieldParsing:
    def test_parse_fields_extracts_schema_lines(self):
        content = ("CURRENT: silicon cells at 22%\n"
                   "EVOLUTION_2055: tandem perovskite stacks\n"
                   "MECHANISM: multi-junction capture\n"
                   "CAUSAL_CHANGE: add intermediate layer\n")
        parsed = ev._parse_fields(content, [
            "CURRENT", "EVOLUTION_2055", "MECHANISM", "CAUSAL_CHANGE"])
        assert parsed["current"] == "silicon cells at 22%"
        assert parsed["causal_change"] == "add intermediate layer"

    def test_missing_fields_stay_absent(self):
        parsed = ev._parse_fields("MECHANISM: x", ["MECHANISM", "TRANSFER"])
        assert "transfer" not in parsed     # Art. VI: never fabricated


# ---------------------------------------------------------------------------
# 2. The product projections — honest causes, no banned sentences
# ---------------------------------------------------------------------------

class TestProductProjections:
    def _session(self, final_status: str, status: str = "COMPLETE",
                 run_dir: Optional[Path] = None,
                 package: Optional[Dict] = None) -> Dict:
        return {"session_id": "s", "user_text": "problem",
                "status": status, "final_status": final_status,
                "run_dir": str(run_dir) if run_dir else None,
                "package": package or {}}

    def test_evolved_candidate_with_package_is_survived(self, tmp_path):
        s = self._session("EVOLVED_INVENTION_CANDIDATE",
                         package={"complete": True})
        out = rs.terminal_outcome(s, tmp_path)
        assert out["outcome"] == rs.OUTCOME_SURVIVED

    def test_evolved_candidate_without_package_requires_experiment(self):
        s = self._session("EVOLVED_INVENTION_CANDIDATE")
        out = rs.terminal_outcome(s, None)
        assert out["outcome"] == rs.OUTCOME_REQUIRES_EXPERIMENT

    def test_under_development_presents_current_invention(self, tmp_path):
        (tmp_path / "INVENTION_LINEAGE.json").write_text(json.dumps({
            "n_generations": 3,
            "current_invention": {"gen": 3, "maturity": "GENERATED"}}))
        s = self._session("INVENTION_UNDER_DEVELOPMENT",
                          run_dir=tmp_path)
        out = rs.terminal_outcome(s, tmp_path)
        assert out["outcome"] == rs.OUTCOME_UNDER_DEVELOPMENT
        assert "GEN 3" in out["basis"]
        assert "maturity GENERATED" in out["basis"]

    def test_legacy_rejected_maps_to_under_development_not_dead_end(self):
        # R416 acceptance: pre-R416 records never render the banned
        # dead-end sentence — they project onto development state.
        s = self._session("REJECTED")
        out = rs.terminal_outcome(s, None)
        assert out["outcome"] == rs.OUTCOME_UNDER_DEVELOPMENT
        assert rs.OUTCOME_LABELS[out["outcome"]] != \
            "No defensible invention survived this run"

    def test_mechanism_generation_failed_is_run_blocked_class(self):
        # infrastructure-class terminal (Art. LXI) — never a verdict
        s = self._session("MECHANISM_GENERATION_FAILED")
        v = us.user_state_view(s)
        assert v["user_state"] == "COMPLETED_GENERATION_FAILED"
        blob = json.dumps(v).lower()
        for b in BANNED_STRINGS:
            assert b not in blob

    def test_generations_projection_full_shape(self, tmp_path):
        (tmp_path / "INVENTION_LINEAGE.json").write_text(json.dumps({
            "generations": [{
                "gen": 2, "invention_id": "inv:x:gen2",
                "parent_id": "inv:x:gen1", "lineage": ["inv:x:gen1",
                                                       "inv:x:gen2"],
                "origin": "EVOLUTION_CAUSAL_DELTA",
                "state": ev.INVENTION_REQUIRES_EXPERIMENT,
                "maturity": ev.MATURITY_GENERATED,
                "architecture": {"mechanism": "m", "intervention": "i"},
                "causal_delta": {"causal_change": "cc",
                                 "new_capability": "nc",
                                 "new_interaction": "ni",
                                 "new_operating_regime": "nor",
                                 "predicted_effect": "pe",
                                 "frontier_capability": "fc",
                                 "thirty_year_engine": {
                                     "current": "a",
                                     "evolution_2055": "b"},
                                 "diagnosed_cause": "ADVERSARIAL_KILL"},
                "challenge": {"survived": True},
                "fresh_evidence": {"n_items": 4, "query": "q"},
                "change_delta": "cc",
            }],
            "n_generations": 2, "current_invention": {"gen": 2},
            "stop_reason": "SURVIVOR_REACHED"}))
        proj = rs.generations_projection({}, tmp_path)
        assert proj is not None
        g = proj["generations"][0]
        assert g["label"] == "INVENTION 02"
        assert g["parent_id"] == "inv:x:gen1"
        assert g["causal_delta"]["frontier_capability"] == "fc"
        assert g["causal_delta"]["thirty_year_engine"]["evolution_2055"] == "b"
        assert g["fresh_evidence"]["n_items"] == 4

    def test_phase_progression_generation_aware(self, tmp_path):
        (tmp_path / "problem.json").write_text("{}")
        (tmp_path / "EVOLUTION_GEN_1.json").write_text("{}")
        (tmp_path / "EVOLUTION_GEN_2.json").write_text("{}")
        (tmp_path / "INVENTION_LINEAGE.json").write_text(json.dumps({
            "generations": [
                {"gen": 1, "challenge": {"killed": True}},
                {"gen": 2, "challenge": {"survived": True}}]}))
        s = self._session("", status="RUNNING", run_dir=tmp_path)
        phases = rs.phase_progression(s, tmp_path, {})
        labels = [p["label"] for p in phases]
        assert "Inventing architecture 1" in labels
        assert "Challenging architecture 1" in labels
        assert "Testing architecture 2" in labels
        assert "Developing architecture 3" in labels
        dev = [p for p in phases
               if p["label"] == "Developing architecture 3"][0]
        assert dev["state"] == "IN_PROGRESS"

    def test_no_lineage_keeps_standard_phases(self, tmp_path):
        (tmp_path / "problem.json").write_text("{}")
        s = self._session("", status="RUNNING", run_dir=tmp_path)
        phases = rs.phase_progression(s, tmp_path, {})
        labels = [p["label"] for p in phases]
        assert labels[:2] == ["Investigating your problem",
                              "Gathering evidence"]
        assert "Inventing architecture 1" in labels

    def test_user_state_never_renders_banned_sentences(self, tmp_path):
        cases = [
            self._session("EVOLVED_INVENTION_CANDIDATE",
                          package={"complete": True, "maturity": "GENERATED"}),
            self._session("EVOLVED_INVENTION_CANDIDATE"),
            self._session("INVENTION_UNDER_DEVELOPMENT", run_dir=tmp_path),
            self._session("MECHANISM_GENERATION_FAILED"),
            self._session("REJECTED"),
            self._session("AUTOMATED_INVENTION_CANDIDATE"),
        ]
        for s in cases:
            v = us.user_state_view(s)
            blob = json.dumps(v).lower()
            for b in BANNED_STRINGS:
                assert b not in blob, (s.get("final_status"), b)

    def test_generation_note_reads_lineage(self, tmp_path):
        (tmp_path / "INVENTION_LINEAGE.json").write_text(json.dumps({
            "n_generations": 4, "current_invention": {"gen": 4,
                                                      "maturity":
                                                      "GENERATED"}}))
        note = us._generation_note({"run_dir": str(tmp_path)})
        assert "4 architecture generations" in note
        assert "GEN 4" in note


# ---------------------------------------------------------------------------
# 3. THE SEALED EVOLUTION ACCEPTANCE FIXTURE (Phase G)
#    The REAL engine execution path — EngineRun.run() end-to-end with a
#    scripted transport: GEN 1 hits a KNOWN structural challenge
#    (synthesis failure), the machine must demonstrate
#    GEN 1 -> CHALLENGE -> DIAGNOSIS -> GEN 2 -> NEW CAUSAL DELTA ->
#    FRESH EVIDENCE -> RE-EVALUATION.
# ---------------------------------------------------------------------------

SEALED_PROBLEM = {
    "problem_id": "r416_sealed_fixture",
    "device": "photovoltaic module",
    "failure_mode": "EFFICIENCY_CEILING",
    "failure": ("Sealed acceptance fixture: the module's conversion "
                "efficiency saturates at the single-junction limit; "
                "the user asked for the most efficient solar panel in "
                "the world."),
    "constraint": "Must beat the single-junction baseline economically.",
    "sources": {"fixture": "SEALED"},
}

# The scripted LLM transport — CONTENT-ADDRESSED (robust to call
# order; the gauntlet interleaves its own calls):
#   "mechanism interpreter" prompt (SYNTHESIZE): transport failure ->
#       SYNTHESIZE fails — the KNOWN structural challenge of GEN 1
#   "Propose the FIRST invention architecture" (fallback baseline):
#       the mandatory invention (Phase C)
#   "Evolve the invention lineage" (causal evolution): the GEN-2
#       architecture with the full causal delta + 30-year walk
#   every other call (independent attack etc.): CALL_FAILED ->
#       ATTACK_INCOMPLETE, which never kills (Art. XXIX)
SCRIPT_BASELINE = {"status": "OK", "content": (
    "MECHANISM: tandem multi-junction photon sorting\n"
    "INTERVENTION: stack a perovskite wide-gap cell on the silicon "
    "cell with a spectrally-selective recombination layer\n"
    "EXPECTED_EFFECT: conversion efficiency above the "
    "single-junction ceiling\n"
    "FALSIFICATION_TEST: measure tandem stack efficiency against "
    "the silicon-only baseline under AM1.5G\n"
    "OPERATING_REGIME: standard terrestrial irradiance\n")}
SCRIPT_EVOLUTION = {"status": "OK", "content": (
    "CURRENT: silicon single-junction module at its efficiency "
    "ceiling\n"
    "EVOLUTION_2055: low-cost tandem perovskite-silicon stacks "
    "with stable wide-gap absorbers\n"
    "REQUIRED_CAPABILITY: a recombination interlayer that is "
    "transparent and stable\n"
    "CAPABILITY_BACKCAST: intermediate band engineering then "
    "mature interlayer deposition\n"
    "TODAYS_FRONTIER: perovskite-silicon tandem cell efficiency "
    "gains from photonic interlayers\n"
    "TRANSFER: use the frontier interlayer in this module's stack\n"
    "MECHANISM: spectrally-selective photonic interlayer enables "
    "tandem current matching\n"
    "INTERVENTION: insert a transparent conductive photonic "
    "recombination layer between the silicon and perovskite "
    "subcells\n"
    "EXPECTED_EFFECT: matched subcell currents raise stack "
    "efficiency beyond the ceiling\n"
    "FALSIFICATION_TEST: measure the tandem stack's IV curve with "
    "and without the interlayer\n"
    "CAUSAL_CHANGE: replace direct contact with a photonic "
    "recombination interlayer (new interaction, not a rewording)\n"
    "NEW_CAPABILITY: spectrally selective carrier recombination\n"
    "NEW_INTERACTION: photon recycling between subcells through "
    "the interlayer\n"
    "NEW_OPERATING_REGIME: current-matched tandem operation\n"
    "PREDICTED_EFFECT: efficiency gain on the order of several "
    "absolute percentage points\n"
    "FRONTIER_CAPABILITY: photonic interlayers from the "
    "perovskite-tandem photovoltaics frontier\n")}
SCRIPTED_RESPONSES: List[Dict[str, Any]] = []   # order-based legacy

SCRIPT_TRANSPORT_FAILURE = {"status": "CALL_FAILED",
                            "error": "sealed fixture: transport down"}


def _scripted_response_for(prompt: str) -> Dict[str, Any]:
    p = prompt or ""
    if "mechanism interpreter" in p:
        return SCRIPT_TRANSPORT_FAILURE
    if "Propose the FIRST invention architecture" in p:
        return SCRIPT_BASELINE
    if "Evolve the invention lineage" in p:
        return SCRIPT_EVOLUTION
    return {"status": "CALL_FAILED",
            "error": "sealed fixture: no script for this prompt"}

FIXTURE_EVIDENCE = [
    {"id": "fx:1", "title": "Tandem perovskite-silicon efficiency",
     "abstract": "Tandem stacks exceed single-junction ceilings.",
     "source": "sealed_fixture", "content_hash": "fx1",
     "retrieval_timestamp": "2026-09-07T00:00:00Z"},
]


class _ScriptedCallResult:
    """A minimal LLMCallResult stand-in for the sealed script."""

    def __init__(self, script: Dict[str, Any]):
        self.status = script.get("status", "CALL_FAILED")
        self.content = script.get("content", "")
        self.error = script.get("error", "")
        self.provider_id = "sealed-fixture"
        self.latency_ms = 0

    def to_meta(self) -> Dict[str, Any]:
        return {"provider": self.provider_id, "model": "fixture",
                "status": self.status}

    @property
    def ok(self) -> bool:
        return self.status == "OK"


def _kill_first_then_pass():
    """The fixture's KNOWN STRUCTURAL CHALLENGE: the deterministic
    engineering attack kills the FIRST architecture it sees (GEN 1 —
    guaranteed by the test fixture per the directive's Phase G), then
    passes everything after (so GEN 2's re-evaluation can survive)."""
    from discovery_fabric.engine import engineering_attack as ea
    real_attack = ea.attack_engineering
    state = {"n": 0}

    def scripted_attack(spec, eng, env=None):
        state["n"] += 1
        if state["n"] == 1:
            return {"overall": "KILLED", "counts": {"KILL": 1,
                                                    "REPAIR": 0},
                    "items": [{"target": "mechanism_feasibility",
                               "verdict": "KILL",
                               "basis": ("sealed fixture: GEN 1's known "
                                         "structural challenge — the "
                                         "interlayer concept lacks a "
                                         "manufacturable deposition path"),
                               "affected_claim_ids": ["mechanism"],
                               "repair_hint": ""}]}
        return real_attack(spec, eng, env)

    return scripted_attack


@pytest.fixture()
def sealed_engine(monkeypatch, tmp_path):
    """The sealed acceptance environment: scripted transport,
    fixture-bound retrieval, per-generation CAD disabled (no OCCT
    compute in the hermetic suite — the geometry path has its own
    battery), evolution budget pinned at 1 for determinism."""
    from discovery_fabric.engine import llm_registry as reg
    from discovery_fabric.a2 import retrieve as a2retrieve

    calls: List[Dict[str, Any]] = []

    def scripted_generate(*args, **kwargs):
        prompt = (kwargs.get("prompt") or
                  (args[0] if args else "") or "")
        calls.append({"prompt": prompt[:200]})
        return _ScriptedCallResult(_scripted_response_for(prompt))

    monkeypatch.setattr(reg, "generate", scripted_generate)

    def scripted_retrieve(problem):
        return list(FIXTURE_EVIDENCE)

    monkeypatch.setattr(a2retrieve, "retrieve", scripted_retrieve)

    def scripted_fresh(problem, architecture, snapshot_version):
        return {
            "snapshot_version": snapshot_version,
            "query": "photovoltaic tandem interlayer mechanism",
            "items": list(FIXTURE_EVIDENCE),
            "n_items": 1, "status": "OK",
            "retrieved_at": "2026-09-07T00:00:00Z",
            "snapshot_hash": "fx-snapshot",
            "boundary": "NEW retrieval for this generation",
        }

    monkeypatch.setattr(ev, "retrieve_fresh_evidence", scripted_fresh)

    monkeypatch.setenv("ENGINE_EVOLUTION_MAX_GENERATIONS", "1")
    monkeypatch.setenv("ENGINE_CAD_LLM", "0")

    # Art. IX: the engine's retrieval custody log is append-only
    # production state — redirect it to tmp so the sealed engine run
    # never touches the committed ledger (the R415 conftest pattern,
    # extended to the retrieval log for engine-level runs)
    from discovery_fabric.source_registry import retrieval_log as _rlog
    monkeypatch.setattr(_rlog, "LOG_PATH", tmp_path / "retrieval_log.jsonl")
    from discovery_fabric.source_registry import maturity as _mat
    monkeypatch.setattr(_mat, "RETRIEVAL_LOG_PATH",
                        tmp_path / "retrieval_log.jsonl")

    # the KNOWN STRUCTURAL CHALLENGE: GEN 1 is guaranteed to die at the
    # engineering attack (Phase G's controlled fixture); GEN 2 onward
    # faces the real deterministic instrument
    from discovery_fabric.engine import engineering_attack as _ea
    monkeypatch.setattr(_ea, "attack_engineering",
                        _kill_first_then_pass())
    # keep the CAD pass from touching OCCT in the hermetic suite: the
    # warrants gate runs first and non-geometric content returns
    # NOT_APPLICABLE honestly; force that path with a stub warrants
    monkeypatch.setattr(
        "discovery_fabric.engine.cad_pipeline.geometry_warrants_3d",
        lambda spec: {"warranted": False,
                      "reasons": ["sealed fixture: geometry disabled"]})

    yield monkeypatch, tmp_path, calls


def _run_engine(out_dir: Path) -> Dict[str, Any]:
    from discovery_fabric.engine.run import EngineRun
    run = EngineRun(dict(SEALED_PROBLEM), str(out_dir),
                    with_package=False)
    return run.run()


class TestSealedEvolutionAcceptance:
    """Phase G — the real engine execution path demonstrates the
    transition, not a unit test."""

    def test_gen1_challenge_diagnosis_gen2_causal_delta_fresh_evidence(
            self, sealed_engine):
        monkeypatch, tmp_path, calls = sealed_engine
        out = tmp_path / "run"
        manifest = _run_engine(out)

        # GEN 1 CHALLENGE: the known structural challenge hit — the
        # synthesis transport failed and the honest status says so
        final = json.loads((out / "final_state.json").read_text())
        pre = manifest
        assert "SYNTHESIZE" in (final.get("failed_stages") or {})
        assert final.get("final_status") in (
            "INVENTION_UNDER_DEVELOPMENT", "EVOLVED_INVENTION_CANDIDATE")

        # the INVENTION_LINEAGE exists (the product contract: at least
        # one architecture, always)
        lineage = json.loads((out / "INVENTION_LINEAGE.json").read_text())
        assert lineage["n_generations"] >= 2
        gens = lineage["generations"]

        # GEN 1: the mandatory fallback architecture (Phase C), born
        # from the synthesis failure, honestly labeled
        g1 = gens[0]
        assert g1["origin"] == "BASELINE_FALLBACK_GENERATION"
        assert g1["maturity"] == ev.MATURITY_GENERATED
        assert g1["generated_by"]["provenance"] == "AI_PROPOSED"
        assert g1["gen"] == 1 and g1["parent_id"] is None

        # DIAGNOSIS: the typed honest cause of GEN-1's death
        d = g1.get("diagnosis") or (gens[1].get("causal_delta") or {})
        assert (g1.get("diagnosis") or {}).get("cause") in (
            ev.CAUSE_MECHANISM_GENERATION_FAILURE,
            ev.CAUSE_ADVERSARIAL_KILL,
            ev.CAUSE_PHYSICS_BOUND_VIOLATION)

        # GEN 2: a brand-new invention identity with the FULL causal
        # delta (Phase D) and the 30-year engine (Phase E)
        g2 = gens[1]
        assert g2["origin"] == "EVOLUTION_CAUSAL_DELTA"
        assert g2["gen"] == 2
        assert g2["parent_id"] == g1["invention_id"]
        assert g2["invention_id"] != g1["invention_id"]
        assert g2["lineage"] == [g1["invention_id"], g2["invention_id"]]
        cd = g2["causal_delta"]
        assert cd["causal_change"], "Phase D: causal_change required"
        assert cd["new_capability"]
        assert cd["new_interaction"]
        assert cd["new_operating_regime"]
        assert cd["predicted_effect"]
        assert cd["frontier_capability"], \
            "Phase F: frontier transfer required"
        ty = cd["thirty_year_engine"]
        assert ty.get("current"), "Phase E: CURRENT step"
        assert ty.get("evolution_2055"), "Phase E: 2055 EVOLUTION step"
        assert ty.get("required_capability"), \
            "Phase E: REQUIRED CAPABILITY step"
        assert ty.get("capability_backcast"), \
            "Phase E: CAPABILITY BACKCAST step"
        assert ty.get("todays_frontier"), \
            "Phase E: TODAY'S FRONTIER step"
        assert ty.get("transfer"), "Phase E: TRANSFER step"
        assert g2["change_delta"] == cd["causal_change"]
        assert g2["reason_for_change"]

        # FRESH EVIDENCE: GEN 2 carries a NEW versioned snapshot
        fe = g2.get("fresh_evidence") or {}
        assert fe.get("snapshot_version") == 2
        assert fe.get("status") == "OK"
        assert fe.get("n_items", 0) >= 1

        # RE-EVALUATION: the gauntlet ran against GEN 2 through the
        # real engine instruments (spec persisted, challenge recorded)
        assert (out / "INVENTION_SPECIFICATION_gen-2.json").exists()
        ch2 = g2["challenge"]
        assert "killed" in ch2
        assert "survived" in ch2 or "kill_stage" in ch2

        # the stop reason is one of the honest terminators
        assert lineage["stop_reason"] in (
            "SURVIVOR_REACHED", "BUDGET_EXHAUSTED",
            "INFORMATION_GAIN_ZERO", "TRANSPORT_BLOCKED")

        # the run's final_state carries the evolution outcome honestly
        assert final.get("evolution", {}).get("n_generations") >= 2

    def test_information_gain_stop_when_cause_repeats(self,
                                                      sealed_engine):
        monkeypatch, tmp_path, calls = sealed_engine
        # make every architecture DIE at the same gauntlet stage: the
        # per-generation diagnosis repeats -> the loop stops honestly
        # instead of burning the budget (the stop rule)
        from discovery_fabric.engine import engineering_attack as ea

        def always_kill(spec, eng, env=None):
            return {"overall": "KILLED", "counts": {"KILL": 1,
                                                    "REPAIR": 0},
                    "items": [{"target": "mechanism_feasibility",
                               "verdict": "KILL",
                               "basis": "sealed: repeatable challenge",
                               "affected_claim_ids": ["mechanism"],
                               "repair_hint": ""}]}

        monkeypatch.setattr(ea, "attack_engineering", always_kill)
        monkeypatch.setenv("ENGINE_EVOLUTION_MAX_GENERATIONS", "5")
        out = tmp_path / "run_ig"
        _run_engine(out)
        lineage = json.loads((out / "INVENTION_LINEAGE.json").read_text())
        # the first evolution step runs; the SECOND consecutive same
        # cause stops the loop before the full budget
        assert lineage["n_generations"] <= 3
        assert lineage["stop_reason"] in ("INFORMATION_GAIN_ZERO",
                                          "BUDGET_EXHAUSTED")
        if lineage["stop_reason"] == "INFORMATION_GAIN_ZERO":
            last = lineage["generations"][-1]
            assert last.get("stop_note"), \
                "the honest stop note must be present"

    def test_no_banned_sentences_in_any_projection(self,
                                                   sealed_engine):
        monkeypatch, tmp_path, calls = sealed_engine
        out = tmp_path / "run_words"
        _run_engine(out)
        session = {"session_id": "s", "status": "COMPLETE",
                   "final_status": "INVENTION_UNDER_DEVELOPMENT",
                   "run_dir": str(out), "package": {}}
        v = us.public_session_view(session)
        blob = json.dumps(v).lower()
        for b in BANNED_STRINGS:
            assert b not in blob, b
        state = rs.canonical_run_state(session)
        blob2 = json.dumps(state).lower()
        for b in BANNED_STRINGS:
            assert b not in blob2, b

    def test_evolution_disabled_is_recorded_not_silent(self,
                                                       monkeypatch,
                                                       tmp_path):
        monkeypatch.setenv("ENGINE_EVOLUTION", "0")
        from discovery_fabric.engine import llm_registry as reg
        monkeypatch.setattr(
            reg, "generate",
            lambda *a, **k: _ScriptedCallResult(
                {"status": "CALL_FAILED", "error": "fixture"}))
        from discovery_fabric.a2 import retrieve as a2retrieve
        monkeypatch.setattr(a2retrieve, "retrieve",
                            lambda problem: list(FIXTURE_EVIDENCE))
        monkeypatch.setattr(
            "discovery_fabric.engine.cad_pipeline.geometry_warrants_3d",
            lambda spec: {"warranted": False, "reasons": ["fixture"]})
        out = tmp_path / "run_off"
        _run_engine(out)
        lineage = json.loads((out / "INVENTION_LINEAGE.json").read_text())
        assert lineage.get("status") == "DISABLED_BY_OPERATOR"
        assert "ENGINE_EVOLUTION=0" in lineage.get("reason", "")

    def test_resume_does_not_rerun_a_completed_lineage(self,
                                                       sealed_engine):
        monkeypatch, tmp_path, calls = sealed_engine
        out = tmp_path / "run_resume"
        _run_engine(out)
        lineage_path = out / "INVENTION_LINEAGE.json"
        before = lineage_path.read_text()
        # a second run() on the same dir must NOT re-run evolution
        _run_engine(out)
        after = lineage_path.read_text()
        data = json.loads(after)
        assert data.get("resumed") is True
        assert json.loads(before)["stop_reason"] == data["stop_reason"]


# ---------------------------------------------------------------------------
# 4. The honest final-status fix (the R416 root cause)
# ---------------------------------------------------------------------------

class TestHonestFinalStatus:
    def test_synthesis_failure_is_typed_not_rejected(self,
                                                     monkeypatch,
                                                     tmp_path):
        from discovery_fabric.engine import llm_registry as reg
        monkeypatch.setattr(
            reg, "generate",
            lambda *a, **k: _ScriptedCallResult(
                {"status": "CALL_FAILED", "error": "fixture: down"}))
        from discovery_fabric.a2 import retrieve as a2retrieve
        monkeypatch.setattr(a2retrieve, "retrieve",
                            lambda problem: list(FIXTURE_EVIDENCE))
        monkeypatch.setattr(
            "discovery_fabric.engine.cad_pipeline.geometry_warrants_3d",
            lambda spec: {"warranted": False, "reasons": ["fixture"]})
        out = tmp_path / "run_honest"
        manifest = _run_engine(out)
        final = json.loads((out / "final_state.json").read_text())
        # the root-cause fix: NOT "REJECTED" — the mechanism generation
        # failed before any candidate existed (Art. LXI)
        assert final["final_status"] != "REJECTED"
        # the reason NEVER blames an adversarial chain that never ran
        blob = final["reason"].lower()
        assert "adversarial" not in blob or "no adversarial" in blob
        # this test stubs ALL transport calls dead, so the honest
        # terminal is the transport-class record (Art. LXI)
        assert final["final_status"] in (
            "MECHANISM_GENERATION_FAILED",)
        # with ALL transport dead the honest record is the typed
        # FALLBACK_GENERATION_FAILED (0 architectures — infrastructure,
        # never a verdict); with any live transport the mandatory
        # invention is produced (covered by the sealed fixture tests)
        if (out / "INVENTION_LINEAGE.json").exists():
            lineage = json.loads(
                (out / "INVENTION_LINEAGE.json").read_text())
            assert lineage.get("status") in (
                "FALLBACK_GENERATION_FAILED", None)
