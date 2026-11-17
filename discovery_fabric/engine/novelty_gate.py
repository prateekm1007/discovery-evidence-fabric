"""discovery_fabric/engine/novelty_gate.py — the deterministic TF-IDF
novelty gate (ShinkaEvolve pattern; R47 D3), migrated from scripts/
into the engine per the F63 remedy (R52). Pre-registered (BEFORE any
ablation run, per the AM44 test protocol):

- gate: reject a candidate whose TF-IDF cosine vs an already-accepted
  candidate/bill is >= NOVELTY_REJECT (duplicate/monoculture);
- borderline band [NOVELTY_JUDGE_LO, NOVELTY_REJECT): LLM judge only
  there (machine step); below the band = novel, accepted;
- pairwise gate among a row's own K candidates as well (kill the
  near-duplicate population F54 found).

Pure python (no new deps). Zero LLM calls in this module.
"""
import math
import re
from collections import Counter

NOVELTY_REJECT = 0.85      # cosine at/above this = duplicate (reject)
NOVELTY_JUDGE_LO = 0.70    # below this = novel (accept as-is)

_TOKEN = re.compile(r"[a-z]{3,}")
_STOP = {"the", "and", "for", "with", "that", "this", "from", "are",
         "was", "were", "has", "have", "had", "not", "but", "can",
         "may", "will", "which", "into", "than", "then", "when"}


def _tf(text: str) -> Counter:
    return Counter(t for t in _TOKEN.findall(text.lower())
                   if t not in _STOP)


def _idf(docs: list) -> dict:
    n = len(docs)
    df = Counter()
    for d in docs:
        df.update(set(d))
    return {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}


def tfidf_cosine(a: str, b: str, corpus: list = None) -> float:
    """Cosine between two texts under TF-IDF weighting; the weighting
    corpus defaults to [a, b] (pure length-normalized TF when the two
    texts are the whole corpus)."""
    ta, tb = _tf(a), _tf(b)
    corpus_docs = corpus if corpus else [ta, tb]
    idf = _idf([list(d) for d in corpus_docs])
    wa = {t: c * idf.get(t, 1.0) for t, c in ta.items()}
    wb = {t: c * idf.get(t, 1.0) for t, c in tb.items()}
    dot = sum(v * wb.get(t, 0.0) for t, v in wa.items())
    na = math.sqrt(sum(v * v for v in wa.values())) or 1.0
    nb = math.sqrt(sum(v * v for v in wb.values())) or 1.0
    return dot / (na * nb)


def jaccard(a: str, b: str) -> float:
    """Token-set Jaccard — the verbatim near-duplicate catch (cosine
    alone under-idf-weights single-token substitutions on tiny
    corpora)."""
    ta, tb = _tf(a), _tf(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    return inter / len(ta | tb)


def duplicate_score(a: str, b: str, corpus: list = None) -> float:
    """Pre-registered composite: max(tfidf cosine, jaccard). The
    cosine leg carries topical novelty; the Jaccard leg carries
    near-verbatim duplication."""
    return max(tfidf_cosine(a, b, corpus), jaccard(a, b))


def gate_row(candidates: list, accepted: list = None) -> dict:
    """Gate one row's candidate set. candidates: [{candidate_id, text}]
    (the text = mechanism + intervention + testable_prediction).
    Returns per-pair similarities and the keep/reject/judge states."""
    accepted = accepted or []
    texts = [c["text"] for c in candidates] + [
        a["text"] if isinstance(a, dict) else a for a in accepted]
    out = {"pairs": [], "verdicts": {}, "rejected": 0, "judge": 0}
    kept = []
    for i, c in enumerate(candidates):
        state = "novel"
        worst = 0.0
        vs = []
        for j, prev in enumerate(candidates[:i]):
            s = duplicate_score(c["text"], prev["text"], texts)
            vs.append((prev.get("candidate_id", f"cand_{j}"), round(s, 4)))
        for a in accepted:
            s = duplicate_score(c["text"], a["text"] if isinstance(
                a, dict) else a, texts)
            vs.append((a.get("candidate_id", "accepted") if isinstance(
                a, dict) else "accepted", round(s, 4)))
        for ref, s in vs:
            if s > worst:
                worst = s
            if s >= NOVELTY_REJECT:
                state = "reject-duplicate"
                break
        if NOVELTY_JUDGE_LO <= worst < NOVELTY_REJECT:
            state = "borderline-judge"
        out["pairs"].append({"candidate_id": c.get(
            "candidate_id", f"cand_{i}"), "similarities": vs,
            "worst": round(worst, 4), "verdict": state})
        out["verdicts"][c.get("candidate_id", f"cand_{i}")] = state
        if state == "reject-duplicate":
            out["rejected"] += 1
        elif state == "borderline-judge":
            out["judge"] += 1
        else:
            kept.append(c)
    out["kept"] = [c.get("candidate_id") for c in kept]
    return out
