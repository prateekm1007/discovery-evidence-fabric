"""tests/test_r412_recovery_arm.py — the R412 recovery-arm seals
(owner directive 2026-09-06: population accounting, DEATH_CAUSE_
RECOVERY, gradient eligibility, availability taxonomy, causal
delta, WHY_NOT_ALREADY_ADOPTED, attacker caveat, preregistration).

Hermetic pins (no LLM, no network):
  - GA-0: the four-class terminal classification over the REAL
    frozen population (13/387/0/0; funnel 550/8/142/0/400; the
    classes sum to unique; rejection surfaces 359/27/1)
  - structural no-LLM: classify_population / recover_death_causes
    accept no callable and no transport — no LLM may invent a
    missing death cause (directive items 3/4)
  - synthetic classification: empty death-cause -> RECORDED_NO_
    DEATH_CAUSE (never invented); unclassifiable states ->
    OTHER_TERMINAL_STATE (recorded, defensive)
  - the emission guard: a non-closing funnel / hidden denominator
    is UN-EMITTABLE (raises)
  - DEATH_CAUSE_RECOVERY: 13 ESTABLISHED with source references +
    verbatim spans; 387 NO_TECH_DEATH_CAUSE; the flow chart's
    next_stage wiring (YES -> CAPABILITY_DEFICIT_EXTRACTION)
  - GA-2: the frozen capability-axis classification (4/6/390);
    every basis span VERBATIM in the real recorded death reason
    (the strong pin); a disputed span fails CLOSED (ineligible +
    recorded defect); NO_TECH_DEATH_CAUSE seeds never eligible
  - availability: ONLY AVAILABLE_TODAY promotes; NEAR_TERM/FUTURE
    are radar (FUTURE_ONLY); UNKNOWN blocks (never promotion,
    never rejection)
  - causal delta: machine-computed set operations; the item-8 gate
    (empty delta, unreferenced new_interaction, label-only delta,
    missing measurement all FAIL)
  - WHY_NOT: span-verified findings admitted; paraphrase downgraded
    to UNKNOWN (blocks promotion); the allowed-findings enum
  - the attacker caveat travels on the funnel (NOT_CALIBRATED,
    never a silent green signal)
  - GA-1b/TVM/backcast span gates: verbatim passes; invention
    counts as nothing
  - the seal: verify_seal passes on the committed prereg; a gutted
    prereg REFUSES the run
  - the sealed temporal control arm is preserved (hash pinned)
"""
import hashlib
import inspect
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.r412.recovery import (  # noqa: E402
    RECORDED_TECHNICAL_DEATH, RECORDED_NONTECHNICAL_REJECTION,
    RECORDED_NO_DEATH_CAUSE, OTHER_TERMINAL_STATE,
    GRADIENT_ELIGIBLE, GRADIENT_PRIOR_ART_SPECIAL_ROUTE,
    GRADIENT_INELIGIBLE, CAPABILITY_DEFICIT,
    PRIOR_ART_ANTICIPATION, REGIME_OR_CONSISTENCY_VIOLATION,
    CAPABILITY_DEFICIT_CLASSIFICATIONS,
    AVAILABLE_TODAY, NEAR_TERM, FUTURE, UNKNOWN,
    PRESENT_CAPABILITY_REDISCOVERY, FUTURE_DEPENDENT,
    UNRESOLVED_AVAILABILITY,
    classify_population, build_population_accounting,
    recover_death_causes, classify_gradient_eligibility,
    classify_availability, availability_branch,
    parent_causal_graph, compute_causal_delta, verify_causal_delta,
    verify_why_not_finding, build_recovery_funnel,
    verify_population_funnel, FunnelArithmeticError,
    ATTACKER_CALIBRATION_STATUS)
from discovery_fabric.r412 import gradient as ga  # noqa: E402
from discovery_fabric.r412 import recovery as rec  # noqa: E402

RUN = REPO / "R411" / "DISCOVERY_RUN"
WATERFALL = REPO / "R412" / "R412_DEATH_CAUSE_WATERFALL.json"
ACCOUNTING = REPO / "R412" / "RECOVERY_ARM" / \
    "R412_POPULATION_ACCOUNTING.json"
PREREG = REPO / "R412" / "R412_GRADIENT_RECOVERY_PREREGISTRATION.json"
TVM_V0 = REPO / "R412" / "RECOVERY_ARM" / "TVM_V0_SNAPSHOT.json"
TEMPORAL_RUN = REPO / "R412" / "TEMPORAL_REPLAY" / \
    "R412_TEMPORAL_REPLAY_RUN.json"
TEMPORAL_RUN_SHA = "e7c4ecd5194b2b5270e51c09034cf246b72cff70" \
                   "8953f16f73ba1cf879fea295"


def _load(p):
    return json.loads(Path(p).read_text())


@pytest.fixture(scope="module")
def frozen():
    return {
        "scored": _load(RUN / "scored_pool.json"),
        "shortlist": _load(RUN / "shortlist.json"),
        "selection": _load(RUN / "selection.json"),
        "waterfall": _load(WATERFALL),
        "funnel": _load(RUN / "funnel_collision.json"),
    }


@pytest.fixture(scope="module")
def accounting(frozen):
    return build_population_accounting(
        frozen["funnel"], frozen["scored"], frozen["shortlist"],
        frozen["selection"], frozen["waterfall"])


# ---------------------------------------------------------------------------
# GA-0 — the population accounting
# ---------------------------------------------------------------------------

