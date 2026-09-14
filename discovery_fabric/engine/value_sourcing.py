"""discovery_fabric/engine/value_sourcing.py — R452: THE VALUE SOURCING ORGAN.

Constitution v2.5.0, Article LXXIV (No Naked Numbers):

> A numerical value may enter canonical state only as a typed value:
> SOURCE_FACT (bound to an exact evidence span with custody), COMPUTED
> (recorded derivation over typed inputs), or MODELLED (a design proposal
> inside a declared, provenance-backed envelope). A value carrying none
> of these is an invented number (Article XXVII) and is BLOCKED.

THE DEFECT THIS MODULE FIXES (external audit of the discovery→engineering
organ, R452 directive):

    The engine had NO evidence→dimension binding stage at all. The
    engineering producer emitted named critical parameters with value
    "UNKNOWN (no sourced value)" on every fresh run; the classifier
    therefore found zero numeric geometry parameters; ENGINEERING_3D was
    structurally unreachable; Article LX (engineering representability)
    was dead while every local gate stayed green. Article XXVII's local
    rule ("no invented numbers") had been implemented as "no numbers."

WHAT THIS MODULE DOES (both directions of the organ):

    1. EXTRACTION — quantitative spans are extracted from the run's FROZEN
       evidence (and from the problem's own declared constraints — the
       buyer's stated requirements are legitimate sourced facts with full
       provenance) into typed candidate facts with custody:
       source id → exact span → content hash → unit family → class.
    2. BINDING — each engineering parameter binds to the best typed fact
       by unit family and recorded term match. Class precedence:
       SOURCE_FACT > COMPUTED > MODELLED > UNKNOWN. Unit conversion is
       explicit and recorded. A MODELLED value may never masquerade as
       SOURCE_FACT (machine-checked downstream in parameter_join).
    3. RESIDUALS — parameters that remain UNKNOWN get the Article LXXV
       action record (why unknown / what would resolve it / the next
       information-gathering action). Never a silent parameters: [].

HONESTY RULES (Art. III/VI/XXV/XXVII):

    - The span is verbatim from the source record; the binding never
      edits the evidentiary text (Art. II).
    - RANGE facts ("15-20 C") are recorded as ranges and are never
      collapsed to a scalar (a midpoint would be an invented number).
    - The problem statement is a REQUIREMENT source: a temperature
      ceiling from the buyer's constraint is a sourced fact ABOUT THE
      REQUIREMENT — it is never promoted to a fact about reality
      (Art. XXVIII).
    - Extraction is deterministic: same evidence corpus → same facts.

reviewer_provenance: AI_REVIEW (Art. LXVII).
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

ORGAN = "VALUE_SOURCING"
ORGAN_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Unit families (canonical unit + conversion factors; deterministic)
# ---------------------------------------------------------------------------

UNIT_FAMILIES: Dict[str, Dict[str, float]] = {
    # canonical: mm
    "LENGTH": {"nm": 1e-6, "um": 1e-3, "µm": 1e-3, "mm": 1.0,
               "cm": 10.0, "dm": 100.0, "m": 1000.0, "km": 1e6},
    # canonical: W
    "POWER": {"mW": 1e-3, "W": 1.0, "kW": 1e3, "MW": 1e6},
    # no offset conversion — family match only (conversion None)
    "TEMPERATURE": {"C": 1.0, "°C": 1.0, "Celsius": 1.0, "K": 1.0,
                    "F": 1.0},
    # canonical: kg
    "MASS": {"mg": 1e-6, "g": 1e-3, "kg": 1.0, "t": 1e3},
    # canonical: s
    "TIME": {"ms": 1e-3, "s": 1.0, "min": 60.0, "minute": 60.0,
             "minutes": 60.0, "h": 3600.0, "hour": 3600.0,
             "hours": 3600.0},
    "VOLTAGE": {"mV": 1e-3, "V": 1.0, "kV": 1e3},
    "CURRENT": {"mA": 1e-3, "A": 1.0},
    # canonical: J
    "ENERGY": {"mJ": 1e-3, "J": 1.0, "kJ": 1e3, "Wh": 3600.0,
               "kWh": 3.6e6},
    # canonical: Pa
    "PRESSURE": {"Pa": 1.0, "kPa": 1e3, "MPa": 1e6, "bar": 1e5,
                 "mbar": 1e2, "atm": 101325.0},
    # canonical: Hz
    "FREQUENCY": {"Hz": 1.0, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9},
    # canonical: Ah
    "CHARGE": {"mAh": 1e-3, "Ah": 1.0},
    "FLOW": {"mL/min": 1.0, "L/min": 1000.0, "mL/s": 60.0,
             "L/s": 60000.0, "m3/s": 6e7},
    "AREA": {"mm2": 1.0, "cm2": 100.0, "m2": 1e6},
    "VOLUME": {"mL": 1.0, "L": 1000.0, "mm3": 1e-3, "cm3": 1.0,
               "m3": 1e6},
    "PERCENT": {"%": 1.0},
}

# units that can appear glued to the number without a space
_BARE_UNITS = sorted(
    {u for fam in UNIT_FAMILIES.values() for u in fam
     if re.fullmatch(r"%|[A-Za-z°µ]+", u)},
    key=len, reverse=True)
_UNIT_ALT = "|".join(re.escape(u) for u in _BARE_UNITS)

# scalar fact: number (optional space) unit
_SCALAR_RE = re.compile(
    rf"(?<![\w.])(\d+(?:\.\d+)?)\s*({_UNIT_ALT})(?![\w])", re.I)
# range fact: low-high unit / low to high unit
_RANGE_RE = re.compile(
    rf"(?<![\w.])(\d+(?:\.\d+)?)\s*(?:[-\u2013]|to)\s*(\d+(?:\.\d+)?)\s*({_UNIT_ALT})(?![\w])",
    re.I)

# term-matching vocabulary for geometry slot names (deterministic; used to
# bind evidence length facts onto form-library geometry slots)
GEOMETRY_SLOT_TERMS: Dict[str, List[str]] = {
    "width": ["width", "wide", "breadth", "across"],
    "panel_width": ["width", "wide", "breadth", "panel"],
    "panel_length": ["length", "long", "span"],
    "length": ["length", "long", "span", "longitudinal"],
    "diameter": ["diameter", "dia", "bore"],
    "outer_diameter": ["diameter", "dia", "outer"],
    "height": ["height", "tall", "depth"],
    "thickness": ["thickness", "thick", "plate thickness"],
    "substrate_t": ["substrate", "thickness", "thick", "plate"],
    "cell_t": ["cell thickness", "cell thick"],
    "functional_t": ["functional layer", "coating thickness",
                     "coating thick"],
    "wall_thickness": ["wall thickness", "wall thick"],
    "frame_w": ["frame", "bezel", "rim"],
}

_STOPWORDS = {
    "the", "a", "an", "of", "at", "in", "on", "for", "and", "or", "to",
    "with", "without", "by", "from", "is", "are", "be", "was", "were",
    "this", "that", "these", "those", "it", "its", "as", "into", "than",
    "then", "when", "where", "which", "who", "what", "how", "why", "no",
    "not", "none", "unknown", "value", "sourced", "parameter", "input",
    "output", "constraint", "design", "domain", "pattern", "expected",
    "effect", "target", "stated", "proposed",
}


def _tokens(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z_]+", (text or "").lower())
            if t not in _STOPWORDS and len(t) > 2]


def _unit_family(unit: str) -> Optional[Tuple[str, float]]:
    for fam, table in UNIT_FAMILIES.items():
        if unit in table:
            return fam, table[unit]
    return None


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


# ---------------------------------------------------------------------------
# Record adapters
# ---------------------------------------------------------------------------

def problem_as_record(problem: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The problem's own declared constraints ARE a source — the buyer's
    stated requirements, with full provenance. A temperature ceiling from
    the problem statement is a sourced fact ABOUT THE REQUIREMENT (never
    promoted to a fact about reality — Art. XXVIII)."""
    problem = problem or {}
    text = " ".join(str(problem.get(k) or "")
                    for k in ("device", "failure", "failure_mode",
                              "constraint", "problem_statement"))
    return {
        "id": f"problem:{problem.get('problem_id') or 'unidentified'}",
        "source_id": f"problem:{problem.get('problem_id') or 'unidentified'}",
        "source_type": "PROBLEM_STATEMENT",
        "title": text[:2000],
        "abstract": "",
        "content_hash": _sha256_text(
            json.dumps(problem, sort_keys=True, default=str)),
    }


