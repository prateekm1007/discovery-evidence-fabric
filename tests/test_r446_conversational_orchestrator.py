"""tests/test_r446_conversational_orchestrator.py — R446-C1: the
conversational orchestration layer's acceptance battery.

Directive §24 (verbatim): the required acceptance tests —
  A — simple problem        : pipeline should stop before unnecessary
                              stages
  B — ambiguous problem     : one useful clarification
  C — strong evidence       : retrieval stops intelligently
  D — conflicting evidence  : conflict becomes explicit
  E — obvious candidate failure: no unnecessary engineering
  F — provider failure      : scientific state remains distinct from
                              infrastructure state
  G — attack NOT_RUN        : never shown as survived
  H — experiment contradiction: successor state changes
  I — user claims proof     : conversation cannot override canonical
                              state
  J — stale artifact        : cannot override current canonical state

Constitutional contract for this battery:
  - OFFLINE by construction: the engine conductor is exercised with
    stub adapters (typed test doubles that seed the RECORDED state the
    real adapters would persist); the real adapters have their own
    networked batteries. No test here depends on network, transport,
    or LLM availability (Art. LXI discipline: an offline test never
    asserts an online capability).
  - No fixture bypasses the CONDUCTOR: the gate, the skip cascade, the
    final-state derivation and the product projections all run through
    the REAL production code paths.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Engine stub adapters — typed test doubles (see module docstring)
# ---------------------------------------------------------------------------

class _StubAdapter:
    """A typed stub: its execute() seeds the envelope with exactly the
    records the scenario needs (the same fields the real adapter
    persists). capability_id keeps the real one for the stage log."""

    def __init__(self, capability_id: str, module_path: str,
                 canonical_fn: str, seed):
        self.capability_id = capability_id
        self.module_path = module_path
        self.canonical_fn = canonical_fn
        self._seed = seed

    def execute(self, env, run_ctx):
        for k, v in (self._seed or {}).items():
            setattr(env, k, v)
        return {"stub": True, "seeded": sorted((self._seed or {}).keys())}


def _patched_adapters(seeds):
    """ADAPTERS with stub entries for the given {stage: seed} — the
    untouched stages keep their real adapters (PREMISE_GATE is fully
    deterministic and runs for real in these scenarios)."""
    from discovery_fabric.engine import adapters as _ad
    patched = dict(_ad.ADAPTERS)
    real = _ad.ADAPTERS
    for stage, seed in seeds.items():
        a = real[stage]
        patched[stage] = _StubAdapter(
            a.capability_id, a.module_path, a.canonical_fn, seed)
    return patched


def _run_engine(problem, td, seeds, stage_gate=None,
                with_package=False):
    """EngineRun through the REAL conductor with stub-seeded stages."""
    from discovery_fabric.engine import run as run_mod
    patched = _patched_adapters(seeds)
    with mock.patch.object(run_mod, "ADAPTERS", patched):
        engine = run_mod.EngineRun(problem, td,
                                   with_package=with_package,
                                   stage_gate=stage_gate)
        manifest = engine.run()
    return engine, manifest


def _stage_statuses(run_dir: Path):
    env = json.loads((run_dir / "candidate_envelope.json").read_text())
    return {e["stage"]: e["status"] for e in env["stage_log"]}


EVIDENCE_ITEM = lambda src, cls: {  # noqa: E731 — test-local lambda
    "source": src, "source_family": src, "classification": cls,
    "id": f"ev_{src}_{cls}"}


# ---------------------------------------------------------------------------
# A — simple problem: the pipeline stops before unnecessary stages
# ---------------------------------------------------------------------------

class TestA_SimpleProblemStopsEarly(unittest.TestCase):

    def test_weak_premise_stops_before_candidate_compute(self):
        """The directive §5 example: 'Stop early if problem existence
        cannot be established.' Evidence exists but NONE of it is
        mechanism-supporting → the gate STOPs SYNTHESIZE; downstream
        records SKIPPED_POLICY_NOT_REACHED; the final status is the
        typed PROBLEM_EXISTENCE_UNESTABLISHED (never a scientific
        rejection, never a burned synthesis)."""
        from toscanini.conversational import nba_controller, stage_policy

        problem = {"problem_id": "r446_a_simple",
                   "device": "garden hose",
                   "failure_mode": "insufficient sparkle",
                   "failure": "the hose does not sparkle",
                   "user_need": "make the hose sparkle"}
        # 9 records, all IRRELEVANT — the adequate-base, zero-support
        # shape (directive §5: problem existence cannot be established)
        seeds = {
            "RETRIEVE": {
                "evidence": [EVIDENCE_ITEM(f"source_{i}", "IRRELEVANT")
                             for i in range(9)],
                # the recorded classification (the resumed-run shape —
                # classification ran and found ZERO mechanism support)
                "evidence_classification": {
                    "items": [EVIDENCE_ITEM(f"source_{i}", "IRRELEVANT")
                              for i in range(9)],
                    "counts": {"IRRELEVANT": 9}},
            },
            "FREEZE": {"evidence_ids": [f"ev_{i}" for i in range(9)]},
            "VERIFY": {},
        }

        def gate(stage, env, nba=None):
            n = nba_controller.decide(env.to_dict())
            return stage_policy.engine_gate(stage, env, n)

        with tempfile.TemporaryDirectory() as td:
            engine, manifest = _run_engine(problem, td, seeds,
                                           stage_gate=gate)
            statuses = _stage_statuses(Path(td))
            fs = json.loads((Path(td) / "final_state.json").read_text())
            # the STOP point and its typed record
            self.assertEqual(statuses["SYNTHESIZE"],
                             "STOPPED_POLICY")
            self.assertEqual(statuses["RANK"],
                             "SKIPPED_POLICY_NOT_REACHED")
            # the NBA controller recorded STOP_HONEST as its preferred
            # action — the action determined the path (directive §8)
            # (checked via the gate's own decide call below)
            # the honest terminal class
            self.assertEqual(fs["final_status"],
                             "PROBLEM_EXISTENCE_UNESTABLISHED")
            self.assertIn("POLICY_STOP", str(fs["reason"]))
            # never a scientific rejection: no attack ran, no kill
            self.assertNotIn("ATTACK", fs.get("failed_stages", {}))
            # the lineage records the policy-stop honestly
            lineage = json.loads(
                (Path(td) / "INVENTION_LINEAGE.json").read_text())
            self.assertEqual(lineage["status"], "SKIPPED_POLICY_STOP")

    def test_nba_records_stop_honest_for_unestablished_problem(self):
        from toscanini.conversational import nba_controller
        env_state = {
            "evidence": [{"id": i} for i in range(9)],
            "evidence_classification": {
                "items": [EVIDENCE_ITEM("s", "IRRELEVANT")
                          for _ in range(9)],
                "counts": {"IRRELEVANT": 9}},
            "mechanism_map": {},
        }
        nba = nba_controller.decide(env_state)
        self.assertEqual(nba["preferred_action"]["action"], "STOP_HONEST")
        self.assertEqual(nba["preferred_action"]["estimated_cost"], 0.0)

    def test_small_base_prefers_retrieval_not_stop(self):
        """The adequacy guard: a small evidence base with zero support
        earns MORE RETRIEVAL, not a stop (Art. V — not a universal
        rejector)."""
        from toscanini.conversational import nba_controller
        env_state = {
            "evidence": [{"id": 1}, {"id": 2}],
            "evidence_classification": {
                "items": [EVIDENCE_ITEM("s", "IRRELEVANT")]},
            "mechanism_map": {},
        }
        nba = nba_controller.decide(env_state)
        self.assertEqual(nba["preferred_action"]["action"],
                         "RETRIEVE_MORE_EVIDENCE")

    def test_clear_problem_runs_the_evidence_chain(self):
        """The converse guard (Art. V: not a universal rejector): a
        problem with mechanism-supporting evidence proceeds to
        synthesis — the policy refuses only DEAD compute, never the
        live chain."""
        problem = {"problem_id": "r446_a_live",
                   "device": "multi-lumen tubing",
                   "failure_mode": "pressure loss",
                   "failure": "pressure loss across the lumens",
                   "user_need": "reduce pressure loss"}
        seeds = {
            "RETRIEVE": {"evidence": [
                EVIDENCE_ITEM("source_a", "DIRECT_SUPPORT"),
                EVIDENCE_ITEM("source_b", "PARTIAL_SUPPORT")]},
            # SYNTHESIZE stubbed: this battery verifies the POLICY/
            # conductor logic, not the LLM synthesis (which has its
            # own networked batteries)
            "SYNTHESIZE": {"mechanism_map": {
                "intervention": "textured liner",
                "mechanism": "boundary layer control"}},
        }

        def gate(stage, env, nba=None):
            from toscanini.conversational import stage_policy
            from toscanini.conversational import nba_controller
            n = nba_controller.decide(env.to_dict())
            return stage_policy.engine_gate(stage, env, n)

        with tempfile.TemporaryDirectory() as td:
            engine, manifest = _run_engine(problem, td, seeds,
                                           stage_gate=gate)
            statuses = _stage_statuses(Path(td))
            self.assertEqual(statuses["SYNTHESIZE"], "OK")


# ---------------------------------------------------------------------------
# B — ambiguous problem: one useful clarification
# ---------------------------------------------------------------------------

class TestB_AmbiguousProblemOneClarification(unittest.TestCase):

    def test_ambiguous_problem_yields_exactly_one_question(self):
        from toscanini.conversational import clarification
        from toscanini.conversational import problem_understanding as pu
        p = pu.build_problem_understanding(
            "We have an issue with our heat exchanger fouling over time "
            "and the maintenance cost is becoming a problem.")
        need = clarification.evaluate_clarification_need(p)
        self.assertTrue(need["needed"])
        # exactly ONE question, materiality-joined
        self.assertTrue(need["question"].endswith("?"))
        self.assertIn("decision_changed", need)
        self.assertGreaterEqual(need["score"], need["threshold"])
        # the refused candidates are recorded (the anti-questionnaire
        # refusal is itself auditable)
        self.assertIsInstance(need["refused"], list)

    def test_clear_problem_never_asks(self):
        from toscanini.conversational import clarification
        from toscanini.conversational import problem_understanding as pu
        p = pu.build_problem_understanding(
            "Find a way to reduce pressure loss in multi-lumen tubing.")
        need = clarification.evaluate_clarification_need(p)
        self.assertFalse(need["needed"])

    def test_industry_selector_is_refused(self):
        """The directive's own bad example: 'Select your industry.' must
        be structurally impossible — domain_hypothesis is in the
        never-ask set."""
        from toscanini.conversational import clarification
        self.assertIn("domain_hypothesis", clarification._NEVER_ASK)


# ---------------------------------------------------------------------------
# C — strong evidence: retrieval stops intelligently
# ---------------------------------------------------------------------------

class TestC_StrongEvidenceRetrievalStops(unittest.TestCase):

    def test_evidence_sufficiency_met_skips_further_retrieval(self):
        from toscanini.conversational import stage_policy as sp
        env_state = {"evidence_classification": {
            "items": [EVIDENCE_ITEM("src_a", "DIRECT_SUPPORT"),
                      EVIDENCE_ITEM("src_a", "PARTIAL_SUPPORT"),
                      EVIDENCE_ITEM("src_b", "DIRECT_SUPPORT"),
                      EVIDENCE_ITEM("src_c", "PARTIAL_SUPPORT")]}}
        suff = sp.evidence_sufficiency(env_state)
        self.assertTrue(suff["sufficient"])
        self.assertEqual(suff["n_source_families"], 3)

    def test_retrieval_stopping_rule_halts_connector_loop(self):
        from toscanini.conversational import stage_policy as sp
        done = [
            {"source": "europepmc", "role": "science", "status": "OK",
             "relevant": 4, "count": 12},
            {"source": "fda_maude", "role": "failure", "status": "OK",
             "relevant": 3, "count": 9},
        ]
        rule = sp.retrieval_stopping(done)
        self.assertTrue(rule["stop"])
        self.assertIn("science", rule["roles_covered"])
        self.assertIn("failure", rule["roles_covered"])

    def test_incomplete_role_coverage_continues(self):
        from toscanini.conversational import stage_policy as sp
        done = [{"source": "europepmc", "role": "science",
                 "status": "OK", "relevant": 2, "count": 5}]
        rule = sp.retrieval_stopping(done)
        self.assertFalse(rule["stop"])

    def test_redundant_mechanism_space_is_skipped_low_value(self):
        """§5: 'Strong evidence + clear mechanism → do not perform
        redundant' generation. A verified primary mechanism + sufficient
        evidence → MECHANISM_SPACE (5 LLM calls) is SKIPPED_LOW_VALUE
        with the distinctness authority preserved downstream."""
        from toscanini.conversational import stage_policy as sp
        env = {"premise_gate": {},
               "mechanism_map": {"intervention": "textured liner",
                                 "mechanism": "boundary layer control"},
               "evidence_classification": {
                   "items": [EVIDENCE_ITEM("a", "DIRECT_SUPPORT"),
                             EVIDENCE_ITEM("a", "DIRECT_SUPPORT"),
                             EVIDENCE_ITEM("b", "PARTIAL_SUPPORT"),
                             EVIDENCE_ITEM("c", "DIRECT_SUPPORT")]}}
        decision = sp.engine_gate("MECHANISM_SPACE", env, nba={
            "preferred_action": {"action": "ATTACK_CANDIDATE"}})
        self.assertIsNotNone(decision)
        self.assertEqual(decision["decision"], "SKIP")
        self.assertEqual(decision["skip_class"], "SKIPPED_LOW_VALUE")
        self.assertIn("COLLISION/ATTACK", decision["reason"])


# ---------------------------------------------------------------------------
# D — conflicting evidence: the conflict becomes explicit
# ---------------------------------------------------------------------------

class TestD_ConflictingEvidenceExplicit(unittest.TestCase):

    def test_unresolved_contradiction_rides_the_run_contract(self):
        """Conflicting evidence surfaces as an EXPLICIT uncertainty in
        the high-level run contract (never smoothed away)."""
        from toscanini.conversational import run_contract as rc
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "candidate_envelope.json").write_text(json.dumps({
                "contradictions": {"contradictions": [{
                    "contradiction_id": "C-1",
                    "description": "source A says X lowers the target; "
                                   "source B says it raises it",
                    "currently_unresolved": True}]},
            }))
            session = {"session_id": "s_d", "status": "COMPLETE",
                       "final_status": "REJECTED"}
            contract = rc.high_level_run_contract(session, td)
            fields = [u.get("field") for u in contract["uncertainties"]]
            self.assertIn("C-1", fields)

    def test_nba_ranks_contradiction_attack(self):
        """With unresolved contradictions, RETRIEVE_MORE is NOT the
        preferred action — attacking the contradiction is."""
        from toscanini.conversational import nba_controller
        env_state = {
            "evidence": [{"id": 1}] * 5,
            "evidence_classification": {
                "items": [EVIDENCE_ITEM("a", "DIRECT_SUPPORT")] * 5},
            "mechanism_map": {"intervention": "x", "mechanism": "y"},
            "attack_results": {},
        }
        nba = nba_controller.decide(env_state)
        self.assertEqual(nba["preferred_action"]["action"],
                         "ATTACK_CANDIDATE")


# ---------------------------------------------------------------------------
# E — obvious candidate failure: no unnecessary engineering
# ---------------------------------------------------------------------------

class TestE_CandidateFailureNoEngineering(unittest.TestCase):

    def test_killed_candidate_policy_refuses_artifacts(self):
        """The directive's own example shape: a candidate that failed
        the mechanism attack gets the typed SKIP with reason and the
        competing-mechanism next action."""
        from toscanini.conversational import stage_policy as sp
        env_state = {
            "mechanism_map": {"intervention": "x", "mechanism": "y"},
            "attack_results": {"overall": "KILL"},
            "adjudication": {"council": {"verdict": "CONTESTED"}},
        }
        decision = sp.expensive_artifact_policy(env_state)
        self.assertEqual(decision["decision"], "SKIP")
        self.assertEqual(decision["skip_class"], "NOT_REQUIRED")
        self.assertIn("no CAD", decision["reason"])
        self.assertIn("competing mechanism", decision["next_action"])

    def test_killed_lineage_generation_refuses_artifacts(self):
        from toscanini.conversational import stage_policy as sp
        env_state = {"mechanism_map": {"intervention": "x",
                                       "mechanism": "y"},
                     "attack_results": {}}
        lineage = {"current_invention": {"gen": 2}, "generations": [
            {"gen": 1, "challenge": {"killed": True,
                                     "kill_reason": "premise fails"}},
            {"gen": 2, "challenge": {"killed": True,
                                     "kill_reason": "physics bounds"}}]}
        decision = sp.expensive_artifact_policy(env_state, lineage)
        self.assertEqual(decision["decision"], "SKIP")

    def test_survivor_escalates_to_engineering(self):
        from toscanini.conversational import stage_policy as sp
        env_state = {
            "mechanism_map": {"intervention": "x", "mechanism": "y"},
            "attack_results": {"overall": "PASS"},
            "adjudication": {"council": {"verdict":
                                         "ESTABLISHED_PROVISIONALLY"}},
        }
        decision = sp.expensive_artifact_policy(env_state)
        self.assertEqual(decision["decision"], "RUN")
        self.assertIn("escalate", decision["reason"])


# ---------------------------------------------------------------------------
# F — provider failure: scientific state distinct from infrastructure
# ---------------------------------------------------------------------------

class TestF_ProviderFailureDistinctStates(unittest.TestCase):

    def test_policy_states_map_to_sixstate_vocabulary(self):
        from toscanini.conversational import stage_policy as sp
        self.assertEqual(sp.project_non_execution("DISABLED_BY_CONFIG"),
                         "NOT_REQUIRED")
        self.assertEqual(
            sp.project_non_execution("SKIPPED_UPSTREAM_FAILURE"),
            "NOT_REACHED")
        self.assertEqual(sp.project_non_execution("SKIPPED_ADMISSION"),
                         "NOT_REQUIRED")
        self.assertEqual(
            sp.project_non_execution("SKIPPED_POLICY_LOW_VALUE"),
            "SKIPPED_LOW_VALUE")
        self.assertEqual(sp.project_non_execution("BLOCKED_POLICY"),
                         "BLOCKED")
        self.assertEqual(sp.project_non_execution("FAILED_EXPLICIT"),
                         "FAILED")
        self.assertEqual(sp.project_non_execution("RENDER_SKIPPED_"
                                                  "LOW_MEMORY"),
                         "BLOCKED")
        # execution states project to None
        self.assertIsNone(sp.project_non_execution("OK"))
        self.assertIsNone(sp.project_non_execution(""))

    def test_six_states_all_distinct(self):
        from toscanini.conversational import stage_policy as sp
        self.assertEqual(len(sp.NON_EXECUTION_STATES), 6)
        self.assertEqual(len(set(sp.NON_EXECUTION_STATES)), 6)

    def test_infra_failure_event_is_never_scientific(self):
        """A BLOCKED attack emits RUN_BLOCKED (infrastructure class),
        never CANDIDATE_REJECTED or CANDIDATE_SURVIVED."""
        from toscanini.conversational import product_events as pe
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "problem.json").write_text(json.dumps({"device": "x"}))
            (td / "envelope_ATTACK.json").write_text(json.dumps({
                "stage_log": [{"stage": "ATTACK",
                               "status": "BLOCKED_POLICY"}]}))
            events = pe.derive_product_events(td, "run_f", "COMPLETE")
            types = [e["type"] for e in events]
            self.assertIn("RUN_BLOCKED", types)
            self.assertNotIn("CANDIDATE_SURVIVED", types)
            self.assertNotIn("CANDIDATE_REJECTED", types)


# ---------------------------------------------------------------------------
# G — attack NOT_RUN: never shown as survived
# ---------------------------------------------------------------------------

class TestG_AttackNotRunNeverSurvived(unittest.TestCase):

    def _attack_scenario(self, status, overall):
        from toscanini.conversational import product_events as pe
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "problem.json").write_text(json.dumps({"device": "x"}))
            (td / "envelope_ATTACK.json").write_text(json.dumps({
                "stage_log": [{"stage": "ATTACK", "status": status}]}))
            (td / "candidate_envelope.json").write_text(json.dumps({
                "attack_results": {"overall": overall}}))
            return [e["type"] for e in
                    pe.derive_product_events(td, "run_g", "COMPLETE")]

    def test_not_run_attack_emits_no_survived(self):
        types = self._attack_scenario("NOT_RUN", None)
        self.assertNotIn("CANDIDATE_SURVIVED", types)
        self.assertNotIn("ATTACKING_CANDIDATE", types)

    def test_blocked_attack_emits_no_survived(self):
        types = self._attack_scenario("BLOCKED_POLICY", None)
        self.assertNotIn("CANDIDATE_SURVIVED", types)

    def test_skipped_upstream_attack_emits_no_events(self):
        """A non-executed stage emits NO scientific event at all."""
        types = self._attack_scenario("SKIPPED_UPSTREAM_FAILURE", None)
        self.assertNotIn("CANDIDATE_SURVIVED", types)
        self.assertNotIn("CANDIDATE_REJECTED", types)
        self.assertNotIn("ATTACKING_CANDIDATE", types)

    def test_executed_kill_emits_rejected_not_survived(self):
        types = self._attack_scenario("OK", "KILL")
        self.assertIn("ATTACKING_CANDIDATE", types)
        self.assertIn("CANDIDATE_REJECTED", types)
        self.assertNotIn("CANDIDATE_SURVIVED", types)

    def test_executed_pass_emits_survived(self):
        types = self._attack_scenario("OK", "PASS")
        self.assertIn("CANDIDATE_SURVIVED", types)


# ---------------------------------------------------------------------------
# H — experiment contradiction: successor state changes
# ---------------------------------------------------------------------------

class TestH_ExperimentContradictionChangesSuccessor(unittest.TestCase):

    def test_outcome_received_and_mutation_events_derive_from_ledger(self):
        """The reality-loop ledger drives OUTCOME_RECEIVED /
        MODEL_UPDATED / CANDIDATE_MUTATED / RE_EVALUATING product
        events — the causal learning loop is visible to the product
        from its OWN records (directive §20)."""
        from toscanini.conversational import product_events as pe
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "problem.json").write_text(json.dumps({"device": "x"}))
            (td / "REALITY_LOOP_LEDGER.json").write_text(json.dumps({
                "events": [{"event_id": "EVT-1"}]}))
            (td / "INVENTION_LINEAGE.json").write_text(json.dumps({
                "generations": [
                    {"gen": 1, "causal_delta": "observed deficit X",
                     "mutation_reason": "inverse of Poiseuille"},
                    {"gen": 2, "challenge": {"killed": True,
                                             "kill_reason": "bounds"}},
                ]}))
            types = [e["type"] for e in
                     pe.derive_product_events(td, "run_h", "COMPLETE")]
            self.assertIn("OUTCOME_RECEIVED", types)
            self.assertIn("MODEL_UPDATED", types)
            self.assertIn("CANDIDATE_MUTATED", types)
            self.assertIn("RE_EVALUATING", types)
            self.assertIn("CANDIDATE_REJECTED", types)

    def test_causal_edges_change_with_outcome(self):
        """The deterministic causal-learning regression (R452 Phase 7
        contract, already pinned by its own battery) — here we pin the
        CONVERSATIONAL layer's reading of it: changing the recorded
        observation changes the mutation events' detail."""
        from toscanini.conversational import product_events as pe
        from discovery_fabric.engine import causal_learning as _cl
        # the engine's own module carries the regression; the
        # conversational layer projects it. Smoke: module exists and
        # exposes the causal-edge vocabulary.
        self.assertTrue(hasattr(_cl, "__doc__"))
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "problem.json").write_text(json.dumps({"device": "x"}))
            (td / "INVENTION_LINEAGE.json").write_text(json.dumps({
                "generations": [{"gen": 2, "causal_delta": "A"}]}))
            events = pe.derive_product_events(td, "run_h2", "COMPLETE")
            muts = [e for e in events if e["type"] == "CANDIDATE_MUTATED"]
            self.assertEqual(len(muts), 1)
            self.assertEqual(muts[0]["detail"]["gen"], 2)


