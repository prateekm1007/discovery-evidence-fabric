"""tests/test_r494_a2_burden_of_proof.py — R494: the A2 gauntlet's v4
BURDEN-OF-PROOF rules (a2_adversarial_gauntlet/2.0.0) — the
three-verdict vocabulary (PASS | RISK | KILLED), the machine-side
enforce_burden_of_proof (lacks-derivation -> RISK, never KILL), the
record's instrument_version + risk_flags + burden_of_proof ledger, and
the consumption gate's v4 wiring (the record's own instrument_version
selects the registry entry; the calibrated authority is RING-BOUND —
a kill served by a different ring escalates, never rejects).

Pinned behaviors:
  1. enforce_burden_of_proof (the ONE authoritative implementation in
     v4_corrections.py): the cal-14 lacks-derivation class demotes; the
     evidence-bare unsupported-mechanism kill is HONEST (the corpus's
     own ruling); a two-sided contradiction (claim value vs divergent
     evidence value, both in the record) keeps its kill; a bare
     unbound assertion demotes; the cal-13 attacker-imported-scope
     class demotes; absence-as-contradiction demotes (Art. XXI.3);
     malformed input fails toward RISK, never toward KILL.
  2. The gauntlet: v4-format lines ("KILLED - basis...") and bare
     v3-format lines both parse; RISK dims ride risk_flags and never
     kill; a demoted kill becomes a RISK flag with its class; a bound
     kill survives and kills; the record carries instrument_version
     2.0.0, the burden_of_proof ledger, and its own transport stamp.
  3. Consumption: a v4 record while 2.0.0 is unmeasured escalates
     (never REJECTED); with a registered meeting-the-bars measurement
     the kill terminates REJECTED again (same ring); a kill served by
     a DIFFERENT ring escalates with a typed ring_mismatch; a legacy
     record (no instrument_version) resolves the 1.0.0 entry.
  4. The registry: the 2.0.0 entry exists and resolves fail-closed
     until its own measurement + seal ship under the pinned names.

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
from discovery_fabric.v4_corrections import (  # noqa: E402
    enforce_burden_of_proof,
)

V4 = "a2_adversarial_gauntlet/2.0.0"
V1 = "a2_adversarial_gauntlet/1.0.0"

_VERIFICATION_OK = {"verified": True, "issues": []}
_PRIOR_ART_PASS = {"prior_art_status": "TOPICAL_RELATED"}


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


EVIDENCED_CANDIDATE = {
    "mechanism": "Hydrocyclone separation removes particles above 100 "
                 "microns from the return flow before UV treatment",
    "predicted_effect": "85% removal of particles above 100 microns "
                        "at 13-15 bar return flow",
    "testable_prediction": "Particle counts before and after the "
                           "cyclone at fleet return rates",
}
EVIDENCED_ITEMS = [{"title": "Tank trial", "finding":
                    "Cyclonic return removed 83-87% of particles "
                    "above 100 microns at 14 bar across 12 voyages"}]


class TestEnforceBurdenOfProof(unittest.TestCase):
    """The ONE authoritative implementation — the named classes."""

    def test_cal14_lacks_derivation_demotes(self):
        r = enforce_burden_of_proof(
            "engineering_infeasibility",
            "KILLED - The hydrocyclone cannot achieve the claimed 85% "
            "removal for particles above 100 microns at the specified "
            "return flow rate without providing cyclone geometry "
            "calculations or pressure drop data that would confirm "
            "separation efficiency",
            EVIDENCED_CANDIDATE, EVIDENCED_ITEMS)
        self.assertEqual(r["verdict"], "RISK")
        self.assertTrue(r["demoted"])
        self.assertEqual(r["demotion_class"], "lacks_derivation")

    def test_evidence_bare_unsupported_mechanism_is_honest(self):
        r = enforce_burden_of_proof(
            "unsupported_mechanism",
            "KILLED - The 4-log inactivation claim at 0.2 s transit "
            "has no supporting evidence of any kind in the record",
            {"mechanism": "UV inactivation in a 0.2 s transit cell",
             "predicted_effect": "4-log organism inactivation"}, [])
        self.assertEqual(r["verdict"], "KILLED")
        self.assertFalse(r["demoted"])
        self.assertEqual(r["disposition"], "evidence_bare_honest_kill")

    def test_two_sided_contradiction_keeps_kill(self):
        r = enforce_burden_of_proof(
            "contradiction",
            "KILLED - The candidate claims 5.5-log inactivation while "
            "its own type-approval report measures 3.8-log mean with "
            "the CI topping at 4.4 and two replicates below the margin",
            {"mechanism": "UV dose delivery",
             "predicted_effect": "5.5-log inactivation"},
            [{"title": "Type approval report", "finding":
              "3.8-log mean inactivation, 95% CI 3.1-4.4, two of ten "
              "replicates below the D-2 margin"}])
        self.assertEqual(r["verdict"], "KILLED")
        self.assertEqual(r["disposition"], "burden_met")

    def test_unbound_bare_assertion_demotes(self):
        r = enforce_burden_of_proof(
            "engineering_infeasibility",
            "KILLED - this design is not buildable with shipyard "
            "methods",
            {"mechanism": "something", "predicted_effect": "an "
                          "effect"}, [])
        self.assertEqual(r["verdict"], "RISK")
        self.assertEqual(r["demotion_class"], "unbound_derivation")

    def test_cal13_attacker_imported_scope_demotes(self):
        r = enforce_burden_of_proof(
            "unsupported_mechanism",
            "KILLED - a 300 micron stage followed by a 120 micron "
            "stage cannot capture particles below 120 microns, yet the "
            "candidate claims nuclei above 120 microns removal while "
            "implying comprehensive suppression of scale particles",
            {"mechanism": "staged filtration: 300 micron stage then "
                          "120 micron stage catching aggregate nuclei "
                          "above 120 microns",
             "predicted_effect": "8x reduction in scale nucleus "
                                 "share"}, [])
        self.assertEqual(r["verdict"], "RISK")
        self.assertEqual(r["demotion_class"], "attacker_imported_scope")

    def test_absence_as_contradiction_demotes(self):
        r = enforce_burden_of_proof(
            "contradiction",
            "KILLED - nothing in the record contradicts the claim, "
            "there is simply no data",
            {"mechanism": "ozone injection",
             "predicted_effect": "3-log kill"}, [])
        self.assertEqual(r["verdict"], "RISK")
        self.assertEqual(r["demotion_class"], "absence_as_contradiction")

    def test_evidenced_record_absence_demand_demotes(self):
        r = enforce_burden_of_proof(
            "unsupported_mechanism",
            "KILLED - the mechanism has no supporting evidence",
            EVIDENCED_CANDIDATE, EVIDENCED_ITEMS)
        self.assertEqual(r["verdict"], "RISK")
        self.assertEqual(r["demotion_class"], "lacks_derivation")

    def test_bound_infeasibility_keeps_kill(self):
        r = enforce_burden_of_proof(
            "engineering_infeasibility",
            "KILLED - removing 10 micron organisms at full flow needs "
            "a pressure drop above 25 bar per the stated 3000 m3/h; "
            "the record's own pump spec tops at 16 bar - the cut point "
            "d50 cannot be met",
            {"mechanism": "hydrocyclone 10um at full flow 3000 m3/h",
             "predicted_effect": "d50 cut point at 10 microns",
             "constraint_set": "pump head limit 16 bar"}, [])
        self.assertEqual(r["verdict"], "KILLED")
        self.assertEqual(r["disposition"], "burden_met")

    def test_malformed_input_fails_toward_risk(self):
        r = enforce_burden_of_proof(
            "engineering_infeasibility", None, object(), None)
        self.assertEqual(r["verdict"], "RISK")
        self.assertTrue(r["demoted"])


class TestGauntletV4Parsing(unittest.TestCase):
    def _resp(self, lines):
        return "\n".join(lines)

    def _attack(self, resp, candidate=None, prior_art="UNKNOWN"):
        cand = candidate or _full_candidate()
        with mock.patch.object(a2, "llm_chat",
                               return_value=resp) as _m:
            rec = a2.adversarial_challenge(cand, True, prior_art)
        return rec

    def test_v4_shape_parses_and_risk_never_kills(self):
        resp = self._resp([
            "UNSUPPORTED_MECHANISM: RISK - the record lacks the "
            "dose calculation the 3.5-log claim needs",
            "WEAK_TRANSFER: PASS - transfer is direct",
            "OBVIOUS_COMBINATION: PASS - no objection",
            "PRIOR_ART: PASS - no objection",
            "CONTRADICTION: PASS - no objection",
            "BOUNDARY_FAILURE: PASS - no objection",
            "ENGINEERING_INFEASIBILITY: PASS - no objection",
            "REGULATORY_INCOMPATIBILITY: PASS - no objection",
            "OVERALL: PASS",
            "REASON: the claim needs its dose derivation",
        ])
        rec = self._attack(resp)
        self.assertEqual(rec["overall"], "PASS")
        self.assertEqual(rec["killed_count"], 0)
        self.assertEqual(len(rec["risk_flags"]), 1)
        self.assertEqual(rec["risk_flags"][0]["dimension"],
                         "unsupported_mechanism")
        self.assertEqual(rec["risk_flags"][0]["source"],
                         "evaluator_risk")
        self.assertEqual(rec["instrument_version"], V4)

    def test_v3_bare_shape_parses_but_bare_kills_demote(self):
        resp = self._resp([
            "UNSUPPORTED_MECHANISM: KILLED",
            "WEAK_TRANSFER: PASS",
            "OBVIOUS_COMBINATION: PASS",
            "PRIOR_ART: PASS",
            "CONTRADICTION: PASS",
            "BOUNDARY_FAILURE: PASS",
            "ENGINEERING_INFEASIBILITY: PASS",
            "REGULATORY_INCOMPATIBILITY: PASS",
            "OVERALL: KILLED",
            "REASON: unsupported",
        ])
        # a BARE kill (no basis text at all) is the measured baseline
        # defect (R445-B: 100% bare assertions; the R493 baseline's
        # TPR 0.0909 root cause) — there is nothing to verify, so the
        # burden is not met and the kill demotes to RISK (fail toward
        # RISK, never toward KILL)
        rec = self._attack(resp)
        self.assertEqual(rec["overall"], "PASS")
        self.assertEqual(rec["killed_count"], 0)
        flags = [f for f in rec["risk_flags"]
                 if f["source"] == "demoted_kill"]
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["demotion_class"],
                         "unbound_derivation")

    def test_evidence_bare_kill_with_stated_absence_keeps_kill(self):
        resp = self._resp([
            "UNSUPPORTED_MECHANISM: KILLED - the 4-log claim at 0.2 s "
            "transit has no supporting evidence of any kind in the "
            "record",
            "WEAK_TRANSFER: PASS - none",
            "OBVIOUS_COMBINATION: PASS - none",
            "PRIOR_ART: PASS - none",
            "CONTRADICTION: PASS - none",
            "BOUNDARY_FAILURE: PASS - none",
            "ENGINEERING_INFEASIBILITY: PASS - none",
            "REGULATORY_INCOMPATIBILITY: PASS - none",
            "OVERALL: KILLED",
            "REASON: zero evidence for the load-bearing claim",
        ])
        cand = {"mechanism": "UV inactivation in a 0.2 s transit cell",
                "predicted_effect": "4-log organism inactivation",
                "falsification_test": "bench loop shows the log "
                                      "reduction or the claim is dead"}
        rec = self._attack(resp, candidate=cand)
        # the corpus's own honest-kill ruling: the record is
        # evidence-bare and the kill SAYS so — honest (a2dev-20)
        self.assertEqual(rec["overall"], "KILLED")
        self.assertEqual(
            rec["v4_corrections_applied"].count(
                "burden_of_proof:evidence_bare_honest_kill"), 1)

    def test_demoted_kill_becomes_risk_flag(self):
        resp = self._resp([
            "UNSUPPORTED_MECHANISM: PASS - none",
            "WEAK_TRANSFER: PASS - none",
            "OBVIOUS_COMBINATION: PASS - none",
            "PRIOR_ART: PASS - none",
            "CONTRADICTION: PASS - none",
            "BOUNDARY_FAILURE: PASS - none",
            "ENGINEERING_INFEASIBILITY: KILLED - cannot achieve the "
            "claimed 85% removal without providing cyclone geometry "
            "calculations that would confirm separation efficiency",
            "REGULATORY_INCOMPATIBILITY: PASS - none",
            "OVERALL: KILLED",
            "REASON: no geometry calculation",
        ])
        cand = dict(EVIDENCED_CANDIDATE)
        cand["evidence_items"] = EVIDENCED_ITEMS
        rec = self._attack(resp, candidate=cand)
        # the absence-based kill demotes to RISK: overall PASS, the
        # objection preserved as a flag with its class
        self.assertEqual(rec["overall"], "PASS")
        self.assertEqual(rec["killed_count"], 0)
        flags = [f for f in rec["risk_flags"]
                 if f["source"] == "demoted_kill"]
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["demotion_class"],
                         "lacks_derivation")
        self.assertEqual(flags[0]["dimension"],
                         "engineering_infeasibility")
        self.assertTrue(rec["attacks"]["engineering_infeasibility"]
                        .startswith("RISK (burden-of-proof:"))
        self.assertEqual(
            rec["burden_of_proof"]["kills_demoted_to_risk"], 1)

    def test_bound_kill_survives_and_kills(self):
        resp = self._resp([
            "UNSUPPORTED_MECHANISM: PASS - none",
            "WEAK_TRANSFER: PASS - none",
            "OBVIOUS_COMBINATION: PASS - none",
            "PRIOR_ART: PASS - none",
            "CONTRADICTION: KILLED - the candidate claims 5.5-log "
            "while the cited type-approval report measures 3.8-log "
            "mean with the CI topping at 4.4",
            "BOUNDARY_FAILURE: PASS - none",
            "ENGINEERING_INFEASIBILITY: PASS - none",
            "REGULATORY_INCOMPATIBILITY: PASS - none",
            "OVERALL: KILLED",
            "REASON: the claim contradicts its own evidence",
        ])
        cand = {"mechanism": "UV dose delivery",
                "predicted_effect": "5.5-log inactivation",
                "evidence_items": [{"title": "Type approval report",
                                    "finding": "3.8-log mean, 95% CI "
                                    "3.1-4.4, two replicates below "
                                    "the margin"}]}
        rec = self._attack(resp, candidate=cand)
        self.assertEqual(rec["overall"], "KILLED")
        self.assertEqual(rec["killed_count"], 1)
        self.assertEqual(
            rec["burden_of_proof"]["kills_kept"], 1)
        self.assertIn("burden_of_proof:burden_met",
                      rec["v4_corrections_applied"])

    def test_record_carries_transport_stamp(self):
        resp = self._resp([
            "UNSUPPORTED_MECHANISM: PASS - none",
            "WEAK_TRANSFER: PASS - none",
            "OBVIOUS_COMBINATION: PASS - none",
            "PRIOR_ART: PASS - none",
            "CONTRADICTION: PASS - none",
            "BOUNDARY_FAILURE: PASS - none",
            "ENGINEERING_INFEASIBILITY: PASS - none",
            "REGULATORY_INCOMPATIBILITY: PASS - none",
            "OVERALL: PASS",
            "REASON: none",
        ])
        rec = self._attack(resp)
        # the instrument's own transport provenance rides the record
        # (mocked llm_chat never sets the meta — the stamp carries
        # whatever the meta holds, never fabricates)
        self.assertIn("transport", rec)
        self.assertIsInstance(rec["transport"], dict)

    def test_verdict_extraction_helpers(self):
        self.assertEqual(a2._verdict_of("KILLED - basis text"), "KILLED")
        self.assertEqual(a2._verdict_of("RISK - basis"), "RISK")
        self.assertEqual(a2._verdict_of("PASS"), "PASS")
        self.assertEqual(a2._verdict_of("KILLED"), "KILLED")
        self.assertEqual(a2._verdict_of(""), "UNKNOWN")
        # containment fallback for mid-line verdicts (malformed)
        self.assertEqual(a2._verdict_of("verdict: KILLED"), "KILLED")
        self.assertEqual(a2._basis_body("KILLED - the basis"),
                         "the basis")
        self.assertEqual(a2._basis_body("RISK - lacks dose data"),
                         "lacks dose data")


class TestConsumptionGateV4(unittest.TestCase):
    def _v4_kill_record(self, provider="zai", model="zai-org/GLM-5.3"):
        return {
            "overall": "KILLED", "killed_count": 1,
            "instrument_version": V4,
            "reason": "the claim contradicts its own evidence",
            "attacks": {"contradiction":
                        "KILLED - claims 5.5-log while the report "
                        "measures 3.8-log"},
            "transport": {"provider": provider, "model": model,
                          "ring_pin": {"requested": provider,
                                       "served_provider": provider,
                                       "served_model": model}},
        }

    def test_registry_entry_v4_exists_and_fails_closed(self):
        self.assertIn(V4, gate.INSTRUMENT_MEASUREMENTS)
        st = gate.resolve_state(instrument_version=V4)
        # the measured-NOT_CALIBRATED state (the R487 precedent: the
        # failing measurement SHIPS; the state derives from real
        # numbers — the union's TPR 0.2727 fails the 0.75 bar)
        self.assertEqual(st["state"], "NOT_CALIBRATED")
        self.assertFalse(st["terminal_kill_admissible"])
        self.assertEqual(st["measured"]["tpr_scoped"], 0.2727)
        self.assertEqual(st["measured"]["fpr_known_good"], 0.0)
        self.assertEqual(st["measured"]["attacker_ring"]["provider"],
                         "xkiro")

    def test_v4_uncalibrated_kill_escalates(self):
        res = a2classify.classify(
            _full_candidate(), _VERIFICATION_OK, _PRIOR_ART_PASS,
            self._v4_kill_record())
        self.assertNotEqual(res["final_status"], "REJECTED")
        esc = res.get("adversarial_escalation") or {}
        self.assertEqual(esc["gate"]["instrument"], V4)
        self.assertFalse(esc["gate"]["terminal_kill_admissible"])

    def test_legacy_record_resolves_the_1_0_0_entry(self):
        rec = self._v4_kill_record()
        rec.pop("instrument_version")
        res = a2classify.classify(
            _full_candidate(), _VERIFICATION_OK, _PRIOR_ART_PASS, rec)
        self.assertNotEqual(res["final_status"], "REJECTED")
        esc = res.get("adversarial_escalation") or {}
        self.assertEqual(esc["gate"]["instrument"], V1)

    def _registered(self, provider="zai", model="zai-org/GLM-5.3"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        td = Path(tmp.name)
        meas = {
            "metrics": {"false_kill_rate_on_known_good": 0.0,
                        "coverage": 1.0, "parse_completeness": 1.0},
            "scoped_tpr_diagnostic": {"tpr": 1.0},
            "threshold_verdict": {"calibrated": True},
            "n_cases_attacked": 21,
            "attacker_ring": {"provider": provider, "model": model},
        }
        seal = {"pre_registered_thresholds": {
            "tpr_min": 0.75, "fpr_max": 0.30,
            "coverage_min": 0.875, "parse_completeness_min": 0.875}}
        (td / "m.json").write_text(json.dumps(meas))
        (td / "s.json").write_text(json.dumps(seal))
        return mock.patch.dict(
            gate.INSTRUMENT_MEASUREMENTS,
            {V4: {"measurement": td / "m.json",
                  "seal": td / "s.json"}})

    def test_calibrated_same_ring_kill_terminates(self):
        with self._registered():
            res = a2classify.classify(
                _full_candidate(), _VERIFICATION_OK,
                _PRIOR_ART_PASS, self._v4_kill_record())
            self.assertEqual(res["final_status"], "REJECTED")
            self.assertNotIn("adversarial_escalation", res)

    def test_calibrated_mismatched_ring_escalates(self):
        with self._registered(provider="zai",
                              model="zai-org/GLM-5.3"):
            rec = self._v4_kill_record(provider="atria",
                                       model="Atria-Dawn-Preview")
            res = a2classify.classify(
                _full_candidate(), _VERIFICATION_OK,
                _PRIOR_ART_PASS, rec)
            # the (rules x ring) authority does not transfer: the kill
            # escalates with a typed ring_mismatch, never rejects
            self.assertNotEqual(res["final_status"], "REJECTED")
            esc = res.get("adversarial_escalation") or {}
            self.assertEqual(esc["gate"]["ring_mismatch"]["kind"],
                             "RING_MISMATCH_PROVIDER")
            self.assertIn("ring-bound", esc["gate"]["reason"])

    def test_calibrated_mismatched_model_escalates(self):
        with self._registered(provider="zai",
                              model="zai-org/GLM-5.3"):
            rec = self._v4_kill_record(provider="zai",
                                       model="some-other-model")
            res = a2classify.classify(
                _full_candidate(), _VERIFICATION_OK,
                _PRIOR_ART_PASS, rec)
            self.assertNotEqual(res["final_status"], "REJECTED")
            esc = res.get("adversarial_escalation") or {}
            self.assertEqual(esc["gate"]["ring_mismatch"]["kind"],
                             "RING_MISMATCH_MODEL")

    def test_record_note_override(self):
        with self._registered() as patch:
            st = gate.resolve_state(instrument_version=V4)
            self.assertEqual(st["state"], "CALIBRATED")
            self.assertTrue(st["terminal_kill_admissible"])
            # an instrument-specific note on the record travels with
            # the state (the v3-engine prose is the fallback only)
            self.assertIn("sealed 40-case corpus",
                          st["measured_verdict_note"])


class TestRiskFlagsNeverTerminal(unittest.TestCase):
    def test_risk_only_record_passes_classify(self):
        rec = {
            "overall": "PASS", "killed_count": 0,
            "instrument_version": V4,
            "reason": "the claim needs its dose derivation",
            "attacks": {"unsupported_mechanism":
                        "RISK - the record lacks the dose calculation",
                        "weak_transfer": "PASS - none",
                        "obvious_combination": "PASS - none",
                        "prior_art": "PASS - none",
                        "contradiction": "PASS - none",
                        "boundary_failure": "PASS - none",
                        "engineering_infeasibility": "PASS - none",
                        "regulatory_incompatibility": "PASS - none"},
            "risk_flags": [{"dimension": "unsupported_mechanism",
                            "verdict": "RISK",
                            "basis": "the record lacks the dose "
                                     "calculation",
                            "source": "evaluator_risk"}],
        }
        res = a2classify.classify(
            _full_candidate(), _VERIFICATION_OK, _PRIOR_ART_PASS, rec)
        self.assertNotEqual(res["final_status"], "REJECTED")
        self.assertFalse(res.get("promotion_blocked", False))


if __name__ == "__main__":
    unittest.main()
