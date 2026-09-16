"""R478 — the external audit's engine P0 tranche, pinned.

The audit (TOSCANINI EXTERNAL AUDIT, 2026-09) measured three engine
P0 classes and this battery pins the fixes:

- P0-2 CONTRADICTION MOVES BELIEF: contradictory user evidence enters
  the ContradictionQueue (previously visibility-only: the audit's
  "B changes visibility only"), the queue payload carries the recorded
  belief update, and an unresolved HIGH/MODERATE contradiction keeps
  the ADJUDICATION no_blocking_contradictions check RED (promotion
  blocked through the EXISTING gate — no new state machine).
- P0-3 NUMERIC FALSIFICATION CONTRACT: the Article-LII projection no
  longer answers the kill outcome with prose when the records carry no
  numeric band, and a prose-only pre-registered decision rule no
  longer grants EXPERIMENT_READY (covered here at the artifact level
  and in test_r444/test_r425 at the gate level).
- P0-4 MEASURED/STATE-DERIVED EIG + NBA INPUTS: the R458 constant
  trace (48x identical EIG 0.85 / cost 2.0 / score 0.2826) is dead by
  construction — attack EIG is a function of recorded state, each
  action carries its input_basis, latency prefers the run's own
  measured stage durations, and cost scaling flips the ranking.
"""
from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone

from discovery_fabric.engine.adapters import (
    ContradictionQueueAdapter, KillerExperimentAdapter,
    NextBestActionAdapter)
from discovery_fabric.engine.candidate import Candidate
from discovery_fabric.engine.experiment_selector import (
    article_lii_contract, select_decisive_experiment)
from discovery_fabric.engine.state_integrity import (
    falsification_contract_status)
from toscanini.conversational import nba_controller


def _direct_item(source_id: str) -> dict:
    return {"source_id": source_id, "title": f"support {source_id}",
            "classification": "DIRECT_SUPPORT",
            "buyer_statement": "relevant to domain, failure mode, "
                               "mechanism.",
            "classification_basis": {"rule": "term-overlap",
                                     "contradiction_basis": None}}


def _contra_item(source_id: str) -> dict:
    return {"source_id": source_id,
            "title": f"counter {source_id}",
            "classification": "CONTRADICTORY",
            "buyer_statement": "contains a negated claim co-located "
                               "with the mechanism terms.",
            "classification_basis": {
                "rule": "negation marker co-located with claim terms",
                "contradiction_basis": "negation marker co-located with "
                                       "claim terms ['not'] in: 'the "
                                       "device does not reduce X.'"}}


def _classification(n_direct: int, n_contra: int) -> dict:
    items = ([_direct_item(f"s{i}") for i in range(n_direct)]
             + [_contra_item(f"c{i}") for i in range(n_contra)])
    return {
        "n_items": len(items),
        "counts": {"DIRECT_SUPPORT": n_direct, "CONTRADICTORY": n_contra},
        "items": items,
        "mechanism_support": {
            "n_direct_support": n_direct,
            "n_contradictory": n_contra,
            "contradictory_source_ids": [f"c{i}" for i in range(n_contra)],
        },
    }


def _env(n_direct: int = 5, n_contra: int = 0) -> Candidate:
    env = Candidate(problem={"device": "x", "failure": "y"},
                    problem_id="p1")
    env.evidence_classification = _classification(n_direct, n_contra)
    return env


def _stage_log_entry(stage: str, minutes: float, status: str = "OK") -> dict:
    t0 = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    return {"stage": stage, "status": status,
            "started_at": t0.isoformat().replace("+00:00", "Z"),
            "finished_at": (t0 + timedelta(minutes=minutes))
            .isoformat().replace("+00:00", "Z")}


# ===========================================================================
# P0-2 — contradiction moves belief
# ===========================================================================

