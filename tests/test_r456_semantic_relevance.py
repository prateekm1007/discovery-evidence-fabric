"""R456 — the Phase-P1 semantic relevance instrument battery.

Offline by construction: the corpus is committed; the frozen R452
records are committed. Covers:
  - the full committed corpus (positives admit, negatives reject,
    gray zone stays in custody) — Art. V both halves
  - the declared metamorphic contract (one band step, no
    REJECTED<->RELEVANT flip) — Art. V metamorphic
  - determinism (byte-identical basis on repeated runs) — Art. LXII
  - totality (empty inputs, tiny pools — never raises)
  - custody semantics (WEAK/REJECTED never silently dropped) — Art. XXV
  - threshold provenance (declared constants + committed corpus) —
    Art. XXVII
  - the held-out frozen R452 boilerplate records REJECT (the measured
    defect the instrument replaces, 24 records)
  - the admission-gaming attack (generic-token padding)
  - the registry integration (doe_osti criterion records the landed
    instrument; the routing-state invariant stays closed)
  - the evidence-fabric integration (mode SEMANTIC_RELEVANCE recorded)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.source_registry import registry as reg  # noqa: E402
from discovery_fabric.source_registry import semantic_relevance as sr  # noqa: E402
from discovery_fabric.source_registry import query_relevance as qr  # noqa: E402
from discovery_fabric.evidence_fabric import adjudicate_relevance  # noqa: E402

CORPUS = REPO / "discovery_fabric" / "source_registry" / \
    "RELEVANCE_CORPUS_R456.json"

BANDS = {"REJECTED": 0, "WEAK_RELEVANCE": 1, "RELEVANT": 2}


def _problem_text(p: dict) -> str:
    return ". ".join(str(p.get(k) or "") for k in
                     ("device", "failure", "user_text")).strip(". ")


@pytest.fixture(scope="module")
def corpus():
    return json.loads(CORPUS.read_text())


@pytest.fixture(scope="module")
def corpus_results(corpus):
    pool = [_problem_text(c["problem"]) for c in corpus["cases"]]
    out = {}
    for c in corpus["cases"]:
        out[c["case_id"]] = sr.adjudicate(
            _problem_text(c["problem"]), c["record_text"], pool)
    return out


# ---------------------------------------------------------------------------
# 1. The committed corpus: positives admit, negatives reject
# ---------------------------------------------------------------------------

def test_corpus_labels_held(corpus, corpus_results):
    for c in corpus["cases"]:
        if "expected_any_of" in c:
            continue  # gray-zone pins — covered by the dedicated test
        got = corpus_results[c["case_id"]]["verdict"]
        assert got == c["expected"], \
            f"{c['case_id']}: expected {c['expected']} got {got}"


def test_gray_zone_pins_never_rejected(corpus, corpus_results):
    for c in corpus["cases"]:
        if "expected_any_of" in c:
            got = corpus_results[c["case_id"]]["verdict"]
            assert got in c["expected_any_of"], \
                f"{c['case_id']}: {got} not in {c['expected_any_of']}"


# ---------------------------------------------------------------------------
# 2. The declared metamorphic contract
# ---------------------------------------------------------------------------

def test_metamorphic_contract(corpus, corpus_results):
    for a, b in [("METAMORPHIC_POS_GEARBOX_PAIR_A",
                  "METAMORPHIC_POS_GEARBOX_PAIR_B"),
                 ("METAMORPHIC_NEG_SIC_PAIR_A",
                  "METAMORPHIC_NEG_SIC_PAIR_B")]:
        va = corpus_results[a]["verdict"]
        vb = corpus_results[b]["verdict"]
        assert abs(BANDS[va] - BANDS[vb]) <= 1, f"{a}/{b}: {va}/{vb}"
        assert {va, vb} != {"REJECTED", "RELEVANT"}, \
            f"{a}/{b}: direct admission flip"


def test_adversarial_surface_paraphrase_random_insertion():
    """Attack: random generic-word padding of a REJECTED record must
    not lift it over the admission floor (the gaming attempt an
    untrusted retriever could try)."""
    problem = ("An ambulatory surgery center runs arthroscopic shoulder "
               "and knee cases on a peristaltic dual-bag irrigation "
               "system: inflow pressure sags, then surges, destabilizing "
               "cavity distension.")
    off_domain = ("Tire pressure monitoring systems: valve-stem leakage "
                  "and temperature-driven gauge-pressure drift in "
                  "passenger-vehicle tires.")
    base = sr.adjudicate(problem, off_domain)
    assert base["verdict"] == "REJECTED"
    padded = off_domain + (" " + "system method process result state "
                           "model design data time case study analysis "
                           "performance effect control test value level "
                           "rate number approach technique application "
                           "field condition feature type form range work "
                           "provide ensure include") * 6
    padded_res = sr.adjudicate(problem, padded)
    assert padded_res["verdict"] != "RELEVANT", \
        f"generic padding lifted the off-domain record: {padded_res['score']}"


# ---------------------------------------------------------------------------
# 3. Determinism (Art. LXII) + totality
# ---------------------------------------------------------------------------

def test_determinism_byte_identical():
    q = "wind farm gearbox lubrication starvation at cold start"
    r = "Cold-start lubricant supply in wind turbine gearboxes: pre-heating."
    a = json.dumps(sr.adjudicate(q, r), sort_keys=True)
    b = json.dumps(sr.adjudicate(q, r), sort_keys=True)
    assert a == b


def test_totality_empty_and_tiny_inputs():
    # empty everything: scores 0, REJECTED, never raises
    d = sr.adjudicate("", "")
    assert d["verdict"] == "REJECTED" and d["score"] == 0.0
    # empty record against a real query
    d2 = sr.adjudicate("battery thermal runaway", "")
    assert d2["verdict"] == "REJECTED"
    # a one-record pool: static fallback path, no crash
    d3 = sr.adjudicate("battery thermal runaway",
                       "Propagation of thermal runaway in cells",
                       pool_texts=["one record only"])
    assert d3["idf_source"] == "static_fallback"
    # pool under MIN_POOL_FOR_IDF disclosed as static fallback
    d4 = sr.adjudicate("battery thermal runaway",
                       "Propagation of thermal runaway in cells",
                       pool_texts=["a", "b", "c"])
    assert d4["idf_source"] == "static_fallback"


# ---------------------------------------------------------------------------
# 4. Threshold provenance (Art. XXVII)
# ---------------------------------------------------------------------------

def test_thresholds_declared_and_corpus_committed():
    assert sr.RELEVANT_FLOOR == 0.36
    assert sr.WEAK_FLOOR == 0.18
    assert sr.CORPUS_PROVENANCE in sr.adjudicate("a b c", "a b c")["method"]
    assert CORPUS.exists(), "the calibration corpus must be committed"
    body = CORPUS.read_text()
    assert "authoring_rule" in body
    assert "Art. VIII" in body


# ---------------------------------------------------------------------------
# 5. Custody semantics (Art. XXV) — through the evidence gate
# ---------------------------------------------------------------------------

class _Rec:
    """Minimal real EvidenceRecord (custody dataclasses, no mocks)."""

    def __init__(self, text, source_type="E2_scientific_intelligence"):
        from discovery_fabric.evidence_fabric.evidence_record import (
            EvidenceRecord, ExactSpan, SourceIdentity)
        self._cls = EvidenceRecord
        self._span = ExactSpan(dataset_id="d", config="c", split="s",
                               row_idx=0, field="text", text=text)
        self._src = SourceIdentity(source_id="s", family="f", url="u")
        self.source_type = source_type

    def build(self, text):
        import hashlib
        from discovery_fabric.evidence_fabric.evidence_record import \
            ExactSpan
        return self._cls(
            evidence_id="ev:test",
            source_identity=self._src,
            source_version="v",
            source_type=self.source_type,
            retrieval_timestamp="2026-09-15T00:00:00Z",
            content_hash=hashlib.sha256(text.encode()).hexdigest(),
            exact_span=ExactSpan(dataset_id="d", config="c", split="s",
                                 row_idx=0, field="text", text=text),
        )


def _promote(text):
    from discovery_fabric.evidence_fabric import _relevance_promote
    rec = _Rec(text).build(text)
    dec = adjudicate_relevance(
        rec, [], [], "",
        problem_text="arthroscopic irrigation inflow pressure instability "
                     "during shoulder and knee cases",
        pool_texts=[text, "another record about gearbox lubrication"])
    _relevance_promote(rec, dec)
    return rec, dec


def test_custody_states_via_promotion():
    # on-domain positive admits to corroboration-pending
    rec, dec = _promote(
        "A closed-loop inflow regulator compensated for aspirator-induced "
        "pressure sag in arthroscopic fluid systems; joint distension "
        "stability improved across 40 shoulder procedures.")
    assert dec["verdict"] == "RELEVANT"
    assert dec["mode"] == "SEMANTIC_RELEVANCE"
    assert rec.admissibility.state == "PENDING_CORROBORATION"
    # off-domain rejection keeps custody, never dropped
    rec2, dec2 = _promote(
        "Tire pressure monitoring systems: valve-stem leakage in "
        "passenger-vehicle tires with fleet alert logic.")
    assert dec2["verdict"] == "REJECTED"
    assert rec2.admissibility.state == "BLOCKED_RELEVANCE_REJECTED"
    assert rec2.admissibility.reasons  # the basis is recorded
    # gray zone stays pending, never admitted
    rec3, dec3 = _promote(
        "Layer growth and interface roughness in epitaxial "
        "silicon-carbide wafers: sublimation-growth process conditions "
        "and micropipe density in substrate yield.")
    assert dec3["verdict"] in ("WEAK_RELEVANCE", "REJECTED")
    assert rec3.admissibility.state != "PENDING_CORROBORATION"


# ---------------------------------------------------------------------------
# 6. The held-out frozen R452 records REJECT (the measured defect)
# ---------------------------------------------------------------------------

def test_frozen_r452_boilerplate_rejected():
    n = 0
    for run in ("ASSAY_RUN_A", "ASSAY_RUN_B", "ASSAY_RUN_C",
                "ASSAY_RUN_A2"):
        f = REPO / "R452" / run / "EVIDENCE_FABRIC_REPORT.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text())
        fp = REPO / "R452" / run / "fresh_problem.json"
        prob = json.loads(fp.read_text()) if fp.exists() else {}
        prob = prob.get("problem", prob)
        qtext = _problem_text(prob)
        for r in (d.get("records") or []):
            rel = r.get("relevance") or {}
            if rel.get("mode") != "TEXT_TERM_OVERLAP":
                continue
            span_text = str((r.get("exact_span") or {}).get("text", ""))
            dec = sr.adjudicate(qtext, span_text)
            assert dec["verdict"] != "RELEVANT", (
                f"{run}/{r.get('evidence_id')}: the boilerplate the "
                f"lexical gate admitted still scores RELEVANT "
                f"({dec['score']})")
            n += 1
    assert n >= 20, f"expected the frozen boilerplate set, got {n}"


# ---------------------------------------------------------------------------
# 7. Registry integration
# ---------------------------------------------------------------------------

def test_doe_osti_criterion_records_landed_instrument():
    info = reg.routing_info("doe_osti")
    assert reg.routing_state("doe_osti") == "SUSPENDED_RELEVANCE"
    crit = info["reinstatement_criterion"].lower()
    assert "semantic" in crit
    assert "landed" in crit
    assert "measured" in crit


def test_routing_state_invariant_closed():
    for sid, rec in reg.SOURCE_REGISTRY.items():
        assert rec.get("routing_state") in reg.ROUTING_STATES, sid


def test_query_relevance_returns_score_and_band():
    rec = {"record_id": "r", "title": "Thermal runaway in cells",
           "normalized": {"abstract": "Nail-penetration abuse testing of "
                                      "lithium-ion cells."}}
    a = qr.adjudicate_record(rec, "battery thermal runaway")
    assert a["relevance"] in (qr.RELEVANT, qr.IRRELEVANT)
    assert "relevance_score" in a and "relevance_band" in a
    assert "method" in a["relevance_basis"]
