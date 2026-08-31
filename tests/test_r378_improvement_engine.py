"""tests/test_r378_improvement_engine.py — adversarial test suite for
the R378 TECHNICAL IMPROVEMENT ENGINE.

Constitutional mandate (Art. V/VIII/XVII): every control gets positive,
negative and metamorphic tests, INCLUDING attempted bypasses:

  ATTACKED BYPASSES
  - fabricated evidence span (Art. VI — provenance forgery attempt)
  - untriggered/off-target mutation (CEO rule 8 — score-chasing)
  - no-op mutation (cosmetic 'improvement')
  - negative-erasure mutation (CEO rule 10 — contradiction laundering)
  - UNKNOWN -> MEASURED conversion (Art. XXV — certainty laundering)
  - residue claimed against absent art (Art. XXI.2 — novelty from
    absence)
  - entity-shift laundering (mutate into a new domain while
    re-adjudicating against stale cached art)
  - EXPERIMENT-tier evaluator registration (Art. XXXVIII — software
    declaring physical-observation authority)

All tests are HERMETIC: the LLM proposer is mocked; no network; no
live keys (conftest guarantee).
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

from discovery_fabric.engine import evaluator_contract as ec  # noqa: E402
from discovery_fabric.engine import improvement_engine as ie  # noqa: E402
from discovery_fabric.benchmark import invention_quality as iq  # noqa: E402


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
EVIDENCE_ABSTRACT = (
    "Acoustic emission sensing of lithium-ion battery cells detects "
    "internal gas generation events preceding thermal runaway. We "
    "report that a piezoelectric acoustic emission sensor bonded to the "
    "cell casing measures parabolic gas-driven surface vibrations at "
    "180-220 kHz, and that the onset of vibration amplitude growth "
    "precedes measurable temperature rise by 40-90 seconds, enabling "
    "pre-emptive disconnection of the cell before venting.")

EV_ITEMS = [{"id": "evidence:acoustic-1",
             "title": "Acoustic emission precedes thermal runaway",
             "text": EVIDENCE_ABSTRACT,
             "content_hash": "deadbeef01"}]

FAMILY_TEXT_A = (
    "Battery pack thermal management with cooling plates. A lithium "
    "battery pack comprises cooling plates and a temperature sensor "
    "coupled to a controller that disconnects the pack when temperature "
    "exceeds a threshold. Gas generation is monitored by a pressure "
    "sensor inside the pack housing.")

FAMILY_TEXT_B = (
    "Piezoelectric vibration monitoring of rotating machinery for early "
    "bearing fault detection. The accelerometer senses mechanical "
    "vibration signatures of the bearing assembly and a controller "
    "halts the machine on anomaly detection.")


def _family(fid: str, text: str, tier: str = "ABSTRACT") -> dict:
    return {
        "family_id": fid,
        "representative": {
            "patent_id": f"US00000{fid[-1]}",
            "title": text[:60],
            "source_id": "LENS_PATENT", "source_url": "https://x/y",
            "assignee": "TEST", "publication_date": "2020-01-01"},
        "family_size": 1, "member_patent_ids": [f"US00000{fid[-1]}"],
        "evidence_tier": tier, "claims_fetch_status": "OK",
        "claims_fetch_path": "fixture",
        "adjudicated_text_excerpt": text,
        "adjudicated_text_sha256": hashlib.sha256(
            text.encode()).hexdigest(),
        "coverage": {},
    }


def _spec(intervention: str = "dual pressure sensors with independent "
                               "signal processing along the infusion path",
          mechanism: str = "Pressure monitoring with redundant sensors",
          span: str = "While there is overlap with existing literature "
                      "on intrathecal baclofen therapy, the clinical "
                      "presentation is distinct.",
          experiment: str = "fetch and audit claims of nearest collision "
                            "patents",
          families=None, uncertainties=None,
          surviving=None,
          evidence_title: str = "Acoustic emission precedes thermal "
                                "runaway") -> dict:
    families = families if families is not None else [
        _family("fam-a", FAMILY_TEXT_A), _family("fam-b", FAMILY_TEXT_B)]
    unc = uncertainties if uncertainties is not None else [
        {"contradiction_id": "con-1", "description": "open contradiction",
         "severity": "HIGH"}]
    surviving = surviving if surviving is not None else [
        "acoustic", "dual", "independent"]
    vs_nearest = [
        {"patent_id": f["representative"]["patent_id"],
         "title": f["representative"]["title"],
         "family_id": f["family_id"], "family_size": 1,
         "evidence_tier": f["evidence_tier"],
         "coverage_class": "PARTIAL_COVER", "coverage_ratio": 0.3,
         "mechanism_overlap_terms": ["battery", "sensor"],
         "distinguishing_terms_covered": ["battery", "pack"],
         "distinguishing_terms_surviving": surviving}
        for f in families]
    return {
        "invention_id": {"value": "inv:test:0001"},
        "problem": {"value": {
            "problem_id": "p-test", "device": "battery pack",
            "failure": "thermal runaway during overcharge",
            "failure_mode": "thermal runaway", "constraint": "retrofit"}},
        "mechanism": {"value": {
            "mechanism": mechanism, "intervention": intervention,
            "expected_effect": "early disconnection before venting",
            "falsification_test": "cell-level overcharge test",
            "mechanism_source_span": span,
            "epistemic_class": "MODELLED"}},
        "evidence": {"value": [
            {"id": "evidence:acoustic-1",
             "title": evidence_title}],
            "evidence_ids": ["evidence:acoustic-1"]},
        "prior_art": {"value": {
            "status": "RESOLVED_DIFFERENTIATED",
            "differentiation_resolution": {
                "state": "RESOLVED_DIFFERENTIATED",
                "epistemic_class": "SEARCH_RESULT",
                "per_family": families, "n_families": len(families),
                "surviving_differentiators": surviving}}},
        "novelty_hypothesis": {"value": {
            "prior_art_status": "RESOLVED_DIFFERENTIATED",
            "collision_novelty_risk": "ADJACENT_COLLISION_CANDIDATES"}},
        "distinguishing_features": {"value": {
            "intervention": intervention,
            "vs_nearest_prior_art": vs_nearest,
            "surviving_differentiators": surviving}},
        "uncertainties": {"value": unc},
        "constraints": {"value": {"stated_constraint": "retrofit"}},
        "killer_experiment": {"value": {
            "selected": experiment, "eig": 0.4}},
        "_evidence_index": {"evidence:acoustic-1": {
            "id": "evidence:acoustic-1",
            "title": evidence_title}},
    }


DECISIVE_ADMIN = {
    "selected": {"experiment":
                 "fetch and audit claims of nearest collision patents",
                 "expected_information_gain": 0.1}}

DECISIVE_GOOD = {
    "selected": {"experiment":
                 "overcharge the cell and compare the acoustic emission "
                 "sensor alarm timing against a conventional temperature "
                 "threshold baseline",
                 "expected_information_gain": 0.5}}


def _ctx(spec=None, decisive=None, attack=None, problem=None):
    from discovery_fabric.engine.evaluator_contract import CandidateContext
    return CandidateContext(
        spec=spec or _spec(), decisive=decisive or DECISIVE_ADMIN,
        problem=problem or {"problem_id": "p-test", "device": "battery pack",
                            "failure": "thermal runaway during overcharge",
                            "constraint": "retrofit"},
        evidence_items=copy.deepcopy(EV_ITEMS), attack=attack)


def _validate_targeting(ctx, fields, dimension):
    """Validate a proposal against the diagnosis, targeting the given
    dimension's limiting feature (unit-test seam for targeting ANY
    measured weakness, independent of rank order)."""
    diag = ie.diagnose(ctx)
    for idx, f in enumerate(diag.limiting_features):
        if f.dimension == dimension:
            return ie.validate_mutation(ctx, _proposal(fields), diag,
                                        target_index=idx)
    raise AssertionError(
        f"{dimension} is not a measured limiting feature of this ctx: "
        f"{[f.dimension for f in diag.limiting_features]}")


VALID_STRENGTHENING_FIELDS = {
    "MUTATION_TYPE": "MECHANISM_STRENGTHENING",
    "MECHANISM": "Acoustic emission sensing of gas-driven surface "
                 "vibrations for pre-emptive disconnection",
    "INTERVENTION": "Bond a piezoelectric acoustic emission sensor to "
                    "the cell casing measuring gas-driven surface "
                    "vibrations at 180-220 kHz for pre-emptive "
                    "disconnection",
    "EXPECTED_EFFECT": "disconnection 40-90 s before venting",
    "FALSIFICATION_TEST": "cell-level overcharge test",
    "MECHANISM_SOURCE_SPAN":
        "a piezoelectric acoustic emission sensor bonded to the cell "
        "casing measures parabolic gas-driven surface vibrations at "
        "180-220 kHz",
    "SOURCE_EVIDENCE_ID": "evidence:acoustic-1",
    "EXPERIMENT": "fetch and audit claims of nearest collision patents",
    "EXPERIMENT_BASELINE": "none",
    "EXPERIMENT_EIG": "0.1",
    "CONSTRAINT_DERIVED": "NONE",
    "MUTATION_REASON": "repairs I1: the mechanism is now derived from "
                       "the acoustic-emission span",
}


def _proposal(fields: dict, status: str = "OK") -> dict:
    return {"proposal_id": "prop:test:0001", "provider": "test",
            "model": "test-model", "status": status,
            "prompt_hash": "ph", "output_hash": "oh",
            "latency_ms": 1, "error": None, "fields": fields}


VALID_EXPERIMENT_FIELDS = {
    "MUTATION_TYPE": "EXPERIMENT_DISCRIMINATION",
    "MECHANISM": "Pressure monitoring with redundant sensors",
    "INTERVENTION": "dual pressure sensors with independent signal "
                    "processing along the infusion path",
    "EXPECTED_EFFECT": "early disconnection before venting",
    "FALSIFICATION_TEST": "cell-level overcharge test",
    "MECHANISM_SOURCE_SPAN": "acoustic emission sensor",
    "SOURCE_EVIDENCE_ID": "evidence:acoustic-1",
    "EXPERIMENT": "overcharge the cell and compare the acoustic emission "
                  "sensor alarm timing against a conventional temperature "
                  "threshold baseline",
    "EXPERIMENT_BASELINE":
        "conventional temperature threshold baseline",
    "EXPERIMENT_EIG": "0.5",
    "CONSTRAINT_DERIVED": "NONE",
    "MUTATION_REASON": "repairs I5: physical experiment with baseline",
}


# ---------------------------------------------------------------------------
# 1. evaluator contract
# ---------------------------------------------------------------------------
class TestEvaluatorContract:
    def test_experiment_tier_registration_rejected(self):
        """Art. XXXVIII BYPASS ATTACK: software declaring rank-5
        physical-observation authority must be structurally refused."""
        with pytest.raises(ValueError):
            ec.register_evaluator("fake_lab", "EXPERIMENT",
                                  lambda ctx: None)

    def test_rank5_registration_rejected(self):
        with pytest.raises(ValueError):
            ec.register_evaluator("fake_lab2", "SIMULATION",
                                  lambda ctx: None, evidence_rank=5)

    def test_unknown_tier_rejected(self):
        with pytest.raises(ValueError):
            ec.register_evaluator("x", "QUANTUM_ORACLE", lambda ctx: None)

    def test_term_rule_evaluator_registered_by_default(self):
        assert any(e["evaluator_id"] == "term_rule_v1"
                   for e in ec.registered_evaluators())

    def test_diagnosis_names_limiting_feature_for_underived(self):
        d = ec.term_rule_evaluate(_ctx())
        assert any(f.dimension == "I1_MECHANISM_EVIDENCE_DERIVATION"
                   and f.weakness_kind == "UNDERIVED"
                   and f.mutation_type == "MECHANISM_STRENGTHENING"
                   for f in d.limiting_features)

    def test_unmeasurable_dims_are_gaps_not_targets(self):
        """Art. XXV: no mutation against an unmeasured link. Blank the
        mechanism AND intervention so I1 is UNMEASURABLE and confirm it
        appears in evidence_gaps, never in limiting_features."""
        spec = _spec(mechanism="", span="",
                     intervention="")
        d = ec.term_rule_evaluate(_ctx(spec=spec))
        dims_in_gaps = {g["dimension"] for g in d.evidence_gaps}
        dims_in_targets = {f.dimension for f in d.limiting_features}
        assert "I1_MECHANISM_EVIDENCE_DERIVATION" in dims_in_gaps
        assert "I1_MECHANISM_EVIDENCE_DERIVATION" not in dims_in_targets

    def test_recombination_flag_names_residue_mutation(self):
        # every intervention element covered by the found families
        # (realistic coverage lists: the family texts contain all these
        # terms — coverage.distinguishing_terms_covered mirrors what
        # coverage_decision records against the text)
        fam_a = _family("fam-a", FAMILY_TEXT_A)
        fam_a["coverage"] = {
            "distinguishing_terms_covered": [
                "battery", "pack", "cooling", "plates", "temperature",
                "controller", "disconnects"],
            "mechanism_overlap_terms": ["battery", "thermal"]}
        spec = _spec(
            intervention="battery pack cooling plates temperature "
                         "sensor controller disconnects pack",
            families=[fam_a, _family("fam-b", FAMILY_TEXT_B)])
        d = ec.term_rule_evaluate(_ctx(spec=spec))
        i3 = [f for f in d.limiting_features
              if f.dimension == "I3_RECOMBINATION_RISK"]
        assert i3 and i3[0].mutation_type == "DIFFERENTIATOR"
        assert i3[0].weakness_kind == "RECOMBINATION"


# ---------------------------------------------------------------------------
# 2. validation gates (the adversarial core)
# ---------------------------------------------------------------------------
class TestValidationGates:
    def _diag(self, ctx=None):
        return ie.diagnose(ctx or _ctx())

    def test_valid_mechanism_strengthening_passes(self):
        ctx = _ctx()
        v = ie.validate_mutation(
            ctx, _proposal(VALID_STRENGTHENING_FIELDS), self._diag(ctx))
        assert v["valid"], v["reasons"]

    def test_fabricated_span_rejected(self):
        """Art. VI BYPASS ATTACK: a span that is NOT a verbatim
        substring of the cited evidence must be rejected."""
        fields = dict(VALID_STRENGTHENING_FIELDS)
        fields["MECHANISM_SOURCE_SPAN"] = \
            "invented span that appears nowhere in the evidence text"
        v = ie.validate_mutation(_ctx(), _proposal(fields), self._diag())
        assert not v["valid"]
        assert any("span_verbatim_in_evidence" in r for r in v["reasons"])

    def test_unknown_evidence_id_rejected(self):
        fields = dict(VALID_STRENGTHENING_FIELDS)
        fields["SOURCE_EVIDENCE_ID"] = "evidence:does-not-exist"
        v = ie.validate_mutation(_ctx(), _proposal(fields), self._diag())
        assert not v["valid"]
        assert any("span_evidence_exists" in r for r in v["reasons"])

    def test_off_target_mutation_rejected(self):
        """CEO rule 8 BYPASS ATTACK: a proposal whose type does not
        match the diagnosed trigger is score-chasing, not repair."""
        fields = dict(VALID_STRENGTHENING_FIELDS)
        fields["MUTATION_TYPE"] = "EXPERIMENT_DISCRIMINATION"
        v = ie.validate_mutation(_ctx(), _proposal(fields), self._diag())
        assert not v["valid"]
        assert any("mutation_type_matches_diagnosis" in r
                   for r in v["reasons"])

    def test_noop_mutation_rejected(self):
        spec = _spec()
        fields = dict(VALID_STRENGTHENING_FIELDS)
        fields["MECHANISM"] = spec["mechanism"]["value"]["mechanism"]
        fields["INTERVENTION"] = \
            spec["mechanism"]["value"]["intervention"]
        ctx = _ctx(spec=spec)
        v = ie.validate_mutation(ctx, _proposal(fields), self._diag(ctx))
        assert not v["valid"]
        assert any("mutation_changes_candidate" in r for r in v["reasons"])

    def test_span_present_but_vocabulary_absent_rejected(self):
        """The span is verbatim but does NOT contain the new mechanism's
        vocabulary — derivation still fails the term rule."""
        fields = dict(VALID_STRENGTHENING_FIELDS)
        fields["MECHANISM"] = "Quantum flux capacitor neutralization"
        fields["INTERVENTION"] = "install a quantum flux capacitor"
        v = ie.validate_mutation(_ctx(), _proposal(fields), self._diag())
        assert not v["valid"]
        assert any("span_derivation_cleared" in r for r in v["reasons"])

    def test_differentiator_without_residue_rejected(self):
        """Art. XXI.2 BYPASS ATTACK: every element covered by found art
        — recombination remains; no residue may be claimed."""
        fields = dict(VALID_STRENGTHENING_FIELDS)
        fields["MUTATION_TYPE"] = "DIFFERENTIATOR"
        fields["INTERVENTION"] = (
            "battery pack cooling plates with temperature sensor and "
            "controller that disconnects the pack")
        spec = _spec(surviving=["dual", "independent", "monitoring"])
        ctx = _ctx(spec=spec)
        v = _validate_targeting(ctx, fields, "I2_DIFFERENTIATOR_TECHNICAL_"
                                             "MEANING")
        assert not v["valid"]
        assert any("meaningful_residue_exists" in r for r in v["reasons"])

    def test_differentiator_with_residue_passes(self):
        spec = _spec(surviving=["dual", "independent", "monitoring"])
        ctx = _ctx(spec=spec)
        fields = dict(VALID_STRENGTHENING_FIELDS)
        fields["MUTATION_TYPE"] = "DIFFERENTIATOR"
        fields["INTERVENTION"] = (
            "bond a piezoelectric acoustic emission sensor to the cell "
            "casing measuring gas-driven surface vibrations for "
            "pre-emptive disconnection")
        v = _validate_targeting(ctx, fields,
                                "I2_DIFFERENTIATOR_TECHNICAL_MEANING")
        assert v["valid"], v["reasons"]

    def test_administrative_experiment_rejected(self):
        spec = _spec(surviving=["acoustic", "piezoelectric", "emission"])
        ctx = _ctx(spec=spec, decisive=DECISIVE_ADMIN)
        fields = dict(VALID_EXPERIMENT_FIELDS)
        fields["EXPERIMENT"] = "search and review the nearest patents"
        fields["EXPERIMENT_BASELINE"] = "nearest patents"
        v = _validate_targeting(
            ctx, fields, "I5_EXPERIMENT_DISCRIMINATION")
        assert not v["valid"]
        assert any("experiment_is_physical" in r for r in v["reasons"])

    def test_experiment_without_baseline_rejected(self):
        spec = _spec(surviving=["acoustic", "piezoelectric", "emission"])
        ctx = _ctx(spec=spec, decisive=DECISIVE_ADMIN)
        fields = dict(VALID_EXPERIMENT_FIELDS)
        fields["EXPERIMENT_BASELINE"] = ""
        v = _validate_targeting(
            ctx, fields, "I5_EXPERIMENT_DISCRIMINATION")
        assert not v["valid"]
        assert any("experiment_names_baseline" in r for r in v["reasons"])

    def test_experiment_baseline_not_referenced_rejected(self):
        spec = _spec(surviving=["acoustic", "piezoelectric", "emission"])
        ctx = _ctx(spec=spec, decisive=DECISIVE_ADMIN)
        fields = dict(VALID_EXPERIMENT_FIELDS)
        # a baseline that shares NO content terms with the experiment
        # text and does not appear verbatim — a named-but-unused
        # baseline cannot distinguish anything
        fields["EXPERIMENT_BASELINE"] = "rotating machinery accelerometer array"
        v = _validate_targeting(
            ctx, fields, "I5_EXPERIMENT_DISCRIMINATION")
        assert not v["valid"]
        assert any("experiment_references_baseline" in r
                   for r in v["reasons"])

    def test_experiment_baseline_paraphrased_reference_passes(self):
        """The engine's reference rule family (>= 2 shared content
        terms): a comparison present with paraphrased wording is a
        REAL comparison (measured replay defect: verbatim-phrase-only
        rejected genuine comparisons)."""
        spec = _spec(surviving=["acoustic", "piezoelectric", "emission"])
        ctx = _ctx(spec=spec, decisive=DECISIVE_ADMIN)
        fields = dict(VALID_EXPERIMENT_FIELDS)
        fields["EXPERIMENT_BASELINE"] = "temperature threshold control"
        v = _validate_targeting(
            ctx, fields, "I5_EXPERIMENT_DISCRIMINATION")
        assert v["valid"], v["reasons"]

    def test_valid_experiment_discrimination_passes(self):
        spec = _spec(surviving=["acoustic", "piezoelectric", "emission"])
        ctx = _ctx(spec=spec, decisive=DECISIVE_ADMIN)
        v = _validate_targeting(
            ctx, VALID_EXPERIMENT_FIELDS,
            "I5_EXPERIMENT_DISCRIMINATION")
        assert v["valid"], v["reasons"]

    def test_technical_relationship_all_known_pairs_rejected(self):
        """I4 BYPASS ATTACK: relabeled known co-occurring elements."""
        spec = _spec(mechanism="battery pack cooling plates temperature "
                               "sensor controller")
        ctx = _ctx(spec=spec)
        fields = dict(VALID_STRENGTHENING_FIELDS)
        fields["MUTATION_TYPE"] = "TECHNICAL_RELATIONSHIP"
        fields["MECHANISM"] = ("battery pack cooling plates with "
                               "temperature sensor controller")
        v = _validate_targeting(ctx, fields,
                                "I4_NEW_TECHNICAL_RELATIONSHIP")
        assert not v["valid"]
        assert any("novel_pair_exists" in r for r in v["reasons"])

    def test_technical_relationship_novel_pair_passes(self):
        spec = _spec(mechanism="battery pack cooling plates temperature "
                               "sensor controller")
        ctx = _ctx(spec=spec)
        fields = dict(VALID_STRENGTHENING_FIELDS)
        fields["MUTATION_TYPE"] = "TECHNICAL_RELATIONSHIP"
        fields["MECHANISM"] = ("piezoelectric acoustic emission "
                               "pre-emptive disconnection of the cell "
                               "before venting")
        v = _validate_targeting(ctx, fields,
                                "I4_NEW_TECHNICAL_RELATIONSHIP")
        assert v["valid"], v["reasons"]

    def test_evidence_constraint_none_rejected(self):
        spec = _spec(span="", mechanism="Quantum flux neutralization")
        # force evidence_support weakness: mechanism vocabulary absent
        # from the cited evidence
        ctx = _ctx(spec=spec)
        fields = dict(VALID_STRENGTHENING_FIELDS)
        fields["MUTATION_TYPE"] = "EVIDENCE_DERIVED_CONSTRAINT"
        fields["CONSTRAINT_DERIVED"] = "NONE"
        v = ie.validate_mutation(ctx, _proposal(fields),
                                 ie.diagnose(ctx))
        assert not v["valid"]
        assert any("constraint_actually_derived" in r
                   for r in v["reasons"])

    def test_transport_failure_is_not_validated(self):
        v = ie.validate_mutation(_ctx(), _proposal({}, status="CALL_FAILED"),
                                 self._diag())
        assert not v["valid"]
        assert v["stage"] == "TRANSPORT_OR_PARSE"


# ---------------------------------------------------------------------------
# 3. apply + provenance chain
# ---------------------------------------------------------------------------
class TestApplyMutation:
    def test_causal_chain_present(self):
        ctx = _ctx()
        diag = ie.diagnose(ctx)
        child = ie.apply_mutation(ctx, _proposal(VALID_STRENGTHENING_FIELDS),
                                  ie.validate_mutation(
                                      ctx, _proposal(
                                          VALID_STRENGTHENING_FIELDS),
                                      diag))
        mut = child.spec["_improvement"]["mutation"]
        assert mut["chain"] == \
            "ORIGINAL -> DIAGNOSTIC -> MUTATION -> NEW CANDIDATE"
        assert mut["parent_spec_hash"]
        assert mut["proposal_provenance"]["output_hash"]
        assert mut["diagnostic_trigger"]["dimension"] == \
            "I1_MECHANISM_EVIDENCE_DERIVATION"
        assert mut["mutation_type"] == "MECHANISM_STRENGTHENING"
        assert mut["applied_at"]

    def test_child_span_derivation_remeasured(self):
        ctx = _ctx()
        diag = ie.diagnose(ctx)
        child = ie.apply_mutation(ctx, _proposal(VALID_STRENGTHENING_FIELDS),
                                  ie.validate_mutation(
                                      ctx, _proposal(
                                          VALID_STRENGTHENING_FIELDS),
                                      diag))
        sd = child.spec["mechanism"]["value"]["span_derivation"]
        assert sd["state"] == "MEASURED"
        assert not sd["underived"]

    def test_parent_negatives_carried(self):
        ctx = _ctx()
        diag = ie.diagnose(ctx)
        child = ie.apply_mutation(ctx, _proposal(VALID_STRENGTHENING_FIELDS),
                                  ie.validate_mutation(
                                      ctx, _proposal(
                                          VALID_STRENGTHENING_FIELDS),
                                      diag))
        preserved, lost = ie.negatives_preserved(
            ie.collect_negatives(ctx.spec, ctx.decisive),
            ie.collect_negatives(child.spec, child.decisive))
        assert preserved, lost


# ---------------------------------------------------------------------------
# 4. REPLAY_CACHE re-adjudication
# ---------------------------------------------------------------------------
class TestReAdjudication:
    def test_cache_readsjudates_for_mutated_profile(self):
        """CEO rule 11: the child's coverage/resolution is COMPUTED for
        the mutated profile against the cached family text — not the
        parent's resolution object."""
        ctx = _ctx()
        diag = ie.diagnose(ctx)
        child = ie.apply_mutation(ctx, _proposal(VALID_STRENGTHENING_FIELDS),
                                  ie.validate_mutation(
                                      ctx, _proposal(
                                          VALID_STRENGTHENING_FIELDS),
                                      diag))
        adj = ie.re_adjudicate_cached(ctx, child)
        assert adj["valid"], adj.get("reason")
        res = adj["resolution"]
        assert res["n_families"] == 2
        # the child's own coverage computed against the family text
        assert res["per_family"][0]["coverage"]["coverage_class"]

    def test_domain_abandonment_invalidates_cache(self):
        """The laundering attack: mutate the candidate into a wholly
        different technical domain (cement curing) — re-adjudicating it
        against the cached battery art would FABRICATE surviving
        differentiators (false novelty from stale art). The cache must
        be invalidated."""
        ctx = _ctx()
        diag = ie.diagnose(ctx)
        child = ie.apply_mutation(ctx, _proposal(VALID_STRENGTHENING_FIELDS),
                                  ie.validate_mutation(
                                      ctx, _proposal(
                                          VALID_STRENGTHENING_FIELDS),
                                      diag))
        # mutate the child into a different domain entirely
        child.spec["mechanism"]["value"]["intervention"] = \
            "cement carbonation curing membrane for bridge decks"
        child.spec["distinguishing_features"]["value"]["intervention"] = \
            "cement carbonation curing membrane for bridge decks"
        child.spec["mechanism"]["value"]["mechanism"] = \
            "carbonation curing of cementitious materials"
        adj = ie.re_adjudicate_cached(ctx, child)
        assert not adj["valid"]
        assert adj["reason"] == "DOMAIN_ABANDONED_CACHE_INVALID"

    def test_in_domain_mutation_keeps_cache_valid(self):
        """The legitimate case: a mechanism-strengthening mutation in
        the SAME domain keeps the cache valid (recorded with its
        domain-overlap terms for audit)."""
        ctx = _ctx()
        diag = ie.diagnose(ctx)
        child = ie.apply_mutation(ctx, _proposal(VALID_STRENGTHENING_FIELDS),
                                  ie.validate_mutation(
                                      ctx, _proposal(
                                          VALID_STRENGTHENING_FIELDS),
                                      diag))
        adj = ie.re_adjudicate_cached(ctx, child)
        assert adj["valid"], adj.get("reason")
        assert adj["domain_overlap_terms"], \
            "domain overlap must be recorded for audit"

    def test_no_cached_families_is_invalid(self):
        spec = _spec(families=[])
        spec["prior_art"]["value"]["differentiation_resolution"][
            "per_family"] = []
        ctx = _ctx(spec=spec)
        adj = ie.re_adjudicate_cached(ctx, ctx)
        assert not adj["valid"]
        assert adj["reason"] == "NO_CACHED_FAMILIES"


