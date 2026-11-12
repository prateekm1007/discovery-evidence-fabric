"""tests/test_r6_audit_round_clean_output.py — regression pins for the
OWNER AUDIT ROUND 2026-11-12 directives, grounded in the AUDITED
composer-era pair data (eval/pairs/dev12_fresh/, af7e2a03f):

  DIRECTIVE 1 — CLEAN OUTPUT: no internal state names or pipeline-
      history narration in the answer text; one plain-language caveat
      line at most; compose -> validate -> repair until valid; a
      contract-invalid composition is NEVER delivered (the auditor saw
      "CONTRACT-INVALID COMPOSITION (...)" banners shipped in 4 of 9
      pairs).
  DIRECTIVE 2 — CONSTRAINT-COMPLIANCE AUDIT in the repair step: each
      user constraint enumerated; the proposal's inputs/measurements/
      dimensions inside the allowed set; the proposal CHANGES
      something (no restating). Audited regressions: fu-004 (pressure
      setpoint outside the temperature+flow allowlist), new04
      ("saturated condensing temperature" is not a listed BMS point),
      new01 (user constraints listed as the design parameters), sofc
      (recommends the anode-supported cell the device already is).
  DIRECTIVE 3 — gimmick-anchor rejection: the mechanism-to-failure
      link check rejects candidates whose anchor record never carries
      the failure phenomenon (fu-004 tanh, fu-003 magnetic sensor,
      p02 graphene-polyaniline binder anchored to a porous-electrode
      simulation paper, new04 wavelet+RF anchored to an atmospheric
      water-harvesting buoy paper).
  DIRECTIVE 4 — USE THE STATED VARIABLE: the sofc 0.15 intergranular
      glass phase fraction must appear in the design, not only as a
      constraint echo; a dict-valued clarification_answer reaches the
      composer context.
  DIRECTIVE 6 — kill records + hypothesis delivery: where every kill's
      typed cause is KILL_CAUSE_NOT_IN_RECORD (p09, fu-005), the
      record-bound candidate is admissible as a flagged UNVERIFIED
      hypothesis instead of a typed no-answer; a scientific kill
      (new07's physics-invalid mechanism) keeps the kill.

Hermetic: zero LLM calls, zero network, zero credentials.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from discovery_fabric.engine.answer_contract import (  # noqa: E402
    validate_answer, internal_narration_tokens)
from discovery_fabric.engine.constraint_audit import (  # noqa: E402
    audit_constraints, allowed_measurements)
from discovery_fabric.engine.mechanism_link import (  # noqa: E402
    mechanism_to_failure_link_check, kill_cause_record,
    KILL_CAUSE_NOT_IN_RECORD, KILL_CAUSE_SCIENTIFIC)
from discovery_fabric.engine.answer_composer import (  # noqa: E402
    compose_if_admissible, MAX_REPAIR_ROUNDS,
    HYPOTHESIS_CAVEAT_LINE)

# ---------------------------------------------------------------------
# fixtures from the audited problems (eval/problems_dev12.json)
# ---------------------------------------------------------------------
FU004 = {
    "problem_id": "dev-fu-004-fouling",
    "device": "shell-and-tube condenser on a steam turbine exhaust, "
              "300 MW unit",
    "failure": "tube-side biofouling accumulates over weeks; heat "
               "transfer degrades causing turbine back-pressure rise "
               "and derating",
    "failure_mode": "biofouling",
    "constraint": "predictor must use existing temperature and flow "
                  "measurements only, fire at least 3 weeks before "
                  "back-pressure hits the derating limit, no "
                  "requirement for new instrumentation",
    "user_variables": ["existing instrumentation only",
                       "at least 3 weeks before derating",
                       "no false trips during load swings"],
    "question_type": "predictor-design",
}

NEW04 = {
    "problem_id": "eval-new04-chiller-fouling-predictor",
    "device": "water-cooled centrifugal chiller condenser tube bank in "
              "a district cooling plant using an open cooling tower "
              "loop",
    "failure": "Condenser tube fouling accumulates silently: the "
               "fouling layer raises condenser approach temperature "
               "and pressure schedules, but operators clean on a "
               "fixed monthly cadence",
    "failure_mode": "condenser-fouling",
    "constraint": "the predictor must use only BMS points already "
                  "logged (chilled water supply/return temperature, "
                  "condenser water supply/return temperature, "
                  "compressor power, pump speed, outdoor wet-bulb), "
                  "must resolve fouling state changes within 3 days "
                  "at full load, and must produce a cleaning trigger "
                  "that reduces total compressor energy by at least 3 "
                  "percent versus the fixed monthly cadence",
    "user_variables": ["BMS points already logged (listed in "
                       "constraint)",
                       "fouling state resolved within 3 days at full "
                       "load",
                       "at least 3 percent compressor energy reduction "
                       "vs the fixed monthly cadence"],
    "question_type": "predictor-design",
}

NEW01 = {
    "problem_id": "eval-new01-supercap-dryout",
    "device": "electric double-layer supercapacitor module in an "
              "automotive under-hood 12 V stop-start system",
    "failure": "Electrolyte dry-out: sustained operation at high "
               "temperature drives solvent evaporation and seal "
               "permeation, collapsing the effective ion transport",
    "failure_mode": "electrolyte-dryout",
    "constraint": "keep capacitance loss below 10 percent over a "
                  "10-year life at up to 2.7 V rated cell voltage and "
                  "65 C maximum ambient, without adding more than "
                  "1 mm of module height",
    "user_variables": ["10-year life target", "2.7 V rated cell "
                       "voltage", "65 C maximum ambient",
                       "capacitance loss below 10 percent",
                       "no more than 1 mm added module height"],
    "question_type": "intervention-proposal",
}

SOFC = {
    "problem_id": "eval-sofc-thermal-cycling",
    "device": "anode-supported solid oxide fuel cell stack with a "
              "yttria-stabilized zirconia electrolyte and a lanthanum "
              "strontium manganite cathode",
    "failure": "Thermal cycling between 25 C and 800 C during "
               "start/stop drives differential expansion between the "
               "electrolyte, the anode, and the glass-ceramic seal; "
               "repeated cycles open microcracks in the seal",
    "failure_mode": "thermal-cycling-fatigue",
    "constraint": "survive 500 thermal cycles from 25 C to 800 C at "
                  "5 C/min heating rate while holding open-circuit "
                  "voltage above 1.0 V and keeping seal leakage below "
                  "1 percent of fuel flow, without increasing stack "
                  "mass above 2 percent",
    "user_variables": ["500 thermal cycles from 25 C to 800 C",
                       "5 C/min heating rate",
                       "open-circuit voltage above 1.0 V",
                       "seal leakage below 1 percent of fuel flow",
                       "stack mass increase below 2 percent"],
    "question_type": "intervention-proposal",
    "clarification_answer": {
        "intergranular glass phase fraction": 0.15,
        "note": "user stated the seal's intergranular glass phase "
                "fraction is 0.15 (mass fraction) for this stack "
                "design"},
}


# =====================================================================
# DIRECTIVE 1 — clean output
# =====================================================================

class TestCleanOutput:
    def test_audited_jargon_tokens_fail_the_contract(self):
        # every jargon line the auditor saw shipped must now FAIL the
        # deterministic contract (clean-output rule) — repaired, never
        # shipped
        audited_lines = [
            "CONTRACT-INVALID COMPOSITION (deterministic answer-shape "
            "contract violations: intervention contract: ...)",
            "THERE ARE NO SURVIVING INTERVENTION CANDIDATES — ALL "
            "KILLED. PRESENTING BEST UNVERIFIED HYPOTHESIS.",
            "No surviving intervention candidates exist in the "
            "provided pipeline data that satisfy the deterministic "
            "evidence contract. The previous attempt relied on "
            "sources that failed verification.",
            "This candidate survived the verification gate as an "
            "AUTOMATED_INVENTION_CANDIDATE with a coherent premise.",
            "The key innovation from the top candidate [cand:A2] is "
            "the use of tanh modulation.",
        ]
        for txt in audited_lines:
            hits = internal_narration_tokens(txt)
            assert hits, f"jargon not caught: {txt!r}"
            rec = validate_answer(
                "INDICATOR: x 4.5 mm/s — ASSUMPTION\nTHRESHOLD: 4.5 "
                "mm/s — ASSUMPTION\nPROTOCOL: n=6 drives.\n" + txt,
                "predictor-design")
            assert rec["valid"] is False
            assert any(v.startswith("clean-output contract:")
                       for v in rec["violations"]), (txt, rec["violations"])

    def test_clean_answer_passes_the_hygiene_rule(self):
        txt = ("Recommend a vibration-based predictor for the "
               "fan-drive bearing.\nINDICATOR: bearing vibration RMS\n"
               "THRESHOLD: 4.5 mm/s — ASSUMPTION\nPROTOCOL: n=6 fan "
               "drives monitored 180 days by vibration RMS logging; "
               "pass if the alert fires before visible spalling.")
        assert internal_narration_tokens(txt) == []
        rec = validate_answer(txt, "predictor-design")
        assert rec["valid"] is True, rec["violations"]

    def test_contract_invalid_never_delivered(self):
        # AMENDED R6 auditor round 2026-11-12 (owner directive 2,
        # DOWNGRADE DON'T DISCARD): the composer now runs the
        # deterministic downgrade on EVERY contract-invalid
        # composition, so the state "COMPOSED_CONTRACT_INVALID" is
        # never emitted by the current engine — the delivered classes
        # are COMPOSED_CONTRACT_VALID / COMPOSED_CONTRACT_DOWNGRADED /
        # COMPOSED_TRUNCATED_DELIVERED, and a typed no-answer is
        # reserved for scientific refusals + transport failure. The
        # legacy state (pre-downgrade records only) reads back as the
        # typed label naming the actual delivery, never silently
        # blank; the downgraded + truncated classes DELIVER with the
        # one plain caveat (Art. XXV: the reader matches the
        # composer's state machine, it does not rewrite history).
        import eval.run as er
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "run"
            d.mkdir()
            (d / "ANSWER_COMPOSED.json").write_text(json.dumps({
                "state": "COMPOSED_CONTRACT_INVALID",
                "answer": "SOME TEXT",
                "contract": {"violations": ["v1"]}}), encoding="utf-8")
            assert er._extract_pipeline_answer(d) == \
                "typed_no_answer:COMPOSED_CONTRACT_INVALID"

    def test_downgraded_composition_delivers_with_one_caveat(self):
        # directive 2 (DOWNGRADE DON'T DISCARD): a composition whose
        # failing EVIDENCE-BACKED claims were relabeled ASSUMPTION and
        # whose invalid citations were dropped SHIPS with the one
        # plain-language caveat — it is never discarded into a blank.
        import eval.run as er
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "run"
            d.mkdir()
            (d / "ANSWER_COMPOSED.json").write_text(json.dumps({
                "state": "COMPOSED_CONTRACT_DOWNGRADED",
                "answer": "INDICATOR: x 4.5 mm/s — ASSUMPTION",
                "caveats": ["Note: some supporting details in this "
                            "answer could not be verified against the "
                            "retrieved records and are labeled as "
                            "engineering assumptions; the "
                            "falsification test is the precondition "
                            "for relying on them."],
                "downgrade": {"applied": True, "n_relabels": 1},
                "contract": {"valid": True, "violations": []}}),
                encoding="utf-8")
            out = er._extract_pipeline_answer(d)
            assert out is not None and "ASSUMPTION" in out
            assert out.count("Note:") == 1

    def test_truncated_delivered_state_ships(self):
        # directive 2: a truncated draft cut at the last complete
        # sentence SHIPS (one plain caveat) — the blank is gone.
        import eval.run as er
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "run"
            d.mkdir()
            (d / "ANSWER_COMPOSED.json").write_text(json.dumps({
                "state": "COMPOSED_TRUNCATED_DELIVERED",
                "answer": "INDICATOR: x 4.5 mm/s — ASSUMPTION.",
                "caveats": ["Note: this answer was shortened at the "
                            "model's output budget and may be "
                            "incomplete."]}), encoding="utf-8")
            out = er._extract_pipeline_answer(d)
            assert out is not None and "ASSUMPTION" in out

    def test_repair_loop_is_bounded_until_valid(self):
        # compose -> validate -> repair UNTIL valid: the loop ends on
        # the first valid pass and never exceeds MAX_REPAIR_ROUNDS
        calls = []

        def llm(prompt, system="", timeout=240, max_tokens=700,
                purpose="", **kw):
            calls.append(purpose)
            if purpose == "answer_composer":
                return {"ok": True, "content": "bad draft THRESHOLD: 9",
                        "finish_reason": "stop"}
            # every repair fixes it
            return {"ok": True, "content": (
                "INDICATOR: vibration RMS\nTHRESHOLD: 4.5 mm/s — "
                "ASSUMPTION\nPROTOCOL: n=6 fan drives monitored 180 "
                "days by vibration RMS logging; pass if the alert "
                "fires before visible spalling."), "finish_reason": "stop"}

        rec = compose_if_admissible(
            {"mechanism_map": {}, "attack_results": {},
             "ranked_results": {"results": [{
                 "disposition": "SURVIVED", "attack_verdict": "SURVIVED",
                 "mechanism": "m", "intervention": "i"}]}},
            FU004, packet=[{"id": "p1", "title": "t",
                            "abstract": "vibration fouling"}],
            verification=None, question_type="predictor-design",
            llm_generate=llm)
        assert rec["state"] == "COMPOSED_CONTRACT_VALID"
        assert calls[0] == "answer_composer"
        assert calls[1] == "answer_composer_repair"
        assert len(calls) == 2, "the loop ENDED on the first valid pass"
        assert rec.get("repair_rounds_used", 0) <= MAX_REPAIR_ROUNDS

    def test_constraint_violation_feedback_rides_the_repair(self):
        # DIRECTIVE 2: a first draft using a pressure setpoint (outside
        # fu-004's temperature+flow allowlist) triggers a repair whose
        # prompt carries the CONSTRAINT VIOLATION line
        prompts = []

        def llm(prompt, system="", timeout=240, max_tokens=700,
                purpose="", **kw):
            prompts.append((purpose, prompt))
            if purpose == "answer_composer":
                return {"ok": True, "content": (
                    "INDICATOR: the turbine exhaust pressure setpoint "
                    "error measured by the pressure transmitter\n"
                    "THRESHOLD: 2.5 kPa — ASSUMPTION\nPROTOCOL: n=5 "
                    "cycles; pass if the alert precedes derating."),
                    "finish_reason": "stop"}
            return {"ok": True, "content": (
                "INDICATOR: condenser cooling-water temperature rise "
                "versus flow, from the existing temperature and flow "
                "measurements\nTHRESHOLD: 2.5 C rise over the clean "
                "baseline — ASSUMPTION (calibrated on 14 days of "
                "healthy data)\nPROTOCOL: n=5 fouling cycles; pass if "
                "the indicator fires at least 3 weeks before "
                "derating."), "finish_reason": "stop"}

        rec = compose_if_admissible(
            {"mechanism_map": {}, "attack_results": {},
             "ranked_results": {"results": [{
                 "disposition": "SURVIVED", "attack_verdict": "SURVIVED",
                 "mechanism": "m", "intervention": "i"}]}},
            FU004, packet=[{"id": "p1", "title": "t",
                            "abstract": "fouling temperature"}],
            verification=None, question_type="predictor-design",
            llm_generate=llm)
        assert rec["state"] == "COMPOSED_CONTRACT_VALID"
        repair_prompt = prompts[1][1]
        assert "CONSTRAINT VIOLATION [DISALLOWED_MEASUREMENT]" \
            in repair_prompt
        assert "temperature and flow" in repair_prompt


# =====================================================================
# DIRECTIVE 2 — constraint-compliance audit (audited regressions)
# =====================================================================

class TestConstraintAudit:
    def test_fu004_pressure_setpoint_flagged(self):
        # the audited fu-004 answer used a turbine exhaust pressure
        # setpoint while only temperature and flow are allowed
        ans = ("INDICATOR: The mean absolute smoothed condenser "
               "pressure error (defined as the moving average of "
               "|turbine exhaust pressure setpoint − measured exhaust "
               "pressure| over a 1-hour window)\nTHRESHOLD: 2.5 kPa — "
               "ASSUMPTION\nPROTOCOL: n=5 cycles; pass if the alert "
               "precedes derating.")
        rec = audit_constraints(FU004, ans)
        assert rec["state"] == "CONSTRAINT_VIOLATIONS"
        types = {v["type"] for v in rec["violations"]}
        assert "DISALLOWED_MEASUREMENT" in types
        assert any("pressure" in v["detail"]
                   for v in rec["violations"]
                   if v["type"] == "DISALLOWED_MEASUREMENT")

    def test_fu004_temperature_flow_answer_passes(self):
        ans = ("INDICATOR: condenser cooling-water temperature rise "
               "against flow from the existing temperature and flow "
               "measurements\nTHRESHOLD: 2.5 C rise — ASSUMPTION\n"
               "PROTOCOL: n=5 fouling cycles; pass if the alert "
               "precedes derating.")
        rec = audit_constraints(FU004, ans)
        assert rec["state"] == "CONSTRAINT_AUDIT_PASS", rec["violations"]

    def test_new04_saturated_condensing_temperature_flagged(self):
        # the audited new04 answer used "saturated condensing
        # temperature", which is not a listed BMS point
        ans = ("INDICATOR: saturated condensing temperature measured "
               "at the condenser\nTHRESHOLD: 3 C shift — ASSUMPTION\n"
               "PROTOCOL: n=12 weeks of BMS logs; pass if fouling is "
               "resolved within 3 days.")
        rec = audit_constraints(NEW04, ans)
        assert rec["state"] == "CONSTRAINT_VIOLATIONS"
        assert any(v["type"] == "DISALLOWED_MEASUREMENT"
                   for v in rec["violations"])

    def test_new04_listed_point_passes(self):
        ans = ("INDICATOR: condenser water supply and return "
               "temperature difference from the logged BMS points\n"
               "THRESHOLD: 1.8 C — ASSUMPTION\nPROTOCOL: n=12 weeks "
               "of logs; pass if fouling is resolved within 3 days.")
        rec = audit_constraints(NEW04, ans)
        assert rec["state"] == "CONSTRAINT_AUDIT_PASS", rec["violations"]

    def test_new01_constraint_echo_parameters_flagged(self):
        # the audited new01 answer listed the user constraints as the
        # design parameters
        ans = ("RECOMMENDED INTERVENTION: reduce dry-out.\n"
               "PARAMETER: 10-year life target — fixed\n"
               "PARAMETER: 2.7 V rated cell voltage — fixed\n"
               "PARAMETER: 65 C maximum ambient — fixed\n"
               "EXPECTED EFFECT: less dry-out.\n"
               "Falsification test: age cells at 65 C for 1000 h and "
               "measure capacitance loss.")
        rec = audit_constraints(NEW01, ans)
        assert rec["state"] == "CONSTRAINT_VIOLATIONS"
        assert any(v["type"] == "RESTATES_USER_CONSTRAINT"
                   for v in rec["violations"])

    def test_sofc_anode_supported_restatement_flagged(self):
        # the audited sofc answer "recommended" the anode-supported
        # cell, which the device already is
        ans = ("The recommended intervention is to transition the "
               "stack architecture to an anode-supported "
               "configuration with a thin electrolyte film.\n"
               "PARAMETER: electrolyte thickness — 10 um — ASSUMPTION\n"
               "Falsification test: run 500 thermal cycles and measure "
               "seal leakage and open-circuit voltage.")
        rec = audit_constraints(SOFC, ans)
        assert rec["state"] == "CONSTRAINT_VIOLATIONS"
        assert any(v["type"] == "RESTATES_GIVEN_DEVICE"
                   for v in rec["violations"])

    def test_genuine_change_not_flagged(self):
        ans = ("RECOMMENDED INTERVENTION: reformulate the seal "
               "glass-ceramic to hold the intergranular glass phase "
               "fraction at 0.15 while adding a compliant second "
               "phase at the seal joint, so the seal creeps instead "
               "of cracking under the differential expansion strain.\n"
               "PARAMETER: seal joint width — 0.4 mm — ASSUMPTION\n"
               "Falsification test: run 500 thermal cycles from 25 C "
               "to 800 C at 5 C/min; measure seal leakage.")
        rec = audit_constraints(SOFC, ans)
        assert rec["state"] == "CONSTRAINT_AUDIT_PASS", rec["violations"]


# =====================================================================
# DIRECTIVE 3 — gimmick-anchor rejection (mechanism-to-failure link)
# =====================================================================

class TestGimmickAnchors:
    def test_fu004_tanh_anchor_rejected(self):
        problem = FU004
        item = {"item_id": "lean_doi:10.1038/s41598-025-34740-7",
                "fields": {}, "_record_text":
                "A novel hyperbolic tangent-based PID controller tuned "
                "by the artificial lemming algorithm for nonlinear "
                "steam condenser pressure control. Precise pressure "
                "regulation in nonlinear shell-and-tube steam "
                "condensers."}
        fields = {"mechanism": "The tanh-weighted pressure error "
                               "isolates degradation from load swings "
                               "as the fouling layer grows",
                  "intervention": "monitor the tanh-weighted error",
                  "predicted_effect": "detect fouling 3 weeks early"}
        r = mechanism_to_failure_link_check(problem, item, fields)
        assert r["verdict"] == "ANCHOR_OFF_DOMAIN", r

    def test_fu003_magnetic_anchor_rejected(self):
        problem = {"device": "4.16 kV induction motor driving a boiler "
                             "feed pump",
                   "failure": "stator winding insulation degrades "
                              "through partial discharge; ground fault "
                              "cascade brings the motor down",
                   "failure_mode": "motor-insulation"}
        item = {"item_id": "lean_doi:10.3390/s25144471", "fields": {},
                "_record_text": "Measuring the Operating Condition of "
                "Induction Motor Using High-Sensitivity Magnetic "
                "Sensor. This study aimed to monitor the operating "
                "state of an induction motor using a highly sensitive "
                "magnetic sensor, which could be applied for anomaly "
                "detection in the future."}
        fields = {"mechanism": "A non-contact magnetic sensor captures "
                               "the flux asymmetry that precedes "
                               "insulation degradation",
                  "intervention": "install one magnetic sensor at the "
                                  "stator",
                  "predicted_effect": "detect degradation 6 months "
                                      "before ground fault"}
        r = mechanism_to_failure_link_check(problem, item, fields)
        assert r["verdict"] == "ANCHOR_OFF_DOMAIN", r

    def test_p02_arxiv_porous_electrode_anchor_rejected(self):
        problem = {"device": "valve-regulated lead-acid battery "
                             "positive plate",
                   "failure": "positive grid corrosion during extended "
                              "float charge consumes grid "
                              "cross-section, raising internal "
                              "resistance until capacity falls",
                   "failure_mode": "corrosion"}
        item = {"item_id": "lean_doi:10.48550/arxiv.1902.01774",
                "fields": {}, "_record_text":
                "Faster Lead-Acid Battery Simulations from "
                "Porous-Electrode Theory: II. Asymptotic Analysis. "
                "Electrochemical and equivalent-circuit modelling are "
                "the two most popular approaches to battery "
                "simulation."}
        fields = {"mechanism": "A graphene-polyaniline gel binder "
                               "stabilizes the paste and slows grid "
                               "corrosion",
                  "intervention": "switch the positive paste binder to "
                                  "a graphene-polyaniline gel",
                  "predicted_effect": "15-year float life"}
        r = mechanism_to_failure_link_check(problem, item, fields)
        assert r["verdict"] == "ANCHOR_OFF_DOMAIN", r

    def test_new04_buoy_anchor_rejected(self):
        problem = NEW04
        item = {"item_id": "lean_doi:10.5281/zenodo.18483338",
                "fields": {}, "_record_text":
                "Skoog Buoy: Open-Source Atmospheric Water Harvesting "
                "Using Deep-Ocean Cooling — No Electricity, No Brine."}
        fields = {"mechanism": "Multiscale wavelet decomposition plus "
                               "a random forest infers fouling from "
                               "BMS points without labeled data",
                  "intervention": "deploy the wavelet + random forest "
                                  "predictor",
                  "predicted_effect": "cleaning trigger 3 days early"}
        r = mechanism_to_failure_link_check(problem, item, fields)
        assert r["verdict"] in ("ANCHOR_OFF_DOMAIN",
                                "GIMMICK_ANCHOR_NO_LINK"), r

    def test_domain_anchored_candidate_passes(self):
        problem = FU004
        item = {"item_id": "lean_fouling_study", "fields": {},
                "_record_text": "Study of tube-side biofouling in "
                "condensers: the fouling layer raises the thermal "
                "resistance and degrades heat transfer; cleaning "
                "restores the clean baseline."}
        fields = {"mechanism": "Cooling-water temperature rise at "
                               "constant flow tracks the fouling layer "
                               "growth",
                  "intervention": "monitor the temperature rise",
                  "predicted_effect": "leading indicator 3 weeks "
                                      "before derating"}
        r = mechanism_to_failure_link_check(problem, item, fields)
        assert r["verdict"] == "LINKED", r

    def test_assemble_candidate_rejects_gimmick(self):
        from discovery_fabric.engine import mechanism_space as _ms
        problem = FU004
        item = {"item_id": "lean_tanh", "structured_hash": "h",
                "_record_text": "A novel hyperbolic tangent-based PID "
                "controller for steam condenser pressure control.",
                "fields": {"system": {"value": "steam condenser "
                                              "pressure control"},
                           "mechanism": {"value": "tanh gain "
                                                  "modulation"},
                           "abstract": {"value": ""}},
                "source": {"id": "doi:x"}}
        op = next(o for o in _ms.TRANSFORMATION_OPERATORS
                  if o["operator_id"] == "DIRECT_TRANSFER")
        fields = {"mechanism": "tanh-weighted pressure error tracks the "
                               "fouling layer growth",
                  "intervention": "monitor the tanh-weighted error in "
                                  "the DCS",
                  "predicted_effect": "detect fouling 3 weeks early",
                  "testable_prediction": "the indicator rises before "
                                         "derating within 3 weeks",
                  "known_failure_modes": "load swings mask the signal",
                  "boundary_conditions": "full load",
                  "mechanism_source_span": "tanh"}
        cand = _ms.assemble_candidate(op, item, fields, problem,
                                      {"provider": "test",
                                       "model": "test"})
        assert cand["candidate_state"] == \
            "NOT_EVIDENCE_ANCHORED_ANCHOR_OFF_DOMAIN", cand[
                "candidate_state"]
        assert cand["candidate_id"].startswith("noncand:MS:")
        assert cand["mechanism_link_check"]["verdict"] == \
            "ANCHOR_OFF_DOMAIN"


# =====================================================================
# DIRECTIVE 4 — use the stated variable (sofc 0.15)
# =====================================================================

class TestStatedVariable:
    def test_dict_clarification_reaches_the_audit(self):
        from discovery_fabric.engine.constraint_audit import \
            _clarification_numbers
        nums = _clarification_numbers(SOFC)
        assert {"name": "intergranular glass phase fraction",
                "value": 0.15} in nums

    def test_zero_point_one_five_only_as_echo_is_flagged(self):
        ans = ("RECOMMENDED INTERVENTION: adjust the stack operation.\n"
               "PARAMETER: intergranular glass phase fraction — 0.15 — "
               "USER-STATED CONSTRAINT\n"
               "Falsification test: run 500 cycles and measure "
               "leakage.")
        rec = audit_constraints(SOFC, ans)
        assert any(v["type"] == "STATED_VARIABLE_UNUSED"
                   for v in rec["violations"]), rec["violations"]

    def test_zero_point_one_five_used_in_design_passes(self):
        ans = ("RECOMMENDED INTERVENTION: reformulate the seal "
               "glass-ceramic to hold the intergranular glass phase "
               "fraction at 0.15 while adding a compliant second "
               "phase, so the seal creeps instead of cracking under "
               "the differential expansion strain.\n"
               "PARAMETER: intergranular glass phase fraction — 0.15 — "
               "ASSUMPTION (design center of the creep/thermal-shock "
               "balance)\n"
               "Falsification test: run 500 thermal cycles from 25 C "
               "to 800 C at 5 C/min; failure is seal leakage above 1 "
               "percent of fuel flow.")
        rec = audit_constraints(SOFC, ans)
        assert not any(v["type"] == "STATED_VARIABLE_UNUSED"
                       for v in rec["violations"]), rec["violations"]

    def test_dict_clarification_reaches_the_composer_prompt(self):
        from discovery_fabric.engine.answer_composer import \
            _variables_block
        blk = _variables_block(SOFC)
        assert "intergranular glass phase fraction = 0.15" in blk


class TestAblationArmFlags:
    """DIRECTIVE 5: steps 2-3 ride as explicit ablation arms."""

    def test_constraint_audit_arm_off(self, monkeypatch=None):
        import os
        from discovery_fabric.engine.constraint_audit import \
            _find_disallowed_measurements
        os.environ["FABRIC_CONSTRAINT_AUDIT"] = "0"
        try:
            from discovery_fabric.engine import answer_composer as ac
            import inspect
            src = inspect.getsource(ac.compose_answer)
            assert "FABRIC_CONSTRAINT_AUDIT" in src
            assert "constraint_audit_arm" in src
        finally:
            os.environ.pop("FABRIC_CONSTRAINT_AUDIT", None)

    def test_knowledge_first_arm_off(self):
        import os
        import inspect
        from discovery_fabric.engine import adapters
        os.environ["FABRIC_KNOWLEDGE_FIRST"] = "0"
        try:
            src = inspect.getsource(adapters._lean_mechanism_space)
            assert "FABRIC_KNOWLEDGE_FIRST" in src
        finally:
            os.environ.pop("FABRIC_KNOWLEDGE_FIRST", None)


# =====================================================================
# DIRECTIVE 6 — kill records + hypothesis delivery
# =====================================================================

# The five tests below pin the AUDIT ROUND'S LIVE RUN ARTIFACTS
# (candidate_envelope.json under eval/runs/<commit>/...). eval/runs is
# GITIGNORED (hashes-only rule): the artifacts exist ONLY on the host
# that ran that round, immediately after it ran (the sandbox rule
# wipes run dirs between invocations). On any other host — or after
# any later invocation — they are ABSENT BY CONSTRUCTION, not by a
# code regression. A live-artifact pin must degrade to a TYPED SKIP
# when its artifacts are absent (the same class as the engine's
# typed-unavailable rung skips), never a silent pass and never a red
# suite everywhere but the host that produced the artifacts (Art. XXV:
# measured reality over aspiration; Art. XXVII: recorded, never
# silent).
RUNS = REPO / "eval" / "runs" / "977851bc16a5"
_AUDIT_ARTIFACTS_PRESENT = RUNS.exists()

requires_audit_artifacts = pytest.mark.skipif(
    not _AUDIT_ARTIFACTS_PRESENT,
    reason=("audit-round live artifacts absent: eval/runs is gitignored "
            "and the pinned run belongs to the audit round's host — "
            "host/run-bound verification, not a regression"))


def _gauntlet(attack_results):
    """Minimal envelope dict the admission analysis reads."""
    return {"attack_results": attack_results,
            "mechanism_map": {},
            "ranked_results": None}


class TestKillCauseClassification:
    @requires_audit_artifacts
    def test_p09_all_kills_not_in_record(self):
        d = json.loads((RUNS / ("r1-pipeline+baseline+judge-2026-11-"
                                "12050540000/bench-p09-packaging-"
                                "barrier/pipeline/candidate_envelope"
                                ".json")).read_text(encoding="utf-8"))
        kc = kill_cause_record(d["attack_results"])
        assert kc["n_kills"] >= 1
        assert kc["all_not_in_record"] is True
        assert all(k["cause"] == KILL_CAUSE_NOT_IN_RECORD
                   for k in kc["per_kill"])

    @requires_audit_artifacts
    def test_fu005_all_kills_not_in_record(self):
        d = json.loads((RUNS / ("r1-pipeline+baseline+judge-2026-11-"
                                "12052337000/dev-fu-005-bridge-bearing/"
                                "pipeline/candidate_envelope.json"))
                       .read_text(encoding="utf-8"))
        kc = kill_cause_record(d["attack_results"])
        assert kc["all_not_in_record"] is True

    @requires_audit_artifacts
    def test_new07_physics_kill_keeps_the_kill(self):
        d = json.loads((RUNS / ("r1-pipeline+baseline+judge-2026-11-"
                                "12051342000/eval-new07-transformer-"
                                "dga-predictor/pipeline/"
                                "candidate_envelope.json"))
                       .read_text(encoding="utf-8"))
        kc = kill_cause_record(d["attack_results"])
        assert kc["all_not_in_record"] is False
        assert KILL_CAUSE_SCIENTIFIC in {
            k["cause"] for k in kc["per_kill"]}
        assert "unsupported_mechanism" in kc["scientific_kill_classes"]


class TestHypothesisDelivery:
    @requires_audit_artifacts
    def test_not_in_record_kills_admit_flagged_hypothesis(self):
        # p09's actual gauntlet record: every kill is a record-
        # availability kill -> the candidate is admissible as a
        # clearly flagged UNVERIFIED hypothesis (the approved attack
        # semantics), never a typed no-answer
        d = json.loads((RUNS / ("r1-pipeline+baseline+judge-2026-11-"
                                "12050540000/bench-p09-packaging-"
                                "barrier/pipeline/candidate_envelope"
                                ".json")).read_text(encoding="utf-8"))
        env = dict(d)
        env["ranked_results"] = None
        cands = compose_if_admissible.__globals__[
            "candidates_from_state"](env, top_n=5)
        assert cands, "the record-bound hypothesis must be admitted"
        c = cands[0]
        assert c["admission"]["class"] == "HYPOTHESIS"
        assert c["hypothesis_unverified"] is True
        assert c["admission"]["reason"] == "ALL_KILLS_NOT_IN_RECORD"

    @requires_audit_artifacts
    def test_scientific_kill_stays_a_no_answer(self):
        # new07's physics-invalid mechanism kill: NO hypothesis
        # admission — the typed no-answer stands (never manufacture an
        # endorsement from a scientific kill)
        d = json.loads((RUNS / ("r1-pipeline+baseline+judge-2026-11-"
                                "12051342000/eval-new07-transformer-"
                                "dga-predictor/pipeline/"
                                "candidate_envelope.json"))
                       .read_text(encoding="utf-8"))
        env = dict(d)
        env["ranked_results"] = None
        cands = compose_if_admissible.__globals__[
            "candidates_from_state"](env, top_n=5)
        assert not cands

    def test_starved_run_never_adjudicated_delivers_hypothesis(self):
        # R6 live run of this round (fu-005 @57e076077cc0, measured):
        # a run that types MECHANISM_STARVED at the mechanism-space
        # distinctness gate leaves the envelope's evidence-SUPPORTED
        # raw candidate NEVER ADJUDICATED (ATTACK_RECORD_ABSENT) —
        # the same FLAGGED_UNVERIFIED_HYPOTHESIS_DELIVERED semantics
        # the committed fu-005 kill record pre-approves. Hermetic
        # fixture: the exact measured envelope shape (empty
        # attack_results, verified evidence, raw_candidate present).
        env = {
            "attack_results": {},
            "adjudication": {"evidence_verification": {
                "verified": True, "evidence_class": "SUPPORTED"}},
            "mechanism_map": {
                "mechanism": "hypothesis mechanism",
                "raw_candidate": {
                    "candidate_id": "cand:A2:test:deadbeef",
                    "mechanism": "hypothesis mechanism",
                    "intervention": "swap the seal compound"}}}
        cands = compose_if_admissible.__globals__[
            "candidates_from_state"](env, top_n=5)
        assert cands, "the never-adjudicated supported candidate " \
            "delivers as a flagged hypothesis"
        c = cands[0]
        assert c["admission"]["class"] == "HYPOTHESIS"
        assert c["hypothesis_unverified"] is True
        assert c["admission"]["reason"] == \
            "ATTACK_NEVER_ADJUDICATED_STARVED_RUN"
        assert c["admission"]["delivery_semantics"] == \
            "FLAGGED_UNVERIFIED_HYPOTHESIS_DELIVERED"
        # the evidence-failed class is NEVER delivered
        env_bad = json.loads(json.dumps(env))
        env_bad["adjudication"]["evidence_verification"]["verified"] = False
        assert not compose_if_admissible.__globals__[
            "candidates_from_state"](env_bad, top_n=5)
        # a BROKEN attack binding (a record that belongs to another
        # candidate) still refuses — never promote an unbound record
        env_broken = json.loads(json.dumps(env))
        env_broken["attack_results"] = {"overall": "SURVIVED",
                                        "revision": "r1"}
        env_broken["mechanism_map"]["revision"] = "r2"
        assert not compose_if_admissible.__globals__[
            "candidates_from_state"](env_broken, top_n=5)

    def test_hypothesis_answer_carries_one_plain_caveat(self):
        import eval.run as er
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "run"
            d.mkdir()
            (d / "ANSWER_COMPOSED.json").write_text(json.dumps({
                "state": "COMPOSED_CONTRACT_VALID",
                "answer": "RECOMMENDED INTERVENTION: use a phenolic "
                          "scavenger...\nFalsification test: measure "
                          "WVTR over 18 months.",
                "admitted_candidates": [{"candidate_id": "c1",
                                         "hypothesis": True}],
                "caveats": ["The first draft was cut off at the "
                            "model's output budget; the answer above "
                            "is the larger-budget recomposition."]}),
                encoding="utf-8")
            ans = er._extract_pipeline_answer(d)
            assert ans is not None
            # ONE plain-language caveat line; the truncation narration
            # never reaches the judge
            assert HYPOTHESIS_CAVEAT_LINE.strip() in ans
            assert "cut off at the model's output budget" not in ans
            assert ans.count("Note:") <= 1
