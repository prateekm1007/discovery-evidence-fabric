"""discovery_fabric/engine/answer_downgrade.py — DOWNGRADE, DON'T
DISCARD (owner audit round 2026-11-12, directive 2).

The R6 auditor measured the delivery cost of the strict ship/no-ship
split: contract-invalid final answers ship NOTHING, which raises the
no-answer rate for the user. The owner's directive: "when provenance
or contract checks fail, deterministically relabel failing
EVIDENCE-BACKED claims as ASSUMPTION, drop invalid citations and ship
the repaired answer with one plain-language caveat. Typed no-answer
only for scientific (contradicted/infeasible) kills." And: "A
truncated or partly invalid answer with a plain caveat beats a blank."

What this module does (deterministic, zero-LLM, Art. IV — it never
manufactures support, it only REMOVES unsupported certainty):
  1. An EVIDENCE-BACKED label whose bracketed citation fails the
     contract (no id, or an id that is not in the frozen packet) is
     relabeled ASSUMPTION and the invalid citation is dropped.
  2. Internal candidate ids ("[cand:...]") — pipeline jargon — are
     stripped from the delivered text (directive 1: clean output).
  3. The result re-runs the deterministic contract. Fully valid after
     the downgrade -> typed COMPOSED_CONTRACT_DOWNGRADED (delivered
     with ONE plain caveat). Still partly invalid -> delivered anyway
     with the same caveat, typed COMPOSED_CONTRACT_INVALID_DELIVERED;
     the open violations ride the record metadata (Art. XXV), never a
     banner, never a blank.

Typed no-answer stays ONLY for: transport failure, and the composer's
typed scientific refusals (NO_ADMISSIBLE_CANDIDATES on scientific /
contradicted / infeasible kills — the hypothesis-class kills are
delivered upstream per the approved attack semantics).

Serves: Art. LXIII (the buyer-facing answer exists), Art. XXV (labels
tell the truth: unsupported certainty becomes a stated assumption),
Art. LXXVII (the answer is the deliverable), Art. LXI (an invalid
citation is never silently converted into silence).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

ANSWER_DOWNGRADE_VERSION = "answer_downgrade/1.0.0"

#: the ONE plain-language caveat a downgraded delivery may carry
#: (directive 1: one plain-language caveat line at most)
DOWNGRADE_CAVEAT_LINE = (
    "Note: some supporting details in this answer could not be "
    "verified against the retrieved records and are labeled as "
    "engineering assumptions; the falsification test is the "
    "precondition for relying on them.")

_EB_LABEL_RE = re.compile(r"\bEVIDENCE[- ]BACKED\b", re.IGNORECASE)
_CITE_RE = re.compile(r"\[([^\[\]]{1,120})\]")
_CAND_ID_RE = re.compile(r"\[cand:[A-Za-z0-9_\-:.]{1,60}\]",
                         re.IGNORECASE)


def _packet_ids(packet: Optional[List[Dict[str, Any]]]) -> set:
    ids: set = set()
    for e in packet or []:
        if not isinstance(e, dict):
            continue
        for k in ("id", "source_id", "item_id", "doi", "title"):
            v = e.get(k)
            if isinstance(v, str) and v.strip():
                ids.add(v.strip().lower())
                ids.add(v.strip().lower().replace("doi:", ""))
    return ids


def _citation_valid(cite: str, packet_ids: set,
                    user_citation_ok: bool = True) -> bool:
    """A citation is VALID when it names a packet record (id/doi/title
    fragment match) OR is a user-provenance span ([user constraint] /
    [user-stated clarification] — P0-5: the user's own text is a legal
    provenance span)."""
    c = cite.strip().lower()
    if not c:
        return False
    if user_citation_ok and (
            c.startswith("user") or "user-stated" in c
            or "user constraint" in c
            or "user-stated clarification" in c):
        return True
    if c in packet_ids:
        return True
    c2 = c.replace("doi:", "").strip()
    if c2 in packet_ids:
        return True
    for pid in packet_ids:
        if len(pid) >= 8 and (pid in c2 or c2 in pid):
            return True
    return False


_EB_WITH_CITE_RE = re.compile(
    r"(?P<label>\bEVIDENCE[- ]BACKED\b)(?P<mid>[^\[\n]{0,120}?)"
    r"(?P<cite>\[[^\[\]\n]{1,120}\])", re.IGNORECASE)
_EB_NO_CITE_RE = re.compile(
    r"(?P<label>\bEVIDENCE[- ]BACKED\b)(?P<mid>[^\[\n]{0,120})"
    r"(?!\s*\[)", re.IGNORECASE)


def downgrade_answer(answer: str,
                     contract_violations: List[Any],
                     packet: Optional[List[Dict[str, Any]]],
                     ) -> Dict[str, Any]:
    """Deterministically downgrade a contract-invalid answer.

    Per claim: an EVIDENCE-BACKED label whose SAME-LINE citation is
    invalid (absent from the packet, not a user-provenance span) is
    relabeled ASSUMPTION and the citation is dropped; a label with no
    citation at all is relabeled ASSUMPTION. Internal candidate ids
    ("[cand:...]") are stripped (directive 1). NEVER adds support,
    never rewrites engineering content — it only relabels and removes.

    Returns {answer, n_relabels, n_citations_dropped, n_jargon_stripped,
             relabels, citations_dropped}."""
    text = str(answer or "")
    packet_ids = _packet_ids(packet)
    relabels: List[str] = []
    dropped: List[str] = []

    def _eb_cite_sub(m: "re.Match") -> str:
        cite = m.group("cite")[1:-1]
        if _citation_valid(cite, packet_ids):
            return m.group(0)
        dropped.append(cite.strip()[:80])
        relabels.append((m.group("label") + m.group("mid")).strip()[:160])
        return "ASSUMPTION" + m.group("mid")

    text = _EB_WITH_CITE_RE.sub(_eb_cite_sub, text)

    # labels with no bracketed id on the same line (contract violation:
    # label without reference) — relabel, drop nothing
    def _eb_nocite_sub(m: "re.Match") -> str:
        relabels.append((m.group("label") + m.group("mid")).strip()[:160])
        return "ASSUMPTION" + m.group("mid")

    text = _EB_NO_CITE_RE.sub(_eb_nocite_sub, text)

    # 2. pipeline-internal candidate ids never ship (directive 1)
    n_jargon = len(_CAND_ID_RE.findall(text))
    if n_jargon:
        text = _CAND_ID_RE.sub("", text)

    # collapse the whitespace the dropped citations left behind
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    return {"downgrade_version": ANSWER_DOWNGRADE_VERSION,
            "answer": text,
            "n_relabels": len(relabels),
            "n_citations_dropped": len(dropped),
            "n_jargon_stripped": n_jargon,
            "relabels": relabels[:10],
            "citations_dropped": dropped[:10]}


def truncate_at_sentence(text: str, max_chars: int = 6000) -> str:
    """A truncated draft delivered at the last COMPLETE sentence
    boundary (owner: 'a truncated ... answer with a plain caveat beats
    a blank'). Never cuts mid-word; never returns more than max_chars."""
    t = str(text or "").strip()
    if len(t) <= max_chars:
        return t
    t = t[:max_chars]
    cut = max(t.rfind("."), t.rfind("!"), t.rfind("?"), t.rfind("\n"))
    if cut < int(max_chars * 0.5):
        return t
    return t[:cut + 1].rstrip()
