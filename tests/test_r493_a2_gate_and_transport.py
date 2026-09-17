"""tests/test_r493_a2_gate_and_transport.py — R493: the A2 measurement
transport (/api/ops/a2-attack, R490 owned plan step 2) + the ring-pin
plumbing for the gauntlet + the union pins that bind the transport to
the R491 consumption gate (R490 owned plan step 5, already deployed by
the R491 union line).

Pinned behaviors:
  1. The A2 transport route: exists in do_POST, mirrors the R487/R491
     calibration-attack discipline (payload caps, typed failures, one
     attack per request, prior_art_state vocabulary gate, disclosed
     evidence_items input mapping, require_provider ring pin validated
     against the registered provider ids).
  2. The gauntlet's ring pin: adversarial_challenge/llm_chat accept
     require_provider; with a pin, the selection policy pins EXACTLY
     that provider with max_preference_fallback=0 (no cascade) and the
     ring_pin block travels on the transport meta (requested / mode /
     served / violation); WITHOUT a pin the policy is the production
     availability cascade (byte-identical behavior).
  3. Union gate pins (the R491 line's classify + registry, verified
     against the DEPLOYED dc90b510 design): the registry entry
     a2_adversarial_gauntlet/1.0.0 exists and resolves fail-closed
     (no shipped A2 measurement -> UNKNOWN_NOT_CALIBRATED, kills not
     admissible); an uncalibrated KILL never terminates REJECTED on
     the gauntlet alone — the classification continues through the
     deterministic gates with the escalation riding the record; the
     unknown verdict vocabulary fails closed to UNKNOWN.
  4. The registered-record path: with a temporarily-registered
     measurement + seal meeting the sealed bars, the gauntlet's KILL
     regains full terminal authority (the calibrated future takes
     exactly this path).

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

from discovery_fabric.a2 import adversarial as a2  # noqa: E402
from discovery_fabric.a2 import classify as a2classify  # noqa: E402
from discovery_fabric.engine import attacker_calibration as gate  # noqa: E402

A2_INSTRUMENT = "a2_adversarial_gauntlet/1.0.0"


def _full_candidate():
    return {
        "mechanism": "a staged hydrodynamic cascade conditions the "
                     "ballast stream",
        "intervention": "inline rotor-stator conditioner on the main",
        "predicted_effect": "3.5-log inactivation at rated flow",
        "testable_prediction": "bench loop shows the reduction over "
                               "three water qualities",
        "falsification_test": "bench loop at 5 m3/h with natural "
                              "seawater shows the log reduction or the "
                              "claim is dead",
    }


_VERIFICATION_OK = {"verified": True, "issues": []}
_PRIOR_ART_PASS = {"prior_art_status": "TOPICAL_RELATED"}


class TestA2TransportRoute(unittest.TestCase):
    @staticmethod
    def _route_source():
        src = (REPO / "toscanini" / "server.py").read_text()
        start = src.index('if p.path == "/api/ops/a2-attack":')
        return src[start:start + 5200]

    def test_route_exists_in_do_post(self):
        src = (REPO / "toscanini" / "server.py").read_text()
        self.assertIn('p.path == "/api/ops/a2-attack"', src)
        self.assertIn("adversarial_challenge as _a2_attack", src)

    def test_route_mirrors_the_calibration_transport_discipline(self):
        src = self._route_source()
        self.assertIn("413", src)                                  # caps typed
        self.assertIn("12_000", src)                               # candidate cap
        self.assertIn("INSTRUMENT_IMPORT_FAILURE", src)
        self.assertIn("INSTRUMENT_EXECUTION_FAILURE", src)
        self.assertIn("UNKNOWN_PRIOR_ART_STATE", src)              # vocabulary gate
        self.assertIn("evidence_items", src)                       # the disclosed input mapping
        self.assertIn("require_provider", src)                     # the R491 ring-pin discipline
        self.assertIn("UNKNOWN_RING_PIN", src)
        self.assertIn("_LAST_ATTACK_PROVIDER_META", src)           # transport provenance
        # one attack per request — no loop over cases in the route
        self.assertNotIn("for case in", src)


class TestGauntletRingPin(unittest.TestCase):
    def test_signatures_accept_the_pin(self):
        import inspect
        self.assertIn("require_provider",
                      inspect.signature(a2.adversarial_challenge).parameters)
        self.assertIn("require_provider",
                      inspect.signature(a2.llm_chat).parameters)

    def test_pinned_policy_pins_exactly_one_provider(self):
        """With require_provider, the selection policy is the pin and
        nothing else — max_preference_fallback=0 — AND the pin rides
        the registry's OWN hard_pin_provider mechanism (the only pin
        the deployed registry enforces; the R493 smoke case measured
        the preference-only pin falling through to another ring)."""
        captured = {}

        class _Res:
            ok = True
            content = "UNSUPPORTED_MECHANISM: PASS\nOVERALL: PASS"

            def to_meta(self):
                return {"ok": True, "provider": "atria",
                        "model": "m", "hard_pin": {"status": "OK"}}

        class _FakeReg:
            @staticmethod
            def generate(prompt, system="", timeout=0, max_retries=0,
                         policy=None, hard_pin_provider=None):
                captured["policy"] = policy
                captured["hard_pin_provider"] = hard_pin_provider
                return _Res()

        import discovery_fabric.engine.llm_registry as real_reg
        with mock.patch.object(real_reg, "generate", _FakeReg.generate):
            out = a2.llm_chat("p", require_provider="atria")
        self.assertTrue(out)
        pol = captured["policy"]
        self.assertEqual(pol.preferred_providers, ["atria"])
        self.assertEqual(pol.max_preference_fallback, 0)
        self.assertEqual(captured["hard_pin_provider"], "atria")
        meta = a2._LAST_ATTACK_PROVIDER_META
        self.assertEqual(meta["ring_pin"]["requested"], "atria")
        self.assertEqual(meta["ring_pin"]["mode"], "HARD_PIN_NO_FALLBACK")
        self.assertEqual(meta["ring_pin"]["served_provider"], "atria")
        self.assertIsNone(meta["ring_pin"]["pin_violation"])

    def test_no_pin_keeps_the_production_cascade(self):
        captured = {}

        class _Res:
            ok = True
            content = "OVERALL: PASS"

            def to_meta(self):
                return {"ok": True, "provider": "atria", "model": "m"}

        class _FakeReg:
            @staticmethod
            def generate(prompt, system="", timeout=0, max_retries=0,
                         policy=None, hard_pin_provider=None):
                captured["policy"] = policy
                captured["hard_pin_provider"] = hard_pin_provider
                return _Res()

        import discovery_fabric.engine.llm_registry as real_reg
        with mock.patch.object(real_reg, "generate", _FakeReg.generate):
            a2.llm_chat("p")
        pol = captured["policy"]
        self.assertIn("atria", pol.preferred_providers)
        self.assertGreater(len(pol.preferred_providers), 1)
        self.assertIsNone(captured["hard_pin_provider"])
        self.assertNotIn("ring_pin", a2._LAST_ATTACK_PROVIDER_META)

    def test_pin_violation_is_typed_not_silent(self):
        captured = {}

        class _Res:
            ok = True
            content = "OVERALL: PASS"

            def to_meta(self):
                return {"ok": True, "provider": "xkiro", "model": "m"}

        class _FakeReg:
            @staticmethod
            def generate(prompt, system="", timeout=0, max_retries=0,
                         policy=None, hard_pin_provider=None):
                captured["policy"] = policy
                captured["hard_pin_provider"] = hard_pin_provider
                return _Res()

        import discovery_fabric.engine.llm_registry as real_reg
        with mock.patch.object(real_reg, "generate", _FakeReg.generate):
            a2.llm_chat("p", require_provider="atria")
        meta = a2._LAST_ATTACK_PROVIDER_META
        self.assertIn("PINNED ring not served",
                      meta["ring_pin"]["pin_violation"])


class TestUnionGatePins(unittest.TestCase):
    """The R491 line's consumption gate + registry — pinned here
    against the DEPLOYED design so the transport round cannot drift
    from the consumption semantics it measures."""

    def test_registry_entry_exists_and_fails_closed(self):
        self.assertIn(A2_INSTRUMENT, gate.INSTRUMENT_MEASUREMENTS)
        st = gate.resolve_state(instrument_version=A2_INSTRUMENT)
        self.assertEqual(st["state"], "UNKNOWN_NOT_CALIBRATED")
        self.assertFalse(st["terminal_kill_admissible"])
        self.assertIn("Art. L", st["reason"])

    def test_uncalibrated_kill_escalates_never_rejects_on_the_gauntlet(self):
        adv = {"overall": "KILLED", "killed_count": 2,
               "reason": "mechanism unsupported by any evidence",
               "attacks": {"unsupported_mechanism": "KILLED",
                           "engineering_infeasibility": "KILLED"}}
        res = a2classify.classify(
            _full_candidate(), _VERIFICATION_OK, _PRIOR_ART_PASS, adv)
        # the gauntlet's kill alone does NOT terminate REJECTED
        self.assertNotEqual(res["final_status"], "REJECTED")
        # the objections ride the record verbatim (preserved, not lost)
        esc = res.get("adversarial_escalation") or {}
        obj = (esc.get("escalated_objection") or {})
        self.assertEqual(
            obj.get("objections_verbatim", {}).get("unsupported_mechanism"),
            "KILLED")
        self.assertEqual(esc["gate"]["instrument"], A2_INSTRUMENT)
        self.assertFalse(esc["gate"]["terminal_kill_admissible"])

    def test_unknown_verdict_vocabulary_fails_closed(self):
        adv = {"overall": "SOME_NOVEL_STATE", "attacks": {}}
        res = a2classify.classify(
            _full_candidate(), _VERIFICATION_OK, _PRIOR_ART_PASS, adv)
        self.assertEqual(res["final_status"], "UNKNOWN")
        self.assertTrue(res["adjudication_blocked"])

    def test_registered_calibration_restores_kill_authority(self):
        """The destination state machine end-to-end: committed records
        meeting the sealed bars -> CALIBRATED -> the gauntlet's KILL
        terminates REJECTED again. The exact path the A2 seal takes
        when (and only when) its own measurement earns it."""
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            meas = {
                # the ENGINE registry schema (resolve_state reads these
                # keys): metrics.{false_kill_rate_on_known_good,
                # coverage, parse_completeness} + scoped_tpr_diagnostic.
                # tpr — the A2 measurement record must ship in THIS
                # schema for the registry to derive its state.
                "metrics": {"false_kill_rate_on_known_good": 0.1,
                            "coverage": 1.0, "parse_completeness": 1.0},
                "scoped_tpr_diagnostic": {"tpr": 0.9},
                "threshold_verdict": {"calibrated": True},
                "n_cases": 21}
            seal = {"pre_registered_thresholds": {
                "tpr_min": 0.75, "fpr_max": 0.30,
                "coverage_min": 0.875,
                "parse_completeness_min": 0.875}}
            (td / "m.json").write_text(json.dumps(meas))
            (td / "s.json").write_text(json.dumps(seal))
            with mock.patch.dict(
                    gate.INSTRUMENT_MEASUREMENTS,
                    {A2_INSTRUMENT: {
                        "measurement": td / "m.json",
                        "seal": td / "s.json"}}):
                st = gate.resolve_state(instrument_version=A2_INSTRUMENT)
                self.assertEqual(st["state"], "CALIBRATED")
                self.assertTrue(st["terminal_kill_admissible"])
                adv = {"overall": "KILLED", "killed_count": 1,
                       "reason": "mechanism unsupported",
                       "attacks": {"unsupported_mechanism": "KILLED"}}
                res = a2classify.classify(
                    _full_candidate(), _VERIFICATION_OK,
                    _PRIOR_ART_PASS, adv)
        self.assertEqual(res["final_status"], "REJECTED")
        self.assertIn("adversarial challenge failed", res["reason"])


class TestMemoryClaimFloor(unittest.TestCase):
    """R493 v4.1: an obviousness kill must be PACKET-ANCHORED (an ev:
    citation or a verbatim echo of an evidence item) — literature /
    commercial-system memory is unverifiable by a no-retrieval
    instrument and can never execute as a kill (measured on
    a2dev-04/12/14; the engine v4's burden-of-proof direction,
    applied to the A2)."""

    @staticmethod
    def _parsed(attacks_text: str, candidate: dict):
        from unittest import mock as _m
        with _m.patch.object(a2, "llm_chat", return_value=attacks_text):
            return a2.adversarial_challenge(candidate, True,
                                            "TOPICAL_RELATED")

    def test_memory_cited_obviousness_kill_demotes(self):
        # the measured a2dev-12/14 shape: named literature/commercial
        # systems, none in the packet
        cand = _full_candidate()
        resp = ("UNSUPPORTED_MECHANISM: PASS\n"
                "WEAK_TRANSFER: PASS\n"
                "OBVIOUS_COMBINATION: KILLED - N2 sparging is a "
                "published technique (IMO GloBallast trials, the Dutch "
                "NoBallast work); combining it with a sensor array is "
                "the textbook configuration\n"
                "PRIOR_ART: PASS\n"
                "CONTRADICTION: PASS\n"
                "BOUNDARY_FAILURE: PASS\n"
                "ENGINEERING_INFEASIBILITY: PASS\n"
                "REGULATORY_INCOMPATIBILITY: PASS\n"
                "OVERALL: KILLED\n"
                "REASON: x")
        res = self._parsed(resp, cand)
        # R494 union: the demotion is the burden-of-proof RISK flag
        # (memory_claim); the 1.1.0 floor name rides as the alias
        self.assertIn("RISK (burden-of-proof: memory_claim)",
                      res["attacks"]["obvious_combination"])
        self.assertIn("a2_v4_floors:memory_claim",
                      res["v4_corrections_applied"])
        self.assertIn("N2 sparging is a published technique",
                      res["attacks"]["obvious_combination"])
        self.assertEqual(res["overall"], "PASS")

    def test_packet_cited_obviousness_kill_survives(self):
        cand = _full_candidate()
        cand["evidence_items"] = [{"id": "ev:prior",
                                   "title": "the Dutch NoBallast "
                                            "N2 stripping trials "
                                            "report"}]
        resp = ("UNSUPPORTED_MECHANISM: PASS\n"
                "WEAK_TRANSFER: PASS\n"
                "OBVIOUS_COMBINATION: KILLED - ev:n2-report reports the "
                "N2 stripping trials the candidate replicates\n"
                "PRIOR_ART: PASS\n"
                "CONTRADICTION: PASS\n"
                "BOUNDARY_FAILURE: PASS\n"
                "ENGINEERING_INFEASIBILITY: PASS\n"
                "REGULATORY_INCOMPATIBILITY: PASS\n"
                "OVERALL: KILLED\n"
                "REASON: x")
        res = self._parsed(resp, cand)
        self.assertIn("KILLED", res["attacks"]["obvious_combination"])
        self.assertNotIn("a2_v4_floors:memory_claim",
                         res["v4_corrections_applied"])

    def test_memory_claim_floor_never_touches_other_dimensions(self):
        cand = _full_candidate()
        cand["evidence_items"] = [{"id": "ev:1", "title": "x"}]
        resp = ("UNSUPPORTED_MECHANISM: KILLED - claimed 3.5-log at "
                "8 Wh/m3 is 1000x below the measurable regime\n"
                "WEAK_TRANSFER: PASS\n"
                "OBVIOUS_COMBINATION: PASS\n"
                "PRIOR_ART: PASS\n"
                "CONTRADICTION: PASS\n"
                "BOUNDARY_FAILURE: PASS\n"
                "ENGINEERING_INFEASIBILITY: PASS\n"
                "REGULATORY_INCOMPATIBILITY: PASS\n"
                "OVERALL: KILLED\n"
                "REASON: x")
        res = self._parsed(resp, cand)
        self.assertNotIn("a2_v4_floors:memory_claim",
                         res["v4_corrections_applied"])
        self.assertEqual(res["overall"], "KILLED")


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestV4Floors(unittest.TestCase):
    """The a2_gauntlet/1.1.0 deterministic floors — every rule WARRANTED
    by a measured R493/A2_BASELINE failure class (Art. LIX tuning on
    the DEV corpus only). The floors demote kills to PRESERVED
    objections; they never create a kill and never touch the
    deterministic gates."""

    @staticmethod
    def _parsed(attacks_text: str, candidate: dict,
                prior_art_state: str = "TOPICAL_RELATED"):
        from unittest import mock as _m
        with _m.patch.object(a2, "llm_chat", return_value=attacks_text):
            return a2.adversarial_challenge(candidate, True, prior_art_state)

    def test_version_travels_on_the_record(self):
        # R494 union: 1.1.0 (the sibling line's floors) + the burden-
        # of-proof rules (this line) -> 2.0.0 in the REGISTRY's id
        # scheme; the record carries BOTH keys (gauntlet_version —
        # the 1.1.0 line's; instrument_version — the registry's)
        self.assertEqual(a2.A2_GAUNTLET_VERSION,
                         "a2_adversarial_gauntlet/2.0.0")

    def test_contradiction_absence_floor(self):
        # the measured a2dev-20 class: CONTRADICTION killed with an
        # EMPTY evidence packet -> absence is not contradiction
        cand = _full_candidate()
        resp = ("UNSUPPORTED_MECHANISM: PASS\n"
                "WEAK_TRANSFER: PASS\n"
                "OBVIOUS_COMBINATION: PASS\n"
                "PRIOR_ART: PASS\n"
                "CONTRADICTION: KILLED - the claim is not supported by "
                "any data\n"
                "BOUNDARY_FAILURE: PASS\n"
                "ENGINEERING_INFEASIBILITY: PASS\n"
                "REGULATORY_INCOMPATIBILITY: PASS\n"
                "OVERALL: KILLED\n"
                "REASON: x")
        res = self._parsed(resp, cand)
        self.assertNotIn("KILLED", res["attacks"]["contradiction"])
        # R494 union: the demotion is the burden-of-proof RISK flag;
        # the 1.1.0 floor name rides as the lineage alias
        self.assertIn("RISK (burden-of-proof: absence_as_contradiction)",
                      res["attacks"]["contradiction"])
        self.assertIn("a2_v4_floors:contradiction_absence",
                      res["v4_corrections_applied"])
        self.assertIn("burden_of_proof:absence_as_contradiction",
                      res["v4_corrections_applied"])
        # the objection is PRESERVED verbatim in the demotion text
        self.assertIn("not supported by any data",
                      res["attacks"]["contradiction"])
        # and the candidate is no longer killed on that dimension
        self.assertEqual(res["overall"], "PASS")

    def test_contradiction_kill_with_evidence_survives_the_floor(self):
        cand = _full_candidate()
        # R494 union: the evidence must actually CARRY the conflicting
        # value (the two-sided standard) — an empty-shell evidence
        # item (id+title only) binds nothing and the kill demotes
        cand["predicted_effect"] = "5.5-log inactivation at rated flow"
        cand["evidence_items"] = [{"id": "ev:1",
                                   "title": "type-approval report",
                                   "finding": "3.8-log mean inactivation"}]
        resp = ("UNSUPPORTED_MECHANISM: PASS\n"
                "WEAK_TRANSFER: PASS\n"
                "OBVIOUS_COMBINATION: PASS\n"
                "PRIOR_ART: PASS\n"
                "CONTRADICTION: KILLED - the type-approval report "
                "measures 3.8-log against the claimed 5.5-log\n"
                "BOUNDARY_FAILURE: PASS\n"
                "ENGINEERING_INFEASIBILITY: PASS\n"
                "REGULATORY_INCOMPATIBILITY: PASS\n"
                "OVERALL: KILLED\n"
                "REASON: x")
        res = self._parsed(resp, cand)
        self.assertIn("KILLED", res["attacks"]["contradiction"])
        self.assertNotIn("a2_v4_floors:contradiction_absence",
                         res["v4_corrections_applied"])
        self.assertIn("burden_of_proof:burden_met",
                      res["v4_corrections_applied"])

    def test_ungrounded_kill_floor(self):
        # the baseline's dominant class: a kill with no number, no
        # named standard, no candidate-grounded content
        cand = _full_candidate()
        resp = ("UNSUPPORTED_MECHANISM: KILLED - the approach seems "
                "questionable overall\n"
                "WEAK_TRANSFER: PASS\n"
                "OBVIOUS_COMBINATION: PASS\n"
                "PRIOR_ART: PASS\n"
                "CONTRADICTION: PASS\n"
                "BOUNDARY_FAILURE: PASS\n"
                "ENGINEERING_INFEASIBILITY: PASS\n"
                "REGULATORY_INCOMPATIBILITY: PASS\n"
                "OVERALL: KILLED\n"
                "REASON: x")
        res = self._parsed(resp, cand)
        # R494 union: the demotion is the burden-of-proof RISK flag;
        # the 1.1.0 floor name rides as the lineage alias
        self.assertIn("RISK (burden-of-proof: unbound_derivation)",
                      res["attacks"]["unsupported_mechanism"])
        self.assertIn("a2_v4_floors:ungrounded_kill",
                      res["v4_corrections_applied"])
        self.assertIn("burden_of_proof:unbound_derivation",
                      res["v4_corrections_applied"])
        self.assertIn("questionable overall",
                      res["attacks"]["unsupported_mechanism"])
        self.assertEqual(res["overall"], "PASS")

    def test_grounded_kills_pass_the_floor(self):
        cand = _full_candidate()
        cand["evidence_items"] = [{"id": "ev:1", "title":
                                   "type-approval report of the same "
                                   "rotor-stator cavitation and UV "
                                   "combination"}]
        resp = ("UNSUPPORTED_MECHANISM: KILLED - claimed 3.5-log "
                "inactivation at 8 Wh/m3 specific energy is 1000x "
                "below the measurable radical regime\n"
                "WEAK_TRANSFER: PASS\n"
                "OBVIOUS_COMBINATION: KILLED - ev:1 documents the "
                "rotor-stator cavitation + UV combination as "
                "type-approved practice\n"
                "PRIOR_ART: PASS\n"
                "CONTRADICTION: PASS\n"
                "BOUNDARY_FAILURE: PASS\n"
                "ENGINEERING_INFEASIBILITY: PASS\n"
                "REGULATORY_INCOMPATIBILITY: PASS\n"
                "OVERALL: KILLED\n"
                "REASON: x")
        res = self._parsed(resp, cand)
        self.assertIn("KILLED", res["attacks"]["unsupported_mechanism"])
        self.assertIn("KILLED", res["attacks"]["obvious_combination"])
        self.assertNotIn("a2_v4_floors:ungrounded_kill",
                         res["v4_corrections_applied"])
        self.assertEqual(res["overall"], "KILLED")

    def test_obviousness_memory_claim_demotes(self):
        # R493 v4.1 (race instance 13, MEASURED): the union's earlier
        # named-specific grounding for obviousness is RETIRED BY
        # MEASUREMENT — the v4 run found memory-cited obviousness
        # kills false-killing clean controls; an obviousness kill must
        # be PACKET-ANCHORED (Art. XIX: the measurement beats the
        # design)
        from discovery_fabric.v4_corrections import (
            enforce_burden_of_proof)
        r = enforce_burden_of_proof(
            "obvious_combination",
            "KILLED - the named techniques (rotor-stator cavitation "
            "+ UV) are standard IMO D-2 practice",
            _full_candidate(), [])
        self.assertEqual(r["verdict"], "RISK")
        self.assertEqual(r["demotion_class"], "memory_claim")

    def test_floor_never_creates_a_kill_and_preserves_the_reason(self):
        # a PASS record passes through the floors untouched
        cand = _full_candidate()
        resp = ("UNSUPPORTED_MECHANISM: PASS\n"
                "WEAK_TRANSFER: PASS\n"
                "OBVIOUS_COMBINATION: PASS\n"
                "PRIOR_ART: PASS\n"
                "CONTRADICTION: PASS\n"
                "BOUNDARY_FAILURE: PASS\n"
                "ENGINEERING_INFEASIBILITY: PASS\n"
                "REGULATORY_INCOMPATIBILITY: PASS\n"
                "OVERALL: PASS\n"
                "REASON: clean")
        res = self._parsed(resp, cand)
        self.assertEqual(res["overall"], "PASS")
        self.assertNotIn("a2_v4_floors:contradiction_absence",
                         res["v4_corrections_applied"])
        self.assertNotIn("a2_v4_floors:ungrounded_kill",
                         res["v4_corrections_applied"])

    def test_kill_grounded_helper(self):
        g = a2._kill_grounded
        cand = _full_candidate()
        # number -> grounded
        self.assertTrue(g("KILLED - 3.5-log claim fails", cand))
        # named standard -> grounded
        self.assertTrue(g("KILLED - violates IMO D-2", cand))
        # 4-word verbatim echo of the candidate's own claims
        self.assertTrue(g("KILLED - staged hydrodynamic cascade "
                          "conditions cannot hold", cand))
        # generic boilerplate -> ungrounded
        self.assertFalse(g("KILLED - seems weak and unclear", cand))

    def test_objection_text_strips_the_verdict_token(self):
        # the demotion text must not re-enter the kill-scan: the
        # quoted objection never carries the literal KILLED token
        t = a2._objection_text("KILLED - the claim is unsupported")
        self.assertNotIn("KILLED", t)
        self.assertIn("the claim is unsupported", t)
        t2 = a2._objection_text("KILLED: bogus (KILLED twice)")
        self.assertNotIn("KILLED", t2)
        self.assertIn("kill-claim", t2)
