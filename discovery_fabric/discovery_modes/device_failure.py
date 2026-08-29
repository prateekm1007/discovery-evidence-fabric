"""DEVICE_FAILURE -> UNMET_CONSTRAINT discovery operator.

CEO database-layer directive — the critical discovery mode:

    device failure
      -> recurring failure mechanism
      -> engineering constraint
      -> existing attempted solutions
      -> remaining limitation
      -> unexplored mechanism space
      -> invention candidate

Constitutional anchors:
- Art. XX (problem existence gates mechanism optimization): without
  DOCUMENTED failure evidence the operator emits PROBLEM_NOT_DOCUMENTED
  and no candidates. Hypothetical failure modes cannot generate problems.
- Art. XXI.3 (provider failure is not absence): if MAUDE or recall
  retrieval fails at transport level, the chain BLOCKS — it never reports
  'no failures' from a failed provider.
- Art. XXI.5 (MAUDE is a signal source): recurrence is measured in raw
  REPORT_COUNT semantics with FDA limitations attached; never incidence,
  never rates.
- Art. XXI.2 (zero results is not novelty): unexplored directions carry
  an explicit NOT-A-NOVELTY-DETERMINATION caveat.
- Art. XXVII (no threshold invention): the recurrence triage threshold is
  a declared MODEL_DERIVED operational parameter with justification.
- Art. XXVIII (no silent semantic promotion): every step records its
  epistemic class; HYPOTHESIS never silently becomes evidence.

Output: a problem record compatible with the a2 problem manifest
(device / failure_mode / failure / constraint) plus the full chain
evidence, so discovered problems can feed the existing discovery pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from discovery_fabric.source_registry.base import (
    STATUS_EMPTY, STATUS_OK, SourceQueryResult,
)

# ---------------------------------------------------------------------------
# Declared operational parameters (Art. XXVII)
# ---------------------------------------------------------------------------

RECURRENCE_MIN_REPORTS = 5
RECURRENCE_THRESHOLD_BASIS = {
    "class": "MODEL_DERIVED",
    "value": RECURRENCE_MIN_REPORTS,
    "justification": (
        "Operational triage filter: a mechanism cluster with fewer than "
        "this many raw MAUDE reports is too weak a signal to prioritize "
        "for constraint derivation in this operator. This is NOT a "
        "clinical incidence or significance threshold — MAUDE report "
        "counts cannot establish incidence (Art. XXI.5). Lowering this "
        "number widens the candidate funnel; it does not change any "
        "evidentiary claim."
    ),
}

NOT_NOVELTY_CAVEAT = (
    "ABSENCE_OF_HITS_IS_NOT_NOVELTY: zero retrieved attempts along this "
    "direction means the retrieved, relevance-filtered set contains none; "
    "it is NOT a novelty determination (Art. XXI.2)."
)

# ---------------------------------------------------------------------------
# Documented mechanism-axis taxonomy
# ---------------------------------------------------------------------------
# Each axis is an engineering intervention family for converting a failure
# mechanism into a candidate design direction. This taxonomy ROUTES and
# GENERATES candidate scaffolding; the per-candidate record carries
# why_selected from the measured failure terms, and the hypothesis class —
# the taxonomy itself is never presented as engineering evidence.

MECHANISM_AXES: List[Dict[str, Any]] = [
    {
        "axis": "LOAD_PATH_REDISTRIBUTION",
        "definition": "Redistribute mechanical load away from the failing element",
        "matches": ["fracture", "break", "crack", "fatigue", "stress", "rupture",
                    "tear", "dislodg", "detachment", "loosen"],
    },
    {
        "axis": "MATERIAL_SUBSTITUTION",
        "definition": "Replace the failing material with one resisting the mechanism",
        "matches": ["wear", "corrosion", "degradation", "erosion", "friction",
                    "fatigue", "crack", "allerg", "toxic", "fracture", "break"],
    },
    {
        "axis": "GEOMETRY_STRAIN_RELIEF",
        "definition": "Reshape geometry to reduce local strain concentration",
        "matches": ["fracture", "kink", "bend", "fatigue", "crack", "stress",
                    "compression", "occlusion", "obstruction"],
    },
    {
        "axis": "REDUNDANCY",
        "definition": "Duplicate the critical function so single-element failure is tolerated",
        "matches": ["failure", "malfunction", "fracture", "break", "interruption",
                    "stop", "ceas", "loss"],
    },
    {
        "axis": "ENERGY_BUDGET_MANAGEMENT",
        "definition": "Manage energy supply/dissipation so the mechanism cannot start",
        "matches": ["battery", "depletion", "overheat", "thermal", "burn",
                    "power", "charging", "energy"],
    },
    {
        "axis": "SEALING_BARRIER_INTEGRITY",
        "definition": "Maintain a barrier against the agent driving the mechanism",
        "matches": ["infection", "contamination", "leak", "ingress", "moisture",
                    "fluid", "coloniz", "biofilm"],
    },
    {
        "axis": "INTERFACE_STABILITY",
        "definition": "Stabilize the interface where relative motion causes failure",
        "matches": ["loosen", "migration", "dislodg", "malposition", "slippage",
                    "fixation", "osteo", "wear", "micromo"],
    },
    {
        "axis": "SENSING_CLOSED_LOOP",
        "definition": "Sense the precursor of the mechanism and intervene before failure",
        "matches": ["malfunction", "failure", "progression", "depletion",
                    "occlusion", "obstruction", "wear"],
    },
]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _terms(text: str) -> List[str]:
    return [t for t in re.split(r"[^a-z0-9]+", _norm(text)) if len(t) > 3]


def _patent_query(device_query: str, mechanism: str, max_terms: int = 8) -> str:
    """Sanitized keyword query for patent title search.

    Lens title search binds a STRING query; passing the full failure-mode
    sentence (with nested parentheses and stop-words) yields EMPTY matches
    (measured 2026-08-29: 'infusion pump Recurring unknown (for use when
    the device problem is not known)' -> 0 records while real pump-patent
    art exists). The patent query therefore uses the salient TERMS: device
    query + mechanism keywords, parenthetical segments dropped, capped.
    The literature query (EuropePMC) is left natural-language — it is a
    relevance-ranked full-text search, not a title search.
    """
    # drop parenthetical qualifiers from the mechanism text
    mech = re.sub(r"\([^)]*\)", " ", mechanism)
    words = _terms(f"{device_query} {mech}")
    # dedupe preserving order, cap
    seen: set = set()
    out: List[str] = []
    for w in words:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return " ".join(out[:max_terms])


# ---------------------------------------------------------------------------
# Step 1: device failure retrieval
# ---------------------------------------------------------------------------

def retrieve_failures(device_query: str, brand_name: Optional[str] = None,
                      timeout: int = 40) -> Dict[str, Any]:
    """Retrieve failure evidence: MAUDE events + recalls.

    Art. XXI.3 discipline: provider failures BLOCK the chain.
    """
    from discovery_fabric.source_registry.connectors.openfda import (
        FdaRecallConnector, MaudeConnector,
    )
    # Phrase-quoted device query (measured: unquoted multi-word terms are
    # an implicit OR across 1.7M records; the quoted phrase is the exact
    # device-phrase semantic this operator needs).
    phrase = brand_name or device_query
    maude_q = f'device.brand_name:"{phrase}"'
    maude = MaudeConnector().search(maude_q + "+AND+event_type:(Malfunction+OR+Injury)",
                                    timeout=timeout)
    recall = FdaRecallConnector().search(
        f'reason_for_recall:"{device_query}"', timeout=timeout)

    provider_failures = []
    for r in (maude, recall):
        if r.status not in (STATUS_OK, STATUS_EMPTY):
            provider_failures.append({
                "source_id": r.source_id, "status": r.status,
                "http_status": r.http_status, "error": r.error,
            })

    return {
        "device_query": device_query,
        "maude": maude,
        "recall": recall,
        "provider_failures": provider_failures,
        "blocked": bool(provider_failures),
    }


# ---------------------------------------------------------------------------
# Step 2: recurring failure mechanism clustering
# ---------------------------------------------------------------------------

@dataclass
class MechanismCluster:
    mechanism_label: str
    report_count: int
    event_types: Dict[str, int] = field(default_factory=dict)
    date_range: Tuple[Optional[str], Optional[str]] = (None, None)
    distinct_devices: int = 0
    contributing_records: List[Dict[str, Any]] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)


def cluster_mechanisms(maude_result: SourceQueryResult) -> List[MechanismCluster]:
    """Group MAUDE records into failure-mechanism clusters.

    Clustering key: the record's product_problems terms (FDA's own
    vocabulary) plus event_type. Report counts are RAW counts with FDA
    limitations attached (Art. XXI.5) — never incidence.
    """
    clusters: Dict[str, MechanismCluster] = {}
    devices_by_cluster: Dict[str, set] = {}
    for rec in maude_result.records:
        n = rec.normalized
        problems = n.get("product_problems") or []
        key_parts = sorted({_norm(p) for p in problems if p}) or [
            _norm(n.get("event_type") or "unspecified")]
        key = " | ".join(key_parts[:3]) or "unspecified"
        cl = clusters.setdefault(key, MechanismCluster(
            mechanism_label=key, report_count=0))
        cl.report_count += 1
        et = n.get("event_type") or "unspecified"
        cl.event_types[et] = cl.event_types.get(et, 0) + 1
        d = n.get("date_received")
        lo, hi = cl.date_range
        cl.date_range = (d if (lo is None or (d and d < lo)) else lo,
                         d if (hi is None or (d and d > hi)) else hi)
        devices_by_cluster.setdefault(key, set()).add(
            n.get("device_brand_name") or n.get("udi_di") or "unknown")
        cl.contributing_records.append({
            "record_id": rec.record_id,
            "raw_payload_sha256": rec.raw_payload_sha256,
            "event_type": et,
            "brand": n.get("device_brand_name"),
        })
    for key, cl in clusters.items():
        cl.distinct_devices = len(devices_by_cluster[key])
        cl.limitations = [
            "REPORT_COUNT semantics: raw MAUDE reports, NOT incidence "
            "(Art. XXI.5; FDA 21 CFR 803 warnings)",
            "CAUSALITY_UNVERIFIED: FDA has not verified device causation",
            "DUPLICATES_POSSIBLE in the source data",
        ]
    return sorted(clusters.values(), key=lambda c: -c.report_count)


# ---------------------------------------------------------------------------
# Step 3: engineering constraint derivation
# ---------------------------------------------------------------------------

def derive_constraint(cluster: MechanismCluster, device_query: str) -> Dict[str, Any]:
    """Derive an engineering-constraint HYPOTHESIS from a mechanism cluster.

    The statement is composed from measured cluster fields; its epistemic
    class is AI_INFERENCE (derived, not measured). The derivation trace
    lists the contributing records.
    """
    mech = cluster.mechanism_label
    top_event = max(cluster.event_types.items(), key=lambda kv: kv[1])[0] \
        if cluster.event_types else "Malfunction"
    statement = (
        f"Devices matching '{device_query}' must maintain function under the "
        f"conditions producing recurring {top_event.lower()} events with "
        f"reported problem(s) [{mech}] — without introducing the new failure "
        f"modes any intervention would add."
    )
    return {
        "constraint_statement": statement,
        "epistemic_class": "AI_INFERENCE",
        "derivation_basis": {
            "mechanism": mech,
            "report_count": cluster.report_count,
            "distinct_devices": cluster.distinct_devices,
            "date_range": list(cluster.date_range),
            "threshold_basis": RECURRENCE_THRESHOLD_BASIS,
        },
        "derivation_trace": cluster.contributing_records[:25],
        "limitations": cluster.limitations,
        "problem_existence_gate": {
            # Art. XX question 1: does the failure mode actually occur?
            "documented_failure_evidence": "MAUDE reports (signal source)",
            "report_count": cluster.report_count,
            "incidence_unknown": True,
            "causality_unverified": True,
        },
    }


# ---------------------------------------------------------------------------
# Step 4: existing attempted solutions
# ---------------------------------------------------------------------------

def retrieve_attempted_solutions(device_query: str, mechanism: str,
                                 timeout: int = 40) -> Dict[str, Any]:
    """Literature + patent retrieval on the constraint.

    Relevance (Art. XXI.4): per-record relevance basis = overlap between
    the record's title/abstract terms and the constraint mechanism terms;
    records below the minimum are marked IRRELEVANT_FILTERED (kept visible,
    never silently used).
    """
    from discovery_fabric.source_registry.connectors.scientific import (
        EuropePmcConnector,
    )
    from discovery_fabric.source_registry.connectors.patents import (
        GooglePatentsConnector,
        LensPatentConnector,
    )
    query = f"{device_query} {mechanism}"
    patent_query = _patent_query(device_query, mechanism)
    lit = EuropePmcConnector().search(query, timeout=timeout)
    # Patent retrieval: Lens patent is the primary live source (measured
    # 2026-08-29: HTTP 200 with real records on the provisioned token);
    # Google Patents retained as a secondary attempt for coverage
    # disclosure. PatentBear is deliberately NOT queried here: the source
    # is provider-metered (20 requests/month) and is reserved for targeted
    # full-text/claims fetches, never routine operator scans.
    # Lens title:(...) search has MEASURED AND-semantics (2026-08-29:
    # 'infusion pump mechanical problem' -> 0 while 'infusion pump' -> 9071;
    # 'infusion pump occlusion' -> 227). FDA problem vocabulary rarely
    # co-occurs in patent titles, so a definitive EMPTY on the
    # mechanism-specific query falls back to the device-only query — the
    # recall step widens, and per-record relevance adjudication (below)
    # supplies the precision (Art. XXI.4). The fallback is DISCLOSED, and
    # a provider failure on the first query does NOT trigger it (Art.
    # XXI.3: only a definitive provider EMPTY does).
    lens_pat = LensPatentConnector().search(patent_query, timeout=timeout)
    patent_query_used = patent_query
    patent_query_fallback = False
    if lens_pat.status == "EMPTY":
        device_only = _patent_query(device_query, "")
        if device_only and device_only != patent_query:
            lens_pat = LensPatentConnector().search(device_only, timeout=timeout)
            patent_query_used = device_only
            patent_query_fallback = True
    gpat = GooglePatentsConnector().search(patent_query_used, timeout=timeout)

    mech_terms = set(_terms(mechanism)) | set(_terms(device_query))
    adjudicated = []
    for rec in lit.records:
        text_terms = set(_terms((rec.title or "") + " " + (rec.normalized.get("abstract") or "")))
        overlap = sorted(mech_terms & text_terms)
        relevant = len(overlap) >= 2
        adjudicated.append({
            "record_id": rec.record_id,
            "title": rec.title,
            "uri": rec.uri,
            "raw_payload_sha256": rec.raw_payload_sha256,
            "relevance": "RELEVANT" if relevant else "IRRELEVANT_FILTERED",
            "relevance_basis": {
                "method": "term overlap between record text and constraint "
                          "mechanism terms (transparent, adjudicable)",
                "overlapping_terms": overlap,
            },
        })
    patent_adjudicated = []
    for rec in lens_pat.records:
        text_terms = set(_terms((rec.title or "") + " " + (rec.normalized.get("snippet") or "")))
        overlap = sorted(mech_terms & text_terms)
        relevant = len(overlap) >= 2
        patent_adjudicated.append({
            "record_id": rec.record_id,
            "title": rec.title,
            "uri": rec.uri,
            "raw_payload_sha256": rec.raw_payload_sha256,
            "relevance": "RELEVANT" if relevant else "IRRELEVANT_FILTERED",
            "relevance_basis": {
                "method": "term overlap between patent title/snippet and "
                          "constraint mechanism terms (transparent, "
                          "adjudicable)",
                "overlapping_terms": overlap,
            },
        })
    patent_status = {
        "primary": {
            "source_id": lens_pat.source_id, "status": lens_pat.status,
            "error": lens_pat.error, "record_count": len(lens_pat.records),
            "relevant": sum(1 for p in patent_adjudicated
                            if p["relevance"] == "RELEVANT"),
            "records": patent_adjudicated,
        },
        "secondary": {
            "source_id": gpat.source_id, "status": gpat.status,
            "error": gpat.error, "record_count": len(gpat.records),
        },
        "note": (
            "Lens patent search is the live patent-coverage path (measured "
            "2026-08-29). Google Patents historically measures UNAVAILABLE "
            "(503 bot-block). Claim-level evidence requires a Patent Bear "
            "full-text fetch (metered, not spent by routine operator runs). "
            "Any provider failure here is NOT treated as absence of prior "
            "art (Art. XXI.3); zero relevant patents in a bounded retrieval "
            "is NOT a novelty determination (Art. XXI.2)."
        ),
    }
    return {
        "query": query,
        "patent_query": patent_query,
        "patent_query_used": patent_query_used,
        "patent_query_fallback": patent_query_fallback,
        "literature": {
            "source_status": lit.status,
            "retrieved": len(adjudicated),
            "relevant": sum(1 for a in adjudicated if a["relevance"] == "RELEVANT"),
            "records": adjudicated,
        },
        "patents": patent_status,
    }


# ---------------------------------------------------------------------------
# Step 5: remaining limitation
# ---------------------------------------------------------------------------

def remaining_limitation(attempted: Dict[str, Any], constraint: Dict[str, Any]) -> Dict[str, Any]:
    """The documented gap: what the retrieved attempts do NOT address.

    Class AI_INFERENCE; explicitly bounded by the retrieved set size —
    never presented as an exhaustive survey (Art. XXI.2 discipline).
    """
    relevant = [r for r in attempted["literature"]["records"]
                if r["relevance"] == "RELEVANT"]
    addressed_terms: set = set()
    for r in relevant:
        addressed_terms.update(r["relevance_basis"]["overlapping_terms"])
    mech_terms = set(_terms(constraint["derivation_basis"]["mechanism"])) | \
        set(_terms(constraint["constraint_statement"]))
    unaddressed = sorted(mech_terms - addressed_terms)
    statement = (
        f"Across the {len(relevant)} relevant retrieved attempts (a bounded, "
        f"non-exhaustive set), none measurably addresses: "
        f"{', '.join(unaddressed) if unaddressed else '(all mechanism terms appear in at least one attempt — no gap statement derivable from this retrieval)'}. "
        f"The retrieval covered {attempted['literature']['retrieved']} literature records; "
        f"patent coverage was provider-limited and is NOT counted as absence."
    )
    return {
        "limitation_statement": statement,
        "epistemic_class": "AI_INFERENCE",
        "basis": {
            "relevant_attempts_counted": len(relevant),
            "retrieved_records": attempted["literature"]["retrieved"],
            "exhaustive_survey": False,
            "patent_coverage": {
                "primary": attempted["patents"]["primary"]["status"],
                "secondary": attempted["patents"]["secondary"]["status"],
            },
        },
        "unaddressed_terms": unaddressed,
    }


# ---------------------------------------------------------------------------
# Step 6: unexplored mechanism space
# ---------------------------------------------------------------------------

def unexplored_mechanism_space(cluster: MechanismCluster,
                               attempted: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Candidate mechanism directions not present in the retrieved attempts.

    Each direction: axis + why_selected (measured failure terms mapping)
    + engagement evidence (which retrieved attempts touch the axis) +
    HYPOTHESIS class + the not-a-novelty-determination caveat.
    """
    mech_text = _norm(cluster.mechanism_label)
    relevant = [r for r in attempted["literature"]["records"]
                if r["relevance"] == "RELEVANT"]
    relevant_text = _norm(" ".join(r["title"] or "" for r in relevant))
    out = []
    for axis in MECHANISM_AXES:
        matched = [m for m in axis["matches"] if m in mech_text]
        if not matched:
            continue  # axis not engaged by this failure mechanism
        in_attempts = any(m in relevant_text for m in axis["matches"])
        if in_attempts:
            continue  # direction appears attempted in the retrieved set
        out.append({
            "direction": axis["axis"],
            "definition": axis["definition"],
            "why_selected": {
                "matched_failure_terms": matched,
                "source": "mechanism-cluster terms measured from MAUDE records",
            },
            "engagement_evidence": {
                "relevant_attempts_touching_axis": 0,
                "set_boundary": "retrieved + relevance-filtered literature only",
            },
            "epistemic_class": "HYPOTHESIS",
            "caveat": NOT_NOVELTY_CAVEAT,
        })
    return out


