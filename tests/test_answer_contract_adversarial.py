"""R6 P0-6: adversarial false-positive tests for the answer contract.

Every branch of the strengthened deterministic contract is attacked with
a fixture that would WIDE-verify under the old checks. Each must fail
the contract (typed violation, never a valid pass). The positive
controls that must stay green assert the contract is not a universal
rejector (Art. V)."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.answer_contract import validate_answer

# P0-5 amendment (disclosed): src-4 carries "over 500 cycles" so the
# all-labeled positive control's cited number actually appears in the
# cited record (joint provenance); the "500 cycles" number the labeled
# parameter claims was previously supported only by a bare number
# elsewhere in the line — the defect P0-5 targets.
PKT = [{"id": "src-4", "doi": "10.1055/src-4",
        "abstract": "glass-ceramic seal activation temperature 400 °C; "
                    "thermal cycling of electrolyte stacks at 25-800 °C "
                    "over 500 cycles",
        "title": "SOFC seal activation"},
       {"id": "src-9",
        "abstract": "refractive index of borosilicate glasses; "
                    "chromatic dispersion in the visible band",
        "title": "optical constants of glasses"}]

PKT_OPTICAL_ONLY = [{"id": "src-9",
                     "abstract": "refractive index of borosilicate glasses; "
                                 "chromatic dispersion in the visible band",
                     "title": "optical constants of glasses"}]


# --- predictor-design branch ----------------------------------------
def test_protocol_measuring_other_quantity_rejected():
    ans = ("INDICATOR: bearing vibration RMS. "
           "THRESHOLD: 4.5 mm/s — ASSUMPTION (alert level). "
           "PROTOCOL: n=12 machines; track ambient humidity for 90 days; "
           "pass if relative humidity stays below threshold; fail otherwise.")
    res = validate_answer(ans, "predictor-design", packet=PKT)
    assert res["valid"] is False
    assert any("VALIDATION PROTOCOL does not name the INDICATOR" in v
               for v in res["violations"])


def test_calibration_rule_without_window_or_method_rejected():
    ans = ("INDICATOR: bearing vibration RMS. "
           "THRESHOLD: baseline + 3 sigma from 14 days of healthy data. "
           "PROTOCOL: n=12 machines; pass if conditional RMS rises "
           "above threshold before maintenance-needed; fail otherwise.")
    res = validate_answer(ans, "predictor-design",
                          packet=PKT, user_variables=["baseline 2.1 mm/s"])
    assert res["valid"] is False
    assert any("calibration rule requires" in v and
               "measurement_method" in v for v in res["violations"])


def test_calibration_rule_defined_passes():
    ans = ("INDICATOR: bearing vibration RMS. "
           "THRESHOLD: 4.5 mm/s — baseline + 3σ measured from 21 days of "
           "healthy-fleet telemetry; sigma recalculated weekly. "
           "PROTOCOL: n=12 machines; pass if RMS rises above threshold "
           "before a maintenance-needed flag; fail otherwise.")
    res = validate_answer(ans, "predictor-design", packet=PKT,
                          user_variables=["4.5 mm/s"])
    assert res["valid"] is True, res["violations"]


def test_unbound_evidence_sourced_number_rejected():
    # a bare number with no packet, no user variable, no ASSUMPTION,
    # no calibration rule — invented provenance
    ans = ("INDICATOR: bearing vibration RMS. "
           "THRESHOLD: 987.6 mm/s with units. "
           "PROTOCOL: n=12 machines; pass if vibration rises first.")
    res = validate_answer(ans, "predictor-design", packet=PKT)
    assert res["valid"] is False
    assert any("no provenance basis" in v for v in res["violations"])


# --- intervention-proposal branch ------------------------------------
def test_one_labeled_parameter_does_not_license_unlabeled():
    ans = ("Switch the seal compound. "
           "PARAMETER: cycle count — 500 cycles — EVIDENCE-BACKED [src-4]. "
           "PARAMETER: seal glass fraction — 20 percent — picked by guess.")
    res = validate_answer(ans, "intervention-proposal", packet=PKT)
    assert res["valid"] is False
    assert any("without an EVIDENCE-BACKED or ASSUMPTION label" in v
               for v in res["violations"])


def test_all_parameters_labeled_passes():
    ans = ("Switch the seal compound. "
           "PARAMETER: cycle count — 500 cycles — EVIDENCE-BACKED [src-4]. "
           "PARAMETER: activation temperature — 400 °C — EVIDENCE-BACKED [src-4]. "
           "Test in a thermal-cycling rig; falsify if OCV falls below 1.0 V.")
    res = validate_answer(ans, "intervention-proposal", packet=PKT,
                          user_variables=["400 °C seal activation"])
    assert res["valid"] is True, res["violations"]


def test_evidence_backed_against_unrelated_source_rejected():
    ans = ("Switch the seal compound. "
           "PARAMETER: cycle count — 500 cycles — EVIDENCE-BACKED [src-9].")
    res = validate_answer(ans, "intervention-proposal",
                          packet=PKT_OPTICAL_ONLY)
    assert res["valid"] is False
    assert any("does not jointly support" in v or
               "not found in evidence packet" in v
               for v in res["violations"])


def test_user_citation_value_must_exist_in_user_variables():
    ans = ("Keep the float regime. "
           "PARAMETER: cycle count — 700 cycles — EVIDENCE-BACKED "
           "[user constraint].")
    res = validate_answer(ans, "intervention-proposal",
                          packet=PKT,
                          user_variables=["500 cycles thermal cycling"])
    assert res["valid"] is False
    assert any("does not jointly support" in v
               for v in res["violations"])


def test_user_citation_value_present_passes():
    ans = ("Keep the float regime. "
           "PARAMETER: cycle count — 500 cycles — EVIDENCE-BACKED "
           "[user constraint]. "
           "Test in a thermal-cycling rig; falsify if OCV falls below 1.0 V after 500 cycles.")
    res = validate_answer(ans, "intervention-proposal",
                          packet=None,
                          user_variables=["500 cycles thermal cycling"])
    assert res["valid"] is True, res["violations"]