class TestPopulationAccounting:
    def test_real_funnel_closes(self, accounting):
        f = accounting["funnel"]
        assert f["raw_accepted"] == 550
        assert f["medical_excluded"] == 8
        assert f["collision_rejected"] == 142
        assert f["dedup_merged"] == 0
        assert f["unique_scored"] == 400

    def test_real_terminal_classes(self, accounting):
        c = accounting["terminal_classification"]["counts"]
        assert c[RECORDED_TECHNICAL_DEATH] == 13
        assert c[RECORDED_NONTECHNICAL_REJECTION] == 387
        assert c[RECORDED_NO_DEATH_CAUSE] == 0
        assert c[OTHER_TERMINAL_STATE] == 0
        assert sum(c.values()) == 400

    def test_rejection_surfaces(self, accounting):
        s = accounting["terminal_classification"]["rejection_surfaces"]
        assert s["SCORING_EVIDENCE_FLOOR"] == 359
        assert s["SHORTLIST_RANK_OUT"] == 27
        assert s["ATTACK_TOURNAMENT_NONTECHNICAL"] == 1

    def test_headline_denominators_complete(self, accounting):
        for k in ("raw_accepted", "unique_scored",
                  "recorded_technical_death",
                  "recorded_nontechnical_rejection",
                  "recorded_no_death_cause", "other_terminal_state",
                  "gradient_eligible", "gradient_attempted"):
            assert k in accounting["headline_denominators"]

    def test_13_subset_is_a_subset_not_the_headline(self, accounting):
        sub = accounting["technical_death_subset"]
        assert sub["n"] == 13
        assert len(sub["candidate_ids"]) == 13
        assert "never the headline population" in \
            sub["subset_status"]

    def test_population_hash_is_deterministic(self, frozen,
                                              accounting):
        again = build_population_accounting(
            frozen["funnel"], frozen["scored"],
            frozen["shortlist"], frozen["selection"],
            frozen["waterfall"])
        assert again["population_sha256"] == \
            accounting["population_sha256"]

    def test_no_llm_structurally(self):
        """The accounting + recovery stages accept no callable and no
        transport: an LLM cannot be wired in, so no LLM may invent a
        missing death cause (directive items 3/4)."""
        for fn in (classify_population, build_population_accounting,
                   recover_death_causes,
                   classify_gradient_eligibility):
            params = inspect.signature(fn).parameters
            for name, p in params.items():
                assert p.default is inspect.Parameter.empty or \
                    isinstance(p.default, (bool, int, str, list,
                                           dict, type(None))), \
                    f"{fn.__name__} has a suspicious default " \
                    f"parameter {name}"
                assert "llm" not in name.lower() and \
                    "model" not in name.lower() and \
                    "transport" not in name.lower(), \
                    f"{fn.__name__} wires an LLM ({name})"

    def test_empty_death_cause_is_never_invented(self, frozen):
        """A waterfall death record with an empty/unknown cause field
        classifies as RECORDED_NO_DEATH_CAUSE — the cause stays
        unestablished; nothing invents one."""
        wf = dict(frozen["waterfall"])
        deaths = [dict(d) for d in wf["deaths"]]
        deaths[0]["death_cause"] = ""
        wf["deaths"] = deaths
        short_ids = [c["candidate_id"]
                     for c in frozen["shortlist"]]
        cls = classify_population(frozen["scored"], short_ids,
                                  deaths)
        row = next(r for r in cls["rows"] if r["candidate_id"] ==
                   deaths[0]["candidate_id"])
        assert row["terminal_class"] == RECORDED_NO_DEATH_CAUSE
        assert row["death_cause_category"] is None

    def test_unclassifiable_state_is_other(self, frozen):
        scored = [dict(c) for c in frozen["scored"]]
        # strip the scoring record from one non-shortlisted candidate
        victim = next(c for c in scored
                      if c["candidate_id"] not in
                      {s["candidate_id"] for s in frozen["shortlist"]})
        victim["scoring"] = {}
        cls = classify_population(
            scored, [c["candidate_id"] for c in frozen["shortlist"]],
            frozen["waterfall"]["deaths"])
        row = next(r for r in cls["rows"]
                   if r["candidate_id"] == victim["candidate_id"])
        assert row["terminal_class"] == OTHER_TERMINAL_STATE


class TestEmissionGuard:
    def test_raw_not_closing_raises(self, accounting):
        broken = json.loads(json.dumps(accounting))
        broken["funnel"]["raw_accepted"] = 551
        with pytest.raises(FunnelArithmeticError):
            verify_population_funnel(broken)

    def test_classes_not_summing_raises(self, accounting):
        broken = json.loads(json.dumps(accounting))
        broken["terminal_classification"]["counts"][
            RECORDED_TECHNICAL_DEATH] = 14
        with pytest.raises(FunnelArithmeticError):
            verify_population_funnel(broken)

    def test_hidden_denominator_raises(self, accounting):
        broken = json.loads(json.dumps(accounting))
        del broken["headline_denominators"]["gradient_eligible"]
        with pytest.raises(FunnelArithmeticError):
            verify_population_funnel(broken)


# ---------------------------------------------------------------------------
# DEATH_CAUSE_RECOVERY + GA-2
# ---------------------------------------------------------------------------

class TestDeathCauseRecovery:
    def test_real_counts(self, accounting, frozen):
        rows = recover_death_causes(accounting,
                                    frozen["waterfall"]["deaths"])
        established = [r for r in rows if r.get(
            "technological_death_cause_established")]
        assert len(established) == 13
        assert len(rows) == 400
        for r in established:
            assert r["verdict"] == \
                "TECHNOLOGICAL_DEATH_CAUSE_ESTABLISHED"
            assert r["source_references"]
            assert r["next_stage"] == "CAPABILITY_DEFICIT_EXTRACTION"
        for r in rows:
            if not r.get("technological_death_cause_established"):
                assert r["verdict"] == "NO_TECH_DEATH_CAUSE"
                assert r["next_stage"] is None
                assert "invent" in r["note"]

    def test_flow_chart_wiring(self, frozen, accounting):
        """YES -> CAPABILITY-DEFICIT EXTRACTION; NO ->
        NO_TECH_DEATH_CAUSE (the directive item-4 flow)."""
        rows = recover_death_causes(accounting,
                                    frozen["waterfall"]["deaths"])
        yes = next(r for r in rows if r.get(
            "technological_death_cause_established"))
        no = next(r for r in rows if not r.get(
            "technological_death_cause_established"))
        assert yes["next_stage"] == "CAPABILITY_DEFICIT_EXTRACTION"
        assert no["verdict"] == "NO_TECH_DEATH_CAUSE"


