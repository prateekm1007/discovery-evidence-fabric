"""tests/test_r491_ring_pinned_calibration.py — R491: the ring-pinned
calibration measurement infrastructure + the ring-bound kill authority
+ the A2 consumption gate (the R490 owner ruling's destination).

Pinned behaviors:
  1. llm_generate(hard_pin_provider=...): ONE provider, ZERO fallback
     (SelectionPolicy max_preference_fallback=0); an unregistered or
     credentialed-out pin fails closed (never a silent ring change);
     the pin travels in the meta (Art. IV)
  2. independent_attack(require_provider=...): the ring_pin block on
     every attack record (pinned and cascade modes); a pin violation
     (pinned ring not served) is recorded loudly
  3. The calibration transport validates require_provider against the
     registry's provider ids (typed 400 UNKNOWN_RING_PIN)
  4. resolve_state surfaces the measurement's attacker_ring; a legacy
     record without one reports ring_binding ABSENT_LEGACY_RECORD
  5. gate_attack_record: a CALIBRATED state's terminal authority is
     RING-BOUND — same ring passes through; a different provider or
     model escalates with a typed ring_mismatch (objections preserved
     verbatim); a legacy calibrated record without a ring keeps the
     pre-R491 semantics (unenforceable, recorded)
  6. The A2 gauntlet's Article L consumption gate in classify(): while
     the gauntlet is uncalibrated its KILL escalates (objections ride
     the promotion record verbatim); the deterministic gates (prior-art
     kill states, the falsification contract) keep full authority; a
     calibrated gauntlet state restores the pre-R491 kill semantics

The R488 measured basis throughout: attacker calibration is
(rules x ring) — the same v3 rules measured FPR 0.25 on the strong
ring's frozen outputs and 1.0 live on the free-tier ring the
availability cascade fell to under load.

reviewer_provenance=AI_REVIEW
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import attacker_calibration as gate  # noqa: E402
from discovery_fabric.engine import independent_attack as ia  # noqa: E402
from discovery_fabric.engine import mechanism_space as ms  # noqa: E402
from discovery_fabric.a2 import adversarial as a2  # noqa: E402


def _fake_result(provider="atria", model="Atria-Dawn-Preview",
                 ok=True, status="OK", content=""):
    """An LLMCallResult-shaped stand-in with the fields llm_generate
    and independent_attack read."""
    class _R:
        pass
    r = _R()
    r.ok = ok
    r.status = status
    r.content = content
    r.provider_id = provider if ok else None
    r.model = model if ok else None
    r.prompt_hash = "ph" * 8
    r.output_hash = "oh" * 8
    r.error = None if ok else "pinned provider failed"
    r.call_provenance = {}
    r.task_degradation = {}
    r.cost_provenance = {}
    r.route = None
    r.failure_type = None
    r.substituted_from = None
    r.retry_notes = None
    r.selection_ledger = {}
    return r


class TestHardPinProvider(unittest.TestCase):
    def _matrix(self):
        return [
            {"provider_id": "atria", "available": True},
            {"provider_id": "xkiro", "available": True},
            {"provider_id": "hf", "available": False},
        ]

    def test_pin_builds_zero_fallback_policy(self):
        import discovery_fabric.engine.llm_registry as reg
        captured = {}

        def fake_generate(prompt, system="", timeout=240, max_retries=2,
                          policy=None, max_tokens=700,
                          max_provider_fallbacks=2):
            captured["policy"] = policy
            captured["fallbacks"] = max_provider_fallbacks
            return _fake_result()

        with mock.patch.object(reg, "generate", fake_generate), \
             mock.patch.object(reg, "availability_matrix",
                               self._matrix):
            meta = ms.llm_generate("p", purpose="independent_attack",
                                   hard_pin_provider="atria")
        self.assertEqual(captured["policy"].preferred_providers,
                         ["atria"])
        self.assertEqual(captured["policy"].max_preference_fallback, 0)
        self.assertEqual(captured["fallbacks"], 0)
        self.assertEqual(meta["hard_pin"]["requested"], "atria")
        self.assertEqual(meta["hard_pin"]["status"],
                         "HARD_PINNED_NO_FALLBACK")
        self.assertEqual(meta["provider"], "atria")

    def test_unknown_provider_id_fails_closed(self):
        import discovery_fabric.engine.llm_registry as reg

        def fake_generate(*a, **k):
            return _fake_result()

        with mock.patch.object(reg, "generate", fake_generate), \
             mock.patch.object(reg, "availability_matrix",
                               self._matrix):
            meta = ms.llm_generate("p", purpose="independent_attack",
                                   hard_pin_provider="no-such-provider")
        self.assertFalse(meta["ok"])
        self.assertIn("unknown_provider_id",
                      meta["hard_pin"]["status"])

    def test_unavailable_provider_fails_closed(self):
        import discovery_fabric.engine.llm_registry as reg

        def fake_generate(*a, **k):
            return _fake_result(ok=False,
                                status="PROVIDER_UNAVAILABLE")

        with mock.patch.object(reg, "generate", fake_generate), \
             mock.patch.object(reg, "availability_matrix",
                               self._matrix):
            meta = ms.llm_generate("p", purpose="independent_attack",
                                   hard_pin_provider="hf")
        self.assertFalse(meta["ok"])
        self.assertIn("pinned_provider_unavailable",
                      meta["hard_pin"]["status"])

    def test_no_pin_is_cascade(self):
        import discovery_fabric.engine.llm_registry as reg

        def fake_generate(*a, **k):
            return _fake_result()

        with mock.patch.object(reg, "generate", fake_generate), \
             mock.patch.object(reg, "availability_matrix",
                               self._matrix), \
             mock.patch(
                 "discovery_fabric.engine.provider_health."
                 "order_for_role", lambda m, r, **k: [
                     x["provider_id"] for x in m]):
            meta = ms.llm_generate("p", purpose="independent_attack")
        self.assertTrue(meta["ok"])
        self.assertNotIn("hard_pin", meta)


CANDIDATE = {
    "candidate_id": "t-r491",
    "mechanism": "a staged wedge-wire cascade removes scale particles "
                 "above 120 microns and the dP-triggered backflush "
                 "restores full flow without mill stop",
    "intervention": "two-stage cascade on the 150 mm supply line",
    "predicted_effect": "campaign clogging events fall from 4.1 to "
                        "below 1.5",
    "testable_prediction": "coupon test shows the reduction over a "
                           "120-hour campaign",
    "novel_design_variable": "stage cut size",
    "known_failure_modes": ["fine passive slimes"],
    "constraint_set": {"boundary_conditions": "14 bar supply"},
}
PROBLEM = {"device": "supply-line filtration", "failure": "clogging"}


class TestRingPinOnRecord(unittest.TestCase):
    def _attack(self, require=None, serve="atria",
                model="Atria-Dawn-Preview"):
        def fake_llm(prompt, system="", timeout=240, max_tokens=700,
                     purpose="independent_attack",
                     exclude_providers=None, hard_pin_provider=None):
            return {
                "ok": True, "status": "OK", "content": (
                    "MECHANISM_FAILURE: SURVIVE — supported "
                    "GROUNDED_IN: none\n"),
                "provider": serve, "model": model,
                "prompt_hash": "ph", "output_hash": "oh", "error": None,
                "hard_pin": ({"requested": hard_pin_provider,
                              "status": "HARD_PINNED_NO_FALLBACK"}
                             if hard_pin_provider else None),
                "call_provenance": {}, "task_degradation": {},
                "cost_provenance": {}, "excluded_providers": [],
                "fallback_to_excluded": False,
            }
        with mock.patch.object(ms, "llm_generate", fake_llm):
            return ia.independent_attack(
                dict(CANDIDATE), dict(PROBLEM), [], None,
                require_provider=require)

    def test_pinned_ring_travels_on_record(self):
        rec = self._attack(require="atria")
        rp = rec["ring_pin"]
        self.assertEqual(rp["requested"], "atria")
        self.assertEqual(rp["mode"], "HARD_PIN_NO_FALLBACK")
        self.assertEqual(rp["served_provider"], "atria")
        self.assertNotIn("pin_violation", rp)

    def test_cascade_mode_travels_on_record(self):
        rec = self._attack()
        rp = rec["ring_pin"]
        self.assertIsNone(rp["requested"])
        self.assertEqual(rp["mode"], "PRODUCTION_CASCADE")

    def test_pin_violation_is_loud(self):
        rec = self._attack(require="atria", serve="xkiro",
                           model="qwen/qwen3.8-max:free")
        self.assertIn("pin_violation", rec["ring_pin"])


class TestTransportRingPinValidation(unittest.TestCase):
    def test_route_validates_require_provider(self):
        src = (REPO / "toscanini" / "server.py").read_text()
        start = src.index('if p.path == "/api/ops/calibration-attack":')
        route = src[start:start + 4000]
        self.assertIn('require_provider', route)
        self.assertIn("UNKNOWN_RING_PIN", route)
        self.assertIn("PROVIDER_SPECS", route)
        # the pin is passed into the instrument, never applied silently
        self.assertIn("require_provider=require_provider", route)


def _measurement_record(with_ring=True, calibrated=True):
    return {
        "artifact_type": "ATTACKER_V3_MEASUREMENT",
        "instrument": "independent_attack/3.0.0",
        "metrics": {
            "false_kill_rate_on_known_good": 0.25 if calibrated else 1.0,
            "coverage": 1.0, "parse_completeness": 1.0, "tnr": 0.75,
        },
        "scoped_tpr_diagnostic": {"tpr": 1.0,
                                  "cohort": "seeded defects"},
        "n_cases_attacked": 22,
        "threshold_verdict": {
            "calibrated": calibrated,
            "bars": {"tpr_min": 0.75, "fpr_max": 0.3,
                     "coverage_min": 0.875,
                     "parse_completeness_min": 0.875},
            "bars_met": {"tpr": True, "fpr": calibrated,
                         "coverage": True, "parse": True},
        },
        **({"attacker_ring": {
            "provider": "atria", "model": "Atria-Dawn-Preview",
            "serving": "22/22 cases on the pinned ring"}}
           if with_ring else {}),
    }


def _seal_record():
    return {"pre_registered_thresholds": {
        "tpr_min": 0.75, "fpr_max": 0.3, "coverage_min": 0.875,
        "parse_completeness_min": 0.875}}


class TestRingBoundAuthority(unittest.TestCase):
    def _state(self, with_ring=True, calibrated=True):
        with tempfile.TemporaryDirectory() as td:
            mp = Path(td) / "m.json"
            sp = Path(td) / "s.json"
            mp.write_text(json.dumps(
                _measurement_record(with_ring, calibrated)))
            sp.write_text(json.dumps(_seal_record()))
            return gate.resolve_state(measurement_path=mp,
                                      seal_path=sp,
                                      instrument_version=(
                                          "independent_attack/3.0.0"))

    def _kill_record(self, provider="atria",
                     model="Atria-Dawn-Preview"):
        return {
            "attack_version": "independent_attack/3.0.0",
            "overall": "KILLED",
            "attacker_provider": provider,
            "attacker_model": model,
            "kill_basis": [
                {"attack_class": "MECHANISM_FAILURE",
                 "basis": "the record cannot be true as stated",
                 "grounding": {}}],
            "items": [],
        }

    def test_measured_ring_surfaces_on_state(self):
        st = self._state()
        self.assertEqual(st["state"], "CALIBRATED")
        ring = st["measured"]["attacker_ring"]
        self.assertEqual(ring["provider"], "atria")
        self.assertEqual(st["ring_binding"],
                         "MEASURED_RING_REQUIRED_AT_CONSUMPTION")

    def test_legacy_record_reports_absent_binding(self):
        st = self._state(with_ring=False, calibrated=False)
        self.assertEqual(st["state"], "NOT_CALIBRATED")
        self.assertIsNone(st["measured"]["attacker_ring"])
        self.assertEqual(st["ring_binding"], "ABSENT_LEGACY_RECORD")

    def test_same_ring_kill_keeps_authority(self):
        st = self._state()
        out = gate.gate_attack_record(self._kill_record(), st)
        self.assertEqual(out["overall"], "KILLED")
        self.assertNotIn("escalation", out)

    def test_provider_mismatch_escalates(self):
        st = self._state()
        out = gate.gate_attack_record(
            self._kill_record(provider="xkiro",
                              model="qwen/qwen3.8-max:free"), st)
        self.assertEqual(out["overall"], "ESCALATED_OBJECTION")
        self.assertEqual(out["raw_overall"], "KILLED")
        mm = out["escalation"]["ring_mismatch"]
        self.assertEqual(mm["kind"], "RING_MISMATCH_PROVIDER")
        self.assertIn("xkiro", mm["reason"])
        # the objection is preserved verbatim
        self.assertEqual(out["preserved_objections"][0]["attack_class"],
                         "MECHANISM_FAILURE")

    def test_model_mismatch_escalates(self):
        st = self._state()
        out = gate.gate_attack_record(
            self._kill_record(provider="atria",
                              model="Atria-Dawn-Preview-v2"), st)
        self.assertEqual(out["overall"], "ESCALATED_OBJECTION")
        self.assertEqual(
            out["escalation"]["ring_mismatch"]["kind"],
            "RING_MISMATCH_MODEL")

    def test_legacy_calibrated_record_keeps_pre_r491_semantics(self):
        # a calibrated measurement with NO ring block: the ring check
        # is unenforceable — recorded, and the pre-R491 semantics hold
        st = self._state(with_ring=False, calibrated=True)
        self.assertEqual(st["state"], "CALIBRATED")
        out = gate.gate_attack_record(
            self._kill_record(provider="xkiro"), st)
        self.assertEqual(out["overall"], "KILLED")

    def test_not_calibrated_state_still_escalates(self):
        st = self._state(with_ring=True, calibrated=False)
        out = gate.gate_attack_record(self._kill_record(), st)
        self.assertEqual(out["overall"], "ESCALATED_OBJECTION")
        self.assertIn("escalation", out)

    def test_a2_registry_entry_fails_closed(self):
        st = gate.resolve_state(
            instrument_version="a2_adversarial_gauntlet/1.0.0")
        self.assertEqual(st["state"], "UNKNOWN_NOT_CALIBRATED")
        self.assertFalse(st["terminal_kill_admissible"])


KILLED_ADVERSARIAL = {
    "overall": "KILLED",
    "reason": "obvious combination of known techniques",
    "attacks": {
        "obvious_combination": "KILLED: obvious combination of a "
                               "cascade and a backflush",
        "engineering_infeasibility": "KILLED: unbounded stress",
    },
}


class TestA2ConsumptionGate(unittest.TestCase):
    def _classify(self, adversarial=None, candidate=None, pa=None,
                  verified=None):
        from discovery_fabric.a2.classify import classify
        return classify(
            candidate or {"falsification_test": "measure dP over 120h "
                                                "and compare against "
                                                "the 1.5-event bar"},
            verified or {"verified": True},
            pa or {"prior_art_status": "NO_MATCH_FOUND"},
            adversarial if adversarial is not None
            else json.loads(json.dumps(KILLED_ADVERSARIAL)))

    def test_uncalibrated_gauntlet_kill_escalates_not_rejects(self):
        res = self._classify()
        self.assertEqual(res["final_status"],
                         "AUTOMATED_INVENTION_CANDIDATE")
        esc = res["adversarial_escalation"]
        self.assertEqual(
            sorted(esc["escalated_objection"]
                   ["gauntlet_killed_dimensions"]),
            ["engineering_infeasibility", "obvious_combination"])
        # objections preserved VERBATIM
        self.assertIn("cascade and a backflush",
                      esc["escalated_objection"]
                      ["objections_verbatim"]["obvious_combination"])
        self.assertEqual(
            esc["gate"]["calibration_state"],
            "UNKNOWN_NOT_CALIBRATED")
        self.assertFalse(esc["gate"]["terminal_kill_admissible"])
        self.assertIn("ESCALATED", res["reason"])

    def test_deterministic_falsification_gate_keeps_authority(self):
        res = self._classify(
            candidate={"falsification_test": "short"})
        self.assertEqual(res["final_status"], "REJECTED")
        # the objections still ride the record
        self.assertIn("adversarial_escalation", res)

    def test_deterministic_prior_art_kill_unchanged(self):
        res = self._classify(
            pa={"prior_art_status": "SPECIFIC_DISCLOSURE"})
        self.assertEqual(res["final_status"], "REJECTED")
        self.assertIn("specific disclosure", res["reason"])

    def test_calibrated_gauntlet_restores_kill_semantics(self):
        fake_state = {
            "state": "CALIBRATED", "terminal_kill_admissible": True}
        with mock.patch.object(
                gate, "resolve_state", return_value=fake_state):
            res = self._classify()
        self.assertEqual(res["final_status"], "REJECTED")
        self.assertIn("adversarial challenge failed", res["reason"])
        self.assertNotIn("adversarial_escalation", res)

    def test_pass_path_has_no_escalation(self):
        res = self._classify(adversarial={"overall": "PASS",
                                          "attacks": {}})
        self.assertEqual(res["final_status"],
                         "AUTOMATED_INVENTION_CANDIDATE")
        self.assertNotIn("adversarial_escalation", res)

    def test_non_scientific_adversarial_still_unknown(self):
        res = self._classify(adversarial={
            "overall": "EVALUATOR_CALL_FAILED", "attacks": {}})
        self.assertEqual(res["final_status"], "UNKNOWN")
        self.assertTrue(res["adjudication_blocked"])

    def test_unknown_verdict_vocabulary_fails_closed(self):
        # R491: an overall outside PASS/KILLED and outside the named
        # non-scientific states is UNKNOWN — never a promotion, never
        # negative knowledge (Art. XXV)
        res = self._classify(adversarial={
            "overall": "SOMETHING_WEIRD", "attacks": {}})
        self.assertEqual(res["final_status"], "UNKNOWN")
        self.assertTrue(res["adjudication_blocked"])
        self.assertTrue(res["promotion_blocked"])


if __name__ == "__main__":
    unittest.main()
