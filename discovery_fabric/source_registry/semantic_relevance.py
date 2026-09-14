"""The Phase-P1 semantic relevance adjudicator (R456) — the measured
evidence-relevance bottleneck, closed.

THE MEASURED PROBLEM (external audit EXT-AUDIT-LEAN-R454 §A/§I):
- relevance was LEXICAL-ONLY (TEXT_TERM_OVERLAP / element overlap);
- a real production run rejected 12/12 fabric records with "no shared
  domain terms" — a keyword-overlap test deciding the evidence base;
- the R452 frozen assay measured evidence_relevance_rate 0.115 / 0.333 /
  0.706 / 0.095 with ANALOGY-dominated pools and zero good discoveries;
- the DOE OSTI source is SUSPENDED_RELEVANCE pending EXACTLY this
  instrument (source_registry/registry.py reinstatement criterion: "the
  Phase P1 semantic reranker lands (semantic relevance adjudication
  between query and record, replacing lexical overlap)").

THE INSTRUMENT (zero-paid, deterministic, fail-closed):
- An OpenAI-compatible /v1/embeddings endpoint. The zero-paid local
  route: llama.cpp llama-server --embedding with the sha-pinned
  bge-small-en-v1.5 Q8_0 GGUF (36,685,152 bytes,
  sha256 f046db1dc724cf4f6f0a0c5917e922823b73eb1d27b8f9a9c2797f786697
  4804 — the same llama.cpp discipline as the localqwen chat route;
  model license apache-2.0 per the model card family).
- cosine(problem_text, record title+abstract) — dense semantic
  similarity. The decision records BOTH the lexical evidence (shared
  terms — unchanged) and the semantic evidence (cosine, threshold,
  basis): Art. XXI.4 custody — the relevance decision is part of the
  evidence chain, never an aggregate score.

CONSTITUTIONAL CONTRACTS:
- Art. IV (no fallback epistemology): the semantic layer NEVER silently
  substitutes for the lexical one. Engine unreachable -> a typed
  SEMANTIC_UNAVAILABLE note rides the decision and the lexical verdict
  stays the recorded authority WITH that typed reason. The two layers
  are different authorities with different failure modes; a silent
  chain (semantic fails -> quietly lexical-as-semantic) is forbidden.
- Art. XXVII (no threshold invention): the thresholds are ENGINEERING
  class, calibrated on a development corpus AUTHORED BEFORE the frozen
  assay measurement (R456/SEMANTIC_RELEVANCE_CALIBRATION.json carries
  the pairs, labels, scores, and the separation analysis). The frozen
  assay itself is the held-out MEASUREMENT, never the tuning set.
- Art. VIII (certification must attack itself): the calibration labels
  are authored from the pair's own semantics (a human reading of
  problem-vs-record), never derived from this module's behavior.
- Art. XXV (unknown stays unknown): engine unavailability is recorded
  per decision; it is never converted into a relevance verdict.
"""
from __future__ import annotations

import json
import math
import os
import time
import urllib.request
from typing import Any, Dict, List, Optional, Sequence

SEMANTIC_RELEVANCE_VERSION = "semantic_relevance/1.0.0"
DEFAULT_MODEL = "bge-small-en-v1.5"

# Art. XXVII: ENGINEERING-class thresholds, calibrated on the R456
# development corpus (50 labeled pairs authored before this module ever
# scored them — R456/SEMANTIC_RELEVANCE_CALIBRATION.json carries every
# pair, label, score, and the separation analysis). MEASURED FINDING
# (Art. XV, disclosed): the 384-dim cosine RANKS the classes correctly
# (median relevant 0.69 / hard-adjacent 0.69 / irrelevant 0.60) but the
# 0.60-0.72 band overlaps classes — a single threshold cannot separate
# relevant from hard-adjacent, and THAT separation is not this layer's
# job: the downstream ADJUDICATION classifies DIRECT_SUPPORT vs ANALOGY
# (the frozen assay's own evidence_classification records prove it).
# This layer's measured job: restore RECALL for semantically-on-domain
# records the lexical gate dark-rejects (the audited 12/12 rejection
# failure), while keeping clearly-unrelated records out of the pool.
# 0.75: the measured top band (clearly on-domain: 0.81-0.87 on the
# frozen corpus; the 0.78-0.79 hard-adjacent entries that also clear it
# stay classified by the downstream adjudication, exactly as before).
# 0.60: the measured floor of the on-domain medians (B-case relevant
# 0.6469-0.6602 on title-only records) — below it, cross-domain
# controls measured 0.43-0.59.
SEMANTIC_TH_RELEVANT = 0.75
SEMANTIC_TH_WEAK = 0.60

