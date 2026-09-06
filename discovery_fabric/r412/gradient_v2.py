"""discovery_fabric.r412.gradient_v2 — the TVM v2 instrument
(R412 gradient arm v2: the sealed field-line instrument change).

WHAT CHANGES vs the sealed v1 instrument (and NOTHING else — the
operator's Phase L: same 10 seeds, same budgets, same thresholds):
  * the TVM proposal prompt is the FIELD-LINE format the same
    proposer class demonstrably follows (GA-1b 13/13) instead of the
    v1 pipe-delimited ENTRY format (91% numeric non-compliance);
  * proposals are verified by the v2 deterministic parser +
    evidence contract (lossless canonical values, byte-exact span
    binding, canonical re-derivation, signal policy) instead of the
    v1 float()/int() casts;
  * RAW proposals AND raw LLM output are PERSISTED per construction
    attempt (the v1 instrument's unpersisted-outputs defect — the
    exact gap that made the v1-vs-v2 reparse unmeasurable — is
    fixed forward: the next comparison needs no reconstruction);
  * queries are expanded through the derived capability-family map
    (Phase D/E: evidence-grounded vocabulary first; the LLM-proposed
    frontier_domains are carried as EXPLORATORY search priority,
    never as capability evidence — Phase F).

REUSED UNCHANGED from the sealed v1/gradient machinery: the GA-1b
deficit extractions (committed), GA-2 eligibility (committed), the
backcast/feasibility/why-not/availability/delta/novelty/attack
instruments (imported by the runner from gradient.py /
temporal_pipeline.py / recovery.py).

No LLM participates in ANY verification decision (Art. XVIII).
Deterministic functions throughout.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import sys

REPO = Path(__file__).resolve().parents[2]
V2DIR = REPO / "R412" / "GRADIENT_V2"
sys.path.insert(0, str(V2DIR))

from tvm_v2 import (  # noqa: E402
    CONTEXT_VALUE, CONTEXT_YEAR,
    parse_value_span, CanonicalValue,
    REP_POINT, REP_RANGE, REP_INEQUALITY,
    REP_ORDINAL_QUALITATIVE, REP_NOT_NUMERIC, REP_MALFORMED,
    verify_span_binding, verify_tvm_entry,
    SPAN_VERIFIED, classify_signal, SIGNAL_PRIMARY_TECHNICAL,
    load_family_map, expand_search_vocabulary,
)

TVM_V2_VERSION = "R412-TVM-V2"
GRADIENT_V2_VERSION = "R412-GRADIENT-V2"

FAMILY_MAP_V2 = V2DIR / "CAPABILITY_FAMILY_MAP_V2.json"
PROMPT_TEMPLATE = V2DIR / "PROMPTS" / \
    "TVM_V2_FRONTIER_ENTRY_PROPOSAL.json"


# ---------------------------------------------------------------------------
# Phase E: the family-driven cross-domain query expansion
# ---------------------------------------------------------------------------

def family_for_rung(rung: str,
                    map_path: Path = FAMILY_MAP_V2
                    ) -> Optional[Dict[str, Any]]:
    """Exact-key family lookup for a capability rung (Phase D map).
    A miss returns None (recorded by the caller; NEVER a fuzzy
    guess — Art. XLIII)."""
    data = json.loads(map_path.read_text())
    q = str(rung).strip().lower()
    for f in data.get("families", []):
        if f.get("exact_capability", "").strip().lower() == q:
            return f
    return None


def build_v2_query(rung: str,
                   map_path: Path = FAMILY_MAP_V2
                   ) -> Dict[str, Any]:
    """The deterministic per-rung retrieval query, Phase E: the
    family's EVIDENCE-GROUNDED vocabulary expands the rung (cross-
    domain); the LLM-proposed vocabulary is carried SEPARATELY as
    exploratory priority (Phase F: it may order WHERE to search,
    never qualify WHAT is found)."""
    fam = family_for_rung(rung, map_path)
    if fam is None:
        return {
            "query": f"{rung} performance trend improvement measured "
                     f"benchmark",
            "family": None,
            "evidence_vocabulary": [],
            "exploratory_vocabulary": [],
            "lookup": "FAMILY_MISS_RECORDED (exact-key only; no "
                      "fuzzy match — Art. XLIII)",
        }
    vocab = list(fam.get("search_vocabulary") or [])[:6]
    expl = list(fam.get("search_vocabulary_llm_proposed") or [])[:4]
    base = f"{rung} {' '.join(vocab)}"[:300]
    return {
        "query": base + " measured improvement trend benchmark",
        "family": fam["family_id"],
        "capability_family": fam["capability_family"],
        "measurement_dimension": fam["measurement_dimension"],
        "evidence_vocabulary": vocab,
        "exploratory_vocabulary": expl,
        "exploratory_note": "AI_PROPOSED_EXPLORATORY: search "
                            "priority only; establishes nothing "
                            "(Phase F / Art. XXVIII)",
    }


# ---------------------------------------------------------------------------
# The v2 TVM proposal gate
# ---------------------------------------------------------------------------

def _record_text(r: Dict[str, Any]) -> str:
    return " ".join([str(r.get("title") or ""),
                     str(r.get("abstract") or r.get("snippet")
                         or "")])


def parse_v2_proposals(text: str) -> Dict[str, Any]:
    """Parse the field-line (JSON) proposal array. The v1 ENTRY-line
    regex parser is GONE; a malformed JSON body is a recorded parse
    failure, never a silent empty set."""
    raw = str(text or "").strip()
    # tolerate fenced JSON blocks
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return {"parse_status": "MALFORMED_NO_JSON_ARRAY",
                "proposals": [], "raw": raw[:400]}
    try:
        arr = json.loads(raw[start:end + 1])
    except json.JSONDecodeError as e:
        return {"parse_status": f"MALFORMED_JSON:{str(e)[:80]}",
                "proposals": [], "raw": raw[:400]}
    if not isinstance(arr, list):
        return {"parse_status": "MALFORMED_NOT_ARRAY",
                "proposals": [], "raw": raw[:400]}
    out = []
    for i, p in enumerate(arr):
        if not isinstance(p, dict):
            out.append({"slot": i, "parse_status":
                        "MALFORMED_NOT_OBJECT"})
            continue
        out.append({"slot": i, "parse_status": "OK", **p})
    return {"parse_status": "OK", "proposals": out,
            "raw": raw[:400]}


def _year_canonical(year_str: str) -> Optional[int]:
    """Canonical year from the proposal's year string (point or
    range midpoint, labeled). None when unparseable."""
    cv = parse_value_span(str(year_str), context=CONTEXT_YEAR)
    if cv.representation == "POINT" and cv.year is not None:
        return int(cv.year)
    if cv.representation == "RANGE" and cv.year_min is not None \
            and cv.year_max is not None:
        return int((cv.year_min + cv.year_max) // 2)
    if cv.normalized_value is not None and 1900 < \
            float(cv.normalized_value) < 2100:
        return int(float(cv.normalized_value))
    return None


def _slope_value(cv: CanonicalValue) -> Tuple[Optional[float], str]:
    """The slope-computable value + its basis label. RANGE uses the
    stated interval's midpoint (derived arithmetic, LABELED — never
    silent precision manufacture); INEQUALITY uses its bound; POINT
    uses the stated value."""
    if cv.representation == "POINT" and cv.normalized_value is not \
            None:
        return float(cv.normalized_value), "POINT_VALUE"
    if cv.representation == "RANGE" and cv.normalized_min is not \
            None and cv.normalized_max is not None:
        return (float(cv.normalized_min) +
                float(cv.normalized_max)) / 2.0, "RANGE_MIDPOINT"
    if cv.representation == "INEQUALITY":
        for attr in ("normalized_value", "normalized_min",
                     "normalized_max"):
            v = getattr(cv, attr, None)
            if v is not None:
                return float(v), "INEQUALITY_BOUND"
    return None, "UNSUITABLE"


def verify_v2_proposals(proposals: List[Dict[str, Any]],
                         records: List[Dict[str, Any]],
                         rung: str,
                         retrieved_at: Optional[str] = None,
                         family_map_path: Path = FAMILY_MAP_V2,
                         ) -> Dict[str, Any]:
    """The deterministic v2 admission gate: signal policy ->
    record-pool membership -> byte-exact span binding (with
    occurrence disambiguation) -> canonical re-derivation from the
    span (the proposer's canonical_value is NEVER trusted) ->
    year binding to the record -> flat-field two-truths checks ->
    family resolution. Rejected proposals are RECORDED with their
    full raw content and a precise reason — never repaired (Art.
    VII), never dropped."""
    # family resolution for this rung
    fam = family_for_rung(rung, family_map_path)
    family_id = (fam or {}).get("family_id")
    # make the tvm_v2 family cache resolve v2 family ids
    load_family_map(path=family_map_path)
    pool = {str(r.get("record_id") or r.get("id")): r
            for r in records or []}
    admitted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for p in proposals or []:
        slot = p.get("slot")
        if p.get("parse_status") != "OK":
            rejected.append({"slot": slot,
                             "reason": "MALFORMED_PROPOSAL",
                             "raw_proposal": p})
            continue
        rid = str(p.get("record_id") or p.get("source_record") or "")
        r = pool.get(rid)
        if r is None:
            rejected.append({"slot": slot,
                            "reason": "RECORD_ID_NOT_IN_RETRIEVED_POOL",
                            "raw_proposal": p})
            continue
        text = _record_text(r)
        span = str(p.get("quoted_span") or "")
        # signal policy FIRST (Phase F: a non-technical signal can
        # never become capability evidence)
        dim = str(p.get("trajectory_dimension") or "")
        if not dim:
            rejected.append({"slot": slot,
                            "reason": "MISSING_TRAJECTORY_DIMENSION",
                            "raw_proposal": p})
            continue
        if classify_signal(dim) != SIGNAL_PRIMARY_TECHNICAL:
            rejected.append({
                "slot": slot,
                "reason": "NON_PRIMARY_SIGNAL_AS_CAPABILITY",
                "signal_class": classify_signal(dim),
                "raw_proposal": p})
            continue
        # span binding (byte-exact)
        occ = p.get("occurrence_index")
        sv = verify_span_binding(span, text, occ if occ is not None
                                 else 0)
        if sv.verdict != SPAN_VERIFIED:
            rejected.append({
                "slot": slot, "reason": sv.verdict,
                "occurrences": sv.occurrences,
                "raw_proposal": p})
            continue
        # value/year must come from committed bytes, not memory
        value_str = str(p.get("value") if p.get("value") is not None
                        else "")
        year_str = str(p.get("year") if p.get("year") is not None
                       else "")
        if value_str and value_str not in span:
            rejected.append({"slot": slot,
                            "reason": "VALUE_TEXT_NOT_IN_QUOTED_SPAN",
                            "raw_proposal": p})
            continue
        if year_str and year_str not in text:
            rejected.append({"slot": slot,
                            "reason": "YEAR_NOT_IN_RECORD_TEXT",
                            "raw_proposal": p})
            continue
        # canonical re-derivation from the span (Art. III)
        cv = parse_value_span(span, context=CONTEXT_VALUE)
        if cv.representation in (REP_NOT_NUMERIC, REP_MALFORMED,
                                 REP_ORDINAL_QUALITATIVE):
            rejected.append({
                "slot": slot,
                "reason": f"VALUE_NOT_MEASURED_NUMERIC:"
                          f"{cv.representation}",
                "raw_proposal": p})
            continue
        yv = _year_canonical(year_str)
        if yv is None:
            rejected.append({"slot": slot,
                            "reason": "YEAR_NOT_CANONICAL",
                            "raw_proposal": p})
            continue
        # canonical value re-check: value_str must re-parse to the
        # SAME representation as the span (two-truths prevention)
        if value_str:
            cv_flat = parse_value_span(value_str,
                                       context=CONTEXT_VALUE)
            if cv_flat.representation != cv.representation:
                rejected.append({
                    "slot": slot,
                    "reason": "FLAT_VALUE_DISAGREES_WITH_SPAN",
                    "raw_proposal": p})
                continue
        flat_value: Optional[float] = None
        if cv.representation == "POINT" and \
                cv.normalized_value is not None:
            flat_value = float(cv.normalized_value)
        entry = {
            "domain": str(p.get("domain") or r.get("domain") or
                          "unspecified"),
            "capability_rung": rung,
            "indicator": str(p.get("indicator") or
                             p.get("metric") or rung),
            "metric": str(p.get("metric") or rung),
            "value": flat_value,
            "unit": str(p.get("unit") or cv.unit or ""),
            "window": year_str or str(p.get("window") or ""),
            "source_record": rid,
            "citation": str(r.get("title") or "")[:200],
            "retrieved_at": retrieved_at,
            "quoted_span": span,
            "span_verification": "SPAN_VERIFIED",
            "confidence": "SPAN_VERIFIED_CANONICAL_DERIVED",
            "canonical_value": cv.to_dict(),
            "signal_class": SIGNAL_PRIMARY_TECHNICAL,
            "trajectory_dimension": dim,
            "capability_family_ref": family_id,
            "occurrence_index": sv.occurrence_index,
            "canonical_year": yv,
            "year_source": year_str,
        }
        gate = verify_tvm_entry(entry, source_text=text)
        if not gate["valid"]:
            rejected.append({
                "slot": slot,
                "reason": "EVIDENCE_CONTRACT:"
                          + ";".join(gate["issues"])[:200],
                "raw_proposal": p})
            continue
        val, basis = _slope_value(cv)
        entry["slope_value"] = val
        entry["slope_value_basis"] = basis
        admitted.append(entry)
    return {
        "admitted": admitted,
        "rejected": rejected,
        "gate": "deterministic v2 admission: signal policy -> pool "
                "membership -> byte-exact span binding -> canonical "
                "re-derivation -> year binding -> flat-field "
                "two-truths -> family resolution; rejected proposals "
                "are recorded with raw content, never repaired",
    }


# ---------------------------------------------------------------------------
# Slopes + query (the cheapest-kill stage reuses the v1 semantics)
# ---------------------------------------------------------------------------

def v2_tvm_slopes(tvm: Dict[str, Any],
                  rung: str) -> List[Dict[str, Any]]:
    """Measured slopes per domain on one rung (v1 semantics, v2
    values): >= 2 admitted entries from the SAME domain with the
    SAME metric+unit at different canonical years. Slope points
    carry their value basis (POINT_VALUE / RANGE_MIDPOINT /
    INEQUALITY_BOUND) — mixed-basis slopes are disclosed, never
    silent."""
    by_domain: Dict[str, List[Dict[str, Any]]] = {}
    for e in tvm.get("entries") or []:
        if str(e.get("capability_rung")) == rung:
            by_domain.setdefault(str(e.get("domain")),
                                 []).append(e)
    out: List[Dict[str, Any]] = []
    for domain, entries in by_domain.items():
        by_metric: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        for e in entries:
            v = e.get("slope_value")
            y = e.get("canonical_year")
            if v is None or y is None:
                continue
            by_metric.setdefault(
                (str(e.get("metric")), str(e.get("unit"))),
                []).append(e)
        best: Optional[Dict[str, Any]] = None
        for (metric, unit), pts in by_metric.items():
            pts = sorted(pts, key=lambda p: p.get("canonical_year")
                         or 0)
            for a, b in zip(pts, pts[1:]):
                dy = (b.get("canonical_year") or 0) - \
                    (a.get("canonical_year") or 0)
                if dy <= 0:
                    continue
                slope = (b["slope_value"] - a["slope_value"]) / dy
                rec = {
                    "domain": domain, "metric": metric, "unit": unit,
                    "slope": round(slope, 6),
                    "abs_slope": round(abs(slope), 6),
                    "from_year": a.get("canonical_year"),
                    "to_year": b.get("canonical_year"),
                    "points": [
                        {"year": p.get("canonical_year"),
                         "value": p.get("slope_value"),
                         "basis": p.get("slope_value_basis"),
                         "span": p.get("quoted_span")}
                        for p in (a, b)],
                }
                if best is None or rec["abs_slope"] > \
                        best["abs_slope"]:
                    best = rec
        if best:
            out.append(best)
    out.sort(key=lambda s: -s["abs_slope"])
    return out


def query_v2_tvm(tvm: Dict[str, Any],
                 rung: str) -> Dict[str, Any]:
    """The GA-3 cheapest-kill query, v2 map: ranked measured movers
    or DEAD_AT_TVM_QUERY (no LLM)."""
    slopes = v2_tvm_slopes(tvm, rung)
    if not slopes:
        return {"verdict": "DEAD_AT_TVM_QUERY",
                "reason": "no measured fast-mover on the rung "
                          "(span-verified entries with >= 2 "
                          "different-year points)",
                "n_entries_on_rung": sum(
                    1 for e in tvm.get("entries") or []
                    if e.get("capability_rung") == rung)}
    return {"verdict": "FAST_MOVERS_RANKED", "slopes": slopes[:5]}


# ---------------------------------------------------------------------------
# The freeze + raw persistence
# ---------------------------------------------------------------------------

def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def build_v2_snapshot(tvm: Dict[str, Any]) -> Dict[str, Any]:
    """Art. XLIV freeze: snapshot + sha256 over the canonical map
    payload, committed before any GA-4 use."""
    payload = _canon(tvm)
    return {
        "tvm_version": TVM_V2_VERSION,
        "entries": tvm.get("entries") or [],
        "n_entries": len(tvm.get("entries") or []),
        "sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "frozen_before_ga4": True,
        "freeze_rule": "the v2 map snapshot + sha256 are committed "
                       "before the first GA-4 backcast call; no "
                       "after-the-fact entry edits (Art. XLIV; a "
                       "changed map is a new snapshot + new freeze "
                       "+ new epistemic version)",
    }


def construction_log_entry(rung: str, records, parsed, gate,
                           model=None, retrieved_at=None,
                           fabric_version=None, prompt_hash=None,
                           output_hash=None,
                           raw_llm_output: str = "",
                           query: Optional[Dict[str, Any]] = None,
                           ) -> Dict[str, Any]:
    """The per-rung construction record — WITH RAW PERSISTENCE (the
    v1 instrument defect fixed forward: the raw LLM output and every
    raw proposal — admitted AND rejected — are persisted, so a
    future instrument comparison replays committed bytes instead of
    reconstructing from prose)."""
    return {
        "rung": rung,
        "n_retrieved": len(records or []),
        "retrieved_at": retrieved_at,
        "retrieval_fabric_version": fabric_version,
        "query": query,
        "n_proposed": len((parsed or {}).get("proposals") or []),
        "n_admitted": len((gate or {}).get("admitted") or []),
        "n_rejected": len((gate or {}).get("rejected") or []),
        "rejected_reasons": [r.get("reason") for r in
                             (gate or {}).get("rejected") or
                             []][:12],
        "raw_proposals": (parsed or {}).get("proposals") or [],
        "raw_rejected_with_reason":
            (gate or {}).get("rejected") or [],
        "raw_llm_output": raw_llm_output,
        "raw_llm_output_sha256":
            hashlib.sha256(raw_llm_output.encode()).hexdigest()
            if raw_llm_output else None,
        "model": model,
        "prompt_hash": prompt_hash,
        "output_hash": output_hash,
    }