class TestGradientEligibility:
    def test_real_split(self, accounting, frozen):
        rows = classify_gradient_eligibility(
            recover_death_causes(accounting,
                                 frozen["waterfall"]["deaths"]),
            frozen["waterfall"]["deaths"])
        assert sum(1 for r in rows
                   if r["eligibility"] == GRADIENT_ELIGIBLE) == 4
        assert sum(1 for r in rows if r["eligibility"] ==
                   GRADIENT_PRIOR_ART_SPECIAL_ROUTE) == 6
        assert sum(1 for r in rows if r["eligibility"] ==
                   GRADIENT_INELIGIBLE) == 390

    def test_every_basis_span_verbatim_in_real_record(self, frozen):
        """The strong pin: every frozen classification row's basis
        span is verbatim-contained in the REAL recorded death
        reason."""
        reasons = {d["candidate_id"]: d["death_reason"]
                   for d in frozen["waterfall"]["deaths"]}
        assert len(CAPABILITY_DEFICIT_CLASSIFICATIONS) == 13
        for cid, row in \
                CAPABILITY_DEFICIT_CLASSIFICATIONS.items():
            assert cid in reasons, f"{cid} not in the waterfall"
            assert rec._norm(row["basis_span"]) in rec._norm(
                reasons[cid]), \
                f"basis span for {cid} not verbatim in the record"

    def test_capability_deficit_rows_carry_named_deficits(self):
        for cid, row in CAPABILITY_DEFICIT_CLASSIFICATIONS.items():
            if row["axis_class"] == CAPABILITY_DEFICIT:
                assert row["named_deficit"]
                assert row["deficit_class"] in (
                    "measurement", "control_computation",
                    "actuation_control",
                    "device_technology_parameter")
            elif row["axis_class"] == PRIOR_ART_ANTICIPATION:
                assert row["named_deficit"] is None
            elif row["axis_class"] == \
                    REGIME_OR_CONSISTENCY_VIOLATION:
                assert row["named_deficit"] is None

    def test_no_tech_death_cause_never_eligible(self, frozen,
                                                accounting):
        rows = classify_gradient_eligibility(
            recover_death_causes(accounting,
                                 frozen["waterfall"]["deaths"]),
            frozen["waterfall"]["deaths"])
        for r in rows:
            if not r.get("technological_death_cause_established"):
                assert r["eligibility"] == GRADIENT_INELIGIBLE
                assert "manufacture a death cause" in \
                    r["ineligibility_reason"]

    def test_disputed_span_fails_closed(self, frozen, accounting):
        """A classification row whose basis span is NOT in the
        record fails CLOSED: ineligible + a recorded defect — never
        a silent pass."""
        rows = classify_gradient_eligibility(
            recover_death_causes(accounting,
                                 frozen["waterfall"]["deaths"]),
            frozen["waterfall"]["deaths"])
        good = next(r for r in rows
                    if r["eligibility"] == GRADIENT_ELIGIBLE)
        assert good["basis_span_verified_verbatim"] is True
        # forge a disputed row in the frozen table and re-run
        saved = dict(CAPABILITY_DEFICIT_CLASSIFICATIONS[
            good["candidate_id"]])
        try:
            CAPABILITY_DEFICIT_CLASSIFICATIONS[
                good["candidate_id"]] = {
                **saved, "basis_span":
                    "this span was never in any death record"}
            rows2 = classify_gradient_eligibility(
                recover_death_causes(
                    accounting, frozen["waterfall"]["deaths"]),
                frozen["waterfall"]["deaths"])
            r2 = next(r for r in rows2 if r["candidate_id"] ==
                      good["candidate_id"])
            assert r2["eligibility"] == GRADIENT_INELIGIBLE
            assert r2["basis_span_verified_verbatim"] is False
            assert "disputed" in r2["defect"]
        finally:
            CAPABILITY_DEFICIT_CLASSIFICATIONS[
                good["candidate_id"]] = saved

    def test_unknown_technical_death_fails_closed(self, frozen,
                                                  accounting):
        """A technical death with NO frozen classification row
        fails CLOSED (ineligible, recorded) — and a death OUTSIDE
        the population is a hidden denominator (un-emittable)."""
        scored = [dict(c) for c in frozen["scored"]] + [{
            "candidate_id": "C-ghost-technical",
            "technology_name": "Ghost",
            "causal_chain": ["a", "b"],
            "scoring": {"confidence": "MEDIUM",
                        "finalist_eligible": False,
                        "composite": 0, "evidence_floor_applied":
                            True}}]
        wf = dict(frozen["waterfall"])
        deaths = [dict(d) for d in wf["deaths"]] + [{
            "candidate_id": "C-ghost-technical",
            "death_cause": "physics", "death_reason":
                "a recorded technical death never classified",
            "death_stage": "attack (F7)"}]
        wf["deaths"] = deaths
        funnel = dict(frozen["funnel"])
        funnel["raw_accepted_from_extraction"] = 551
        funnel["survivor_count"] = 401
        acc2 = build_population_accounting(
            funnel, scored, frozen["shortlist"],
            frozen["selection"], wf)
        rows = classify_gradient_eligibility(
            recover_death_causes(acc2, deaths), deaths)
        ghost = next(r for r in rows
                     if r["candidate_id"] == "C-ghost-technical")
        assert ghost["eligibility"] == GRADIENT_INELIGIBLE
        assert "fail closed" in ghost["ineligibility_reason"]

    def test_orphan_death_is_hidden_denominator(self, frozen,
                                                accounting):
        """A waterfall death for a candidate outside the population
        must make the accounting UN-EMITTABLE (raises)."""
        wf = dict(frozen["waterfall"])
        deaths = [dict(d) for d in wf["deaths"]] + [{
            "candidate_id": "C-not-in-population",
            "death_cause": "physics",
            "death_reason": "orphan death",
            "death_stage": "attack (F7)"}]
        wf["deaths"] = deaths
        with pytest.raises(FunnelArithmeticError):
            build_population_accounting(
                frozen["funnel"], frozen["scored"],
                frozen["shortlist"], frozen["selection"], wf)


# ---------------------------------------------------------------------------
# availability taxonomy (directive item 7)
# ---------------------------------------------------------------------------

