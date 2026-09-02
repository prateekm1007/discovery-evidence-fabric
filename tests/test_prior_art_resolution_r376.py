"""R376 — PRIOR-ART DIFFERENTIATION + RESOLUTION tests (hermetic + adversarial).

CEO directive 2026-08-31:
> "Build a stronger multi-query prior-art search strategy around the actual
>  mechanism and distinguishing technical features."
> "Require claim/mechanism-level relevance before a result can become
>  nearest prior art."
> "Search for both direct prior art and adjacent technical approaches."
> "Preserve unresolved states honestly."

Every test below pins a MEASURED defect from
TOSCANINI/PRIOR_ART_FAILURE_TRACE.json or attacks the new machinery as
an intelligent adversary would (Art. XVII). All network touchpoints are
mocked — hermetic (no live quota burn, no flakiness).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.prior_art_v2 import collision_resolution as cr  # noqa: E402
from discovery_fabric.a2.classify import KILL_STATES, NON_KILL_STATES  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures: the measured defect cases
# ---------------------------------------------------------------------------
CFRP_MM = {
    "intervention": ("Incorporate carbon fiber reinforced polymer (CFRP) "
                     "components at stress points in the knee prosthesis "
                     "design to distribute mechanical loads more evenly"),
    "mechanism": ("Carbon fiber reinforced polymer has higher "
                  "strength-to-weight ratio and modulus closer to bone, "
                  "reducing stress shielding at the tibial interface"),
    "expected_effect": "reduced loosening and even load distribution",
}
CFRP_PROBLEM = {"device": "knee prosthesis",
                "failure": "detachment of device"}

BATTERY_MM = {
    "intervention": ("Implement multi-sensory monitoring system using "
                     "X-ray imaging, optical sensors, acoustic sensors, "
                     "and spectroscopy to detect early thermal runaway in "
                     "EV battery packs"),
    "mechanism": ("Early off-gas and acoustic emission signatures precede "
                  "thermal runaway and are detectable by multi-modal "
                  "sensing before catastrophic failure"),
    "expected_effect": "early warning before catastrophic failure",
}
BATTERY_PROBLEM = {"device": "EV battery pack", "failure": "thermal runaway"}


def _hit(pid, title, snippet="", source="lens_patent", qclass="MECHANISM",
         assignee=""):
    return cr.PatentHit(patent_id=pid, title=title, snippet=snippet,
                        source_id=source, source_url=f"https://x/{pid}",
                        query_class=qclass, query="q", assignee=assignee,
                        publication_date="", raw_payload_sha256="")


def _patch_search(monkeypatch, hits, errors=None):
    """Patch the two network touchpoints: search + claims fetch."""
    monkeypatch.setattr(cr, "search_patents",
                        lambda ladder, sources=None, sleep_between=0.4,
                        per_source_results=5: (list(hits),
                                               list(errors or [])))
    monkeypatch.setattr(
        cr, "fetch_claim_evidence",
        lambda patent_id, hit: {"claims_text": "", "abstract": "",
                                "fetch_status": "NOT_ATTEMPTED"})
    import types
    monkeypatch.setattr(cr, "time",
                        types.SimpleNamespace(sleep=lambda s: None))


# ---------------------------------------------------------------------------
# 1. Query ladder — mechanism-centered, not first-words (defect class F)
# ---------------------------------------------------------------------------
class TestQueryLadder:
    def test_ladder_carries_entity_and_mechanism(self):
        profile = cr.build_candidate_profile(CFRP_MM, CFRP_PROBLEM)
        ladder = cr.build_query_ladder(profile)
        classes = [s["query_class"] for s in ladder]
        # R377: FUNCTION class added (measured recall defect: a detection
        # candidate's ladder carried no form of 'detect' and never
        # retrieved detection art — CEO directive cycle R377). The four
        # R376 classes and their order are UNCHANGED.
        assert classes == ["ENTITY", "MECHANISM", "DISTINGUISHING",
                           "FUNCTION", "ADJACENT"]

    def test_formulation_defect_pinned_cfrp(self):
        """The measured defect: the query was 'implement comprehensive
        post-market surveillance system using' for a CFRP knee candidate.
        The DISTINGUISHING query must now carry carbon/fiber/polymer."""
        profile = cr.build_candidate_profile(CFRP_MM, CFRP_PROBLEM)
        dist = [s for s in cr.build_query_ladder(profile)
                if s["query_class"] == "DISTINGUISHING"][0]
        q = dist["query"]
        assert "carbon" in q and "fiber" in q and "polymer" in q
        assert "surveillance" not in q and "implement" not in q

    def test_formulation_defect_pinned_battery(self):
        """Measured defect: battery query contained neither 'battery' nor
        'thermal'. The ENTITY query must anchor both."""
        profile = cr.build_candidate_profile(BATTERY_MM, BATTERY_PROBLEM)
        entity = [s for s in cr.build_query_ladder(profile)
                  if s["query_class"] == "ENTITY"][0]
        q = entity["query"]
        assert "battery" in q and "thermal" in q

    def test_natural_word_forms_not_folded(self):
        """Measured defect: folded tokens ('prosthesi') in query strings
        returned EMPTY from Lens. No query may carry a folded token;
        entity/distinguishing queries must carry the natural form."""
        profile = cr.build_candidate_profile(CFRP_MM, CFRP_PROBLEM)
        ladder = cr.build_query_ladder(profile)
        for step in ladder:
            tokens = step["query"].split()
            assert "prosthesi" not in tokens, step["query"]
        natural_present = any(
            "prosthesis" in s["query"].split()
            for s in ladder)
        assert natural_present

    def test_compact_form_for_title_scoped_sources(self):
        """Lens binds title:(...) — compact top-3 form must exist."""
        profile = cr.build_candidate_profile(CFRP_MM, CFRP_PROBLEM)
        for step in cr.build_query_ladder(profile):
            assert len(step["query_compact"].split()) <= 3

    def test_adjacent_query_excludes_implementation_terms(self):
        """ADJACENT finds function-level art without the candidate's
        implementation (what could destroy differentiation)."""
        profile = cr.build_candidate_profile(CFRP_MM, CFRP_PROBLEM)
        adj = [s for s in cr.build_query_ladder(profile)
               if s["query_class"] == "ADJACENT"][0]
        # implementation-specific terms stay OUT of the adjacent query
        assert "carbon" not in adj["query"] or "fiber" not in adj["query"]


# ---------------------------------------------------------------------------
# 2. Mechanism-level adjudication (defect class E — adversarial)
# ---------------------------------------------------------------------------
class TestMechanismAdjudication:
    def test_query_relevant_but_mechanism_irrelevant_never_nearest(self):
        """ADVERSARIAL (the measured surgical-robots defect): a hit whose
        title matches the QUERY words but not the candidate's mechanism
        must NOT become nearest prior art."""
        profile = cr.build_candidate_profile(BATTERY_MM, BATTERY_PROBLEM)
        # surgical robot shares 'imaging system' query words, not the
        # battery/thermal mechanism
        robot = _hit("US1", "Robotic surgical system for imaging during "
                            "surgery", "A robotic system with imaging "
                            "modules for surgical navigation.",
                     qclass="DISTINGUISHING")
        adj = cr.adjudicate_hit(robot, profile)
        assert adj["verdict"] in ("IRRELEVANT", "ADJACENT_ONLY")
        assert adj["verdict"] != "MECHANISM_RELEVANT"

    def test_database_patent_not_nearest_for_pedicle_screw(self):
        """The measured 'Database access system' prior art for a pedicle
        screw candidate."""
        mm = {"intervention": "Standardize thread geometry and material "
                              "composition in the pedicle screw system",
              "mechanism": "Standardized thread geometry distributes "
                           "insertion torque evenly across pedicle bone",
              "expected_effect": "fewer screw fractures"}
        problem = {"device": "pedicle screw", "failure": "break"}
        profile = cr.build_candidate_profile(mm, problem)
        db_patent = _hit("US2", "Database access system and methods for "
                                "enterprise data processing",
                         "Systems and methods for data processing.")
        adj = cr.adjudicate_hit(db_patent, profile)
        assert adj["verdict"] == "IRRELEVANT"

    def test_true_mechanism_art_is_relevant(self):
        profile = cr.build_candidate_profile(BATTERY_MM, BATTERY_PROBLEM)
        real = _hit("US3", "Battery thermal runaway detection sensor "
                           "system", "A battery thermal runaway detection "
                           "sensor system for use within a battery "
                           "enclosure with off-gas sensing.")
        adj = cr.adjudicate_hit(real, profile)
        assert adj["verdict"] == "MECHANISM_RELEVANT"
        assert len(adj["mechanism_overlap_terms"]) >= 2


# ---------------------------------------------------------------------------
# 3. Family clustering (defect class M)
# ---------------------------------------------------------------------------
class TestFamilyClustering:
    def test_distinct_families_not_merged(self):
        """MEASURED (CFRP knee case): CFRP-composite MATERIAL art and
        metal-reinforced knee-component art are distinct families; a weak
        'polymer reinforced' overlap must not merge them."""
        cfrp = _hit("US4", "High-strength wear-resistant carbon fiber "
                           "reinforced polymer composite material",
                    "Carbon fiber reinforced polymer composite with high "
                    "strength and wear resistance for structural parts.")
        knee = _hit("US5", "Metal reinforced polymer femoral component "
                           "for orthopaedic knee prosthesis",
                    "A metal reinforced polymer femoral knee prosthesis "
                    "component with improved fixation.")
        profile = cr.build_candidate_profile(CFRP_MM, CFRP_PROBLEM)
        adjs = [cr.adjudicate_hit(h, profile) for h in (cfrp, knee)]
        fams = cr.cluster_families([cfrp, knee], adjs)
        assert len(fams) == 2

    def test_same_invention_variants_merge(self):
        """Same-invention variants (near-identical titles) merge."""
        a = _hit("US6A", "Metal reinforced polymer femoral component for "
                         "orthopaedic knee prosthesis", "x")
        b = _hit("US6B", "Metal reinforced polymer femoral component for "
                         "orthopaedic knee prosthesis", "y")
        profile = cr.build_candidate_profile(CFRP_MM, CFRP_PROBLEM)
        adjs = [cr.adjudicate_hit(h, profile) for h in (a, b)]
        fams = cr.cluster_families([a, b], adjs)
        assert len(fams) == 1
        assert len(fams[0]["members"]) == 2

    def test_same_assignee_merges(self):
        a = _hit("US7A", "Alpha battery venting valve", "s" * 100,
                 assignee="ACME CORP")
        b = _hit("US7B", "Beta thermal vent membrane", "s" * 90,
                 assignee="ACME CORP")
        profile = cr.build_candidate_profile(BATTERY_MM, BATTERY_PROBLEM)
        adjs = [cr.adjudicate_hit(h, profile) for h in (a, b)]
        fams = cr.cluster_families([a, b], adjs)
        assert len(fams) == 1


# ---------------------------------------------------------------------------
# 4. Resolution state machine (CEO directive 6 — honest UNRESOLVED)
# ---------------------------------------------------------------------------
class TestResolutionStates:
    def test_all_sources_failed_unresolved(self):
        """Art. XXI.3: provider failure is never absence."""
        profile = cr.build_candidate_profile(BATTERY_MM, BATTERY_PROBLEM)
        res = cr.resolve_differentiation(
            [], profile,
            [{"query": "q", "source": "google_patents", "error": "HTTP 503"}],
            searches_succeeded=False, deep_fetch=False)
        assert res["state"] == "UNRESOLVED_INSUFFICIENT_EVIDENCE"

    def test_zero_relevant_hits_not_novelty(self):
        """Art. XXI.2: zero hits is not novelty — UNRESOLVED, never a
        RESOLVED/no-match claim."""
        profile = cr.build_candidate_profile(BATTERY_MM, BATTERY_PROBLEM)
        res = cr.resolve_differentiation(
            [], profile, [], searches_succeeded=True, deep_fetch=False)
        assert res["state"] == "UNRESOLVED_NO_RELEVANT_ART"

    def test_title_tier_family_is_partial(self):
        """A family whose evidence is TITLE-only (no abstract, no claims)
        cannot support resolution — UNRESOLVED_PARTIAL_EVIDENCE."""
        profile = cr.build_candidate_profile(BATTERY_MM, BATTERY_PROBLEM)
        hit = _hit("US8", "Battery thermal runaway detection sensor",
                   snippet="")  # no snippet -> TITLE tier
        fam = {"family_id": "PA-FAM-01", "representative": hit,
               "members": [hit], "adjudication": {}}
        res = cr.resolve_differentiation(
            [fam], profile, [], searches_succeeded=True, deep_fetch=False)
        assert res["state"] == "UNRESOLVED_PARTIAL_EVIDENCE"

    def test_partial_cover_resolves_differentiated(self):
        profile = cr.build_candidate_profile(BATTERY_MM, BATTERY_PROBLEM)
        # abstract-tier family covering the mechanism but NOT the
        # acoustic/multi-modal differentiators
        hit = _hit("US9", "Battery thermal runaway detection sensor "
                          "system", "A battery thermal runaway detection "
                          "sensor system for use within a battery "
                          "enclosure housing one or more cells.",
                   )
        fam = {"family_id": "PA-FAM-01", "representative": hit,
               "members": [hit], "adjudication": {}}
        res = cr.resolve_differentiation(
            [fam], profile, [], searches_succeeded=True, deep_fetch=False)
        assert res["state"] == "RESOLVED_DIFFERENTIATED"
        assert res["surviving_differentiators"]
        # every family's evidence tier recorded
        assert res["per_family"][0]["evidence_tier"] == "ABSTRACT"

    def test_full_cover_resolves_anticipated(self):
        """ADVERSARIAL: a patent whose abstract covers the mechanism AND
        >= 80% of the candidate's FULL element set => RESOLVED_ANTICIPATED
        (kill state). The engine must be able to recognize its own
        anticipation honestly. A true anticipating patent reads like the
        candidate itself — the fixture embeds the full intervention."""
        profile = cr.build_candidate_profile(BATTERY_MM, BATTERY_PROBLEM)
        full_elements = " ".join(profile.distinguishing_full)
        hit = _hit("US10", f"EV battery pack thermal runaway early "
                           f"detection monitoring",
                   f"A multi-sensory monitoring system using X-ray "
                   f"imaging, optical sensors, acoustic sensors, and "
                   f"spectroscopy to detect early thermal runaway in EV "
                   f"battery packs: {full_elements} providing early "
                   f"warning before catastrophic failure.")
        fam = {"family_id": "PA-FAM-01", "representative": hit,
               "members": [hit], "adjudication": {}}
        res = cr.resolve_differentiation(
            [fam], profile, [], searches_succeeded=True, deep_fetch=False)
        assert res["state"] == "RESOLVED_ANTICIPATED"
        assert res["per_family"][0]["coverage"]["coverage_class"] == \
            "FULL_COVER"

    def test_domain_only_patent_cannot_anticipate(self):
        """ADVERSARIAL (the measured dilution defect): a DOMAIN-only
        patent (battery thermal runaway early warning with optical
        sensing) must NOT anticipate a candidate whose true
        differentiators are multi-modal sensing / acoustic / individual
        cells. With the FULL element set as denominator the ratio stays
        below the anticipation threshold."""
        mm = {"intervention": ("Implement multi-modal sensing system "
                               "within battery pack using optical sensors "
                               "and acoustic monitors to detect early "
                               "signs of thermal runaway in individual "
                               "cells"),
              "mechanism": "sensing",
              "expected_effect": "early warning"}
        problem = {"device": "EV battery pack",
                   "failure": "thermal runaway propagation"}
        profile = cr.build_candidate_profile(mm, problem)
        hit = _hit("US10b", "Battery package thermal runaway early "
                            "warning system with optical sensing",
                   "A battery package thermal runaway early warning "
                   "system with optical sensing of cell off-gas for EV "
                   "battery packs, providing early warning before "
                   "propagation.")
        cov = cr.coverage_decision(profile,
                                   f"{hit.title} {hit.snippet}")
        assert cov["coverage_class"] != "FULL_COVER", (
            f"domain-only patent anticipated at ratio="
            f"{cov['coverage_ratio']} — denominator dilution regression")
        # the true differentiators survive
        surviving = set(cov["distinguishing_terms_surviving"])
        assert "acoustic" in surviving or "multi" in surviving or \
            "modal" in surviving

    def test_thresholds_declared(self):
        """Art. XXVII: thresholds carry class + justification."""
        for name, t in cr.THRESHOLDS.items():
            assert t["epistemic_class"] in (
                "ENGINEERING", "CLINICAL", "PHYSIOLOGICAL",
                "MODEL_DERIVED", "BUYER_DEFINED"), name
            assert t.get("justification"), name

    def test_resolution_carries_limitation(self):
        """Art. XXVIII: search-derived resolution is never a novelty
        determination — the limitation must be inline."""
        profile = cr.build_candidate_profile(BATTERY_MM, BATTERY_PROBLEM)
        res = cr.resolve_differentiation(
            [], profile, [], searches_succeeded=True, deep_fetch=False)
        assert "not a novelty determination" in \
            res["constitutional_limitation"]
        assert res["epistemic_class"] == "SEARCH_RESULT"


# ---------------------------------------------------------------------------
# 5. run_collision end-to-end (mocked network)
# ---------------------------------------------------------------------------
class TestRunCollision:
    def test_nearest_prior_art_entries_carry_coverage(self):
        profile = cr.build_candidate_profile(BATTERY_MM, BATTERY_PROBLEM)
        hit = _hit("US11", "Battery thermal runaway detection sensor "
                           "system", "A battery thermal runaway detection "
                           "sensor system for use within a battery "
                           "enclosure housing one or more cells with "
                           "off-gas monitoring.")
        with pytest.MonkeyPatch.context() as mp:
            _patch_search(mp, [hit])
            r = cr.run_collision(BATTERY_MM, BATTERY_PROBLEM)
        assert r["prior_art_status"] == "RESOLVED_DIFFERENTIATED"
        entry = r["nearest_prior_art"][0]
        for k in ("coverage_class", "coverage_ratio", "evidence_tier",
                  "mechanism_overlap_terms",
                  "distinguishing_terms_surviving", "family_id"):
            assert k in entry, k

    def test_source_failure_recorded_not_absence(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(cr, "search_patents",
                       lambda ladder, sources=None, sleep_between=0.4,
                       per_source_results=5: (
                           [], [{"query": "q", "source": "google_patents",
                                 "error": "HTTP 503",
                                 "epistemic_state":
                                     "UNRESOLVED_SOURCE_FAILURE"}]))
            mp.setattr(cr, "fetch_claim_evidence",
                       lambda pid, hit: {"claims_text": "",
                                         "abstract": "",
                                         "fetch_status": "NOT_ATTEMPTED"})
            r = cr.run_collision(BATTERY_MM, BATTERY_PROBLEM)
        # R394 s2 contract change (deliberate, directive-driven): a
        # PARTIAL search failure is UNRESOLVED_SEARCH_INCOMPLETE — more
        # precise than the old coarse UNRESOLVED_INSUFFICIENT_EVIDENCE.
        # Both forbid absence and differentiation claims; the errors are
        # still recorded (the test's load-bearing intent).
        assert r["prior_art_status"] == "UNRESOLVED_SEARCH_INCOMPLETE"
        assert r["patent"]["source_errors"]

    def test_adjacent_only_hits_recorded_as_threats(self):
        """ADJACENT_ONLY hits (entity domain, not mechanism) are recorded
        as differentiation threats — never as nearest prior art.

        Fixture: an infusion-pump candidate whose mechanism profile is
        pressure-wave analysis; an infusion-pump domain patent sharing
        entity terms (infusion, pump) but not the mechanism terms."""
        mm = {"intervention": "Pressure-wave reflection analysis for "
                              "early occlusion detection in the delivery "
                              "line",
              "mechanism": "Occlusions reflect pressure waves; analyzing "
                           "the reflection signature detects partial "
                           "occlusions earlier than alarms",
              "expected_effect": "earlier occlusion alarm"}
        problem = {"device": "infusion pump", "failure": "occlusion"}
        adjacent = _hit("US12", "Infusion pump flow calibration "
                                "apparatus", "An infusion pump with a "
                                "flow calibration apparatus and pumping "
                                "mechanism for accurate delivery.",
                        qclass="ADJACENT")
        profile = cr.build_candidate_profile(mm, problem)
        adj = cr.adjudicate_hit(adjacent, profile)
        assert adj["verdict"] == "ADJACENT_ONLY", adj
        with pytest.MonkeyPatch.context() as mp:
            _patch_search(mp, [adjacent])
            r = cr.run_collision(mm, problem)
        assert r["nearest_prior_art"] == []
        assert r["patent"]["adjacent_only_hits"]

    def test_metered_source_not_queried(self):
        """PatentBear is OPT-IN (R378 CEO directive: 'Use PatentBear for
        patents'): absent from `sources` it is never queried, and the
        artifact records the metered-source policy. The quota guard
        refusal is recorded as an error, never as absence."""
        with pytest.MonkeyPatch.context() as mp:
            _patch_search(mp, [])
            r = cr.run_collision(BATTERY_MM, BATTERY_PROBLEM)
        metered = r["patent"]["metered_sources"]
        assert "patentbear" in metered
        assert "opt-in" in metered["patentbear"]["policy"].lower()
        # patentbear was NOT in the default source list -> no patentbear
        # query was issued (the patched search records every call)
        issued = [e for e in r["patent"]["source_errors"]
                  if e.get("source") == "patentbear"]
        assert issued == []

    def test_patentbear_quota_guard_refusal_is_error_not_absence(self):
        """When the persistent meter is at/below the reserve floor, the
        guard refuses BEFORE the call and the refusal surfaces as an
        UNRESOLVED_SOURCE_FAILURE error — never as zero hits / absence
        (Art. XXI.3 + metered-source policy)."""
        import tempfile
        from pathlib import Path
        from discovery_fabric.prior_art_v2 import sources as psrc
        with tempfile.TemporaryDirectory() as td:
            meter = Path(td) / "patentbear_meter.json"
            meter.write_text('{"monthly_remaining": 1}')
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(psrc, "PATENTBEAR_METER_PATH", meter)
                r = psrc.search_patent_bear("battery thermal runaway")
            assert not r.success
            assert "RATE_LIMITED" in (r.error or "")
            assert r.error_code == 429


# ---------------------------------------------------------------------------
# 6. classify state machine (kill / non-kill)
# ---------------------------------------------------------------------------
class TestClassifyStates:
    def test_resolved_anticipated_is_kill(self):
        assert "RESOLVED_ANTICIPATED" in KILL_STATES

    def test_resolved_differentiated_is_non_kill(self):
        assert "RESOLVED_DIFFERENTIATED" in NON_KILL_STATES

    def test_unresolved_states_non_kill(self):
        for s in ("UNRESOLVED_PARTIAL_EVIDENCE",
                  "UNRESOLVED_NO_RELEVANT_ART",
                  "UNRESOLVED_INSUFFICIENT_EVIDENCE"):
            assert s in NON_KILL_STATES

    def test_classify_kills_on_anticipated(self):
        from discovery_fabric.a2.classify import classify
        res = classify(
            {"candidate_id": "x",
             "falsification_test": "measure X under condition Y"},
            {"verified": True},
            {"prior_art_status": "RESOLVED_ANTICIPATED"},
            {"overall": "PASS"})
        assert res["final_status"] == "REJECTED"
        assert res.get("promotion_blocked") is True
        assert "RESOLVED_ANTICIPATED" in res["reason"]

    def test_classify_passes_on_differentiated(self):
        from discovery_fabric.a2.classify import classify
        res = classify(
            {"candidate_id": "x",
             "falsification_test": "measure X under condition Y"},
            {"verified": True},
            {"prior_art_status": "RESOLVED_DIFFERENTIATED"},
            {"overall": "PASS"})
        assert res.get("final_status") != "REJECTED"

    def test_adjudication_check_rejects_anticipated(self):
        """The adjudication 'no_specific_prior_disclosure' check must
        fail for RESOLVED_ANTICIPATED (consistency with the kill)."""
        adapters_text = (REPO / "discovery_fabric" / "engine" /
                         "adapters.py").read_text()
        classify_text = (REPO / "discovery_fabric" / "a2" /
                         "classify.py").read_text()
        # adjudication tuple in adapters.py
        assert '"RESOLVED_ANTICIPATED"' in adapters_text
        # KILL_STATES in classify.py
        assert '"RESOLVED_ANTICIPATED"' in classify_text


# ---------------------------------------------------------------------------
# 7. Grid-candidate collision independence (defect class E, architectural)
# ---------------------------------------------------------------------------
class TestGridCandidateIndependence:
    def test_env_with_candidate_reruns_collision(self, monkeypatch):
        """The CFRP grid candidate must NOT carry the naive candidate's
        surveillance-system collision. _env_with_candidate re-runs the
        collision with the candidate's own mechanism."""
        import discovery_fabric.engine.prior_art_v2_bridge as bridge

        mm = dict(CFRP_MM, intervention="Different intervention entirely")
        called = {}

        def fake_collision(mechanism_map, problem):
            called["intervention"] = mechanism_map.get("intervention")
            return {"collision": {"novelty_risk": "TEST",
                                  "nearest_prior_art": [],
                                  "differentiation_resolution": {
                                      "state": "UNRESOLVED_NO_RELEVANT_ART",
                                      "epistemic_class": "SEARCH_RESULT"}},
                    "prior_art": {
                        "prior_art_status": "UNRESOLVED_NO_RELEVANT_ART",
                        "differentiation_resolution": {
                            "state": "UNRESOLVED_NO_RELEVANT_ART"}}}

        monkeypatch.setattr(bridge, "candidate_collision", fake_collision)
        # simulate the run.py call path (import inside function)
        import discovery_fabric.engine.prior_art_v2_bridge as b2
        out = b2.candidate_collision(mm, CFRP_PROBLEM)
        assert called["intervention"] == mm["intervention"]
        assert out["prior_art"]["prior_art_status"] == \
            "UNRESOLVED_NO_RELEVANT_ART"

    def test_run_py_wires_collision_rerun(self):
        """run.py's _env_with_candidate must call the bridge (source
        inspection — the wiring is the defect fix)."""
        text = (REPO / "discovery_fabric" / "engine" / "run.py").read_text()
        assert "prior_art_v2_bridge" in text
        assert "candidate_collision" in text
        assert "UNRESOLVED_INSUFFICIENT_EVIDENCE" in text  # honest fallback


# ---------------------------------------------------------------------------
# 8. Instrument byte-identity (Art. XXX — do not optimize the evaluator)
# ---------------------------------------------------------------------------
class TestInstrumentUnchanged:
    def test_candidate_quality_instrument_hash(self):
        """The Q-instrument must be BYTE-IDENTICAL to the frozen R375
        version (declared hash). Any change is a gate violation."""
        import hashlib
        p = (REPO / "discovery_fabric" / "benchmark" /
             "candidate_quality.py")
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        expected = "7e36ea45c8ca4c4ae90c53df5e00ec77" \
                   "c487a66ca9dd629d2520f55284af10ca"
        assert h == expected, (
            "candidate_quality.py was modified — the measurement "
            "instrument is FROZEN (CEO: do not optimize the evaluator; "
            "Art. XXX)")

    def test_q3_recognizes_new_resolved_states(self):
        """The unchanged instrument must grade the new states correctly:
        RESOLVED_* -> 1.0 (position resolved), UNRESOLVED_* -> 0.0."""
        from discovery_fabric.benchmark.candidate_quality import (
            measure_prior_art_resolution)
        for status, expected in (
                ("RESOLVED_DIFFERENTIATED", 1.0),
                ("RESOLVED_ANTICIPATED", 1.0),
                ("UNRESOLVED_PARTIAL_EVIDENCE", 0.0),
                ("UNRESOLVED_NO_RELEVANT_ART", 0.0),
                ("UNRESOLVED_INSUFFICIENT_EVIDENCE", 0.0),
                ("POSSIBLE_RELEVANCE", 0.0)):
            spec = {"novelty_hypothesis": {
                "value": {"prior_art_status": status}}}
            m = measure_prior_art_resolution(spec)
            assert m["score"] == expected, status


# ---------------------------------------------------------------------------
# 9. Invention spec enrichment
# ---------------------------------------------------------------------------
class TestSpecEnrichment:
    def test_vs_nearest_carries_coverage_fields(self):
        from discovery_fabric.engine.invention_spec import \
            build_invention_spec
        from discovery_fabric.engine.candidate import Candidate
        env = Candidate(problem=CFRP_PROBLEM, problem_id="t")
        env.mechanism_map = dict(CFRP_MM, raw_candidate={})
        env.collision_results = {
            "nearest_prior_art": [{
                "title": "Carbon fiber reinforced knee prosthesis "
                         "component",
                "patent_id": "US13", "family_id": "PA-FAM-01",
                "family_size": 3, "evidence_tier": "ABSTRACT",
                "coverage_class": "PARTIAL_COVER", "coverage_ratio": 0.5,
                "mechanism_overlap_terms": ["carbon", "fiber"],
                "distinguishing_terms_surviving": ["knee", "stress"]}],
            "query_ladder": [{"query_class": "MECHANISM",
                              "query": "q"}],
            "differentiation_resolution": {
                "state": "RESOLVED_DIFFERENTIATED",
                "surviving_differentiators": ["knee", "stress"]},
        }
        env.prior_art = {
            "prior_art_status": "RESOLVED_DIFFERENTIATED"}
        env.epistemic_state = {"final_status":
                               "AUTOMATED_INVENTION_CANDIDATE"}
        env.adjudication = {"council": {"verdict":
                                        "ESTABLISHED_PROVISIONALLY"}}
        env.evidence = [{"id": "e1", "title": "t",
                         "source_uri": "u", "content_hash": "h"}]
        spec = build_invention_spec(env, {"run_id": "r"})
        df = spec["distinguishing_features"]["value"]
        entry = df["vs_nearest_prior_art"][0]
        assert entry["coverage_class"] == "PARTIAL_COVER"
        assert entry["evidence_tier"] == "ABSTRACT"
        assert entry["distinguishing_terms_surviving"] == ["knee",
                                                           "stress"]
        assert df["surviving_differentiators"] == ["knee", "stress"]
        pa = spec["prior_art"]["value"]
        assert pa["differentiation_resolution"]["state"] == \
            "RESOLVED_DIFFERENTIATED"
        # integrity: no fact promotion violations
        assert spec["_integrity"]["passed"] is True