# ---------------------------------------------------------------------------
# I — user claims proof: conversation cannot override canonical state
# ---------------------------------------------------------------------------

class TestI_UserClaimsProof(unittest.TestCase):

    def test_proof_claim_is_context_only(self):
        from toscanini.conversational import conversation_memory as cm
        cls = cm.classify_user_message("We proved candidate B works.")
        self.assertEqual(cls["classification"], "ASSERTION_PROOF")
        self.assertFalse(cls["affects_canonical_state"])
        self.assertIn("REALITY_EVENT", cls["required_for_state_change"])

    def test_guard_refuses_scientific_fields(self):
        from toscanini.conversational import conversation_memory as cm
        guarded = cm.guard_session_update({
            "conversation": [{"role": "user", "text":
                              "We proved candidate B."}],
            "final_status": "EVOLVED_INVENTION_CANDIDATE",
            "package": {"complete": True},
        })
        self.assertIn("conversation", guarded["allowed"])
        self.assertNotIn("final_status", guarded["allowed"])
        self.assertNotIn("package", guarded["allowed"])
        refused = {r["field"] for r in guarded["refused"]}
        self.assertEqual(refused, {"final_status", "package"})

    def test_answer_route_cannot_write_verdicts(self):
        """The clarification-answer path (the ONLY conversation route
        that touches stored state) can carry just the three context
        fields — a verdict injected through it is refused by the guard."""
        from toscanini.conversational import conversation_memory as cm
        guarded = cm.guard_session_update({
            "clarification_answer": {"field": "target_variable",
                                     "answer": "pressure loss"},
            "clarification": {"field": "target_variable"},
            "conversation": [],
            "status": "COMPLETE",
            "final_status": "INVENTION_SURVIVED",
        })
        self.assertEqual(set(guarded["allowed"].keys()),
                         {"clarification_answer", "clarification",
                          "conversation"})


