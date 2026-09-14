"""Universal FAILURE -> GAP -> OPPORTUNITY discovery operator.

CEO lifecycle directive (2026-08-29): "Extend S5 into a universal
discovery operator":

    REAL-WORLD FAILURE
      -> FAILURE MECHANISM
      -> ENGINEERING CONSTRAINT
      -> EXISTING SOLUTIONS
      -> WHY THEY FAIL
      -> UNRESOLVED GAP
      -> ALTERNATIVE PHYSICAL PRINCIPLES
      -> CROSS-DOMAIN TRANSFER
      -> INVENTION CANDIDATE

    "Every step must have evidence or explicit epistemic classification."

This module extends device_failure.py (S5), reusing its measured steps
(retrieve_failures, cluster_mechanisms, derive_constraint,
retrieve_attempted_solutions, remaining_limitation) and adding:

  why_they_fail                 recall root-cause records + MAUDE event
                                narratives (EVIDENCE_BOUND where records
                                exist; explicit NO_EVIDENCE otherwise)
  alternative_physical_principles  physics-principle taxonomy applied to
                                the constraint (HYPOTHESIS, declared)
  cross_domain_transfer         the same constraint class queried in the
                                directive's other device domains
                                (EVIDENCE_BOUND with custody)
  invention_candidate           synthesis with kill conditions
                                (AI_INFERENCE, declared, never evidence)

Constitutional anchors: Art. XX (problem-existence gate), Art. XXI.3
(provider failure != absence), Art. XXI.2 (zero hits != novelty),
Art. XXVIII (no silent semantic promotion — every step's class is
recorded and never upgraded), Art. XXXII (the alternative explanation
for every gap: 'the retrieval was too narrow', disclosed per candidate).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from discovery_fabric.discovery_modes.device_failure import (
    MechanismCluster, RECURRENCE_MIN_REPORTS, NOT_NOVELTY_CAVEAT,
    cluster_mechanisms, derive_constraint, remaining_limitation,
    retrieve_attempted_solutions, retrieve_failures,
)
from discovery_fabric.source_registry.base import (
    STATUS_EMPTY, STATUS_OK, SourceQueryResult,
)
from discovery_fabric.source_registry.connectors.scientific import (
    EuropePmcConnector,
)

# ---------------------------------------------------------------------------
# Declared operational parameters (Art. XXVII)
# ---------------------------------------------------------------------------

#: The directive's cross-domain search space. Domains are searched for
#: constraint-class analogues; the engine may KILL a domain (no usable
#: transfer evidence) — kills are recorded, not hidden.
DIRECTIVE_DOMAINS = {
    "ORTHOPEDICS": "orthopedic implant",
    "CARDIOVASCULAR": "cardiovascular device",
    "NEUROVASCULAR": "neurovascular device",
    "OPHTHALMOLOGY": "ophthalmic device",
    "SURGICAL": "surgical instrument",
}

#: Physics-principle taxonomy (ENGINEERING_TAXONOMY — curated, declared,
#: never evidence). Grammar maps constraint terms to principles CAPABLE
#: of addressing them; 'alternative' means: capable but NOT engaged by
#: the retrieved attempted-solution set.
PHYSICAL_PRINCIPLES = [
    {
        "principle": "MECHANICAL_LOAD_PATH",
        "family": "mechanical",
        "definition": "Static/dynamic load distribution through geometry and stiffness",
        "addresses": ["fracture", "break", "crack", "fatigue", "stress",
                      "loosen", "rupture", "tear", "wear"],
        "engagement_markers": ["load path", "stiffness", "stress shielding", "load distribution", "stress concentrat"],
    },
    {
        "principle": "SUPERELASTIC_PHASE_TRANSFORMATION",
        "family": "materials physics",
        "definition": "Stress-induced phase transformation absorbing strain "
                      "(e.g., nitinol-class behavior)",
        "addresses": ["kink", "bend", "fracture", "fatigue", "deformation",
                      "compression"],
        "engagement_markers": ["superelastic", "nitinol", "phase transformation", "shape memory"],
    },
    {
        "principle": "FLUID_DYNAMIC_SHAPING",
        "family": "fluid mechanics",
        "definition": "Pressure/flow fields shaped by geometry to move or "
                      "stagnate fluid deliberately",
        "addresses": ["occlusion", "obstruction", "thrombus", "flow",
                      "leak", "blockage", "embol"],
        "engagement_markers": ["flow diverter", "hemodynamic", "pressure gradient", "shear stress", "stagnation", "flow field"],
    },
    {
        "principle": "TRIBOLOGICAL_SURFACING",
        "family": "surface physics",
        "definition": "Friction/wear behavior engineered at the interface "
                      "(coatings, texture, lubricity)",
        "addresses": ["wear", "friction", "erosion", "degradation", "roughness"],
        "engagement_markers": ["tribolog", "lubric", "coating", "surface texture", "friction coefficient"],
    },
    {
        "principle": "OSSEOINTEGRATIVE_TOPOLOGY",
        "family": "biological interface",
        "definition": "Porous/surface topology driving bone or tissue ingrowth "
                      "for fixation",
        "addresses": ["loosen", "migration", "fixation", "micromo", "osteolysis"],
        "engagement_markers": ["porous", "ingrowth", "osseointegrat", "bone ongrowth", "trabecular"],
    },
    {
        "principle": "ELECTROMAGNETIC_ACTUATION",
        "family": "electromagnetism",
        "definition": "Fields coupling to conductive/magnetic elements for "
                      "actuation or sensing without mechanical linkage",
        "addresses": ["occlusion", "obstruction", "malfunction", "failure",
                      "control", "regulation"],
        "engagement_markers": ["electromagnetic", "magnetic", "actuat", "induction", "coil", "capacitive", "impedance"],
    },
    {
        "principle": "DIFFUSIVE_TRANSPORT_CONTROL",
        "family": "transport phenomena",
        "definition": "Concentration-gradient-driven transport throttled by "
                      "materials and geometry",
        "addresses": ["corrosion", "degradation", "toxic", "leach", "infection",
                      "restenosis", "proliferation"],
        "engagement_markers": ["diffus", "elution", "concentration gradient", "permeab", "drug deliver"],
    },
    {
        "principle": "ACOUSTIC_RADIATION_FORCE",
        "family": "wave physics",
        "definition": "Acoustic energy for actuation, sensing, or localized "
                      "mechanical effect through tissue",
        "addresses": ["occlusion", "obstruction", "thrombus", "malfunction",
                      "detection"],
        "engagement_markers": ["acoustic", "ultrasound", "sonic", "cavitation", "lithotripsy"],
    },
    {
        "principle": "THERMAL_PHASE_CHANGE",
        "family": "thermodynamics",
        "definition": "Latent-heat phase transitions for expansion, locking, "
                      "or energy buffering",
        "addresses": ["migration", "malposition", "loosen", "fixation",
                      "occlusion"],
        "engagement_markers": ["phase change", "thermal expansion", "latent heat", "melting point", "shape memory polymer"],
    },
]

TAXONOMY_CLASS = "ENGINEERING_TAXONOMY"
HYPOTHESIS_CLASS = "HYPOTHESIS"
INFERENCE_CLASS = "AI_INFERENCE"
EVIDENCE_CLASS = "EVIDENCE_BOUND"


# ---------------------------------------------------------------------------
# Step 5 (new): WHY THEY FAIL — evidence-bound root-cause extraction
# ---------------------------------------------------------------------------

def why_they_fail(recall: SourceQueryResult, maude: SourceQueryResult,
                  cluster: MechanismCluster,
                  device_query: str) -> Dict[str, Any]:
    """Why existing solutions fail, from the providers' own words.

    Evidence: recall root-cause descriptions (FDA recall records) and
    the MAUDE event narratives (mdr_text) of the cluster's contributing
    reports. If neither carries root-cause text, the step reports
    NO_ROOT_CAUSE_EVIDENCE — it never fabricates a 'why' (Art. VI)."""
    root_causes: List[Dict[str, Any]] = []
    for r in recall.records[:20]:
        n = r.normalized or {}
        rc = n.get("root_cause_description") or n.get("reason")
        if rc and str(rc).strip():
            root_causes.append({
                "epistemic_class": EVIDENCE_CLASS,
                "text": str(rc).strip()[:400],
                "custody": {
                    "source_id": r.source_id,
                    "record_id": r.record_id,
                    "raw_payload_sha256": r.raw_payload_sha256,
                    "retrieved_at": r.retrieved_at,
                    "query": r.query,
                },
            })
    cluster_ids = {c["record_id"] for c in cluster.contributing_records}
    narratives: List[Dict[str, Any]] = []
    for r in maude.records:
        if r.record_id not in cluster_ids:
            continue
        narrative = (r.normalized or {}).get("narrative_text")
        if narrative and str(narrative).strip():
            narratives.append({
                "epistemic_class": EVIDENCE_CLASS,
                "text": str(narrative).strip()[:400],
                "custody": {
                    "source_id": r.source_id,
                    "record_id": r.record_id,
                    "raw_payload_sha256": r.raw_payload_sha256,
                    "retrieved_at": r.retrieved_at,
                    "query": r.query,
                },
            })
        if len(narratives) >= 10:
            break
    if not root_causes and not narratives:
        return {
            "why_statement": "NO_ROOT_CAUSE_EVIDENCE: neither recall records "
                             "nor MAUDE narratives in the retrieved set carry "
                             "root-cause text for this mechanism.",
            "epistemic_class": "NO_EVIDENCE",
            "root_causes": [],
            "narratives": [],
        }
    parts = []
    if root_causes:
        parts.append(
            f"{len(root_causes)} recall root-cause descriptions (FDA "
            f"enforcement records, custody attached)")
    if narratives:
        parts.append(f"{len(narratives)} MAUDE event narratives from this "
                     f"mechanism cluster (mdr_text, custody attached)")
    return {
        "why_statement": (
            "Why existing solutions fail, per retrieved evidence: "
            + "; ".join(parts)
            + ". Statements are the providers' own words, custody-attached; "
              "the aggregation across records is "
            f"{INFERENCE_CLASS} (bounded by the retrieved set)."
        ),
        "epistemic_class": EVIDENCE_CLASS,
        "aggregation_class": INFERENCE_CLASS,
        "root_causes": root_causes,
        "narratives": narratives,
    }


# ---------------------------------------------------------------------------
# Step 7 (new): ALTERNATIVE PHYSICAL PRINCIPLES
# ---------------------------------------------------------------------------

def alternative_physical_principles(constraint: Dict[str, Any],
                                    attempted: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Principles capable of addressing the constraint that the retrieved
    attempted-solution set does NOT engage.

    Selection = constraint-term grammar (measured terms) vs principle
    grammar; 'not engaged' = principle family absent from the relevant
    retrieved attempts' text. HYPOTHESIS class with the no-novelty
    caveat — the taxonomy ROUTES invention thinking; it is never
    engineering evidence."""
    stmt = (constraint.get("constraint_statement") or "").lower()
    mech = (constraint.get("derivation_basis", {}).get("mechanism") or "").lower()
    text = f"{stmt} {mech}"
    relevant_text = " ".join(
        (r.get("title") or "") + " " + " ".join(r.get("relevance_basis", {})
                                                .get("overlapping_terms", []))
        for r in attempted["literature"]["records"]
        if r.get("relevance") == "RELEVANT").lower()
    out: List[Dict[str, Any]] = []
    for p in PHYSICAL_PRINCIPLES:
        addressed = [m for m in p["addresses"] if m in text]
        if not addressed:
            continue  # principle not engaged by this constraint
        # Engagement means the attempts WORK IN THIS PRINCIPLE'S FAMILY
        # (family-specific vocabulary), not that they share the
        # constraint's own failure term — 'fracture' appears in every
        # fracture-related attempt by definition.
        engaged_by_attempts = any(
            m in relevant_text for m in p["engagement_markers"])
        if engaged_by_attempts:
            continue  # existing solutions already work in this family
        out.append({
            "principle": p["principle"],
            "family": p["family"],
            "definition": p["definition"],
            "constraint_terms_addressed": addressed,
            "why_alternative": {
                "constraint_engages_principle": True,
                "principle_family_in_retrieved_attempts": False,
                "set_boundary": "retrieved + relevance-filtered attempts only",
            },
            "epistemic_class": HYPOTHESIS_CLASS,
            "taxonomy_class": TAXONOMY_CLASS,
            "caveat": NOT_NOVELTY_CAVEAT,
        })
    return out


