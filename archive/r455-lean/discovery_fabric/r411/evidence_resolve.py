"""discovery_fabric/r411/evidence_resolve.py — F4a: verifier-side
evidence resolution (Art. II / III / XXI.4).

WHY THIS EXISTS (mid-run implementation correction, disclosed in the run
record): the frozen scoring contract measures evidence_strength as
"number AND family-independence of fabric evidence records backing the
mechanism claims". The original implementation counted the GENERATOR's
self-citations (candidate.evidence_refs) — the claimant defining what
its evidence says, which Art. III forbids, and Art. XXI.4 requires
independent relevance adjudication recorded in the custody chain.

This module resolves evidence the constitutionally correct way:
  1. an LLM call (untrusted proposer, SEPARATE_CONTEXT_ONLY — never
     labelled independent) receives the candidate's claims and the
     FROZEN pool records, and proposes claim -> record bindings with
     EXACT QUOTED SPANS from the record text;
  2. a DETERMINISTIC gate verifies every span is verbatim-contained in
     the record's title+abstract (casefold + whitespace-normalized);
     any span that fails verification is REJECTED and recorded, never
     repaired (Art. IV / VII);
  3. the resolved evidence set (distinct verified records + source
     families) feeds the SAME frozen anchor ladder and the SAME
     evidence floor — the measurement gets strictly STRONGER
     (self-citations that do not verify now count as nothing), never
     weaker.

Art. XLIV (evidence boundary): only the frozen per-domain pool is
read; no new retrieval happens in this stage.

The LLM may propose bindings; only the machine gate admits them.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

EVIDENCE_RESOLVE_VERSION = "R411-EVIDENCE-RESOLVE-V1"

# Deterministic claim set derived from the candidate record (s10-C major
# claims). Each maps to a candidate field; the proposer must bind or
# mark UNBOUND.
CLAIM_FIELDS = [
    ("PROBLEM_EXISTS", "problem"),
    ("PHENOMENON", "unexploited_phenomenon"),
    ("BASELINE_LIMITATION", "baseline_incumbent"),
    ("MAGNITUDE_PHYSICS", "predicted_effect"),
]

# how much record text the proposer sees (prefix cut — a span quoted
# from the shown prefix is verbatim in the full text, so the gate can
# verify against the full title+abstract)
ABSTRACT_CHARS = 700
MAX_RECORDS = 28

RESOLVE_PROMPT = """You are an evidence-verification instrument inside an engineering discovery engine. You are NOT judging whether the technology is good. Your ONLY job: for each CLAIM below, find which RECORDS state the supporting fact, and quote the EXACT words.

CANDIDATE CLAIMS (from a technology candidate extracted from this pool):
{claims}

EVIDENCE POOL (frozen retrieval snapshot; RECORD_IDs and their title + abstract text):
{records}

TASK: For EACH claim, in order, either bind it to records that STATE the supporting fact, or mark it UNBOUND.

RULES:
- A binding is only valid if the record text STATES the fact. Similar topic is NOT enough.
- The SPAN must be an EXACT VERBATIM quote copied character-for-character from that record's title or abstract shown above (10-60 words). No paraphrase, no ellipsis, no invented text.
- You may bind one claim to multiple records; you may use a record for multiple claims.
- If NO record states the fact, output UNBOUND for that claim. UNBOUND is a valid, expected answer — do not force weak bindings.
- Only use RECORD_IDs that appear above. NEVER invent record ids.

