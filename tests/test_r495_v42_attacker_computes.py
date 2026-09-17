"""R495 — v4.2 (a2_adversarial_gauntlet/2.1.0, DEV): the
ATTACKER-COMPUTES kill standard.

The warrant (measured, twice): the deployed 2.0.0 instrument's
repetition runs (R495/A2_200_REPETITION + the shipped run #1) typed the
failure class the 2.0.0 record itself named — the evaluator hedges
derivable-but-uncomputed defects into RISK ("asserts 2.5-log removal by
density separation alone but provides no derivation linking the claimed
10 um d50 to the specific gravity of marine organisms"), TPR 0.27/0.22
vs the 0.75 bar while FPR stays 0.0 on every measured ring.

v4.2 changes ONE thing, on both sides of the instrument:
  1. the prompt: the attacker may MEET the burden by COMPUTING the
     derivation from the record's own numbers (show the arithmetic);
  2. the machine (CORRECTION 12 rule 4.5): a computed magnitude
     relation ANCHORED to a record NUMBER is a KEEP
     (attacker_computed_derivation) — placed AFTER the packet-anchor
     rule (obviousness stays strict: a computation cannot establish
     obviousness) and BEFORE the absence rule (the attacker may compute
     what the record lacked — the entire point).

These tests pin every boundary of the new rule AND the preservation of
every standing demotion class (the R491/R493/R494 discipline: a new
KEEP path must not reopen a closed false-kill class).
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.a2 import adversarial as a2  # noqa: E402
from discovery_fabric.v4_corrections import (  # noqa: E402
    enforce_burden_of_proof,
    attacker_computed_derivation,
    BURDEN_OF_PROOF_VERSION,
)

V42 = "a2_adversarial_gauntlet/2.1.0"

# the a2dev-05 shape (the measured hedged class): the record carries
# the numbers the derivation needs; the 2.0.0 evaluator refused to
# compute; the v4.2 evaluator computes and kills.
HYDROCYCLONE_CANDIDATE = {
    "mechanism": "de-aerating hydrocyclone removes organisms by "
                 "density separation at a 10 um d50 cut",
    "predicted_effect": "2.5-log organism removal at 700 m3/h using "
                        "only the existing pump head",
    "constraint_set": "300 mm mains; no added pumps; marine organisms "
                      "near the specific gravity of water (SG ~1.0)",
}
COMPUTED_BASIS = (
    "KILLED - the record claims 2.5-log removal by density separation "
    "at its own 10 um d50, but its own constraint set states the "
    "organisms sit near SG 1.0 — the density driving force at the "
    "record's 10 um d50 is near zero, roughly 1000x too weak to drive "
    "the claimed 2.5-log at 700 m3/h"
)
# the same defect, NOT computed — the 2.0.0 hedged form (must still
# demote: the R491 class is preserved)
HEDGED_BASIS = (
    "KILLED - the record asserts 2.5-log removal by density separation "
    "alone but provides no derivation linking the claimed 10 um d50 "
    "cut point to the specific gravity of marine organisms near that "
    "of water"
)


class TestVersions(unittest.TestCase):
    def test_gauntlet_version_bumped(self):
        self.assertEqual(a2.A2_GAUNTLET_VERSION, V42)
        self.assertEqual(a2.GAUNTLET_VERSION, V42)

    def test_burden_rules_version_bumped(self):
        self.assertEqual(BURDEN_OF_PROOF_VERSION, "burden_of_proof/1.1.0")

    def test_prompt_carries_the_computed_standard(self):
        self.assertIn("COMPUTE the defect", a2.ATTACK_PROMPT)
        self.assertIn("show the arithmetic", a2.ATTACK_PROMPT)
        # the computed example anchors the record's own values
        self.assertIn("10 um d50", a2.ATTACK_PROMPT)
        # the two-disposition rule replaced the flat prohibition
        self.assertNotIn(
            "NEVER kill a candidate merely for lacking a calculation",
            a2.ATTACK_PROMPT)
        self.assertIn(
            "a missing calculation you could have performed is not a "
            "RISK", a2.ATTACK_PROMPT)


class TestRule45(unittest.TestCase):
    """The new KEEP path — form AND anchor, and nothing else."""

    def test_computed_relation_with_record_anchor_keeps(self):
        r = enforce_burden_of_proof(
            "unsupported_mechanism", COMPUTED_BASIS,
            HYDROCYCLONE_CANDIDATE, [])
        self.assertEqual(r["verdict"], "KILLED")
        self.assertFalse(r["demoted"])
        self.assertEqual(r["disposition"],
                         "attacker_computed_derivation")

    def test_absence_demand_without_computation_still_demotes(self):
        """The R491 false-kill class is PRESERVED: on an EVIDENCED
        record (the cal-14 fixture class), an absence-demand with no
        shown arithmetic never kills, v4.2 or not. (On an evidence-BARE
        record the absence-asserting unsupported-mechanism kill stays
        the standing honest kill — rule 3, pinned below.)"""
        r = enforce_burden_of_proof(
            "unsupported_mechanism", HEDGED_BASIS,
            HYDROCYCLONE_CANDIDATE,
            [{"title": "Cyclone bench trial", "finding":
              "removal tracked the 10 um d50 across three feed rates"}])
        self.assertEqual(r["verdict"], "RISK")
        self.assertTrue(r["demoted"])
        self.assertEqual(r["demotion_class"], "lacks_derivation")

    def test_relation_without_record_anchor_still_demotes(self):
        """The fabrication guard: a magnitude relation whose numbers
        bind to NOTHING in the record is the unbound class (a
        requirement asserted from memory, dressed as arithmetic)."""
        r = enforce_burden_of_proof(
            "engineering_infeasibility",
            "KILLED - the claimed removal is 1000x too weak against "
            "typical industry requirements for this class of system",
            {"mechanism": "a novel separation stage",
             "predicted_effect": "2.5-log removal at rated flow"}, [])
        self.assertEqual(r["verdict"], "RISK")
        self.assertTrue(r["demoted"])
        self.assertEqual(r["demotion_class"], "unbound_derivation")

    def test_obviousness_not_rescued_by_computation(self):
        """Rule 4 fires BEFORE 4.5: obviousness kills need the PACKET
        anchor; a ratio over record numbers cannot establish
        obviousness (the v4.1 measured class — closed, stays closed)."""
        r = enforce_burden_of_proof(
            "obvious_combination",
            "KILLED - this is a 3x cheaper repack of the standard "
            "filter-plus-UV train every commercial system uses, an "
            "obvious combination at the record's own 350 m3/h",
            {"mechanism": "filter plus UV in series",
             "predicted_effect": "2.5-log at 350 m3/h"}, [])
        self.assertEqual(r["verdict"], "RISK")
        self.assertTrue(r["demoted"])
        self.assertEqual(r["demotion_class"], "memory_claim")

    def test_one_sided_contradiction_not_rescued_by_computation(self):
        """Rule 1 fires BEFORE 4.5: a contradiction needs BOTH sides;
        arithmetic cannot substitute for the missing evidence side."""
        r = enforce_burden_of_proof(
            "contradiction",
            "KILLED - the claimed 3.5-log is 10x above what the "
            "evidence would support if it were provided",
            {"mechanism": "UV stage", "predicted_effect": "3.5-log"}, [])
        self.assertEqual(r["verdict"], "RISK")
        self.assertTrue(r["demoted"])
        self.assertEqual(r["demotion_class"],
                         "absence_as_contradiction")

    def test_prior_art_state_binding_unchanged(self):
        r = enforce_burden_of_proof(
            "prior_art", "KILLED - already disclosed",
            {"mechanism": "a stage"}, [],
            prior_art_state="IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE")
        self.assertEqual(r["verdict"], "KILLED")
        self.assertEqual(r["disposition"], "prior_art_state_binding")

    def test_record_stated_magnitude_still_burden_met(self):
        """A record-bound kill WITHOUT relation language keeps its
        standing disposition (burden_met) — 4.5 adds a path, it does
        not re-route the old one."""
        r = enforce_burden_of_proof(
            "engineering_infeasibility",
            "KILLED - the candidate's own 13-15 bar return flow "
            "exceeds the 10 bar rating its own spec declares",
            {"predicted_effect": "85% removal at 13-15 bar",
             "constraint_set": "components rated to 10 bar"}, [])
        self.assertEqual(r["verdict"], "KILLED")
        self.assertEqual(r["disposition"], "burden_met")

    def test_evidence_bare_honest_kill_preserved(self):
        r = enforce_burden_of_proof(
            "unsupported_mechanism",
            "KILLED - The 4-log inactivation claim at 0.2 s transit "
            "has no supporting evidence of any kind in the record",
            {"mechanism": "UV inactivation in a 0.2 s transit cell",
             "predicted_effect": "4-log organism inactivation"}, [])
        self.assertEqual(r["verdict"], "KILLED")
        self.assertEqual(r["disposition"], "evidence_bare_honest_kill")

    def test_malformed_still_fails_toward_risk(self):
        r = enforce_burden_of_proof(None, None, None, None)
        self.assertEqual(r["verdict"], "RISK")
        self.assertTrue(r["demoted"])
        self.assertEqual(r["demotion_class"], "burden_check_error")


class TestHelper(unittest.TestCase):
    """The form/anchor split, directly."""

    def test_form_without_anchor_is_not_a_derivation(self):
        self.assertFalse(attacker_computed_derivation(
            "1000x too weak against typical requirements",
            {"mechanism": "a stage", "predicted_effect": "2.5-log"}))

    def test_anchor_without_form_is_not_a_derivation(self):
        self.assertFalse(attacker_computed_derivation(
            "the record's own 10 um d50 is cited here with no "
            "arithmetic relation at all",
            HYDROCYCLONE_CANDIDATE))

    def test_form_and_anchor_is_a_derivation(self):
        self.assertTrue(attacker_computed_derivation(
            COMPUTED_BASIS, HYDROCYCLONE_CANDIDATE))

    def test_evidence_side_numbers_anchor_too(self):
        self.assertTrue(attacker_computed_derivation(
            "KILLED - the claimed 3.5-log is 10x above the measured "
            "3.8-log band the evidence itself reports",
            {"predicted_effect": "3.5-log inactivation"},
            [{"finding": "mean 3.8-log with replicates below margin"}]))


if __name__ == "__main__":
    unittest.main()