# ---------------------------------------------------------------------------
# Step 8 (new): CROSS-DOMAIN TRANSFER
# ---------------------------------------------------------------------------

def cross_domain_transfer(constraint: Dict[str, Any], source_domain: str,
                          domains: Optional[Dict[str, str]] = None,
                          timeout: int = 30) -> Dict[str, Any]:
    """Search the directive's OTHER device domains for the same
    constraint class solved by a different physical principle.

    Each domain is queried live (EuropePMC). Domains with usable
    evidence report TRANSFER_EVIDENCE records with custody; domains
    with none report KILLED (engine kills weak spaces — the kill is the
    result, not an absence of effort)."""
    domains = domains or DIRECTIVE_DOMAINS
    stmt_terms = sorted({
        t for t in re.split(r"[^a-z]+",
                            (constraint.get("constraint_statement") or "").lower())
        if len(t) > 4
    })
    focus = " ".join(stmt_terms[:6]) or (constraint.get("constraint_statement") or "")[:80]
    per_domain: Dict[str, Any] = {}
    for name, domain_query in domains.items():
        if name == source_domain:
            per_domain[name] = {"status": "SOURCE_DOMAIN_EXCLUDED"}
            continue
        try:
            res = EuropePmcConnector().search(
                f"({focus}) AND ({domain_query})", timeout=timeout)
        except Exception as e:  # noqa: BLE001 — provider failures surfaced
            per_domain[name] = {"status": "SEARCH_FAILED", "error": str(e)[:120]}
            continue
        if res.status not in (STATUS_OK, STATUS_EMPTY):
            per_domain[name] = {
                "status": res.status,
                "note": "Art. XXI.3: provider failure is not absence",
            }
            continue
        usable = []
        for r in res.records[:5]:
            blob = ((r.normalized or {}).get("title") or "").lower()
            overlap = [t for t in stmt_terms if t in blob]
            if overlap:
                usable.append({
                    "epistemic_class": EVIDENCE_CLASS,
                    "title": r.normalized.get("title"),
                    "pmid": r.normalized.get("pmid"),
                    "constraint_overlap": overlap,
                    "custody": {
                        "source_id": r.source_id,
                        "record_id": r.record_id,
                        "raw_payload_sha256": r.raw_payload_sha256,
                        "retrieved_at": r.retrieved_at,
                        "query": r.query,
                    },
                })
        if usable:
            per_domain[name] = {
                "status": "TRANSFER_EVIDENCE",
                "records": usable,
                "note": "analogous constraint evidenced in this domain; "
                        "transfer OPPORTUNITY (not proof of applicability)",
            }
        else:
            per_domain[name] = {
                "status": "KILLED_NO_USABLE_TRANSFER",
                "retrieved": len(res.records),
                "note": "domain queried; no record title measurably overlaps "
                        "the constraint terms. Killed as a transfer source "
                        "for THIS constraint (not a claim about the domain).",
            }
    return {
        "source_domain": source_domain,
        "constraint_terms": stmt_terms,
        "per_domain": per_domain,
        "epistemic_class": "MIXED",
        "classification_note": "TRANSFER_EVIDENCE entries are EVIDENCE_BOUND; "
                               "KILLED entries are measured retrieval results "
                               "bounded by one query per domain.",
    }