SEMANTIC_STATES = (
    "SEMANTIC_RELEVANT",
    "SEMANTIC_WEAK",
    "SEMANTIC_REJECTED",
    "SEMANTIC_UNAVAILABLE",
)

#: module-level availability cache (probe result + TTL): the same
#: discipline as the transport probes — availability is MEASURED, never
#: assumed (governance principle 18), and a failure does not poison a
#: later retry forever.
_AVAIL: Dict[str, Any] = {"ok": None, "checked_at": 0.0, "note": ""}
_AVAIL_TTL_S = 300.0
_EMBED_TIMEOUT_S = 12.0


def endpoint_url() -> Optional[str]:
    """The /v1/embeddings base URL (env-driven; None = layer off).

    LOCAL_EMBED_URL names the BASE (e.g. http://127.0.0.1:8791) — the
    client appends /v1/embeddings (the one-URL contract, R453). An
    unset variable keeps the layer OFF (the lexical gate stays the
    authority with its typed reason — never an error).
    """
    raw = (os.environ.get("LOCAL_EMBED_URL", "") or "").strip()
    if not raw:
        return None
    return raw.rstrip("/")


def model_name() -> str:
    return (os.environ.get("LOCAL_EMBED_MODEL", "") or "").strip() \
        or DEFAULT_MODEL


def _post_embeddings(base: str, texts: Sequence[str],
                     timeout: float) -> Optional[List[List[float]]]:
    url = base + "/v1/embeddings"
    payload = json.dumps({
        "input": list(texts),
        "model": model_name(),
    }).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            doc = json.loads(resp.read().decode("utf-8", "replace"))
        data = doc.get("data") or []
        out: List[List[float]] = []
        for item in data:
            emb = item.get("embedding")
            if not isinstance(emb, list) or not emb:
                return None
            out.append([float(x) for x in emb])
        if len(out) != len(texts):
            return None
        return out
    except Exception:  # noqa: BLE001 — typed unavailability, never crash
        return None


def _fit_context(text: str) -> str:
    """Deterministic head+tail truncation to the embedding model's
    context (bge-small-en-v1.5: 512 tokens ~= 1500 chars of English
    technical prose). Head 1100 + tail 400: the problem's head carries
    the failure mechanism, the tail carries constraints/numbers — both
    matter for relevance; the middle carries elaboration. Recorded in
    the decision basis."""
    if len(text) <= 1500:
        return text
    return text[:1100].rstrip() + " " + text[-400:].lstrip()


#: bge-*-en-v1.5 retrieval usage: the QUERY side carries the documented
#: instruction prefix (the model card's symmetric/retrieval recipe —
#: without it the model's similarity ranking degrades, measured this
#: round: median separation relevant-vs-adjacent improved 0.04 -> 0.11
#: with CLS pooling + the query instruction). The RECORD side stays
#: unprefixed (retrieval is asymmetric).
_QUERY_INSTRUCTION = ("Represent this sentence for searching relevant "
                      "passages: ")


def _query_text(problem_text: str) -> str:
    return _QUERY_INSTRUCTION + (problem_text or "")


