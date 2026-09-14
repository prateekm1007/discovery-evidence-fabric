"""discovery_fabric/r412/gradient.py — the R412 gradient/recovery
arm's GA pipeline: prompts, parsers, span gates, and stage records
for the POST-SEAL execution (owner directive 2026-09-06, items
4-12).

Every stage has a typed failure state and a recorded reason. Every
LLM proposal is span-grounded or counts as NOTHING:

  GA-1b  operational deficit extraction (LLM proposes with exact
         spans from the RECORDED death reason; deterministic
         verbatim-containment gate verifies; failures are
         EXTRACTION_FAILED -> INCOMPLETE, never invented)
  GA-2   gradient eligibility (deterministic; recovery module)
  GA-3   TVM query (deterministic; NO LLM) — no measured fast-mover
         -> DEAD_AT_TVM_QUERY, the cheapest kill before any
         mechanism writing
  TVM    construction (fabric retrieval per rung + LLM proposals
         with exact spans + deterministic gate); the constructed map
         is SNAPSHOTTED + HASHED + COMMITTED before the first GA-4
         call (Art. XLIV evidence freeze; the v0 snapshot and this
         protocol are sealed pre-run)
  GA-4   capability backcast: outcome -> capability -> technology ->
         physical mechanism -> manufacturing method -> control
         architecture -> materials -> computation -> measurement;
         transfer the CAUSAL MECHANISM, never the industry label
  GA-5   transfer feasibility vs the target constraint (every
         assumption needs a present-day anchor)
  GA-5.5 WHY_NOT_ALREADY_ADOPTED (allowed-findings enum; non-UNKNOWN
         findings require a span-verified record; UNKNOWN blocks
         promotion on the absence claim — the phantom-arbitrage
         guard)
  GA-6   present-day availability test — REUSES the sealed verify
         instrument from the temporal arm UNCHANGED (import, not
         copy) + the availability taxonomy (only AVAILABLE_TODAY
         auto-qualifies for PRESENT_CAPABILITY_REDISCOVERY)
  GA-7   causal-architecture delta verification (recovery module:
         machine-computed delta, structural gate)
  GA-8   fresh collision search + novelty (reuses the temporal arm's
         novelty machinery; the 5-class taxonomy)
  GA-9   fresh attack (reuses the temporal arm's attack machinery;
         the NOT_CALIBRATED caveat travels on every verdict)

No model transport lives in this module: the runner injects
callables (hermetic tests; the sealed runner is the only live
transport user). Transport failures are INCOMPLETE, never REJECTED
(Art. LXI). Zero is an acceptable outcome (Art. LXVIII).
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from .recovery import (  # noqa: F401
    AVAILABLE_TODAY, FUTURE, NEAR_TERM, UNKNOWN,
    PRESENT_CAPABILITY_REDISCOVERY, FUTURE_DEPENDENT,
    UNRESOLVED_AVAILABILITY,
    classify_availability, availability_branch,
    compute_causal_delta, verify_causal_delta, parent_causal_graph,
    verify_why_not_finding, WHY_NOT_ALLOWED_FINDINGS,
    attacker_caveat, build_recovery_funnel,
    verify_population_funnel, FunnelArithmeticError,
    _norm,
)

GRADIENT_VERSION = "R412-GRADIENT-V1"
TVM_VERSION = "R412-TVM-V1"

# ---------------------------------------------------------------------------
# GA-1b — the operational deficit extraction (span-gated)
# ---------------------------------------------------------------------------

DEFICIT_EXTRACTION_PROMPT = """You are extracting the OPERATIONAL capability deficit that killed a rejected technology candidate. This is EVIDENCE RECOVERY from a recorded death, not new adjudication: every field must be grounded in the RECORDED DEATH REASON text below. You may not add facts, values, or causes that are not in that text.

CANDIDATE: {name} ({cid})
DOMAIN: {domain}
RECORDED DEATH REASON (verbatim, immutable): {death_reason}

FROZEN CLASSIFICATION (pre-sealed): axis_class={axis_class}; named_deficit={named_deficit}

Answer in EXACTLY this field-line format (one line per field, no prose outside the fields):

DEFICIT_SPAN: "<verbatim quote from the recorded death reason that names the deficit>"
TARGET_CONSTRAINT: "<verbatim quote of the specific constraint the transfer must attack>"
REQUIRED_VALUE: <the required operating value+unit AS STATED IN THE DEATH REASON, or exactly NOT_STATED>
QUANTIFIED_GAP: <the quantified gap as stated in the death reason, or exactly NOT_STATED>
CAPABILITY_RUNG: <the capability rung name for the Technology Velocity Map, 2-6 words, e.g. "actuation active alignment", "device switching energy", "control oriented modeling", "differential measurement instrumentation">
RUNG_DIRECTION: <up or down — does the required capability improve by increasing or decreasing the rung metric>
FRONTIER_DOMAINS: <comma-separated present-day domains that demonstrably lead on this rung, or exactly UNKNOWN>

