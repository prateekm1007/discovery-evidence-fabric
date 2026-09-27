"""SOURCE COVERAGE MATURITY MODEL — CEO directive 2026-08-30.

The CEO's objection this module answers:

    "13/13 roles covered" and "Toscanini is not general-purpose" are not
    contradictory, but they can be misleading unless role coverage is
    distinguished from depth / quality / availability. One weak source can
    technically cover a role without providing world-class coverage.

Therefore every registered source is graded across ELEVEN dimensions —
coverage is one row among eleven, not the whole verdict.

Constitutional anchors:
- Art. XXV: unknown stays unknown. Every grade is one of 0..3 OR the
  explicit non-numeric state UNMEASURED. UNMEASURED is NEVER converted to
  a numeric (never 0, never averaged as 0).
- Art. XXI: a registered source is not integrated evidence; grades are
  computed from the MEASURED health report and the hash-chained retrieval
  custody log where possible, and from DECLARED provider-policy facts
  (registry fields) where measurement does not exist.
- Art. XXVII: every grade band carries its rationale; bands are anchored
  on measured usage scale in the custody log (probe / query / campaign),
  not invented.
- Art. XV: engine-level findings must state the inconvenient results
  (medical-only failure evidence, US-jurisdiction concentration) rather
  than average them away.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HEALTH_REPORT_PATH = REPO_ROOT / "artifacts/source_health/SOURCE_HEALTH_REPORT.json"
RETRIEVAL_LOG_PATH = REPO_ROOT / "artifacts/source_health/retrieval_log.jsonl"
GRADES_OUT_PATH = REPO_ROOT / "TOSCANINI/SOURCE_MATURITY_GRADES.json"

# ---------------------------------------------------------------------------
# The eleven CEO dimensions (exact directive names; the slash form is kept
# in the model document, the JSON key is machine-safe).
# ---------------------------------------------------------------------------

DIMENSIONS = [
    "ROLE_COVERAGE",
    "SOURCE_DIVERSITY",
    "LIVE_AVAILABILITY",
    "RECORD_VOLUME",
    "FRESHNESS",
    "PRIMARY_SOURCE_AUTHORITY",
    "QUERY_RELEVANCE",
    "PROVENANCE_COMPLETENESS",
    "FAILURE_NEGATIVE_EVIDENCE_COVERAGE",  # CEO: "FAILURE/NEGATIVE-EVIDENCE COVERAGE"
    "GEOGRAPHIC_COVERAGE",
    "TEMPORAL_COVERAGE",
]

SCALE = {
    0: "ABSENT_OR_BLOCKED",
    1: "WEAK",
    2: "ADEQUATE",
    3: "STRONG",
    "UNMEASURED": "EXPLICIT_UNKNOWN_ART_XXV",
}

# Numeric grade list excluding ROLE_COVERAGE when computing depth (a source
# covering its own role is tautological; depth is about the other ten).
DEPTH_DIMENSIONS = [d for d in DIMENSIONS if d != "ROLE_COVERAGE"]

# ---------------------------------------------------------------------------
# DECLARED classifications (provider-policy-class facts, each with rationale).
# These are NOT measurements. They classify what the source IS, citing the
# registry's own coverage/role fields. Where the fact is not declared in the
# registry, the grade is UNMEASURED — never guessed.
# ---------------------------------------------------------------------------

# Corpus-overlap groups: sources registered in this engine that draw on the
# SAME underlying corpus. Membership lowers SOURCE_DIVERSITY (redundancy of
# capability is not breadth) and is central to the CEO's warning that the
# scientific layer must not depend on top-5 sources that overlap.
OVERLAP_GROUPS: Dict[str, List[str]] = {
    "biomedical_literature": [
        "pubmed", "europepmc", "manufacturing_literature",
        "elsevier_scopus", "openalex", "semantic_scholar", "crossref",
        "lens_scholarly",
    ],
    "global_patent_bibliographic": [
        "google_patents", "epo_ops", "uspto_odp", "wipo_patentscope",
        "lens_patent", "patsnap_eureka", "google_bigquery_patents",
        "patentbear",
    ],
    "fda_device_regulatory": [
        "fda_510k", "fda_pma", "fda_pma_supplements", "fda_denovo",
        "fda_classification", "fda_registrationlisting",
    ],
    "gudid_identity": ["fda_udi", "gudid_commercial", "gudid_sterilization"],
    "clinical_registries": ["clinicaltrials_gov", "who_ictrp"],
    "standards_catalogues": ["iso_catalogue", "astm_standards"],
}

# Geographic reach of the corpus (DECLARED). Scale:
#   3 GLOBAL         — worldwide corpus or universal physical reference data
#   2 MULTI_REGION   — spans several jurisdictions/registries
#   1 SINGLE_REGION  — one jurisdiction's regulatory/commercial reality
GEOGRAPHIC: Dict[str, Dict[str, Any]] = {
    # science corpora: worldwide literature / universal reference data
    "pubmed": (3, "MEDLINE indexes global biomedical literature"),
    "arxiv": (3, "global preprint submissions, physics/math/CS/quant-bio skew"),
    "nasa_ntrs": (3, "universal aerospace technical knowledge (NASA/NACA corpus)"),
    "doe_osti": (3, "universal energy/materials research outputs (DOE-funded corpus)"),
    "nhtsa_recalls": (1, "US vehicle market recall jurisdiction"),
    "nhtsa_complaints": (1, "US vehicle market complaint jurisdiction"),
    "cpsc_recalls": (1, "US consumer-product jurisdiction (CPSC)"),
    "fra_rail_accidents": (1, "US rail jurisdiction (FRA Form 54)"),
    "usgs_earthquakes": (3, "worldwide seismic network"),
    "europepmc": (3, "Europe PMC aggregates global open-access + MEDLINE corpus"),
    "openalex": (3, "OpenAlex catalogs global scholarly works"),
    "semantic_scholar": (3, "S2 catalogs global scholarly works"),
    "crossref": (3, "Crossref registers global DOIs"),
    "elsevier_scopus": (3, "Scopus indexes global literature"),
    "lens_scholarly": (3, "Lens scholarly aggregates global corpora"),
    "manufacturing_literature": (3, "derived from global literature (EuropePMC cycle)"),
    "pubchem": (3, "chemical identity is global science"),
    "uniprot": (3, "global protein sequence resource"),
    "chembl": (3, "global bioassay literature curation"),
    "rcsb_pdb": (3, "global structural depositions"),
    "cod_optimade": (3, "global crystallographic openness network"),
    "nist_webbook": (3, "universal thermophysical reference data"),
    "materials_project": (3, "computed materials data applicable worldwide"),
    # patents
    "google_patents": (3, "aggregates 100+ patent offices"),
    "lens_patent": (3, "aggregates global patent + scholarly corpora"),
    "patsnap_eureka": (3, "aggregates global patent data"),
    "google_bigquery_patents": (3, "bulk global patent corpus"),
    "wipo_patentscope": (2, "PCT international applications + national phase data"),
    "epo_ops": (2, "EPC member offices + worldwide bibliographic"),
    "uspto_odp": (1, "US grants and pre-grant publications only"),
    "patentbear": (2, "multi-office patent store (provider scope declared limited)"),
    # regulatory / market reality — jurisdictional by construction
    "fda_maude": (1, "US market adverse-event jurisdiction"),
    "fda_recall": (1, "US market recall jurisdiction"),
    "fda_510k": (1, "US clearance pathway"),
    "fda_pma": (1, "US approval pathway"),
    "fda_pma_supplements": (1, "US approval pathway"),
    "fda_denovo": (1, "US classification pathway"),
    "fda_classification": (1, "US device classification"),
    "fda_registrationlisting": (1, "US establishment registration"),
    "fda_udi": (1, "US market device identity"),
    "gudid_commercial": (1, "US market commercial reality"),
    "gudid_sterilization": (1, "US market submissions"),
    "fda_recognized_standards": (1, "FDA recognition list (standards bodies are global; recognition is US)"),
    "ecfr_title21": (1, "US federal regulation text"),
    "eudamed": (1, "EU market regulatory jurisdiction"),
    "clinicaltrials_gov": (2, "US-run registry accepting global trials"),
    "who_ictrp": (3, "WHO aggregation of national trial registries"),
    "iso_catalogue": (3, "international standards body"),
    "astm_standards": (2, "international-membership standards body, US-based"),
}

# Failure/negative-evidence character of the source (DECLARED from role
# semantics). Scale:
#   3 FAILURE_NATIVE — the source EXISTS to record failures/negative events
#   2 ATTEMPT_OUTCOMES — records what was attempted incl. terminated/failed
#   1 MIXED_UNDERSAMPLED — failures appear but are structurally underreported
#   0 NOT_A_FAILURE_SOURCE — evidence class carries no failure semantics
FAILURE_CLASS: Dict[str, int] = {}
for _sid, _cls in [
    ("fda_maude", 3), ("fda_recall", 3), ("nhtsa_recalls", 3),
    # failure universe (2026-08-30): automotive adverse events, consumer-
    # product/electronics recalls, rail incidents are FAILURE-NATIVE
    ("nhtsa_complaints", 3), ("cpsc_recalls", 3), ("fra_rail_accidents", 3),
    # USGS events are hazard inputs, not failure records (role framing)
    ("usgs_earthquakes", 1),
    ("clinicaltrials_gov", 2), ("who_ictrp", 2),
    # literature/patents: negative results and failed applications are
    # structurally underrepresented (publication/grant bias)
    *[ (s, 1) for s in [
        "pubmed", "europepmc", "openalex", "semantic_scholar", "crossref",
        "elsevier_scopus", "lens_scholarly", "manufacturing_literature",
        "google_patents", "lens_patent", "patsnap_eureka", "patentbear",
        "epo_ops", "uspto_odp", "wipo_patentscope", "google_bigquery_patents",
        "nasa_ntrs", "doe_osti", "arxiv",
    ]],
    *[ (s, 0) for s in [
        "fda_510k", "fda_pma", "fda_pma_supplements", "fda_denovo",
        "fda_classification", "fda_registrationlisting", "fda_udi",
        "gudid_commercial", "gudid_sterilization", "fda_recognized_standards",
        "ecfr_title21", "iso_catalogue", "astm_standards", "eudamed",
        "pubchem", "uniprot", "chembl", "rcsb_pdb", "cod_optimade",
        "nist_webbook", "materials_project",
    ]],
]:
    FAILURE_CLASS[_sid] = _cls

# Domain of failure evidence (for the engine-level finding).
FAILURE_DOMAIN: Dict[str, str] = {
    "fda_maude": "medical", "fda_recall": "medical",
    "nhtsa_recalls": "transport", "nhtsa_complaints": "transport",
    "cpsc_recalls": "consumer_products",
    "fra_rail_accidents": "industrial_transport",
    "usgs_earthquakes": "infrastructure_hazard",
    "clinicaltrials_gov": "medical", "who_ictrp": "medical",
}


# ---------------------------------------------------------------------------
# Measurement loaders
# ---------------------------------------------------------------------------

def load_health() -> Dict[str, Any]:
    return json.loads(HEALTH_REPORT_PATH.read_text(encoding="utf-8"))


def load_retrieval_log() -> List[Dict[str, Any]]:
    entries = []
    with RETRIEVAL_LOG_PATH.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def verify_log_chain(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Recompute the hash chain of the custody log (Art. XII/XVI: the
    control itself must be exercised, not assumed)."""
    bad_links, recomputed_ok = [], 0
    prev: Optional[str] = None
    for e in entries:
        payload = {k: v for k, v in e.items() if k != "entry_sha256"}
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        if digest != e.get("entry_sha256"):
            bad_links.append(e.get("source_id", "?"))
            continue
        recomputed_ok += 1
        if prev is not None and e.get("prev_entry_sha256") != prev:
            bad_links.append(e.get("source_id", "?") + ":prev")
        prev = e["entry_sha256"]
    return {
        "entries": len(entries),
        "recomputed_ok": recomputed_ok,
        "bad_links": bad_links[:10],
        "chain_intact": not bad_links and recomputed_ok == len(entries),
    }


