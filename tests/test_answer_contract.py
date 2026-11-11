"""Answer-shape contract tests (R3): predictor-design and
intervention-proposal contracts are deterministic and routed by
question_type."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine.answer_contract import validate_answer

PREDICTOR_GOOD = (
    "Track bearing vibration RMS on the predictor envelope. "
    "INDICATOR: bearing vibration RMS band excess. "
    "THRESHOLD: RMS > 4.5 mm/s with units (ISO 10816-3); baseline 2.1 mm/s. "
    "PROTOCOL: n=12 machines, 90 days; pass if RMS band excess rises above "
    "threshold 3 consecutive shifts before a maintenance-needed flag; fail "
    "otherwise. Falsify if flag fires after maintenance."
)
PREDICTOR_BAD = (
    "Use machine learning to detect anomalies in bearing signals. "
    "The system will learn normal operation and alert when anomalies occur."
)
INTERVENTION_GOOD = (
    "Change seal compound to HNR with 5.8 pphr curing agent. "
    "PARAMETER: seal glass fraction — 0.15 — ASSUMPTION. "
    "PARAMETER: cycle count — 500 cycles — EVIDENCE-BACKED. "
    "Test in a thermal-cycling rig per the record; falsify if OCV < 1.0 V "
    "after 500 cycles."
)
INTERVENTION_BAD = (
    "Use better seal materials and improve design."
)


def test_predictor_contract_accepts_complete_answer():
    # evidence-sourced threshold (packet contains the ISO 10816-3 band
    # 4.5 mm/s) — one of the three honest bases (owner directive 2026-11-11)
    pkt = [{"id": "iso10816-3", "abstract":
            "velocity criterion for machine group 1: 4.5 mm/s RMS alarm",
            "title": "ISO 10816-3"}]
    res = validate_answer(PREDICTOR_GOOD, "predictor-design", packet=pkt)
    assert res["valid"] is True, res["violations"]
    assert res["bindings"]["threshold_basis"] == "packet_or_user_variable"


def test_predictor_threshold_assumption_basis():
    # R6 owner directive: an ASSUMPTION-labeled threshold number is a
    # valid basis even with NO packet at all
    ans = ("INDICATOR: bearing vibration RMS band excess. "
           "THRESHOLD: RMS 4.5 mm/s — ASSUMPTION (engineering alert level). "
           "PROTOCOL: n=12 machines, 90 days; pass if RMS band excess "
           "rises above threshold 3 consecutive shifts; fail otherwise.")
    res = validate_answer(ans, "predictor-design", packet=[])
    assert res["valid"] is True, res["violations"]
    assert res["bindings"]["threshold_basis"] == "assumption"


def test_predictor_threshold_calibration_rule_basis():
    # R6 owner directive: a defined calibration rule (baseline + k sigma
    # from N days of healthy data) is a valid basis — no packet needed
    ans = ("INDICATOR: chiller approach temperature rise. "
           "THRESHOLD: alert when approach temperature exceeds baseline "
           "+ 3 sigma, computed from 14 days of sampled chiller "
           "telemetry. "
           "PROTOCOL: n=6 chillers, 120 days; pass if the approach "
           "temperature alert fires before the condenser-fouling "
           "maintenance flag; fail otherwise.")
    res = validate_answer(ans, "predictor-design", packet=[])
    assert res["valid"] is True, res["violations"]
    assert res["bindings"]["threshold_basis"] == "calibration_rule"


def test_predictor_threshold_bare_number_rejected():
    # a bare unlabeled number with none of the three bases is the violation
    ans = ("INDICATOR: bearing vibration RMS band excess. "
           "THRESHOLD: 7.3 mm/s alert level. "
           "PROTOCOL: n=12 machines, 90 days; pass if RMS band excess "
           "rises above threshold; fail otherwise.")
    res = validate_answer(ans, "predictor-design", packet=[])
    assert res["valid"] is False
    assert any("no provenance basis" in v for v in res["violations"]), \
        res["violations"]


def test_threshold_decimal_regex_fixed():
    # R6: the (?::\.\d+)? typo — THRESHOLD: 4.5 must extract the decimal
    # "4.5", never the ":" artefact; whole numbers unchanged
    from discovery_fabric.engine.answer_contract import _threshold_number
    assert _threshold_number("THRESHOLD: 4.5 mm/s") == "4.5"
    assert _threshold_number("THRESHOLD: 12 mm/s") == "12"
    assert _threshold_number("THRESHOLD: 0.25 percent") == "0.25"
    assert _threshold_number("no marker here") is None
    # the fallback line-regex must not truncate at the letter 'n'
    # (the old [^\\n\\.] class excluded it)
    assert _threshold_number(
        "THRESHOLD: indication fraction > 2% of fleet") == "2"


def test_predictor_contract_rejects_generic_answer():
    res = validate_answer(PREDICTOR_BAD, "predictor-design")
    assert res["valid"] is False
    assert any("indicator" in v.lower() for v in res["violations"])
    assert any("threshold" in v.lower() for v in res["violations"])
    assert any("n=" in v.lower() or "n " in v.lower()
               for v in res["violations"])


def test_intervention_contract_accepts_labeled_parameters():
    # the EVIDENCE-BACKED parameter cites evidence that is present
    pkt = [{"id": "astm-seal", "abstract":
            "accelerated thermal-cycling evidence: 500 cycles, OCV 1.0 V",
            "title": "Seal compound validation"}]
    good = ("Change seal compound to HNR. "
            "PARAMETER: glass fraction — 0.15 — ASSUMPTION [astm-seal]. "
            "PARAMETER: cycle count — 500 cycles — EVIDENCE-BACKED [astm-seal]. "
            "Test in a thermal-cycling rig per the record; falsify if "
            "OCV < 1.0 V after 500 cycles.")
    res = validate_answer(good, "intervention-proposal", packet=pkt)
    assert res["valid"] is True, res["violations"]


def test_intervention_contract_rejects_unlabeled_generic_answer():
    res = validate_answer(INTERVENTION_BAD, "intervention-proposal")
    assert res["valid"] is False
    assert any("EVIDENCE-BACKED" in v or "ASSUMPTION" in v
               for v in res["violations"])


def test_unknown_type_is_rejected():
    res = validate_answer("whatever", "something-else")
    assert res["valid"] is False


PERCENT_CASE = (
    "PARAMETER: creep-rate alert — 10 percent of rated deflection — ASSUMPTION. "
    "Test in the creep rig; falsify if deflection exceeds 5-10 percent before "
    "500 cycles; accept if below threshold."
)


def test_intervention_contract_accepts_percent_and_range():
    # R5 P0-2: "10%" and ranges like "5-10 percent" must satisfy the
    # numeric-with-units floor (\b after % never matched)
    res = validate_answer(PERCENT_CASE, "intervention-proposal")
    assert res["valid"] is True, res["violations"]


def test_intervention_contract_accepts_percent_symbol():
    ans = ("PARAMETER: creep-rate alert — 10% of rated deflection — "
           "ASSUMPTION. Test in the rig; falsify if deflection exceeds "
           "5-10% before 500 cycles; accept if below threshold.")
    res = validate_answer(ans, "intervention-proposal")
    assert res["valid"] is True, res["violations"]


def test_predictor_contract_accepts_percent_threshold():
    # R6: percent thresholds still work; the number carries an honest
    # basis (ASSUMPTION) since no packet is provided here
    ans = ("INDICATOR: dropout fraction of laser diodes. "
           "THRESHOLD: dropout fraction > 2% of fleet — ASSUMPTION. "
           "PROTOCOL: n=80 devices, 180 days; pass if dropout exceeds 2% "
           "before end of service; fail otherwise.")
    res = validate_answer(ans, "predictor-design")
    assert res["valid"] is True, res["violations"]


# ---------------------------------------------------------------------------
# R6 measured follow-up (fresh-run 1, sofc): the composer's citations of
# USER-stated grounds were manufactured into violations — (a) bracket
# contents with SPACES did not match the packet-id class, and (b) a user
# citation can never be in the packet blob. User constraints/variables
# are legitimate provenance (the same principle the predictor branch
# encodes as the packet_or_user_variable threshold basis).
# ---------------------------------------------------------------------------

USER_CITE = (
    "Implement a thermal management system with active cooling. "
    "PARAMETER: activation temperature — 400°C — EVIDENCE-BACKED [doi:10.1016/j.ceramint.2012.01.043]. "
    "PARAMETER: target open-circuit voltage — 1.0 V — EVIDENCE-BACKED [user constraint]. "
    "PARAMETER: seal glass fraction — 0.15 — EVIDENCE-BACKED [user-stated clarification]. "
    "Test in a thermal-cycling rig; falsify if OCV < 1.0 V after 500 cycles."
)

PACKET_DOI_ONLY = [{"id": "ev-1", "doi": "10.1016/j.ceramint.2012.01.043",
                    "abstract": "activation temperature 400 °C for the "
                                "glass-ceramic seal; thermal cycling of "
                                "electrolyte stacks",
                    "title": "SOFC thermal cycling and seal activation"}]

USER_VARS = ["maintain OCV above 1.0 V", "seal glass fraction 0.15",
             "activation temperature 400 °C"]


def test_intervention_user_citations_accepted():
    # the user citations verify against the user's stated variables
    res = validate_answer(USER_CITE, "intervention-proposal",
                          packet=PACKET_DOI_ONLY,
                          user_variables=USER_VARS)
    assert res["valid"] is True, res["violations"]


def test_intervention_user_citation_without_packet():
    # no packet AND no user variables: a citation named "user
    # constraint" has nothing user-stated for it to bind to, so it is
    # not legitimate provenance (Art. XXV/XXVII)
    only_user = (
        "Implement a thermal management system with active cooling. "
        "PARAMETER: target open-circuit voltage — 1.0 V — "
        "EVIDENCE-BACKED [user constraint]. "
        "PARAMETER: seal glass fraction — 0.15 — "
        "EVIDENCE-BACKED [user-stated clarification]. "
        "Test in a thermal-cycling rig; falsify if OCV < 1.0 V.")
    res = validate_answer(only_user, "intervention-proposal", packet=None)
    assert res["valid"] is False
    # with the user's stated variables supplied and matching, legit
    only_user2 = validate_answer(only_user, "intervention-proposal",
                                 packet=None,
                                 user_variables=USER_VARS)
    assert only_user2["valid"] is True, only_user2["violations"]


def test_intervention_unknown_citation_still_rejected():
    # an invented bracket id that is neither a packet id nor a user
    # citation is STILL a violation (the floor is not loosened)
    bad = ("Change the seal compound. "
           "PARAMETER: cycle count — 500 cycles — EVIDENCE-BACKED [made-up-source-42]. "
           "Test in the rig; falsify if OCV < 1.0 V.")
    res = validate_answer(bad, "intervention-proposal", packet=PACKET_DOI_ONLY)
    assert res["valid"] is False
    assert any("not found in evidence packet" in v
               for v in res["violations"])


def test_intervention_missing_citation_still_rejected():
    # a bare EVIDENCE-BACKED label with NO citation anywhere nearby
    # remains a violation
    bad = ("Change the seal compound. "
           "PARAMETER: cycle count — 500 cycles — EVIDENCE-BACKED and "
           "measured per the standard. Test in the rig; falsify if "
           "OCV < 1.0 V.")
    res = validate_answer(bad, "intervention-proposal", packet=PACKET_DOI_ONLY)
    assert res["valid"] is False
    assert any("without a referenced source id" in v
               for v in res["violations"])