Hard rules:
- DEFICIT_SPAN and TARGET_CONSTRAINT must be VERBATIM substrings of the recorded death reason. Paraphrase or invention fails the gate.
- If the death reason states no numeric requirement, REQUIRED_VALUE is exactly NOT_STATED. Never estimate.
- CAPABILITY_RUNG must describe the CAPABILITY, not the industry.
"""


def build_deficit_extraction_prompt(
    candidate: Dict[str, Any], death: Dict[str, Any],
    frozen: Dict[str, Any]) -> str:
    return DEFICIT_EXTRACTION_PROMPT.format(
        name=str(candidate.get("technology_name") or "")[:120],
        cid=str(candidate.get("candidate_id") or ""),
        domain=str(candidate.get("target_domain") or
                   candidate.get("domain_id") or "")[:80],
        death_reason=str(death.get("death_reason") or "")[:900],
        axis_class=str(frozen.get("axis_class") or ""),
        named_deficit=str(frozen.get("named_deficit") or
                          "see death reason"),
    )


DEFICIT_FIELDS = (
    "DEFICIT_SPAN", "TARGET_CONSTRAINT", "REQUIRED_VALUE",
    "QUANTIFIED_GAP", "CAPABILITY_RUNG", "RUNG_DIRECTION",
    "FRONTIER_DOMAINS",
)


def _field_lines(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in (text or "").splitlines():
        m = re.match(r"^([A-Z_0-9]+)\s*:\s*(.*)$", line.strip())
        if m:
            out.setdefault(m.group(1), m.group(2).strip())
    return out


def _strip_quotes(s: str) -> str:
    s = (s or "").strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1]
    return s


def parse_deficit_extraction(text: str) -> Dict[str, Any]:
    fields = _field_lines(text)
    missing = [f for f in DEFICIT_FIELDS if not fields.get(f)]
    return {
        "stage": "GA1B_DEFICIT_EXTRACTION",
        "gradient_version": GRADIENT_VERSION,
        "parse_status": "OK" if not missing else "INCOMPLETE_FIELDS",
        "missing_fields": missing,
        "fields": {f: _strip_quotes(fields.get(f, "")) for f in
                   DEFICIT_FIELDS},
    }


def verify_deficit_extraction(
    extraction: Dict[str, Any], death: Dict[str, Any],
) -> Dict[str, Any]:
    """The GA-1b span gate: DEFICIT_SPAN and TARGET_CONSTRAINT must
    be verbatim-contained (casefold + whitespace-normalized) in the
    RECORDED death reason. Numeric fields must be quoted-or-
    NOT_STATED. A failed gate is EXTRACTION_FAILED -> the seed stays
    INCOMPLETE (never invented, never silently eligible)."""
    fields = extraction.get("fields") or {}
    reason_norm = _norm(str(death.get("death_reason") or ""))
    problems: List[str] = []
    if extraction.get("parse_status") != "OK":
        problems.append(f"parse_status={extraction.get('parse_status')}")
    for f in ("DEFICIT_SPAN", "TARGET_CONSTRAINT"):
        span = _norm(str(fields.get(f) or ""))
        if not span or len(span) < 20:
            problems.append(f"{f} too short")
        elif span not in reason_norm:
            problems.append(f"{f} NOT verbatim in the recorded death "
                            f"reason")
    rung = str(fields.get("CAPABILITY_RUNG") or "").strip()
    if not rung or rung.casefold() == "unknown":
        problems.append("CAPABILITY_RUNG missing or UNKNOWN")
    direction = str(fields.get("RUNG_DIRECTION") or "").strip().lower()
    if direction not in ("up", "down"):
        problems.append(f"RUNG_DIRECTION invalid: {direction!r}")
    for f in ("REQUIRED_VALUE", "QUANTIFIED_GAP"):
        v = str(fields.get(f) or "").strip()
        if not v:
            problems.append(f"{f} missing")
        elif v == "NOT_STATED":
            continue
        elif not re.search(r"\d", v):
            problems.append(f"{f} neither numeric nor NOT_STATED")
    ok = not problems
    return {
        "stage": "GA1B_SPAN_GATE",
        "gate": "PASS" if ok else "FAIL",
        "status": "OK" if ok else "EXTRACTION_FAILED",
        "problems": problems,
        "capability_rung": rung if ok else None,
        "rung_direction": direction if ok else None,
        "required_value": str(fields.get("REQUIRED_VALUE") or ""),
        "quantified_gap": str(fields.get("QUANTIFIED_GAP") or ""),
        "deficit_span": str(fields.get("DEFICIT_SPAN") or ""),
        "target_constraint": str(fields.get("TARGET_CONSTRAINT") or ""),
        "frontier_domains": str(
            fields.get("FRONTIER_DOMAINS") or "UNKNOWN"),
        "note": ("span-grounded evidence recovery; failures are "
                 "INCOMPLETE and never adjudicated into existence"),
    }


# ---------------------------------------------------------------------------
# TVM — the Technology Velocity Map (evidence-native)
# ---------------------------------------------------------------------------

TVM_PROPOSAL_PROMPT = """You are binding MEASURED performance-trend evidence to a Technology Velocity Map entry. Every number must come from a retrieved record below — you may not assert values.