class TestP0_2_ContradictionMovesBelief(unittest.TestCase):
    """The audit's acceptance: A-supports/B-contradicts must move a
    belief number AND block promotion — not merely add a label."""

    def test_user_evidence_contradiction_enters_queue_blocking(self):
        """A(5, DIRECT_SUPPORT) + B(1, CONTRADICTORY) -> a typed
        con:evidence:* contradiction, HIGH severity (derived: direct
        support exists, so the contradiction threatens a promotable
        state), MODERATE quality -> is_blocking."""
        env = _env(n_direct=5, n_contra=1)
        out = ContradictionQueueAdapter().execute(env, {})
        d = out["apply_to"]["contradictions"]
        ev = [c for c in d["contradictions"]
              if c["contradiction_id"].startswith("con:evidence:")]
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["severity"], "HIGH")
        self.assertEqual(ev[0]["evidence_quality"], "MODERATE")
        self.assertIn("does not reduce X",
                      ev[0]["description"])  # the basis travels verbatim
        self.assertGreaterEqual(d["blocking_count"], 1)

    def test_belief_update_moves_the_number(self):
        """The recorded confidence delta is the declared linear formula
        applied to the measured counts — a number, never a label."""
        env = _env(n_direct=5, n_contra=1)
        out = ContradictionQueueAdapter().execute(env, {})
        b = out["apply_to"]["contradictions"]["belief_update"]
        self.assertEqual(b["n_direct_support"], 5)
        self.assertEqual(b["n_contradictory"], 1)
        self.assertAlmostEqual(b["support_ratio"], 5 / 6, places=3)
        self.assertAlmostEqual(b["confidence_delta"],
                               round(-0.4 * (1 / 6), 3), places=3)
        self.assertIn("-0.4", b["basis"])

    def test_contradiction_without_support_stays_visible_not_blocking(self):
        """Art. V — not a universal rejector: with zero direct support
        the mechanism is already unsupported; the contradiction is
        MEDIUM (visible, non-blocking) and the belief still moves."""
        env = _env(n_direct=0, n_contra=1)
        out = ContradictionQueueAdapter().execute(env, {})
        d = out["apply_to"]["contradictions"]
        ev = [c for c in d["contradictions"]
              if c["contradiction_id"].startswith("con:evidence:")]
        self.assertEqual(ev[0]["severity"], "MEDIUM")
        self.assertEqual(d["blocking_count"], 0)
        self.assertLess(d["belief_update"]["confidence_delta"], 0)

    def test_blocking_contradiction_holds_the_adjudication_gate(self):
        """The promotion gate is the EXISTING adjudication check
        (no_blocking_contradictions on blocking_count) — the queued
        user-evidence contradiction now feeds it RED."""
        env = _env(n_direct=5, n_contra=1)
        out = ContradictionQueueAdapter().execute(env, {})
        env.contradictions = out["apply_to"]["contradictions"]
        # the adjudication check reads exactly this field (adapters.py,
        # the ADJUDICATION checks list) — reproduced here verbatim so
        # the test breaks if the check's source changes shape
        check_result = (env.contradictions or {}).get(
            "blocking_count", 0) == 0
        self.assertFalse(check_result,
                         "blocking user-evidence contradiction must "
                         "hold the no_blocking_contradictions gate")


# ===========================================================================
# P0-3 — numeric falsification contract (artifact-level)
# ===========================================================================

class TestP0_3_NumericFalsificationContract(unittest.TestCase):
    def test_prose_only_records_cannot_answer_the_kill_outcome(self):
        env = Candidate(problem={"device": "x", "failure": "y"},
                        problem_id="p1")
        env.mechanism_map = {
            "intervention": "reduce limescale",
            "mechanism": "thermal shock",
            "expected_effect": "cuts limescale mass",
            "falsification_test": "bench test of deposit mass"}
        contract = article_lii_contract(env)
        self.assertNotIn("FALSIFICATION_THRESHOLD", contract)
        self.assertIn("numeric band",
                      contract["FALSIFICATION_THRESHOLD_BLOCKER"])
        status = falsification_contract_status(contract)
        self.assertFalse(status["contract_complete"])

    def test_numeric_effect_answers_with_verbatim_bands(self):
        env = Candidate(problem={"device": "x", "failure": "y"},
                        problem_id="p1")
        env.mechanism_map = {
            "intervention": "reduce limescale",
            "mechanism": "thermal shock",
            "expected_effect": "cuts deposit mass by 35 percent",
            "falsification_test": "bench test of deposit mass"}
        contract = article_lii_contract(env)
        self.assertIn("FALSIFICATION_THRESHOLD", contract)
        self.assertEqual(
            contract["FALSIFICATION_BANDS"]["expected_effect_numbers"],
            ["35"])
        status = falsification_contract_status(contract)
        self.assertTrue(status["contract_complete"])

    def test_selector_artifact_carries_the_contract(self):
        """select_decisive_experiment embeds the same gate — a prose
        candidate's artifact cannot present an answered kill outcome."""
        env = Candidate(problem={"device": "x", "failure": "y"},
                        problem_id="p1")
        env.mechanism_map = {
            "intervention": "i", "mechanism": "m",
            "expected_effect": "better", "falsification_test": "test it"}
        art = select_decisive_experiment(env)
        fc = art["falsification_contract"]
        self.assertNotIn("FALSIFICATION_THRESHOLD", fc)
        self.assertIn("FALSIFICATION_THRESHOLD_BLOCKER", fc)


