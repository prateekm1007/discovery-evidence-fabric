"""CEO 2026-08-31 relevance-failure directive — regression tests for the
doe_osti 0.175 root-cause fixes and the source-routing grammar gate.

Every test here pins a MEASURED defect from the investigation
(scripts/osti_relevance_failure_investigation.py):

  D1 question-form queries  -> keyword_form / _is_question_form
  D2 abstract drop          -> OSTI description retention + adjudicator sees it
  D3 XML/JSON format flip   -> dual-shape parse_payload
  D4 trailing '?'           -> build_url strips it
  R1 grammar routing        -> base grammar gate refuses before HTTP

Hermetic: no network. HTTP-level behavior is pinned by stubbing _request.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.source_registry.base import (
    STATUS_GRAMMAR_MISMATCH,
    STATUS_OK,
    STATUS_PARSE_FAILED,
)
from discovery_fabric.source_registry.connectors.failure_universe import (
    NhtsaComplaintConnector,
)
from discovery_fabric.source_registry.connectors.govtech_reports import (
    DoeOstiConnector,
)
from discovery_fabric.source_registry import query_relevance as qr
from toscanini import problem_builder as pb


# ---------------------------------------------------------------------------
# D3: dual-format parsing (measured flip: same query -> XML or JSON)
# ---------------------------------------------------------------------------

OSTI_JSON = [{
    "osti_id": "3369038",
    "title": "Hydrogen Embrittlement of Railroad Steels",
    "description": "Study of hydrogen embrittlement mechanisms in steels "
                   "under rail vibration loading.",
    "publication_date": "2026-01-01T00:00:00Z",
    "product_type": "Technical Report",
    "doi": "10.2172/3369038",
    "authors": ["Ronevich, J."],
    "research_orgs": ["Sandia National Laboratories"],
    "subjects": ["hydrogen embrittlement"],
}]

OSTI_XML = (
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\r\n<records>\r\n<record>\r\n"
    "  <osti_id>3369038</osti_id>\r\n"
    "  <title>Hydrogen Embrittlement of Railroad Steels</title>\r\n"
    "  <description>Study of hydrogen embrittlement mechanisms in steels "
    "under rail vibration loading.</description>\r\n"
    "  <authors>\r\n      <author>Ronevich, J. [SNL]</author>"
    "<author>Ehrhart, B. [SNL]</author>\r\n  </authors>\r\n"
    "  <product_type>Technical Report</product_type>\r\n"
    "  <doi>10.2172/3369038</doi>\r\n"
    "  <subjects>\r\n      <subject>hydrogen embrittlement</subject>"
    "<subject>steels</subject>\r\n  </subjects>\r\n"
    "</record>\r\n</records>\r\n"
)


class TestOstiDualFormatParse:
    def test_json_array_parses(self):
        payload = DoeOstiConnector().parse_payload(
            json.dumps(OSTI_JSON).encode(), "hydrogen embrittlement steel")
        recs = payload["records"]
        assert len(recs) == 1 and recs[0]["osti_id"] == "3369038"

    def test_xml_parses_to_same_shape(self):
        """THE measured flip defect: XML answers were PARSE_FAILED before."""
        payload = DoeOstiConnector().parse_payload(
            OSTI_XML.encode(), "hydrogen embrittlement steel")
        recs = payload["records"]
        assert len(recs) == 1
        r = recs[0]
        assert r["osti_id"] == "3369038"
        assert r["title"] == "Hydrogen Embrittlement of Railroad Steels"
        assert "hydrogen embrittlement mechanisms" in r["description"]
        assert r["authors"] == ["Ronevich, J. [SNL]", "Ehrhart, B. [SNL]"]
        assert r["subjects"] == ["hydrogen embrittlement", "steels"]

    def test_garbage_fails_closed(self):
        with pytest.raises(ValueError):
            DoeOstiConnector().parse_payload(b"<html>error page</html>", "q")
        with pytest.raises(ValueError):
            DoeOstiConnector().parse_payload(b"not json", "q")

    def test_xml_normalize_keeps_description(self):
        """D2: the abstract reaches normalized.description (was DROPPED)."""
        conn = DoeOstiConnector()
        payload = conn.parse_payload(OSTI_XML.encode(), "hydrogen embrittlement")
        recs = conn.normalize_payload(payload, "hydrogen embrittlement", "sha")
        assert len(recs) == 1
        assert recs[0].normalized["description"].startswith(
            "Study of hydrogen embrittlement")
        assert recs[0].normalized["subjects"] == [
            "hydrogen embrittlement", "steels"]

    def test_json_normalize_keeps_description(self):
        conn = DoeOstiConnector()
        payload = conn.parse_payload(
            json.dumps(OSTI_JSON).encode(), "hydrogen embrittlement")
        recs = conn.normalize_payload(payload, "hydrogen embrittlement", "sha")
        assert "hydrogen embrittlement mechanisms" in \
            recs[0].normalized["description"]

    def test_search_accepts_xml_response(self):
        """End-to-end through _execute with a stubbed XML HTTP answer."""
        conn = DoeOstiConnector()

        def fake_request(url, timeout=25):
            return OSTI_XML.encode(), STATUS_OK, 200, None, None
        conn._request = fake_request  # noqa: SLF001 — stub under test
        res = conn.search("hydrogen embrittlement steel")
        assert res.status == STATUS_OK
        assert len(res.records) == 1
        assert res.records[0].normalized["description"]


# ---------------------------------------------------------------------------
# D2: the adjudicator actually sees the OSTI abstract + subjects
# ---------------------------------------------------------------------------

class TestAdjudicatorSeesAbstract:
    def _record(self, title, description=None, subjects=None):
        norm = {}
        if description:
            norm["description"] = description
        if subjects:
            norm["subjects"] = subjects
        return {"record_id": "osti:1", "title": title, "normalized": norm}

    def test_abstract_only_match_adjudicates_relevant(self):
        """Title says nothing; the abstract carries the query concepts.
        Before the fix this record was IRRELEVANT (title-only text)."""
        rec = self._record(
            "Vibration and Shock Loading Assessment",
            description="Rail steels under hydrogen embrittlement "
                        "conditions were assessed for fatigue life.")
        a = qr.adjudicate_record(rec, "hydrogen embrittlement steel")
        assert a["relevance"] == qr.RELEVANT

    def test_subjects_only_match_adjudicates_relevant(self):
        rec = self._record(
            "Fusion Materials Semiannual Report",
            subjects=["hydrogen embrittlement", "structural steels"])
        a = qr.adjudicate_record(rec, "hydrogen embrittlement")
        assert a["relevance"] == qr.RELEVANT

    def test_offdomain_record_still_filtered(self):
        """Fail-closed direction: abstract present but off-topic stays
        IRRELEVANT — the fix must not admit garbage (Art. V)."""
        rec = self._record(
            "Williston Basin Resource Study",
            description="Commercial-scale subsurface hydrogen storage "
                        "economics and risk assessment.")
        a = qr.adjudicate_record(rec, "hydrogen embrittlement steel")
        assert a["relevance"] == qr.IRRELEVANT

    def test_threshold_rule_unchanged(self):
        """Art. VII guard: MIN_OVERLAP_TERMS is still 2 and the required
        rule is still min(2, n_query_terms)."""
        assert qr.MIN_OVERLAP_TERMS == 2


# ---------------------------------------------------------------------------
# D4: trailing '?' stripped from OSTI URLs
# ---------------------------------------------------------------------------

class TestTrailingPunctuation:
    def test_question_mark_stripped(self):
        url = DoeOstiConnector().build_url(
            "Why do wind turbine gearbox bearings develop micropitting?")
        # the ONLY '?' in the URL is the query-string separator; the
        # encoded query payload carries no %3F
        assert url.count("?") == 1
        assert "%3F" not in url
        assert url.endswith("micropitting&rows=10")

    def test_clean_query_unchanged(self):
        url = DoeOstiConnector().build_url("lithium battery safety")
        assert "lithium%20battery%20safety" in url


# ---------------------------------------------------------------------------
# D1: keyword-form query discipline
# ---------------------------------------------------------------------------

class TestKeywordForm:
    def test_question_prefix_stripped(self):
        assert pb.keyword_form(
            "How can hydrogen embrittlement be prevented in high-strength "
            "steels?") == "hydrogen embrittlement prevented high-strength steels"

    def test_why_question_normalized(self):
        out = pb.keyword_form(
            "Why do lithium-ion battery packs in electric vehicles develop "
            "thermal runaway during fast charging?")
        # interrogative + filler dropped; content terms kept in order,
        # capped at 10 (fast charging -> 'charging' is term #11, dropped)
        assert out == ("lithium-ion battery packs electric vehicles "
                       "develop thermal runaway during fast")

    def test_cap_is_configurable(self):
        out = pb.keyword_form(
            "Why do lithium-ion battery packs in electric vehicles develop "
            "thermal runaway during fast charging?", max_terms=12)
        assert out.endswith("fast charging")

    def test_keyword_query_untouched(self):
        assert pb.keyword_form("lithium battery safety") == \
            "lithium battery safety"

    def test_filler_only_collapses_to_empty(self):
        assert pb.keyword_form("what is the") == ""

    def test_max_terms_cap(self):
        out = pb.keyword_form("a b c d e f g h i j k l m n o p")
        assert len(out.split()) == 10

    def test_is_question_form(self):
        assert pb._is_question_form(
            "How can hydrogen embrittlement be prevented in high-strength "
            "steels?")
        assert pb._is_question_form(
            "Why do lithium-ion battery packs in electric vehicles develop "
            "thermal runaway")
        assert not pb._is_question_form("lithium battery safety")
        assert not pb._is_question_form("wind turbine gearbox failure")
        assert not pb._is_question_form("How")  # single word: not a sentence


# ---------------------------------------------------------------------------
# R1: grammar gate — sources refuse questions they cannot answer
# ---------------------------------------------------------------------------

class TestGrammarGate:
    def test_nhtsa_refuses_free_text_before_http(self):
        """Measured defect: 'wind turbine gearbox micropitting failure' ->
        HTTP 500 UNAVAILABLE. Must now be GRAMMAR_MISMATCH with NO request."""
        conn = NhtsaComplaintConnector()
        sent = []

        def spy_request(url, timeout=25):
            sent.append(url)
            return b"", "UNAVAILABLE", 500, "HTTP 500", None
        conn._request = spy_request  # noqa: SLF001 — spy under test
        res = conn.search("wind turbine gearbox micropitting failure")
        assert res.status == STATUS_GRAMMAR_MISMATCH
        assert res.ok is False
        assert sent == []  # NO HTTP request burned
        assert "make|model|year" in (res.error or "")

    def test_nhtsa_accepts_vehicle_grammar(self):
        conn = NhtsaComplaintConnector()
        fixture = json.dumps({
            "count": 1, "message": "ok",
            "results": [{"odiNumber": 1, "summary": "Brake failure",
                         "manufacturer": "Toyota",
                         "components": "SERVICE BRAKES",
                         "dateComplaintFiled": "2020-01-01"}],
        }).encode()

        def fake_request(url, timeout=25):
            return fixture, STATUS_OK, 200, None, None
        conn._request = fake_request  # noqa: SLF001 — stub under test
        res = conn.search("toyota|camry|2020")
        assert res.status == STATUS_OK
        assert len(res.records) == 1

    def test_grammar_mismatch_is_not_provider_failure(self):
        """Art. XXV: the error text must say routing error, not absence."""
        conn = NhtsaComplaintConnector()
        conn._request = lambda url, timeout=25: (b"", "OK", 200, None, None)
        res = conn.search("some free text query")
        assert "not a provider failure" in (res.error or "")
        assert "not absence" in (res.error or "")


class TestProblemBuilderRouting:
    """Automotive family without an extracted vehicle -> NOT_QUERIED_GRAMMAR."""

    @staticmethod
    def _build(monkeypatch, extraction):
        monkeypatch.setattr(pb, "extract_problem_fields",
                            lambda text: dict(extraction))
        return pb.build_problem("Why do lithium-ion battery packs fail?")

    def test_automotive_without_vehicle_skips_nhtsa(self, monkeypatch):
        out = self._build(monkeypatch, {
            "domain": "automotive", "device": "lithium-ion battery pack",
            "failure_mode": "thermal runaway", "constraint": "must not ignite",
            "failure_query": "lithium battery thermal runaway",
            "science_query": "lithium battery thermal runaway vehicle",
            "_llm": {"status": "OK", "provider": "test",
                     "latency_ms": 1},
        })
        statuses = {r["source"]: r["status"] for r in out["evidence_pack"]["retrieval"]}
        assert statuses["nhtsa_complaints"] == "NOT_QUERIED_GRAMMAR"
        assert statuses["nhtsa_recalls"] == "NOT_QUERIED_GRAMMAR"
        notes = out["evidence_pack"]["extraction"]["routing_notes"]
        assert any("nhtsa_complaints" in n for n in notes)
        assert "ROUTING:" in out["problem"]["failure"]

    def test_vehicle_reaches_nhtsa_as_query(self, monkeypatch):
        """With a vehicle extracted, the vehicle IS the NHTSA query."""
        captured = {}
        real_search_one = pb._search_one

        def spy_search_one(name, role, cls, query, timeout=40,
                           run_id="toscanini:ui"):
            captured[name] = query
            return {"source": name, "role": role, "status": "CALL_FAILED",
                    "count": 0, "records": [], "relevant": 0, "error": "stub"}
        monkeypatch.setattr(pb, "extract_problem_fields", lambda text: {
            "domain": "automotive", "device": "battery pack",
            "failure_mode": "thermal runaway", "constraint": "x",
            "failure_query": "lithium battery thermal runaway",
            "science_query": "lithium battery thermal runaway",
            "vehicle": "tesla|model 3|2021",
            "_llm": {"status": "OK", "provider": "test", "latency_ms": 1},
        })
        monkeypatch.setattr(pb, "_search_one", spy_search_one)
        pb.build_problem("EV battery fires")
        assert captured.get("nhtsa_complaints") == "tesla|model 3|2021"
        assert captured.get("nhtsa_recalls") == "tesla|model 3|2021"

    def test_malformed_vehicle_dropped(self, monkeypatch):
        out = self._build(monkeypatch, {
            "domain": "automotive", "device": "car", "failure_mode": "fire",
            "constraint": "x",
            "failure_query": "vehicle fire",
            "science_query": "vehicle fire",
            "vehicle": "my neighbors car",
            "_llm": {"status": "OK", "provider": "test", "latency_ms": 1},
        })
        statuses = {r["source"]: r["status"] for r in out["evidence_pack"]["retrieval"]}
        assert statuses["nhtsa_complaints"] == "NOT_QUERIED_GRAMMAR"


class TestOstiQuestionQueryEndToEnd:
    """The measured UI failure replayed hermetically: a question-form query
    through the FIXED connector round-trip (stubbed HTTP)."""

    def test_question_mark_never_reaches_the_url(self, monkeypatch):
        conn = DoeOstiConnector()
        seen_urls = []

        def fake_request(url, timeout=25):
            seen_urls.append(url)
            return OSTI_XML.encode(), STATUS_OK, 200, None, None
        conn._request = fake_request  # noqa: SLF001 — spy under test
        res = conn.search(
            "Why do wind turbine gearbox bearings develop micropitting?")
        assert res.status == STATUS_OK
        assert all("%3F" not in u for u in seen_urls)
        assert len(seen_urls) == 1


# ---------------------------------------------------------------------------
# Collision-stage query pollution + prior-art relevance filter
# (measured: 'implement multi-sensory monitoring system using x-ray' ->
#  surgical robots as nearest prior art for a battery candidate)
# ---------------------------------------------------------------------------

MEASURED_INTERVENTION = (
    "Implement multi-modal sensing system within battery pack using "
    "optical sensors and acoustic monitors to detect early signs of "
    "thermal runaway in individual cells")


class TestCollisionQueryForm:
    def test_measured_defect_query_now_content_bearing(self):
        """The exact intervention from the t6_energy run: the old first-6
        words produced 'implement multi-sensory monitoring system using
        x-ray'. keyword_form keeps content terms only."""
        from discovery_fabric.source_registry.query_relevance import (
            keyword_form)
        q = keyword_form(MEASURED_INTERVENTION, max_terms=6)
        words = q.split()
        assert words[:2] == ["multi-modal", "sensing"]
        for filler in ("implement", "system", "using", "within", "the"):
            assert filler not in words
        assert "battery" in words  # the DOMAIN term survives