OUTPUT FORMAT — plain text, no markdown, exactly this structure per claim:
CLAIM: PROBLEM_EXISTS
RECORD: <record_id>
SPAN: "<verbatim quote>"
RECORD: <record_id>
SPAN: "<verbatim quote>"
CLAIM: PHENOMENON
RECORD: <record_id>
SPAN: "<verbatim quote>"
CLAIM: BASELINE_LIMITATION
UNBOUND
CLAIM: MAGNITUDE_PHYSICS
RECORD: <record_id>
SPAN: "<verbatim quote>"
(every claim in the order given; each either RECORD/SPAN lines or a single UNBOUND line)
"""


def _normalize(s: str) -> str:
    """Casefold + collapse all whitespace for verbatim-containment."""
    return re.sub(r"\s+", " ", s or "").casefold().strip()


def _record_text(r: Dict[str, Any]) -> str:
    return " ".join(str(r.get("title") or "") + " " +
                    str(r.get("abstract") or r.get("snippet") or "")
                    for _ in [0])  # title + abstract single blob


def build_resolve_prompt(candidate: Dict[str, Any],
                         pool: List[Dict[str, Any]]) -> str:
    claims = []
    for label, field in CLAIM_FIELDS:
        if field == "baseline_incumbent":
            val = (candidate.get("baseline") or {}).get(
                "baseline_incumbent") or ""
        else:
            val = candidate.get(field) or ""
        claims.append(f"{label}: {str(val)[:400]}")
    records = []
    for r in pool[:MAX_RECORDS]:
        rid = r.get("record_id") or r.get("id")
        title = str(r.get("title") or "")[:200]
        abstract = str(r.get("abstract") or
                       r.get("snippet") or "")[:ABSTRACT_CHARS]
        records.append(f"RECORD_ID: {rid}\nTITLE: {title}\n"
                       f"ABSTRACT: {abstract}")
    return RESOLVE_PROMPT.format(
        claims="\n".join(claims),
        records="\n\n".join(records))


# ---------------------------------------------------------------------------
# Deterministic parser + span gate
# ---------------------------------------------------------------------------

_CLAIM_LINE = re.compile(r"^CLAIM:\s*([A-Z_]+)\s*$", re.MULTILINE)
_REC_LINE = re.compile(r"^RECORD:\s*(.+?)\s*$", re.MULTILINE)
_SPAN_LINE = re.compile(r'^SPAN:\s*"?([^"\n]+)"?\s*$', re.MULTILINE)
_UNBOUND_LINE = re.compile(r"^UNBOUND\s*$", re.MULTILINE)


def parse_bindings(text: str) -> Dict[str, Any]:
    """Parse the proposer output into per-claim record/span proposals.
    Deterministic; malformed lines are recorded as parse_failures,
    never guessed."""
    claims_seen: List[str] = []
    proposals: List[Dict[str, str]] = []
    unbound: List[str] = []
    # walk line by line (the format is line-structured)
    current_claim: Optional[str] = None
    pending_record: Optional[str] = None
    failures: List[str] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _CLAIM_LINE.match(line)
        if m:
            current_claim = m.group(1)
            if current_claim not in claims_seen:
                claims_seen.append(current_claim)
            pending_record = None
            continue
        if current_claim is None:
            failures.append(f"line before any CLAIM: {line[:60]}")
            continue
        if _UNBOUND_LINE.match(line):
            unbound.append(current_claim)
            pending_record = None
            continue
        m = _REC_LINE.match(line)
        if m:
            pending_record = m.group(1).strip()
            continue
        m = _SPAN_LINE.match(line)
        if m and pending_record:
            span = m.group(1).strip().strip('"').strip()
            proposals.append({
                "claim": current_claim,
                "record_id": pending_record,
                "proposed_span": span,
            })
            pending_record = None
            continue
        failures.append(f"unparseable line: {line[:60]}")
    return {
        "claims_seen": claims_seen,
        "proposals": proposals,
        "unbound": unbound,
        "parse_failures": failures,
    }


def verify_spans(proposals: List[Dict[str, str]],
                 pool: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The machine gate: every proposed span must be verbatim-contained
    in that record's title+abstract. Failed spans are rejected with the
    recorded reason; never repaired."""
    pool_index = {str(r.get("record_id") or r.get("id")): r for r in pool}
    verified: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for p in proposals:
        rid = str(p.get("record_id"))
        span = str(p.get("proposed_span"))
        r = pool_index.get(rid)
        if r is None:
            rejected.append({**p, "reason": "RECORD_ID_NOT_IN_FROZEN_POOL"})
            continue
        text_norm = _normalize(_record_text(r))
        span_norm = _normalize(span)
        if not span_norm or len(span_norm) < 20:
            rejected.append({**p, "reason": "SPAN_TOO_SHORT"})
            continue
        if span_norm in text_norm:
            verified.append({
                "claim": p["claim"],
                "record_id": rid,
                "span": span,
                "verification": "VERBATIM_CONTAINED",
            })
        else:
            rejected.append({**p, "reason": "SPAN_NOT_VERBATIM_IN_RECORD"})
    return {"verified": verified, "rejected": rejected}