class TestAvailability:
    def _row(self, exists, regime="yes"):
        return {"exists_today": exists,
                "operating_regime_match": regime,
                "name": "cap"}

    def _ver(self, verdict, status="OK"):
        return {"verdict": verdict, "status": status}

    def test_only_demonstrated_today_is_available_today(self):
        assert classify_availability(
            self._ver("DEMONSTRATED"), self._row("yes")) == \
            AVAILABLE_TODAY

    def test_demonstrated_without_regime_is_unknown(self):
        assert classify_availability(
            self._ver("DEMONSTRATED"), self._row("yes", "no")) == \
            UNKNOWN

    def test_partial_is_near_term_not_today(self):
        assert classify_availability(
            self._ver("NOT_DEMONSTRATED"), self._row("partial")) == \
            NEAR_TERM

    def test_no_is_future(self):
        assert classify_availability(
            self._ver("NOT_DEMONSTRATED"), self._row("no")) == FUTURE

    def test_transport_failure_is_unknown(self):
        assert classify_availability(
            self._ver("NOT_DEMONSTRATED",
                      "INCOMPLETE_TRANSPORT"), self._row("yes")) == \
            UNKNOWN

    def test_claimed_but_undemonstrated_is_unknown(self):
        assert classify_availability(
            self._ver("NOT_DEMONSTRATED"), self._row("yes")) == \
            UNKNOWN

    def test_branch_all_available_today_promotes(self):
        b = availability_branch({"a": AVAILABLE_TODAY,
                                 "b": AVAILABLE_TODAY})
        assert b["branch"] == PRESENT_CAPABILITY_REDISCOVERY
        assert b["outcome_class"] == "PRESENT_RECOVERY"

    def test_branch_future_is_radar_not_principal(self):
        b = availability_branch({"a": AVAILABLE_TODAY,
                                 "b": FUTURE})
        assert b["branch"] == FUTURE_DEPENDENT
        assert b["outcome_class"] == "FUTURE_ONLY"
        assert "NOT the principal" in b["note"]

    def test_branch_near_term_is_radar(self):
        b = availability_branch({"a": NEAR_TERM})
        assert b["branch"] == FUTURE_DEPENDENT
        assert b["horizon"] == NEAR_TERM

    def test_branch_unknown_blocks(self):
        b = availability_branch({"a": UNKNOWN})
        assert b["branch"] == UNRESOLVED_AVAILABILITY
        assert b["outcome_class"] == "UNRESOLVED"


# ---------------------------------------------------------------------------
# causal-architecture delta (directive item 8)
# ---------------------------------------------------------------------------

class TestCausalDelta:
    def _parent(self):
        return {"nodes": [
            {"id": "p1", "label": "acoustic waves cause mixing"},
            {"id": "p2", "label": "mixing raises h coefficient"},
        ], "edges": [
            {"from": "p1", "to": "p2", "relation": "causes"}]}

    def _desc(self, extra_node=True, extra_edge=True):
        nodes = [
            {"id": "d1", "label": "acoustic waves cause mixing"},
            {"id": "d2", "label": "mixing raises h coefficient"}]
        edges = [{"from": "d1", "to": "d2", "relation": "causes"}]
        if extra_node:
            nodes.append({"id": "d3", "label":
                          "closed-loop sensing modulates the waves"})
        if extra_edge:
            edges.append({"from": "d3", "to": "d1",
                          "relation": "modulates"})
        return {"nodes": nodes, "edges": edges}

    def test_delta_is_machine_computed(self):
        d = compute_causal_delta(self._parent(), self._desc())
        assert d["added_nodes"] == [
            "closed-loop sensing modulates the waves"]
        assert d["removed_nodes"] == []
        assert d["changed_edges"]["added"] == [[
            "closed-loop sensing modulates the waves", "modulates",
            "acoustic waves cause mixing"]]
        assert d["delta_computed_by"].startswith("set operations")

    def test_full_delta_passes_the_gate(self):
        d = compute_causal_delta(self._parent(), self._desc())
        # the promoted descendant's record explicitly contains ALL
        # EIGHT directive-item-8 fields
        d["new_interaction"] = "closed-loop sensing modulates the " \
                               "waves"
        d["predicted_new_effect"] = \
            "flatness improves 30% in the module"
        d["measurement"] = "thermocouple array at 1 Hz"
        g = verify_causal_delta(
            d, d["new_interaction"], d["predicted_new_effect"],
            d["measurement"])
        assert g["gate"] == "PASS"
        assert g["verdict"] == "NEW_CAUSAL_ARCHITECTURE"
        for field in rec.CAUSAL_DELTA_REQUIRED_FIELDS:
            assert field in d, f"promoted record missing {field}"

    def test_empty_delta_fails(self):
        d = compute_causal_delta(self._parent(), self._desc(
            extra_node=False, extra_edge=False))
        g = verify_causal_delta(d, "nothing new", "effect", "meas")
        assert g["gate"] == "FAIL"
        assert g["verdict"] == "INSUFFICIENT_DELTA"
        assert any("empty structural delta" in p
                   for p in g["problems"])

    def test_unreferenced_new_interaction_fails(self):
        d = compute_causal_delta(self._parent(), self._desc())
        g = verify_causal_delta(
            d, "a better sensor makes everything improve",
            "effect", "meas")
        assert g["gate"] == "FAIL"
        assert any("better sensor" in p for p in g["problems"])

    def test_label_only_delta_fails(self):
        """A renamed/parameterized parent node with the same edge
        structure — the 'different material / new industry'
        failure mode."""
        desc = {"nodes": [
            {"id": "d1", "label": "ultrasonic acoustic waves cause "
                                 "mixing"},
            {"id": "d2", "label": "mixing raises h coefficient"}],
            "edges": [{"from": "d1", "to": "d2",
                       "relation": "causes"}]}
        d = compute_causal_delta(self._parent(), desc)
        g = verify_causal_delta(
            d, "ultrasonic acoustic waves cause mixing", "effect",
            "meas")
        assert g["gate"] == "FAIL"
        assert any("LABEL_ONLY" in p for p in g["problems"])

    def test_missing_measurement_fails_closed(self):
        d = compute_causal_delta(self._parent(), self._desc())
        g = verify_causal_delta(
            d, "closed-loop sensing modulates the waves", "effect",
            "")
        assert g["gate"] == "FAIL"
        assert g["verdict"] == "INCOMPLETE_DELTA"

    def test_parent_graph_comes_from_the_record(self, frozen):
        cand = frozen["scored"][0]
        g = parent_causal_graph(cand)
        chain = [str(s) for s in cand.get("causal_chain") or []]
        assert [n["label"] for n in g["nodes"]] == chain


# ---------------------------------------------------------------------------
# WHY_NOT_ALREADY_ADOPTED (directive item 9)
# ---------------------------------------------------------------------------

