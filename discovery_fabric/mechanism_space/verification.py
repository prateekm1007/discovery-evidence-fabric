"""R401 Phase 11 — mechanism-level evidence verification.

The constitutional rule this module encodes:

    PHENOMENON SUPPORT DOES NOT IMPLY MECHANISM SUPPORT.

An evidence record that observes the same failure/effect as a candidate
mechanism does NOT support the mechanism. Support requires overlap on the
CAUSAL account: the evidence's asserted mechanism (its cause->effect
content) must overlap the candidate's causal graph (its edges' node
labels), not merely its topic.

Verdict vocabulary (exactly the directive's five):
    SUPPORTS / PARTIALLY_SUPPORTS / CONTRADICTS / IRRELEVANT /
    NOT_ENOUGH_EVIDENCE

V0 is deterministic rule-based matching over structured evidence fields
(no LLM): every verdict cites the records and the matched/unmatched
causal pairs that produced it.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List

VERDICTS = ("SUPPORTS", "PARTIALLY_SUPPORTS", "CONTRADICTS", "IRRELEVANT",
            "NOT_ENOUGH_EVIDENCE")


def _tok(s: str):
    return set(w for w in re.findall(r"[a-z]{3,}", (s or "").lower()))


def _sim(a: set, b: set) -> float:
    return len(a & b) / max(1, len(a | b))


def _candidate_topic(cand: Dict[str, Any]) -> set:
    """Topic tokens: system + failure mode + problem statement. These match
    ANY on-topic record, so they can never carry MECHANISM evidence (the
    phenomenon-support-is-not-mechanism-support rule, enforced downstream)."""
    return _tok(f"{cand.get('system','')} "
                f"{cand.get('failure_mode','').replace('_',' ')} "
                f"{cand.get('problem','')}")


def _candidate_causal_pairs(cand: Dict[str, Any]) -> List[tuple]:
    g = cand["mechanism_graph"]
    labels = {n["id"]: n["label"] for n in g["nodes"]}
    return [(labels[e["src"]], e["rel"], labels[e["dst"]]) for e in g["edges"]]


def _pair_supported(pair: tuple, ev_mech: set, ev_effect: set,
                    topic: set = frozenset()) -> bool:
    src, rel, dst = pair
    src_t = _tok(src) - topic   # topic tokens cannot carry causal evidence
    dst_t = _tok(dst) - topic
    if not src_t or not dst_t:
        return False
    ev = ev_mech | ev_effect
    # the evidence must carry BOTH the cause-side and the effect-side of
    # the asserted causal pair, in mechanism-specific vocabulary
    return bool((src_t & ev) and (dst_t & ev))


def verify_one(evidence: Dict[str, Any], cand: Dict[str, Any],
               sim_floor: float = 0.03) -> Dict[str, Any]:
    """Verdict of ONE evidence record against ONE candidate mechanism."""
    ev_mech = _tok(evidence.get("mechanism", ""))
    ev_effect = _tok(evidence.get("observed_effect", ""))
    topic = _candidate_topic(cand)
    topic_sim = _sim(topic, ev_mech | ev_effect)
    pairs = _candidate_causal_pairs(cand)
    matched = [p for p in pairs if _pair_supported(p, ev_mech, ev_effect, topic)]

    # CONTRADICTS: evidence carries an explicit contrary marker about the
    # candidate's predicted direction on the same phenomenon. V0 signal:
    # a 'contrary' field set by the evidence author/adjudicator, or the
    # words 'no effect'/'does not'/'worsen' aligned with the topic.
    text = f"{evidence.get('claim','')} {evidence.get('observed_effect','')}".lower()
    contrary = bool(evidence.get("contrary")) or (
        topic_sim >= sim_floor and re.search(
            r"\b(no effect|not associated|does not (cause|lead|reduce)|"
            r"worsen(s|ed)?|increases? .{0,40}instead of reduc)", text))

    if topic_sim < sim_floor and not matched:
        return {"verdict": "IRRELEVANT", "topic_similarity": round(topic_sim, 3),
                "matched_causal_pairs": [], "evidence": evidence["source"]}
    if contrary:
        return {"verdict": "CONTRADICTS", "topic_similarity": round(topic_sim, 3),
                "matched_causal_pairs": [list(p) for p in matched],
                "evidence": evidence["source"]}
    if not matched:
        # phenomenon-level overlap only: the constitution's exact case —
        # same effect observed, causal account untested by this record.
        return {"verdict": "NOT_ENOUGH_EVIDENCE",
                "topic_similarity": round(topic_sim, 3),
                "matched_causal_pairs": [], "evidence": evidence["source"]}
    strong = [p for p in matched if _pair_supported(p, ev_mech, set(), topic)]
    verdict = "SUPPORTS" if len(strong) >= max(1, len(pairs) // 2) \
        else "PARTIALLY_SUPPORTS"
    return {"verdict": verdict, "topic_similarity": round(topic_sim, 3),
            "matched_causal_pairs": [list(p) for p in matched],
            "strong_pairs": [list(p) for p in strong],
            "evidence": evidence["source"]}


def verify_mechanism_evidence(evidence: List[Dict[str, Any]],
                              cand: Dict[str, Any]) -> Dict[str, Any]:
    """Bundle verdict for one candidate across all evidence records."""
    per = [verify_one(e, cand) for e in evidence]
    counts = {v: 0 for v in VERDICTS}
    for r in per:
        counts[r["verdict"]] += 1
    if counts["CONTRADICTS"]:
        bundle = "CONTRADICTED"
    elif counts["SUPPORTS"] >= 2 or (counts["SUPPORTS"] >= 1 and
                                     counts["PARTIALLY_SUPPORTS"] >= 1):
        bundle = "SUPPORTED"
    elif counts["SUPPORTS"] or counts["PARTIALLY_SUPPORTS"]:
        bundle = "PARTIALLY_SUPPORTED"
    elif counts["NOT_ENOUGH_EVIDENCE"]:
        bundle = "PHENOMENON_LEVEL_ONLY"
    else:
        bundle = "UNSUPPORTED"
    return {"candidate": cand["id"], "bundle_verdict": bundle,
            "counts": counts, "per_evidence": per}