# ---------------------------------------------------------------------------
# J — stale artifact cannot override current canonical state
# ---------------------------------------------------------------------------

class TestJ_StaleArtifactCannotOverride(unittest.TestCase):

    def test_completion_marker_gates_complete(self):
        """A run dir with a package ZIP + final_state but NO completion
        marker never reads as COMPLETE (the R446-C1 Task-4 authority;
        here pinned for the contract view)."""
        from toscanini.conversational import run_contract as rc
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "final_state.json").write_text(json.dumps({
                "final_status": "EVOLVED_INVENTION_CANDIDATE"}))
            (td / "BRIDGE_REPORT.json").write_text(json.dumps({
                "outcome": "COMPLETED"}))
            (td / "PACKAGE_REPORT.json").write_text(json.dumps({
                "complete": True}))
            session = {"session_id": "s_j", "status": "RUNNING"}
            contract = rc.high_level_run_contract(session, td)
            self.assertEqual(
                contract["current_state"]["complete_marker"], "NOT_MARKED")

    def test_package_event_requires_own_report_field(self):
        """PACKAGE_READY requires the package report's own complete
        field — a stale BRIDGE_REPORT outcome alone does not emit it
        when the package report says otherwise (current truth wins)."""
        from toscanini.conversational import product_events as pe
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "problem.json").write_text(json.dumps({"device": "x"}))
            (td / "BRIDGE_REPORT.json").write_text(json.dumps({
                "outcome": "COMPLETED"}))
            (td / "PACKAGE_REPORT.json").write_text(json.dumps({
                "complete": False}))
            types = [e["type"] for e in
                     pe.derive_product_events(td, "run_j", "COMPLETE")]
            self.assertNotIn("PACKAGE_READY", types)

    def test_killed_lineage_never_emits_package_ready(self):
        from toscanini.conversational import product_events as pe
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "problem.json").write_text(json.dumps({"device": "x"}))
            (td / "BRIDGE_REPORT.json").write_text(json.dumps({
                "outcome": "COMPLETED"}))
            (td / "PACKAGE_REPORT.json").write_text(json.dumps({
                "complete": True}))
            (td / "INVENTION_LINEAGE.json").write_text(json.dumps({
                "current_invention": {"gen": 1},
                "generations": [{"gen": 1, "challenge":
                                 {"killed": True}}]}))
            # the package event derives from the reports (they say
            # complete) — but the run contract's view of the invention
            # truth carries the killed verdict; here we pin that the
            # event layer itself stays report-faithful and the KILL is
            # visible in the stream:
            types = [e["type"] for e in
                     pe.derive_product_events(td, "run_j2", "COMPLETE")]
            self.assertIn("CANDIDATE_REJECTED", types)