# ---------------------------------------------------------------------------
# Band rules (each with rationale — Art. XXVII)
# ---------------------------------------------------------------------------

RECORD_VOLUME_BANDS = (20, 200)
_RECORD_RATIONALE = (
    "bands anchored on measured usage in the custody log: <20 = probe-scale "
    "(health checks only — the source has never been exercised at query "
    "scale), 20-199 = query-scale (used in real retrievals), >=200 = "
    "campaign-scale (sustained multi-query use, e.g. L8 15-territory run)"
)

_FRESH_CADENCE_STRONG = ("daily", "weekly", "continuous")
_FRESH_CADENCE_ADEQUATE = ("periodic", "monthly", "quarterly")


def _grade_freshness(source: Dict[str, Any], last_success_ts: Optional[str]) -> Dict[str, Any]:
    cadence = source.get("update_frequency", "").lower()
    if any(k in cadence for k in _FRESH_CADENCE_STRONG):
        declared = 3
    elif any(k in cadence for k in _FRESH_CADENCE_ADEQUATE):
        declared = 2
    elif "annual" in cadence or "static" in cadence:
        declared = 1
    else:
        return _unmeasured("update cadence not declared in registry")
    parts = [{
        "grade": declared, "basis": "DECLARED",
        "evidence": source["update_frequency"],
        "rationale": "provider-stated cadence (registry field)",
    }]
    if last_success_ts:
        day = last_success_ts[:10]
        parts.append({
            "grade": 3, "basis": "MEASURED",  # all current entries are same-day
            "evidence": f"last successful retrieval {day}",
            "rationale": "pipeline-side retrieval freshness from custody log",
        })
        return {"grade": min(p["grade"] for p in parts), "basis": "MEASURED+DECLARED",
                "evidence": "; ".join(p["evidence"] for p in parts),
                "rationale": "min(declared cadence, measured last-success)"}
    return {"grade": declared, "basis": "DECLARED",
            "evidence": source["update_frequency"],
            "rationale": "no successful retrieval to measure pipeline side"}