# ---------------------------------------------------------------------------
# 5. keep-or-kill
# ---------------------------------------------------------------------------
class TestKeepOrKill:
    def _parent_eval(self, ctx):
        return ie._measure_ctx(ctx)

    def test_targeted_improvement_keeps(self):
        ctx = _ctx()
        diag = ie.diagnose(ctx)
        child = ie.apply_mutation(ctx, _proposal(VALID_STRENGTHENING_FIELDS),
                                  ie.validate_mutation(
                                      ctx, _proposal(
                                          VALID_STRENGTHENING_FIELDS),
                                      diag))
        re_eval = ie.re_evaluate(child, collision_mode="REPLAY_CACHE",
                                 parent_ctx=ctx)
        decision = ie.keep_or_kill(self._parent_eval(ctx), re_eval,
                                   "I1_MECHANISM_EVIDENCE_DERIVATION",
                                   ctx, child)
        assert decision["action"] == "KEEP", decision["reasons"]
        assert decision["improved"]

    def test_no_improvement_rejects(self):
        ctx = _ctx()
        diag = ie.diagnose(ctx)
        # apply a mutation that fixes nothing on the targeted dimension:
        # craft a proposal whose span is verbatim but shares minimal
        # vocabulary with the mechanism
        fields = dict(VALID_STRENGTHENING_FIELDS)
        fields["MECHANISM"] = "Pressure monitoring with redundant sensors"
        fields["INTERVENTION"] = \
            "dual pressure sensors with independent signal processing " \
            "along the infusion path acoustic emission"
        fields["MECHANISM_SOURCE_SPAN"] = \
            "Acoustic emission sensing of lithium-ion battery cells"
        # target I1 via a fabricated diag-validated path is not
        # possible (validation gates it); instead verify keep_or_kill
        # rejects when re-evaluation shows no I1 gain:
        re_eval = self._parent_eval(ctx)
        decision = ie.keep_or_kill(re_eval, re_eval,
                                   "I1_MECHANISM_EVIDENCE_DERIVATION",
                                   ctx, ctx)
        assert decision["action"] == "REJECT_MUTATION"
        assert not decision["improved"]

    def test_unknown_conversion_rejected(self):
        """Art. XXV BYPASS ATTACK: an EVIDENCE-gap dimension (no family
        text) scoring MEASURED from nowhere in cache mode (no new
        evidence) must block the KEEP."""
        ctx = _ctx()
        parent_eval = self._parent_eval(ctx)
        parent_eval["i_dimensions"] = dict(parent_eval["i_dimensions"])
        parent_eval["i_dimensions"]["I4_NEW_TECHNICAL_RELATIONSHIP"] = {
            "score": None, "state": "UNMEASURABLE_NO_FAMILY_TEXT"}
        child_eval = dict(parent_eval)
        child_eval["i_dimensions"] = dict(parent_eval["i_dimensions"])
        child_eval["i_dimensions"]["I4_NEW_TECHNICAL_RELATIONSHIP"] = {
            "score": 0.9, "state": "MEASURED"}
        child_eval["collision_mode"] = "REPLAY_CACHE"
        decision = ie.keep_or_kill(
            parent_eval, child_eval,
            "I1_MECHANISM_EVIDENCE_DERIVATION", ctx, ctx)
        assert decision["action"] == "REJECT_MUTATION"
        assert any("UNKNOWN evidence-gap converted" in r
                   for r in decision["reasons"])

    def test_text_gap_conversion_is_legitimate_and_recorded(self):
        """A TERSE-mechanism UNMEASURABLE (candidate-text gap, not an
        evidence gap) may legitimately become MEASURED when the
        mutation supplies richer text — measured against the SAME
        family texts. Recorded for audit, never silent."""
        ctx = _ctx()
        parent_eval = self._parent_eval(ctx)
        parent_eval["i_dimensions"] = dict(parent_eval["i_dimensions"])
        parent_eval["i_dimensions"]["I4_NEW_TECHNICAL_RELATIONSHIP"] = {
            "score": None, "state": "UNMEASURABLE_TERSE_MECHANISM"}
        child_eval = dict(parent_eval)
        child_eval["i_dimensions"] = dict(parent_eval["i_dimensions"])
        child_eval["i_dimensions"]["I4_NEW_TECHNICAL_RELATIONSHIP"] = {
            "score": 0.9, "state": "MEASURED"}
        child_eval["collision_mode"] = "REPLAY_CACHE"
        decision = ie.keep_or_kill(
            parent_eval, child_eval,
            "I1_MECHANISM_EVIDENCE_DERIVATION", ctx, ctx)
        assert not any("UNKNOWN evidence-gap converted" in r
                       for r in decision["reasons"])
        assert decision["checks"]["text_gap_conversions_recorded"] == [
            "I4_NEW_TECHNICAL_RELATIONSHIP"]

    def test_prior_art_degradation_rejected(self):
        ctx = _ctx()
        parent_eval = self._parent_eval(ctx)
        child_eval = dict(parent_eval)
        child_eval["prior_art_status"] = "UNRESOLVED_INSUFFICIENT_EVIDENCE"
        decision = ie.keep_or_kill(
            parent_eval, child_eval,
            "I1_MECHANISM_EVIDENCE_DERIVATION", ctx, ctx)
        assert decision["action"] == "REJECT_MUTATION"
        assert any("degraded" in r for r in decision["reasons"])

    def test_anticipated_child_rejected_as_kill_grade(self):
        ctx = _ctx()
        parent_eval = self._parent_eval(ctx)
        child_eval = dict(parent_eval)
        child_eval["prior_art_status"] = "RESOLVED_ANTICIPATED"
        decision = ie.keep_or_kill(
            parent_eval, child_eval,
            "I1_MECHANISM_EVIDENCE_DERIVATION", ctx, ctx)
        assert decision["action"] == "REJECT_MUTATION"
        assert any("RESOLVED_ANTICIPATED" in r for r in decision["reasons"])