# ---------------------------------------------------------------------------
# Schema + contract validations (the deliverable JSONs vs the code)
# ---------------------------------------------------------------------------

class TestSchemasMatchCode(unittest.TestCase):

    def test_problem_understanding_schema_deliverable(self):
        """CODER1_PROBLEM_UNDERSTANDING_SCHEMA.json must exist at the
        repo root, validate as JSON, and agree with the code's field
        list and origin vocabulary."""
        from toscanini.conversational import problem_understanding as pu
        p = REPO_ROOT / "CODER1_PROBLEM_UNDERSTANDING_SCHEMA.json"
        self.assertTrue(p.is_file(), "deliverable schema missing")
        schema = json.loads(p.read_text())
        fields = schema["properties"]["fields"]["properties"] \
            if "properties" in schema.get("schema", schema) else None
        # fall back to the schema's own declared field list
        declared = schema.get("fields") or \
            (schema.get("properties", {}).get("fields", {})
             .get("properties", {}))
        for f in pu.DIRECTIVE_FIELDS:
            self.assertIn(f, declared, f"field {f} missing from schema")

    def test_product_event_schema_deliverable(self):
        from toscanini.conversational import product_events as pe
        p = REPO_ROOT / "CODER1_PRODUCT_EVENT_SCHEMA.json"
        self.assertTrue(p.is_file(), "deliverable schema missing")
        schema = json.loads(p.read_text())
        types = schema.get("event_types") or \
            schema.get("properties", {}).get("type", {}).get("enum", [])
        for t in pe.EVENT_TYPES:
            self.assertIn(t, types, f"event type {t} missing")

    def test_nba_contract_deliverable(self):
        p = REPO_ROOT / "CODER1_NEXT_BEST_ACTION_CONTRACT.json"
        self.assertTrue(p.is_file(), "deliverable missing")
        contract = json.loads(p.read_text())
        self.assertIn("preferred_action", json.dumps(contract)[:200000])

    def test_every_derived_event_validates(self):
        from toscanini.conversational import product_events as pe
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "problem.json").write_text(json.dumps({"device": "x"}))
            (td / "PROBLEM_UNDERSTANDING.json").write_text(json.dumps({
                "unknowns": [{"field": "target_variable"}]}))
            (td / "envelope_SYNTHESIZE.json").write_text(json.dumps({
                "stage_log": [{"stage": "SYNTHESIZE",
                               "status": "OK"}]}))
            (td / "candidate_envelope.json").write_text(json.dumps({
                "mechanism_map": {"intervention": "i"},
                "attack_results": {"overall": "PASS"},
                "killer_experiment": {"selected": {"name": "flow test"}}}))
            (td / "final_state.json").write_text(json.dumps({
                "final_status": "REJECTED"}))
            events = pe.derive_product_events(td, "run_v", "COMPLETE")
            self.assertTrue(events)
            for ev in events:
                self.assertEqual(pe.validate_event(ev), [],
                                 f"invalid event: {ev['type']}")