# ---------------------------------------------------------------------------
# Step 9 (new): INVENTION CANDIDATE synthesis
# ---------------------------------------------------------------------------

def invention_candidate(device_query: str, cluster: MechanismCluster,
                        constraint: Dict[str, Any],
                        principles: List[Dict[str, Any]],
                        transfer: Dict[str, Any]) -> Dict[str, Any]:
    """Synthesize the invention candidate with kill conditions.

    Class: AI_INFERENCE end to end (the synthesis step). The candidate
    is a structured hypothesis — problem evidence (OBSERVED) +
    alternative principle (HYPOTHESIS) + transfer evidence (EVIDENCE_
    BOUND where present). No component is silently promoted."""
    slug = "".join(c if c.isalnum() else "_" for c in device_query.lower())[:40]
    mech_slug = "".join(c if c.isalnum() else "_" for c
                        in cluster.mechanism_label.lower())[:40]
    primary = principles[0]["principle"] if principles else "UNRESOLVED"
    transfer_domains = [d for d, v in transfer.get("per_domain", {}).items()
                        if v.get("status") == "TRANSFER_EVIDENCE"]
    kill_conditions = [
        {
            "condition": "PRIOR_ART_COLLISION",
            "test": "Exhaustive classification search (A61F classes + "
                    "mechanism keywords) across live patent sources",
            "kill_if": "any claim reads on the candidate mechanism "
                       "(novelty destroyed)",
        },
        {
            "condition": "PHYSICS_INFEASIBILITY",
            "test": f"Quantitative feasibility model of {primary} against "
                    f"the constraint's measured terms",
            "kill_if": "required magnitude/precision exceeds physical "
                       "limits of the principle in vivo",
        },
        {
            "condition": "TRANSFER_INVALIDITY",
            "test": "Domain-transfer justification check: does the source "
                    "domain's loading/biology actually match the target "
                    "domain's",
            "kill_if": "the constraint physics differs so the transferred "
                       "principle does not apply",
        },
        {
            "condition": "PROBLEM_SIGNAL_COLLAPSE",
            "test": "Independent failure-data re-query (different query "
                    "phrasing) confirms the recurring mechanism",
            "kill_if": "the mechanism cluster fails to reproduce under "
                       "re-phrased retrieval",
        },
    ]
    return {
        "candidate_id": f"opp:{slug}:{mech_slug}:{primary[:24]}",
        "problem": {
            "device": device_query,
            "failure_mechanism": cluster.mechanism_label,
            "constraint": constraint.get("constraint_statement"),
            "epistemic_class": "OBSERVED (MAUDE signal; incidence unknown)",
        },
        "mechanism_hypothesis": {
            "physical_principle": primary,
            "principle_family": principles[0]["family"] if principles else None,
            "definition": principles[0]["definition"] if principles else None,
            "epistemic_class": HYPOTHESIS_CLASS,
            "caveat": NOT_NOVELTY_CAVEAT,
        },
        "cross_domain_evidence": {
            "transfer_domains": transfer_domains,
            "epistemic_class": EVIDENCE_CLASS if transfer_domains else "NO_EVIDENCE",
        },
        "kill_conditions": kill_conditions,
        "synthesis_class": INFERENCE_CLASS,
        "strongest_alternative_explanation": (
            "The unresolved gap may reflect retrieval narrowness, not a "
            "true engineering gap: the attempted-solution set is bounded "
            "by one literature query and provider-limited patent coverage. "
            "Kill condition PRIOR_ART_COLLISION and PROBLEM_SIGNAL_COLLAPSE "
            "exist to test exactly this (Art. XXXII)."
        ),
        "not_a_novelty_determination": True,
    }