# ---------------------------------------------------------------------------
# 6. the loop (mocked proposer — hermetic)
# ---------------------------------------------------------------------------
class TestImproveLoop:
    def _mock_proposer(self, monkeypatch, proposals):
        """Return a proposer serving the given proposal records in
        order (one per call). Accepts the directional-feedback kwarg
        (ignored by the mock — the mock serves fixed proposals)."""
        calls = {"n": 0, "served": []}

        def fake(ctx, diagnosis, target_index=0, provider=None,
                 feedback=None):
            i = min(calls["n"], len(proposals) - 1)
            calls["n"] += 1
            p = copy.deepcopy(proposals[i])
            calls["served"].append(p.get("status"))
            return p
        monkeypatch.setattr(ie, "propose_mutation", fake)
        return calls

    def test_improved_with_ledger(self, monkeypatch):
        ctx = _ctx()
        self._mock_proposer(monkeypatch, [
            _proposal(VALID_STRENGTHENING_FIELDS),
            _proposal(VALID_EXPERIMENT_FIELDS)])
        ledger = ie.improve_candidate(ctx, max_iterations=2,
                                      collision_mode="REPLAY_CACHE")
        assert ledger["outcome"] in ("IMPROVED", "KILLED_NO_IMPROVING_"
                                     "MUTATION", "KILLED_NO_DEFENSIBLE_"
                                     "MUTATION")
        assert ledger["iterations"], "at least one iteration recorded"
        assert ledger["baseline"]["i_average"] is not None
        assert ledger["outcome_summary"]["iterations_run"] >= 1
        # the causal chain is on the final spec when a KEEP happened
        if ledger["outcome"] == "IMPROVED":
            hist = ledger["current_ctx"].spec["_improvement"]["history"]
            assert hist, "provenance history recorded"
            assert all(m.get("mutation_id") for m in hist)

    def test_invalid_proposals_kill(self, monkeypatch):
        """CEO rule 9: no defensible mutation -> honest KILL."""
        ctx = _ctx()
        bad = dict(VALID_STRENGTHENING_FIELDS)
        bad["MECHANISM_SOURCE_SPAN"] = "fabricated span not in evidence"
        self._mock_proposer(monkeypatch, [_proposal(bad)])
        ledger = ie.improve_candidate(ctx, max_iterations=1,
                                      max_proposals=2,
                                      collision_mode="REPLAY_CACHE")
        assert ledger["outcome"] == "KILLED_NO_DEFENSIBLE_MUTATION"
        assert "no defensible mutation" in ledger["outcome_reason"]
        # every rejected proposal is recorded with its reasons
        props = ledger["iterations"][0]["proposals"]
        assert props and props[0]["validation"]["valid"] is False

    def test_transport_block_is_not_a_kill(self, monkeypatch):
        """Art. XXV: infrastructure failure must not masquerade as a
        research verdict."""
        ctx = _ctx()
        self._mock_proposer(monkeypatch, [
            _proposal({}, status="PROVIDER_UNAVAILABLE")])
        ledger = ie.improve_candidate(ctx, max_iterations=1,
                                      collision_mode="REPLAY_CACHE")
        assert ledger["outcome"] == "IMPROVEMENT_BLOCKED_TRANSPORT"

    def test_rejected_mutation_tries_next_proposal(self, monkeypatch):
        """CEO rule 9 semantics: 'no defensible mutation can improve the
        candidate' must mean the proposal budget was actually SPENT.
        When a validated mutation is REJECTED on re-evaluation, the
        parent stands and the loop generates the next proposal —
        measured w7 defect: the first regressing mutation killed the
        candidate while proposal budget remained. (Loop mechanics are
        tested by mocking keep_or_kill's verdict sequence: REJECT then
        KEEP — the deterministic keep-or-kill logic itself is covered
        by TestKeepOrKill.)"""
        real_kok = ie.keep_or_kill
        verdicts = {"n": 0}

        def fake_kok(parent_eval, child_eval, target_dimension,
                     parent_ctx, child_ctx):
            v = real_kok(parent_eval, child_eval, target_dimension,
                         parent_ctx, child_ctx)
            if verdicts["n"] == 0:
                verdicts["n"] += 1
                return dict(v, action="REJECT_MUTATION",
                            reasons=v["reasons"] + [
                                "injected-first-rejection (loop-mechanics "
                                "test)"])
            return v
        monkeypatch.setattr(ie, "keep_or_kill", fake_kok)
        calls = {"n": 0}

        def fake_proposer(ctx, diagnosis, target_index=0, provider=None,
                          feedback=None):
            p = _proposal(VALID_STRENGTHENING_FIELDS)
            calls["n"] += 1
            return p
        monkeypatch.setattr(ie, "propose_mutation", fake_proposer)
        ctx = _ctx()
        ledger = ie.improve_candidate(
            ctx, max_iterations=1, max_proposals=3,
            collision_mode="REPLAY_CACHE")
        it = ledger["iterations"][0]
        # the first applied mutation was REJECTED, the parent stood,
        # and the loop generated ANOTHER proposal and applied it
        assert len(it.get("mutation_attempts") or []) == 2
        assert calls["n"] == 2, \
            "the loop must generate a second proposal after the first " \
            "applied mutation was rejected"
        assert it["mutation_attempts"][0]["decision"]["action"] == \
            "REJECT_MUTATION"
        # the injected rejection reason traveled as DIRECTIONAL
        # FEEDBACK into the second proposal's prompt (observable via
        # the proposer's feedback argument)
        assert ledger["outcome"] in ("IMPROVED",
                                     "KILLED_NO_IMPROVING_MUTATION")
        # the final decision is the SECOND attempt's (KEEP from the
        # real keep_or_kill on a genuinely improving mutation)
        assert it["decision"]["action"] == "KEEP"

    def test_attacked_candidate_not_improved(self):
        """Art. XX: a candidate whose premise the attack already killed
        is not mechanism-optimized."""
        ctx = _ctx(attack={"overall": "KILLED", "items": []})
        ledger = ie.improve_candidate(ctx)
        assert ledger["outcome"] == \
            "IMPROVEMENT_NOT_RUN_CANDIDATE_KILLED"

    def test_healthy_candidate_not_mutated(self):
        # a HEALTHY candidate: I1 >= 0.70 needs the evidence TITLE to
        # carry the mechanism's vocabulary (the instrument measures
        # evidence_support against titles — the recorded R377 reality),
        # differentiators specific, experiment discriminating
        span = ("piezoelectric acoustic emission sensor bonded to the "
                "cell casing measures parabolic gas-driven surface "
                "vibrations")
        spec = _spec(
            intervention="bond a piezoelectric acoustic emission sensor "
                         "to the cell casing measuring gas-driven "
                         "surface vibrations for pre-emptive "
                         "disconnection",
            mechanism=span,
            span=span,
            experiment="overcharge the cell and compare the acoustic "
                       "emission sensor alarm timing against a "
                       "conventional temperature threshold baseline",
            surviving=["acoustic", "piezoelectric", "emission",
                       "casing"],
            evidence_title="Piezoelectric acoustic emission sensor bonded "
                           "to the cell casing measures parabolic "
                           "gas-driven surface vibrations in batteries")
        ctx = _ctx(spec=spec, decisive=DECISIVE_GOOD)
        ledger = ie.improve_candidate(ctx, max_iterations=1,
                                      collision_mode="REPLAY_CACHE")
        assert ledger["outcome"] == "HEALTHY_NO_MUTATION", \
            ledger["iterations"]
        assert ledger["iterations"] == []


