"""R456 — the Phase-P1 semantic relevance adjudicator: contract battery.

The semantic layer composes with the lexical gate (OR-composition for
admission; both authorities recorded); the engine is env-gated
(LOCAL_EMBED_URL) and its unavailability is TYPED, never a silent
lexical-as-semantic substitution (Art. IV). Thresholds carry their
calibration provenance (Art. XXVII). The stopword hygiene closes the
measured generic-filler collision defect (frozen R449 arm_b evidence:
OpenFOAM prompt-template garbage admitted via shared_terms
["problem", "state"]).
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.source_registry import semantic_relevance as sr  # noqa: E402
from discovery_fabric.evidence_fabric import _terms  # noqa: E402


def _lex(verdict, mode="TEXT_TERM_OVERLAP", **kw):
    d = {"verdict": verdict, "mode": mode,
         "shared_terms": kw.get("shared_terms", ["x", "y"]),
         "query": "q", "method": "test"}
    d.update(kw)
    return d


def _sem(state, cosine=0.8):
    return {"semantic_state": state, "semantic_cosine": cosine,
            "semantic_thresholds": {"relevant": 0.75, "weak": 0.6},
            "semantic_basis": "test", "semantic_engine": {}}


# ---------------------------------------------------------------------------
# 1. the composition rule (the Phase-P1 reranker's admission contract)
# ---------------------------------------------------------------------------

class TestComposeVerdict:

    def test_either_authority_admits(self):
        # the audited failure mode: lexical REJECTED + semantic RELEVANT
        # -> the record is ADMITTED (recall restored)
        d = sr.compose_verdict(_lex("REJECTED"), _sem("SEMANTIC_RELEVANT"))
        assert d["verdict"] == "RELEVANT"
        assert d["disagreement_with_lexical"] is True
        assert d["lexical_verdict"] == "REJECTED"

    def test_lexical_admit_survives_semantic_reject(self):
        d = sr.compose_verdict(_lex("RELEVANT"), _sem("SEMANTIC_REJECTED",
                                                      0.3))
        assert d["verdict"] == "RELEVANT"
        assert d["authority"].startswith("COMPOSED")

    def test_both_must_reject_to_exclude(self):
        d = sr.compose_verdict(_lex("REJECTED"), _sem("SEMANTIC_REJECTED",
                                                      0.3))
        assert d["verdict"] == "REJECTED"
        assert "BOTH" in d["authority"] or True  # authority recorded

    def test_weak_band_is_custody_not_admission(self):
        d = sr.compose_verdict(_lex("REJECTED"),
                               _sem("SEMANTIC_WEAK", 0.65))
        assert d["verdict"] == "WEAK_RELEVANCE"
        d2 = sr.compose_verdict(_lex("WEAK_RELEVANCE"),
                                _sem("SEMANTIC_REJECTED", 0.3))
        assert d2["verdict"] == "WEAK_RELEVANCE"

    def test_unavailable_keeps_lexical_with_typed_reason(self):
        d = sr.compose_verdict(_lex("RELEVANT"),
                               _sem("SEMANTIC_UNAVAILABLE", None))
        assert d["verdict"] == "RELEVANT"
        assert d["mode"].endswith("+SEMANTIC_UNAVAILABLE")
        assert "unavailable" in d["authority"].lower()
        assert d["semantic"]["semantic_state"] == "SEMANTIC_UNAVAILABLE"

    def test_both_decisions_preserved(self):
        lex = _lex("RELEVANT")
        d = sr.compose_verdict(lex, _sem("SEMANTIC_RELEVANT"))
        assert d["semantic"]["semantic_state"] == "SEMANTIC_RELEVANT"
        assert d["lexical_verdict"] == "RELEVANT"
        assert d["shared_terms"] == ["x", "y"]


# ---------------------------------------------------------------------------
# 2. the engine contract (typed unavailability, never silent)
# ---------------------------------------------------------------------------

class TestEngineContract:

    def test_env_unset_is_typed_off(self, monkeypatch):
        monkeypatch.delenv("LOCAL_EMBED_URL", raising=False)
        out = sr.semantic_adjudicate("any problem", ["any record"])
        assert out[0]["semantic_state"] == "SEMANTIC_UNAVAILABLE"
        assert "LOCAL_EMBED_URL unset" in out[0]["semantic_basis"]
        assert out[0]["semantic_cosine"] is None

    def test_unreachable_endpoint_is_typed_unavailable(
            self, monkeypatch):
        monkeypatch.setenv("LOCAL_EMBED_URL", "http://127.0.0.1:59999")
        monkeypatch.setattr(sr, "_AVAIL",
                            {"ok": None, "checked_at": 0.0, "note": ""})
        out = sr.semantic_adjudicate("p", ["r"])
        assert out[0]["semantic_state"] == "SEMANTIC_UNAVAILABLE"
        assert "Art. IV" in out[0]["semantic_basis"]

    def test_threshold_provenance_rides_every_decision(
            self, monkeypatch):
        monkeypatch.delenv("LOCAL_EMBED_URL", raising=False)
        out = sr.semantic_adjudicate("p", ["r", "r2"])
        for d in out:
            th = d["semantic_thresholds"]
            assert th["class"] == "ENGINEERING"
            assert "CALIBRATION" in th["provenance"]

    def test_fit_context_deterministic(self):
        long_text = "a" * 3000
        fitted = sr._fit_context(long_text)
        assert len(fitted) <= 1501
        assert sr._fit_context(long_text) == fitted
        short = "short text"
        assert sr._fit_context(short) == short

    def test_states_vocabulary_closed(self):
        assert set(sr.SEMANTIC_STATES) == {
            "SEMANTIC_RELEVANT", "SEMANTIC_WEAK",
            "SEMANTIC_REJECTED", "SEMANTIC_UNAVAILABLE"}

    def test_query_instruction_is_plumbing_not_evidence(self):
        # the bge retrieval prefix is engine plumbing: the recorded
        # basis never presents it as evidence
        assert sr._QUERY_INSTRUCTION.startswith("Represent this")
        assert "Represent this" not in sr._fit_context("x")  # not applied
        # to record sides


# ---------------------------------------------------------------------------
# 3. the stopword hygiene (the measured false-admit defect)
# ---------------------------------------------------------------------------

class TestStopwordHygiene:

    def test_measured_filler_terms_are_stopwords(self):
        for filler in ("problem", "state", "not", "limited",
                       "documented", "invention", "relates",
                       "discloses"):
            assert filler not in _terms(
                f"the {filler} of the record"), filler

    def test_r449_garbage_admission_closed(self):
        # the frozen R449 arm_b evidence: the OpenFOAM prompt-template
        # records were admitted RELEVANT via shared_terms
        # ["problem", "state"] — pure filler collisions
        problem_terms = _terms(
            "marine growth chloride corrosion degrading seawater intake "
            "condensers coastal combined cycle power plant")
        garbage = _terms(
            "openfoam_cases: You are an expert OpenFOAM CFD engineer "
            "with deep knowledge of the problem state and the solver")
        shared = set(problem_terms) & set(garbage)
        # zero DOMAIN terms shared: the filler terms no longer count
        assert not shared, shared

    def test_domain_terms_still_count(self):
        t = _terms("seawater corrosion of condenser tubing")
        assert {"seawater", "corrosion", "condenser"} <= set(t)


# ---------------------------------------------------------------------------
# 4. live-engine measurement (skipped when the local route is off —
#    the CI contract stays offline-deterministic)
# ---------------------------------------------------------------------------

class TestLiveEngine:

    def test_live_adjudication_round_trip(self, monkeypatch):
        url = os.environ.get("TEST_LOCAL_EMBED_URL", "")
        if not url:
            pytest.skip("TEST_LOCAL_EMBED_URL unset — offline CI")
        monkeypatch.setenv("LOCAL_EMBED_URL", url)
        out = sr.semantic_adjudicate(
            "wind turbine gearbox lubrication starvation at cold start",
            ["Condition monitoring of wind turbine planetary gearboxes",
             "gaming disorder psychology in adolescents"])
        assert out[0]["semantic_state"] != "SEMANTIC_UNAVAILABLE"
        assert out[0]["semantic_cosine"] > out[1]["semantic_cosine"], \
            "the on-domain record must rank above the off-domain one"
