"""discovery_fabric/engine/citation_identity.py — bibliographic
citation-identity verification (R139 DIR-6, the auditor's [[25]]
class: exact lookup + fuzzy match (+ optional LLM arbiter) to kill
alias / forged-id citations BEFORE they become source identities).

The R139 verifier probes measured the defect this instrument targets:
a binding citing "lean_doi:10.1080/..." (a synthetic alias) while the
frozen record is "doi:10.1080/..." — the alias was ADMITTED by the
R138 rule. The R139S3 admission resolver now refuses aliases at the
admission boundary; THIS instrument moves the check EARLIER — to
evidence CLASSIFICATION time, where every frozen record's citation
identity is typed before any mechanism construction sees it.

Deterministic core (zero LLM, Art. 1 — same bytes in, same verdict
out; no wall clock, no hash-order dependence):
  1. SCHEME normalization — https://doi.org/, dx.doi.org/, doi:
     prefixes stripped; lowercase; whitespace collapsed.
  2. SHAPE validation — a DOI must match ^10\\.\\d{4,9}/\\S+$; a
     malformed id is FORGED_ID (fail closed).
  3. ALIAS detection — known synthetic alias prefixes (lean_, and the
     extensible ALIAS_PREFIXES family) are typed ALIAS_IDENTITY with
     the de-aliased candidate recorded for the ledger (detection only;
     admission refuses the alias outright).
  4. TITLE consistency — the record's own title must be present and
     fuzzy-match its own citation context (SequenceMatcher on folded
     tokens — deterministic): < 0.50 FORGED_ID (the bytes do not
     belong to the name), 0.50-0.85 AMBIGUOUS_TITLE, >= 0.85 matches.
  5. Optional legs (the [[25]] pattern): a registry_lookup callable
     (Crossref/OpenAlex exact+fuzzy) and an llm_arbiter callable,
     consulted only in the AMBIGUOUS band; absent legs leave the
     verdict typed UNRESOLVED_ARBITER — unknown stays unknown
     (Art. XXV), never silently resolved.
"""
from __future__ import annotations

import difflib
import re
from typing import Any, Callable, Dict, Optional

# the R138-era synthetic alias family + room for future ones; a new
# prefix is ADDED to this list with its catch logged in the ledger
ALIAS_PREFIXES = ("lean_", "doied_", "ref_")

_DOI_SHAPE = re.compile(r"^10\.\d{4,9}/\S+$")

# the identity bands (the fuzzy leg of the [[25]] pattern)
_STRONG_MATCH = 0.85
_WEAK_MATCH = 0.50


def normalize_citation_id(evidence_id: str) -> str:
    """Canonical citation-id form: scheme/URL prefixes stripped,
    lowercased, whitespace collapsed. Deterministic."""
    eid = str(evidence_id or "").strip()
    for pref in ("https://doi.org/", "http://doi.org/",
                 "https://dx.doi.org/", "http://dx.doi.org/",
                 "doi:", "DOI:"):
        if eid.lower().startswith(pref.lower()):
            eid = eid[len(pref):]
    return " ".join(eid.split()).lower()


def _fold(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(text or "").lower()))