# ---------------------------------------------------------------------------
# Step 7: invention candidate (chain assembly)
# ---------------------------------------------------------------------------

def discover_from_failure(device_query: str, brand_name: Optional[str] = None,
                          timeout: int = 40) -> Dict[str, Any]:
    """Run the full DEVICE_FAILURE -> UNMET_CONSTRAINT chain."""
    from discovery_fabric.source_registry.base import utc_now

    steps: List[Dict[str, Any]] = []

    def _step(name: str, status: str, detail: Dict[str, Any]) -> Dict[str, Any]:
        s = {"step": name, "status": status, **detail}
        steps.append(s)
        return s

    # Step 1: retrieve failure evidence
    retrieval = retrieve_failures(device_query, brand_name=brand_name, timeout=timeout)
    if retrieval["blocked"]:
        _step("retrieve_failures", "BLOCKED_PROVIDER_FAILURE", {
            "provider_failures": retrieval["provider_failures"],
            "note": "Art. XXI.3: provider failure is NOT absence; the chain "
                    "does not proceed to 'no failures'.",
        })
        return _assemble(device_query, steps, candidates=[], blocked=True)
    maude, recall = retrieval["maude"], retrieval["recall"]
    _step("retrieve_failures", "OK", {
        "maude_status": maude.status, "maude_records": len(maude.records),
        "maude_total_population": maude.total_hits,
        "recall_status": recall.status, "recall_records": len(recall.records),
        "sample_disclosure": (
            f"MAUDE analysis is based on the first {len(maude.records)} retrieved "
            f"reports of a provider-reported population of {maude.total_hits} "
            f"matching reports — cluster counts are SAMPLE statistics, not "
            f"population counts (Art. XXI.5)."
        ) if maude.total_hits and maude.total_hits > len(maude.records) else None,
    })

    # Step 1b: problem-existence gate (Art. XX)
    if maude.status == STATUS_EMPTY and recall.status == STATUS_EMPTY:
        _step("problem_existence_gate", "PROBLEM_NOT_DOCUMENTED", {
            "note": "Both providers answered definitively with zero records "
                    "for this query. No documented failure -> no candidates "
                    "(Art. XX).",
        })
        return _assemble(device_query, steps, candidates=[])

    # Step 2: recurring mechanisms
    clusters = cluster_mechanisms(maude)
    recurring = [c for c in clusters if c.report_count >= RECURRENCE_MIN_REPORTS]
    _step("cluster_mechanisms", "OK" if clusters else "EMPTY", {
        "clusters": len(clusters),
        "recurring_clusters": len(recurring),
        "recurrence_threshold": RECURRENCE_THRESHOLD_BASIS,
        "cluster_summary": [
            {"mechanism": c.mechanism_label, "report_count": c.report_count,
             "distinct_devices": c.distinct_devices}
            for c in clusters[:10]
        ],
    })
    if not recurring:
        # no cluster passes the declared triage threshold — honest stop
        _step("problem_existence_gate", "SIGNAL_BELOW_TRIAGE_THRESHOLD", {
            "note": "Reports exist but no mechanism cluster meets the "
                    "declared MODEL_DERIVED recurrence triage threshold. "
                    "No candidates generated (problem-existence too weak "
                    "to justify mechanism work — Art. XX).",
        })
        return _assemble(device_query, steps, candidates=[])

    # Steps 3-7 per recurring cluster
    candidates = []
    for cluster in recurring[:3]:  # top 3 mechanisms per run (operational bound)
        constraint = derive_constraint(cluster, device_query)
        attempted = retrieve_attempted_solutions(
            device_query, cluster.mechanism_label, timeout=timeout)
        limitation = remaining_limitation(attempted, constraint)
        space = unexplored_mechanism_space(cluster, attempted)

        candidate = {
            "candidate_id": f"dfc:{_slug(device_query)}:{_slug(cluster.mechanism_label)[:60]}",
            "problem": {
                # a2-problem-manifest-compatible shape
                "device": device_query,
                "failure_mode": (max(cluster.event_types.items(), key=lambda kv: kv[1])[0]
                                 if cluster.event_types else "Malfunction"),
                "failure": f"Recurring {cluster.mechanism_label} "
                           f"({cluster.report_count} MAUDE reports in a "
                           f"{len(maude.records)}-report sample of a population "
                           f"of {maude.total_hits}, {cluster.distinct_devices} "
                           f"distinct reported devices)",
                "constraint": constraint["constraint_statement"],
            },
            "constraint": constraint,
            "attempted_solutions": attempted,
            "remaining_limitation": limitation,
            "unexplored_mechanism_space": space,
            "epistemic_classes": {
                "problem": "OBSERVED (MAUDE signal, incidence unknown)",
                "constraint": "AI_INFERENCE",
                "remaining_limitation": "AI_INFERENCE (bounded by retrieved set)",
                "unexplored_directions": "HYPOTHESIS (not novelty determinations)",
            },
            "provenance": {
                "maude_query": maude.query,
                "maude_record_count": len(maude.records),
                "maude_payload_sha": maude.records[0].raw_payload_sha256 if maude.records else None,
                "recall_query": recall.query,
                "literature_query": attempted["query"],
            },
        }
        candidates.append(candidate)

    _step("derive_constraints_and_candidates", "OK", {
        "candidates_generated": len(candidates),
        "per_candidate_directions": [
            {"candidate_id": c["candidate_id"],
             "unexplored_directions": len(c["unexplored_mechanism_space"])}
            for c in candidates
        ],
    })
    return _assemble(device_query, steps, candidates=candidates)


def _slug(text: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in (text or "").lower())[:80]


def _assemble(device_query: str, steps: List[Dict[str, Any]],
              candidates: List[Dict[str, Any]], blocked: bool = False) -> Dict[str, Any]:
    from discovery_fabric.source_registry.base import utc_now
    return {
        "operator": "DEVICE_FAILURE_TO_UNMET_CONSTRAINT",
        "device_query": device_query,
        "run_timestamp": utc_now(),
        "chain_steps": steps,
        "candidates": candidates,
        "blocked": blocked,
        "notes": {
            "llm_free": True,
            "mistral_key_activated": False,
            "fda_maude_limitations_attached": True,
        },
    }