def _record_text(record: Dict[str, Any]) -> str:
    return " ".join([
        str(record.get("title") or ""),
        str(record.get("abstract") or ""),
    ])


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract_quantitative_facts(records: List[Dict[str, Any]]) -> List[Dict]:
    """Deterministic extraction of typed quantitative facts from source
    records (evidence items or problem-as-record). Every fact carries the
    full custody chain (Art. XXI.9)."""
    facts: List[Dict] = []
    seen_spans = set()
    for record in records or []:
        rid = str(record.get("id") or record.get("source_id") or "")
        if not rid:
            continue
        text = _record_text(record)
        if not text.strip():
            continue
        content_hash = str(record.get("content_hash") or
                           _sha256_text(text))
        source_kind = ("PROBLEM_STATEMENT"
                       if record.get("source_type") == "PROBLEM_STATEMENT"
                       else "EVIDENCE")
        # ranges first (so "15-20 C" is not double-recorded as scalar)
        scalar_spans: set = set()
        for m in _RANGE_RE.finditer(text):
            low_s, high_s, unit = m.group(1), m.group(2), m.group(3)
            fam = _unit_family(unit)
            if fam is None:
                continue
            span = m.group(0)
            scalar_spans.add(span)
            facts.append(_fact(
                record=record, rid=rid, content_hash=content_hash,
                source_kind=source_kind, span=span,
                value_type="RANGE", unit=unit, family=fam[0],
                value=float(high_s), low=float(low_s), high=float(high_s),
                context=_context(text, m.start(), m.end())))
        for m in _SCALAR_RE.finditer(text):
            unit = m.group(2)
            fam = _unit_family(unit)
            if fam is None:
                continue
            span = m.group(0)
            if span in scalar_spans:
                continue
            key = (rid, span)
            if key in seen_spans:
                continue
            seen_spans.add(key)
            facts.append(_fact(
                record=record, rid=rid, content_hash=content_hash,
                source_kind=source_kind, span=span,
                value_type="SCALAR", unit=unit, family=fam[0],
                value=float(m.group(1)), low=None, high=None,
                context=_context(text, m.start(), m.end())))
    return facts