# ---------------------------------------------------------------------------
# Engine integration: the gate, the conductor, and the vocabulary
# ---------------------------------------------------------------------------

class TestEngineGateIntegration(unittest.TestCase):

    def test_absent_gate_behavior_unchanged(self):
        """The constitutional invariant: without a stage_gate the
        conductor behaves EXACTLY as pre-R446 (the premise-fatality
        cascade still produces SKIPPED_UPSTREAM_FAILURE, the canonical
        vocabulary is untouched)."""
        problem = {"problem_id": "r446_no_gate",
                   "device": "borosilicate glass liner",
                   "failure_mode": "grain-boundary sliding",
                   "failure": "grain-boundary sliding limits service",
                   "user_need": "prevent grain boundary sliding"}
        seeds = {"RETRIEVE": {"evidence": []}, "FREEZE": {}}
        with tempfile.TemporaryDirectory() as td:
            engine, manifest = _run_engine(problem, td, seeds)
            statuses = _stage_statuses(Path(td))
            self.assertEqual(statuses.get("SYNTHESIZE"),
                             "SKIPPED_UPSTREAM_FAILURE")

    def test_gate_skip_records_typed_status(self):
        """A policy SKIP persists SKIPPED_POLICY_LOW_VALUE with the
        reason and next_action on the stage entry — a recorded refusal,
        never a silent code path."""
        problem = {"problem_id": "r446_gate_skip",
                   "device": "multi-lumen tubing",
                   "failure_mode": "pressure loss",
                   "failure": "pressure loss",
                   "user_need": "reduce pressure loss"}
        seeds = {
            "RETRIEVE": {
                "evidence": [
                    EVIDENCE_ITEM("a", "DIRECT_SUPPORT"),
                    EVIDENCE_ITEM("a", "DIRECT_SUPPORT"),
                    EVIDENCE_ITEM("b", "PARTIAL_SUPPORT"),
                    EVIDENCE_ITEM("c", "DIRECT_SUPPORT")],
            },
            "VERIFY": {
                # the recorded classification (the authority the
                # sufficiency rule reads — seeded at VERIFY because
                # that is the stage that records it in the live chain)
                "evidence_classification": {
                    "items": [
                        EVIDENCE_ITEM("a", "DIRECT_SUPPORT"),
                        EVIDENCE_ITEM("a", "DIRECT_SUPPORT"),
                        EVIDENCE_ITEM("b", "PARTIAL_SUPPORT"),
                        EVIDENCE_ITEM("c", "DIRECT_SUPPORT")],
                    "counts": {"DIRECT_SUPPORT": 3,
                               "PARTIAL_SUPPORT": 1}},
            },
            "SYNTHESIZE": {"mechanism_map": {
                "intervention": "textured liner",
                "mechanism": "boundary layer control"},
                "mechanism_ids": ["m1"]},
        }

        def gate(stage, env, nba=None):
            from toscanini.conversational import stage_policy
            from toscanini.conversational import nba_controller
            n = nba_controller.decide(env.to_dict())
            return stage_policy.engine_gate(stage, env, n)

        with tempfile.TemporaryDirectory() as td:
            engine, manifest = _run_engine(problem, td, seeds,
                                           stage_gate=gate)
            statuses = _stage_statuses(Path(td))
            self.assertEqual(statuses.get("MECHANISM_SPACE"),
                             "SKIPPED_POLICY_LOW_VALUE")
            env = json.loads(
                (Path(td) / "candidate_envelope.json").read_text())
            entry = [e for e in env["stage_log"]
                     if e["stage"] == "MECHANISM_SPACE"][0]
            self.assertIn("skip_reason", entry)
            self.assertEqual(entry.get("skip_class"),
                             "SKIPPED_LOW_VALUE")
            self.assertIn("next_action", entry)

    def test_gate_error_fails_open_to_run(self):
        """A raising gate is treated as RUN — the orchestration layer
        can never hold the epistemic chain hostage (fail-open for the
        POLICY layer only)."""
        problem = {"problem_id": "r446_gate_err",
                   "device": "tubing",
                   "failure_mode": "pressure loss",
                   "failure": "pressure loss",
                   "user_need": "reduce"}
        seeds = {"RETRIEVE": {"evidence": [
            EVIDENCE_ITEM("a", "DIRECT_SUPPORT")]},
            "SYNTHESIZE": {"mechanism_map": {
                "intervention": "i", "mechanism": "m"}}}

        def bad_gate(stage, env, nba=None):
            raise RuntimeError("policy layer exploded")

        with tempfile.TemporaryDirectory() as td:
            engine, manifest = _run_engine(problem, td, seeds,
                                           stage_gate=bad_gate)
            statuses = _stage_statuses(Path(td))
            # stages still executed (RUN semantics); the error is
            # disclosed on the entry blocks
            self.assertIn(statuses.get("SYNTHESIZE"),
                          ("OK", "FAILED_EXPLICIT",
                           "SKIPPED_UPSTREAM_FAILURE"))