class TestCollisionPriorArtFilter:
    """End-to-end through CollisionEngineAdapter.execute with stubbed
    patent search + prior-art modules."""

    @pytest.fixture()
    def collision_result(self, monkeypatch):
        import types
        adapter_mod = pytest.importorskip(
            "discovery_fabric.engine.adapters")
        # stub a2.prior_art.search_prior_art
        pa = types.ModuleType("discovery_fabric.a2.prior_art")
        pa.search_prior_art = lambda text, device: {
            "prior_art_status": "NO_MATCHING_EVIDENCE_FOUND",
            "result_count": 0, "results": [], "queries": ["q"],
            "limitations": [],
        }
        # stub prior_art_v2.sources.search_google_patents: return the
        # MEASURED junk hits + one genuine adjacent-art hit (as dataclass
        # instances — the adapter calls asdict() on each hit)
        src = types.ModuleType("discovery_fabric.prior_art_v2.sources")
        import dataclasses

        @dataclasses.dataclass
        class _Hit:
            title: str
            patent_id: str
            source_url: str

        _HITS = [
            _Hit("Portable radiographic imaging apparatus and system",
                 "US9492137B2", "u1"),
            _Hit("Robotic surgical system for insertion of surgical "
                 "implants", "US20230181258A1", "u2"),
            _Hit("Battery package thermal runaway early warning system "
                 "with optical sensing", "CN212313296U", "u3"),
        ]

        class _SQR:
            success = True
            error = None
            hits = _HITS
        src.search_google_patents = lambda q, num_results=5: _SQR()
        import sys
        monkeypatch.setitem(sys.modules, "discovery_fabric.a2.prior_art", pa)
        monkeypatch.setitem(
            sys.modules, "discovery_fabric.prior_art_v2.sources", src)

        from discovery_fabric.engine.candidate import Candidate
        env = Candidate(
            problem={"device": "EV battery pack",
                     "failure": "thermal runaway propagation",
                     "failure_mode": "thermal runaway",
                     "constraint": "c"},
            problem_id="p_test",
            mechanism_map={"intervention": MEASURED_INTERVENTION,
                           "mechanism": "sensing"})
        adapter = None
        for cls in vars(adapter_mod).values():
            if isinstance(cls, type) and getattr(
                    cls, "capability_id", "") == "COLLISION_ENGINE":
                adapter = cls
                break
        assert adapter is not None, "CollisionEngineAdapter not found"
        result = adapter().execute(env, {})
        return result

    def test_offdomain_patents_excluded_from_nearest(self,
                                                     collision_result):
        collision = collision_result["apply_to"]["collision_results"]
        titles = [p["title"] for p in collision["nearest_prior_art"]]
        assert not any("surgical" in t.lower() for t in titles)
        assert not any("radiographic" in t.lower() for t in titles)
        # the genuine adjacent-art hit IS kept
        assert any("Battery package thermal runaway" in t for t in titles)

    def test_offdomain_hits_stay_recorded_with_verdicts(self,
                                                        collision_result):
        """Art. XV: junk hits are disclosed with adjudications, not
        silently dropped. (Two queries run — base + expansion — so each
        hit is adjudicated once per query.)"""
        collision = collision_result["apply_to"]["collision_results"]
        adjudications = collision["patent"]["relevance_adjudications"]
        assert len(adjudications) == 6  # 2 queries x 3 hits, all adjudicated
        by_record = {}
        for a in adjudications:
            by_record.setdefault(a["record_id"], set()).add(a["relevance"])
        assert by_record["US20230181258A1"] == {"IRRELEVANT_FILTERED"}
        assert by_record["US9492137B2"] == {"IRRELEVANT_FILTERED"}
        assert by_record["CN212313296U"] == {"RELEVANT"}
        assert collision["patent"]["hit_count"] == 6
        assert collision["patent"]["relevant_hit_count"] >= 1

    def test_patent_query_is_keyword_form(self, collision_result):
        collision = collision_result["apply_to"]["collision_results"]
        queries = collision["patent"]["queries"]
        assert queries, "patent queries recorded"
        first = queries[0]
        for filler in ("implement", "system", "using", "within"):
            assert not first.startswith(filler)
        assert "battery" in first or "sensing" in first

    def test_novelty_risk_recomputes_on_filtered_pool(self,
                                                      collision_result):
        collision = collision_result["apply_to"]["collision_results"]
        # one relevant hit that overlaps base terms -> ADJACENT candidates
        assert collision["novelty_risk"] == "ADJACENT_COLLISION_CANDIDATES"