class TestWhyNot:
    def _records(self):
        return [{
            "record_id": "r1", "title":
                "Wind turbine drivetrain alignment limitations",
            "abstract": "Operational shaft deflections exceed "
                        "assembly tolerances by an order of "
                        "magnitude; static shims cannot maintain "
                        "micron-scale alignment in service."}]

    def test_verbatim_finding_admitted(self):
        g = verify_why_not_finding(
            "control_mismatch", "r1",
            "static shims cannot maintain micron-scale alignment "
            "in service", self._records())
        assert g["admitted"] is True
        assert g["finding"] == "control_mismatch"
        assert g["verification"] == "VERBATIM_CONTAINED"

    def test_paraphrase_downgrades_to_unknown(self):
        g = verify_why_not_finding(
            "control_mismatch", "r1",
            "the shims are not able to hold alignment as the shaft "
            "sags much more than the tolerance allows", 
            self._records())
        assert g["finding"] == "UNKNOWN"
        assert g["admitted"] is False
        assert g["reason"] == "SPAN_NOT_VERBATIM_IN_RECORD"

    def test_unknown_allowed(self):
        g = verify_why_not_finding("UNKNOWN", "", "", [])
        assert g["finding"] == "UNKNOWN"
        assert g["admitted"] is True
        assert "phantom-arbitrage" in g["reason"]

    def test_enum_enforced(self):
        g = verify_why_not_finding(
            "market_did_not_want_it", "r1", "x" * 30,
            self._records())
        assert g["finding"] == "UNKNOWN"
        assert g["reason"] == "FINDING_NOT_IN_ALLOWED_ENUM"

    def test_unknown_record_rejected(self):
        g = verify_why_not_finding(
            "disciplinary_silo", "no-such-record", "x" * 30,
            self._records())
        assert g["finding"] == "UNKNOWN"
        assert g["reason"] == "RECORD_ID_NOT_IN_RETRIEVED_SET"

    def test_allowed_findings_are_the_directive_enum(self):
        assert set(rec.WHY_NOT_ALLOWED_FINDINGS) == {
            "disciplinary_silo", "missing_measurement",
            "manufacturing_constraint", "integration_complexity",
            "economic_constraint", "environmental_mismatch",
            "control_mismatch", "historical_path_dependence",
            "overlooked_interaction", "UNKNOWN"}


# ---------------------------------------------------------------------------
# attacker caveat (directive item 10) + LIRY
# ---------------------------------------------------------------------------

class TestAttackerCaveatAndLiry:
    def test_caveat_is_not_calibrated_and_never_green(self):
        assert ATTACKER_CALIBRATION_STATUS[
            "attacker_calibration"] == "NOT_CALIBRATED"
        assert "universal-kill" in ATTACKER_CALIBRATION_STATUS[
            "measured_basis"]
        assert "NOT be silently converted" in \
            ATTACKER_CALIBRATION_STATUS["disposition"]

    def test_funnel_carries_the_caveat(self):
        f = build_recovery_funnel({
            "raw_accepted": 550, "unique_scored": 400,
            "recorded_technical_death": 13,
            "recorded_nontechnical_rejection": 387,
            "recorded_no_death_cause": 0, "other_terminal_state": 0,
            "gradient_eligible": 10, "gradient_attempted": 10,
            "present_rediscoveries": 2,
            "future_dependent_radar": 5,
            "unresolved_availability": 3,
            "normal_pipeline_survivors": 1})
        assert f["attacker_calibration_status"][
            "attacker_calibration"] == "NOT_CALIBRATED"
        assert f["liry"]["liry"] == 0.1
        assert f["liry"]["present_recovery_yield"] == 0.2
        assert "PRESENT_RECOVERY" in f["liry"][
            "principal_metric"]

    def test_funnel_missing_denominator_raises(self):
        counts = {
            "raw_accepted": 550, "unique_scored": 400,
            "recorded_technical_death": 13,
            "recorded_nontechnical_rejection": 387,
            "recorded_no_death_cause": 0, "other_terminal_state": 0,
            "gradient_eligible": 10, "gradient_attempted": 10,
            "present_rediscoveries": 0,
            "future_dependent_radar": 0,
            "unresolved_availability": 0}
        with pytest.raises(FunnelArithmeticError):
            build_recovery_funnel(counts)  # survivors missing


# ---------------------------------------------------------------------------
# the gradient span gates (GA-1b / TVM / backcast)
# ---------------------------------------------------------------------------

