"""tests/test_r402_discovery_integrity.py — R402: the pinned attacks.

Every test here is the ADVERSARIAL PROBE that found the defect (the
external audit's own attacks), turned into the test that pins the fix
(Art. XVII/XVIII: the attack that found the bug must be the test that
holds the fix). All tests are hermetic: no network, no live LLM, the
cemetery sandboxed by the conftest guard.

  1. Audit probes A/B/C (distinctness v1 defect): identical causal
     graph + renamed knob / pure synonym / added specificity — the v1
     instrument kept ALL of them as GENUINE_MECHANISM_DIFFERENCE. v2
     must not count ANY of them as materially distinct.
  2. No universal merger: genuinely different causal cores stay
     DISTINCT (Art. V).
  3. The diversity metric counts DISTINCT verdicts only (Art. XLVIII).
  4. Search-space neutrality: the hardcoded "prevention coating flow"
     solution class is gone; queries derive from problem facts and
     carry derivation marks (Art. XLIII) — measured across the audit's
     8 domains.
  5. Evidence boundary: the frozen plane and the post-freeze expansion
     plane are separately hashed; every candidate's evidence bundle
     carries the Art. XLIV fields (audit CB-3).
  6. Disabled stage honesty: an unevaluated verification yields
     UNKNOWN, never REJECTED (audit NF-2, Art. XXV/LXI).
  7. Rejection reasons carry the kill dimensions (audit CB-6).
  8. The declared stage graph resolves: depends_on is in the
     STAGE_ORDER namespace; ADAPTERS keys == STAGE_ORDER entries
     (audit NF-1 + CB-9).
  9. Cemetery universality: a PROVEN_INVARIANT written in NEW domain
     vocabulary hard-blocks a matching candidate (audit CB-5), and the
     mechanism space CONSUMES the cemetery (Art. LI).
  10. TLS verification is ON by default with a recorded opt-out
      (audit CB-10).
  11. The operator item cap that produced the space is recorded
      (audit CB-12).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import mechanism_space as ms  # noqa: E402


# ---------------------------------------------------------------------------
# shared fixtures: minimal candidate dicts with FULL control of the
# causal graph and the envelope fields (the distinctness instrument's
# exact inputs)
# ---------------------------------------------------------------------------
def _cand(graph_terms: dict, intervention: str, knob: str,
          boundary: str, failures: str, effect: str = "") -> dict:
    nodes = {
        "intervention_site": {"label": "INTERVENTION",
                              "terms": sorted(graph_terms.get(
                                  "intervention_site", set()))},
        "causal_agent": {"label": "MECHANISM",
                         "terms": sorted(graph_terms.get(
                             "causal_agent", set()))},
        "physical_effect": {"label": "PREDICTED_EFFECT",
                            "terms": sorted(graph_terms.get(
                                "physical_effect", set()))},
        "observed_outcome": {"label": "OBSERVED_EFFECT",
                             "terms": sorted(graph_terms.get(
                                 "observed_outcome", set()))},
    }
    edges = [
        {"from": "intervention_site", "to": "causal_agent",
         "relation": "ACTIVATES"},
        {"from": "causal_agent", "to": "physical_effect",
         "relation": "PRODUCES"},
    ]
    if nodes["observed_outcome"]["terms"]:
        edges.append({"from": "physical_effect", "to": "observed_outcome",
                      "relation": "MEASURES_AGAINST"})
    return {
        "candidate_id": "cand",
        "candidate_hash": "hash",
        "candidate_state": "CANDIDATE",
        "mechanism_graph": {"nodes": nodes, "edges": edges,
                            "graph_version": "mechanism_graph/1.0.0"},
        "intervention": intervention,
        "predicted_effect": effect,
        "constraint_set": {"boundary_conditions": boundary},
        "known_failure_modes": [f.strip() for f in failures.split(";")
                                if f.strip()],
        "novel_design_variable": knob,
    }


HEPARIN_GRAPH = {
    "intervention_site": {"heparin", "bond", "catheter", "luminal",
                          "surface"},
    "causal_agent": {"heparin", "bonding", "inhibits", "clotting",
                     "cascade", "activation", "surface"},
    "physical_effect": {"thrombus", "area", "reduced", "percent",
                        "low", "flow"},
    "observed_outcome": {"occlusion", "days"},
}

BASE = dict(
    graph_terms=HEPARIN_GRAPH,
    intervention="bond heparin to the catheter luminal surface",
    knob="luminal heparin surface density",
    boundary="flow rate above 20 mL/min; venous pressure below 40 mmHg",
    failures="heparin leaching over weeks; bonding layer delamination",
    effect="thrombus area reduced by at least 50 percent under low flow",
)


# ---------------------------------------------------------------------------
# 1. The audit's probes A/B/C — identical causal graph, envelope deltas
# ---------------------------------------------------------------------------
class TestAuditProbesDistinctness:
    """The exact probes the external auditor ran against the v1
    instrument (kept 2/2 GENUINE_MECHANISM_DIFFERENCE at graph Jaccard
    1.0). v2 must return EQUIVALENT or INDETERMINATE — never DISTINCT,
    never counted by the diversity metric."""

    def _probe(self, **overrides) -> None:
        base = dict(_cand(**BASE), candidate_id="c0",
                    candidate_hash="h0")
        probe = dict(_cand(**{**BASE, **overrides}), candidate_id="c1",
                     candidate_hash="h1")
        cmp = ms.compare_candidates(base, probe)
        # the causal core is IDENTICAL by construction
        assert cmp["causal_core_jaccard"] == 1.0
        assert cmp["verdict"] != "DISTINCT", (
            f"audit probe defect: identical causal core + envelope delta "
            f"counted as DISTINCT ({cmp['verdict']}): {cmp['basis']}")
        dedup = ms.deduplicate_candidates([base, probe])
        assert dedup["n_distinct"] == 1, (
            "an identical causal graph with an envelope delta must not "
            "create a second materially distinct mechanism")
        return cmp

    def test_probe_A_renamed_design_knob(self):
        # A: renamed design knob (same physics, new knob name)
        cmp = self._probe(knob="luminal anticoagulant loading density")
        assert cmp["verdict"] == "EQUIVALENT"
        assert "design variable" in cmp["basis"]

    def test_probe_B_pure_synonym_rename(self):
        # B: pure synonym rename of the knob
        cmp = self._probe(knob="surface concentration of bonded heparin")
        assert cmp["verdict"] == "EQUIVALENT"

    def test_probe_C_added_specificity(self):
        # C: added specificity in the boundary conditions
        cmp = self._probe(
            boundary=("flow rate above 20 mL/min; venous pressure below "
                      "40 mmHg; temperature 37 C; hematocrit 30-45 "
                      "percent"))
        assert cmp["verdict"] == "INDETERMINATE"
        assert "boundary" in cmp["basis"]
        # INDETERMINATE is retained but never counted as distinct
        a = dict(_cand(**BASE), candidate_id="c0", candidate_hash="h0")
        b = dict(_cand(**{**BASE, "boundary": (
            "flow rate above 20 mL/min; venous pressure below 40 "
            "mmHg; temperature 37 C; hematocrit 30-45 percent")}),
            candidate_id="c1", candidate_hash="h1")
        dedup = ms.deduplicate_candidates([a, b])
        assert dedup["n_kept"] == 2          # kept, visible
        assert dedup["n_distinct"] == 1      # but not counted

    def test_three_verdict_vocabulary_exists(self):
        assert ms.DISTINCTNESS_VERDICTS == (
            "DISTINCT", "EQUIVALENT", "INDETERMINATE")
        assert ms.DISTINCTNESS_INSTRUMENT_VERSION.startswith(
            "mechanism_distinctness/2")


# ---------------------------------------------------------------------------
# 2. No universal merger (Art. V) — genuinely different cores survive
# ---------------------------------------------------------------------------
class TestNoUniversalMerger:
    def test_genuinely_different_cores_stay_distinct(self):
        base = dict(_cand(**BASE), candidate_id="c0",
                    candidate_hash="h0")
        different = dict(_cand(
            graph_terms={
                "intervention_site": {"applied", "electrostatic",
                                      "field", "lumen", "wall"},
                "causal_agent": {"electrostatic", "repulsion", "like",
                                 "charges", "boundary"},
                "physical_effect": {"particle", "deposition",
                                    "reduced", "repulsion"},
                "observed_outcome": {"occlusion", "grounded"},
            },
            intervention="charge the catheter lumen wall with an "
                         "applied electrostatic field",
            knob="applied lumen wall voltage",
            boundary="applied voltage 0-2 kV; conductive aqueous fluid",
            failures="discharge at high voltage; field distortion",
            effect="deposition mass reduced as voltage increases"),
            candidate_id="c1", candidate_hash="h1")
        cmp = ms.compare_candidates(base, different)
        assert cmp["verdict"] == "DISTINCT"
        dedup = ms.deduplicate_candidates([base, different])
        assert dedup["n_kept"] == 2
        assert dedup["n_distinct"] == 2
        assert dedup["retain_events"][-1]["difference_basis"][
            "differing_dimensions"]

    def test_wording_only_duplicate_still_merges(self):
        # the v1 positive case must survive the v2 instrument: a
        # wording-only duplicate whose causal core is >= the merge bar
        # (this pair measures aggregate Jaccard ~0.9) still collapses
        base = dict(_cand(**BASE), candidate_id="c0",
                    candidate_hash="h0")
        reworded = dict(_cand(
            graph_terms={
                "intervention_site": HEPARIN_GRAPH[
                    "intervention_site"],
                "causal_agent": HEPARIN_GRAPH["causal_agent"],
                # ONE wording substitution: reduced -> decreased
                "physical_effect": {"thrombus", "area", "decreased",
                                    "percent", "low", "flow"},
                "observed_outcome": HEPARIN_GRAPH[
                    "observed_outcome"],
            },
            intervention="apply a heparin bond onto the catheter "
                         "luminal surface",
            knob="density of heparin on the luminal surface",
            boundary=BASE["boundary"],
            failures="bonding layer delamination; heparin leaching "
                     "over weeks",
            effect="thrombus area decreased by at least 50 percent "
                   "under low flow"),
            candidate_id="c1", candidate_hash="h1")
        cmp = ms.compare_candidates(base, reworded)
        assert cmp["causal_core_jaccard"] >= 0.8
        dedup = ms.deduplicate_candidates([base, reworded])
        assert dedup["n_kept"] == 1
        assert dedup["n_equivalent_merged"] == 1
        # the merge must be SEMANTIC (near-duplicate), not the trivial
        # identical-hash path — the comparison record proves it
        assert dedup["dedup_events"][0]["reason"].startswith(
            "NEAR_DUPLICATE")
        assert "differ only in wording" in \
            dedup["dedup_events"][0]["reason"]


# ---------------------------------------------------------------------------
# 3. The diversity metric counts DISTINCT only (Art. XLVIII)
# ---------------------------------------------------------------------------
class TestDiversityMetric:
    def test_metrics_count_distinct_not_retained(self):
        # three candidates of ONE mechanism family: the base + two
        # knob-renames (Art. XLII: renames cannot create inventions)
        base = dict(_cand(**BASE), candidate_id="c0",
                    candidate_hash="h0")
        knob_renamed = dict(_cand(**{**BASE, "knob": "anticoagulant "
                                     "loading"}), candidate_id="c1",
                            candidate_hash="h1")
        knob_renamed2 = dict(_cand(**{**BASE, "knob": "bonded drug "
                                      "dosage"}), candidate_id="c2",
                             candidate_hash="h2")
        generated = [base, knob_renamed, knob_renamed2]
        space = {"distinctness": None}
        dedup = ms.deduplicate_candidates(generated)
        retained = [c for c in generated
                    if c["candidate_state"] == "CANDIDATE"
                    and c.get("distinctness_verdict") != "EQUIVALENT"]
        metrics = ms._metrics(space, generated, retained, [], 2)
        # 3 generated, 1 distinct family, 2 knob-renames merged
        assert metrics["material_distinctness_rate"] == round(1 / 3, 3)
        assert metrics["material_mechanism_diversity"]["n_distinct"] == 1
        assert metrics["material_mechanism_diversity"][
            "n_equivalent_merged"] == 2
        assert metrics["mechanism_candidates_after_dedup"] == 1

    def test_instrument_version_reported(self):
        dedup = ms.deduplicate_candidates([_cand(**BASE)])
        assert dedup["instrument_version"].startswith(
            "mechanism_distinctness/2")


# ---------------------------------------------------------------------------
# 4. Search-space neutrality (Art. XLIII) — the 8 audit domains
# ---------------------------------------------------------------------------
AUDIT_DOMAINS = [
    ("lithium-ion battery pack", "thermal runaway"),
    ("DC fast charger", "DC arc fault"),
    ("anaerobic digester", "rag clogging"),
    ("orthopedic hip implant", "aseptic loosening"),
    ("precision oscillator", "humidity drift"),
    ("semiconductor wafer handler", "surface pickup"),
    ("steam turbine blade", "blade erosion"),
    ("urinary catheter", "catheter obstruction"),
]

_SOLUTION_CLASS_WORDS = ("coating", "flow", "prevention")


class TestSearchSpaceNeutrality:
    @pytest.mark.parametrize("device,failure", AUDIT_DOMAINS)
    def test_no_hardcoded_solution_class_across_domains(
            self, monkeypatch, device, failure):
        # hermetic: the queries are computed BEFORE the R401_NO_EXPANSION
        # early return, so the env flag gives us the exact query text
        # with zero network calls
        monkeypatch.setenv("R401_NO_EXPANSION", "1")
        problem = {
            "device": device, "failure_mode": failure,
            "failure": f"{failure} of the {device}",
            "constraint": "maintain rated performance under stated "
                          "operating conditions"}
        out = ms.multi_source_expansion(problem)
        # the audit measured the v1 query hardcoding "prevention
        # coating flow" into EVERY domain; v2 must contain none of it
        for qname, q in out["queries"].items():
            text = (q["text"] or "").lower() if isinstance(
                q, str) else str(q.get("text", "")).lower()
            for word in _SOLUTION_CLASS_WORDS:
                assert word not in text, (
                    f"hardcoded solution-class word '{word}' leaked "
                    f"into the {qname} query for {device}/{failure}: "
                    f"{text} (Art. XLIII violation)")
            # derivation is recorded per query (Art. XLIII)
            if not isinstance(q, str):
                assert q["derivation"] in (
                    "DERIVED_FROM_PROBLEM_FACTS",
                    "DERIVED_FROM_EVIDENCE", "EXPLORATORY_HYPOTHESIS")
        assert out["search_space_neutrality"][
            "solution_class_injection"] == "NONE"

    def test_queries_derive_from_problem_facts(self, monkeypatch):
        monkeypatch.setenv("R401_NO_EXPANSION", "1")
        problem = {
            "device": "steam turbine blade", "failure_mode": "erosion",
            "failure": "erosion of the blade leading edge",
            "constraint": "maintain efficiency within 2 percent"}
        out = ms.multi_source_expansion(problem)
        q_mech = out["queries"]["mechanism"]["text"].lower()
        # the constraint vocabulary (the unmet need) must be present —
        # the query is EARNED from the problem, not injected
        assert "erosion" in q_mech
        assert out["queries"]["mechanism"]["term_sources"]["constraint"]


# ---------------------------------------------------------------------------
# 5. Evidence boundary (Art. XLIV) — audit CB-3
# ---------------------------------------------------------------------------
class TestEvidenceBoundary:
    def test_two_planes_separately_hashed(self, monkeypatch):
        monkeypatch.setenv("R401_NO_EXPANSION", "1")
        ev = [{"id": "ev-1", "source": "europepmc",
               "title": "t", "abstract": "a" * 300,
               "content_hash": "ch-1"}]
        monkeypatch.setattr(
            ms, "multi_source_expansion", lambda problem: {
                "expansion_version": "multi_source_expansion/2.0.0",
                "queries": {}, "sources": {},
                "records": [{
                    "id": "exp-1", "source": "openalex",
                    "title": "cross-domain record",
                    "abstract": "b" * 300, "content_hash": "ch-exp-1"}],
                "n_records": 1,
                "evidence_version": ms._evidence_version_record(
                    "SEARCH_OK", [{"id": "exp-1",
                                   "content_hash": "ch-exp-1"}]),
            })
        se = ms.build_structured_evidence(
            {"problem_id": "p1", "device": "d", "failure_mode": "f",
             "failure": "f of d", "constraint": "c"}, ev, top_k=2)
        boundary = se["evidence_boundary"]
        # the frozen plane and the expansion plane are SEPARATELY
        # hashed — never a silent union
        frozen_h = boundary["frozen_plane"]["evidence_hash"]
        exp_h = boundary["expansion_plane"]["evidence_hash"]
        assert frozen_h and exp_h and frozen_h != exp_h
        assert boundary["frozen_plane"]["evidence_snapshot_id"] != \
            boundary["expansion_plane"]["evidence_snapshot_id"]
        # plane membership travels on every structured item
        planes = {it.get("_evidence_plane") for it in se["items"]}
        assert planes == {"FROZEN_PRIMARY", "DISCOVERY_EXPANSION"}

    def test_candidates_carry_article_xliv_fields(self, monkeypatch):
        monkeypatch.setenv("R401_NO_EXPANSION", "1")
        from tests.test_r401_mechanism_space import (
            MEDICAL_RECORD, MEDICAL_EXTRACTION, GOOD_CANDIDATE_RESPONSE,
            PROBLEM, _fake_llm)
        monkeypatch.setattr(
            ms, "multi_source_expansion", lambda problem: {
                "expansion_version": "multi_source_expansion/2.0.0",
                "queries": {}, "sources": {}, "records": [],
                "n_records": 0,
                "evidence_version": ms._evidence_version_record(
                    "DISABLED", [])})
        monkeypatch.setattr(ms, "llm_generate",
                            _fake_llm([MEDICAL_EXTRACTION,
                                       GOOD_CANDIDATE_RESPONSE]))
        space = ms.build_mechanism_space(
            PROBLEM, [MEDICAL_RECORD], top_k=1,
            per_operator_item_cap=1, min_candidates=1)
        cand = space["candidates"][0]
        eb = cand["evidence_bundle"]
        for field in ("evidence_plane", "evidence_snapshot_id",
                      "evidence_hash", "retrieval_role",
                      "retrieval_version", "retrieval_sources",
                      "retrieval_timestamp"):
            assert field in eb, (
                f"Art. XLIV field {field} missing from evidence_bundle")
        assert eb["evidence_plane"] == "FROZEN_PRIMARY"
        assert eb["evidence_snapshot_id"].startswith("evsnap_")
        assert eb["evidence_hash"]
        assert boundary_present(space)

    def test_disabled_expansion_carries_version_record(self, monkeypatch):
        monkeypatch.setenv("R401_NO_EXPANSION", "1")
        out = ms.multi_source_expansion({"device": "d",
                                          "failure_mode": "f"})
        assert out["state"].startswith("DISABLED_BY_ENV")
        assert out["evidence_version"]["evidence_snapshot_id"]
        assert out["evidence_version"]["freeze_event"]["event"] == \
            "NEW_FREEZE_PERFORMED"


def boundary_present(space) -> bool:
    se = space.get("structured_evidence") or {}
    return bool((se.get("evidence_boundary") or {}).get("frozen_plane"))


# ---------------------------------------------------------------------------
# 6. Disabled-stage honesty (Art. XXV/LXI) — audit NF-2
# ---------------------------------------------------------------------------
class TestDisabledStageHonesty:
    def test_unevaluated_verification_is_unknown_not_rejected(self):
        from discovery_fabric.a2.classify import classify
        # the audit's exact failure: VERIFY stage disabled ->
        # evidence_verification = {} -> final REJECTED "evidence
        # verification failed". v2: UNKNOWN, stage state named.
        res = classify({"falsification_test": "x" * 20}, {},
                       {"prior_art_status": "NO_MATCH_FOUND"},
                       {"overall": "PASS"})
        assert res["final_status"] == "UNKNOWN"
        assert res["verification_state"] == "NOT_EVALUATED"
        assert "NOT_EVALUATED" in res["reason"]
        assert "never negative knowledge" in res["reason"]

    def test_explicit_not_run_state_is_unknown(self):
        from discovery_fabric.a2.classify import classify
        res = classify({"falsification_test": "x" * 20},
                       {"state": "NOT_RUN"},
                       {"prior_art_status": "NO_MATCH_FOUND"},
                       {"overall": "PASS"})
        assert res["final_status"] == "UNKNOWN"

    def test_real_verification_failure_still_rejects_with_issues(self):
        from discovery_fabric.a2.classify import classify
        # a verification that RAN and failed is real negative
        # knowledge — REJECTED, and now the reason says WHY
        res = classify(
            {"falsification_test": "x" * 20},
            {"verified": False,
             "issues": ["mechanism span not verbatim in record",
                        "source hash mismatch"]},
            {"prior_art_status": "NO_MATCH_FOUND"},
            {"overall": "PASS"})
        assert res["final_status"] == "REJECTED"
        assert res["verification_state"] == "EVALUATED_FAILED"
        assert "mechanism span not verbatim" in res["reason"]


# ---------------------------------------------------------------------------
# 7. Rejection reason completeness (Art. LXIII) — audit CB-6
# ---------------------------------------------------------------------------
class TestRejectionReasonCompleteness:
    def test_empty_reason_falls_back_to_kill_dimensions(self):
        from discovery_fabric.a2.classify import classify
        # v1 rendered "adversarial challenge failed: " (empty tail)
        res = classify(
            {"falsification_test": "x" * 20},
            {"verified": True},
            {"prior_art_status": "NO_MATCH_FOUND"},
            {"overall": "KILLED", "reason": "",
             "attacks": {"physics": "KILLED: violates conservation",
                         "safety": "KILLED: uncontrolled failure"}})
        assert res["final_status"] == "REJECTED"
        # the reason carries the kill dimensions — never an empty
        # trailing colon (v1 rendered "adversarial challenge failed: ")
        assert res["reason"].rstrip().endswith((")", "e", "s"))
        assert not res["reason"].rstrip().endswith(":")
        assert res["reason"].count(":") >= 2
        assert "physics" in res["reason"] and "safety" in res["reason"]

    def test_prior_art_kill_cannot_kill_on_non_kill_state(self):
        from discovery_fabric.a2.classify import classify
        # the v1 protection must survive the v2 reason rewrite
        res = classify(
            {"falsification_test": "x" * 20},
            {"verified": True},
            {"prior_art_status": "TOPICAL_RELATED"},
            {"overall": "KILLED", "reason": "",
             "attacks": {"prior_art": "KILLED: found prior art"}})
        assert res["final_status"] == "AUTOMATED_INVENTION_CANDIDATE"


# ---------------------------------------------------------------------------
# 8. Stage graph resolution — audit NF-1 + CB-9
# ---------------------------------------------------------------------------
class TestStageGraphResolves:
    def test_every_depends_on_resolves_to_a_stage(self):
        from discovery_fabric.engine.adapters import ADAPTERS, STAGE_ORDER
        unresolved = {}
        for stage, adapter in ADAPTERS.items():
            for dep in adapter.depends_on:
                if dep not in STAGE_ORDER:
                    unresolved.setdefault(stage, []).append(dep)
        assert not unresolved, (
            f"depends_on entries outside the STAGE_ORDER namespace "
            f"(audit NF-1): {unresolved}")

    def test_adapters_keys_equal_stage_order(self):
        from discovery_fabric.engine.adapters import ADAPTERS, STAGE_ORDER
        assert set(ADAPTERS) == set(STAGE_ORDER), (
            "registered-but-unreachable or unreachable-but-registered "
            "stages (audit CB-9)")
        # R481: 17 stages (IMPROVE joined; documented change)
        assert len(ADAPTERS) == len(STAGE_ORDER) == 17

    def test_dependencies_are_acyclic_and_ordered(self):
        from discovery_fabric.engine.adapters import ADAPTERS, STAGE_ORDER
        pos = {s: i for i, s in enumerate(STAGE_ORDER)}
        for stage, adapter in ADAPTERS.items():
            for dep in adapter.depends_on:
                assert pos[dep] < pos[stage], (
                    f"{stage} depends on {dep} which appears LATER in "
                    f"STAGE_ORDER — the declared graph contradicts the "
                    f"execution order")


# ---------------------------------------------------------------------------
# 9. Cemetery universality + consumption (Art. LI) — audit CB-5
# ---------------------------------------------------------------------------
NEW_DOMAIN_INVARIANT = {
    "entry_id": "CE-TEST-900",
    "territory_id": "TEST-T99",
    "mechanism_name": "Piezoelectric energy harvesting from bridge "
                      "bearing vibration",
    "proposed_version": "T1",
    "killed_at_version": "T2",
    "kill_reason": "PHYSICS_CEILING",
    "what_was_proposed": "Harvest microwatt power from bearing "
                         "vibration via piezoelectric stack.",
    "why_it_failed": "Measured vibration energy density is below the "
                     "piezoelectric conversion threshold by 4 orders "
                     "of magnitude.",
    "reusable_lesson": "Piezoelectric harvesting cannot power active "
                       "sensing where vibration amplitude is below "
                       "1 micron RMS.",
    "what_to_avoid": "Do not propose piezoelectric harvesting below "
                     "1 micron RMS vibration amplitude.",
    "physical_constraint": "Vibration energy density below 1 micron RMS "
                           "amplitude cannot power piezoelectric "
                           "harvesting of usable sensor power.",
    "evidence_sources": [],
    "epistemic_class": "PROVEN_INVARIANT",
}


class TestCemeteryUniversality:
    def _seed(self, tmp_path, monkeypatch, entries):
        import orchestrator.mechanism_cemetery as mc
        p = tmp_path / "CEMETERY_TEST.json"
        p.write_text(__import__("json").dumps(
            {"description": "test", "entries": entries}))
        monkeypatch.setattr(mc, "CEMETERY_PATH", p)
        return mc

    def test_new_domain_invariant_blocks(self, tmp_path, monkeypatch):
        # the audit's CB-5 core: a PROVEN_INVARIANT written in NEW
        # domain vocabulary (no csf/jacobian/stiffness terms) must be
        # ABLE to hard-block a matching candidate
        mc = self._seed(tmp_path, monkeypatch, [NEW_DOMAIN_INVARIANT])
        res = mc.check_candidate_against_cemetery(
            "Piezoelectric stack harvesting sensor power from bridge "
            "bearing vibration below 1 micron RMS amplitude")
        assert res["verdict"] == "BLOCKED"
        assert res["hard_blocks"][0]["cemetery_entry"] == "CE-TEST-900"
        assert res["hard_blocks"][0]["domain_match"] >= 2

    def test_non_matching_candidate_proceeds(self, tmp_path, monkeypatch):
        mc = self._seed(tmp_path, monkeypatch, [NEW_DOMAIN_INVARIANT])
        res = mc.check_candidate_against_cemetery(
            "Heparin bonding of a catheter luminal surface to reduce "
            "thrombus formation under low flow")
        assert res["verdict"] == "PROCEED"
        assert not res["hard_blocks"]

    def test_entry_domain_terms_universal(self):
        from orchestrator.mechanism_cemetery import (
            CemeteryEntry, entry_domain_terms)
        entry = CemeteryEntry(**NEW_DOMAIN_INVARIANT)
        terms = entry_domain_terms(entry)
        assert terms, "new-domain invariant carries no domain terms"
        assert any("piezoelectric" == t or "vibration" == t
                   for t in terms)


class TestMechanismSpaceConsumesCemetery:
    def test_blocked_candidates_are_killed_with_entry_ids(
            self, tmp_path, monkeypatch):
        import json as _json
        import orchestrator.mechanism_cemetery as mc
        p = tmp_path / "CEMETERY_TEST.json"
        p.write_text(_json.dumps(
            {"description": "test", "entries": [NEW_DOMAIN_INVARIANT]}))
        monkeypatch.setattr(mc, "CEMETERY_PATH", p)
        from discovery_fabric.engine.mechanism_space import \
            _consult_cemetery
        blocked = _cand(
            graph_terms={
                "intervention_site": {"piezoelectric", "stack",
                                      "bridge", "bearing"},
                "causal_agent": {"piezoelectric", "harvesting",
                                 "conversion", "vibration"},
                "physical_effect": {"sensor", "power", "microwatt"},
            },
            intervention="piezoelectric stack harvesting from bridge "
                         "bearing vibration",
            knob="stack thickness",
            boundary="vibration amplitude below 1 micron RMS",
            failures="fatigue",
            effect="microwatt sensor power")
        clean = _cand(**BASE)
        record = _consult_cemetery([clean, blocked])
        # Art. LI: the killed invariant CHANGED future search
        assert record["state"] == "CONSULTED"
        assert record["n_blocked"] == 1
        assert record["blocked"][0]["entries"] == ["CE-TEST-900"]
        assert blocked["candidate_state"] == \
            "NOT_A_CANDIDATE_CEMETERY_PROVEN_INVARIANT"
        assert blocked["cemetery_block"][0]["cemetery_entry"] == \
            "CE-TEST-900"
        assert clean["candidate_state"] == "CANDIDATE"

    def test_unavailable_cemetery_is_honest_state(self, monkeypatch):
        import builtins
        real_import = builtins.__import__

        def _broken(name, *a, **k):
            if "mechanism_cemetery" in name:
                raise ImportError("simulated: orchestrator layer absent")
            return real_import(name, *a, **k)
        monkeypatch.setattr(builtins, "__import__", _broken)
        from discovery_fabric.engine.mechanism_space import \
            _consult_cemetery
        record = _consult_cemetery([_cand(**BASE)])
        assert record["state"] == "CEMETERY_CONSULTATION_UNAVAILABLE"
        # infrastructure failure is NEVER a block (Art. XXV)
        assert record["n_blocked"] == 0


# ---------------------------------------------------------------------------
# 10. TLS verification default (audit CB-10)
# ---------------------------------------------------------------------------
class TestTLSVerification:
    def test_default_is_verify_on(self, monkeypatch):
        monkeypatch.delenv("ENGINE_TLS_VERIFY", raising=False)
        import importlib
        import discovery_fabric.a2.retrieve as retrieve_mod
        importlib.reload(retrieve_mod)
        assert retrieve_mod._TLS_VERIFY_ENABLED is True
        assert retrieve_mod._SSL.check_hostname is True
        assert retrieve_mod._SSL.verify_mode != 0  # CERT_NONE == 0

    def test_explicit_opt_out_is_recorded(self, monkeypatch):
        monkeypatch.setenv("ENGINE_TLS_VERIFY", "0")
        import importlib
        import discovery_fabric.a2.retrieve as retrieve_mod
        importlib.reload(retrieve_mod)
        assert retrieve_mod._TLS_VERIFY_ENABLED is False
        monkeypatch.delenv("ENGINE_TLS_VERIFY", raising=False)
        importlib.reload(retrieve_mod)


# ---------------------------------------------------------------------------
# 11. Operator item cap recorded (audit CB-12)
# ---------------------------------------------------------------------------
class TestOperatorCapRecorded:
    def test_space_records_the_cap_and_its_source(self, monkeypatch):
        monkeypatch.setenv("R401_NO_EXPANSION", "1")
        monkeypatch.setenv("R401_OPERATOR_ITEM_CAP", "3")
        from tests.test_r401_mechanism_space import (
            MEDICAL_RECORD, MEDICAL_EXTRACTION, GOOD_CANDIDATE_RESPONSE,
            PROBLEM, _fake_llm)
        monkeypatch.setattr(ms, "llm_generate",
                            _fake_llm([MEDICAL_EXTRACTION,
                                       GOOD_CANDIDATE_RESPONSE]))
        space = ms.build_mechanism_space(
            PROBLEM, [MEDICAL_RECORD], top_k=1, min_candidates=1)
        # the number that produced any distinctness result is recorded
        # with its source — no unrecorded environment knob (CB-12)
        assert space["per_operator_item_cap"] == 3
        assert space["item_cap_source"] == "env R401_OPERATOR_ITEM_CAP"