def resolved_evidence_summary(verified: List[Dict[str, Any]],
                              pool: List[Dict[str, Any]]
                              ) -> Dict[str, Any]:
    """Distinct verified records + source families (the frozen ladder
    inputs), computed from the GATE-VERIFIED set only."""
    pool_index = {str(r.get("record_id") or r.get("id")): r for r in pool}
    records = sorted({v["record_id"] for v in verified})
    families = set()
    for rid in records:
        prov = (pool_index.get(rid) or {}).get("provenance") or {}
        fam = prov.get("source_family") or prov.get("family") or ""
        if fam:
            families.add(fam)
    return {
        "distinct_verified_records": len(records),
        "record_ids": records,
        "source_families": sorted(families),
        "n_source_families": len(families),
        "claims_with_verified_binding": sorted(
            {v["claim"] for v in verified}),
    }


def resolve_evidence(candidate: Dict[str, Any],
                     pool: List[Dict[str, Any]],
                     llm_meta: Dict[str, Any],
                     parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble the F4a record for one candidate from the LLM call meta
    + parsed output. The deterministic gate runs here; nothing from the
    proposer enters the evidence set without passing it."""
    gate = verify_spans(parsed.get("proposals") or [], pool)
    summary = resolved_evidence_summary(gate["verified"], pool)
    return {
        "resolve_version": EVIDENCE_RESOLVE_VERSION,
        "candidate_id": candidate.get("candidate_id"),
        "claims_adjudicated": [c for c, _ in CLAIM_FIELDS],
        "claims_seen_by_parser": parsed.get("claims_seen") or [],
        "verified_bindings": gate["verified"],
        "rejected_bindings": gate["rejected"],
        "unbound_claims": parsed.get("unbound") or [],
        "parse_failures": parsed.get("parse_failures") or [],
        "resolved_evidence": summary,
        "gate": ("deterministic verbatim span containment "
                 "(casefold + whitespace-normalized) against the frozen "
                 "pool title+abstract; rejected spans recorded, never "
                 "repaired (Art. IV/VII)"),
        "proposer_independence": "SEPARATE_CONTEXT_ONLY",
        "proposer_never_labels_itself_independent": (
            "the proposer is the untrusted LLM (Art. XVIII); only the "
            "machine gate admits bindings (Art. XLV)"),
        "llm_call": {
            "purpose": "r411_evidence_resolution",
            "ok": llm_meta.get("ok"),
            "status": llm_meta.get("status"),
            "model": llm_meta.get("model") or llm_meta.get("provider"),
            "prompt_hash": llm_meta.get("prompt_hash"),
            "output_hash": llm_meta.get("output_hash"),
        },
        "pool_sha256": (candidate.get("pool_sha256") or
                        _pool_sha(pool)),
    }


def _pool_sha(pool: List[Dict[str, Any]]) -> str:
    import hashlib
    import json
    return hashlib.sha256(json.dumps(pool, sort_keys=True).encode()
                          ).hexdigest()


def resolved_evidence_strength(ev: Dict[str, Any]) -> int:
    """The SAME frozen anchor ladder, measured on the GATE-VERIFIED set:
    0: none; 1: >=1; 2: >=3; 3: >=3 across >=2 families (or >=5/2);
    4: >=5 across >=3 families. Identical anchors to measure_evidence_
    strength — the input changed (self-cited refs -> verified records),
    the ladder did not."""
    n = (ev.get("resolved_evidence") or {}).get(
        "distinct_verified_records") or 0
    fam = (ev.get("resolved_evidence") or {}).get("n_source_families") or 0
    if n >= 5 and fam >= 3:
        return 4
    if (n >= 5 and fam >= 2) or (n >= 3 and fam >= 2):
        return 3
    if n >= 3:
        return 2
    if n >= 1:
        return 1
    return 0
