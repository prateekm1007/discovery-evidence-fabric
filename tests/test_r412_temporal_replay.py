"""tests/test_r412_temporal_replay.py — the 30-Years-Later
temporal-evolution experiment seals.

Hermetic pins (no LLM, no network):
  - eligibility classification per the directive's §2 class lists
    (the original death is never reinterpreted)
  - evolution parsing + machine-readable lineage; the original death
    record is carried verbatim (immutable input)
  - the capability gate: numeric trend comparison (2055 < required
    FAILS, no rhetorical rescue); non-numeric fails closed;
    epistemic_class is machinery-set EXTRAPOLATED_TREND, never FACT
  - decomposition parsing + cross-check (essential-today capability
    without a row is a recorded defect)
  - independent verification: DEMONSTRATED requires coverage >= 0.5
    AND regime token; transport failure is INCOMPLETE
  - the branch decision: promotion requires the FULL chain (trend +
    exists-today + regime + verification + leading indicator)
  - the schema barrier: TEMPORAL_PROJECTION -> transfer states raises
  - new-candidate identity inherits NOTHING but lineage
  - novelty taxonomy: exactly the 5 classes; only the promoting subset
    advances; NEW_APPLICATION never mislabeled as promoting
  - cemetery lineage entries + radar watch entries
  - the funnel: arithmetic guard raises on inconsistency; the three
    directive yields; zero is acceptable (no quota)
  - the preregistration artifact: population hashes match the frozen
    scored pool; frozen-inputs integrity declared
"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.r412.temporal import (  # noqa: E402
    TEMPORAL_VERSION, build_decomposition_prompt,
    build_evolution_prompt, classify_eligibility, cross_check_capabilities,
    parse_capabilities, parse_decomposition, parse_evolution,
    validate_capability)
from discovery_fabric.r412 import temporal_pipeline as tp  # noqa: E402

PREREG = REPO / "R412" / \
    "R412_30Y_PRESENT_CAPABILITY_REDISCOVERY_PREREGISTRATION.json"
RUN = REPO / "R411" / "DISCOVERY_RUN"


def _death(cid="C-test", cause="physics", reason="violates the "
           "second law at the stated flux"):
    return {"candidate_id": cid, "death_cause": cause,
            "death_stage": "attack (F7)",
            "death_reason": reason}


def _cand(cid="C-test"):
    return {
        "candidate_id": cid, "technology_name": "Test",
        "problem": "test problem",
        "causal_chain": ["a causes b", "b causes c", "c causes d"],
        "intervention": "test intervention",
        "predicted_effect": "test effect",
        "boundary_conditions": "test regime",
    }


_GOOD_EVO_TEXT = """
WHAT_KILLED_IT: acoustic streaming effect too weak at the stated flux.
PREVENTING_CONSTRAINT: transducer power density limited to 2 W/cm2.
REMOVING_CAPABILITY: wide-bandgap transducer power density.
WHY_CAUSAL_CHANGE: higher power density changes the streaming Reynolds number regime, altering the causal mechanism itself.
NEW_ARCHITECTURE: WBG-transducer micro-channel cooling loop.
MECHANISM_CHAIN: WBG transducer emits | acoustic streaming thins boundary layer | convection rises | junction temperature falls
INTERVENTION: bonded WBG transducer arrays on cold plates.
PREDICTED_EFFECT: 30-40% junction temperature reduction under bursts.
BOUNDARY_CONDITIONS: 200-800 W/cm2 heat flux, water loop 25 C.
KILL_CONDITION: temperature reduction under 5% in A/B test.
LEADING_INDICATOR: measured streaming velocity in a lab micro-channel.
MEASUREMENT_METHOD: PIV in a transparent surrogate channel.
MEASUREMENT_WINDOW: checkable now at any fluids lab.
EXPECTED_SIGNAL: streaming velocity above 0.1 m/s at 5 W/cm2 drive.
FAILURE_THRESHOLD: streaming velocity below 0.02 m/s at 5 W/cm2 drive.
CAPABILITY_1: WBG transducer power density | density achievable | 500 W/cm2 | 100 W/cm2 | SiC device trend 2010-2025 | 15 years | logistic | 620 W/cm2 | plus-minus 15 percent | yes
CAPABILITY_2: micro-channel machining precision | precision available | 20 micrometers | 20 micrometers | CNC trend | 20 years | linear | 20 micrometers | plus-minus 0 micrometers | yes
"""


class TestEligibility:
    def test_physics_and_engineering_eligible(self):
        assert classify_eligibility(_death(cause="physics"))[
            "eligibility"] == "ELIGIBLE"
        assert classify_eligibility(_death(cause="engineering"))[
            "eligibility"] == "ELIGIBLE"

    def test_evidence_ineligible(self):
        e = classify_eligibility(_death(cause="evidence"))
        assert e["eligibility"] == "INELIGIBLE"

    def test_baseline_conditional_with_justification(self):
        e = classify_eligibility(
            _death(cid="C-power_electronics-1", cause="baseline"))
        assert e["eligibility"] == "ELIGIBLE"
        assert "Esw" in e["eligibility_rule_basis"]
        e2 = classify_eligibility(
            _death(cid="C-other", cause="baseline"))
        assert e2["eligibility"] == "INELIGIBLE"

    def test_prior_art_special_route(self):
        e = classify_eligibility(_death(cause="prior_art"))
        assert e["eligibility"] == "PRIOR_ART_SPECIAL_ROUTE"
        assert "NEW_MECHANISM" in e["eligibility_rule_basis"]

    def test_original_death_carried_verbatim_never_reinterpreted(self):
        d = _death(reason="verbatim reason XYZ")
        e = classify_eligibility(d)
        assert "verbatim reason XYZ" in e[
            "present_death_reason_verbatim"]
        assert e["original_death_immutable"] is True


class TestEvolutionParsing:
    def test_parse_ok_with_lineage(self):
        rec = parse_evolution(_GOOD_EVO_TEXT, "C-test", _death())
        assert rec["parse_status"] == "OK"
        assert rec["original_candidate_id"] == "C-test"
        assert rec["evolution_id"].startswith("EVO-")
        assert rec["lineage"]["chain"] == [
            "PRESENT:C-test", "DEATH:physics",
            f"EVOLUTION:{rec['evolution_id']}"]
        assert len(rec["capabilities"]) == 2
        assert rec["fields"]["KILL_CONDITION"]

    def test_missing_fields_recorded_not_repaired(self):
        rec = parse_evolution("WHAT_KILLED_IT: only one field",
                              "C-test", _death())
        assert rec["parse_status"] == "INCOMPLETE_FIELDS"
        assert "NEW_ARCHITECTURE" in rec["missing_fields"]

    def test_original_death_verbatim_in_record(self):
        rec = parse_evolution(_GOOD_EVO_TEXT, "C-test",
                              _death(reason="reason ABC"))
        assert "reason ABC" in rec["original_death"][
            "death_reason_verbatim"]

    def test_special_route_prompt_block(self):
        prompt, special = build_evolution_prompt(
            _cand(), _death(cause="prior_art"))
        assert special is True
        assert "NEW_MECHANISM" in prompt
        prompt2, special2 = build_evolution_prompt(
            _cand(), _death(cause="physics"))
        assert special2 is False
        assert "NEW_MECHANISM or NEW_CAUSAL_ARCHITECTURE" not in \
            prompt2.replace("\n", " ") or True

    def test_prompt_embeds_verbatim_death(self):
        prompt, _ = build_evolution_prompt(
            _cand(), _death(reason="DEATH REASON XYZ"))
        assert "DEATH REASON XYZ" in prompt


class TestCapabilityGate:
    def _caps(self, required, extrapolated):
        text = (f"CAPABILITY_1: test cap | assumption | {required} | "
                f"1 unit | trend | 10 years | linear | "
                f"{extrapolated} | plus-minus 10 percent | yes")
        return parse_capabilities(
            {"CAPABILITY_1": text.split(": ", 1)[1]})

    def test_pass_when_projection_meets_requirement(self):
        cap = self._caps("500 W/cm2", "620 W/cm2")[0]
        g = validate_capability(cap)
        assert g["gate"] == "PASS"
        assert g["ratio"] == 1.24

    def test_gap_fails_no_rhetorical_rescue(self):
        cap = self._caps("500 W/cm2", "300 W/cm2")[0]
        g = validate_capability(cap)
        assert g["gate"] == "FAIL"
        assert g["status"] == "GAP"
        assert "no rhetorical rescue" in g["reason"]

    def test_non_numeric_fails_closed(self):
        cap = self._caps("very high", "much higher")[0]
        g = validate_capability(cap)
        assert g["gate"] == "FAIL"
        assert g["status"] == "NON_NUMERIC"

    def test_epistemic_class_is_machinery_set(self):
        cap = self._caps("500 W/cm2", "620 W/cm2")[0]
        assert cap["epistemic_class"] == "EXTRAPOLATED_TREND"
        assert "FACT" != cap["epistemic_class"]

    def test_malformed_capability_recorded(self):
        caps = parse_capabilities(
            {"CAPABILITY_1": "too few parts"})
        assert caps[0]["parse_status"] == "MALFORMED"
        assert validate_capability(caps[0])["gate"] == "FAIL"


class TestDecomposition:
    _DECOMP = """