CAPABILITY RUNG: {rung}
RETRIEVED RECORDS (the ONLY admissible evidence pool):
{record_list}

Answer in EXACTLY this field-line format (one line per entry, up to 8):

ENTRY_1: <domain> | <metric> | <value> | <unit> | <year of the measured value, YYYY> | <record_id> | "<verbatim quote from that record's title+abstract containing the metric and value>"
ENTRY_2: <same format>

Hard rules:
- The span must be a VERBATIM substring of that record's title+abstract. Paraphrase fails the gate.
- The year is the year OF THE MEASURED VALUE as stated in the record, not the publication year, when they differ.
- domain = the application domain of the record, not the journal name.
- Only performance-trend-relevant records; a record with no measured value for the rung yields no entry.
"""


def build_tvm_proposal_prompt(rung: str,
                              records: List[Dict[str, Any]]) -> str:
    lines = []
    for r in records or []:
        lines.append(
            f"- record_id: {r.get('record_id') or r.get('id')} | "
            f"title: {str(r.get('title') or '')[:160]} | "
            f"abstract: {str(r.get('abstract') or
                             r.get('snippet') or '')[:400]}")
    return TVM_PROPOSAL_PROMPT.format(
        rung=rung, record_list="\n".join(lines) or "(no records)")


TVM_ENTRY_PARTS = (
    "domain", "metric", "value", "unit", "year", "record_id", "span",
)


def parse_tvm_entries(text: str) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for i in range(1, 9):
        raw = None
        for line in (text or "").splitlines():
            m = re.match(rf"^ENTRY_{i}\s*:\s*(.*)$", line.strip())
            if m:
                raw = m.group(1).strip()
                break
        if raw is None:
            continue
        parts = [p.strip() for p in raw.split("|")]
        if len(parts) != len(TVM_ENTRY_PARTS):
            entries.append({"slot": f"ENTRY_{i}", "raw": raw[:300],
                            "parse_status": "MALFORMED"})
            continue
        e = dict(zip(TVM_ENTRY_PARTS, parts))
        e["span"] = _strip_quotes(e["span"])
        e["slot"] = f"ENTRY_{i}"
        e["parse_status"] = "OK"
        entries.append(e)
    return entries


def _record_text(r: Dict[str, Any]) -> str:
    return " ".join([str(r.get("title") or ""),
                     str(r.get("abstract") or r.get("snippet") or "")])


def verify_tvm_entries(
    entries: List[Dict[str, Any]],
    retrieved: List[Dict[str, Any]],
    rung: str,
) -> Dict[str, Any]:
    """The TVM construction gate (the R411 F4a instrument pattern):
    every entry's span must be verbatim-contained in the cited
    record's title+abstract within the retrieved pool. Rejected
    entries are recorded, never repaired. Admitted entries carry
    verified_verbatim: true and their source identity."""
    pool_index = {str(r.get("record_id") or r.get("id")): r
                  for r in retrieved or []}
    admitted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for e in entries or []:
        if e.get("parse_status") != "OK":
            rejected.append({**e, "reason": "MALFORMED"})
            continue
        r = pool_index.get(str(e.get("record_id")))
        if r is None:
            rejected.append({**e,
                             "reason": "RECORD_ID_NOT_IN_RETRIEVED_POOL"})
            continue
        span_norm = _norm(str(e.get("span") or ""))
        if not span_norm or len(span_norm) < 20:
            rejected.append({**e, "reason": "SPAN_TOO_SHORT"})
            continue
        if span_norm not in _norm(_record_text(r)):
            rejected.append({**e, "reason": "SPAN_NOT_VERBATIM_IN_RECORD"})
            continue
        try:
            value = float(str(e.get("value")))
            year = int(str(e.get("year")))
        except (TypeError, ValueError):
            rejected.append({**e, "reason": "VALUE_OR_YEAR_NOT_NUMERIC"})
            continue
        admitted.append({
            "capability_rung": rung,
            "domain": str(e.get("domain")),
            "metric": str(e.get("metric")),
            "value": value,
            "unit": str(e.get("unit")),
            "year": year,
            "source": {
                "record_id": str(r.get("record_id") or r.get("id")),
                "citation": str(r.get("title") or "")[:200],
            },
            "provenance": {
                "span": str(e.get("span")),
                "verified_verbatim": True,
            },
            "confidence": "SPAN_VERIFIED",
        })
    return {"admitted": admitted, "rejected": rejected,
            "gate": "the deterministic verbatim-containment gate "
                    "(R411 F4a pattern); rejected entries count as "
                    "nothing"}


def tvm_slopes(tvm: Dict[str, Any],
               rung: str) -> List[Dict[str, Any]]:
    """Measured slopes per domain on one rung. A slope requires >= 2
    admitted entries from the SAME domain with the SAME metric+unit
    at different years (movement must be measured, not asserted).
    Ranking is by max |slope| — the steepest measured mover first
    (the search-order policy; v0 records direction rather than
    adjudicating it, which is the backcast's job)."""
    by_domain: Dict[str, List[Dict[str, Any]]] = {}
    for e in tvm.get("entries") or []:
        if str(e.get("capability_rung")) == rung:
            by_domain.setdefault(str(e.get("domain")), []).append(e)
    out: List[Dict[str, Any]] = []
    for domain, entries in by_domain.items():
        by_metric: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        for e in entries:
            by_metric.setdefault(
                (str(e.get("metric")), str(e.get("unit"))), []).append(e)
        best: Optional[Dict[str, Any]] = None
        for (metric, unit), pts in by_metric.items():
            pts = sorted(pts, key=lambda p: p.get("year") or 0)
            for a, b in zip(pts, pts[1:]):
                dy = (b.get("year") or 0) - (a.get("year") or 0)
                if dy <= 0:
                    continue
                slope = (b.get("value") - a.get("value")) / dy
                rec = {
                    "domain": domain, "metric": metric, "unit": unit,
                    "slope": round(slope, 6),
                    "abs_slope": round(abs(slope), 6),
                    "from": {"year": a.get("year"),
                             "value": a.get("value")},
                    "to": {"year": b.get("year"),
                           "value": b.get("value")},
                    "source_record_ids": [
                        a.get("source", {}).get("record_id"),
                        b.get("source", {}).get("record_id")],
                }
                if best is None or rec["abs_slope"] > best["abs_slope"]:
                    best = rec
        if best is not None:
            out.append(best)
    out.sort(key=lambda r: -r["abs_slope"])
    return out


def query_tvm(tvm: Dict[str, Any],
              rung: str) -> Dict[str, Any]:
    """GA-3 (deterministic, NO LLM): rank measured fast-movers on the
    required capability rung. No measured fast-mover ->
    DEAD_AT_TVM_QUERY — the cheapest kill (fabric calls only, no
    mechanism writing)."""
    slopes = tvm_slopes(tvm, rung)
    if not slopes:
        return {
            "stage": "GA3_TVM_QUERY",
            "rung": rung,
            "verdict": "DEAD_AT_TVM_QUERY",
            "reason": ("no measured fast-mover on this rung: no "
                       "domain has >= 2 span-verified entries with "
                       "the same metric+unit at different years — "
                       "movement is not measured, so there is "
                       "nothing to transfer"),
            "n_entries_on_rung": sum(
                1 for e in tvm.get("entries") or []
                if str(e.get("capability_rung")) == rung),
        }
    return {
        "stage": "GA3_TVM_QUERY",
        "rung": rung,
        "verdict": "FAST_MOVERS_RANKED",
        "ranked": slopes,
        "search_order_policy": (
            "steepest measured slope first (a policy over the ranked "
            "map, never a hard-coded belief about industries)"),
    }


def build_tvm_snapshot(tvm: Dict[str, Any]) -> Dict[str, Any]:
    """The Art. XLIV freeze: the constructed map is snapshotted,
    hashed, and committed BEFORE the first GA-4 call. No TVM edits
    after the snapshot (a new map is a NEW snapshot + new freeze)."""
    payload = json_dumps(tvm)
    return {
        "tvm_version": TVM_VERSION,
        "entries": tvm.get("entries") or [],
        "n_entries": len(tvm.get("entries") or []),
        "sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "frozen_before_ga4": True,
        "freeze_rule": (
            "the TVM snapshot + sha256 are committed before the "
            "first GA-4 backcast call; no after-the-fact entry edits "
            "(Art. XLIV; a changed map is a new snapshot + new "
            "freeze + new epistemic version)"),
    }


def json_dumps(obj: Any) -> str:
    import json as _json
    return _json.dumps(obj, sort_keys=True)


# ---------------------------------------------------------------------------
# GA-4 — the capability backcast (frontier-to-laggard transfer)
# ---------------------------------------------------------------------------

BACKCAST_PROMPT = """Assume the year is 2055. You are a rigorous engineering scientist. A technology was REJECTED in 2026 for a recorded capability deficit. A PRESENT-DAY frontier domain already has the capability it lacked. Construct the descendant by transferring the CAUSAL MECHANISM from the frontier to the laggard target — never the industry label.

REJECTED SEED (2026):
- name: {name} | domain: {domain}
- problem: {problem}
- recorded causal chain: {causal_chain}
- intervention: {intervention}
- predicted effect: {predicted}

RECORDED CAUSE OF DEATH (verbatim, immutable): {death_reason}

THE CAPABILITY DEFICIT (recovered, span-grounded): {deficit}
REQUIRED OPERATING VALUE: {required_value}
TVM-RANKED FRONTIER CANDIDATES (measured movers on the rung): {frontier}

Answer in EXACTLY this field-line format:

OUTCOME: <the outcome the descendant delivers>
CAPABILITY: <the transferred capability>
TECHNOLOGY: <the concrete technology carrying it>
PHYSICAL_MECHANISM: <the physical mechanism, one sentence>
MANUFACTURING_METHOD: <how the descendant is manufactured>
CONTROL_ARCHITECTURE: <how it is controlled>
MATERIALS: <the materials>
COMPUTATION: <the computation involved>
MEASUREMENT: <how the effect is measured>
PARENT_NODE_1: <verbatim one step from the seed's recorded causal chain>
PARENT_NODE_2: <next recorded step, same format; repeat lines as needed>
PARENT_EDGE_1: <node number> -> <node number>
DESC_NODE_1: <descendant causal node 1>
DESC_NODE_2: <descendant causal node 2; repeat as needed>
DESC_EDGE_1: <node number> -> <node number>
NEW_INTERACTION: <the causal relationship that exists in the descendant but NOT in the parent — name the nodes it connects>
PREDICTED_NEW_EFFECT: <the new effect this relationship produces, with units>
MEASUREMENT_PLAN: <how the new effect is measured>
CAPABILITY_1: <the transferred capability name> | <required value + unit in the target domain> | <essential today: yes or no>
CAPABILITY_2: <second capability, same format; up to 3 lines; omit if none>
KILL_CONDITION: <the experimental outcome that kills the descendant>
CAPABILITY_SOURCE_SPAN: "<verbatim quote from the frontier candidate entries or the recorded death reason that grounds the transferred capability>"

Hard rules:
- Transfer the CAUSAL MECHANISM, never the industry label: "apply domain X's approach" is invalid; state the mechanism.
- PARENT_NODE lines must be VERBATIM steps of the recorded causal chain. Invention fails the gate.
- NEW_INTERACTION must connect at least one node that does not exist in the parent. "Better sensor", "faster processor", "different material", or "new industry" alone is INSUFFICIENT — state the new causal relationship.
- If the frontier candidates do not actually carry the required capability, say so in NEW_INTERACTION with the word INSUFFICIENT_FRONTIER and stop.
"""


def build_backcast_prompt(
    candidate: Dict[str, Any], death: Dict[str, Any],
    deficit: Dict[str, Any], tvm_query: Dict[str, Any],
) -> str:
    chain = " -> ".join(str(s) for s in
                        candidate.get("causal_chain") or [])[:500]
    ranked = tvm_query.get("ranked") or []
    frontier = "; ".join(
        f"{r.get('domain')} ({r.get('metric')} {r.get('slope')} "
        f"{r.get('unit')}/yr)" for r in ranked[:5]) or \
        "(no ranked movers)"
    return BACKCAST_PROMPT.format(
        name=str(candidate.get("technology_name") or "")[:120],
        domain=str(candidate.get("target_domain") or
                   candidate.get("domain_id") or "")[:80],
        problem=str(candidate.get("problem") or "")[:300],
        causal_chain=chain,
        intervention=str(candidate.get("intervention") or "")[:300],
        predicted=str(candidate.get("predicted_effect") or "")[:250],
        death_reason=str(death.get("death_reason") or "")[:600],
        deficit=str(deficit.get("deficit_span") or
                    deficit.get("named_deficit") or "")[:300],
        required_value=str(deficit.get("required_value") or
                           "NOT_STATED")[:120],
        frontier=frontier[:600],
    )


BACKCAST_FIELDS = (
    "OUTCOME", "CAPABILITY", "TECHNOLOGY", "PHYSICAL_MECHANISM",
    "MANUFACTURING_METHOD", "CONTROL_ARCHITECTURE", "MATERIALS",
    "COMPUTATION", "MEASUREMENT", "NEW_INTERACTION",
    "PREDICTED_NEW_EFFECT", "MEASUREMENT_PLAN", "KILL_CONDITION",
    "CAPABILITY_SOURCE_SPAN",
)

CAPABILITY_LINE_PARTS = ("name", "required_value", "essential_today")


def _parse_capability_lines(
        fields: Dict[str, str]) -> List[Dict[str, Any]]:
    caps: List[Dict[str, Any]] = []
    for i in range(1, 4):
        raw = fields.get(f"CAPABILITY_{i}")
        if not raw:
            continue
        parts = [p.strip() for p in raw.split("|")]
        if len(parts) != len(CAPABILITY_LINE_PARTS):
            caps.append({"slot": f"CAPABILITY_{i}", "raw": raw[:300],
                         "parse_status": "MALFORMED"})
            continue
        cap = dict(zip(CAPABILITY_LINE_PARTS, parts))
        cap["slot"] = f"CAPABILITY_{i}"
        cap["parse_status"] = "OK"
        caps.append(cap)
    return caps


def parse_backcast(text: str) -> Dict[str, Any]:
    fields = _field_lines(text)
    parent_nodes: List[Dict[str, Any]] = []
    desc_nodes: List[Dict[str, Any]] = []
    parent_edges: List[Dict[str, Any]] = []
    desc_edges: List[Dict[str, Any]] = []
    for i in range(1, 12):
        if fields.get(f"PARENT_NODE_{i}"):
            parent_nodes.append({"id": f"p{i}",
                                 "label": fields[f"PARENT_NODE_{i}"]})
        if fields.get(f"DESC_NODE_{i}"):
            desc_nodes.append({"id": f"d{i}",
                               "label": fields[f"DESC_NODE_{i}"]})
    for i in range(1, 12):
        for prefix, store in (("PARENT_EDGE_", parent_edges),
                              ("DESC_EDGE_", desc_edges)):
            raw = fields.get(f"{prefix}{i}")
            if not raw:
                continue
            m = re.match(r"^(\d+)\s*->\s*(\d+)$", raw.replace(
                "node", "").strip())
            if m:
                store.append({"from": m.group(1), "to": m.group(2),
                              "relation": "causal"})
            else:
                store.append({"from": raw, "to": raw,
                              "relation": "UNPARSED"})
    missing = [f for f in BACKCAST_FIELDS if not fields.get(f)]
    capabilities = _parse_capability_lines(fields)
    insufficient = "INSUFFICIENT_FRONTIER" in str(
        fields.get("NEW_INTERACTION") or "")
    return {
        "stage": "GA4_CAPABILITY_BACKCAST",
        "gradient_version": GRADIENT_VERSION,
        "parse_status": ("INSUFFICIENT_FRONTIER" if insufficient else
                         "OK" if not missing and desc_nodes and
                         desc_edges and capabilities else
                         "INCOMPLETE_FIELDS" if missing else
                         "NO_GRAPH"),
        "missing_fields": missing,
        "fields": {f: _strip_quotes(fields.get(f, "")) for f in
                   BACKCAST_FIELDS},
        "capabilities": capabilities,
        "parent_graph": {"nodes": parent_nodes, "edges": parent_edges},
        "descendant_graph": {"nodes": desc_nodes, "edges": desc_edges},
    }


def verify_backcast(
    backcast: Dict[str, Any], candidate: Dict[str, Any],
    deficit: Dict[str, Any],
) -> Dict[str, Any]:
    """The GA-4 gates: (a) the PARENT graph must be verbatim-grounded
    in the seed's recorded causal chain (the parent graph is READ
    from the record — proposals that invent parent steps fail); (b)
    the capability source span must be verbatim in the recorded
    death reason or the deficit span; (c) INSUFFICIENT_FRONTIER is an
    honest terminal finding, not a failure. The causal delta itself
    is verified at GA-7 by the machine-computed gate."""
    if backcast.get("parse_status") == "INSUFFICIENT_FRONTIER":
        return {
            "stage": "GA4_VERIFY", "gate": "HONEST_STOP",
            "verdict": "INSUFFICIENT_FRONTIER",
            "note": ("the backcast honestly reports the ranked "
                     "frontier does not carry the required "
                     "capability; recorded, no descendant built"),
        }
    problems: List[str] = []
    if backcast.get("parse_status") != "OK":
        problems.append(f"parse_status={backcast.get('parse_status')}")
    chain_text = _norm(" -> ".join(str(s) for s in
                                   candidate.get("causal_chain") or []))
    chain_steps = [_norm(str(s)) for s in
                   candidate.get("causal_chain") or [] if
                   str(s).strip()]
    for n in (backcast.get("parent_graph") or {}).get("nodes") or []:
        label = _norm(str(n.get("label") or ""))
        if not label:
            continue
        if label not in chain_steps and label not in chain_text:
            problems.append(
                f"parent node not verbatim in the recorded causal "
                f"chain: {n.get('label')!r}")
    cap_span = _norm(str((backcast.get("fields") or {}).get(
        "CAPABILITY_SOURCE_SPAN") or ""))
    source_norms = [chain_text, _norm(str(deficit.get(
        "deficit_span") or "")), _norm(str(deficit.get(
        "target_constraint") or ""))]
    if not cap_span or len(cap_span) < 20 or not any(
            cap_span in s for s in source_norms if s):
        problems.append(
            "CAPABILITY_SOURCE_SPAN not verbatim in the recorded "
            "chain/death material")
    return {
        "stage": "GA4_VERIFY",
        "gate": "PASS" if not problems else "FAIL",
        "problems": problems,
        "note": ("parent graph verbatim-grounded in the recorded "
                 "causal chain; capability source span-grounded; the "
                 "causal-architecture delta is machine-verified at "
                 "GA-7"),
    }


# ---------------------------------------------------------------------------
# GA-5 — transfer feasibility (assumptions need present-day anchors)
# ---------------------------------------------------------------------------

FEASIBILITY_PROMPT = """Assess the transfer feasibility of this descendant against the target constraint. Every required assumption must carry a present-day anchor (a retrieved record that demonstrates the assumption's capability TODAY) or be honestly marked UNANCHORED.

DESCENDANT: {outcome}
TARGET CONSTRAINT (verbatim): {constraint}
MECHANISM: {mechanism}

Answer in EXACTLY this field-line format:

ASSUMPTION_1: <the assumption> | <record_id of the anchor, or exactly UNANCHORED>
ASSUMPTION_2: <same format; up to 4 lines>
FEASIBILITY_VERDICT: FEASIBLE_TODAY | FEASIBLE_WITH_UNANCHORED_ASSUMPTIONS | INFEASIBLE
BLOCKING_REASON: <the single most dangerous unanchored assumption, or NONE>

Hard rules:
- A record_id anchor must be a record from the retrieved set used in this stage.
- Never invent record ids. If no record supports the assumption, write UNANCHORED.
"""


def build_feasibility_prompt(backcast: Dict[str, Any],
                             deficit: Dict[str, Any]) -> str:
    f = backcast.get("fields") or {}
    return FEASIBILITY_PROMPT.format(
        outcome=str(f.get("OUTCOME") or "")[:200],
        constraint=str(deficit.get("target_constraint") or
                       deficit.get("deficit_span") or "")[:300],
        mechanism=str(f.get("PHYSICAL_MECHANISM") or "")[:300],
    )


def parse_feasibility(text: str) -> Dict[str, Any]:
    fields = _field_lines(text)
    assumptions: List[Dict[str, Any]] = []
    for i in range(1, 5):
        raw = fields.get(f"ASSUMPTION_{i}")
        if not raw:
            continue
        parts = [p.strip() for p in raw.split("|")]
        if len(parts) == 2:
            assumptions.append({"assumption": parts[0],
                                "anchor": parts[1]})
        else:
            assumptions.append({"assumption": raw[:200],
                                "anchor": "MALFORMED"})
    verdict = str(fields.get("FEASIBILITY_VERDICT") or "").strip()
    return {
        "stage": "GA5_TRANSFER_FEASIBILITY",
        "assumptions": assumptions,
        "feasibility_verdict": verdict if verdict in (
            "FEASIBLE_TODAY", "FEASIBLE_WITH_UNANCHORED_ASSUMPTIONS",
            "INFEASIBLE") else "MALFORMED",
        "blocking_reason": str(
            fields.get("BLOCKING_REASON") or "NONE")[:300],
        "parse_status": "OK" if assumptions and verdict else
                        "INCOMPLETE_FIELDS",
    }


def verify_feasibility(
    feasibility: Dict[str, Any],
    anchored_record_ids: List[str],
) -> Dict[str, Any]:
    """The GA-5 gate: every anchor must point at a record from the
    retrieved set (present-day anchor). Unanchored assumptions are
    recorded; promotion with unanchored assumptions is blocked (Art.
    XLVI: a mechanism transferred is not novel merely because the
    domain changed — and an unanchored assumption is unproven)."""
    valid = {str(r) for r in anchored_record_ids or []}
    anchored, unanchored = [], []
    for a in feasibility.get("assumptions") or []:
        anchor = str(a.get("anchor") or "")
        if anchor in valid:
            anchored.append({**a, "anchor_status": "ANCHORED"})
        else:
            unanchored.append({**a, "anchor_status": "UNANCHORED"})
    blocked = bool(unanchored)
    return {
        "stage": "GA5_GATE",
        "anchored": anchored,
        "unanchored": unanchored,
        "promotion_allowed": not blocked,
        "verdict": ("FEASIBLE_TODAY" if anchored and not unanchored
                    else "FEASIBLE_WITH_UNANCHORED_ASSUMPTIONS"
                    if anchored else "NO_ANCHORED_ASSUMPTIONS"),
        "note": ("each assumption needs a present-day anchor; "
                 "unanchored assumptions block promotion and are "
                 "recorded, never repaired"),
    }


# ---------------------------------------------------------------------------
# GA-5.5 — WHY_NOT_ALREADY_ADOPTED
# ---------------------------------------------------------------------------

WHY_NOT_PROMPT = """Investigate why this transferred capability has NOT already been adopted in the target domain. The discovery target is not mere technology transfer — it is transfer that reveals an OVERLOOKED CAUSAL ARCHITECTURE. If the absence is not evidenced, the answer is UNKNOWN.

TARGET DOMAIN: {domain}
TRANSFERRED CAPABILITY: {capability}
TARGET-DOMAIN RECORDS (the evidence pool for the absence claim):
{record_list}

Allowed findings (choose exactly one):
disciplinary_silo, missing_measurement, manufacturing_constraint, integration_complexity, economic_constraint, environmental_mismatch, control_mismatch, historical_path_dependence, overlooked_interaction, UNKNOWN

Answer in EXACTLY this field-line format:

FINDING: <one allowed finding>
RECORD_ID: <the target-domain record that names the limitation WITHOUT the imported capability, or exactly NONE>
SPAN: "<verbatim quote from that record naming the limitation, or exactly NONE>"

Hard rules:
- A non-UNKNOWN finding REQUIRES a verbatim span from a retrieved target-domain record. No record -> UNKNOWN.
- UNKNOWN is an honest answer; it blocks promotion on the absence claim (phantom-arbitrage guard).
"""


def build_why_not_prompt(
    domain: str, capability: str,
    records: List[Dict[str, Any]]) -> str:
    lines = []
    for r in records or []:
        lines.append(
            f"- record_id: {r.get('record_id') or r.get('id')} | "
            f"title: {str(r.get('title') or '')[:160]} | "
            f"abstract: {str(r.get('abstract') or
                             r.get('snippet') or '')[:400]}")
    return WHY_NOT_PROMPT.format(
        domain=str(domain)[:80], capability=str(capability)[:200],
        record_list="\n".join(lines) or "(no records)")


