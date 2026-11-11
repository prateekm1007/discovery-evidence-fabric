"""P0-5 (owner directive 2026-11-11, item 5): claim-level provenance.

Every quantitative claim of an EVIDENCE-BACKED parameter is checked
JOINTLY — quantity + value + unit — against the exact supporting span
(the cited packet record, or the specific user-variable /
clarification entry that carries it). A number appearing elsewhere in
the source is NOT support. The five adversarial classes (each a typed
violation, never a silent pass):

  1. same_number_wrong_quantity — the value is in the span, the span
     never ties it to the claim's quantity;
  2. wrong_unit                 — value + quantity present, the
     claim's unit absent;
  3. unrelated_source           — neither number nor quantity in the
     cited span;
  4. substring_number           — the claim's number only as the head
     of a longer number in the span;
  5. value_not_in_source        — the span names the quantity but not
     this value (user entries: no single entry carries both — a value
     in entry A is not support for a quantity entry A never names).

Recorded conversions / derivations are admitted and recorded
(bindings["claims"][i].conversion_recorded); ASSUMPTION parameters
stay available. The predictor's packet_or_user_variable threshold
basis was tightened the same way: value + unit must co-occur in the
packet/user blob — a bare number elsewhere is unknown.

The clarification text travels into validate_answer on BOTH compose
paths (compose + repair) — asserted by spying the module-level
validate_answer inside compose_answer.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.answer_contract import validate_answer

# the cited records (exact spans the claims bind to)
PACKET = [
    {"id": "rec-a",
     "abstract": "float voltage 2.27 V per cell; charge current 10 A; "
                 "shelf life 15 years",
     "title": "battery float regime"},
    {"id": "rec-b",
     "abstract": "bearing vibration RMS 4.5 mm/s; rotation speed "
                 "4000 rpm",
     "title": "vibration baseline"},
    {"id": "rec-d",
     "abstract": "charge current 750 mA; battery energy 1.2 Wh",
     "title": "charge profile"},
]


def _cls(violations, cls):
    hits = [v for v in violations
            if f"does not jointly support its parameter ({cls})" in v]
    assert hits, (cls, violations)
    return True


# ---------------------------------------------------------------------
# 1. same_number_wrong_quantity — the value belongs to another
#    quantity in the span
# ---------------------------------------------------------------------
def test_same_number_wrong_quantity_rejected():
    ans = ("PARAMETER: charge voltage — 10 V — EVIDENCE-BACKED [rec-a]. "
           "Test in the charge rig; falsify if the cell fails.")
    # rec-a carries 10 A (a current) and 2.27 V (a different value):
    # the number 10 is in the record but never tied to the charge
    # voltage
    res = validate_answer(ans, "intervention-proposal", packet=PACKET)
    assert res["valid"] is False
    _cls(res["violations"], "same_number_wrong_quantity")


# ---------------------------------------------------------------------
# 2. wrong_unit — value + quantity present, the claim's unit absent
# ---------------------------------------------------------------------
def test_wrong_unit_rejected():
    ans = ("PARAMETER: rotation speed — 4000 cycles — EVIDENCE-BACKED "
           "[rec-b]. "
           "Test in the rig; falsify if vibration rises.")
    # rec-b names the speed 4000 rpm — not "4000 cycles"
    res = validate_answer(ans, "intervention-proposal", packet=PACKET)
    assert res["valid"] is False
    _cls(res["violations"], "wrong_unit")


# ---------------------------------------------------------------------
# 3. unrelated source — neither number nor quantity in the cited span
# ---------------------------------------------------------------------
def test_unrelated_source_rejected():
    ans = ("PARAMETER: seal thickness — 512 µm — EVIDENCE-BACKED "
           "[rec-b]. "
           "Test in the rig; falsify if delamination occurs.")
    res = validate_answer(ans, "intervention-proposal", packet=PACKET)
    assert res["valid"] is False
    _cls(res["violations"], "unrelated_source")


# ---------------------------------------------------------------------
# 4. substring number — 400 only as the head of 4000 in the span
# ---------------------------------------------------------------------
def test_substring_number_rejected():
    ans = ("PARAMETER: rotation speed — 400 rpm — EVIDENCE-BACKED "
           "[rec-b]. "
           "Test in the rig; falsify if vibration rises.")
    res = validate_answer(ans, "intervention-proposal", packet=PACKET)
    assert res["valid"] is False
    _cls(res["violations"], "substring_number")


# ---------------------------------------------------------------------
# 5. value not in the span / no single user entry carries both
# ---------------------------------------------------------------------
def test_value_not_in_source_rejected():
    ans = ("PARAMETER: shelf life — 20 years — EVIDENCE-BACKED "
           "[rec-a]. "
           "Test in the rig; falsify if capacity fades early.")
    # rec-a names the shelf life (15 years) but not 20
    res = validate_answer(ans, "intervention-proposal", packet=PACKET)
    assert res["valid"] is False
    _cls(res["violations"], "value_not_in_source")


def test_user_entry_cross_citation_rejected():
    # the value lives in entry 1, the quantity in entry 2: no single
    # entry that names the quantity carries the value — not support
    ans = ("PARAMETER: shelf life — 10 years — EVIDENCE-BACKED "
           "[user variables]. "
           "Test in the rig; falsify if capacity fades early.")
    res = validate_answer(ans, "intervention-proposal", packet=None,
                          user_variables=["charge current 10 A",
                                         "shelf life 20 years"])
    assert res["valid"] is False
    _cls(res["violations"], "value_not_in_source")


def test_user_citation_without_user_entries_typed():
    ans = ("PARAMETER: shelf life — 15 years — EVIDENCE-BACKED "
           "[user constraint]. "
           "Test in the rig; falsify if capacity fades early.")
    res = validate_answer(ans, "intervention-proposal", packet=None)
    assert res["valid"] is False
    assert any("has no user-stated variable or clarification to "
               "bind to" in v for v in res["violations"])


# ---------------------------------------------------------------------
# recorded conversion / derivation — admitted and recorded
# ---------------------------------------------------------------------
def test_recorded_conversion_admitted_and_recorded():
    ans = ("PARAMETER: charge rate — 0.75 A (derived from the 750 mA "
           "charge current in the record) — EVIDENCE-BACKED [rec-d]. "
           "Test in the charge rig; falsify if capacity fades early.")
    res = validate_answer(ans, "intervention-proposal", packet=PACKET)
    assert res["valid"] is True, res["violations"]
    claims = res["bindings"]["claims"]
    eb = [c for c in claims if c["label"] == "evidence-backed"]
    assert eb, claims
    assert eb[0]["conversion_recorded"] is True
    assert eb[0]["source_kind"] == "packet_record"
    assert eb[0]["cited"] == "[rec-d]"


# ---------------------------------------------------------------------
# ASSUMPTION stays available — the honest unverified base is not a
# manufactured evidence claim
# ---------------------------------------------------------------------
def test_assumption_parameter_stays_admissible():
    ans = ("PARAMETER: settling time — 12 s — ASSUMPTION. "
           "Test in the rig; falsify if oscillation persists.")
    res = validate_answer(ans, "intervention-proposal", packet=PACKET)
    assert res["valid"] is True, res["violations"]
    asg = [c for c in res["bindings"]["claims"]
           if c["label"] == "assumption"]
    assert asg and asg[0]["cited"] is None


# ---------------------------------------------------------------------
# bindings["claims"] — the provenance record the judge can read
# ---------------------------------------------------------------------
def test_claims_recorded_for_admitted_bindings():
    ans = ("PARAMETER: charge current — 10 A — EVIDENCE-BACKED [rec-a]. "
           "PARAMETER: glass fraction — 0.15 — ASSUMPTION. "
           "Test in the rig; falsify if it fails.")
    res = validate_answer(ans, "intervention-proposal", packet=PACKET)
    assert res["valid"] is True, res["violations"]
    eb = [c for c in res["bindings"]["claims"]
          if c["label"] == "evidence-backed"]
    assert len(eb) == 1
    assert eb[0]["source_kind"] == "packet_record"
    assert eb[0]["conversion_recorded"] is False
    assert {"value": "10", "unit": "a"} in eb[0]["pairs"]
    assert res["bindings"]["claims"][0]["quantity"]


def test_clarification_entry_is_a_user_entry_with_index():
    # the clarification text is an entry of its own (last); a claim
    # that only the clarification carries binds to it with the entry
    # index recorded. Entry 0 (the user variable) names a quantity
    # word of the claim ("charge") but never its value+unit, so it
    # must not win the binding.
    ans = ("PARAMETER: charge voltage — 12.2 V — EVIDENCE-BACKED "
           "[user-stated clarification]. "
           "Test in the rig; falsify if capacity fades early.")
    res = validate_answer(ans, "intervention-proposal", packet=None,
                          user_variables=["charge current 10 A"],
                          clarification="charge voltage 12.2 V at 25 °C")
    assert res["valid"] is True, res["violations"]
    eb = [c for c in res["bindings"]["claims"]
          if c["label"] == "evidence-backed"]
    assert eb[0]["source_kind"] == "user_entry"
    assert eb[0]["entry_index"] == 1  # entry 0 = the user variable


# ---------------------------------------------------------------------
# predictor branch: the packet_or_user_variable basis requires
# value + unit CO-OCCURRENCE in the blob (a bare number elsewhere is
# unknown, never a manufactured basis)
# ---------------------------------------------------------------------
_PDT = ("INDICATOR: bearing vibration RMS band excess. "
        "THRESHOLD: RMS 4.5 mm/s alert level. "
        "PROTOCOL: n=12 machines; pass if RMS band excess rises above "
        "threshold; fail otherwise.")


def test_predictor_bare_number_elsewhere_is_unknown():
    # 4.5 occurs in the blob (as kW and as a Hz number) but never as
    # "4.5 mm/s" — no co-occurrence, no basis
    pkt = [{"id": "iso", "abstract":
             "motor input 4.5 kW at 4.5 Hz; vibration criterion",
            "title": "machine baseline"}]
    res = validate_answer(_PDT, "predictor-design", packet=pkt)
    assert res["valid"] is False, res["violations"]
    assert res["bindings"]["threshold_basis"] == "unknown"
    assert any("no provenance basis" in v for v in res["violations"])


def test_predictor_cooccurrence_passes():
    pkt = [{"id": "iso", "abstract":
             "vibration criterion for machine group 1: 4.5 mm/s RMS "
             "alarm",
            "title": "ISO 10816-3"}]
    res = validate_answer(_PDT, "predictor-design", packet=pkt)
    assert res["valid"] is True, res["violations"]
    assert res["bindings"]["threshold_basis"] == "packet_or_user_variable"


# ---------------------------------------------------------------------
# the composer passes the clarification into validate_answer on BOTH
# paths (compose + repair)
# ---------------------------------------------------------------------
def test_composer_passes_clarification_on_both_paths(monkeypatch):
    import discovery_fabric.engine.answer_contract as ac
    calls = {"n": 0}
    orig = ac.validate_answer

    def spy_validate(answer, question_type, packet=None,
                     user_variables=None, clarification=None):
        calls["n"] += 1
        calls[f"clarification_{calls['n']}"] = clarification
        return orig(answer, question_type, packet=packet,
                    user_variables=user_variables,
                    clarification=clarification)
    monkeypatch.setattr(ac, "validate_answer", spy_validate)

    from discovery_fabric.engine.answer_composer import compose_answer
    problem = {"device": "lead-acid float battery bank",
               "failure": "grid corrosion creep",
               "failure_mode": "corrosion",
               "question_type": "intervention-proposal",
               "user_variables": ["maintain 350 kW duty"],
               "clarification_text": "float at 2.27 V per cell"}
    good = ("PARAMETER: float voltage — 2.27 V per cell — "
            "EVIDENCE-BACKED [user-stated clarification]. "
            "Test in the float rig; falsify if corrosion grows faster.")
    bad = ("PARAMETER: float voltage — 2.27 V per cell — "
           "EVIDENCE-BACKED [user-stated clarification]. "
           "It will be fine.")

    def factory(responses):
        n = {"i": 0}

        def llm(prompt, system="", timeout=240, max_tokens=700,
                purpose="", **kw):
            r = responses[min(n["i"], len(responses) - 1)]
            n["i"] += 1
            return {"ok": True, "content": r, "prompt_hash": "p" * 8,
                    "output_hash": "o" * 8}
        return llm

    # first pass valid: ONE call, clarification rides in
    rec = compose_answer(problem, [], [], None, "intervention-proposal",
                        llm_generate=factory([good]))
    assert rec["state"] == "COMPOSED_CONTRACT_VALID", rec
    assert calls["clarification_1"] == "float at 2.27 V per cell"

    # first pass violates (no test/measure named): repair also rides
    # the clarification
    calls["n"] = 0
    for k in list(calls):
        if k.startswith("clarification_"):
            del calls[k]
    rec = compose_answer(problem, [], [], None, "intervention-proposal",
                        llm_generate=factory([bad, good]))
    assert rec["state"] == "COMPOSED_CONTRACT_VALID", rec
    assert calls["clarification_1"] == "float at 2.27 V per cell"
    assert calls["clarification_2"] == "float at 2.27 V per cell"