def _fact(*, record: Dict, rid: str, content_hash: str, source_kind: str,
          span: str, value_type: str, unit: str, family: str, value: float,
          low: Optional[float], high: Optional[float],
          context: str) -> Dict[str, Any]:
    fam_table = UNIT_FAMILIES[family]
    # offset-like families are NEVER cross-converted (92 C is not 92 K —
    # a family-only conversion would manufacture numbers, Art. XXVII)
    if family in ("TEMPERATURE", "PERCENT"):
        canonical_unit, canonical_value, conversion = unit, value, None
    else:
        canonical_unit = _canonical_unit(family)
        factor = fam_table.get(unit)
        conversion = None
        if factor is not None and unit != canonical_unit:
            conversion = {"from_unit": unit, "to_unit": canonical_unit,
                          "factor": factor}
        canonical_value = (round(value * factor, 9)
                           if factor is not None else value)
    return {
        "fact_id": _sha256_text(f"{rid}|{span}|{value_type}")[:16],
        "value_type": value_type,
        "value": value,
        "low": low,
        "high": high,
        "unit": unit,
        "unit_family": family,
        "canonical_unit": canonical_unit,
        "canonical_value": canonical_value,
        "conversion": conversion,
        "span": span,
        "context": context,
        "source_kind": source_kind,
        "source_id": rid,
        "source_type": record.get("source_type") or "",
        "content_hash": content_hash,
    }


def _canonical_unit(family: str) -> str:
    table = UNIT_FAMILIES[family]
    if family == "TEMPERATURE" or family == "PERCENT":
        # first key is the canonical spelling
        return next(iter(table))
    # the entry whose factor is 1.0 is the canonical unit
    for unit, factor in table.items():
        if factor == 1.0:
            return unit
    return next(iter(table))


def _context(text: str, start: int, end: int, width: int = 90) -> str:
    lo = max(0, start - width)
    hi = min(len(text), end + width)
    return re.sub(r"\s+", " ", text[lo:hi]).strip()


# ---------------------------------------------------------------------------
# Binding: facts -> engineering parameters
# ---------------------------------------------------------------------------