class TestGrammarMismatchStatusModel:
    """GRAMMAR_MISMATCH must classify as an ENGINE-side defect, never as a
    provider block class (AUTH/EGRESS/...) and never as provider absence."""

    def test_block_class_is_engine_query_grammar(self):
        from discovery_fabric.source_registry.status_model import (
            classify_block)
        out = classify_block(request_status="GRAMMAR_MISMATCH",
                             error="query does not match source grammar")
        assert out["status"] == "BLOCKED"
        assert out["block_class"] == "ENGINE_QUERY_GRAMMAR"
        assert "engine-side" in out["block_evidence"]["fired_rule"] or \
            "engine" in out["block_evidence"]["fired_rule"].lower()

    def test_signature_rules_do_not_override_grammar(self):
        """The grammar fast-path fires BEFORE signature scanning — a
        grammar-mismatch error mentioning 'api key' must NOT classify as
        AUTH."""
        from discovery_fabric.source_registry.status_model import (
            classify_block)
        out = classify_block(
            request_status="GRAMMAR_MISMATCH",
            error="api key not configured for this grammar question")
        assert out["block_class"] == "ENGINE_QUERY_GRAMMAR"

    def test_health_check_routes_grammar_mismatch(self):
        from discovery_fabric.source_registry.status_model import (
            classify_block)
        out = classify_block(request_status="GRAMMAR_MISMATCH")
        assert out["block_class"] in \
            ("ENGINE_QUERY_GRAMMAR",)  # vocabulary pinned


