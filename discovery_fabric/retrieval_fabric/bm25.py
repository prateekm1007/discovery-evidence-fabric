"""Deterministic BM25 per-record relevance (owner round 2026-11-12, item A2).

Owner directive: "deterministic per-record relevance to failure + constraint
(BM25 or embedding) for anchor choice and packet order." This module is the
BM25 instrument — no new external dependency: pure-stdlib Okapi BM25
(k1=1.2, b=0.75), whole-token discipline inherited from
query_expansion (R6 A4 follow-up: hyphenated compounds stay whole; stopword
list shared with the query-derivation instrument, Art. XXVII: a recorded
policy input, never per-problem tuning), zero LLM, deterministic (identical
inputs -> byte-identical ordering).

Document side: record title + abstract (the mechanism-bearing text;
metadata-only documents score on their title and rank accordingly — that
is the signal, never a fabrication, Art. XXV). Query side: the problem's
OWN content facts only (device + failure + failure_mode + constraint;
Art. XLIII — no solution-class injection).

The anchor-domain match instrument below mirrors the engine gate
(intervention_gate.anchor_domain_check: distinctive shared tokens >= 3,
low-information vocabulary excluded) over the record's raw text, so the
reported rate is comparable to the gate that actually rejects off-domain
anchors (Art. LXXVII: the metric must measure the decision it feeds).
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from discovery_fabric.retrieval_fabric.query_expansion import _STOPWORDS

#: k1/b are the recorded instrument constants (Art. XXVII) — Okapi defaults,
#: not per-problem tuning.
BM25_K1 = 1.2
BM25_B = 0.75

#: whole-token discipline (query_expansion R6 A4 follow-up): lowercase
#: alphanumeric runs; hyphen/dot/slash compounds kept whole; single
#: characters and shared stopwords dropped.
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-./][a-z0-9]+)*")

#: mirror of the anchor-domain gate's distinctive-token rule
#: (intervention_gate.anchor_domain_check, measured 2026-11-12): shared
#: tokens must be lenient >= 4 and outside the gate's low-info set.
_ANCHOR_DISTINCTIVE_MIN_LEN = 4
_ANCHOR_MIN_SHARED = 3  # == intervention_gate._ANCHOR_MIN_SHARED_TOKENS
_ANCHOR_LOW_INFO = frozenset(
    "stack content contents percentage value level layer layers field "
    "fields time period state model models case cases data point points "
    "system systems analysis results result test tests method methods "
    "approach approaches based using".split())


def tokenize(text: Optional[str]) -> List[str]:
    """Deterministic token list (order preserved, lowercase, compounds
    whole). Every instrument in this module shares this tokenizer, so a
    record's score and a query's expansion cannot disagree about words."""
    if not text:
        return []
    out: List[str] = []
    for tok in _TOKEN_RE.findall(str(text).lower()):
        if len(tok) > 1 and tok not in _STOPWORDS:
            out.append(tok)
    return out


def problem_relevance_text(problem: Optional[Dict[str, Any]]) -> str:
    """The problem's own content facts as one text block (Art. XLIII).
    Empty when no problem — callers must then leave ordering unchanged."""
    if not problem:
        return ""
    return " ".join(str(problem.get(k) or "") for k in
                   ("device", "failure", "failure_mode", "constraint"))


def record_text(record: Dict[str, Any]) -> str:
    """One record's mechanism-bearing text, flat keys and the canonical
    nested form (best_record / normalized) both accepted — the engine
    items and the canonical pool dicts carry the same fields under
    different nesting."""
    flat = " ".join(str(record.get(k) or "") for k in
                    ("title", "abstract", "snippet"))
    nested = (record.get("best_record") or record.get("normalized")
              or {})
    if isinstance(nested, dict):
        flat += " " + " ".join(str(nested.get(k) or "") for k in
                               ("title", "abstract", "summary"))
    return flat


class BM25:
    """Okapi BM25 over a fixed document set. The document set is fixed
    at construction per call site (one problem, one pool) — the score is
    a pure function of (pool, problem text); rerunning the same inputs
    yields identical scores (the replay discipline)."""

    def __init__(self, docs: Sequence[str],
                 k1: float = BM25_K1, b: float = BM25_B) -> None:
        self.k1 = k1
        self.b = b
        tokenized = [tokenize(d) for d in docs]
        self._tf: List[Dict[str, int]] = [
            {} for _ in tokenized]
        for toks in tokenized:
            for t in toks:
                self._tf[-1][t] = self._tf[-1].get(t, 0) + 1
        n = len(docs)
        self._n = n
        self._avgdl = (sum(len(t) for t in tokenized) / n) if n else 0.0
        self._dfs: Dict[str, int] = {}
        for tf in self._tf:
            for t in tf:
                self._dfs[t] = self._dfs.get(t, 0) + 1
        self._lens = [len(t) for t in tokenized]

    def scores(self, query_text: str) -> List[float]:
        """BM25 score per document (0.0 when the query has no tokens)."""
        q = tokenize(query_text)
        if not q or not self._n:
            return [0.0] * self._n
        idf: Dict[str, float] = {}
        for t in set(q):
            df = self._dfs.get(t, 0)
            # Okapi idf, floor at 0 (rare terms score >= common ones; a
            # term absent from the pool scores 0 — recorded, not invented)
            idf[t] = max(0.0, math.log((self._n - df + 0.5)
                                       / (df + 0.5)))
        out: List[float] = []
        for i in range(self._n):
            tf_map = self._tf[i]
            dl = self._lens[i] or 1
            s = 0.0
            for t in set(q):
                f = tf_map.get(t, 0)
                if not f:
                    continue
                s += idf[t] * f * (self.k1 + 1) / (
                    f + self.k1 * (1 - self.b + self.b * dl /
                                   (self._avgdl or 1)))
            out.append(s)
        return out


def select_anchors(records: Sequence[Dict[str, Any]],
                   problem: Optional[Dict[str, Any]],
                   top_k: int = 6) -> Tuple[List[int], List[float]]:
    """Deterministic anchor choice: BM25 over (title + abstract) against
    the problem text; ties break on the record's own id so two hosts
    produce byte-identical orders."""
    if not records:
        return ([], [])
    idx = BM25([record_text(r) for r in records])
    scores = idx.scores(problem_relevance_text(problem))
    order = sorted(range(len(records)),
                   key=lambda i: (-scores[i],
                                  str(records[i].get("id")
                                      or records[i].get("canonical_id")
                                      or "")))
    return order[:max(0, top_k)], scores


def anchor_domain_match(problem: Dict[str, Any],
                       record: Dict[str, Any]) -> Dict[str, Any]:
    """The anchor-domain question as the ENGINE GATE asks it
    (intervention_gate.anchor_domain_check): do the record's distinctive
    tokens overlap the problem's domain text by >= 3? Deterministic,
    zero LLM; the returned dict is machine-checkable (Art. LXXXV)."""
    pt = " ".join(str(problem.get(k) or "") for k in
                  ("domain", "device", "failure", "failure_mode"))
    pt_tokens = {t for t in tokenize(pt)
                 if len(t) >= _ANCHOR_DISTINCTIVE_MIN_LEN
                 and t not in _ANCHOR_LOW_INFO}
    at_tokens = {t for t in tokenize(record_text(record))
                 if len(t) >= _ANCHOR_DISTINCTIVE_MIN_LEN
                 and t not in _ANCHOR_LOW_INFO}
    shared = sorted(pt_tokens & at_tokens)
    return {"shared": shared[:12],
            "n_shared": len(shared),
            "match": len(shared) >= _ANCHOR_MIN_SHARED}


def anchor_domain_match_rate(problem: Dict[str, Any],
                             records: Sequence[Dict[str, Any]],
                             top_k: int = 6) -> Dict[str, Any]:
    """Match rate over the top_k anchors SELECTED BY BM25 itself (the
    decision this metric feeds, Art. LXXVII): fraction of the top-k that
    pass the domain match. top_k >= pool size clamps to the pool."""
    sel, _ = select_anchors(records, problem, top_k)
    if not sel:
        return {"rate": None, "matched": 0, "n": 0,
                "selected": [], "detail": []}
    detail = []
    matched = 0
    for i in sel:
        m = anchor_domain_match(problem, records[i])
        detail.append({"index": i,
                       "id": str(records[i].get("id")
                                or records[i].get("canonical_id") or ""),
                       "title": str(records[i].get("title") or "")[:100],
                       "n_shared": m["n_shared"], "match": m["match"]})
        matched += 1 if m["match"] else 0
    return {"rate": round(matched / len(sel), 3),
            "matched": matched, "n": len(sel),
            "selected": [str(records[i].get("id") or
                             records[i].get("canonical_id") or "")
                         for i in sel],
            "detail": detail}