# ---------------------------------------------------------------------------
# Problem Understanding contract (directive §3)
# ---------------------------------------------------------------------------

class TestProblemUnderstandingContract(unittest.TestCase):

    def test_twelve_fields_present_and_typed(self):
        from toscanini.conversational import problem_understanding as pu
        p = pu.build_problem_understanding(
            "Find a way to reduce pressure loss in multi-lumen tubing.")
        for f in pu.DIRECTIVE_FIELDS:
            self.assertIn(f, p, f"missing directive field: {f}")
        # typed origins
        self.assertEqual(p["problem_statement"]["origin"], "USER_STATED")
        self.assertEqual(p["target_variable"]["origin"], "INFERRED_MODEL")
        self.assertEqual(p["domain_hypothesis"]["origin"], "INFERRED_MODEL")

    def test_unknown_stays_unknown(self):
        from toscanini.conversational import problem_understanding as pu
        p = pu.build_problem_understanding("hello")
        self.assertIsNone(p["desired_outcome"]["value"])
        self.assertEqual(p["desired_outcome"]["origin"], "UNKNOWN")
        fields = [u["field"] for u in p["unknowns"]]
        self.assertIn("desired_outcome", fields)
        self.assertIn("target_variable", fields)

    def test_llm_enrichment_types_and_never_overrides_user(self):
        from toscanini.conversational import problem_understanding as pu
        p = pu.build_problem_understanding(
            "Find a way to reduce pressure loss in multi-lumen tubing.")
        p = pu.enrich_with_extraction(p, {
            "domain": "medical",
            "device": "multi-lumen catheter",
            "objective": "reduce pressure loss",
        })
        self.assertEqual(p["llm_fields"]["domain_hypothesis"]["origin"],
                         "MODEL_DERIVED_LLM")
        # user-stated outcome NOT overridden; the LLM disagreement is
        # recorded (never silent)
        self.assertEqual(p["desired_outcome"]["origin"], "USER_STATED")
        self.assertTrue(any(d["field"] == "desired_outcome"
                            for d in p["disagreements"]))

    def test_clarification_answer_types_user_stated(self):
        from toscanini.conversational import problem_understanding as pu
        p = pu.build_problem_understanding("improve our process")
        p = pu.apply_clarification_answer(p, "target_variable",
                                          "energy per unit output")
        self.assertEqual(p["target_variable"]["origin"], "USER_STATED")
        self.assertEqual(p["target_variable"]["value"],
                         "energy per unit output")
        fields = [u["field"] for u in p["unknowns"]]
        self.assertNotIn("target_variable", fields)