def title_similarity(cited_title: str, record_title: str) -> float:
    """Deterministic fuzzy title similarity (folded-token
    SequenceMatcher ratio, 0.0-1.0)."""
    a, b = _fold(cited_title), _fold(record_title)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def verify_citation_identity(evidence_id: str,
                             cited_title: str,
                             record_title: str = "",
                             registry_lookup: Optional[Callable[
                                 [str], Optional[Dict[str, Any]]]] = None,
                             llm_arbiter: Optional[Callable[
                                 [str, str, str], Optional[bool]]] = None,
                             ) -> Dict[str, Any]:
    """Type ONE citation's identity. Returns a typed verdict record —
    the verdict is a LABEL for the ledger and downstream gates; only
    CANONICAL_EXACT may ever act as a source identity."""
    eid_raw = str(evidence_id or "")
    eid = normalize_citation_id(eid_raw)

    # 3. alias detection (BEFORE shape — an alias of a well-formed DOI
    # is still an alias, not an identity)
    alias_of = None
    for pref in ALIAS_PREFIXES:
        if eid.startswith(pref):
            alias_of = normalize_citation_id(eid[len(pref):])
            break

    # 2. shape validation
    shape_ok = bool(_DOI_SHAPE.match(eid if not alias_of else alias_of))
    if alias_of:
        return {
            "verdict": "ALIAS_IDENTITY",
            "evidence_id": eid_raw, "normalized_id": eid,
            "alias_prefix": eid[:len(eid) - len(alias_of or "")],
            "de_aliased_candidate": alias_of,
            "shape_ok": shape_ok,
            "title_similarity": None,
            "note": ("synthetic alias detected at classification time; "
                     "admission refuses aliases outright (R139S3)")}

    if not eid or not shape_ok:
        return {
            "verdict": "FORGED_ID",
            "evidence_id": eid_raw, "normalized_id": eid,
            "shape_ok": False, "title_similarity": None,
            "note": ("the id is not a well-formed DOI — a malformed "
                     "citation can never prove source identity")}

    sim = title_similarity(cited_title, record_title)
    if not _fold(cited_title) or not _fold(record_title):
        # a missing title is an INCOMPLETE record, not a forged one —
        # unknown stays unknown (Art. XXV), never a fabricated refusal
        return {
            "verdict": "MISSING_TITLE",
            "evidence_id": eid_raw, "normalized_id": eid,
            "shape_ok": True, "title_similarity": None,
            "arbiter_consulted": None,
            "note": ("the id is well-formed but a title leg is absent "
                     "— the fuzzy identity check cannot run; type the "
                     "record incomplete instead of guessing")}
    if sim < _WEAK_MATCH:
        verdict, arbiter = "FORGED_ID", None
    elif sim < _STRONG_MATCH:
        # the AMBIGUOUS band — the optional legs decide; absent legs
        # leave it typed unknown (never silently resolved)
        verdict, arbiter = "AMBIGUOUS_TITLE", False
        if registry_lookup is not None:
            try:
                reg = registry_lookup(eid)
                arbiter = bool(reg)
                if arbiter:
                    verdict = "REGISTRY_RESOLVED"
            except Exception:
                arbiter = None
        if verdict == "AMBIGUOUS_TITLE" and llm_arbiter is not None:
            try:
                ok = llm_arbiter(eid, cited_title, record_title)
                arbiter = ok
                if ok:
                    verdict = "ARBITER_RESOLVED"
                else:
                    verdict = "ARBITER_REFUSED"
            except Exception:
                arbiter = None
        if verdict == "AMBIGUOUS_TITLE":
            return {
                "verdict": "UNRESOLVED_ARBITER",
                "evidence_id": eid_raw, "normalized_id": eid,
                "shape_ok": True, "title_similarity": round(sim, 4),
                "arbiter_consulted": arbiter,
                "note": ("title identity in the ambiguous band and no "
                         "arbiter leg resolved it — unknown stays "
                         "unknown (Art. XXV)")}
    else:
        verdict, arbiter = "CANONICAL_EXACT", None
    return {
        "verdict": verdict,
        "evidence_id": eid_raw, "normalized_id": eid,
        "shape_ok": True, "title_similarity": round(sim, 4),
        "arbiter_consulted": arbiter,
        "note": ("deterministic citation-identity typing (R139 DIR-6, "
                 "the [[25]] class instrument)")}


def classify_record_citation(record: Dict[str, Any]) -> Dict[str, Any]:
    """The classification-time entry: type ONE frozen evidence
    record's own citation identity (its id against its own title —
    self-consistency; the registry/LLM legs stay optional)."""
    return verify_citation_identity(
        record.get("id"), record.get("title"),
        record.get("title") or record.get("citation_context"))