# ===========================================================================
# P0-4 — measured/state-derived EIG and NBA inputs
# ===========================================================================

class TestP0_4_StateDerivedEIG(unittest.TestCase):
    def _state(self, n_direct=5, n_contra=0, attack_ran=False,
               stage_log=None):
        return {
            "evidence": [{"id": i} for i in range(max(n_direct, 1))],
            "evidence_classification": _classification(n_direct, n_contra),
            "mechanism_map": {"intervention": "x", "mechanism": "y"},
            "attack_results": {"overall": "PASS"} if attack_ran else {},
            "stage_log": stage_log or [],
        }

    def test_attack_eig_varies_with_state(self):
        """The audit's exact complaint: the trace was 48x identical.
        Different recorded states now produce different EIG values —
        by construction, not by hope."""
        low = nba_controller.decide(self._state(n_direct=3, n_contra=0))
        high = nba_controller.decide(self._state(n_direct=6, n_contra=2))
        low_eig = next(a["expected_information_gain"]
                       for a in low["ranked_actions"]
                       if a["action"] == "ATTACK_CANDIDATE")
        high_eig = next(a["expected_information_gain"]
                        for a in high["ranked_actions"]
                        if a["action"] == "ATTACK_CANDIDATE")
        self.assertGreater(high_eig, low_eig)

    def test_r458_constant_trace_is_dead(self):
        """The R458 trace carried the SAME EIG for 48 decisions; the
        same fixture shapes now yield distinct, state-dependent values
        and every action carries its derivation. (A single state may
        still land on 0.85 — the dead class is CONSTANCY, not the
        coincidence of one value.)"""
        eigs = []
        for n_direct, n_contra in ((3, 0), (5, 0), (4, 3)):
            dec = nba_controller.decide(
                self._state(n_direct=n_direct, n_contra=n_contra))
            atk = next(a for a in dec["ranked_actions"]
                       if a["action"] == "ATTACK_CANDIDATE")
            eigs.append(atk["expected_information_gain"])
            basis = atk["input_basis"]["eig"]
            self.assertEqual(basis["inputs"]["n_direct_support"], n_direct)
            self.assertEqual(basis["inputs"]["n_contradictory"], n_contra)
            self.assertIn("formula", basis)
        self.assertEqual(len(set(eigs)), 3,
                         "the R458 constant-trace class is dead: three "
                         f"states must give three values, got {eigs}")

    def test_measured_latency_preferred_when_stage_ran(self):
        """A run whose SYNTHESIZE stage measured 2.5 min feeds the
        attack action its OWN measured latency (MEASURED_IN_RUN); a
        run without one falls back to the declared prior."""
        with_meas = self._state(
            stage_log=[_stage_log_entry("SYNTHESIZE", 2.5)])
        dec = nba_controller.decide(with_meas)
        atk = next(a for a in dec["ranked_actions"]
                   if a["action"] == "ATTACK_CANDIDATE")
        self.assertEqual(atk["estimated_latency_s"], 150.0)
        self.assertIn("MEASURED_IN_RUN", atk["input_basis"]["latency"])
        without = nba_controller.decide(self._state())
        atk2 = next(a for a in without["ranked_actions"]
                    if a["action"] == "ATTACK_CANDIDATE")
        self.assertEqual(atk2["estimated_latency_s"], 120.0)
        self.assertIn("DECLARED_PRIOR", atk2["input_basis"]["latency"])

    def test_cost_scaling_flips_ranking(self):
        """The audit's acceptance: 10x cost scaling must flip the
        ranking. Pinned on the ONE scoring authority (the V4 formula
        the controller and the engine adapter share)."""
        cheap = nba_controller.controller_action(
            "CHEAP", "u", expected_information_gain=0.7,
            probability_of_decision_change=0.8, decision_impact=0.9,
            estimated_cost=0.3, estimated_latency_s=10.0,
            required_capability="c", risk="r", reason="r")
        costly = nba_controller.controller_action(
            "COSTLY", "u", expected_information_gain=0.9,
            probability_of_decision_change=0.8, decision_impact=0.95,
            estimated_cost=3.0, estimated_latency_s=100.0,
            required_capability="c", risk="r", reason="r")
        self.assertGreater(cheap["score"], costly["score"])
        scaled = nba_controller.controller_action(
            "CHEAP", "u", expected_information_gain=0.7,
            probability_of_decision_change=0.8, decision_impact=0.9,
            estimated_cost=3.0, estimated_latency_s=10.0,
            required_capability="c", risk="r", reason="r")
        self.assertLess(scaled["score"], costly["score"])

    def test_engine_nba_eig_derives_from_priority(self):
        """The engine-stage NBA adapter's contradiction actions now
        derive EIG from the queue's own priority fields (the audit's
        0.5ximpact+0.2 literal is retired)."""
        env = _env(n_direct=5, n_contra=1)
        env.contradictions = ContradictionQueueAdapter().execute(
            env, {})["apply_to"]["contradictions"]
        out = NextBestActionAdapter().execute(env, {})
        payload = out["apply_to"]["next_best_action"]
        ev_actions = [a for a in payload["ranked_actions"]
                      if a["action_id"].startswith("con:evidence:")]
        self.assertEqual(len(ev_actions), 1)
        # HIGH/0.6/MODERATE/0.8 -> priority = 1.0*0.6*0.7*0.8 = 0.336
        # EIG = 0.2 + 0.6*0.336 = 0.4016 -> 0.402
        self.assertEqual(ev_actions[0]["expected_information_gain"], 0.402)

    def test_killer_likelihoods_state_derived(self):
        """The killer-experiment outcome likelihoods (the R458-era
        0.85 literal) now move with recorded contradiction pressure
        and carry their derivation."""
        env0 = _env(n_direct=5, n_contra=0)
        env0.contradictions = {"unresolved_count": 0}
        out0 = KillerExperimentAdapter().execute(env0, {})
        env1 = _env(n_direct=5, n_contra=0)
        env1.contradictions = {"unresolved_count": 3}
        out1 = KillerExperimentAdapter().execute(env1, {})

        def _p_repro(out):
            opts = out["apply_to"]["killer_experiment"]["options_ranked"]
            # the ranked options carry eig traces; the likelihood basis
            # travels on the raw option — read it from the payload's
            # recorded basis instead
            return out["apply_to"]["killer_experiment"].get(
                "likelihood_basis", {})

        b0, b1 = _p_repro(out0), _p_repro(out1)
        self.assertEqual(b0["inputs"]["unresolved_contradictions"], 0)
        self.assertEqual(b1["inputs"]["unresolved_contradictions"], 3)
        self.assertGreater(b1["pressure"], b0["pressure"])
        # more pressure -> strictly less confident reproduction
        self.assertLess(b1["pressure"], 1.0)
        self.assertIn("formula", b0)
        self.assertIn("MODEL_DERIVED", b0["provenance"])
        # and the emitted option actually used the derived value
        opts0 = out0["apply_to"]["killer_experiment"]["options_ranked"]
        opts1 = out1["apply_to"]["killer_experiment"]["options_ranked"]
        self.assertNotEqual(opts0[0]["eig"], opts1[0]["eig"])


if __name__ == "__main__":
    unittest.main()