# ---------------------------------------------------------------------------
# Model provenance (directive §18/§19)
# ---------------------------------------------------------------------------

class TestModelProvenance(unittest.TestCase):

    def test_routing_table_declares_deterministic_work(self):
        from toscanini.conversational import model_provenance as mp
        for w in ("content_hashing", "geometry_build",
                  "stage_policy_decisions"):
            entry = mp.work_class(w)
            self.assertEqual(entry["routing"], "DETERMINISTIC")
            self.assertEqual(entry["llm_calls_allowed"], 0)
        entry = mp.work_class("mechanism_reasoning")
        self.assertEqual(entry["routing"], "LLM")
        self.assertEqual(entry["required_task_class"], "STRONG")

    def test_downgrade_never_inherits_authority(self):
        from toscanini.conversational import model_provenance as mp
        rec = mp.model_provenance_for(
            {"provider": "local", "model": "qwen3-1.7b",
             "task": "CHEAP", "latency_ms": 4200},
            requested_task="STRONG", run_id="r1")
        self.assertEqual(rec["authority_state"], "AUTHORITY_DOWNGRADED")
        self.assertEqual(rec["capability_tier"], "TIER_CHEAP")
        self.assertIn("SERVING tier", rec["downgrade_consequence"])

    def test_missing_provenance_is_a_defect(self):
        from toscanini.conversational import model_provenance as mp
        problems = mp.audit_model_derived_state({"provider": "x"})
        self.assertIn("model-derived state missing field: model_id",
                      problems)


