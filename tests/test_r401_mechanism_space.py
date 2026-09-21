"""tests/test_r401_mechanism_space.py — R401 Phase 10: ADVERSARIAL
TESTS A–J (the directive's exact list) plus the bypass attempts the
directive's failure modes imply.

  A. near-duplicate candidates collapse.
  B. phenomenon evidence without mechanism support becomes
     NOT_ENOUGH_EVIDENCE.
  C. contradictory evidence stays CONTRADICTS.
  D. invalid transformed geometry is rejected.
  E. impossible boundary condition is rejected.
  F. candidate without a testable prediction is not an invention
     candidate.
  G. baseline-equivalent candidate is killed (ineligible for survivor
     selection).
  H. implementation-impossible candidate is killed (independent attack).
  I. unsupported mechanism is MECHANISM_NOT_SIMULATABLE.
  J. genuinely different mechanisms survive deduplication.

All tests are hermetic: the LLM call site (mechanism_space.llm_generate)
is monkeypatched; no network; no provider credential required.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import mechanism_space as ms  # noqa: E402
from discovery_fabric.engine import independent_attack as ia  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures: one rich problem + realistic custodied records
# ---------------------------------------------------------------------------
PROBLEM = {
    "problem_id": "r401_adv",
    "device": "tunneled hemodialysis catheter",
    "failure": "thrombotic occlusion of the catheter lumen under low flow",
    "failure_mode": "thrombosis",
    "constraint": "maintain drainage above 0.05 mL/min at venous pressure",
}

MEDICAL_RECORD = {
    "id": "evd-med-001",
    "source": "europepmc",
    "title": "Heparin-bonded luminal surfaces reduce thrombus formation "
             "in tunneled hemodialysis catheters",
    "abstract": (
        "In a controlled bench study we demonstrate that heparin bonding "
        "of the catheter lumen reduces thrombus formation under low flow "
        "conditions. Heparin bonding inhibits clotting cascade activation "
        "at the luminal surface. We measured thrombus area at flow rate "
        "50 mL/min and venous pressure 20 mmHg: heparin-bonded lumens "
        "showed significantly reduced thrombus compared with untreated "
        "polyurethane controls. Failure of untreated catheters by "
        "thrombotic occlusion was observed within days."),
    "content_hash": "hash-med-001",
    "retrieval_timestamp": "2026-09-03T00:00:00Z",
}

FOREIGN_RECORD = {
    "id": "evd-fgn-002",
    "source": "nasa_ntrs",
    "title": "Electrostatic repulsion prevents particle occlusion of "
             "microfluidic channels in vacuum systems",
    "abstract": (
        "We show that an applied electrostatic field repels charged "
        "dust particles from channel walls, preventing particle "
        "occlusion of microfluidic channels in vacuum chambers. Charged "
        "channel walls accumulated no particle deposition while "
        "grounded channels occluded and flow stopped. The mechanism is "
        "electrostatic repulsion of like charges at the surface "
        "boundary; the effect was measured at applied voltage 2 kV and "
        "temperature -50 C, with flow maintained through deposition-"
        "prone sections."),
    "content_hash": "hash-fgn-002",
    "retrieval_timestamp": "2026-09-03T00:00:00Z",
}

CONTRA_RECORD = {
    "id": "evd-con-003",
    "source": "pubmed",
    "title": "Heparin bonding does not reduce thrombus in slow-flow "
             "venous access grafts",
    "abstract": (
        "In a randomized study, heparin-bonded venous access grafts did "
        "not reduce thrombus formation under low flow; occlusion rates "
        "were not different from controls. We measured thrombus area at "
        "flow rate 50 mL/min: no significant difference."),
    "content_hash": "hash-con-003",
    "retrieval_timestamp": "2026-09-03T00:00:00Z",
}


def _fake_llm(responses):
    """Fake the ONE LLM call site with a queue of canned responses."""
    state = {"i": 0}

    def _gen(prompt, system="", timeout=240, max_tokens=700,
             purpose="mechanism_space", exclude_providers=None):
        i = state["i"]
        state["i"] += 1
        if i >= len(responses):
            return {"ok": False, "status": "CALL_FAILED",
                    "content": None, "provider": "fake",
                    "model": "fake", "error": "queue exhausted"}
        r = responses[i]
        if r is None:  # simulate transport failure
            return {"ok": False, "status": "CALL_FAILED",
                    "content": None, "provider": "fake",
                    "model": "fake", "error": "simulated failure"}
        return {"ok": True, "status": "OK", "content": r,
                "provider": "fake", "model": "fake-model",
                "prompt_hash": "ph" + str(i), "output_hash": "oh" + str(i),
                "error": None, "excluded_providers": [], "fallback": False}
    return _gen


MEDICAL_EXTRACTION = (
    "CLAIM: Heparin bonding of catheter lumens reduces thrombus "
    "formation under low flow\n"
    "OBSERVED_EFFECT: significantly reduced thrombus area versus "
    "polyurethane controls\n"
    "SYSTEM: tunneled hemodialysis catheter lumen\n"
    "INTERVENTION: heparin bonding of the luminal surface\n"
    "MECHANISM: heparin bonding inhibits clotting cascade activation at "
    "the luminal surface\n"
    "BOUNDARY_CONDITIONS: flow rate 50 mL/min and venous pressure "
    "20 mmHg\n"
    "CONSTRAINTS: luminal surface treatment must not narrow the lumen\n"
    "FAILURE_MODE: thrombotic occlusion\n"
    "CONFIDENCE: HIGH\n"
)

FOREIGN_EXTRACTION = (
    "CLAIM: applied electrostatic fields repel charged particles and "
    "prevent channel occlusion in vacuum\n"
    "OBSERVED_EFFECT: charged channel walls accumulated no particle "
    "deposition while grounded channels occluded and flow stopped\n"
    "SYSTEM: vacuum chamber microfluidic channels\n"
    "INTERVENTION: applied electrostatic field of 2 kV on channel walls\n"
    "MECHANISM: electrostatic repulsion of like charges at the surface "
    "boundary\n"
    "BOUNDARY_CONDITIONS: applied voltage 2 kV, temperature -50 C\n"
    "CONSTRAINTS: none stated\n"
    "FAILURE_MODE: particle occlusion of channels\n"
    "CONFIDENCE: MEDIUM\n"
)

# a well-formed candidate instantiation bound to the medical record
GOOD_CANDIDATE_RESPONSE = (
    "MECHANISM: heparin bonding inhibits clotting cascade activation at "
    "the luminal surface\n"
    "INTERVENTION: bond heparin to the catheter luminal surface\n"
    "PREDICTED_EFFECT: thrombus area reduced by at least 50 percent "
    "under low flow\n"
    "NOVEL_DESIGN_VARIABLE: luminal heparin surface density\n"
    "TESTABLE_PREDICTION: at flow rate 50 mL/min, thrombus area is "
    "reduced by at least 50 percent versus untreated controls\n"
    "KNOWN_FAILURE_MODES: heparin leaching over weeks; bonding layer "
    "delamination\n"
    "BOUNDARY_CONDITIONS: flow rate above 20 mL/min; venous pressure "
    "below 40 mmHg\n"
    "MECHANISM_SOURCE_SPAN: Heparin bonding inhibits clotting cascade "
    "activation at the luminal surface\n"
)

# worded differently but STRUCTURALLY IDENTICAL (the A-case duplicate)
REWORDED_DUPLICATE_RESPONSE = (
    "MECHANISM: bonding of heparin to the lumen inhibits activation of "
    "the clotting cascade at the surface\n"
    "INTERVENTION: apply a heparin bond onto the catheter lumen surface\n"
    "PREDICTED_EFFECT: thrombus area decreased by 50 percent or more "
    "under low flow\n"
    "NOVEL_DESIGN_VARIABLE: density of heparin on the luminal surface\n"
    "TESTABLE_PREDICTION: thrombus area at flow rate 50 mL/min is "
    "decreased by at least 50 percent relative to untreated controls\n"
    "KNOWN_FAILURE_MODES: leaching of heparin over weeks; delamination "
    "of the bonding layer\n"
    "BOUNDARY_CONDITIONS: flow above 20 mL/min; venous pressure below "
    "40 mmHg\n"
    "MECHANISM_SOURCE_SPAN: Heparin bonding inhibits clotting cascade "
    "activation at the luminal surface\n"
)

# a GENUINELY different mechanism (the J-case survivor)
DIFFERENT_MECHANISM_RESPONSE = (
    "MECHANISM: electrostatic repulsion of like charges keeps charged "
    "particles away from the surface boundary\n"
    "INTERVENTION: charge the catheter lumen wall with an applied "
    "electrostatic field\n"
    "PREDICTED_EFFECT: particle and thrombus deposition reduced by "
    "repulsion rather than chemistry\n"
    "NOVEL_DESIGN_VARIABLE: applied lumen wall voltage\n"
    "TESTABLE_PREDICTION: deposition mass at the lumen wall is reduced "
    "as applied voltage increases from 0 to 2 kV\n"
    "KNOWN_FAILURE_MODES: discharge at high voltage; field distortion "
    "by conductive fluid\n"
    "BOUNDARY_CONDITIONS: applied voltage 0-2 kV; conductive aqueous "
    "fluid\n"
    "MECHANISM_SOURCE_SPAN: electrostatic repulsion of like charges at "
    "the surface boundary\n"
)

# no testable prediction (the F-case)
NO_PREDICTION_RESPONSE = (
    "MECHANISM: heparin bonding inhibits clotting cascade activation at "
    "the luminal surface\n"
    "INTERVENTION: bond heparin to the catheter luminal surface\n"
    "PREDICTED_EFFECT: reduced thrombus\n"
    "NOVEL_DESIGN_VARIABLE: heparin density\n"
    "TESTABLE_PREDICTION: it will work better\n"
    "KNOWN_FAILURE_MODES: leaching\n"
    "BOUNDARY_CONDITIONS: low flow\n"
    "MECHANISM_SOURCE_SPAN: Heparin bonding inhibits clotting cascade "
    "activation at the luminal surface\n"
)


def _structured(record, extraction, problem=PROBLEM):
    return ms.extract_structured_evidence_item(record, problem)


def _op(op_id):
    return next(o for o in ms.TRANSFORMATION_OPERATORS
                if o["operator_id"] == op_id)


@pytest.fixture
def medical_item(monkeypatch):
    monkeypatch.setattr(ms, "llm_generate",
                        _fake_llm([MEDICAL_EXTRACTION]))
    return _structured(MEDICAL_RECORD, MEDICAL_EXTRACTION)


@pytest.fixture
def foreign_item(monkeypatch):
    monkeypatch.setattr(ms, "llm_generate",
                        _fake_llm([FOREIGN_EXTRACTION]))
    return _structured(FOREIGN_RECORD, FOREIGN_EXTRACTION)


# ---------------------------------------------------------------------------
# Phase 1: structured evidence
# ---------------------------------------------------------------------------
class TestStructuredEvidence:
    def test_eleven_fields_present(self, medical_item):
        out = medical_item
        assert set(ms.STRUCTURED_EVIDENCE_FIELDS) - {
            "source", "provenance"} == set(out["fields"])
        assert "source" in out and "provenance" in out
        assert out["fields"]["mechanism"]["state"] == "VALID"

    def test_provenance_inherited_not_created(self, medical_item):
        # Art. VI / R401 Phase 1: no competing truth ledger — the
        # provenance is the item's own custody chain
        prov = medical_item["provenance"]
        assert "inherited_from_evidence_item" in prov["custody"]
        assert medical_item["source"]["source_id"] == "evd-med-001"
        assert medical_item["source"]["content_hash"] == "hash-med-001"

    def test_untrusted_field_is_demoted_never_kept(self, monkeypatch):
        # the model imports a field wholly absent from the record —
        # Art. XVIII: the validator must demote it to UNEXTRACTED
        imported = MEDICAL_EXTRACTION.replace(
            "SYSTEM: tunneled hemodialysis catheter lumen",
            "SYSTEM: quantum chromodynamics flux lattice")
        monkeypatch.setattr(ms, "llm_generate", _fake_llm([imported]))
        out = _structured(MEDICAL_RECORD, imported)
        assert out["fields"]["system"]["state"] == \
            "UNTRUSTED_NOT_IN_RECORD"
        assert out["fields"]["system"]["value"] == ms.UNEXTRACTED

    def test_llm_unavailable_is_honest(self, monkeypatch):
        monkeypatch.setattr(ms, "llm_generate", _fake_llm([None]))
        out = _structured(MEDICAL_RECORD, None)
        assert all(f["state"] == "LLM_UNAVAILABLE"
                   for f in out["fields"].values())
        assert out["fields"]["mechanism"]["value"] == ms.UNEXTRACTED

    def test_confidence_vocabulary_validated(self, monkeypatch):
        bad = MEDICAL_EXTRACTION.replace("CONFIDENCE: HIGH",
                                         "CONFIDENCE: ABSOLUTELY")
        monkeypatch.setattr(ms, "llm_generate", _fake_llm([bad]))
        out = _structured(MEDICAL_RECORD, bad)
        assert out["fields"]["confidence"]["state"] == "INVALID_VALUE"
        assert out["confidence"] == ms.UNEXTRACTED


# ---------------------------------------------------------------------------
# Phase 5: the reranker serves the mechanism space (recorded, honest)
# ---------------------------------------------------------------------------
class TestReranker:
    def test_mechanism_dense_record_ranks_first(self):
        recs = [MEDICAL_RECORD, {"id": "evd-x", "title": "Index of "
                "tables", "abstract": "Table of contents page."}]
        out = ms.mechanism_signal_rerank(recs, top_k=1)
        assert out["selected_ids"] == ["evd-med-001"]
        assert out["all_scores"][0]["classes_present"] > \
            out["all_scores"][1]["classes_present"]

    def test_rerank_is_not_a_relevance_verdict(self):
        out = ms.mechanism_signal_rerank([MEDICAL_RECORD], top_k=1)
        assert "NOT a relevance verdict" in out["policy"]


# ---------------------------------------------------------------------------
# Phase 2 + Phase 10 A/J/F: operators, candidates, distinctness
# ---------------------------------------------------------------------------
class TestOperatorsAndDistinctness:
    def test_five_operators_are_structurally_different(self):
        # the directive's core demand: not five prompts. The input
        # contracts must differ STRUCTURALLY (different predicates with
        # different vocabularies) and the search constraints differ.
        ids = [o["operator_id"] for o in ms.TRANSFORMATION_OPERATORS]
        assert set(ids) == {
            "DIRECT_TRANSFER", "CROSS_DOMAIN_ANALOGY",
            "GEOMETRIC_TRANSFORMATION", "BOUNDARY_CONDITION_CHANGE",
            "FAILURE_PATH_INVERSION"}
        contracts = [o["input_contract"].__code__.co_code
                     for o in ms.TRANSFORMATION_OPERATORS]
        assert len(set(contracts)) == 5  # five distinct predicates
        constraints = [o["search_constraint"]
                       for o in ms.TRANSFORMATION_OPERATORS]
        assert len(set(constraints)) == 5

    def test_direct_transfer_contract_same_system(self, medical_item):
        c = ms._contract_direct_transfer(medical_item, PROBLEM)
        assert c["satisfied"] is True
        assert c["shared_system_terms"]

    def test_cross_domain_contract_foreign_system(self, medical_item,
                                                  foreign_item):
        assert ms._contract_cross_domain_analogy(
            foreign_item, PROBLEM)["satisfied"] is True
        # a SAME-domain item never feeds the analogy operator
        assert ms._contract_cross_domain_analogy(
            medical_item, PROBLEM)["satisfied"] is False

    def test_geometry_and_boundary_and_failure_contracts(self,
                                                         medical_item):
        assert ms._contract_geometric_transformation(
            medical_item, PROBLEM)["satisfied"] is True
        assert ms._contract_boundary_condition_change(
            medical_item, PROBLEM)["satisfied"] is True
        assert ms._contract_failure_path_inversion(
            medical_item, PROBLEM)["satisfied"] is True

    def test_operator_honest_refusal_when_no_evidence(self):
        res = ms.apply_operator(_op("DIRECT_TRANSFER"), [], PROBLEM)
        assert res["state"] == "NO_APPLICABLE_EVIDENCE"
        assert "nothing" in res["note"]

    def _candidates_from(self, monkeypatch, responses, items,
                         ops=("DIRECT_TRANSFER",)):
        """One (response, item, operator) per candidate — the fake LLM
        queue serves exactly one call per apply_operator invocation."""
        out = []
        for i, resp in enumerate(responses):
            op_id = ops[0] if len(ops) == 1 else ops[i]
            item = items[i] if isinstance(items, list) else items
            monkeypatch.setattr(ms, "llm_generate",
                                _fake_llm([resp]))
            res = ms.apply_operator(_op(op_id), [item], PROBLEM)
            out.extend(c for c in res["candidates"]
                       if isinstance(c, dict))
        return out

    def test_A_near_duplicates_collapse(self, monkeypatch,
                                        medical_item):
        # two candidates: worded differently, structurally identical
        cands = self._candidates_from(
            monkeypatch,
            [GOOD_CANDIDATE_RESPONSE, REWORDED_DUPLICATE_RESPONSE],
            [medical_item, medical_item])
        assert len(cands) == 2
        assert all(c["candidate_state"] == "CANDIDATE" for c in cands)
        dedup = ms.deduplicate_candidates(cands)
        assert dedup["n_kept"] == 1
        assert dedup["dedup_events"]
        assert "differ only in wording" in \
            dedup["dedup_events"][0]["reason"]

    def test_J_genuinely_different_mechanisms_survive(self, monkeypatch,
                                                      medical_item,
                                                      foreign_item):
        # DIRECT_TRANSFER instantiates the domain-matched mechanism;
        # CROSS_DOMAIN_ANALOGY maps the foreign mechanism — genuinely
        # different causal structures, both must survive dedup
        cands = self._candidates_from(
            monkeypatch,
            [GOOD_CANDIDATE_RESPONSE, DIFFERENT_MECHANISM_RESPONSE],
            [medical_item, foreign_item],
            ops=("DIRECT_TRANSFER", "CROSS_DOMAIN_ANALOGY"))
        assert len(cands) == 2
        assert all(c["candidate_state"] == "CANDIDATE" for c in cands)
        assert {c["transformation_operator"] for c in cands} == {
            "DIRECT_TRANSFER", "CROSS_DOMAIN_ANALOGY"}
        dedup = ms.deduplicate_candidates(cands)
        assert dedup["n_kept"] == 2
        assert dedup["retain_events"]
        # the retain records the structural difference (which
        # dimensions differ)
        diff = dedup["retain_events"][-1]["difference_basis"]
        assert diff and diff["differing_dimensions"]

    def test_F_no_testable_prediction_is_not_a_candidate(self,
                                                         monkeypatch,
                                                         medical_item):
        cands = self._candidates_from(
            monkeypatch, [NO_PREDICTION_RESPONSE], [medical_item])
        assert cands[0]["candidate_state"] == \
            "NOT_A_CANDIDATE_NO_TESTABLE_PREDICTION"
        assert not cands[0]["testable_prediction_check"]["testable"]
        dedup = ms.deduplicate_candidates(cands)
        assert dedup["n_kept"] == 0

    def test_span_not_verbatim_rejects_candidate(self, monkeypatch,
                                                 medical_item):
        bad_span = GOOD_CANDIDATE_RESPONSE.replace(
            "MECHANISM_SOURCE_SPAN: Heparin bonding inhibits clotting "
            "cascade activation at the luminal surface",
            "MECHANISM_SOURCE_SPAN: an invented span that appears "
            "nowhere in the record")
        monkeypatch.setattr(ms, "llm_generate", _fake_llm([bad_span]))
        res = ms.apply_operator(_op("DIRECT_TRANSFER"), [medical_item],
                                PROBLEM)
        cand = res["candidates"][0]
        assert cand["span_binding"]["verbatim_in_record"] is False
        assert cand["candidate_state"] == "NOT_A_CANDIDATE_SPAN_NOT_VERBATIM"

    def test_candidate_carries_nine_required_fields(self, monkeypatch,
                                                    medical_item):
        monkeypatch.setattr(ms, "llm_generate",
                            _fake_llm([GOOD_CANDIDATE_RESPONSE]))
        res = ms.apply_operator(_op("DIRECT_TRANSFER"), [medical_item],
                                PROBLEM)
        cand = res["candidates"][0]
        for f in ms.CANDIDATE_REQUIRED_FIELDS:
            assert f in cand, f"missing required field {f}"
        assert cand["mechanism_graph"]["nodes"]
        assert cand["mechanism_graph"]["edges"]
        assert cand["candidate_hash"]
        assert cand["derivation_trace"]["operator"] == "DIRECT_TRANSFER"


# ---------------------------------------------------------------------------
# Phase 4 + Phase 10 B/C: mechanism-level evidence verification
# ---------------------------------------------------------------------------
class TestMechanismVerification:
    def _candidate(self, monkeypatch, item):
        monkeypatch.setattr(ms, "llm_generate",
                            _fake_llm([GOOD_CANDIDATE_RESPONSE]))
        res = ms.apply_operator(_op("DIRECT_TRANSFER"), [item], PROBLEM)
        return res["candidates"][0]

    def test_B_phenomenon_without_mechanism_is_not_enough_evidence(
            self, monkeypatch):
        # an item whose PHENOMENON overlaps the problem (thrombus,
        # occlusion, low flow) but whose mechanism vocabulary does not
        # overlap the candidate's asserted mechanism -> NOT_ENOUGH_
        # EVIDENCE, never weak support
        phenomenon_record = {
            "id": "evd-phen-004",
            "source": "pubmed",
            "title": "Catheter occlusion rates in low-flow venous "
                     "access",
            "abstract": (
                "Retrospective registry of catheter occlusion events "
                "under low flow. Occlusion and thrombus event rates are "
                "tabulated by device model. No mechanism was studied; "
                "the registry records the phenomenon only."),
            "content_hash": "hash-phen-004",
        }
        extraction = (
            "CLAIM: catheter occlusion occurs under low flow\n"
            "OBSERVED_EFFECT: occlusion and thrombus events tabulated\n"
            "SYSTEM: venous access catheters registry\n"
            "INTERVENTION: none\n"
            "MECHANISM: UNEXTRACTED\n"
            "BOUNDARY_CONDITIONS: low flow\n"
            "CONSTRAINTS: none\n"
            "FAILURE_MODE: occlusion\n"
            "CONFIDENCE: LOW\n")
        monkeypatch.setattr(ms, "llm_generate",
                            _fake_llm([extraction]))
        phen_item = ms.extract_structured_evidence_item(
            phenomenon_record, PROBLEM)
        monkeypatch.setattr(ms, "llm_generate",
                            _fake_llm([MEDICAL_EXTRACTION]))
        med_item = ms.extract_structured_evidence_item(
            MEDICAL_RECORD, PROBLEM)
        cand = self._candidate(monkeypatch, med_item)
        verdict = ms.verify_item_against_candidate(cand, phen_item,
                                                   PROBLEM)
        assert verdict["relation"] == "NOT_ENOUGH_EVIDENCE"
        assert "phenomenon support is NOT mechanism support" in \
            verdict["basis"]

    def test_C_contradictory_evidence_stays_contradicts(self, monkeypatch):
        monkeypatch.setattr(ms, "llm_generate",
                            _fake_llm([CONTRA_RECORD and
                                       "CLAIM: heparin bonding does not "
                                       "reduce thrombus under low flow\n"
                                       "OBSERVED_EFFECT: no significant "
                                       "difference in thrombus area\n"
                                       "SYSTEM: venous access grafts\n"
                                       "INTERVENTION: heparin bonding\n"
                                       "MECHANISM: heparin bonding shows "
                                       "no thrombus reduction\n"
                                       "BOUNDARY_CONDITIONS: flow rate "
                                       "50 mL/min\n"
                                       "CONSTRAINTS: none\n"
                                       "FAILURE_MODE: thrombotic "
                                       "occlusion\n"
                                       "CONFIDENCE: MEDIUM\n"]))
        contra_item = ms.extract_structured_evidence_item(
            CONTRA_RECORD, PROBLEM)
        monkeypatch.setattr(ms, "llm_generate",
                            _fake_llm([MEDICAL_EXTRACTION]))
        med_item = ms.extract_structured_evidence_item(
            MEDICAL_RECORD, PROBLEM)
        cand = self._candidate(monkeypatch, med_item)
        verdict = ms.verify_item_against_candidate(cand, contra_item,
                                                   PROBLEM)
        assert verdict["relation"] == "CONTRADICTS"
        assert verdict["contradiction_basis"]
        # the AGGREGATE keeps contradictions visible — CONTESTED state,
        # never absorbed into a support state
        agg = ms.verify_mechanism_support(
            cand, [med_item, contra_item], PROBLEM)
        assert agg["mechanism_support_state"] == "CONTESTED"
        assert agg["contradictions_visible"]
        assert agg["counts"]["SUPPORTS"] >= 1  # support remains visible

    def test_supports_requires_same_system_and_bound_mechanism(
            self, monkeypatch):
        monkeypatch.setattr(ms, "llm_generate",
                            _fake_llm([MEDICAL_EXTRACTION]))
        med_item = ms.extract_structured_evidence_item(
            MEDICAL_RECORD, PROBLEM)
        cand = self._candidate(monkeypatch, med_item)
        verdict = ms.verify_item_against_candidate(cand, med_item,
                                                   PROBLEM)
        assert verdict["relation"] == "SUPPORTS"

    def test_analogy_never_becomes_direct_support(self, monkeypatch):
        # cross-system mechanism overlap caps at PARTIALLY_SUPPORTS
        monkeypatch.setattr(ms, "llm_generate",
                            _fake_llm([FOREIGN_EXTRACTION]))
        foreign = ms.extract_structured_evidence_item(
            FOREIGN_RECORD, PROBLEM)
        monkeypatch.setattr(ms, "llm_generate",
                            _fake_llm([MEDICAL_EXTRACTION]))
        med_item = ms.extract_structured_evidence_item(
            MEDICAL_RECORD, PROBLEM)
        cand = self._candidate(monkeypatch, med_item)
        # a candidate that ASSERTS the foreign mechanism vocabulary:
        # the evidence speaks to it mechanistically, but from a
        # different system
        cand_cross = dict(cand)
        cand_cross["mechanism"] = ("electrostatic repulsion of like "
                                   "charges at the surface boundary "
                                   "prevents occlusion of the catheter "
                                   "lumen")
        verdict = ms.verify_item_against_candidate(cand_cross, foreign,
                                                   PROBLEM)
        assert verdict["relation"] == "PARTIALLY_SUPPORTS"
        assert "ANALOGY" in verdict["basis"] or "never direct support" \
            in verdict["basis"]

    def test_irrelevant_evidence_is_irrelevant(self, monkeypatch):
        off_record = {
            "id": "evd-off-005",
            "source": "arxiv",
            "title": "Galois representations of elliptic curves",
            "abstract": "We prove modularity results for Galois "
                        "representations attached to elliptic curves "
                        "over the rationals.",
        }
        extraction = (
            "CLAIM: modularity of Galois representations\n"
            "OBSERVED_EFFECT: proof of modularity\n"
            "SYSTEM: elliptic curves over the rationals\n"
            "INTERVENTION: UNEXTRACTED\n"
            "MECHANISM: UNEXTRACTED\n"
            "BOUNDARY_CONDITIONS: UNEXTRACTED\n"
            "CONSTRAINTS: UNEXTRACTED\n"
            "FAILURE_MODE: UNEXTRACTED\n"
            "CONFIDENCE: LOW\n")
        monkeypatch.setattr(ms, "llm_generate", _fake_llm([extraction]))
        off_item = ms.extract_structured_evidence_item(off_record,
                                                       PROBLEM)
        monkeypatch.setattr(ms, "llm_generate",
                            _fake_llm([MEDICAL_EXTRACTION]))
        med_item = ms.extract_structured_evidence_item(
            MEDICAL_RECORD, PROBLEM)
        cand = self._candidate(monkeypatch, med_item)
        verdict = ms.verify_item_against_candidate(cand, off_item,
                                                   PROBLEM)
        assert verdict["relation"] == "IRRELEVANT"


# ---------------------------------------------------------------------------
# Phase 10 D/E/G/I: the downstream gates reject invalid candidates
# ---------------------------------------------------------------------------
class TestDownstreamGateRejection:
    ENG_HYD = {"engineering_core": {"critical_parameters": [
        {"label": "primary lumen diameter", "value": 1.0,
         "domain": "fluidics_hydraulic"},
        {"label": "floor lumen diameter", "value": 0.6,
         "domain": "fluidics_hydraulic"}]}}

    def test_D_invalid_transformed_geometry_is_rejected(self):
        # a geometric transformation that yields an impossible lumen
        # (120 mm) is killed at the physics gate BEFORE simulation
        from discovery_fabric.engine import physics_gate as pg
        eng = {"engineering_core": {"critical_parameters": [
            {"label": "primary lumen diameter", "value": 120.0,
             "domain": "fluidics_hydraulic"}]}}
        out = pg.evaluate_candidate_physics({}, eng, {})
        assert out["plausibility_gate"]["status"] == \
            "PLAUSIBILITY_BOUND_VIOLATED"
        assert any(v["class"] == "GEOMETRIC_SCALE"
                   for v in out["plausibility_gate"]["violations"])
        assert out["baseline_comparison"] is None

    def test_E_impossible_boundary_condition_is_rejected(self):
        from discovery_fabric.engine import physics_core as pc
        from discovery_fabric.engine import physics_gate as pg
        spec = pg._network_spec(1.0, 0.6, "thermal")
        spec["fluid"]["temperature_K"] = 500.0
        r = pc.solve_network(spec)
        assert r["status"] == "PLAUSIBILITY_BOUND_VIOLATED"
        assert any(v["class"] == "THERMAL" for v in r["violations"])

    def test_G_baseline_equivalent_candidate_is_killed(self):
        # select_survivors makes DOES_NOT_BEAT_BASELINE candidates
        # ineligible for strongest-survivor selection — the release can
        # never claim an improvement the physics says is not delivered
        from discovery_fabric.engine.engineering_attack import \
            select_survivors
        candidates = [
            {"candidate_id": "cand-baseline-equiv", "killed": False,
             "attack": {"overall": "SURVIVED", "counts": {}},
             "quality": {"verdict": "PASS"},
             "physics_lifecycle": "DOES_NOT_BEAT_BASELINE"},
            {"candidate_id": "cand-beats", "killed": False,
             "attack": {"overall": "SURVIVED", "counts": {}},
             "quality": {"verdict": "PASS"},
             "physics_lifecycle": "BEATS_BASELINE"},
        ]
        sel = select_survivors(candidates)
        assert sel.get("selected") != "cand-baseline-equiv"

    def test_I_unsupported_mechanism_is_mechanism_not_simulatable(self):
        # an out-of-scope mechanism gets the honest refusal, never a
        # fabricated physics comparison
        from discovery_fabric.engine import physics_gate as pg
        from discovery_fabric.engine.run import _physics_lifecycle
        eng = {"engineering_core": {"critical_parameters": [
            {"label": "antenna gain", "value": 5.0,
             "domain": "electromagnetics"}]}}
        out = pg.evaluate_candidate_physics({}, eng, {})
        assert out["applicable"] is False
        assert _physics_lifecycle(out) == "MECHANISM_NOT_SIMULATABLE"
        # and a missing evaluation is also the honest refusal
        assert _physics_lifecycle({}) == "MECHANISM_NOT_SIMULATABLE"

    def test_no_new_physics_solvers_were_added(self):
        # Phase 7 guard: the V0 hydraulic solver remains the ONLY
        # physics model — physics_core must not grow CFD/FEA/thermal/
        # electromagnetic SOLVERS (bound families are checks, not
        # solvers)
        from discovery_fabric.engine import physics_core as pc
        src = Path(pc.__file__).read_text().lower()
        for banned in ("cfd", "finite element", "navier-stokes",
                       "maxwell solver", "electromagnetic solver"):
            assert banned not in src, f"banned solver vocabulary: {banned}"


# ---------------------------------------------------------------------------
# Phase 6 + Phase 10 H: the independent attacker
# ---------------------------------------------------------------------------
class TestIndependentAttack:
    ATTACK_KILL_RESPONSE = (
        "MECHANISM_FAILURE: SURVIVE — the mechanism is plausible\n"
        "BOUNDARY_CONDITION_FAILURE: RISK — boundary at low flow may "
        "weaken the effect\n"
        "EVIDENCE_CONTRADICTION: SURVIVE — no contradicting evidence "
        "cited\n"
        "BASELINE_EQUIVALENCE: SURVIVE — effect differs from baseline\n"
        "IMPLEMENTATION_IMPOSSIBILITY: KILL — the design requires "
        "bonding heparin uniformly inside a 1 mm catheter lumen while "
        "preserving the flow passage, and no manufacturing process can "
        "achieve uniform molecular bonding on an interior tube surface "
        "at production scale without blocking the lumen\n"
        "MEASUREMENT_AMBIGUITY: SURVIVE — the prediction is measurable\n"
    )

    NAKED_KILL_RESPONSE = (
        "MECHANISM_FAILURE: KILL — it fails\n"
        "BOUNDARY_CONDITION_FAILURE: SURVIVE — fine\n"
        "EVIDENCE_CONTRADICTION: SURVIVE — fine\n"
        "BASELINE_EQUIVALENCE: SURVIVE — fine\n"
        "IMPLEMENTATION_IMPOSSIBILITY: SURVIVE — buildable\n"
        "MEASUREMENT_AMBIGUITY: SURVIVE — measurable\n"
    )

    ALL_SURVIVE_RESPONSE = "\n".join(
        f"{c}: SURVIVE — no failure found in this class, the "
        f"candidate holds" for c in ia.ATTACK_CLASSES)

    CAND = {
        "candidate_id": "cand:MS:DIRECT_TRANSFER:test01",
        "mechanism": "heparin bonding inhibits clotting cascade "
                     "activation at the luminal surface",
        "intervention": "bond heparin to the catheter luminal surface",
        "predicted_effect": "thrombus area reduced by 50 percent",
        "testable_prediction": "thrombus area reduced by 50 percent at "
                               "50 mL/min",
        "novel_design_variable": "heparin surface density",
        "known_failure_modes": ["leaching", "delamination"],
        "constraint_set": {"boundary_conditions": "low flow"},
    }

    def test_H_implementation_impossible_candidate_is_killed(self,
                                                             monkeypatch):
        monkeypatch.setattr(ms, "llm_generate",
                            _fake_llm([self.ATTACK_KILL_RESPONSE]))
        rec = ia.independent_attack(self.CAND, PROBLEM, [MEDICAL_RECORD],
                                    generator_provider="zai")
        assert rec["overall"] == "KILLED"
        assert rec["state"] == "ATTACK_RUN"
        kills = [i for i in rec["items"] if i["verdict"] == "KILL"]
        assert len(kills) == 1
        assert kills[0]["attack_class"] == "IMPLEMENTATION_IMPOSSIBILITY"
        assert "manufacturing" in kills[0]["basis"]

    def test_naked_kill_without_basis_is_invalid(self, monkeypatch):
        # Art. XVIII bypass attempt: a KILL without a concrete basis is
        # INVALID — never applied, never fabricated
        monkeypatch.setattr(ms, "llm_generate",
                            _fake_llm([self.NAKED_KILL_RESPONSE]))
        rec = ia.independent_attack(self.CAND, PROBLEM, [MEDICAL_RECORD],
                                    generator_provider="zai")
        assert rec["overall"] == "UNCERTAIN"
        assert rec["counts"]["INVALID"] == 1
        assert not rec.get("kill_basis")

    def test_all_survive_is_survived(self, monkeypatch):
        monkeypatch.setattr(ms, "llm_generate",
                            _fake_llm([self.ALL_SURVIVE_RESPONSE]))
        rec = ia.independent_attack(self.CAND, PROBLEM, [MEDICAL_RECORD],
                                    generator_provider="zai")
        assert rec["overall"] == "SURVIVED"
        assert rec["counts"]["SURVIVE"] == 6

    def test_attack_incomplete_never_kills(self, monkeypatch):
        monkeypatch.setattr(ms, "llm_generate", _fake_llm([None]))
        rec = ia.independent_attack(self.CAND, PROBLEM, [MEDICAL_RECORD],
                                    generator_provider="zai")
        assert rec["overall"] == "ATTACK_INCOMPLETE"
        assert "NOT killed by an attack that did not execute" in rec["note"]

    def test_independence_mode_recorded_and_honest(self, monkeypatch):
        # same provider -> SEPARATE_CONTEXT (disclosed, never claimed as
        # provider separation)
        monkeypatch.setattr(ms, "llm_generate", _fake_llm(
            [self.ALL_SURVIVE_RESPONSE]))
        rec = ia.independent_attack(self.CAND, PROBLEM, [MEDICAL_RECORD],
                                    generator_provider="fake")
        # the fake call site ignores exclusion; the honest fallback
        # records SEPARATE_CONTEXT
        assert rec["independence_mode"] in ia.INDEPENDENCE_MODES
        if rec["attacker_provider"] == rec["generator_provider"]:
            assert rec["independence_mode"] == "SEPARATE_CONTEXT"
            assert "no alternative provider" in rec["independence_note"]

    def test_six_attack_classes_are_the_directive_set(self):
        assert set(ia.ATTACK_CLASSES) == {
            "MECHANISM_FAILURE", "BOUNDARY_CONDITION_FAILURE",
            "EVIDENCE_CONTRADICTION", "BASELINE_EQUIVALENCE",
            "IMPLEMENTATION_IMPOSSIBILITY", "MEASUREMENT_AMBIGUITY"}


# ---------------------------------------------------------------------------
# The MECHANISM_SPACE stage entry gate + the orchestrator
# ---------------------------------------------------------------------------
class TestStageIntegration:
    def test_entry_gate_skips_on_unverified_evidence(self):
        from discovery_fabric.engine.stage_entry import justify
        from discovery_fabric.engine.candidate import Candidate
        env = Candidate(problem=PROBLEM, problem_id="r401_adv")
        env.evidence = [MEDICAL_RECORD]
        # no verification ran: no classification, no adjudication
        block = justify("MECHANISM_SPACE", env, {}, set())
        assert block["entry_status"] == "SKIPPED"
        assert "EVIDENCE_VERIFICATION_FAILED" in block["skip_reason"]

    def test_entry_gate_allows_with_verified_evidence(self):
        from discovery_fabric.engine.stage_entry import justify
        from discovery_fabric.engine.candidate import Candidate
        env = Candidate(problem=PROBLEM, problem_id="r401_adv")
        env.evidence = [MEDICAL_RECORD]
        env.evidence_classification = {
            "items": [{"classification": "DIRECT_SUPPORT"}]}
        block = justify("MECHANISM_SPACE", env, {}, set())
        assert block["entry_status"] == "ALLOWED"
        assert block["prerequisite"] == "VERIFIED_EVIDENCE"

    def test_stage_order_carries_mechanism_space(self):
        from discovery_fabric.engine.adapters import STAGE_ORDER
        assert STAGE_ORDER.index("MECHANISM_SPACE") == \
            STAGE_ORDER.index("VERIFY") + 1
        # R515 IMPROVE-placeholder removal: the chain is 15 stages
        # (documented change)
        assert len(STAGE_ORDER) == 15

    def test_adapter_skips_honestly_when_gate_fails(self):
        from discovery_fabric.engine.adapters import MechanismSpaceAdapter
        from discovery_fabric.engine.candidate import Candidate
        env = Candidate(problem=PROBLEM, problem_id="r401_adv")
        env.evidence = [MEDICAL_RECORD]
        res = MechanismSpaceAdapter().execute(env, {"run_id": "r"})
        assert res["apply_to"]["mechanism_space"]["state"] == \
            "SKIPPED_EVIDENCE_VERIFICATION_FAILED"

    def test_no_evidence_is_honest_refusal(self):
        space = ms.build_mechanism_space(PROBLEM, [])
        assert space["state"] == "NO_EVIDENCE"
        assert space["metrics"]["mechanism_candidates_generated"] == 0


# ---------------------------------------------------------------------------
# The full orchestrated space (hermetic e2e of the stage function)
# ---------------------------------------------------------------------------
class TestBuildMechanismSpace:
    def test_full_space_with_two_records(self, monkeypatch):
        # hermetic: the live multi-source expansion is OFF for this
        # test (the expansion itself is live-tested by the e2e run)
        import os
        monkeypatch.setenv("R401_NO_EXPANSION", "1")
        # extraction (x2, rerank order is deterministic) + operator
        # instantiation calls — the queue serves them in order; failures
        # at the tail are honest states, never fabrications
        responses = [
            MEDICAL_EXTRACTION, FOREIGN_EXTRACTION,     # extractions
            GOOD_CANDIDATE_RESPONSE,                    # DIRECT_TRANSFER
            DIFFERENT_MECHANISM_RESPONSE,               # CROSS_DOMAIN
            None, None, None, None, None,               # others fail
        ]
        monkeypatch.setattr(ms, "llm_generate", _fake_llm(responses))
        space = ms.build_mechanism_space(
            PROBLEM, [MEDICAL_RECORD, FOREIGN_RECORD], top_k=2,
            per_operator_item_cap=1, min_candidates=2)
        assert space["state"] in ("BUILT", "BUILT_BELOW_MIN")
        assert space["n_candidates_generated"] >= 1
        m = space["metrics"]
        for k in ("mechanism_candidates_generated",
                  "mechanism_candidates_after_dedup", "operator_counts",
                  "material_distinctness_rate",
                  "evidence_mechanism_support_rate",
                  "contradiction_rate", "testable_prediction_rate"):
            assert k in m, f"missing Phase 9 metric {k}"

    def test_metrics_are_honest_when_llm_unavailable(self, monkeypatch):
        import os
        monkeypatch.setenv("R401_NO_EXPANSION", "1")
        monkeypatch.setattr(ms, "llm_generate", _fake_llm([None]))
        space = ms.build_mechanism_space(PROBLEM, [MEDICAL_RECORD],
                                         top_k=1)
        # zero candidates generated — honest, never fabricated
        assert space["metrics"][
            "mechanism_candidates_generated"] == 0
        assert space["metrics"]["material_distinctness_rate"] is None