def parse_why_not(text: str) -> Dict[str, Any]:
    fields = _field_lines(text)
    return {
        "stage": "GA5P5_WHY_NOT_ALREADY_ADOPTED",
        "finding": str(fields.get("FINDING") or "").strip(),
        "record_id": str(fields.get("RECORD_ID") or "").strip(),
        "span": _strip_quotes(str(fields.get("SPAN") or "")),
        "allowed_findings": list(WHY_NOT_ALLOWED_FINDINGS),
        "parse_status": "OK" if fields.get("FINDING") else
                        "INCOMPLETE_FIELDS",
    }


def verify_why_not(
    parsed: Dict[str, Any],
    retrieved: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """GA-5.5 gate: reuse recovery.verify_why_not_finding; UNKNOWN
    blocks promotion (the absence claim must be evidenced)."""
    gate = verify_why_not_finding(
        parsed.get("finding"), parsed.get("record_id"),
        parsed.get("span"), retrieved)
    return {
        "stage": "GA5P5_GATE",
        **gate,
        "promotion_allowed": gate.get("admitted") and
        gate.get("finding") != "UNKNOWN",
        "note": ("absence-of-adoption must be evidenced by a "
                 "target-domain record naming the limitation without "
                 "the imported capability; UNKNOWN cannot promote "
                 "(phantom-arbitrage guard, directive item 9)"),
    }


# ---------------------------------------------------------------------------
# GA-6 — the present-day availability test (reuses the sealed
# verify instrument UNCHANGED)
# ---------------------------------------------------------------------------

def verify_instrument():
    """The sealed verify instrument, imported from the temporal arm
    and REUSED unchanged (import, never a copy — Art. LXIV)."""
    from .temporal_pipeline import verify_capability
    return verify_capability


def availability_map(
    capabilities: List[Dict[str, Any]],
    decomposition_rows: List[Dict[str, Any]],
    verifications: List[Dict[str, Any]],
) -> Dict[str, str]:
    """The availability taxonomy over the descendant's essential
    capabilities (directive item 7)."""
    row_by_name = {}
    for r in decomposition_rows or []:
        if r.get("parse_status") in (None, "OK"):
            row_by_name[str(r.get("name") or "").casefold()] = r
    ver_by_name = {str(v.get("capability")): v
                   for v in verifications or []}
    out: Dict[str, str] = {}
    for cap in capabilities or []:
        name = str(cap.get("name") or "")
        key = name.casefold()
        row = row_by_name.get(key)
        if row is None:
            for k, v in row_by_name.items():
                if key in k or k in key:
                    row = v
                    break
        ver = ver_by_name.get(name)
        if ver is None:
            # no verification record: an UNVERIFIED claim is UNKNOWN
            out[name] = UNKNOWN
            continue
        out[name] = classify_availability(ver, row)
    return out


# ---------------------------------------------------------------------------
# The stage record + the fail-closed seal check
# ---------------------------------------------------------------------------

def gradient_stage_record(
    stage: str, seed_id: str, payload: Dict[str, Any],
    model: Optional[str] = None,
) -> Dict[str, Any]:
    rec = {
        "stage": stage,
        "seed_candidate_id": seed_id,
        "gradient_version": GRADIENT_VERSION,
        "reviewer_provenance": "AI_REVIEW",
        **payload,
    }
    if model:
        rec["model"] = model
    return rec


SEAL_REQUIRED_PATHS = (
    ("artifact_type",),
    ("population", "population_sha256"),
    ("tvm_v0", "sha256"),
    ("model_versions",),
    ("prompts",),
    ("token_and_cost_budgets",),
    ("stopping_rules",),
    ("resource_allocation",),
    ("headline_schema",),
)


def verify_seal(prereg: Dict[str, Any]) -> Dict[str, Any]:
    """The fail-closed seal check the RUNNER must pass before ANY
    gradient model call: every pre-registered element present
    (machinery, schemas, preregistration, population hash, TVM
    snapshot hash, prompts/model identifiers, budget, stopping
    rules). A missing element refuses the run — no after-the-fact
    changes (directive item 11)."""
    missing = []
    for path in SEAL_REQUIRED_PATHS:
        node: Any = prereg
        for key in path:
            if not isinstance(node, dict) or key not in node:
                missing.append(".".join(path))
                node = None
                break
            node = node[key]
    return {
        "seal_valid": not missing,
        "missing": missing,
        "action": "REFUSE_RUN" if missing else "RUN_ALLOWED",
    }