class TestGradientSpanGates:
    def test_deficit_extraction_verbatim_passes(self, frozen):
        death = frozen["waterfall"]["deaths"][0]
        cid = death["candidate_id"]
        cand = next(c for c in frozen["scored"]
                    if c["candidate_id"] == cid)
        reason = death["death_reason"]
        text = "\n".join([
            "DEFICIT_SPAN: " + reason[:80],
            "TARGET_CONSTRAINT: " + reason[:80],
            "REQUIRED_VALUE: NOT_STATED",
            "QUANTIFIED_GAP: 10-100x",
            "CAPABILITY_RUNG: actuation active alignment",
            "RUNG_DIRECTION: up",
            "FRONTIER_DOMAINS: semiconductor lithography, optics"])
        parsed = ga.parse_deficit_extraction(text)
        gate = ga.verify_deficit_extraction(parsed, death)
        assert gate["gate"] == "PASS"
        assert gate["capability_rung"] == \
            "actuation active alignment"

    def test_deficit_extraction_invention_fails(self, frozen):
        death = frozen["waterfall"]["deaths"][0]
        text = "\n".join([
            "DEFICIT_SPAN: a completely invented span that appears "
            "nowhere in the death record at all whatsoever",
            "TARGET_CONSTRAINT: another invented constraint span "
            "with plenty of length to pass the size gate",
            "REQUIRED_VALUE: 42 terawatts",
            "QUANTIFIED_GAP: 10-100x",
            "CAPABILITY_RUNG: magic capability rung",
            "RUNG_DIRECTION: up",
            "FRONTIER_DOMAINS: UNKNOWN"])
        parsed = ga.parse_deficit_extraction(text)
        gate = ga.verify_deficit_extraction(parsed, death)
        assert gate["gate"] == "FAIL"
        assert gate["status"] == "EXTRACTION_FAILED"

    def test_tvm_entries_verbatim_admitted(self):
        records = [{
            "record_id": "r1", "title":
                "Piezo actuator bandwidth trends",
            "abstract": "Measured closed-loop bandwidth rose from "
                        "120 Hz in 2015 to 900 Hz in 2024 across "
                        "the surveyed stages."}]
        text = ("ENTRY_1: precision motion | closed-loop bandwidth |"
                " 900 | Hz | 2024 | r1 | \"closed-loop bandwidth "
                "rose from 120 Hz in 2015 to 900 Hz in 2024\"")
        entries = ga.parse_tvm_entries(text)
        gate = ga.verify_tvm_entries(entries, records,
                                     "actuation active alignment")
        assert len(gate["admitted"]) == 1
        e = gate["admitted"][0]
        assert e["value"] == 900.0 and e["year"] == 2024
        assert e["provenance"]["verified_verbatim"] is True

    def test_tvm_entries_paraphrase_rejected(self):
        records = [{
            "record_id": "r1", "title": "t", "abstract":
                "Measured closed-loop bandwidth rose from 120 Hz in "
                "2015 to 900 Hz in 2024."}]
        text = ("ENTRY_1: motion | bandwidth | 900 | Hz | 2024 | r1 "
                "| \"the bandwidth got much better over the "
                "decade\"")
        gate = ga.verify_tvm_entries(ga.parse_tvm_entries(text),
                                     records, "rung")
        assert gate["admitted"] == []
        assert gate["rejected"][0]["reason"] == \
            "SPAN_NOT_VERBATIM_IN_RECORD"

    def test_tvm_slopes_need_two_points(self):
        tvm = {"entries": [
            {"capability_rung": "r", "domain": "d",
             "metric": "bw", "unit": "Hz", "value": 120,
             "year": 2015},
            {"capability_rung": "r", "domain": "d",
             "metric": "bw", "unit": "Hz", "value": 900,
             "year": 2024},
        ]}
        slopes = ga.tvm_slopes(tvm, "r")
        assert len(slopes) == 1
        assert slopes[0]["slope"] == pytest.approx(
            (900 - 120) / 9, rel=1e-3)

    def test_query_tvm_dead_without_movers(self):
        q = ga.query_tvm({"entries": [
            {"capability_rung": "r", "domain": "d",
             "metric": "bw", "unit": "Hz", "value": 900,
             "year": 2024}]}, "r")
        assert q["verdict"] == "DEAD_AT_TVM_QUERY"
        assert "cheapest" not in q["reason"]  # reason is honest
        assert "movement is not measured" in q["reason"]

    def test_tvm_snapshot_hash_and_freeze(self):
        snap = ga.build_tvm_snapshot(
            {"entries": [{"capability_rung": "r"}]})
        assert snap["frozen_before_ga4"] is True
        assert len(snap["sha256"]) == 64

    def test_backcast_parent_nodes_must_be_recorded(self, frozen):
        death = frozen["waterfall"]["deaths"][0]
        cid = death["candidate_id"]
        cand = next(c for c in frozen["scored"]
                    if c["candidate_id"] == cid)
        chain = [str(s) for s in cand["causal_chain"]]
        cap_line = (chain[0] if chain else "step") + " | 5 W | yes"
        text = "\n".join([
            "OUTCOME: o", "CAPABILITY: c", "TECHNOLOGY: t",
            "PHYSICAL_MECHANISM: m", "MANUFACTURING_METHOD: mm",
            "CONTROL_ARCHITECTURE: ca", "MATERIALS: mat",
            "COMPUTATION: comp", "MEASUREMENT: meas",
            f"PARENT_NODE_1: {chain[0] if chain else 'step'}",
            "PARENT_EDGE_1: 1 -> 1",
            "DESC_NODE_1: d1", "DESC_NODE_2: d2",
            "DESC_EDGE_1: 1 -> 2",
            "NEW_INTERACTION: d1 causes d2",
            "PREDICTED_NEW_EFFECT: e", "MEASUREMENT_PLAN: mp",
            "CAPABILITY_1: " + cap_line,
            "KILL_CONDITION: kc",
            f"CAPABILITY_SOURCE_SPAN: {death['death_reason'][:60]}"])
        parsed = ga.parse_backcast(text)
        assert parsed["parse_status"] == "OK"
        assert parsed["capabilities"][0]["name"] == (
            chain[0] if chain else "step")
        gate = ga.verify_backcast(parsed, cand, {
            "deficit_span": death["death_reason"][:60],
            "target_constraint": death["death_reason"][:60]})
        assert gate["gate"] == "PASS"

    def test_backcast_invented_parent_fails(self, frozen):
        death = frozen["waterfall"]["deaths"][0]
        cid = death["candidate_id"]
        cand = next(c for c in frozen["scored"]
                    if c["candidate_id"] == cid)
        text = "\n".join([
            "OUTCOME: o", "CAPABILITY: c", "TECHNOLOGY: t",
            "PHYSICAL_MECHANISM: m", "MANUFACTURING_METHOD: mm",
            "CONTROL_ARCHITECTURE: ca", "MATERIALS: mat",
            "COMPUTATION: comp", "MEASUREMENT: meas",
            "PARENT_NODE_1: an invented parent step that was never "
            "recorded in the candidate's causal chain at all",
            "PARENT_EDGE_1: 1 -> 1",
            "DESC_NODE_1: d1", "DESC_NODE_2: d2",
            "DESC_EDGE_1: 1 -> 2",
            "NEW_INTERACTION: d1 causes d2",
            "PREDICTED_NEW_EFFECT: e", "MEASUREMENT_PLAN: mp",
            "CAPABILITY_1: capability | 5 W | yes",
            "KILL_CONDITION: kc",
            "CAPABILITY_SOURCE_SPAN: " +
            death["death_reason"][:60]])
        parsed = ga.parse_backcast(text)
        gate = ga.verify_backcast(parsed, cand, {
            "deficit_span": death["death_reason"][:60],
            "target_constraint": death["death_reason"][:60]})
        assert gate["gate"] == "FAIL"
        assert any("not verbatim" in p for p in gate["problems"])

    def test_insufficient_frontier_is_honest_stop(self, frozen):
        parsed = ga.parse_backcast(
            "OUTCOME: x\nNEW_INTERACTION: INSUFFICIENT_FRONTIER "
            "the ranked movers do not carry the capability")
        gate = ga.verify_backcast(parsed, frozen["scored"][0], {})
        assert gate["gate"] == "HONEST_STOP"

    def test_sealed_verify_instrument_reused_unchanged(self):
        from discovery_fabric.r412.temporal_pipeline import \
            verify_capability
        assert ga.verify_instrument() is verify_capability