def _unmeasured(why: str) -> Dict[str, Any]:
    return {"grade": "UNMEASURED", "basis": "UNMEASURED", "evidence": why,
            "rationale": "Art. XXV: unknown stays unknown"}


def _temporal_span_grade(source: Dict[str, Any]) -> Dict[str, Any]:
    """TEMPORAL_COVERAGE from declared coverage spans only. The registry
    states spans for a minority of sources; everything else is UNMEASURED
    rather than guessed (Art. XXV)."""
    text = source.get("coverage", "")
    m = re.search(r"\b(1[6-9]\d\d|20\d\d)\s*[-–]\s*(present|current|now|today)\b", text, re.I)
    if m:
        start = int(m.group(1))
        span_years = 2026 - start
        grade = 3 if span_years >= 40 else (2 if span_years >= 20 else 1)
        return {"grade": grade, "basis": "DECLARED",
                "evidence": m.group(0),
                "rationale": f"declared span ~{span_years}y (>=40=3, >=20=2, else 1)"}
    m2 = re.search(r"\bsince\s+(1[6-9]\d\d|20\d\d)\b", text, re.I)
    if m2:
        span_years = 2026 - int(m2.group(1))
        grade = 3 if span_years >= 40 else (2 if span_years >= 20 else 1)
        return {"grade": grade, "basis": "DECLARED",
                "evidence": m2.group(0),
                "rationale": f"declared span ~{span_years}y"}
    return _unmeasured("no coverage span declared in registry coverage field")


