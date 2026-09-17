"""tests/test_r490_a2_calibration_annotation.py — the A2 calibration-
scope decision, record layer (R490/A2_CALIBRATION_SCOPE.json option a).

Pinned behaviors:
  1. Every adversarial_challenge result carries the Article L scope
     annotation (calibration_scope), whatever the outcome: KILL, PASS,
     EVALUATOR_CALL_FAILED, NOT_RUN (evidence gate).
  2. The annotation states the uncalibrated state
     (UNCALIBRATED_NO_MEASUREMENT_SHIPPED) and the sealed-bar coverage
     (NONE) — the R489 composition finding is permanently visible on
     every A2 record.
  3. The annotation is METADATA ONLY: the KILL verdict, the dimension
     verdicts, the V4 corrections and the reason all pass through
     UNCHANGED (no gate semantics changed by hand this round — the
     consumption-side escalation rides the next behavior deploy).
  4. The annotation survives a mutating consumer (the stamped dict is a
     copy: mutating the result copy does not corrupt the module
     constant).

reviewer_provenance=AI_REVIEW
"""
from __future__ import annotations

import sys
import unittest
from unittest import mock
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.a2 import adversarial as a2  # noqa: E402


CANDIDATE = {
    "candidate_id": "t-r490",
    "mechanism": "a ducted radial diffuser ring upstream of the existing "
                 "flat-faced follower converts the point contact into a "
                 "hydrostatic pad without touching the cam profile",
    "intervention": "bolt-on ring between the stud and the follower",
    "predicted_effect": "contact stress falls below the 1.0 gigapascal "
                        "rolling-contact band",
    "testable_prediction": "strain-gauge coupon test over one 20-hour "
                           "shift shows the reduction",
    "evidence_items": [
        {"id": "ev:cam-pad-doc",
         "title": "USPTO 4,444,444: bolt-on hydrostatic pad ring for "
                  "cam-follower interfaces, claimed as the standard "
                  "retrofit for point-contact followers"}],
}

KILL_RESPONSE = """
UNSUPPORTED_MECHANISM: PASS
WEAK_TRANSFER: PASS
OBVIOUS_COMBINATION: KILLED - ev:cam-pad-doc discloses the bolt-on ring converting point contact into a hydrostatic pad as the standard cam-follower retrofit (R493 v4: packet-anchored per the kill standard)
PRIOR_ART: PASS
CONTRADICTION: PASS
BOUNDARY_FAILURE: PASS
ENGINEERING_INFEASIBILITY: PASS
REGULATORY_INCOMPATIBILITY: PASS
OVERALL: KILLED
REASON: the ring is a standard hydrostatic pad retrofit known in the cam-follower literature.
"""

PASS_RESPONSE = """
UNSUPPORTED_MECHANISM: PASS
WEAK_TRANSFER: PASS
OBVIOUS_COMBINATION: PASS
PRIOR_ART: PASS
CONTRADICTION: PASS
BOUNDARY_FAILURE: PASS
ENGINEERING_INFEASIBILITY: PASS
REGULATORY_INCOMPATIBILITY: PASS
OVERALL: PASS
REASON: the mechanism is specific and evidence-anchored.
"""


class TestR490A2CalibrationAnnotation(unittest.TestCase):
    def test_scope_constant_shape(self):
        self.assertEqual(
            a2.A2_CALIBRATION_SCOPE["article_l_state"],
            "UNCALIBRATED_NO_MEASUREMENT_SHIPPED")
        self.assertIn("NONE", a2.A2_CALIBRATION_SCOPE["sealed_bar_coverage"])
        self.assertIn("R490/A2_CALIBRATION_SCOPE.json",
                      a2.A2_CALIBRATION_SCOPE["ruling"])

    def test_kill_carries_annotation_and_verdict_unchanged(self):
        with mock.patch.object(a2, "llm_chat", return_value=KILL_RESPONSE):
            res = a2.adversarial_challenge(
                dict(CANDIDATE), evidence_verified=True,
                prior_art_state="NO_MATCH_FOUND")
        # R493/R494 union: the fixture is the sibling line's GROUNDED
        # kill (the 4-gram overlap with the candidate's own mechanism
        # text binds it) — under the union's burden-of-proof rules the
        # grounding carries the burden and the kill SURVIVES (their
        # amended intent). The bare-kill-demotes contract is pinned in
        # test_r494_a2_burden_of_proof (the R445-B class).
        self.assertEqual(res["overall"], "KILLED")
        self.assertIn("KILLED", res["attacks"]["obvious_combination"])
        # the annotation rides the record
        cs = res["calibration_scope"]
        self.assertEqual(cs["article_l_state"],
                         "UNCALIBRATED_NO_MEASUREMENT_SHIPPED")
        # metadata only: no demotion, no escalation, verdict untouched
        # BY THE ANNOTATION (the surviving kill above is the RULES'
        # doing, not the annotation's)
        self.assertNotIn("attack_outcome", res)
        self.assertNotIn("escalated", res)

    def test_pass_carries_annotation(self):
        with mock.patch.object(a2, "llm_chat", return_value=PASS_RESPONSE):
            res = a2.adversarial_challenge(
                dict(CANDIDATE), evidence_verified=True,
                prior_art_state="NO_MATCH_FOUND")
        self.assertEqual(res["overall"], "PASS")
        self.assertEqual(res["calibration_scope"]["article_l_state"],
                         "UNCALIBRATED_NO_MEASUREMENT_SHIPPED")

    def test_transport_failure_carries_annotation(self):
        with mock.patch.object(a2, "llm_chat", return_value=None):
            res = a2.adversarial_challenge(
                dict(CANDIDATE), evidence_verified=True,
                prior_art_state="NO_MATCH_FOUND")
        self.assertEqual(res["overall"], "EVALUATOR_CALL_FAILED")
        self.assertFalse(res["is_scientific_verdict"])
        self.assertEqual(res["calibration_scope"]["article_l_state"],
                         "UNCALIBRATED_NO_MEASUREMENT_SHIPPED")

    def test_not_run_carries_annotation(self):
        res = a2.adversarial_challenge(
            dict(CANDIDATE), evidence_verified=False,
            prior_art_state="NO_MATCH_FOUND")
        self.assertEqual(res["overall"], "NOT_RUN")
        self.assertEqual(res["calibration_scope"]["article_l_state"],
                         "UNCALIBRATED_NO_MEASUREMENT_SHIPPED")

    def test_annotation_is_a_copy(self):
        """A mutating consumer cannot corrupt the module constant."""
        with mock.patch.object(a2, "llm_chat", return_value=PASS_RESPONSE):
            res = a2.adversarial_challenge(
                dict(CANDIDATE), evidence_verified=True,
                prior_art_state="NO_MATCH_FOUND")
        res["calibration_scope"]["article_l_state"] = "TAMPERED"
        self.assertEqual(
            a2.A2_CALIBRATION_SCOPE["article_l_state"],
            "UNCALIBRATED_NO_MEASUREMENT_SHIPPED")


if __name__ == "__main__":
    unittest.main()