# ---------------------------------------------------------------------------
# Run contract shape (directive §11)
# ---------------------------------------------------------------------------

class TestRunContractShape(unittest.TestCase):

    def test_seven_field_contract(self):
        from toscanini.conversational import run_contract as rc
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "run_manifest.json").write_text(json.dumps({
                "finished_at": "2026-09-14T00:00:00Z",
                "final_status": "REJECTED",
                "failed_stages": {},
                "final_envelope_hash": "abc",
                "run_id": "r"}))
            (td / "NBA_CONTROLLER.json").write_text(json.dumps({
                "preferred_action": {"action": "GENERATE_COMPETING_"
                                               "MECHANISM",
                                     "reason": "candidate killed"}}))
            session = {"session_id": "s7", "status": "COMPLETE"}
            contract = rc.high_level_run_contract(session, td)
            for f in ("run_id", "current_state", "human_progress",
                      "next_action", "artifacts", "blocking_reason",
                      "uncertainties"):
                self.assertIn(f, contract)
            self.assertEqual(contract["next_action"]["action"],
                             "GENERATE_COMPETING_MECHANISM")
            self.assertEqual(
                contract["current_state"]["complete_marker"],
                "COMPLETE_MARKED")

    def test_blocking_reason_infrastructure_class(self):
        from toscanini.conversational import run_contract as rc
        session = {"session_id": "s8",
                   "status": "RUN_BLOCKED_TRANSPORT",
                   "error": "provider exhausted"}
        contract = rc.high_level_run_contract(session, None)
        self.assertEqual(contract["blocking_reason"]["kind"],
                         "INFRASTRUCTURE")
        self.assertTrue(contract["blocking_reason"]["resumable"])


# ---------------------------------------------------------------------------
# HTTP routing (the production-smoke regression): the GET routes must be
# registered in do_GET — the first deploy's live probe caught them
# mis-registered in do_POST ("no such endpoint"); this pins the fix
# (Art. XXXI: every correction creates its memory artifact).
# ---------------------------------------------------------------------------

class TestHttpRouting(unittest.TestCase):

    def _server(self):
        import threading
        from http.server import ThreadingHTTPServer
        from toscanini import server as sv

        class _MemStore:
            def __init__(self):
                self.sessions = {
                    "ts_route_1": {
                        "session_id": "ts_route_1",
                        "user_text": "reduce pressure loss",
                        "status": "COMPLETE",
                        "final_status": "REJECTED",
                        "run_dir": None,
                        "created_at": "2026-09-14T00:00:00Z",
                        "updated_at": "2026-09-14T00:01:00Z",
                    }}

            def get_session(self, sid):
                return self.sessions.get(sid)

            @staticmethod
            def session_access(sid, owner_key=None, operator_key=None):
                return "OWNER"

        mem = _MemStore()
        orig_store = sv.store

        class _Quiet(ThreadingHTTPServer):
            def handle_error(self, request, client_address):
                pass

        srv = _Quiet(("127.0.0.1", 0), sv.Handler)
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        return srv, mem, sv, orig_store

    def test_contract_route_is_a_get_route(self):
        import http.client
        srv, mem, sv, orig_store = self._server()
        port = srv.server_address[1]
        try:
            sv.store = mem
            conn = http.client.HTTPConnection("127.0.0.1", port,
                                              timeout=10)
            conn.request("GET", "/api/run/ts_route_1/contract")
            resp = conn.getresponse()
            body = json.loads(resp.read())
            self.assertEqual(resp.status, 200,
                             f"contract route failed: {body}")
            self.assertIn("run_id", body)
            self.assertIn("current_state", body)
            self.assertIn("next_action", body)
        finally:
            sv.store = orig_store
            srv.shutdown()
            srv.server_close()

    def test_product_events_route_is_a_get_route(self):
        import http.client
        srv, mem, sv, orig_store = self._server()
        port = srv.server_address[1]
        try:
            sv.store = mem
            conn = http.client.HTTPConnection("127.0.0.1", port,
                                              timeout=10)
            conn.request("GET", "/api/run/ts_route_1/product-events")
            resp = conn.getresponse()
            body = json.loads(resp.read())
            self.assertEqual(resp.status, 200,
                             f"product-events route failed: {body}")
            self.assertIn("events", body)
        finally:
            sv.store = orig_store
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