# ---------------------------------------------------------------------------
# 7. determinism + frozen instruments
# ---------------------------------------------------------------------------
class TestDeterminismAndFreeze:
    def test_validation_is_deterministic(self):
        ctx = _ctx()
        diag = ie.diagnose(ctx)
        v1 = ie.validate_mutation(ctx, _proposal(
            VALID_STRENGTHENING_FIELDS), diag)
        v2 = ie.validate_mutation(copy.deepcopy(ctx), _proposal(
            VALID_STRENGTHENING_FIELDS), ie.diagnose(copy.deepcopy(ctx)))
        assert v1["valid"] == v2["valid"]
        assert v1["checks"] == v2["checks"]

    def test_proposal_parse_field_protocol(self):
        content = (
            "MUTATION_TYPE: MECHANISM_STRENGTHENING\n"
            "MECHANISM: acoustic emission sensing\n"
            "INTERVENTION: bond piezoelectric sensor\n"
            "EXPECTED_EFFECT: early disconnect\n"
            "FALSIFICATION_TEST: overcharge test\n"
            "MECHANISM_SOURCE_SPAN: acoustic emission sensor\n"
            "SOURCE_EVIDENCE_ID: evidence:acoustic-1\n"
            "EXPERIMENT: overcharge test with baseline\n"
            "EXPERIMENT_BASELINE: temperature threshold\n"
            "EXPERIMENT_EIG: 0.5\n"
            "CONSTRAINT_DERIVED: NONE\n"
            "MUTATION_REASON: fixes I1\n"
            "GARBAGE LINE THAT SHOULD BE IGNORED")
        parsed = ie._parse_proposal(content)
        assert parsed["MUTATION_TYPE"] == "MECHANISM_STRENGTHENING"
        assert parsed["SOURCE_EVIDENCE_ID"] == "evidence:acoustic-1"
        assert "GARBAGE" not in parsed

    def test_q_instrument_still_frozen(self):
        p = (REPO / "discovery_fabric" / "benchmark" /
             "candidate_quality.py")
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        assert h == ("7e36ea45c8ca4c4ae90c53df5e00ec77"
                     "c487a66ca9dd629d2520f55284af10ca"), \
            "candidate_quality.py was modified — FROZEN (Art. XXX)"

    def test_i_instrument_r378_change_is_additive_only(self):
        """The R378 dead-code fix (raw_candidate read at BOTH tag and
        value level) is additive: a spec WITHOUT value.raw_candidate
        must measure IDENTICALLY to the R377 instrument, executed from
        git HEAD in isolation on the same fixture."""
        import importlib.util
        import subprocess
        import tempfile
        spec = _spec()
        r378 = iq.measure_mechanism_derivation(spec)
        r = subprocess.run(
            ["git", "show",
             "HEAD:discovery_fabric/benchmark/invention_quality.py"],
            cwd=str(REPO), capture_output=True, text=True)
        assert r.returncode == 0
        with tempfile.TemporaryDirectory() as td:
            mod_path = Path(td) / "iq_r377.py"
            mod_path.write_text(r.stdout)
            fixture = Path(td) / "fixture.json"
            fixture.write_text(json.dumps(spec))
            sys.path.insert(0, str(REPO))
            sys.path.insert(0, td)
            try:
                mu = importlib.util.spec_from_file_location(
                    "iq_r377", str(mod_path))
                m = importlib.util.module_from_spec(mu)
                mu.loader.exec_module(m)
                r377 = m.measure_mechanism_derivation(
                    json.loads(fixture.read_text()))
            finally:
                sys.path.remove(str(REPO))
                sys.path.remove(td)
        assert r378["score"] == r377["score"]
        assert r378["span_support"] == r377["span_support"]
        assert r378["evidence_support"] == r377["evidence_support"]

    def test_i_instrument_reads_value_level_source_span(self):
        """The R378 fix: a child spec carrying
        value.raw_candidate.source_evidence.source_span (written by
        apply_mutation, validated verbatim-in-evidence upstream) now
        measures its genuine evidence derivation — the R377 instrument
        could not see it (dead tag-level path)."""
        spec = _spec(
            mechanism="piezoelectric acoustic emission sensing",
            span="piezoelectric acoustic emission sensor bonded to the "
                 "cell casing measures gas-driven surface vibrations")
        spec["mechanism"]["value"]["raw_candidate"] = {
            "source_evidence": {
                "source_span": spec["mechanism"]["value"][
                    "mechanism_source_span"]}}
        r = iq.measure_mechanism_derivation(spec)
        assert r["evidence_support"] is not None and \
            r["evidence_support"] > 0.4, \
            "the cited span must count as evidence text for a " \
            "span-derived mechanism"