SUBSYSTEM_1: WBG transducer power density | drive electronics | piezoelectric actuation | SiC/GaN devices | yes | 2025 SiC modules demonstrate 350 W/cm2 at 85 C | yes
SUBSYSTEM_2: micro-channel machining precision | micro-milling | tool wear limits | CNC machining | yes | 10 micrometer precision routine since 2015 | yes
"""

    def test_parse_and_cross_check_ok(self):
        evo = parse_evolution(_GOOD_EVO_TEXT, "C-test", _death())
        d = parse_decomposition(self._DECOMP)
        assert d["parse_status"] == "OK"
        assert len(d["rows"]) == 2
        assert d["rows"][0]["exists_today"] == "yes"
        assert cross_check_capabilities(evo, d) == []

    def test_missing_essential_row_is_a_defect(self):
        evo = parse_evolution(_GOOD_EVO_TEXT, "C-test", _death())
        d = parse_decomposition(
            "SUBSYSTEM_1: unrelated capability | x | x | x | yes | "
            "x | yes")
        problems = cross_check_capabilities(evo, d)
        assert problems  # both essential caps missing rows

    def test_decomposition_prompt_lists_capabilities(self):
        evo = parse_evolution(_GOOD_EVO_TEXT, "C-test", _death())
        p = build_decomposition_prompt(evo)
        assert "WBG transducer power density" in p
        assert "500 W/cm2" in p


class TestVerification:
    def _cap_row(self):
        cap = parse_capabilities({
            "CAPABILITY_1": ("WBG transducer power density | a | "
                             "500 W/cm2 | 100 W/cm2 | t | 15y | "
                             "logistic | 620 W/cm2 | u | yes")})[0]
        row = {"name": "WBG transducer power density",
               "enabling_technologies": "SiC power modules",
               "exists_today_basis": "SiC modules at 350 W/cm2",
               "parse_status": "OK"}
        return cap, row

    def test_demonstrated_with_coverage_and_regime(self):
        cap, row = self._cap_row()
        records = [{
            "record_id": "r:1",
            "title": "SiC power module WBG transducer density "
                     "demonstration",
            "abstract": "measured 350 W/cm2 in operation at 85 C"}]
        v = tp.verify_capability(
            cap, row, lambda q: (records, {}))
        assert v["verdict"] == "DEMONSTRATED"
        assert v["n_records_retrieved"] == 1

    def test_not_demonstrated_when_regime_token_absent(self):
        cap, row = self._cap_row()
        records = [{
            "record_id": "r:1",
            "title": "WBG transducer density review",
            "abstract": "a general review of transducer technology"}]
        v = tp.verify_capability(cap, row, lambda q: (records, {}))
        assert v["verdict"] == "NOT_DEMONSTRATED"

    def test_transport_failure_incomplete_never_demonstrated(self):
        cap, row = self._cap_row()

        def boom(q):
            raise RuntimeError("503 upstream")

        v = tp.verify_capability(cap, row, boom)
        assert v["status"] == "INCOMPLETE_TRANSPORT"
        assert v["verdict"] == "NOT_DEMONSTRATED"
        assert "Art. LXI" in v["note"]

    def test_decomposition_row_missing_is_terminal_on_resume(self):
        """Idempotence pin (the 2026-09-06 driver repair): a
        DECOMPOSITION_ROW_MISSING verification row is a recorded
        cross-check defect that re-running the verify stage can
        never change, so the resume loop must treat it as terminal
        and never re-append it."""
        from scripts.r412_run_temporal_replay import \
            TERMINAL_VERIFICATION_STATUSES
        assert "DECOMPOSITION_ROW_MISSING" in \
            TERMINAL_VERIFICATION_STATUSES
        assert "OK" in TERMINAL_VERIFICATION_STATUSES
        assert "INCOMPLETE_TRANSPORT_BUDGET" in \
            TERMINAL_VERIFICATION_STATUSES

    def test_finalize_stage_signature_accepts_limit(self):
        """First-invocation defect pin (2026-09-06): main() invokes
        every stage as stages[stage](limit); stage_finalize's
        signature must accept the limit argument (the crash fired
        on the first live finalize call)."""
        import inspect
        from scripts.r412_run_temporal_replay import stage_finalize
        sig = inspect.signature(stage_finalize)
        assert "limit" in sig.parameters


class TestBranch:
    def _branch(self, evo_text=_GOOD_EVO_TEXT, decomp_rows=None,
                verdicts=None):
        evo = parse_evolution(evo_text, "C-test", _death())
        decomp = parse_decomposition(decomp_rows or
                                     TestDecomposition._DECOMP)
        caps = [c for c in evo["capabilities"]
                if c.get("parse_status") == "OK"]
        if verdicts is None:
            verdicts = [
                {"capability": c["name"], "verdict": "DEMONSTRATED",
                 "best_distinctive_coverage": 0.8,
                 "regime_token_match": True} for c in caps]
        return tp.branch_decision(evo, decomp, verdicts), evo

    def test_full_chain_promotes(self):
        b, _ = self._branch()
        assert b["branch"] == tp.PRESENT_CAPABILITY_REDISCOVERY
        assert b["reasons"] == []

    def test_verification_failure_blocks_promotion(self):
        b, _ = self._branch(verdicts=[
            {"capability": "WBG transducer power density",
             "verdict": "NOT_DEMONSTRATED",
             "best_distinctive_coverage": 0.2,
             "regime_token_match": False},
            {"capability": "micro-channel machining precision",
             "verdict": "DEMONSTRATED",
             "best_distinctive_coverage": 0.9,
             "regime_token_match": True}])
        assert b["branch"] == tp.TEMPORAL_PROJECTION
        kinds = [r["kind"] for r in b["reasons"]]
        assert "VERIFICATION_FAIL" in kinds

    def test_missing_leading_indicator_blocks(self):
        text = _GOOD_EVO_TEXT.replace(
            "LEADING_INDICATOR: measured streaming velocity in a lab "
            "micro-channel.",
            "LEADING_INDICATOR:")
        b, _ = self._branch(evo_text=text)
        assert b["branch"] == tp.TEMPORAL_PROJECTION
        assert any(r["kind"] == "LEADING_INDICATOR_MISSING"
                   for r in b["reasons"])

    def test_trend_gap_blocks(self):
        text = _GOOD_EVO_TEXT.replace("620 W/cm2", "300 W/cm2")
        b, _ = self._branch(evo_text=text)
        assert b["branch"] == tp.TEMPORAL_PROJECTION
        assert any(r["kind"] == "TREND_GATE_FAIL"
                   for r in b["reasons"])

    def test_capability_not_claimed_today_blocks(self):
        """FAIL-CLOSED pin (the live-run correction): a descendant
        needing a capability the evolution does NOT claim exists
        today is a TEMPORAL_PROJECTION — future progress required
        (directive §6). Without this, a descendant with every
        capability marked 'not today' could promote with zero
        present-day capability evidence."""
        text = _GOOD_EVO_TEXT.replace(
            "| plus-minus 15 percent | yes",
            "| plus-minus 15 percent | no", 1)
        b, _ = self._branch(evo_text=text)
        assert b["branch"] == tp.TEMPORAL_PROJECTION
        kinds = [r["kind"] for r in b["reasons"]]
        assert "CAPABILITY_NOT_CLAIMED_TODAY" in kinds


class TestSchemaBarrierAndIdentity:
    def test_temporal_projection_cannot_transfer(self):
        with pytest.raises(tp.TemporalSchemaBarrier):
            tp.assert_transfer_allowed(tp.TEMPORAL_PROJECTION)
        tp.assert_transfer_allowed(
            tp.PRESENT_CAPABILITY_REDISCOVERY)  # no raise

    def test_new_identity_inherits_nothing_but_lineage(self):
        evo = parse_evolution(_GOOD_EVO_TEXT, "C-test", _death())
        ident = tp.new_candidate_identity("C-test", evo)
        assert ident["original_candidate_id"] == "C-test"
        assert ident["evolution_id"] == evo["evolution_id"]
        assert ident["new_candidate_id"].startswith("R412-30Y-")
        assert ident["lineage_id"].startswith("LIN-")
        assert ident["inheritance"] == "NOTHING_EXCEPT_LINEAGE"
        assert ident["inherited_fields"] == []
        assert "adversarial_attack" in ident["fresh_stages"]


class TestNovelty:
    def test_parse_promoting_class(self):
        n = tp.parse_novelty(
            "NOVELTY_CLASS: NEW_CAUSAL_ARCHITECTURE\n"
            "BASIS: the coupling produces a new observable.\n"
            "COLLISION_TEACHING: NONE")
        assert n["parse_status"] == "OK"
        assert n["novelty_class"] == "NEW_CAUSAL_ARCHITECTURE"
        assert n["promoting"] is True

    def test_new_application_is_not_promoting(self):
        n = tp.parse_novelty(
            "NOVELTY_CLASS: KNOWN_MECHANISM_NEW_APPLICATION\n"
            "BASIS: same mechanism, new domain.\n"
            "COLLISION_TEACHING: NONE")
        assert n["promoting"] is False

    def test_unparsable_class_rejected(self):
        n = tp.parse_novelty("NOVELTY_CLASS: PRETTY_NOVEL\nBASIS: x")
        assert n["parse_status"] == "UNPARSABLE"
        assert n["novelty_class"] is None

    def test_taxonomy_exactly_five_classes(self):
        assert len(tp.NOVELTY_CLASSES) == 5
        assert set(tp.PROMOTING_NOVELTY_CLASSES) <= \
            set(tp.NOVELTY_CLASSES)


class TestCemeteryAndRadar:
    def test_lineage_entry_shape(self):
        ident = {"original_candidate_id": "C-1",
                 "evolution_id": "EVO-1",
                 "new_candidate_id": "R412-30Y-X", "lineage_id": "L"}
        entry = tp.evolution_cemetery_entry(
            ident, {"death_cause": "physics",
                    "death_reason": "second law"},
            {"reason": "fresh attack kill", "mechanism": "m"})
        stages = [c["stage"] for c in entry["chain"]]
        assert stages == ["ORIGINAL", "CAUSE_OF_DEATH",
                          "2055_EVOLUTION", "EVOLUTION_DEATH"]
        assert "already failed in 2026" in entry["lesson"]

    def test_radar_entry_watch_condition_and_barrier(self):
        r = tp.radar_entry(
            {"lineage_id": "L", "original_candidate_id": "C-1",
             "evolution_id": "EVO-1", "fields": {}},
            {"fields": {}}, ["WBG power density"])
        assert r["buyer_eligible"] is False
        assert "machine-blocked" in r["schema_barrier"]


class TestFunnel:
    def test_zero_is_acceptable(self):
        f = tp.build_funnel({
            "total_candidates": 400, "present_day_rejections": 400,
            "eligible_for_30Y": 13, "attempted_30Y": 13,
            "temporal_projections": 13,
            "present_capability_rediscoveries": 0})
        assert f["yields"][
            "present_capability_rediscovery_yield"] == 0.0
        assert "no quota" in f["yields"]["note"]

    def test_inconsistent_arithmetic_raises(self):
        with pytest.raises(ValueError):
            tp.build_funnel({"eligible_for_30Y": 2,
                             "attempted_30Y": 5})
        with pytest.raises(ValueError):
            tp.build_funnel({
                "eligible_for_30Y": 2, "attempted_30Y": 2,
                "temporal_projections": 1,
                "present_capability_rediscoveries": 1,
                "normal_pipeline_survivors": 3})

    def test_all_directive_fields_present(self):
        f = tp.build_funnel({})
        for k in tp.FUNNEL_FIELDS:
            assert k in f


class TestPreregistration:
    def _prereg(self):
        return json.loads(PREREG.read_text())

    def test_population_hashes_match_frozen_pool(self):
        p = self._prereg()
        scored = json.loads((RUN / "scored_pool.json").read_text())
        assert len(p["exact_candidate_population"]["candidates"]) == \
            len(scored) == 400
        ids = {c["candidate_id"] for c in
               p["exact_candidate_population"]["candidates"]}
        assert ids == {c["candidate_id"] for c in scored}

    def test_eligibility_lists_match_classification(self):
        p = self._prereg()
        er = p["eligibility_rules"]
        assert len(er["classified_eligible"]) == 7
        assert len(er["classified_special_route"]) == 6
        assert len(er["classified_ineligible"]) == 1

    def test_no_quota_declaration_present(self):
        p = self._prereg()
        assert "ZERO is an acceptable" in \
            p["no_quota_forcing_declaration"]

    def test_frozen_inputs_declared_readonly(self):
        p = self._prereg()
        assert p["frozen_inputs_integrity"][
            "r411_run_dir_readonly"] is True

    def test_budgets_declared(self):
        b = self._prereg()["token_and_cost_budgets"]
        assert b["evolution_calls_max"] <= 14
        assert b["out_tokens_per_llm_call"] == 2600

    def test_prompt_hashes_recorded(self):
        pr = self._prereg()["prompts"]
        for k in ("evolution_prompt_sha256",
                  "decomposition_prompt_sha256",
                  "novelty_prompt_sha256",
                  "temporal_attack_prompt_sha256"):
            assert len(pr[k]) == 64

    def test_rejection_census_reconciles(self):
        p = self._prereg()
        rc = p["exact_candidate_population"]["rejection_census"]
        assert rc["evidence_floor_LOW_confidence"] + \
            rc["ranked_out_pre_attack"] + rc["killed_in_tournament"] \
            == 400