# ---------------------------------------------------------------------------
# the seal + the committed artifacts
# ---------------------------------------------------------------------------

class TestSealAndArtifacts:
    def test_seal_passes_on_committed_prereg(self):
        check = ga.verify_seal(_load(PREREG))
        assert check["seal_valid"] is True
        assert check["action"] == "RUN_ALLOWED"

    def test_gutted_prereg_refuses(self):
        prereg = _load(PREREG)
        del prereg["stopping_rules"]
        check = ga.verify_seal(prereg)
        assert check["seal_valid"] is False
        assert check["action"] == "REFUSE_RUN"
        assert "stopping_rules" in check["missing"]

    def test_accounting_artifact_matches_live_records(self, frozen,
                                                      accounting):
        art = _load(ACCOUNTING)
        assert art["population_sha256"] == \
            accounting["population_sha256"]
        assert art["headline_denominators"][
            "raw_accepted"] == 550
        assert art["headline_denominators"][
            "gradient_eligible"] == 10
        assert art["headline_denominators"][
            "gradient_attempted"] == 0
        assert art["no_model_calls"]["llm_calls"] == 0
        assert art["no_model_calls"]["retrieval_calls"] == 0

    def test_prereg_hashes_match_the_artifacts(self):
        prereg = _load(PREREG)
        assert prereg["population"]["population_sha256"] == \
            _load(ACCOUNTING)["population_sha256"]
        assert prereg["tvm_v0"]["sha256"] == hashlib.sha256(
            TVM_V0.read_bytes()).hexdigest()
        assert prereg["source_campaign"][
            "population_accounting_sha256"] == hashlib.sha256(
            ACCOUNTING.read_bytes()).hexdigest()

    def test_tvm_v0_is_schema_only_no_entries(self):
        snap = _load(TVM_V0)
        assert snap["entries"] == []
        assert snap["n_entries"] == 0
        assert "NO LLM-asserted numbers" in snap["schema"][
            "hard_rule"]

    def test_resource_allocation_covers_the_attempted_set(self):
        art = _load(ACCOUNTING)
        priority = art["resource_allocation"]["priority_order"]
        assert len(priority) == 10
        assert priority[0] == "C-wind-2"
        eligible = {r["candidate_id"] for r in
                    art["gradient_eligibility"]["rows"]
                    if r["eligibility"] in (
                        GRADIENT_ELIGIBLE,
                        GRADIENT_PRIOR_ART_SPECIAL_ROUTE)}
        assert set(priority) == eligible

    def test_temporal_control_arm_preserved(self):
        """The sealed temporal replay run record is byte-identical
        to its sealed hash (the control arm is never retro-edited)."""
        sha = hashlib.sha256(TEMPORAL_RUN.read_bytes()).hexdigest()
        assert sha == TEMPORAL_RUN_SHA
        assert _load(PREREG)["temporal_control_arm"][
            "run_record_sha256"] == TEMPORAL_RUN_SHA
        assert _load(ACCOUNTING)[
            "sealed_temporal_control_arm"]["result"].startswith(
            "0/13")

    def test_prereg_declares_supersession_and_principal_metric(
            self):
        prereg = _load(PREREG)
        assert "never the headline population" in \
            prereg["supersession"]["what_changed"]
        assert "PRESENT_RECOVERY" in prereg["purpose"]
        assert "not the principal" in prereg["purpose"] or \
            "NOT the principal" in prereg["purpose"]
        assert prereg["status"] == "SEALED_BY_COMMIT"

    def test_runner_refuses_without_seal(self, monkeypatch,
                                         tmp_path):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "r412_run_gradient_arm",
            REPO / "scripts" / "r412_run_gradient_arm.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # quarantine the run directory too (Art. IX: a test never
        # mutates production state, even on paths that today return
        # before writing)
        monkeypatch.setattr(mod, "OUT_DIR", tmp_path / "run")
        monkeypatch.setattr(mod, "PREREG", tmp_path / "nope.json")
        rc = mod.stage_seal()
        assert rc == 1


# ---------------------------------------------------------------------------
# the population accounting vs the pre-existing R412 artifacts
# (cross-artifact consistency: no orphan numbers)
# ---------------------------------------------------------------------------

class TestCrossArtifactConsistency:
    def test_technical_deaths_match_the_waterfall(self, frozen,
                                                  accounting):
        wf_tech = {
            d["candidate_id"] for d in frozen["waterfall"]["deaths"]
            if d["death_cause"] in rec.TECHNICAL_DEATH_CAUSES}
        acc_tech = set(accounting["technical_death_subset"]
                       ["candidate_ids"])
        assert acc_tech == wf_tech

    def test_temporal_attempted_13_is_a_subset_here(self,
                                                    accounting):
        """The temporal arm's 13 attempted targets are exactly the
        technical-death subset — reported as a SUBSET of the 400,
        not as the population."""
        art = _load(ACCOUNTING)
        assert len(art["technical_death_subset"][
            "candidate_ids"]) == 13
        assert art["headline_denominators"]["unique_scored"] == 400


# ---------------------------------------------------------------------------
# ALLOCATION-ORDER REPAIR tests (pre-first-model-call, 2026-09-06):
# the sealed 10-seed priority allocation IS the attempted set. These
# tests are the falsifiers for the repair: an ineligible seed that
# reaches GA-3/GA-4, or a backcast spent outside the allocation,
# or an allocation rung starved by non-allocation rungs under the
# sealed construction cap, all FAIL here. Art. XVII: the attempted
# bypass IS the test.
# ---------------------------------------------------------------------------