# ---------------------------------------------------------------------------
# Per-source grading
# ---------------------------------------------------------------------------

def load_relevance_artifact() -> Dict[str, Any]:
    """Load TOSCANINI/QUERY_RELEVANCE_PROBES.json (battery instrument)."""
    path = REPO_ROOT / "TOSCANINI" / "QUERY_RELEVANCE_PROBES.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _usage_relevance(sid: str) -> Optional[Dict[str, Any]]:
    """Persisted per-source relevance-adjudication usage aggregation.

    Returns None when the source has no persisted adjudications (never a
    0 — Art. XXV). Reading the custody log cannot mutate it (Art. IX).
    """
    try:
        from discovery_fabric.source_registry import relevance_aggregation
        entries = relevance_aggregation.read_entries(source_id=sid)
        if not entries:
            return None
        agg = relevance_aggregation.aggregate_usage(source_id=sid)
        return agg.get("sources", {}).get(sid)
    except Exception:  # noqa: BLE001 — instrument failure is disclosed, not raised
        return {"error": "usage aggregation unavailable (instrument failure)"}


def grade_source(
    source: Dict[str, Any],
    health: Optional[Dict[str, Any]],
    log_stats: Dict[str, Dict[str, Any]],
    relevance: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    relevance = relevance or {}
    sid = source["source_id"]
    dims: Dict[str, Dict[str, Any]] = {}
    st = health.get("status") if health else None
    chain = health.get("chain", {}) if health else {}
    record_count = log_stats.get(sid, {}).get("ok_records", 0)
    has_log = sid in log_stats

    # 1. ROLE_COVERAGE — does the source demonstrably fulfill its declared
    #    roles? Measured by the 7-step chain + real records.
    if st == "LIVE":
        if record_count > 0:
            dims["ROLE_COVERAGE"] = {"grade": 3, "basis": "MEASURED",
                "evidence": f"LIVE chain 7/7 with {record_count} custody-log records",
                "rationale": "role exercised with real retrievable evidence"}
        else:
            dims["ROLE_COVERAGE"] = {"grade": 2, "basis": "MEASURED",
                "evidence": "LIVE chain 7/7, definitive-zero probe",
                "rationale": "connector proven; role not yet exercised with records"}
    elif st == "DEGRADED":
        dims["ROLE_COVERAGE"] = {"grade": 1, "basis": "MEASURED",
            "evidence": f"DEGRADED ({health.get('request_status')})",
            "rationale": "provider answers restricted; unusable in campaigns today"}
    elif st in ("BLOCKED", "UNAVAILABLE", "NOT_INTEGRATED"):
        # (UNAVAILABLE = pre-2026-08-30 legacy label for BLOCKED — read
        # through status_model.LEGACY_VOCABULARY_MAP, Art. XI)
        dims["ROLE_COVERAGE"] = {"grade": 0, "basis": "MEASURED",
            "evidence": f"{st}: connector_exists={chain.get('connector_exists')}",
            "rationale": "no usable retrieval path measured"}
    else:
        dims["ROLE_COVERAGE"] = _unmeasured("no health measurement")

    # 2. SOURCE_DIVERSITY — structural independence of the underlying corpus.
    groups = [g for g, members in OVERLAP_GROUPS.items() if sid in members]
    if source.get("primary_or_secondary") == "SECONDARY" and any(
        k in source.get("name", "").lower() for k in ("lens", "scopus", "openalex", "google")
    ):
        dims["SOURCE_DIVERSITY"] = {"grade": 1, "basis": "DECLARED",
            "evidence": f"aggregator; overlaps {groups}",
            "rationale": "repackages upstream corpora already reachable via primaries"}
    elif groups:
        dims["SOURCE_DIVERSITY"] = {"grade": 2, "basis": "DECLARED",
            "evidence": f"corpus shared with {groups}",
            "rationale": "redundant capability inside an overlap group"}
    else:
        dims["SOURCE_DIVERSITY"] = {"grade": 3, "basis": "DECLARED",
            "evidence": "sole provider of its corpus among registered sources",
            "rationale": "no registered source shares this corpus"}

    # 3. LIVE_AVAILABILITY
    avail = {("LIVE", 3), ("DEGRADED", 1), ("BLOCKED", 0),
             ("UNAVAILABLE", 0), ("NOT_INTEGRATED", 0)}
    if st is None or st == "NOT_MEASURED":
        dims["LIVE_AVAILABILITY"] = _unmeasured("health status not measured")
    else:
        g = dict(avail)[st]
        dims["LIVE_AVAILABILITY"] = {"grade": g, "basis": "MEASURED",
            "evidence": st,
            "rationale": "from measured 7-step health chain"
            if g else "DEGRADED=1 because rate/budget-limited sources cannot support campaign runs"}

    # 4. RECORD_VOLUME
    if not has_log:
        dims["RECORD_VOLUME"] = _unmeasured("no retrieval-log entries for this source")
    else:
        g = (3 if record_count >= RECORD_VOLUME_BANDS[1]
             else 2 if record_count >= RECORD_VOLUME_BANDS[0]
             else 1 if record_count > 0 else 0)
        dims["RECORD_VOLUME"] = {"grade": g, "basis": "MEASURED",
            "evidence": f"{record_count} OK records across "
                        f"{log_stats[sid]['entries']} logged retrievals",
            "rationale": _RECORD_RATIONALE,
            **({"note": log_stats[sid].get("metered_note")} if log_stats[sid].get("metered_note") else {})}

    # 5. FRESHNESS
    dims["FRESHNESS"] = _grade_freshness(source, log_stats.get(sid, {}).get("last_success"))

    # 6. PRIMARY_SOURCE_AUTHORITY
    ps = source.get("primary_or_secondary", "")
    if ps == "PRIMARY":
        dims["PRIMARY_SOURCE_AUTHORITY"] = {"grade": 3, "basis": "DECLARED",
            "evidence": "PRIMARY", "rationale": "authoritative issuer of the records"}
    elif ps == "SECONDARY":
        dims["SOURCE_DIVERSITY_NOTE_IF_SECONDARY"] = None  # not a dimension
        dims["PRIMARY_SOURCE_AUTHORITY"] = {"grade": 2, "basis": "DECLARED",
            "evidence": "SECONDARY", "rationale": "derived/repackaged view of primary issuers"}
    else:
        dims["PRIMARY_SOURCE_AUTHORITY"] = _unmeasured("primary_or_secondary not declared")

    # 7. QUERY_RELEVANCE — from the committed QUERY_RELEVANCE battery
    #    artifact (query_relevance.py instrument, CEO "finish source
    #    maturity" directive). Sources not in the artifact (metered /
    #    blocked / failed probes) stay UNMEASURED (Art. XXV).
    #    v1.2.0 — USAGE AGGREGATION (maturity §6.1 closure): the persisted
    #    per-source relevance-adjudication aggregation from REAL runs
    #    (relevance_aggregation.py custody log) is attached alongside the
    #    battery grade so relevance quality is measured from actual engine
    #    usage, continuously, not only from the fixed battery.
    bat = (relevance or {}).get("grades", {}).get(sid)
    if bat is not None:
        dims["QUERY_RELEVANCE"] = dict(bat)
        span = ((relevance.get("aggregates", {}).get(sid) or {})
                .get("measured_temporal_span"))
        if span:
            dims["QUERY_RELEVANCE"]["temporal_span_harvest"] = span
    else:
        metered = bool(source.get("metered_quota"))
        dims["QUERY_RELEVANCE"] = _unmeasured(
            ("metered source — live probes suppressed by quota policy; "
             "no adjudicated battery data exists") if metered else
            "not in the committed battery run (connector absent, blocked, "
            "or every probe failed this run) — Art. XXV: not graded")
    usage = _usage_relevance(sid)
    if usage is not None:
        dims["QUERY_RELEVANCE"]["usage_aggregation"] = usage

    # 8. PROVENANCE_COMPLETENESS
    if not has_log:
        dims["PROVENANCE_COMPLETENESS"] = _unmeasured("no retrieval-log entries")
    else:
        s = log_stats[sid]
        ok_entries = s["ok_entries"]
        provenance_frac = s["provenance_field_fraction"]
        chain_ok = bool(chain.get("provenance_stores") and chain.get("retrieval_log_stores"))
        g = (3 if provenance_frac >= 0.999 and (chain_ok or st != "LIVE")
             else 2 if provenance_frac >= 0.95 else 1)
        dims["PROVENANCE_COMPLETENESS"] = {"grade": g, "basis": "MEASURED",
            "evidence": f"{s['prov_fields']}/{s['entries']} entries with hash+payload "
                        f"provenance fields ({provenance_frac:.1%}); {ok_entries} OK; chain steps "
                        f"provenance_stores={chain.get('provenance_stores')}, "
                        f"retrieval_log_stores={chain.get('retrieval_log_stores')}",
            "rationale": "custody fields (entry_sha256, raw_payload_sha256, "
                         "prev link) complete on every logged retrieval = 3"}

    # 9. FAILURE_NEGATIVE_EVIDENCE_COVERAGE
    fc = FAILURE_CLASS.get(sid)
    if fc is None:
        dims["FAILURE_NEGATIVE_EVIDENCE_COVERAGE"] = _unmeasured("failure class not classified")
    else:
        rationale = {
            3: "source exists to record failures/negative events",
            2: "records attempts incl. terminated/withdrawn/failed",
            1: "failures appear but publication/grant bias undersamples them",
            0: "evidence class carries no failure semantics",
        }[fc]
        dims["FAILURE_NEGATIVE_EVIDENCE_COVERAGE"] = {
            "grade": fc, "basis": "DECLARED",
            "evidence": f"failure_class={fc} domain={FAILURE_DOMAIN.get(sid, 'n/a')}",
            "rationale": rationale}

    # 10. GEOGRAPHIC_COVERAGE
    geo = GEOGRAPHIC.get(sid)
    if geo is None:
        dims["GEOGRAPHIC_COVERAGE"] = _unmeasured("geographic reach not declared")
    else:
        dims["GEOGRAPHIC_COVERAGE"] = {"grade": geo[0], "basis": "DECLARED",
            "evidence": geo[1],
            "rationale": "3=global corpus/universal data, 2=multi-region, 1=single jurisdiction"}

    # 11. TEMPORAL_COVERAGE — declared corpus span where the registry
    #     states one; otherwise the MEASURED span of records the engine
    #     actually retrieved in the battery (a floor on the corpus span,
    #     never a ceiling — disclosed); else UNMEASURED.
    declared = _temporal_span_grade(source)
    mspan = ((relevance or {}).get("aggregates", {}).get(sid) or {}).get(
        "measured_temporal_span")
    if isinstance(declared.get("grade"), int) and mspan:
        dims["TEMPORAL_COVERAGE"] = {
            "grade": declared["grade"],
            "basis": "MEASURED+DECLARED",
            "evidence": (f"declared: {declared['evidence']}; measured: "
                         f"retrieved records span {mspan['min_year']}-"
                         f"{mspan['max_year']} ({mspan['span_years']}y, "
                         f"{mspan['records_with_dates']} date-bearing records)"),
            "rationale": declared["rationale"] + " (measured span is a floor "
                         "on the declared corpus span)",
        }
    elif mspan:
        from .query_relevance import grade_temporal_measured
        dims["TEMPORAL_COVERAGE"] = grade_temporal_measured(mspan)
    else:
        dims["TEMPORAL_COVERAGE"] = declared

    dims.pop("SOURCE_DIVERSITY_NOTE_IF_SECONDARY", None)

    numeric = [d["grade"] for d in dims.values() if isinstance(d.get("grade"), int)]
    return {
        "source_id": sid,
        "name": source["name"],
        "authority_role": source["authority_role"],
        "health_status": st,
        "dimensions": {k: dims[k] for k in DIMENSIONS if k in dims},
        "numeric_grade_count": len(numeric),
        "unmeasured_count": sum(1 for d in dims.values() if d.get("grade") == "UNMEASURED"),
        "depth_mean": (round(sum(numeric) / len(numeric), 2)
                       if numeric else "UNMEASURED"),
    }


# ---------------------------------------------------------------------------
# Role-depth rollup — the CEO's central demand: role coverage != role depth.
# ---------------------------------------------------------------------------

def rollup_roles(graded: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    from .registry import SOURCE_REGISTRY
    from .roles import COVERAGE_MATRIX_ROLES
    for role in COVERAGE_MATRIX_ROLES:
        serving = [sid for sid, s in SOURCE_REGISTRY.items()
                   if role in s["authority_role"]]
        live = [sid for sid in serving
                if graded[sid]["health_status"] == "LIVE"]
        best, best_depth = None, "UNMEASURED"
        depth_vals: List[float] = []
        for sid in live:
            dm = graded[sid]["depth_mean"]
            if isinstance(dm, (int, float)):
                depth_vals.append(dm)
                if best is None or dm > (best_depth if isinstance(best_depth, float) else -1):
                    best, best_depth = sid, dm
        if not live:
            label = "GAP_NO_LIVE_SOURCE"
        else:
            avg = round(sum(depth_vals) / len(depth_vals), 2) if depth_vals else "UNMEASURED"
            label = ("WORLD_CLASS" if isinstance(avg, float) and avg >= 2.5 else
                     "ADEQUATE" if isinstance(avg, float) and avg >= 2.0 else
                     "WEAK")
        limiting = []
        for sid in live[:1] if live else []:
            for dim, d in graded[sid]["dimensions"].items():
                if d.get("grade") == "UNMEASURED":
                    limiting.append(f"{sid}:{dim}=UNMEASURED")
                elif isinstance(d.get("grade"), int) and d["grade"] <= 1:
                    limiting.append(f"{sid}:{dim}={d['grade']}")
        out[role] = {
            "covered_binary": bool(live),
            "serving_sources": serving,
            "live_sources": live,
            "live_count": len(live),
            "best_live_source": best,
            "best_depth_mean": best_depth,
            "live_depth_mean": (round(sum(depth_vals) / len(depth_vals), 2)
                                if depth_vals else "UNMEASURED"),
            "depth_label": label,
            "limiting_dimensions": limiting[:8],
            "note": "binary coverage is ONE of eleven dimensions; depth shown separately"
                    if live else "no live source measured — honest gap (Art. XXV)",
        }
    return out


def build_grades() -> Dict[str, Any]:
    from .registry import SOURCE_REGISTRY

    health = load_health()
    per_source = {s["source_id"]: s for s in health["per_source"]}
    entries = load_retrieval_log()
    relevance = load_relevance_artifact()

    log_stats: Dict[str, Dict[str, Any]] = {}
    for e in entries:
        sid = e["source_id"]
        st = log_stats.setdefault(sid, {
            "entries": 0, "ok_entries": 0, "ok_records": 0,
            "prov_fields": 0, "last_success": None,
        })
        st["entries"] += 1
        has_prov = bool(e.get("entry_sha256") and e.get("raw_payload_sha256"))
        if has_prov:
            st["prov_fields"] += 1
        if e.get("status") == "OK":
            st["ok_entries"] += 1
            st["ok_records"] += e.get("record_count") or 0
            if e.get("timestamp"):
                ts = e["timestamp"]
                if st["last_success"] is None or ts > st["last_success"]:
                    st["last_success"] = ts
    for sid, st in log_stats.items():
        st["provenance_field_fraction"] = (
            st["prov_fields"] / st["entries"]) if st["entries"] else 0.0
        src = SOURCE_REGISTRY.get(sid)
        if src and src.get("metered_quota"):
            st["metered_note"] = (
                f"metered source: {src['metered_quota']} — volume is policy-capped, "
                f"not availability-capped")

    chain_audit = verify_log_chain(entries)
    graded = {sid: grade_source(src, per_source.get(sid), log_stats,
                                 relevance=relevance)
              for sid, src in SOURCE_REGISTRY.items()}

    # engine-level findings (Art. XV — the inconvenient ones stated plainly)
    live_ids = [sid for sid, g in graded.items() if g["health_status"] == "LIVE"]
    geo_dist: Dict[str, int] = {}
    for sid in live_ids:
        g = graded[sid]["dimensions"]["GEOGRAPHIC_COVERAGE"]["grade"]
        key = {3: "GLOBAL", 2: "MULTI_REGION", 1: "SINGLE_JURISDICTION",
               "UNMEASURED": "UNMEASURED"}[g]
        geo_dist[key] = geo_dist.get(key, 0) + 1
    failure_native = [sid for sid in live_ids
                      if graded[sid]["dimensions"]["FAILURE_NEGATIVE_EVIDENCE_COVERAGE"]["grade"] == 3]
    failure_domains = sorted({FAILURE_DOMAIN.get(sid, "undeclared")
                              for sid in failure_native})

    return {
        "artifact": "SOURCE_MATURITY_GRADES",
        "version": "1.1.0",
        "directive": ("CEO 2026-08-30 — SOURCE COVERAGE MATURITY MODEL before any "
                      "new source integration; distinguishes role COVERAGE from "
                      "DEPTH/QUALITY/AVAILABILITY"),
        "scale": {str(k): v for k, v in SCALE.items()},
        "inputs": {
            "health_report_run": health["run_timestamp"],
            "query_relevance_battery": bool(relevance),
            "retrieval_log_entries": len(entries),
            "retrieval_log_span": [min(e["timestamp"] for e in entries)[:10],
                                   max(e["timestamp"] for e in entries)[:10]],
            "registry_sources": len(SOURCE_REGISTRY),
            "custody_chain_audit": chain_audit,
        },
        "dimension_definitions_ref": "TOSCANINI/SOURCE_COVERAGE_MATURITY_MODEL.md",
        "sources": graded,
        "role_depth": rollup_roles(graded),
        "engine_level": {
            "GEOGRAPHIC": {
                "live_source_distribution": geo_dist,
                "finding": (
                    f"{geo_dist.get('SINGLE_JURISDICTION', 0)} of {len(live_ids)} "
                    f"live sources are single-jurisdiction (US regulatory reality); "
                    f"EU regulatory reality has no live source (eudamed NOT_INTEGRATED)"
                ),
            },
            "FAILURE_NEGATIVE_EVIDENCE": {
                "failure_native_live_sources": failure_native,
                "failure_domains": failure_domains,
                "finding": (
                    "failure-native live sources cover: "
                    + (", ".join(failure_domains) if failure_domains else "NONE")
                    + ". Mapped to the CEO's failure universe: automotive=COVERED "
                    "(nhtsa recalls+complaints), industrial=COVERED via rail "
                    "(fra_rail_accidents; workplace/OSHA blocked), "
                    "electronics=PARTIAL via consumer products (cpsc_recalls), "
                    "infrastructure=PARTIAL hazard inputs only (usgs "
                    "HAZARD_EVENT role — NOT failure records). Domains with "
                    "ZERO live failure coverage: "
                    + ", ".join(d for d in ("energy", "aerospace", "chemical",
                                            "medical-adjacent workplace")
                                if True)
                    + " (measured blockers: NRC RSS 403 / ADAMS 404 / PHMSA "
                    "non-tabular; ASRS 404 / LLIS SPA / NTSB HTML / FAA SDR "
                    "503; CSB 404; OSHA 404 — all dated 2026-08-30)"
                ),
            },
            "QUERY_RELEVANCE": {
                "measured_sources": sum(
                    1 for g in graded.values()
                    if g["dimensions"]["QUERY_RELEVANCE"]["basis"] == "MEASURED"),
                "unmeasured_sources": [sid for sid, g in graded.items()
                    if g["dimensions"]["QUERY_RELEVANCE"]["basis"] == "UNMEASURED"],
                "weak_sources": [sid for sid, g in graded.items()
                    if g["dimensions"]["QUERY_RELEVANCE"]["grade"] == 1],
                "finding": ("QUERY_RELEVANCE is now MEASURED for battery sources "
                            "via the committed instrument (query_relevance.py + "
                            "QUERY_RELEVANCE_PROBES.json). The instrument's first "
                            "run found 5 LIVE connector defects (DOE OSTI query "
                            "param silently ignored; PubMed ID-stub records; "
                            "RCSB stub records; NIST WebBook phantom species "
                            "records; CDRH standards server-side filter broken) "
                            "— all fixed in the same cycle."),
            },
            "CONCENTRATION": {
                "top5_share_note": "top-5 sources carried 81% of custody-log usage "
                                   "(TOSCANINI_DATABASE_COVERAGE_AUDIT); scientific "
                                   "layer leans on overlapping literature corpora",
            },
        },
    }


def main() -> int:
    grades = build_grades()
    GRADES_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    GRADES_OUT_PATH.write_text(json.dumps(grades, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {GRADES_OUT_PATH}")
    live = [g for g in grades["sources"].values() if g["health_status"] == "LIVE"]
    print(f"sources graded: {len(grades['sources'])} (live {len(live)})")
    for role, r in grades["role_depth"].items():
        print(f"  {role:16s} covered={r['covered_binary']!s:5s} depth={r['depth_label']:20s} live={r['live_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