# ---------------------------------------------------------------------------
# The universal operator (9 steps)
# ---------------------------------------------------------------------------

def discover_opportunity(device_query: str, source_domain: str,
                         brand_name: Optional[str] = None,
                         timeout: int = 30) -> Dict[str, Any]:
    """Run the full universal chain for one device query + its domain."""
    from discovery_fabric.source_registry.base import utc_now

    steps: List[Dict[str, Any]] = []

    def _step(name: str, status: str, detail: Dict[str, Any]) -> None:
        steps.append({"step": name, "status": status, **detail})

    # Steps 1-2: REAL-WORLD FAILURE + mechanism (S5 measured machinery)
    retrieval = retrieve_failures(device_query, brand_name=brand_name,
                                  timeout=timeout)
    if retrieval["blocked"]:
        _step("real_world_failure", "BLOCKED_PROVIDER_FAILURE",
              {"provider_failures": retrieval["provider_failures"]})
        return _assemble(device_query, steps, candidates=[], blocked=True)
    maude, recall = retrieval["maude"], retrieval["recall"]
    _step("real_world_failure", "OK", {
        "maude_status": maude.status, "maude_records": len(maude.records),
        "recall_status": recall.status, "recall_records": len(recall.records),
        "retrieval_levels": retrieval.get("retrieval_levels"),
    })

    clusters = cluster_mechanisms(maude)
    recurring = [c for c in clusters if c.report_count >= RECURRENCE_MIN_REPORTS]
    _step("failure_mechanism", "OK" if clusters else "EMPTY", {
        "clusters": len(clusters), "recurring": len(recurring),
    })
    if maude.status == STATUS_EMPTY and recall.status == STATUS_EMPTY:
        _step("problem_existence_gate", "PROBLEM_NOT_DOCUMENTED", {})
        return _assemble(device_query, steps, candidates=[])
    if not recurring:
        _step("problem_existence_gate", "SIGNAL_BELOW_TRIAGE_THRESHOLD", {
            "threshold_basis": "MODEL_DERIVED recurrence triage (S5)",
        })
        return _assemble(device_query, steps, candidates=[])

    candidates = []
    for cluster in recurring[:2]:  # operational bound: top 2 mechanisms
        # Step 3: engineering constraint (S5)
        constraint = derive_constraint(cluster, device_query)
        # Step 4: existing solutions (S5)
        attempted = retrieve_attempted_solutions(
            device_query, cluster.mechanism_label, timeout=timeout)
        # Step 5: why they fail (new)
        why = why_they_fail(recall, maude, cluster, device_query)
        # Step 6: unresolved gap (S5)
        limitation = remaining_limitation(attempted, constraint)
        # Step 7: alternative physical principles (new)
        principles = alternative_physical_principles(constraint, attempted)
        # Step 8: cross-domain transfer (new)
        transfer = cross_domain_transfer(constraint, source_domain,
                                         timeout=timeout)
        # Step 9: invention candidate (new)
        cand = invention_candidate(device_query, cluster, constraint,
                                   principles, transfer)
        cand["chain_detail"] = {
            "constraint": constraint,
            "attempted_solutions": attempted,
            "why_they_fail": why,
            "remaining_limitation": limitation,
            "alternative_physical_principles": principles,
            "cross_domain_transfer": transfer,
        }
        candidates.append(cand)
        _step(f"chain:{cand['candidate_id']}", "OK", {
            "principles_found": len(principles),
            "transfer_domains": [d for d, v in transfer["per_domain"].items()
                                 if v.get("status") == "TRANSFER_EVIDENCE"],
            "killed_domains": [d for d, v in transfer["per_domain"].items()
                               if v.get("status") == "KILLED_NO_USABLE_TRANSFER"],
        })

    return _assemble(device_query, steps, candidates=candidates)


def _assemble(device_query: str, steps: List[Dict[str, Any]],
              candidates: List[Dict[str, Any]],
              blocked: bool = False) -> Dict[str, Any]:
    from discovery_fabric.source_registry.base import utc_now
    return {
        "operator": "FAILURE_TO_GAP_TO_OPPORTUNITY",
        "device_query": device_query,
        "run_timestamp": utc_now(),
        "chain_steps": steps,
        "candidates": candidates,
        "blocked": blocked,
        "epistemic_summary": {
            "problem": "OBSERVED where failure records exist (MAUDE/recall "
                       "custody attached)",
            "constraint": INFERENCE_CLASS,
            "why_they_fail": f"{EVIDENCE_CLASS} where root-cause records "
                             f"exist; NO_EVIDENCE otherwise",
            "gap": f"{INFERENCE_CLASS} bounded by retrieved set",
            "principles": f"{HYPOTHESIS_CLASS} ({TAXONOMY_CLASS} routing)",
            "transfer": f"{EVIDENCE_CLASS} per record; KILLED domains are "
                        f"measured retrievals",
            "candidate": INFERENCE_CLASS,
        },
    }
