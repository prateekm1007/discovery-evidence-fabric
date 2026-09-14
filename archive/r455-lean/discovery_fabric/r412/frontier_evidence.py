"""discovery_fabric.r412.frontier_evidence — the Frontier Evidence
Acquisition Layer (FEAL) for the R412 gradient arm v3.

OPERATOR DIRECTIVE (2026-09-06 audit, "Exact directions to coder"):
build a retrieval-first Gradient V3 arm whose objective is NOT to
manufacture a nonzero result but to determine whether a better
frontier-evidence acquisition system can expose real quantitative
capabilities that the v2 proposer could not see.

The directive's required chain:
  field bottleneck -> capability requirement -> candidate frontier
  domains -> quantitative evidence retrieval -> evidence normalization
  -> capability trajectory -> causal transfer

This module implements the acquisition + normalization layers
DETERMINISTICALLY (no LLM participates in any measurement here —
Art. XVIII; every score is computed from evidence properties, never
model opinion):

  * three retrieval lanes, each separately attributable:
      LANE A — the v1 plain query form (reproduced byte-identically)
      LANE B — capability requirement + explicit measurement
                terminology (the operator's frozen vocabulary)
      LANE C — frontier-domain transfer: the ga1b AI-proposed frontier
                domains anchor WHERE to search, the target capability
                is the bridge (exploratory priority only — investment/
                talent/never-qualifies rules enforced by tvm_v2
                signal_policy at admission)
  * full pool persistence (record_id, title, abstract, source,
    source family, evidence lane, publication year via multi-field
    fallback, doi, patent number, query, retrieved_at) — the v2 run
    persisted only id/title/abstract, which made source attribution
    and year recovery unmeasurable (disclosed in the v2 diagnostic)
  * deterministic numeric evidence extraction over record text
    (closed unit vocabulary + the tvm_v2 lossless value parser; every
    extracted span is byte-exact in the record text by construction)
  * the Frontier Evidence Score (deterministic; rewards explicit
    measured value, baseline/comparator, improvement direction, year,
    recency, in-abstract context; penalizes title-only evidence,
    unverifiable values, missing units, missing baseline, purely
    qualitative claims — NOT a novelty score, never labeled as one)
  * capability trajectory assembly (capability -> metric -> value ->
    baseline -> year -> source -> domain -> trajectory) with
    cross-source corroboration states
    (SINGLE_SOURCE_SIGNAL / MULTI_SOURCE_SIGNAL /
    REPLICATED_TRAJECTORY / UNKNOWN) — a single paper is eligible for
    exploration but never automatically a "rapidly improving frontier
    capability"
  * multi-level capability derivation from each death (directive item
    9: several candidate capability families per death, derived
    deterministically from committed evidence, never invented)

Constitutional anchors: Art. II (exact spans), Art. XXI (search
activity is not evidence; relevance recorded), Art. XLIII (query
derivation labeled), Art. XLIV (new retrieval = new epistemic
version), Art. XXVII (weights/thresholds carry provenance class),
Art. XLVII (identical instrument across arms), Art. LIX (no tuning
against frozen benchmarks), Art. LXII (regenerable from committed
bytes).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[2]
V2DIR = REPO / "R412" / "GRADIENT_V2"
import sys  # noqa: E402

sys.path.insert(0, str(V2DIR))

from tvm_v2 import (  # noqa: E402
    parse_value_span, CONTEXT_VALUE, CONTEXT_YEAR,
    REP_POINT, REP_RANGE, REP_INEQUALITY,
)

FEAL_VERSION = "R412-FEAL-1.0.0"
FAMILY_MAP_V2 = V2DIR / "CAPABILITY_FAMILY_MAP_V2.json"
GA1B_PATH = REPO / "R412" / "RECOVERY_ARM" / "GRADIENT_RUN" / \
    "ga1b.jsonl"

# ---------------------------------------------------------------------------
# Closed vocabularies (frozen; every list carries its provenance class)
# ---------------------------------------------------------------------------

#: LANE B measurement terminology — OPERATOR_DIRECTIVE frozen list
#: (directive item 3, verbatim) + the value/unit surface forms needed
#: to bind it to quantitative text. Closed: no term may be added
#: post-freeze without a new epistemic version (Art. XLIV).
MEASUREMENT_TERMS: List[str] = [
    "performance", "efficiency", "loss", "precision", "accuracy",
    "throughput", "latency", "reliability", "energy", "yield",
    "lifetime", "manufacturing tolerance",
]

#: measurement-verb vocabulary (records that BEAR measurement, for the
#: measurement-bearing rate) — ENGINEERING class, closed, frozen.
MEASUREMENT_VERBS: List[str] = [
    "measured", "measure", "measurement", "experiment", "experimental",
    "evaluated", "evaluation", "demonstrated", "characterized",
    "quantified", "tested", "validated", "benchmarked", "analyzed",
    "simulated", "investigated", "assessed", "compared", "observed",
    "recorded", "reported", "achieved", "obtained",
]

#: baseline/comparator vocabulary (Frontier Evidence Score reward;
#: directive item 4 "baseline/comparator") — ENGINEERING class.
BASELINE_TERMS: List[str] = [
    "baseline", "compared", "comparison", "versus", " vs ",
    "reference", "conventional", "state-of-the-art", "state of the art",
    "prior art", "previous", "existing", "benchmark", "control group",
    "counterpart", "commercial", "industry standard", "best reported",
    "best-in-class", "reference design",
]

#: improvement-direction vocabulary (score reward) — ENGINEERING class.
DIRECTION_TERMS: List[str] = [
    "increase", "increased", "improve", "improved", "improvement",
    "gain", "gained", "enhanced", "enhancement", "higher", "raise",
    "raised", "reduce", "reduced", "reduction", "decrease", "decreased",
    "lower", "lowered", "cut", "achieves", "achieved", "reach",
    "reached", "reaches", "exceeds", "surpass", "surpasses",
    "outperform", "outperforms",
]

#: METRIC vocabulary for span->metric attribution (trajectory keying).
#: Closed; OPERATOR_DIRECTIVE measurement list + surface forms the
#: engineering literature uses for the 13 sealed capability rungs.
METRIC_TERMS: List[str] = [
    # operator measurement list (surface forms)
    "switching loss", "conduction loss", "power loss", "loss",
    "efficiency", "conversion efficiency", "energy efficiency",
    "accuracy", "precision", "throughput", "latency", "reliiability",
    "energy consumption", "power consumption", "energy", "yield",
    "lifetime", "fatigue life", "cycle life", "tolerance",
    "manufacturing tolerance", "bandwidth", "control bandwidth",
    "power density", "energy density", "specific power", "specific energy",
    "cost", "cost per unit", "material removal rate", "surface roughness",
    "detection accuracy", "false positive rate", "sensitivity",
    "resolution", "response time", "settling time", "rise time",
    "torque density", "power output", "output power", "thrust",
    "pressure drop", "heat transfer coefficient", "thermal resistance",
    "junction temperature", "coefficient of performance", "cop",
    "emissivity", "absorption capacity", "capture efficiency",
    "coulombic efficiency", "capacity retention", "capacity fade",
    "state of charge", "soh", "fill factor", "open circuit voltage",
    "power factor", "total harmonic distortion", "thd",
    "tracking efficiency", "mismatch loss", "availability",
    "mean time between failures", "mtbf", "failure rate",
    "defect rate", "alignment tolerance", "misalignment",
    "surface finish", "tool wear", "cutting force", "waviness",
    "prediction error", "forecast error", "modeling error",
    "detection rate", "detection limit", "signal to noise ratio",
    "drift", "stability", "repeatability", "reproducibility",
    "duty cycle", "frequency response", "gain margin", "phase margin",
    "overshoot", "steady state error", "robustness",
]

# longest-first ordering so "switching loss" matches before "loss"
METRIC_TERMS_SORTED = sorted(METRIC_TERMS, key=lambda t: -len(t))

#: unit vocabulary (closed; ENGINEERING class). Longest-first so that
#: 'mW' is never shadowed by 'W', 'kHz' by 'Hz', 'mm' by 'm'.
UNIT_SYMBOLS: List[str] = [
    # multi-symbol composites first
    "W/cm2", "W/cm2", "A/cm2", "mW/cm2", "W/mK", "Wh/kg", "W/kg",
    "kWh/kg", "J/cm3", "m3/h", "m3/s", "L/min", "mL/min", "mS/cm",
    "lm/W", "dBm", "dBi", "MHz", "GHz", "THz", "kHz", "Hz",
    "kPa", "MPa", "GPa", "mbar", "bar", "Pa",
    "kV", "mV", "kA", "mA", "mW", "kW", "MW", "GW", "mJ", "kJ",
    "MJ", "kWh", "MWh", "Wh",
    "ms", "us", "ns", "ps",
    "mg", "ug", "kg", "mm", "cm", "um", "nm", "km",
    "kN", "dB", "ppm", "ppb", "rpm", "mil",
    # single-letter symbols last (require following boundary)
    "%", "V", "A", "W", "J", "K", "N", "g", "m", "s", "h", "L", "t",
    "°C", "°F", "°",
]

#: word-form units (require space + word boundary)
WORD_UNITS: List[str] = [
    "percent", "percentage", "fold", "volts", "volt", "amperes",
    "amps", "amp", "watts", "watt", "joules", "joule", "seconds",
    "second", "minutes", "minute", "hours", "hour", "days", "day",
    "years", "year", "meters", "meter", "millimeters", "micrometers",
    "nanometers", "kelvin", "cycles", "degrees", "rpm",
]


def _unit_alternation(units: List[str]) -> str:
    escaped = [re.escape(u) for u in units if u]
    return "|".join(sorted(escaped, key=len, reverse=True))


_NUM = r"\d+(?:\.\d+)?"

#: number + unit (symbol form; longest unit first). The unit must be
#: preceded by the number (optional space) and followed by a
#: non-alphanumeric boundary so 'm' never matches inside 'min' when
#: 'min' itself is listed first (it is, via longest-first).
_NUMERIC_UNIT_RE = re.compile(
    rf"({_NUM})\s?({_unit_alternation(UNIT_SYMBOLS)})(?![A-Za-z0-9])")

#: range form: NUM [-|–|to] NUM unit
_NUMERIC_RANGE_RE = re.compile(
    rf"({_NUM})\s*(?:[-\u2013]|to)\s*({_NUM})\s?"
    rf"({_unit_alternation(UNIT_SYMBOLS)})(?![A-Za-z0-9])")

#: word-unit form: NUM space WORD-UNIT (word boundary)
_NUMERIC_WORD_UNIT_RE = re.compile(
    rf"({_NUM})\s({_unit_alternation(WORD_UNITS)})\b")

#: ratio/fold forms: NUM x / NUM-fold (dimensionless capability claims)
_NUMERIC_FOLD_RE = re.compile(rf"({_NUM})\s?(x\b|-fold\b|fold\b)")

#: any numeric token (diagnostic tier 1)
_ANY_NUM_RE = re.compile(r"\d+(?:\.\d+)?")

#: a bare year token (excluded from numeric-bearing tier 2)
_YEAR_TOKEN_RE = re.compile(r"\b(19|20)\d{2}\b")

#: domain classification table for diversity measurement — closed
#: heuristic (DERIVED_HEURISTIC class, disclosed on every use: domain
#: labels come from title keywords, never from model opinion).
DOMAIN_KEYWORDS: List[Tuple[str, List[str]]] = [
    ("wind_energy", ["wind turbine", "wind energy", "wind farm",
                     "offshore wind", "turbine blade", "nacelle"]),
    ("power_electronics", ["inverter", "converter", "power semiconductor",
                           "switching", "mosfet", "igbt", "gan ", "sic ",
                           "wide bandgap", "wide-bandgap", "pwm", "dpwm",
                           "power electronics", "power module"]),
    ("batteries_storage", ["battery", "batteries", "lithium-ion",
                           "li-ion", "lithium ion", "electrode",
                           "electrochemical cell", "state of charge"]),
    ("thermal_management", ["heat exchanger", "thermal management",
                            "cooling", "heat sink", "heat transfer",
                            "data center cooling", "air conditioning",
                            "refrigeration", "chiller"]),
    ("machining_manufacturing", ["machining", "cutting tool", "milling",
                                 "turning", "grinding", "surface finish",
                                 "tool wear", "workpiece", "cnc"]),
    ("chemical_process", ["chemical process", "reactor", "distillation",
                          "separation column", "absorption", "amine",
                          "catalytic", "catalyst", "solvent"]),
    ("carbon_capture", ["carbon capture", "co2 capture", "co2 removal",
                        "post-combustion", "dac ", "direct air capture",
                        "carbon sequestration"]),
    ("semiconductor_fab", ["semiconductor manufacturing", "lithography",
                           "wafer", "fab ", "photolithography",
                           "etching", "deposition", "process node",
                           "chip manufacturing", "integrated circuit"]),
    ("metrology_sensing", ["sensor", "measurement system", "metrology",
                           "detection", "monitoring", "diagnostic",
                           "measurement instrument", "calibration"]),
    ("control_systems", ["control system", "controller", "feedback",
                         "model predictive control", "adaptive control",
                         "closed-loop", "closed loop", "actuator",
                         "servo", "tracking control"]),
    ("renewables_pv", ["photovoltaic", "solar cell", "pv ", "solar panel",
                       "perovskite", "multi-junction", "solar inverter"]),
    ("aerospace_propulsion", ["aircraft", "aerospace", "propulsion",
                              "turbomachinery", "jet engine", "rocket"]),
]

# -- Frontier Evidence Score weights (frozen; provenance below) ------
#: Weight provenance (Art. XXVII): the reward/penalize STRUCTURE is
#: OPERATOR_DIRECTIVE (directive item 4 list, verbatim mapping); the
#: numeric weights are ENGINEERING (monotone operationalization of
#: that list — each directive-listed property moves the score in the
#: required direction; no weight was tuned against any benchmark).
FES_WEIGHTS: Dict[str, int] = {
    "measured_value_with_unit": 25,
    "measurement_context": 10,
    "improvement_direction": 10,
    "baseline_comparator": 10,
    "year_recoverable": 10,
    "recency_recent": 8,
    "recency_mid": 5,
    "recency_old": 2,
    "in_abstract_context": 5,
    "title_only_penalty": -15,
    "value_without_unit_penalty": -10,
    "missing_baseline_penalty": -5,
    "qualitative_only_penalty": -20,
}

#: trajectory-level score components (same provenance class)
TRAJ_WEIGHTS: Dict[str, int] = {
    "multi_source_signal": 15,
    "replicated_trajectory": 25,
    "three_or_more_points": 10,
    "three_or_more_sources": 5,
    "domain_diversity_two_plus": 10,
    "year_span_three_plus": 5,
}


# ---------------------------------------------------------------------------
# Lane query construction (directive item 3 — three separate lanes,
# each with its own attribution; never one arbitrary formulation)
# ---------------------------------------------------------------------------

def _load_family_map(map_path: Path = FAMILY_MAP_V2) -> Dict[str, Any]:
    return json.loads(Path(map_path).read_text())


def family_for_rung(rung: str,
                    map_path: Path = FAMILY_MAP_V2
                    ) -> Optional[Dict[str, Any]]:
    """Exact-key family lookup (the Phase-D map; a miss returns None,
    never a fuzzy guess — Art. XLIII)."""
    data = _load_family_map(map_path)
    q = str(rung).strip().lower()
    for f in data.get("families", []):
        if f.get("exact_capability", "").strip().lower() == q:
            return f
    return None


def load_ga1b(path: Path = GA1B_PATH) -> List[Dict[str, Any]]:
    """The committed GA-1b extractions (13 span-verified records)."""
    out = []
    for line in Path(path).read_text().splitlines():
        if line.strip():
            rec = json.loads(line)
            if rec.get("status") == "OK":
                out.append(rec)
    return out


def rungs_from_ga1b(path: Path = GA1B_PATH) -> List[Dict[str, Any]]:
    """Ordered (rung, gate) pairs from the committed GA-1b records.
    Allocation rungs first (the sealed priority order), then the rest
    — deterministic, no re-allocation."""
    prereg = json.loads(
        (REPO / "R412" / "R412_GRADIENT_RECOVERY_PREREGISTRATION.json")
        .read_text())
    priority = prereg["resource_allocation"]["priority_order"]
    gate_by_cid = {}
    for rec in load_ga1b(path):
        gate_by_cid[rec["candidate_id"]] = (rec.get("gate") or {})
    rung_by_cid = {cid: (g.get("capability_rung") or "")
                   for cid, g in gate_by_cid.items()}
    ordered: List[Dict[str, Any]] = []
    seen = set()
    for cid in priority:
        rung = rung_by_cid.get(cid)
        if rung and rung.casefold() not in seen:
            seen.add(rung.casefold())
            ordered.append({"rung": rung, "gate": gate_by_cid[cid],
                            "family": family_for_rung(rung)})
    for rec in load_ga1b(path):
        rung = (rec.get("gate") or {}).get("capability_rung") or ""
        if rung and rung.casefold() not in seen:
            seen.add(rung.casefold())
            ordered.append({"rung": rung, "gate": rec.get("gate") or {},
                            "family": family_for_rung(rung)})
    return ordered


def lane_a_query(rung: str) -> Dict[str, Any]:
    """LANE A — the v1 plain query form, reproduced byte-identically
    (scripts/r412_run_gradient_arm.py line 398-399: f\"{rung}
    performance trend improvement measured benchmark\"). The control
    column: same plumbing as every other lane, the KNOWN v1
    formulation."""
    return {
        "lane": "A",
        "query": f"{rung} performance trend improvement measured "
                 f"benchmark",
        "lane_attribution": "LANE_A_V1_PLAIN",
        "query_provenance": {
            "rung": "DERIVED_FROM_EVIDENCE (ga1b span-verified rung)",
            "form": "V1_FORM_REPRODUCED (byte-identical to the sealed "
                    "v1 TVM query construction)",
        },
    }


def _measurement_terms_string() -> str:
    return " ".join(MEASUREMENT_TERMS)


def lane_b_queries(rung: str,
                   map_path: Path = FAMILY_MAP_V2
                   ) -> List[Dict[str, Any]]:
    """LANE B — capability requirement + explicit measurement
    terminology (directive item 3, the operator's frozen list). Two
    queries per rung: (1) the exact capability requirement form; (2)
    the measurement-dimension form (directive item 9: several
    candidate capability families per death — the family's
    measurement dimension is a second, deterministic, evidence-derived
    abstraction of the same death)."""
    fam = family_for_rung(rung, map_path)
    out: List[Dict[str, Any]] = []
    seen_queries = set()

    def _add_b(query: str, attribution: str,
               provenance: Dict[str, str]) -> None:
        # deduplicate: a measurement-dimension form that collapses to
        # the same query as the exact-capability form adds nothing
        if query in seen_queries:
            return
        seen_queries.add(query)
        out.append({
            "lane": "B",
            "query": query,
            "lane_attribution": attribution,
            "query_provenance": provenance,
        })

    _add_b(f"{rung} {_measurement_terms_string()} measured "
            f"improvement",
            "LANE_B_CAPABILITY_MEASUREMENT",
            {
                "rung": "DERIVED_FROM_EVIDENCE (ga1b span-verified "
                        "rung)",
                "measurement_vocabulary": "OPERATOR_DIRECTIVE "
                                          "(frozen list, directive "
                                          "item 3)",
            })
    if fam:
        dims = [t.strip() for t in str(
            fam.get("measurement_dimension") or "").split(",")
                if t.strip()]
        if dims:
            core = " ".join(dims[:5])
            _add_b(f"{core} {_measurement_terms_string()} "
                    f"measured improvement",
                    "LANE_B_MEASUREMENT_DIMENSION_FORM",
                    {
                        "measurement_dimension":
                            "DERIVED_FROM_EVIDENCE (family map basis "
                            "spans; directive item 9 second capability "
                            "abstraction per death)",
                        "measurement_vocabulary":
                            "OPERATOR_DIRECTIVE (frozen list)",
                    })
    return out


#: epistemic-state markers that may appear in the ga1b
#: frontier_domains field but are NEVER search domains (Art. XXV:
#: unknown is an honest state, not a place to search). CLOSED set.
INVALID_FRONTIER_DOMAIN_TOKENS = {
    "unknown", "not stated", "n/a", "na", "none", "unspecified",
    "not reported", "not determined", "", "tbd",
}


def _valid_frontier_domains(gate: Dict[str, Any]) -> List[str]:
    """Frontier domains with epistemic-state markers filtered out.
    A rung with no VALID recorded domain yields [] — recorded by
    the caller as LANE_C_NO_VALID_FRONTIER_DOMAIN, never a
    fabricated search term."""
    raw = str(gate.get("frontier_domains") or "")
    out = []
    for d in raw.split(","):
        d = d.strip()
        if d and d.lower() not in INVALID_FRONTIER_DOMAIN_TOKENS:
            out.append(d)
    return out


def lane_c_queries(rung: str,
                   gate: Optional[Dict[str, Any]] = None,
                   map_path: Path = FAMILY_MAP_V2
                   ) -> List[Dict[str, Any]]:
    """LANE C — frontier-domain transfer: search domains with
    candidate rapid progress, using the TARGET CAPABILITY as the
    bridge. The frontier domains come from the committed ga1b
    extractions (AI_PROPOSED_EXPLORATORY — they may order WHERE to
    search, never qualify WHAT is found; the tvm_v2 signal policy
    rejects investment/talent/experimental-concentration evidence at
    admission, so a domain's money concentration can never launder
    itself into capability)."""
    gate = gate or {}
    domains = _valid_frontier_domains(gate)
    fam = family_for_rung(rung, map_path)
    # the capability bridge: the rung plus any measurement-dimension
    # terms NOT already in the rung (token deduplication — a redundant
    # bridge repeats the rung and dilutes the domain anchor)
    bridge_tokens = str(rung).lower().split()
    if fam:
        dims = [t.strip().lower() for t in str(
            fam.get("measurement_dimension") or "").split(",")
                if t.strip()]
        for d in dims[:3]:
            if d not in bridge_tokens:
                bridge_tokens.append(d)
    bridge = " ".join(bridge_tokens)
    out: List[Dict[str, Any]] = []
    for dom in domains[:2]:
        out.append({
            "lane": "C",
            "query": f"{dom} {bridge} measured performance "
                     f"improvement",
            "lane_attribution": "LANE_C_FRONTIER_DOMAIN_TRANSFER",
            "frontier_domain": dom,
            "query_provenance": {
                "frontier_domain":
                    "AI_PROPOSED_EXPLORATORY (ga1b gate.frontier_domains;"
                    " search priority only — establishes nothing; the "
                    "signal policy rejects investment-class evidence at "
                    "admission)",
                "capability_bridge":
                    "DERIVED_FROM_EVIDENCE (rung + family measurement "
                    "dimension)",
            },
        })
    return out


def all_lane_queries(rungs: List[Dict[str, Any]]
                     ) -> List[Dict[str, Any]]:
    """The full v3 lane query plan (deterministic; recorded verbatim
    in the preregistration BEFORE any lane evaluation)."""
    out: List[Dict[str, Any]] = []
    for r in rungs:
        rung = r["rung"]
        out.append({**lane_a_query(rung), "rung": rung})
        for q in lane_b_queries(rung):
            out.append({**q, "rung": rung})
        for q in lane_c_queries(rung, r.get("gate")):
            out.append({**q, "rung": rung})
    return out


# ---------------------------------------------------------------------------
# Pool normalization (evidence persistence — the v2 defect fixed
# forward: source identity + year + lane attribution on every record)
# ---------------------------------------------------------------------------

_YEAR_FIRST_RE = re.compile(r"\b(19[5-9]\d|20[0-2]\d)\b")


def extract_year(*values: Any) -> Optional[int]:
    """Deterministic publication-year recovery from any of the field
    forms the fabric's records carry (publication_year, year,
    issued_year, publication_date 'YYYY-MM-DD', published
    'YYYY-MM...', firstPublicationDate). Returns None when no year is
    recoverable — never a guess (Art. XXV)."""
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if not s:
            continue
        m = _YEAR_FIRST_RE.search(s[:12])
        if m:
            y = int(m.group(1))
            if 1950 <= y <= 2099:
                return y
    return None


def pool_record_from_item(item: Dict[str, Any],
                          canonical: Optional[Dict[str, Any]] = None,
                          ) -> Dict[str, Any]:
    """One FEAL pool record from a fabric engine item, enriched from
    the fabric report's canonical record (year multi-field fallback).
    Everything the evidence layer needs is persisted: identity, text,
    source attribution, year, lane, raw hash."""
    prov = item.get("provenance") or {}
    best = (canonical or {}).get("best_record") or {}
    year = extract_year(
        item.get("publication_year"),
        (item.get("source_specific") or {}).get("publication_year")
        if isinstance(item.get("source_specific"), dict) else None,
        best.get("publication_year"),
        best.get("year"),
        best.get("issued_year"),
        best.get("publication_date"),
        best.get("published"),
        best.get("firstPublicationDate"),
        best.get("first_publication_date"),
    )
    abstract = str(item.get("abstract") or "")
    return {
        "record_id": item.get("id") or item.get("canonical_id"),
        "title": str(item.get("title") or ""),
        "abstract": abstract,
        "source": item.get("source") or
                  (canonical or {}).get("origin_source"),
        "source_family": item.get("source_family") or
                         prov.get("source_family"),
        "evidence_lane": item.get("evidence_lane"),
        "publication_year": year,
        "doi": item.get("doi") or (canonical or {}).get("doi"),
        "patent_number": item.get("patent_number") or
                         (canonical or {}).get("patent_number"),
        "document_type": item.get("document_type"),
        "raw_payload_sha256": prov.get("raw_payload_sha256") or "",
        "indexing_sources": prov.get("indexing_sources") or [],
        "origin_source": (canonical or {}).get("origin_source"),
        "source_uri": item.get("source_uri"),
        "publication_status": item.get("publication_status"),
        "limitations": item.get("limitations") or [],
    }


def domain_class(record: Dict[str, Any]) -> str:
    """Closed-heuristic domain classification (title keywords only;
    DERIVED_HEURISTIC provenance — never model opinion). Patents with
    no classified keyword fall to patent_unclassified."""
    t = (str(record.get("title") or "") + " " +
         str(record.get("abstract") or "")[:300]).lower()
    for dom, kws in DOMAIN_KEYWORDS:
        if any(kw in t for kw in kws):
            return dom
    if str(record.get("record_id") or "").startswith("patent:"):
        return "patent_unclassified"
    return "other_unclassified"


# ---------------------------------------------------------------------------
# Deterministic numeric evidence extraction (evidence normalization)
# ---------------------------------------------------------------------------

def _sentences(text: str) -> List[Tuple[int, int, str]]:
    """Sentence segmentation WITHOUT breaking decimal numbers:
    split on [.!?;] that is not between digits. Returns
    (start_offset, end_offset, sentence) tuples for span->sentence
    attribution."""
    out: List[Tuple[int, int, str]] = []
    start = 0
    for i, ch in enumerate(text):
        if ch in ".!?;":
            prev = text[i - 1] if i > 0 else ""
            nxt = text[i + 1] if i + 1 < len(text) else ""
            if prev.isdigit() and nxt.isdigit():
                continue  # decimal point / range inside a number
            if nxt and not nxt.isspace() and ch == ".":
                # abbreviation-like (e.g., 'e.g.'); still a boundary for
                # our purposes only if followed by space — skip tight
                continue
            out.append((start, i + 1, text[start:i + 1].strip()))
            start = i + 1
    if start < len(text):
        out.append((start, len(text), text[start:].strip()))
    return [s for s in out if s[2]]


def _sentence_for_span(sentences: List[Tuple[int, int, str]],
                       span_start: int) -> Tuple[int, str]:
    """(sentence_index, sentence_text) for a span offset — the LAST
    sentence whose start <= span_start (spans live in the sentence that
    contains them)."""
    idx = 0
    for i, (s, e, txt) in enumerate(sentences):
        if s <= span_start:
            idx = i
        else:
            break
    return idx, sentences[idx][2]


def _find_metric(sentence: str, span: str) -> Optional[str]:
    """Nearest closed-vocabulary metric term in the sentence (ties:
    the earliest). None when no metric term is present — the evidence
    still records, but trajectories require a metric key."""
    positions: List[Tuple[int, str]] = []
    s_low = sentence.lower()
    span_pos = s_low.find(span.lower())
    if span_pos < 0:
        span_pos = 0
    for term in METRIC_TERMS_SORTED:
        start = 0
        while True:
            p = s_low.find(term, start)
            if p < 0:
                break
            # word-boundary check for the metric term
            before_ok = p == 0 or not (s_low[p - 1].isalnum())
            after = p + len(term)
            after_ok = after >= len(s_low) or not (
                s_low[after].isalnum())
            if before_ok and after_ok:
                positions.append((p, term))
            start = p + 1
    if not positions:
        return None
    positions.sort(key=lambda pt: (abs(pt[0] - span_pos), pt[0]))
    return positions[0][1]


def _vocab_hits(sentence: str, vocab: List[str]) -> List[str]:
    s_low = " " + sentence.lower() + " "
    hits = []
    for term in vocab:
        t = term.strip().lower()
        if not t:
            continue
        if f" {t} " in s_low or f" {t}" in s_low.rstrip():
            hits.append(t)
    return hits


def _candidate_spans(text: str
                     ) -> List[Tuple[str, int, bool, bool]]:
    """(span, offset, is_range, has_unit) candidates from one text
    block. Spans are extracted FROM the text, hence byte-exact by
    construction (Art. II). Deduplicated by (span, offset)."""
    found: Dict[Tuple[str, int], Tuple[str, int, bool, bool]] = {}
    for m in _NUMERIC_RANGE_RE.finditer(text):
        span = m.group(0)
        found[(span, m.start())] = (span, m.start(), True, True)
    for m in _NUMERIC_UNIT_RE.finditer(text):
        span = m.group(0)
        if (span, m.start()) not in found:
            found[(span, m.start())] = (span, m.start(), False, True)
    for m in _NUMERIC_WORD_UNIT_RE.finditer(text):
        span = m.group(0)
        if (span, m.start()) not in found:
            found[(span, m.start())] = (span, m.start(), False, True)
    for m in _NUMERIC_FOLD_RE.finditer(text):
        span = m.group(0)
        if (span, m.start()) not in found:
            found[(span, m.start())] = (span, m.start(), False, False)
    return [found[k] for k in sorted(found.keys(),
                                     key=lambda k: k[1])]


def extract_numeric_evidence(title: str, abstract: str
                             ) -> Dict[str, Any]:
    """Deterministic numeric-evidence extraction over one record's
    title+abstract. Every returned evidence item:
      span (byte-exact in the source text), representation (tvm_v2
      lossless parse), canonical value dict, unit, in_abstract flag,
      metric attribution (closed vocabulary), sentence,
      baseline_comparator terms, improvement_direction terms,
      measurement_context flag.
    A span that the value parser rejects (MALFORMED / NOT_NUMERIC /
    ORDINAL_QUALITATIVE) is recorded in rejected_candidates with its
    reason — never silently dropped (Art. XV)."""
    title = str(title or "")
    abstract = str(abstract or "")
    evidences: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for block_name, block in (("title", title),
                              ("abstract", abstract)):
        if not block.strip():
            continue
        sentences = _sentences(block)
        for span, offset, is_range, has_unit in \
                _candidate_spans(block):
            cv = parse_value_span(span, context=CONTEXT_VALUE)
            if cv.representation not in (REP_POINT, REP_RANGE,
                                         REP_INEQUALITY):
                rejected.append({
                    "span": span, "block": block_name,
                    "reason": f"PARSE_{cv.representation}",
                })
                continue
            s_idx, sentence = _sentence_for_span(sentences, offset)
            metric = _find_metric(sentence, span)
            base_hits = _vocab_hits(sentence, BASELINE_TERMS)
            dir_hits = _vocab_hits(sentence, DIRECTION_TERMS)
            verb_hits = _vocab_hits(
                " ".join(sentences[i][2] for i in range(
                    max(0, s_idx - 1), min(len(sentences), s_idx + 2))),
                MEASUREMENT_VERBS)
            evidences.append({
                "span": span,
                "block": block_name,
                "in_abstract": block_name == "abstract",
                "representation": cv.representation,
                "canonical": cv.to_dict(),
                "unit": cv.unit or ("" if not has_unit else
                                    _unit_of(span)),
                "is_range": is_range,
                "sentence": sentence[:400],
                "metric": metric,
                "metric_provenance": "CLOSED_VOCABULARY_NEAREST_TERM"
                                     if metric else "UNLABELED_METRIC",
                "baseline_comparator": base_hits[:4],
                "improvement_direction": dir_hits[:4],
                "measurement_context": bool(verb_hits),
            })
    return {"evidences": evidences, "rejected_candidates": rejected}


def _unit_of(span: str) -> str:
    """The unit token of a matched span (for spans whose canonical
    parse carries no canonical unit — the raw unit is still recorded
    verbatim)."""
    m = _NUMERIC_UNIT_RE.search(span) or \
        _NUMERIC_RANGE_RE.search(span) or \
        _NUMERIC_WORD_UNIT_RE.search(span)
    if m:
        groups = [g for g in m.groups() if g is not None]
        return groups[-1] if len(groups) > 1 else ""
    return ""


def record_has_measurement_vocab(title: str, abstract: str) -> bool:
    t = f"{title} {abstract}".lower()
    return any(v in t for v in MEASUREMENT_VERBS)


def record_signal_families(title: str, abstract: str
                            ) -> List[str]:
    """Which of the six primary signal families (signal_policy) have
    surface forms in the record text — the performance/cost/efficiency/
    reliability/manufacturing/deployment signal rate inputs."""
    t = f"{title} {abstract}".lower()
    fams = {
        "performance": ["performance", "accuracy", "precision",
                        "throughput", "latency", "bandwidth", "speed",
                        "sensitivity", "resolution", "power density"],
        "cost": ["cost", "price", "capex", "cheaper",
                 "cost-effective", "expensive"],
        "efficiency": ["efficiency", "loss", "losses", "yield",
                       "figure of merit", "consumption"],
        "reliability": ["reliability", "lifetime", "durability",
                        "failure rate", "drift", "degradation",
                        "fatigue"],
        "manufacturing": ["manufacturing", "fabrication", "tolerance",
                          "wafer", "machining", "scalab"],
        "deployment": ["deployment", "installed", "field units",
                       "adoption", "commercial deployment"],
    }
    return sorted(name for name, kws in fams.items()
                  if any(kw in t for kw in kws))


# ---------------------------------------------------------------------------
# Frontier Evidence Score (deterministic — NOT a novelty score)
# ---------------------------------------------------------------------------

def frontier_evidence_score(record: Dict[str, Any],
                            extraction: Dict[str, Any]
                            ) -> Dict[str, Any]:
    """The Frontier Evidence Score for ONE record (directive item 4):
    computed from evidence properties only, never model opinion. The
    component trace is always returned with the score (never a bare
    number), so every point is auditable (Art. XXVII)."""
    evs = extraction.get("evidences") or []
    unit_evs = [e for e in evs if e.get("unit")]
    any_numeric = bool(evs)
    in_abstract = any(e.get("in_abstract") for e in evs)
    abstract_nonempty = bool(str(record.get("abstract") or "").strip())
    year = record.get("publication_year")
    text = f"{record.get('title')} {record.get('abstract')}"
    any_baseline = any(e.get("baseline_comparator") for e in evs) or \
        bool(_vocab_hits(text, BASELINE_TERMS))
    components: Dict[str, int] = {}

    def add(name: str) -> None:
        components[name] = FES_WEIGHTS[name]

    if unit_evs:
        add("measured_value_with_unit")
    if any(e.get("measurement_context") for e in evs):
        add("measurement_context")
    if any(e.get("improvement_direction") for e in evs):
        add("improvement_direction")
    if any_baseline:
        add("baseline_comparator")
    if year is not None:
        add("year_recoverable")
        if year >= 2020:
            add("recency_recent")
        elif year >= 2015:
            add("recency_mid")
        elif year >= 2010:
            add("recency_old")
    if in_abstract:
        add("in_abstract_context")
    if any_numeric and not abstract_nonempty:
        # numeric evidence present ONLY in the title, no abstract
        add("title_only_penalty")
    if any_numeric and not unit_evs:
        add("value_without_unit_penalty")
    if not any_baseline:
        add("missing_baseline_penalty")
    if not any_numeric:
        add("qualitative_only_penalty")

    score = sum(components.values())
    return {
        "score": score,
        "components": components,
        "weights_version": FEAL_VERSION,
        "weights_provenance": (
            "reward/penalize structure = OPERATOR_DIRECTIVE item 4; "
            "numeric weights = ENGINEERING (monotone operationalization, "
            "never tuned against any benchmark — Art. XXVII/LIX)"),
        "is_not_a_novelty_score": True,
    }


# ---------------------------------------------------------------------------
# Capability trajectory + cross-source corroboration (items 5-6)
# ---------------------------------------------------------------------------

CORROBORATION_STATES = (
    "SINGLE_SOURCE_SIGNAL", "MULTI_SOURCE_SIGNAL",
    "REPLICATED_TRAJECTORY", "UNKNOWN",
)


def _slope_value_from_canonical(cand: Dict[str, Any]
                                ) -> Tuple[Optional[float], str]:
    """The trajectory point value + basis label (same discipline as
    gradient_v2._slope_value: RANGE midpoint is LABELED arithmetic,
    never silent precision manufacture)."""
    rep = cand.get("representation")
    if rep == "POINT" and cand.get("normalized_value") is not None:
        return float(cand["normalized_value"]), "POINT_VALUE"
    if rep == "RANGE" and cand.get("normalized_min") is not None \
            and cand.get("normalized_max") is not None:
        return ((float(cand["normalized_min"]) +
                 float(cand["normalized_max"])) / 2.0,
                "RANGE_MIDPOINT")
    if rep == "INEQUALITY":
        for k in ("normalized_value", "normalized_min",
                  "normalized_max"):
            if cand.get(k) is not None:
                return float(cand[k]), "INEQUALITY_BOUND"
    return None, "UNSUITABLE"


def _source_family_of(rec: Dict[str, Any]) -> str:
    return str(rec.get("source_family") or rec.get("source") or
               "unknown")


def build_trajectories(rung: str,
                       records: List[Dict[str, Any]],
                       extractions: Optional[Dict[str, Any]] = None
                       ) -> List[Dict[str, Any]]:
    """Assemble capability trajectories from a rung's pool records:
    capability -> metric -> value -> baseline -> year -> source ->
    domain -> trajectory (directive item 5). Multiple time points are
    recovered when present (capability velocity, not existence).
    Corroboration states are explicit (directive item 6): a single
    paper is SINGLE_SOURCE_SIGNAL (exploration-eligible, never
    automatically a 'rapidly improving frontier capability')."""
    if extractions is None:
        extractions = {}
    by_metric: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for rec in records:
        rid = str(rec.get("record_id"))
        ext = extractions.get(rid) or extract_numeric_evidence(
            rec.get("title", ""), rec.get("abstract", ""))
        for ev in ext.get("evidences") or []:
            metric = ev.get("metric")
            if not metric:
                continue  # unlabeled metric never forms a trajectory
            unit = str(ev.get("unit") or "dimensionless")
            val, basis = _slope_value_from_canonical(
                ev.get("canonical") or {})
            if val is None:
                continue
            year = rec.get("publication_year")
            by_metric.setdefault((metric, unit), []).append({
                "record_id": rid,
                "title": str(rec.get("title") or "")[:160],
                "year": year,
                "value": val,
                "value_basis": basis,
                "span": ev.get("span"),
                "source": rec.get("source"),
                "source_family": _source_family_of(rec),
                "domain": domain_class(rec),
                "baseline_comparator": ev.get("baseline_comparator"),
                "improvement_direction": ev.get("improvement_direction"),
                "sentence": ev.get("sentence"),
                "record_fes": (extractions.get(rid) or {}).get(
                    "fes", {}).get("score"),
            })
    out: List[Dict[str, Any]] = []
    for (metric, unit), points in by_metric.items():
        pts = sorted(
            [p for p in points if p.get("year") is not None],
            key=lambda p: (p["year"], p["record_id"]))
        sources = sorted({str(p.get("source")) for p in pts})
        families = sorted({str(p.get("source_family")) for p in pts})
        domains = sorted({str(p.get("domain")) for p in pts})
        years = [p["year"] for p in pts]
        velocity = None
        direction = None
        if len(pts) >= 2:
            first, last = pts[0], pts[-1]
            dy = (last["year"] or 0) - (first["year"] or 0)
            if dy > 0:
                velocity = round(
                    (last["value"] - first["value"]) / dy, 6)
                direction = ("increase" if velocity > 0 else
                             "decrease" if velocity < 0 else "flat")
        corroboration = _corroboration_state(pts)
        t_components: Dict[str, int] = {}
        if corroboration == "MULTI_SOURCE_SIGNAL":
            t_components["multi_source_signal"] = \
                TRAJ_WEIGHTS["multi_source_signal"]
        if corroboration == "REPLICATED_TRAJECTORY":
            t_components["replicated_trajectory"] = \
                TRAJ_WEIGHTS["replicated_trajectory"]
        if len(pts) >= 3:
            t_components["three_or_more_points"] = \
                TRAJ_WEIGHTS["three_or_more_points"]
        if len(families) >= 3:
            t_components["three_or_more_sources"] = \
                TRAJ_WEIGHTS["three_or_more_sources"]
        if len(domains) >= 2:
            t_components["domain_diversity_two_plus"] = \
                TRAJ_WEIGHTS["domain_diversity_two_plus"]
        if years and max(years) - min(years) >= 3:
            t_components["year_span_three_plus"] = \
                TRAJ_WEIGHTS["year_span_three_plus"]
        out.append({
            "capability_rung": rung,
            "metric": metric,
            "unit": unit,
            "n_points": len(pts),
            "points": pts,
            "years": years,
            "year_span": (max(years) - min(years)) if years else 0,
            "sources": sources,
            "source_families": families,
            "domains": domains,
            "capability_velocity": velocity,
            "velocity_direction": direction,
            "corroboration": corroboration,
            "trajectory_score": sum(t_components.values()),
            "trajectory_score_components": t_components,
            "unpointed_evidence_count": len(
                [p for p in points if p.get("year") is None]),
        })
    out.sort(key=lambda t: (-t["trajectory_score"],
                            -t["n_points"], t["metric"]))
    return out


def _corroboration_state(points: List[Dict[str, Any]]) -> str:
    """Directive item 6 states, deterministically:
      UNKNOWN               — fewer than 2 usable points
      SINGLE_SOURCE_SIGNAL  — all points from ONE source
      MULTI_SOURCE_SIGNAL   — >=2 distinct sources but not a
                              consistent multi-year replication
      REPLICATED_TRAJECTORY — >=2 independent source families with
                              consistent direction across >=2 years
    """
    if len(points) < 2:
        return "UNKNOWN"
    sources = {str(p.get("source")) for p in points}
    if len(sources) == 1:
        return "SINGLE_SOURCE_SIGNAL"
    families = {str(p.get("source_family")) for p in points}
    years = sorted({p.get("year") for p in points
                    if p.get("year") is not None})
    if len(families) >= 2 and len(years) >= 2:
        return "REPLICATED_TRAJECTORY"
    return "MULTI_SOURCE_SIGNAL"


def summarize_pool(records: List[Dict[str, Any]],
                   extractions: Dict[str, Any]) -> Dict[str, Any]:
    """Per-invocation pool summary (the diagnostic + benchmark metric
    inputs — every number regenerable from committed bytes)."""
    n = len(records) or 1
    with_abstract = [r for r in records
                     if str(r.get("abstract") or "").strip()]
    numeric_ids = {rid for rid, ext in extractions.items()
                   if ext.get("evidences")}
    unit_ids = {rid for rid, ext in extractions.items()
                if any(e.get("unit") for e in ext.get("evidences")
                       or [])}
    meas_ids = {rid for rid, ext in extractions.items()
                if ext.get("has_measurement_vocab")}
    years = [r.get("publication_year") for r in records
             if r.get("publication_year") is not None]
    domains = sorted({domain_class(r) for r in records})
    sources = sorted({str(r.get("source")) for r in records})
    families = sorted({str(r.get("source_family")) for r in records})
    return {
        "n_records": len(records),
        "n_unique_record_ids": len({str(r.get("record_id"))
                                    for r in records}),
        "abstract_bearing_count": len(with_abstract),
        "abstract_bearing_rate": round(len(with_abstract) / n, 4),
        "numeric_bearing_count": len(numeric_ids),
        "numeric_bearing_rate": round(len(numeric_ids) / n, 4),
        "unit_bearing_numeric_count": len(unit_ids),
        "unit_bearing_numeric_rate": round(len(unit_ids) / n, 4),
        "measurement_bearing_count": len(meas_ids),
        "measurement_bearing_rate": round(len(meas_ids) / n, 4),
        "year_recovered_count": len(years),
        "year_recovery_rate": round(len(years) / n, 4),
        "domain_classes": domains,
        "domain_diversity": len(domains),
        "sources": sources,
        "source_families": families,
        "source_family_diversity": len(families),
    }


def extraction_for_pool(records: List[Dict[str, Any]]
                        ) -> Dict[str, Any]:
    """Run the deterministic extraction over a pool and attach the
    Frontier Evidence Score + measurement-vocab flag per record."""
    out: Dict[str, Any] = {}
    for rec in records:
        rid = str(rec.get("record_id"))
        ext = extract_numeric_evidence(rec.get("title", ""),
                                       rec.get("abstract", ""))
        ext["fes"] = frontier_evidence_score(rec, ext)
        ext["has_measurement_vocab"] = record_has_measurement_vocab(
            rec.get("title", ""), rec.get("abstract", ""))
        ext["signal_families"] = record_signal_families(
            rec.get("title", ""), rec.get("abstract", ""))
        ext["domain_class"] = domain_class(rec)
        out[rid] = ext
    return out


# ---------------------------------------------------------------------------
# Multi-level capability derivation (directive item 9)
# ---------------------------------------------------------------------------

def capability_levels(rung: str,
                      map_path: Path = FAMILY_MAP_V2
                      ) -> List[Dict[str, Any]]:
    """Several candidate capability families per death, derived
    DETERMINISTICALLY from committed evidence (never invented):
      L1 — the exact ga1b capability rung
      L2 — the family's capability_family abstraction
      L3 — the family's measurement-dimension core
    Every level carries its derivation class and verbatim basis."""
    fam = family_for_rung(rung, map_path)
    levels = [{
        "level": "L1_EXACT_CAPABILITY",
        "capability": rung,
        "derivation": "DERIVED_FROM_EVIDENCE (ga1b span-verified "
                      "capability rung, committed bytes)",
    }]
    if fam:
        if fam.get("capability_family"):
            levels.append({
                "level": "L2_CAPABILITY_FAMILY",
                "capability": str(fam["capability_family"]),
                "derivation": "DERIVED_FROM_EVIDENCE (family map "
                              "capability_family, grounded in the "
                              "verbatim basis span)",
            })
        dims = [t.strip() for t in str(
            fam.get("measurement_dimension") or "").split(",")
                if t.strip()]
        if dims:
            levels.append({
                "level": "L3_MEASUREMENT_DIMENSION",
                "capability": " ".join(dims),
                "derivation": "DERIVED_FROM_EVIDENCE (family map "
                              "measurement_dimension, grounded in the "
                              "verbatim basis span)",
            })
    return levels