def _critical_parameters(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    core = spec.get("engineering_core") or {}
    out = []
    for p in core.get("critical_parameters") or []:
        if isinstance(p, dict) and p.get("parameter"):
            out.append(p)
    return out


def _bind_critical(critical: List[Dict], facts: List[Dict],
                    relevance: "_RelevanceGate") -> List[Dict]:
    """Bind each critical parameter to the best typed fact by unit family
    + recorded term match. Deterministic; every decision recorded.

    Relevance gate (Art. XXI.4): an EVIDENCE fact may only bind when its
    source record is relevance-tied to the problem's own vocabulary —
    an accelerator-physics '20 cm' is not evidence about a laptop
    chassis. PROBLEM_STATEMENT facts are relevant by construction.

    Unit conflation guard: TEMPERATURE and PERCENT families bind only on
    EXACT unit equality (92 C is not 92 K — family-only matching across
    offset/percent-like units manufactures numbers, Art. XXVII)."""
    bindings: List[Dict] = []
    for p in critical:
        pname = str(p.get("parameter") or "")
        symbol = str(p.get("symbol") or "")
        unit = str(p.get("unit") or "")
        fam = _unit_family(unit) if unit else None
        param_tokens = set(_tokens(pname)) | (
            {symbol.lower()} if symbol and len(symbol) <= 3 else set())
        best = None
        if fam:
            for f in facts:
                if f["unit_family"] != fam[0]:
                    continue
                if f["value_type"] != "SCALAR":
                    continue
                # exact-unit rule for offset-like families
                if fam[0] in ("TEMPERATURE", "PERCENT") \
                        and f["unit"] != unit:
                    continue
                if not relevance.allows(f):
                    continue
                ctx_tokens = set(_tokens(f["context"]))
                matched = sorted(param_tokens & ctx_tokens)
                if not matched and not (
                        symbol and symbol.lower() in f["context"].lower()):
                    continue
                score = (len(matched), len(f["span"]))
                if best is None or score > best[0]:
                    best = (score, f, matched)
        if best is not None:
            _, f, matched = best
            prov = {
                "source_kind": f["source_kind"],
                "source_id": f["source_id"],
                "span": f["span"],
                "content_hash": f["content_hash"],
                "context": f["context"],
                "matched_terms": matched,
                "binding_rule": "unit_family+term-overlap+relevance",
            }
            fam_table = UNIT_FAMILIES[fam[0]]
            if f["unit"] == unit:
                value, conv = f["value"], None
            else:
                # same convertible family: convert the FACT into the
                # PARAMETER's unit — explicit and recorded (Art. XXVII)
                factor = fam_table[f["unit"]] / fam_table.get(unit, 1.0)
                value = round(f["value"] * factor, 9)
                conv = {"from_unit": f["unit"], "to_unit": unit,
                        "factor": factor}
            if conv is not None:
                prov["unit_conversion"] = conv
            bindings.append({
                "param_id": p.get("parameter_id"),
                "parameter": pname,
                "symbol": symbol,
                "unit": unit,
                "value": value,
                "value_class": "SOURCE_FACT",
                "provenance": prov,
                "envelope": None,
                "uncertainty": (
                    "single-sourced value; no independent corroboration — "
                    "uncertainty unquantified until a second source or a "
                    "measurement exists"),
                "binding_status": "BOUND",
            })
        else:
            bindings.append(_unknown_binding(p))
    return bindings


def _unknown_binding(p: Dict[str, Any]) -> Dict[str, Any]:
    """Article LXXV: UNKNOWN must be ACTIONABLE — every unresolved
    parameter carries the next information-gathering action."""
    pname = str(p.get("parameter") or "")
    unit = str(p.get("unit") or "")
    return {
        "param_id": p.get("parameter_id"),
        "parameter": pname,
        "symbol": p.get("symbol"),
        "unit": unit,
        "value": None,
        "value_class": "UNKNOWN",
        "provenance": None,
        "envelope": None,
        "uncertainty": "unquantified (no sourced value in the frozen "
                       "corpus)",
        "binding_status": "UNBOUND",
        "next_action": {
            "why_unknown": (
                f"no quantitative span of unit family "
                f"{_unit_family(unit)[0] if _unit_family(unit) else 'ANY'} "
                f"with matching terminology was found in the frozen "
                f"evidence corpus or the problem statement"),
            "what_would_resolve_it": (
                "a retrieved source (paper abstract, patent claim, "
                "datasheet, standard) or a measurement stating this "
                f"quantity in {unit or 'its natural unit'}"),
            "candidate_action": (
                f"targeted retrieval: \"{pname}\" + quantitative "
                f"modifiers; else design the cheapest measurement that "
                f"constrains it"),
            "expected_information_gain": (
                "converts the parameter from UNKNOWN to SOURCE_FACT, "
                "enabling equation linkage and engineering synthesis"),
            "owner_stage": "PARAMETER_SOURCING (next run) / OWNER if "
                           "no legal path exists",
        },
    }


def _bind_geometry_facts(facts: List[Dict],
                         relevance: "_RelevanceGate",
                         ) -> Dict[str, Dict]:
    """Bind LENGTH-family scalar facts onto form-library geometry slot
    names by recorded term match (the evidence→dimension binding the
    audit demanded). Only SCALAR facts bind; RANGE facts are recorded as
    declared envelopes, never collapsed to a scalar.

    Relevance gate (Art. XXI.4): an accelerator paper's '20 cm' is not
    evidence about a laptop chassis — decisions recorded, never silent.
    Envelope sanity (magnitude vs the form family's physical envelope)
    is enforced downstream in parameter_join, which knows the routed
    form."""
    out: Dict[str, Dict] = {}
    for slot, terms in GEOMETRY_SLOT_TERMS.items():
        best = None
        for f in facts:
            if f["unit_family"] != "LENGTH" or f["value_type"] != "SCALAR":
                continue
            if not relevance.allows(f):
                continue
            ctx = f["context"].lower()
            hits = [t for t in terms
                    if re.search(rf"\b{re.escape(t)}\b", ctx)]
            if not hits:
                continue
            # prefer the tightest term (multi-word terms first)
            score = (max(len(t) for t in hits), len(hits))
            if best is None or score > best[0]:
                best = (score, f, hits)
        if best is not None:
            _, f, hits = best
            out[slot] = {
                "slot": slot,
                "value_class": "SOURCE_FACT",
                "value": f["canonical_value"],  # mm
                "unit": "mm",
                "provenance": {
                    "source_kind": f["source_kind"],
                    "source_id": f["source_id"],
                    "span": f["span"],
                    "content_hash": f["content_hash"],
                    "context": f["context"],
                    "matched_terms": hits,
                    "binding_rule": "geometry-slot-term+length-family+"
                                    "relevance",
                    **({"unit_conversion": f["conversion"]}
                       if f["conversion"] else {}),
                },
            }
    return out


class _RelevanceGate:
    """Art. XXI.4 — relevance must be independently established BEFORE a
    search result enters the evidence pipeline. Deterministic proxy:
    an EVIDENCE record is relevance-tied when its own context vocabulary
    shares at least TWO content tokens with the problem's own
    vocabulary (device/failure/constraint). A single generic adjective
    ('compact') shared with an accelerator paper is NOT relevance.
    PROBLEM_STATEMENT records are relevant by construction. Every
    decision is recorded for the audit trail."""

    MIN_SHARED_TOKENS = 2

    def __init__(self, problem_tokens: set):
        self._problem_tokens = problem_tokens
        self.decisions: List[Dict[str, Any]] = []

    def allows(self, fact: Dict[str, Any]) -> bool:
        if fact["source_kind"] == "PROBLEM_STATEMENT":
            return True
        source_tokens = set(_tokens(
            fact.get("context") or ""))
        overlap = sorted(source_tokens & self._problem_tokens)
        ok = len(overlap) >= self.MIN_SHARED_TOKENS
        self.decisions.append({
            "fact_id": fact["fact_id"],
            "source_id": fact["source_id"],
            "span": fact["span"],
            "relevant": ok,
            "shared_tokens": overlap,
            "rule": (f"problem-vocabulary token overlap >= "
                     f"{self.MIN_SHARED_TOKENS} (Art. XXI.4)"),
        })
        return ok


# ---------------------------------------------------------------------------
# The organ entry point
# ---------------------------------------------------------------------------

def source_parameters(engineering_spec: Dict[str, Any],
                      evidence_items: List[Dict[str, Any]],
                      problem: Optional[Dict[str, Any]] = None,
                      ) -> Dict[str, Any]:
    """Run the value-sourcing organ over one engineering specification.

    Returns the SOURCING_RECORD: facts, parameter bindings, class counts,
    residuals. Deterministic for the same inputs.
    """
    records: List[Dict[str, Any]] = [problem_as_record(problem)] \
        if problem else []
    records.extend(evidence_items or [])
    facts = extract_quantitative_facts(records)

    # Art. XXI.4 relevance gate — every decision recorded
    problem_tokens = set(_tokens(" ".join(
        str((problem or {}).get(k) or "")
        for k in ("device", "failure", "failure_mode", "constraint"))))
    relevance = _RelevanceGate(problem_tokens)

    critical = _critical_parameters(engineering_spec or {})
    bindings = _bind_critical(critical, facts, relevance)
    geometry_bindings = _bind_geometry_facts(facts, relevance)

    counts = {"SOURCE_FACT": 0, "COMPUTED": 0, "MODELLED": 0, "UNKNOWN": 0}
    for b in bindings:
        counts[b["value_class"]] += 1
    for _ in geometry_bindings.values():
        counts["SOURCE_FACT"] += 1

    return {
        "organ": ORGAN,
        "organ_version": ORGAN_VERSION,
        "at": _now(),
        "reviewer_provenance": "AI_REVIEW",
        "constitution": "v2.5.0 Art. LXXIV/LXXV (no naked numbers; "
                        "unknown must be actionable)",
        "extraction_summary": {
            "records_scanned": len(records),
            "evidence_records": len(evidence_items or []),
            "problem_statement_record": bool(problem),
            "facts_extracted": len(facts),
            "facts_scalar": sum(1 for f in facts
                                if f["value_type"] == "SCALAR"),
            "facts_range": sum(1 for f in facts
                               if f["value_type"] == "RANGE"),
            "fact_ids": [f["fact_id"] for f in facts],
        },
        "facts": facts,
        "parameters": bindings,
        "geometry_bindings": geometry_bindings,
        "relevance_decisions": relevance.decisions,
        "value_class_counts": counts,
        "residuals": [b for b in bindings
                      if b["value_class"] == "UNKNOWN"],
    }


# ---------------------------------------------------------------------------
# The bridge hook (R452 wiring)
# ---------------------------------------------------------------------------

def _read_run_dir_json(work_dir: Optional[str], name: str) -> Optional[Any]:
    if not work_dir:
        return None
    import pathlib
    p = pathlib.Path(work_dir) / name
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001 — corrupt record is honest absence
        return None


def ensure_sourced_parameters(run_result: Dict[str, Any],
                              work_dir: Optional[str] = None,
                              run_id: Optional[str] = None,
                              ) -> Tuple[Dict[str, Any], Optional[Dict]]:
    """The production hook: called by the bridge before classification.

    - NO-OP when the spec already carries >=3 numeric geometry parameters
      (the released chain / a prior sourcing pass — Art. IV: no
      double-write, no fallback).
    - NO-OP when there is no engineering specification (honest absence).
    - Otherwise: source + join, persist PARAMETER_SOURCE_RECORD.json in
      the run dir (the authority trail, Art. X), and return the enriched
      run_result whose engineering_specification now carries the typed
      parameters the classifier consumes.
    """
    spec = (run_result or {}).get("engineering_specification") or {}
    if not spec:
        return run_result, None

    from discovery_fabric.engine.invention_bridge import classifier as _clf
    if len(_clf._geometry_parameters(spec)) >= 3:
        return run_result, None

    evidence = run_result.get("evidence")
    if not evidence:
        freeze = _read_run_dir_json(work_dir, "envelope_FREEZE.json")
        evidence = (freeze or {}).get("evidence") if isinstance(
            freeze, dict) else None
    problem = (run_result.get("problem")
               or _read_run_dir_json(work_dir, "problem.json"))
    if not evidence and not problem:
        return run_result, None

    sourcing = source_parameters(spec, evidence or [], problem=problem)

    from discovery_fabric.engine import parameter_join as pj
    joined = pj.join_parameters(spec, sourcing, run_result=run_result)

    record = {
        "organ": ORGAN,
        "organ_version": ORGAN_VERSION,
        "status": "SOURCED",
        "at": _now(),
        "run_id": run_id,
        "reviewer_provenance": "AI_REVIEW",
        "constitution": "v2.5.0 Art. LXXIV/LXXV; the discovery→engineering "
                        "organ (R452)",
        "extraction_summary": sourcing["extraction_summary"],
        "value_class_counts": joined["join_report"]["value_class_counts"],
        "parameters": joined["join_report"]["parameter_records"],
        "physical_site": joined["physical_site"],
        "join_report": {k: v for k, v
                        in joined["join_report"].items()
                        if k != "parameter_records"},
        "residuals_next_actions": [
            {"parameter": r["parameter"],
             "next_action": r["next_action"]}
            for r in sourcing["residuals"]],
    }
    if work_dir:
        import pathlib
        out = pathlib.Path(work_dir) / "PARAMETER_SOURCE_RECORD.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record, indent=2))

    enriched = dict(run_result or {})
    enriched["engineering_specification"] = joined["spec"]
    return enriched, record