def _load_runner_module(monkeypatch, tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "r412_run_gradient_arm_alloc_test",
        REPO / "scripts" / "r412_run_gradient_arm.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Art. IX: a test never mutates production state. The path
    # globals are module constants computed at import time, so each
    # is patched explicitly (patching OUT_DIR alone is not enough).
    run = tmp_path / "run"
    run.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(mod, "OUT_DIR", run)
    monkeypatch.setattr(mod, "TVM_FROZEN", run / "TVM_FROZEN.json")
    monkeypatch.setattr(mod, "TVM_CONSTRUCTED",
                        run / "TVM_CONSTRUCTED.json")
    return mod


class TestAllocationEnforcement:
    PREREG_PRIORITY = None  # loaded lazily from the real artifact

    @property
    def priority(self):
        if self.PREREG_PRIORITY is None:
            self.PREREG_PRIORITY = _load(PREREG)[
                "resource_allocation"]["priority_order"]
        return self.PREREG_PRIORITY

    def test_ga3_queries_exactly_the_sealed_allocation_in_order(
            self, monkeypatch, tmp_path):
        """13 GA-1b-OK seeds (10 allocation + 3 ineligible) -> GA-3
        records exist ONLY for the 10 allocation seeds, in the sealed
        priority order. The ineligible regime/consistency deaths
        never enter the gradient machinery."""
        mod = _load_runner_module(monkeypatch, tmp_path)
        ga1b = []
        for cid in _load(ACCOUNTING)["technical_death_subset"][
                "candidate_ids"]:
            ga1b.append({
                "candidate_id": cid, "status": "OK",
                "gate": {"capability_rung": f"rung-{cid}"}})
        (mod.OUT_DIR / "ga1b.jsonl").write_text(
            "\n".join(json.dumps(r) for r in ga1b))
        # a TVM with a measured mover on every rung
        entries = []
        for cid in _load(ACCOUNTING)["technical_death_subset"][
                "candidate_ids"]:
            for year, val in ((2020, 10.0), (2024, 50.0)):
                entries.append({
                    "capability_rung": f"rung-{cid}",
                    "domain": "d", "metric": "m", "value": val,
                    "unit": "u", "year": year})
        tvm_frozen = {"entries": entries}
        mod.TVM_FROZEN.write_text(json.dumps(tvm_frozen))
        rc = mod.stage_ga3()
        assert rc == 0
        lines = [json.loads(x) for x in
                 (mod.OUT_DIR / "ga3.jsonl").read_text().
                 splitlines() if x.strip()]
        recorded = [l["candidate_id"] for l in lines]
        assert recorded == self.priority
        assert len(recorded) == 10

    def test_ga4_refuses_backcast_outside_the_allocation(
            self, monkeypatch, tmp_path):
        """A forged GA-3 FAST_MOVERS_RANKED record for a
        non-allocation seed cannot buy a backcast: no LLM call, no
        GA-4 record (the budget is never re-allocated to
        non-eligible candidates)."""
        mod = _load_runner_module(monkeypatch, tmp_path)
        mod.TVM_FROZEN.write_text(json.dumps({"entries": []}))
        ineligible = "C-heat_exchanger-1~4"  # regime violation death
        assert ineligible not in self.priority
        ga3_rec = {"candidate_id": ineligible,
                   "verdict": "FAST_MOVERS_RANKED", "rung": "r"}
        (mod.OUT_DIR / "ga3.jsonl").write_text(
            json.dumps(ga3_rec))
        called = []

        def _no_llm(*a, **k):
            called.append(a)
            raise AssertionError(
                "backcast spent outside the sealed allocation")

        monkeypatch.setattr(mod, "_llm", _no_llm)
        rc = mod.stage_ga4()
        assert rc == 0
        assert not called
        assert not (mod.OUT_DIR / "ga4.jsonl").exists()

    def test_tvm_build_constructs_allocation_rungs_first(
            self, monkeypatch, tmp_path):
        """Under the sealed construction cap, the 10 allocation
        rungs are built BEFORE any non-allocation rung; the
        rung left unbuilt by the cap is recorded
        INCOMPLETE_BUDGET_SHORTFALL — never silently dropped."""
        mod = _load_runner_module(monkeypatch, tmp_path)
        all_seeds = _load(ACCOUNTING)["technical_death_subset"][
            "candidate_ids"]
        ga1b = [{"candidate_id": cid, "status": "OK",
                 "gate": {"capability_rung": f"rung-{cid}"}}
                for cid in all_seeds]
        (mod.OUT_DIR / "ga1b.jsonl").write_text(
            "\n".join(json.dumps(r) for r in ga1b))
        records = [{"record_id": "r-1", "title": "t",
                    "abstract": "a measured 5 unit trend"}]
        monkeypatch.setattr(
            mod, "_retrieve", lambda q: (records, {}))
        monkeypatch.setattr(
            mod, "_llm",
            lambda *a, **k: {"ok": True, "content": "", "model":
                             "test", "prompt_hash": "h",
                             "output_hash": "h"})
        # 13 distinct rungs, cap 12: the 13th must be a
        # NON-allocation rung
        rc = mod.stage_tvm_build(12)
        assert rc == 0
        tvm = json.loads(mod.TVM_CONSTRUCTED.read_text())
        log = tvm["construction_log"]
        attempted = [str(e["rung"]) for e in log
                     if e.get("n_retrieved") is not None]
        allocation_rungs = {f"rung-{cid}"
                            for cid in self.priority}
        shortfall = [e for e in log if e.get("status") ==
                     "INCOMPLETE_BUDGET_SHORTFALL"]
        assert len(attempted) == 12
        # every allocation rung was attempted
        assert allocation_rungs <= set(attempted)
        # the starved rung is NOT an allocation rung
        assert len(shortfall) == 1
        assert str(shortfall[0]["rung"]) not in allocation_rungs

    def test_tvm_build_never_reattempts_a_completed_rung(
            self, monkeypatch, tmp_path):
        """A rung with a completed attempt (even zero admitted
        entries) is terminal for construction: re-invocation cannot
        fish for better entries (rejected entries are recorded,
        never repaired)."""
        mod = _load_runner_module(monkeypatch, tmp_path)
        ga1b = [{"candidate_id": self.priority[0], "status": "OK",
                 "gate": {"capability_rung": "rung-a"}}]
        (mod.OUT_DIR / "ga1b.jsonl").write_text(
            json.dumps(ga1b[0]))
        records = [{"record_id": "r-1", "title": "t",
                    "abstract": "a"}]
        monkeypatch.setattr(
            mod, "_retrieve", lambda q: (records, {}))
        monkeypatch.setattr(
            mod, "_llm",
            lambda *a, **k: {"ok": True, "content": "", "model":
                             "test", "prompt_hash": "h",
                             "output_hash": "h"})
        assert mod.stage_tvm_build() == 0
        calls = []
        monkeypatch.setattr(
            mod, "_retrieve",
            lambda q: (calls.append(q), records, {})[1:])
        assert mod.stage_tvm_build() == 0
        assert calls == []  # no re-attempt of the completed rung