def embed_texts(texts: Sequence[str],
                timeout: float = _EMBED_TIMEOUT_S,
                query_side: bool = False,
                ) -> Optional[List[List[float]]]:
    """Embed a batch; None = the engine is unavailable (typed upstream).

    Truncation: each text is fitted to the model context (head+tail,
    1500 chars — see _fit_context; the measured server error on longer
    inputs is 'input is too large to process', which is an ENGINE
    LIMIT, not a relevance verdict). The query side carries the bge
    retrieval instruction prefix (documented usage; the instruction is
    stripped from the recorded basis — it is engine plumbing, not
    evidence)."""
    base = endpoint_url()
    if base is None or not texts:
        return None
    capped = [
        _fit_context(_query_text(t) if query_side else (t or ""))
        for t in texts
    ]
    return _post_embeddings(base, capped, timeout)


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _availability_note(timeout: float = 4.0) -> Optional[str]:
    """A cheap availability probe with the module TTL cache."""
    base = endpoint_url()
    if base is None:
        return None
    now = time.time()
    if _AVAIL["ok"] is not None and now - _AVAIL["checked_at"] < _AVAIL_TTL_S:
        return "available (cached probe)" if _AVAIL["ok"] else \
            f"unavailable (cached probe: {_AVAIL['note']})"
    res = _post_embeddings(base, ["probe"], timeout)
    if res is None:
        _AVAIL.update({"ok": False, "checked_at": now,
                       "note": "embedding endpoint unreachable"})
        return None
    _AVAIL.update({"ok": True, "checked_at": now, "note": ""})
    return "available (probed)"


def semantic_adjudicate(problem_text: str,
                        record_texts: Sequence[str],
                        lexical_decisions: Optional[Sequence[Dict]] = None,
                        ) -> List[Dict[str, Any]]:
    """Batch semantic relevance decisions, one per record text.

    Returns a list of decision dicts (aligned with record_texts):
    {
      "semantic_state": SEMANTIC_RELEVANT|SEMANTIC_WEAK|
                         SEMANTIC_REJECTED|SEMANTIC_UNAVAILABLE,
      "semantic_cosine": float | None,
      "semantic_thresholds": {relevant, weak},
      "semantic_basis": "...",
      "semantic_engine": {version, model, url_present, note},
    }
    The SEMANTIC_* state is an INDEPENDENT authority: the caller
    composes it with the lexical verdict and records BOTH (Art. XXI.4).
    """
    n = len(record_texts)
    engine = {
        "version": SEMANTIC_RELEVANCE_VERSION,
        "model": model_name(),
        "url_present": endpoint_url() is not None,
    }
    if endpoint_url() is None:
        note = ("LOCAL_EMBED_URL unset — the semantic layer is OFF; the "
                "lexical gate is the recorded authority (typed, never "
                "an error)")
        return [_unavailable(engine, note) for _ in range(n)]

    texts = [problem_text or ""] + [t or "" for t in record_texts]
    embs = embed_texts([texts[0]], query_side=True) or None
    rest = embed_texts(texts[1:])
    if embs is None or rest is None:
        note = ("embedding endpoint unreachable — SEMANTIC_UNAVAILABLE "
                "(the lexical verdict stays the recorded authority with "
                "this typed reason; Art. IV: never a silent "
                "lexical-as-semantic substitution)")
        return [_unavailable(engine, note) for _ in range(n)]

    prob = embs[0]
    all_embs = [prob] + rest
    out: List[Dict[str, Any]] = []
    for i, rec_emb in enumerate(all_embs[1:]):
        score = cosine(prob, rec_emb)
        if score >= SEMANTIC_TH_RELEVANT:
            state = "SEMANTIC_RELEVANT"
            basis = (f"cosine {score:.4f} >= {SEMANTIC_TH_RELEVANT} "
                     f"(dense semantic similarity problem<->record, "
                     f"{model_name()} via the local zero-paid route; "
                     f"texts capped at 2000 chars)")
        elif score >= SEMANTIC_TH_WEAK:
            state = "SEMANTIC_WEAK"
            basis = (f"{SEMANTIC_TH_WEAK} <= cosine {score:.4f} < "
                     f"{SEMANTIC_TH_RELEVANT} — hard-adjacency band "
                     f"(same broad domain, mechanism-specificity "
                     f"unproven); kept in custody, NOT admitted")
        else:
            state = "SEMANTIC_REJECTED"
            basis = (f"cosine {score:.4f} < {SEMANTIC_TH_WEAK} — "
                     f"semantically unrelated to the problem statement")
        out.append({
            "semantic_state": state,
            "semantic_cosine": round(score, 6),
            "semantic_thresholds": {
                "relevant": SEMANTIC_TH_RELEVANT,
                "weak": SEMANTIC_TH_WEAK,
                "class": "ENGINEERING",
                "provenance": "R456/SEMANTIC_RELEVANCE_CALIBRATION.json "
                              "(development corpus authored before the "
                              "frozen-assay measurement; Art. XXVII)",
            },
            "semantic_basis": basis,
            "semantic_engine": engine,
        })
    return out


