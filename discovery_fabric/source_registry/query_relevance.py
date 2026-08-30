"""QUERY_RELEVANCE measurement instrument — CEO directive 2026-08-30 ("finish
source maturity, not source count": measure `query_relevance` per source).

The problem this closes (maturity model v1.0.0 honest finding):
QUERY_RELEVANCE was UNMEASURED for every source. Per-record relevance
adjudication EXISTS in the discovery pipeline (discovery_modes/
device_failure.py: RELEVANT / IRRELEVANT_FILTERED with a transparent,
adjudicable basis) but was never aggregated per-source — and its outputs
are not persisted in run artifacts, so there was nothing to aggregate
from history.

This instrument runs a FIXED, COMMITTED probe battery per source and
adjudicates every returned record with THE SAME term-overlap method the
discovery pipeline already uses (consistency: the maturity measurement
and the pipeline adjudicator are one method, not two).

Constitutional anchors:
- Art. XXI.4: relevance must be independently established per record —
  the battery adjudicates EVERY returned record and records the basis.
- Art. XXVI: this is a measurement instrument, not a certification. Its
  output is builder-measured; the committed script is the reproduction
  command.
- Art. XXV: a provider failure during the battery leaves the source
  UNMEASURED for this run — never graded from failure.
- Art. XXVII: grade bands are ENGINEERING-class thresholds, declared here
  with justification, before aggregation.

Method (declared, deterministic):
1. BATTERY defines 2 fixed queries per source (grammar-honoring: each
   query uses the connector's own measured query grammar).
2. Every returned record is adjudicated RELEVANT iff the overlap between
   the query's content terms and the record's title+abstract/snippet
   terms is >= MIN_OVERLAP_TERMS (2 — identical to the pipeline rule in
   device_failure.py). For structure-parameterized endpoints where every
   record is by construction about the query (e.g. NHTSA
   make|model|year), a per-source STRUCTURAL_RELEVANCE note replaces the
   term rule and is disclosed per record.
3. Per source: relevant_rate = relevant / adjudicated across all battery
   queries that returned records; grammar = per-query status.
4. Grade bands (ENGINEERING class, disclosed):
     3  rate >= 2/3   — majority of returned records on-domain
     2  1/3 <= rate < 2/3
     1  rate < 1/3 with >= 1 query returning records (off-domain flood)
   UNMEASURED — no battery query returned records (failed/empty/blocked)
   or the source is metered (live probes suppressed by policy).

Threshold justification (Art. XXVII): a discovery engine that feeds
retrieved records into evidence needs the majority of them on-domain
when its queries are already domain-specific (2/3 = STRONG); 1/3 is the
minimum at which a returned set still contains a usable on-domain
signal (ADEQUATE); below that the source answers the grammar but not
the question (WEAK). These are ENGINEERING judgment thresholds about
the ENGINE's consumption needs, not claims about the providers.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Adjudication vocabulary (mirrors discovery_modes/device_failure.py)
# ---------------------------------------------------------------------------

RELEVANT = "RELEVANT"
IRRELEVANT = "IRRELEVANT_FILTERED"
MIN_OVERLAP_TERMS = 2  # identical rule to the pipeline adjudicator

_STOP = {
    "the", "a", "an", "of", "in", "for", "and", "or", "to", "with",
    "on", "by", "at", "from", "is", "are", "was", "were", "be", "been",
    "name", "brand", "device", "reason", "recall", "supplement", "exists",
    "applicant", "registration",
}


def _fold(term: str) -> str:
    """Deterministic plural folding for term comparison.

    Rationale (instrument defect found on the 2026-08-30 battery):
    'lithium battery safety' matched 'Battery' but missed 'batteries' —
    no-stemming tokenization undercounts relevance on plural titles
    (DOE OSTI graded WEAK largely on this artifact). A deterministic
    fold (ies->y, trailing s strip) is disclosed here and applied
    uniformly to query and record terms alike.
    """
    if len(term) > 3 and term.endswith("ies"):
        return term[:-3] + "y"
    if len(term) > 3 and term.endswith("s") and not term.endswith("ss"):
        return term[:-1]
    return term


def terms(text: str) -> List[str]:
    """Content terms of a string (same tokenization family as the pipeline)."""
    return [_fold(t) for t in re.split(r"[^a-z0-9]+", (text or "").lower())
            if len(t) > 2 and t not in _STOP]


# ---------------------------------------------------------------------------
# keyword_form — engine-level query-form discipline (2026-08-31, CEO
# source-routing directive). Single implementation shared by the UI problem
# builder and the engine's prior-art collision stage: search APIs answer
# KEYWORD queries; interrogative prefixes, sentence punctuation and filler
# words measurably degrade or zero results (measured on DOE OSTI 0.175
# relevance failure investigation; measured on the patent collision stage
# where 'implement multi-sensory monitoring system using x-ray' returned
# surgical robots as nearest prior art for a battery-sensing candidate).
# ---------------------------------------------------------------------------

_KEYWORD_FILLER = {
    "the", "a", "an", "of", "in", "for", "and", "or", "to", "with",
    "on", "by", "at", "from", "is", "are", "was", "were", "be", "been",
    "being", "do", "does", "did", "can", "could", "should", "would",
    "how", "why", "what", "when", "which", "where", "who", "that", "this",
    "these", "those", "it", "its", "their", "my", "your", "i", "we",
    "implement", "implementing", "using", "use", "used", "within",
    "system", "method", "apparatus", "device",
}

_INTERROGATIVE_RE = re.compile(
    r"^(how|why|what|when|which|where|who|can|could|should|is|are|do|does|did)\b[ \-]?",
    re.IGNORECASE,
)


def keyword_form(query: str, max_terms: int = 10) -> str:
    """Normalize a search string to keyword form (deterministic, disclosed).

    Transforms (no stemming, no synonym maps — Art. II spirit: nothing is
    inferred):
      1. strip an interrogative prefix ('How can ...' -> '...')
      2. strip sentence punctuation ('?', '.', '!')
      3. drop filler tokens that carry no query content
      4. cap at max_terms content terms, preserving order
    Returns "" when nothing content-bearing remains.
    """
    q = _INTERROGATIVE_RE.sub("", (query or "").strip())
    q = q.strip().rstrip("?.! ").strip()
    tokens = [t for t in re.split(r"[^A-Za-z0-9\-]+", q) if t]
    kept = [t for t in tokens if t.lower() not in _KEYWORD_FILLER]
    return " ".join(kept[:max_terms])


def is_question_form(query: str) -> bool:
    """True when a query is an interrogative sentence, not keywords.

    Deterministic: trailing '?' OR (interrogative first word AND >= 5
    tokens). 'lithium battery safety' never trips; 'How can hydrogen
    embrittlement be prevented in high-strength steels?' always does.
    """
    q = (query or "").strip()
    if q.endswith("?"):
        return True
    words = q.split()
    first = words[0].lower() if words else ""
    return first in {
        "how", "why", "what", "when", "which", "where", "who", "can",
        "could", "should", "is", "are", "do", "does", "did",
    } and len(words) >= 5


def query_content_terms(query: str) -> List[str]:
    """Content terms of a query, honoring field:value grammar (openFDA).

    'device.brand_name:"infusion pump"' -> ['infusion', 'pump'] — the field
    name is grammar, the value is content.
    """
    q = query
    m = re.match(r"^([a-z0-9_.]+):(.*)$", q)
    field = m.group(1) if m else ""
    q = m.group(2) if m else q
    q = re.sub(r"\s+AND\s+[a-z0-9_.]+:?[^A-Za-z]*$", "", q)  # ES suffix clause
    return terms(q), field


def record_text(rec: Dict[str, Any]) -> str:
    """Title + abstract/snippet + structured text fields of a record dict.

    2026-08-31 (relevance-failure investigation): added `subjects` (and
    singular `subject`) — DOE OSTI records carry subject-term lists the
    old rule never saw. This is evidence EXPANSION (Art. VII allowed fix
    #3: obtain better evidence), not threshold weakening: the >= 2
    term-overlap rule, MIN_OVERLAP_TERMS and the band thresholds are all
    UNCHANGED — the adjudicator simply receives text the provider already
    returned that the connector was discarding.
    """
    n = rec.get("normalized", {}) or {}
    parts = [rec.get("title") or ""]
    for k in ("abstract", "snippet", "summary", "component", "problem",
              "purpose", "description", "condition", "conditions",
              "keywords", "applicant", "defect_summary", "consequence",
              "hazards", "products", "cause", "components", "subjects",
              "subject"):
        v = n.get(k) or rec.get(k)
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, list):
            parts.extend(str(x) for x in v[:8])
    return " ".join(parts)


def adjudicate_record(rec: Dict[str, Any], query: str) -> Dict[str, Any]:
    """Adjudicate one record against one query (transparent basis).

    Threshold rule (instrument defect fixed 2026-08-30 after the first
    battery run): required overlap is min(MIN_OVERLAP_TERMS, number of
    query content terms). The >=2 rule exists to prevent single-word
    accidental collisions on MULTI-concept queries; for a single-concept
    query ('aspirin', 'medtronic', '10993') the single term IS the
    concept and demanding 2 overlaps is impossible-by-construction.

    Field-binding rule (Art. II spirit): when the query uses a
    field:value grammar, the value is ALSO checked against the
    corresponding normalized field (e.g. 'applicant:medtronic' checks
    normalized.applicant) — the query binds to a field, and the field
    is where exact evidence lives, not the title.
    """
    qterms_list, field = query_content_terms(query)
    qterms = set(qterms_list)
    rterms = set(terms(record_text(rec)))
    overlap = sorted(qterms & rterms)
    required = min(MIN_OVERLAP_TERMS, len(qterms)) if qterms else 1
    relevant = len(overlap) >= required
    basis_extra = ""
    if field and relevant is False:
        # field-bound second chance: exact substring of the value in the
        # targeted normalized field (target key = last segment of field)
        target_key = field.split(".")[-1]
        n = rec.get("normalized", {}) or {}
        target_val = n.get(target_key)
        raw_value = re.sub(r'^[a-z0-9_.]+:', "", query).strip('" ')
        if isinstance(target_val, str) and raw_value.lower() in target_val.lower():
            relevant = True
            basis_extra = (f"; field-bound match: normalized.{target_key} "
                           f"contains {raw_value!r}")
    return {
        "record_id": rec.get("record_id"),
        "title": (rec.get("title") or "")[:140],
        "relevance": RELEVANT if relevant else IRRELEVANT,
        "relevance_basis": {
            "method": f"term overlap >= {required} (min({MIN_OVERLAP_TERMS}, "
                      f"{len(qterms)} query terms)) between query content "
                      f"terms and record text terms (transparent, "
                      f"adjudicable — same rule family as the pipeline)"
                      f"{basis_extra}",
            "overlapping_terms": overlap,
        },
    }


# ---------------------------------------------------------------------------
# The battery (fixed, committed — reproduction = run the script)
# ---------------------------------------------------------------------------
# Two queries per source. Query 1 keeps the historically proven health
# grammar (domain: medical/transport baseline). Query 2 probes a DIFFERENT
# domain than the engine's historical medical core — the cross-domain
# generality the CEO's six-domain benchmark needs. Queries are
# grammar-honoring per connector (measured grammar classes from the
# 2026-08-29/30 integration rounds).

BATTERY: Dict[str, List[str]] = {
    # --- SCIENTIFIC (free text) ---
    "europepmc":       ["hydrocephalus shunt valve", "battery thermal runaway"],
    "pubmed":          ["hydrocephalus shunt valve", "battery thermal runaway"],
    "openalex":        ["hydrocephalus shunt valve", "battery thermal runaway"],
    "semantic_scholar": ["hydrocephalus shunt valve", "battery thermal runaway"],
    "crossref":        ["hydrocephalus shunt valve", "battery thermal runaway"],
    "elsevier_scopus": ["hydrocephalus shunt valve", "battery thermal runaway"],
    "lens_scholarly":  ["hydrocephalus shunt valve", "battery thermal runaway"],
    "nasa_ntrs":       ["battery thermal runaway", "turbine blade fatigue"],
    "doe_osti":        ["lithium battery safety", "wind turbine gearbox failure"],
    "arxiv":           ["battery thermal runaway", "crack propagation composite"],
    # --- PATENT (free text) ---
    "lens_patent":     ["hydrocephalus shunt valve", "lithium battery thermal management"],
    "google_patents":  ["hydrocephalus shunt valve", "lithium battery thermal management"],
    "patsnap_eureka":  ["hydrocephalus shunt valve", "lithium battery thermal management"],
    # --- REGULATORY (openFDA grammar) ---
    "fda_510k":        ['device_name:"infusion pump"', 'device_name:"hip implant"'],
    "fda_pma":         ['applicant:medtronic', 'applicant:boston scientific'],
    "fda_classification": ['device_name:"infusion pump"', 'device_name:"hip implant"'],
    "fda_udi":            ['brand_name:"infusion pump"', 'brand_name:"hip system"'],
    "fda_registrationlisting": ['registration.name:medtronic', 'registration.name:stryker'],
    # --- ADVERSE_EVENT / RECALL ---
    "fda_maude":       ['device.brand_name:"infusion pump"', "device.brand_name:ventilator"],
    "fda_recall":      ['reason_for_recall:"infusion pump"', 'reason_for_recall:"hip implant"'],
    "nhtsa_recalls":   ["toyota|camry|2020", "ford|explorer|2019"],
    # --- NEW FAILURE UNIVERSE (2026-08-30, measured live) ---
    "nhtsa_complaints": ["toyota|camry|2020", "ford|explorer|2019"],
    "cpsc_recalls":    ["2026-06-01", "2026-01-01"],
    "usgs_earthquakes": ["2026-07-01", "2026-01-01"],
    "fra_rail_accidents": ["2023-01-01", "2020-01-01"],
    # --- CLINICAL ---
    "clinicaltrials_gov": ["hydrocephalus", "heart failure"],
    # --- MATERIALS / CHEMISTRY / BIOLOGY ---
    "cod_optimade":    ["hydroxyapatite", "silicon carbide"],
    "nist_webbook":    ["zirconium dioxide", "titanium"],
    "materials_project": ["TiO2", "LiFePO4"],
    "pubchem":         ["aspirin", "ibuprofen"],
    "uniprot":         ["insulin", "hemoglobin"],
    "chembl":          ["aspirin", "ibuprofen"],
    "rcsb_pdb":        ["insulin", "hemoglobin"],
    # --- STANDARDS ---
    "fda_recognized_standards": ["10993", "60601"],
    "ecfr_title21":    ["888", "820"],
    # --- MANUFACTURING ---
    "fda_pma_supplements": ['supplement_reason:"Process Change - Manufacturer/Sterilizer/Packager/Supplier"', 'supplement_reason:"Process Change - Manufacturing Site"'],
    "manufacturing_literature": ["additive manufacturing", "injection molding"],
    "gudid_sterilization": ['brand_name:"catheter" AND _exists_:sterilization', 'brand_name:"implant" AND _exists_:sterilization'],
    # --- COMMERCIAL ---
    "gudid_commercial": ['brand_name:"hip system"', 'brand_name:"infusion pump"'],
}

# Sources deliberately NOT in the battery and why (disclosed, not silent):
BATTERY_EXCLUSIONS: Dict[str, str] = {
    "patentbear": "metered (20 req/month) — live probes suppressed by policy",
    "patentsnap_eureka_note": "patsnap_eureka IS probed (key present, non-metered)",
    "fda_denovo": "connector absent (route blocked — measured 2026-08-30)",
    "who_ictrp": "connector absent (legacy API retired — measured 2026-08-30)",
    "wipo_patentscope": "connector absent (key-required, no credential)",
    "iso_catalogue": "connector absent (bot-blocked)",
    "astm_standards": "connector absent (paywalled full text)",
    "eudamed": "connector absent (EC registration required)",
    "epo_ops": "connector exists; AUTH_FAILED expected without credential — "
               "probe would burn nothing but also measures nothing about "
               "relevance; availability dimension already records the block",
    "uspto_odp": "same class as epo_ops (credential-blocked)",
    "google_bigquery_patents": "connector exists; billing-required",
    "materials_project_note": "materials_project IS probed to re-measure the "
                              "IP block with the CEO-provided key",
}

# Structure-parameterized endpoints: every returned record is BY CONSTRUCTION
# about the query (e.g. NHTSA recallsByVehicle returns only that vehicle's
# campaigns). Relevance is adjudicated structurally + spot-checked, and the
# method note is attached per record.
STRUCTURAL_RELEVANCE: Dict[str, str] = {
    "nhtsa_complaints": (
        "vehicle-parameterized endpoint: every returned record is by "
        "construction an owner complaint for the queried make|model|year; "
        "relevance adjudicated structurally, spot-checked via component/"
        "summary field presence"
    ),
    "nhtsa_recalls": (
        "vehicle-parameterized endpoint: every returned record is by "
        "construction a recall campaign for the queried make|model|year; "
        "relevance adjudicated structurally (record belongs to the queried "
        "vehicle), spot-checked via component field presence"
    ),
    "gudid_sterilization": (
        "boolean-filtered GUDID view: every returned record carries the "
        "queried brand name AND a sterilization field by construction"
    ),
    # date-window grammars: the query IS the filter — every returned
    # record satisfies it by construction; term overlap is meaningless
    # for a date floor
    "cpsc_recalls": (
        "date-window grammar (RecallDateStart): every returned record is a "
        "recall published on/after the queried date by construction"
    ),
    "usgs_earthquakes": (
        "parameterized filter (starttime + minmagnitude): every returned "
        "record is a measured seismic event satisfying both parameters by "
        "construction"
    ),
    "fra_rail_accidents": (
        "date-floor grammar ($where date >= X): every returned record is a "
        "Form 54 rail accident on/after the queried date by construction"
    ),
    # registry-number lookups: the endpoint resolves the number directly
    "fda_recognized_standards": (
        "standard-number lookup: records returned for '10993' carry that "
        "number in their designation by construction of the search"
    ),
    "ecfr_title21": (
        "CFR part lookup: records returned for '888' are sections of that "
        "part by construction of the endpoint"
    ),
}


# ---------------------------------------------------------------------------
# Aggregation + grading
# ---------------------------------------------------------------------------

#
# Date-window grammars: the query is a filter parameter, not content —
# two different past dates both include the newest page, so IDENTICAL
# record sets are EXPECTED, not a query-ignored defect. The query-
# differentiation check skips them (flag would be a false positive).
DATE_WINDOW_GRAMMARS = {"cpsc_recalls", "usgs_earthquakes", "fra_rail_accidents"}


def aggregate(results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    """Aggregate per-query battery results into per-source summaries.

    Also computes QUERY_DIFFERENTIATION: when two different battery
    queries returned >1 record each and the record-id sets are IDENTICAL,
    the source is flagged QUERY_POSSIBLY_IGNORED — the defect class found
    live on DOE OSTI 2026-08-30 (`query=` param silently ignored;
    different queries, byte-identical record sets). This is a HYPOTHESIS
    flag for investigation, not a verdict (small corpora can legitimately
    overlap).
    """
    agg: Dict[str, Dict[str, Any]] = {}
    for sid, queries in results.items():
        structural = STRUCTURAL_RELEVANCE.get(sid)
        adjudicated = 0
        relevant = 0
        per_query = []
        years: List[int] = []
        id_sets: List[tuple] = []
        for q in queries:
            recs = q.get("records") or []
            adj = []
            for r in recs:
                years.extend(extract_record_years(r))
                if structural:
                    # structural relevance: record is by construction about
                    # the parameterized query; spot-check = non-empty text
                    has_text = bool((r.get("title") or "").strip()) or bool(
                        record_text(r).strip())
                    adj.append({
                        "record_id": r.get("record_id"),
                        "title": (r.get("title") or "")[:140],
                        "relevance": RELEVANT if has_text else IRRELEVANT,
                        "relevance_basis": {
                            "method": "STRUCTURAL: " + structural,
                            "overlapping_terms": [],
                        },
                    })
                else:
                    adj.append(adjudicate_record(r, q["query"]))
            n_rel = sum(1 for a in adj if a["relevance"] == RELEVANT)
            adjudicated += len(adj)
            relevant += n_rel
            if len(recs) > 1:
                id_sets.append((q["query"], tuple(sorted(
                    str(r.get("record_id")) for r in recs))))
            per_query.append({
                "query": q["query"],
                "status": q.get("status"),
                "retrieved": len(recs),
                "relevant": n_rel,
                "rate": round(n_rel / len(adj), 3) if adj else None,
                "adjudications": adj,
            })
        rate = (relevant / adjudicated) if adjudicated else None
        differentiation = "NOT_EVALUABLE"
        if sid in DATE_WINDOW_GRAMMARS:
            differentiation = "PARAMETERIZED_DATE_WINDOW"
        elif len(id_sets) >= 2:
            sets = [s for _, s in id_sets]
            if all(s == sets[0] for s in sets[1:]):
                differentiation = "QUERY_POSSIBLY_IGNORED"
            else:
                differentiation = "DISTINCT"
        agg[sid] = {
            "queries": per_query,
            "adjudicated_records": adjudicated,
            "relevant_records": relevant,
            "relevant_rate": round(rate, 3) if rate is not None else None,
            "query_differentiation": differentiation,
            "measured_temporal_span": measured_temporal_span(years),
        }
    return agg


# ---------------------------------------------------------------------------
# TEMPORAL_SPAN harvest (dates on battery records — CEO dimension
# `temporal_coverage`; converts UNMEASURED into MEASURED where the engine
# has actually retrieved date-bearing records)
# ---------------------------------------------------------------------------

_YEAR_RE = re.compile(r"\b(1[6-9]\d\d|20\d\d)\b")
_DATE_KEYS = ("date", "year", "publication_date", "pub_year", "report_date",
              "event_date", "received_date", "decision_date", "component_date",
              "last_update", "completion_date", "start_date")


def extract_record_years(rec: Dict[str, Any]) -> List[int]:
    """Years found in a record's date-bearing normalized fields.

    Deliberately NARROW: only declared date-ish keys, only 1500-2099
    4-digit values. Title text is NOT mined (a title mentioning '1970'
    is not a publication date). If no date field exists, the record
    contributes nothing — Art. XXV.
    """
    n = rec.get("normalized", {}) or {}
    out: List[int] = []
    for k, v in n.items():
        kl = k.lower()
        if not any(d in kl for d in _DATE_KEYS):
            continue
        if isinstance(v, (int, float)) and 1500 <= v <= 2099:
            out.append(int(v))
        elif isinstance(v, str):
            m = _YEAR_RE.search(v)
            if m:
                y = int(m.group(1))
                if 1500 <= y <= 2099:
                    out.append(y)
    return out


def measured_temporal_span(years: List[int]) -> Optional[Dict[str, Any]]:
    """Span of years across date-bearing retrieved records (may be None)."""
    if not years:
        return None
    return {
        "min_year": min(years),
        "max_year": max(years),
        "span_years": max(years) - min(years),
        "records_with_dates": len(years),
    }


def grade_temporal_measured(span: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Grade TEMPORAL_COVERAGE from measured retrieved-record span.

    Bands mirror the declared-span bands in maturity.py (>=40y=3, >=20y=2,
    else 1) so the two bases are comparable. Disclosed limitation: this
    measures the span of records THE ENGINE RETRIEVED, not the corpus —
    a floor on the corpus span, never a ceiling.
    """
    if not span:
        return {
            "grade": "UNMEASURED", "basis": "UNMEASURED",
            "evidence": "no date-bearing records in the battery",
            "rationale": "Art. XXV: not inferable",
        }
    sy = span["span_years"]
    g = 3 if sy >= 40 else (2 if sy >= 20 else 1)
    return {
        "grade": g, "basis": "MEASURED",
        "evidence": f"retrieved records span {span['min_year']}-{span['max_year']} "
                    f"({sy}y across {span['records_with_dates']} date-bearing records)",
        "rationale": "measured floor on corpus span (records actually "
                     "retrieved by the engine, not the full corpus); bands "
                     ">=40y=3, >=20y=2, else 1 — identical to the declared-"
                     "span bands",
    }


def grade_query_relevance(summary: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Grade one source's aggregate (bands declared in module docstring)."""
    if not summary or not summary.get("adjudicated_records"):
        return {
            "grade": "UNMEASURED", "basis": "UNMEASURED",
            "evidence": "no battery query returned records this run "
                        "(failed / empty / blocked) — Art. XXV: not graded",
            "rationale": "relevance quality is not inferable from provider "
                         "failure or definitive empties",
        }
    rate = summary["relevant_rate"]
    diff = summary.get("query_differentiation")
    if diff == "QUERY_POSSIBLY_IGNORED":
        return {
            "grade": 1, "basis": "MEASURED",
            "evidence": f"rate {rate:.0%} BUT different battery queries "
                        f"returned IDENTICAL record-id sets — the query "
                        f"parameter is possibly ignored (defect class found "
                        f"live on DOE OSTI 2026-08-30)",
            "rationale": "a source that returns the same records regardless "
                         "of query provides no query-relevant evidence; "
                         "flagged for investigation (hypothesis, Art. "
                         "XXI.8-analog)",
        }
    if rate >= 2 / 3:
        g = 3
    elif rate >= 1 / 3:
        g = 2
    else:
        g = 1
    return {
        "grade": g, "basis": "MEASURED",
        "evidence": f"{summary['relevant_records']}/{summary['adjudicated_records']} "
                    f"battery records adjudicated relevant "
                    f"(rate {rate:.0%}); query_differentiation={diff}",
        "rationale": "ENGINEERING bands (Art. XXVII, declared in "
                     "query_relevance.py): >=2/3 majority on-domain = 3; "
                     ">=1/3 usable signal = 2; <1/3 off-domain flood = 1",
    }