class TestInventionQualityInstrument:

    def _spec(self, *, evidence_ids=None, pa_titles=None,
              pa_status="UNRESOLVED_INSUFFICIENT_EVIDENCE",
              intervention="optical battery sensing"):
        from discovery_fabric.benchmark import candidate_quality as cq
        ev = evidence_ids if evidence_ids is not None else ["ev:1"]
        return {
            "mechanism": {"value": {"mechanism": "m", "intervention":
                                    intervention},
                          "evidence_ids": ev},
            "distinguishing_features": {
                "value": {"intervention": intervention,
                          "vs_nearest_prior_art": [
                              {"title": t, "patent_id": f"P{i}"}
                              for i, t in enumerate(pa_titles or [])]},
                "evidence_ids": ev},
            "prior_art": {"value": {"status": "x"}, "evidence_ids": ev},
            "killer_experiment": {"value": {"eig": 0.5},
                                  "evidence_ids": ev},
            "novelty_hypothesis": {"value": {
                "prior_art_status": pa_status,
                "multi_source_directions": {}}},
        }

    def test_scores_spec_with_specific_prior_art(self):
        from discovery_fabric.benchmark import candidate_quality as cq
        spec = self._spec(
            pa_titles=["Battery thermal runaway optical warning system",
                       "Lithium battery sensing apparatus"],
            pa_status="RESOLVED_NOVEL")
        decisive = {"selected": {
            "experiment": "bench test", "expected_information_gain": 0.5,
            "hypotheses": [{"name": "H1", "prior_probability": 0.5,
                            "provenance": "test"}],
            "kill_probability": "UNKNOWN (no sourced base rate)"}}
        r = cq.measure_run.__wrapped__ if hasattr(
            cq.measure_run, "__wrapped__") else None
        # measure via the public path on a temp dir
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "INVENTION_SPECIFICATION.json").write_text(json.dumps(spec))
            (p / "DECISIVE_EXPERIMENT.json").write_text(json.dumps(decisive))
            out = cq.measure_run(p)
        assert out["state"] == "MEASURED"
        dims = {d["dimension"]: d["score"] for d in out["dimensions"]}
        assert dims["Q2_PRIOR_ART_SPECIFICITY"] == 1.0
        assert dims["Q3_PRIOR_ART_RESOLUTION"] == 1.0
        assert dims["Q5_CHAIN_COMPLETENESS"] == 1.0
        assert out["band"] == "STRONG"

    def test_scores_crossdomain_junk_prior_art_low(self):
        from discovery_fabric.benchmark import candidate_quality as cq
        spec = self._spec(
            pa_titles=["Robotic surgical system for implants",
                       "Radiation imaging method"],
            pa_status="UNRESOLVED_INSUFFICIENT_EVIDENCE")
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "INVENTION_SPECIFICATION.json").write_text(json.dumps(spec))
            out = cq.measure_run(p)
        dims = {d["dimension"]: d["score"] for d in out["dimensions"]}
        assert dims["Q2_PRIOR_ART_SPECIFICITY"] == 0.0
        assert dims["Q3_PRIOR_ART_RESOLUTION"] == 0.0
        # the two differentiation dimensions collapse while the chain
        # remains structurally complete — exactly the measured survey
        # pattern (Q5=1.0, Q2/Q3=0.0)
        assert dims["Q5_CHAIN_COMPLETENESS"] == 1.0
        assert out["weakest_dimension"] in (
            "Q2_PRIOR_ART_SPECIFICITY", "Q3_PRIOR_ART_RESOLUTION")
        assert out["band"] != "STRONG"

    def test_unbound_evidence_scores_low_q1(self):
        from discovery_fabric.benchmark import candidate_quality as cq
        spec = self._spec(evidence_ids=[], pa_titles=[])
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "INVENTION_SPECIFICATION.json").write_text(json.dumps(spec))
            out = cq.measure_run(p)
        dims = {d["dimension"]: d["score"] for d in out["dimensions"]}
        assert dims["Q1_EVIDENCE_BINDING"] == 0.0
        assert out["state"] == "MEASURED"

    def test_missing_spec_is_unmeasurable_not_zero(self):
        """Art. XXV: no spec -> UNMEASURABLE, never a fabricated 0."""
        from discovery_fabric.benchmark import candidate_quality as cq
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            out = cq.measure_run(Path(td))
        assert out["state"] == "NO_SPEC"
        assert out["verdict"] == "UNMEASURABLE"
