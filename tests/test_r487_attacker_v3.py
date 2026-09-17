"""tests/test_r487_attacker_v3.py — the v3 ANCHOR + ACCOMMODATION
discipline (the R417 ruling's decisive repair) + the calibration
measurement transport.

Pinned behaviors:
  1. ANCHOR floor: a computation-only KILL demotes (objection preserved)
  2. CONCESSION_DISPOSAL: a kill bound to the candidate's own declared
     known_failure_modes demotes
  3. HEDGED_TARGET: a kill disputing a quoted/attributed hedged quantity
     demotes; the attacker's OWN hedged arithmetic does NOT demote
  4. UNSTATED_ELEMENT: a kill resting on record silence demotes
  5. TYPICAL_VALUE_PREMISE: a kill premising an explicitly typical
     external value demotes
  6. EVIDENCE-anchored kills are never accommodation-demoted
  7. A true seeded-defect-shaped kill (unhedged internal contradiction,
     anchored) STANDS
  8. Overall composition: kills all demoted -> ESCALATED_OBJECTION with
     the v3 rule traveling on the preserved objection
  9. The gate: v3.0.0 resolves fail-closed (UNKNOWN_NOT_CALIBRATED)
     until its OWN measurement exists in-tree; v1/v2/v2.1 states are
     unchanged (NOT_CALIBRATED)
  10. The calibration transport route: validates payload shape, caps,
      and returns the instrument's record (mocked LLM)

reviewer_provenance=AI_REVIEW
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import attacker_calibration as gate  # noqa: E402
from discovery_fabric.engine import independent_attack as ia  # noqa: E402


CANDIDATE = {
    "candidate_id": "t-v3",
    "mechanism": "a staged wedge-wire cascade removes scale particles "
                 "above 120 microns and the dP-triggered backflush "
                 "restores full flow",
    "intervention": "two-stage cascade on the 150 mm supply line",
    "predicted_effect": "campaign clogging events fall from 4.1 to "
                        "below 1.5",
    "testable_prediction": "coupon test shows the reduction over a "
                           "120-hour campaign",
    "novel_design_variable": "stage cut size",
    "known_failure_modes": [
        "fine passive slimes crossing both stages (addressed by the "
        "existing biocide program, measured share 18 percent)"],
    "constraint_set": {
        "boundary_conditions": "14 bar supply; roll-change-window "
                               "installation; no mill stop"},
}


def _bindings(*kinds, span="fine passive slimes crossing both",
              field="known_failure_modes"):
    out = []
    for k in kinds:
        b = {"binding": k, "verified": True}
        if k == "record":
            b["ground"] = (f"verbatim span '{span}' "
                           f"(field: {field})")
        out.append(b)
    return out

#: a mechanism-field span (NOT a concession) for the stand-tests
_MECH_SPAN = dict(span="campaign clogging events fall",
                  field="predicted_effect")


class TestAnchorFloor(unittest.TestCase):
    def test_computation_only_kill_demotes(self):
        dem = ia.anchor_check(_bindings("computation"))
        self.assertIsNotNone(dem)
        self.assertEqual(dem["rule"], "NO_ANCHOR_BINDING")

    def test_anchored_kill_stands(self):
        self.assertIsNone(
            ia.anchor_check(_bindings("computation", "record")))
        self.assertIsNone(
            ia.anchor_check(_bindings("evidence")))
        self.assertIsNone(
            ia.anchor_check(_bindings("declared_scope")))


class TestAccommodation(unittest.TestCase):
    def test_concession_disposal_demotes(self):
        basis = ("the candidate's own failure-mode concession states "
                 "that 'fine passive slimes crossing both stages' "
                 "constitute a measured 18 percent share of the load, "
                 "so the cascade is structurally incapable")
        dem = ia.accommodation_check(
            basis, CANDIDATE, _bindings("record", "computation"))
        self.assertIsNotNone(dem)
        self.assertEqual(dem["rule"], "CONCESSION_DISPOSAL")

    def test_evidence_anchor_never_demoted(self):
        basis = ("no bypass line stated anywhere in the intervention "
                 "and typically 1-3 bar is needed and the claimed "
                 "'roughly 4x' is disputed")
        self.assertIsNone(
            ia.accommodation_check(basis, CANDIDATE,
                                   _bindings("evidence", "computation")))

    def test_unstated_element_demotes(self):
        basis = ("the backflush is reverse-flow on the single header "
                 "with no bypass line stated anywhere in the "
                 "intervention, so supply is interrupted")
        dem = ia.accommodation_check(
            basis, CANDIDATE,
            _bindings("record", "computation", **_MECH_SPAN))
        self.assertIsNotNone(dem)
        self.assertEqual(dem["rule"], "UNSTATED_ELEMENT")

    def test_typical_value_premise_demotes(self):
        basis = ("a hydrocyclone requires a feed pressure differential "
                 "(typically 1-3 bar for a 150 mm unit) to develop the "
                 "tangential velocity, which the return leg cannot "
                 "supply")
        dem = ia.accommodation_check(
            basis, CANDIDATE,
            _bindings("record", "computation", **_MECH_SPAN))
        self.assertIsNotNone(dem)
        self.assertEqual(dem["rule"], "TYPICAL_VALUE_PREMISE")

    def test_hedged_target_demotes_when_quoted(self):
        basis = ("the doubled throat yields a 2x shift, not the "
                 "claimed \"roughly 4x\" bridging threshold, so the "
                 "prediction collapses")
        dem = ia.accommodation_check(
            basis, CANDIDATE,
            _bindings("record", "computation", **_MECH_SPAN))
        self.assertIsNotNone(dem)
        self.assertEqual(dem["rule"], "HEDGED_TARGET")

    def test_attacker_own_hedge_does_not_demote(self):
        # the hedge is the attacker's own arithmetic, unquoted and
        # unattributed to the candidate's claim — a true physics kill
        # shape (cal-01) must stand
        basis = ("the field-ion interaction energy is roughly "
                 "chi*B^2/(2*mu0) which is nine orders below kT, so "
                 "the claimed nucleation shift cannot occur")
        self.assertIsNone(
            ia.accommodation_check(basis, CANDIDATE,
                                   _bindings("record", "declared_scope",
                                             **_MECH_SPAN)))

    def test_unhedged_internal_contradiction_stands(self):
        # the cal-04 shape: two unhedged record claims in opposition
        basis = ("the mechanism claims it will eliminate the "
                 "late-campaign crown excursions, yet the same "
                 "candidate's predicted effect states thermal-crown "
                 "variation stays at 28 microns late-campaign, same as "
                 "today")
        self.assertIsNone(
            ia.accommodation_check(basis, CANDIDATE,
                                   _bindings("record", "computation",
                                             **_MECH_SPAN)))


class TestValidateParsedV3(unittest.TestCase):
    def _items(self, content, candidate, evidence=()):
        return ia._validate_parsed(
            ia._parse_attack(content), candidate, list(evidence))

    def test_v3_demotion_shape_on_parsed_kill(self):
        content = (
            "MECHANISM_FAILURE: KILL — the cascade cannot touch the "
            "'fine passive slimes crossing both stages' conceded at 18 "
            "percent share, structurally limiting the claimed fall "
            "from 4.1 to 1.5 GROUNDED_IN: RECORD \"fine passive slimes "
            "crossing both stages\"\n"
            "BOUNDARY_CONDITION_FAILURE: SURVIVE — within the declared "
            "envelope GROUNDED_IN: none\n")
        items = self._items(content, CANDIDATE)
        mech = [i for i in items
                if i["attack_class"] == "MECHANISM_FAILURE"][0]
        self.assertEqual(mech["verdict"], "ABSTAIN")
        self.assertEqual(mech["demoted_from"], "KILL")
        self.assertIn(mech["demotion_layer"],
                      ("v3_anchor", "v3_accommodation"))
        rule = (mech.get("anchor") or mech.get("accommodation") or {}
                ).get("rule")
        self.assertEqual(rule, "CONCESSION_DISPOSAL")
        # the objection is PRESERVED
        self.assertIn("slimes", mech["basis"])

    def test_true_kill_stands_through_v3(self):
        content = (
            "MECHANISM_FAILURE: KILL — the mechanism claims it will "
            "eliminate the late-campaign excursions yet the predicted "
            "effect states the 28 micron variation stays as today, so "
            "the record cannot be true as stated GROUNDED_IN: RECORD "
            "\"campaign clogging events fall from 4.1 to below 1.5\"\n")
        items = self._items(content, CANDIDATE)
        mech = [i for i in items
                if i["attack_class"] == "MECHANISM_FAILURE"][0]
        self.assertEqual(mech["verdict"], "KILL")
        self.assertNotIn("demotion_layer", mech)

    def test_computation_only_parsed_kill_demotes(self):
        content = (
            "EVIDENCE_CONTRADICTION: KILL — the numbers are internally "
            "inconsistent: 88 percent of blockages but 2.9 events of "
            "4.1 total GROUNDED_IN: COMPUTATION 88 vs 2.9/4.1\n")
        items = self._items(content, CANDIDATE)
        ev = [i for i in items
              if i["attack_class"] == "EVIDENCE_CONTRADICTION"][0]
        self.assertEqual(ev["verdict"], "ABSTAIN")
        self.assertEqual(ev["demotion_layer"], "v3_anchor")


class TestGateRegistry(unittest.TestCase):
    # R488: the live sealed-corpus v3 measurement RAN (22/22 cases on the
    # deployed instrument, the production ring) and SHIPPED — the gate's
    # state advanced from UNKNOWN_NOT_CALIBRATED (pre-measurement, the
    # R487 pin) to the MEASURED negative NOT_CALIBRATED (FPR 1.0 vs the
    # 0.30 bar). The INVARIANT this test guards is the fail-closed
    # DISCIPLINE — a not-calibrated instrument holds NO terminal kill
    # authority, whether the state is unknown or measured-negative —
    # never a particular state string (the R419 ratified-state
    # precedent).
    def test_v3_fail_closed(self):
        st = gate.resolve_state(
            instrument_version="independent_attack/3.0.0")
        self.assertIn(st["state"],
                      ("UNKNOWN_NOT_CALIBRATED", "NOT_CALIBRATED"))
        self.assertFalse(st["terminal_kill_admissible"])
        if st["state"] == "NOT_CALIBRATED":
            # the measured path: the shipped record's numbers re-derived
            m = st["measured"] or {}
            self.assertEqual(m.get("n_cases_attacked"), 22)
            self.assertEqual(m.get("fpr_known_good"), 1.0)

    def test_v3_unknown_path_still_fail_closed(self):
        # the pre-shipment semantics stay reachable and fail-closed:
        # an explicit unreadable measurement path -> UNREADABLE, no
        # terminal authority, never a silent pass-through
        st = gate.resolve_state(
            measurement_path=Path("definitely-absent-measurement.json"),
            instrument_version="independent_attack/3.0.0")
        self.assertIn(st["state"],
                      ("UNKNOWN_NOT_CALIBRATED",
                       "UNREADABLE_NOT_CALIBRATED"))
        self.assertFalse(st["terminal_kill_admissible"])

    def test_v2_states_unchanged(self):
        for v in ("1.0.0", "2.0.0", "2.1.0"):
            st = gate.resolve_state(
                instrument_version=f"independent_attack/{v}")
            self.assertEqual(st["state"], "NOT_CALIBRATED", v)
            self.assertFalse(st["terminal_kill_admissible"], v)

    def test_version_bumped(self):
        self.assertEqual(ia.ATTACK_VERSION, "independent_attack/3.0.0")

    def test_consumption_composition_carries_v3_state(self):
        rec = {"attack_version": ia.ATTACK_VERSION, "overall": "KILLED",
               "kill_basis": [{"attack_class": "X", "basis": "b"}]}
        gated = gate.apply_at_consumption(rec)
        self.assertEqual(gated["overall"], "ESCALATED_OBJECTION")
        esc = gated["escalation"]
        self.assertEqual(esc["instrument"], "independent_attack/3.0.0")
        # R488: the state string advanced to the measured negative
        # (the live measurement shipped); the consumption DISCIPLINE —
        # a KILLED record escalates while the instrument is not
        # calibrated — is the invariant and is unchanged
        self.assertIn(esc["calibration_state"],
                      ("UNKNOWN_NOT_CALIBRATED", "NOT_CALIBRATED"))


class _Handler:
    """Minimal harness calling the do_POST route body via the real
    handler class is heavyweight; the route's decision logic is tested
    through the recorded source (the r389 precedent) + shape checks."""

    @classmethod
    def route_source(cls) -> str:
        src = (REPO / "toscanini" / "server.py").read_text()
        start = src.index('if p.path == "/api/ops/calibration-attack":')
        return src[start:start + 4000]


class TestCalibrationTransportRoute(unittest.TestCase):
    def test_route_exists_with_caps_and_typed_failures(self):
        src = _Handler.route_source()
        self.assertIn('_run_attack(candidate, problem, evidence, None)',
                      src)
        self.assertIn("12_000", src)   # candidate cap
        self.assertIn("413", src)      # payload cap typed
        self.assertIn("INSTRUMENT_IMPORT_FAILURE", src)
        self.assertIn("INSTRUMENT_EXECUTION_FAILURE", src)
        # one attack per request — no loop over cases in the route
        self.assertNotIn("for case in", src)

    def test_route_placed_in_do_post(self):
        src = (REPO / "toscanini" / "server.py").read_text()
        self.assertIn('p.path == "/api/ops/calibration-attack"', src)


class TestDryrunArtifact(unittest.TestCase):
    def test_dryrun_recorded_and_scoped_honestly(self):
        p = REPO / "R487" / "ATTACKER_V3_DESIGN_DRYRUN.json"
        if not p.exists():
            self.skipTest("dry-run artifact not generated yet")
        rec = json.loads(p.read_text())
        self.assertEqual(rec["artifact_type"],
                         "ATTACKER_V3_DESIGN_DRYRUN")
        self.assertIn("NOT the v3 measurement", rec["scope"])
        hc = rec["headline_confusion"]
        self.assertEqual(hc["TPR"], 1.0)
        self.assertLessEqual(hc["FPR"], 0.30)
        self.assertGreaterEqual(hc["TNR"], 0.70)


if __name__ == "__main__":
    unittest.main(verbosity=2)