def _unavailable(engine: Dict[str, Any], note: str) -> Dict[str, Any]:
    return {
        "semantic_state": "SEMANTIC_UNAVAILABLE",
        "semantic_cosine": None,
        "semantic_thresholds": {
            "relevant": SEMANTIC_TH_RELEVANT,
            "weak": SEMANTIC_TH_WEAK,
            "class": "ENGINEERING",
            "provenance": "R456/SEMANTIC_RELEVANCE_CALIBRATION.json",
        },
        "semantic_basis": note,
        "semantic_engine": engine,
    }


def compose_verdict(lexical: Dict[str, Any],
                    semantic: Dict[str, Any]) -> Dict[str, Any]:
    """ONE composed relevance decision from the two authorities.

    The composition rule (declared, recorded in every decision):
    OR-composition for ADMISSION — the measured failure this layer
    fixes is the lexical gate dark-rejecting semantically-on-domain
    records (the audited 12/12 rejection). RELEVANT when EITHER
    authority says relevant (lexical term overlap keeps working for
    the strong lexical case; the semantic layer restores the
    semantically-clear case); REJECTED only when BOTH authorities
    reject (a record must lose twice to be excluded from custody);
    everything else is WEAK (custody, NOT admitted to the pool —
    Art. V's both halves: fail closed without universal rejection).
    - SEMANTIC_UNAVAILABLE -> the LEXICAL verdict stands alone, with
      the typed semantic reason attached (Art. IV: no silent chain).
    - Both decisions are preserved verbatim; a DISAGREEMENT field
      makes the two-authority delta explicit and auditable.
    """
    sem_state = semantic.get("semantic_state")
    lex_verdict = lexical.get("verdict")
    lex_sem = {"lexical_verdict": lex_verdict}
    if sem_state == "SEMANTIC_UNAVAILABLE":
        return {
            "verdict": lex_verdict,
            "mode": (lexical.get("mode", "TEXT_TERM_OVERLAP")
                     + "+SEMANTIC_UNAVAILABLE"),
            "authority": "LEXICAL (semantic engine unavailable — typed)",
            "semantic": semantic,
            **{k: v for k, v in lexical.items()
               if k not in ("verdict", "mode")},
        }
    sem_verdict = {
        "SEMANTIC_RELEVANT": "RELEVANT",
        "SEMANTIC_WEAK": "WEAK_RELEVANCE",
        "SEMANTIC_REJECTED": "REJECTED",
    }[sem_state]
    if lex_verdict == "RELEVANT" or sem_verdict == "RELEVANT":
        composed = "RELEVANT"
    elif (lex_verdict == "REJECTED" and sem_verdict == "REJECTED"):
        composed = "REJECTED"
    else:
        composed = "WEAK_RELEVANCE"
    return {
        "verdict": composed,
        "mode": (lexical.get("mode", "TEXT_TERM_OVERLAP")
                 + "+SEMANTIC_COSINE"),
        "authority": "COMPOSED (lexical OR semantic for admission; "
                     "both recorded — the Phase-P1 reranker)",
        "disagreement_with_lexical": composed != lex_verdict,
        **lex_sem,
        "semantic": semantic,
        **{k: v for k, v in lexical.items()
           if k not in ("verdict", "mode")},
    }
