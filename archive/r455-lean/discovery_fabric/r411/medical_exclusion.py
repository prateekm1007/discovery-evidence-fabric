"""discovery_fabric/r411/medical_exclusion.py — Directive s1 hard domain gate.

R411 selects NON-MEDICAL technologies. This module is the deterministic
exclusion screen: any candidate whose final commercial application is a
medical device, component, or use is EXCLUDED before scoring, no matter how
strong its other properties. The screen is vocabulary-based (recorded,
auditable, no LLM judgment involved — Art. XXVII: the rule is explicit and
mechanical) and evaluates the candidate's TARGET APPLICATION, not the
origin of its physics (the directive explicitly allows non-medical use of
physics that originated in medicine).

Constitution notes:
  - Art. XXI.4 discipline: the screen's verdict is recorded with the
    matched terms, so a human can audit WHY a candidate was excluded.
  - The screen errs on the side of EXCLUSION (fail-closed, Art. V) for
    regulated medical surfaces, but does NOT exclude industrial,
    agricultural, energy, aerospace... uses of the same physics.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

# Terms that indicate a MEDICAL final application (directive s1 list).
MEDICAL_APPLICATION_TERMS = [
    "clinical", "implantable", "implant", "patient", "surgical",
    "surgery", "diagnosis", "diagnostic", "drug delivery", "drug-delivery",
    "prosthes", "prosthetic", "medical sensor", "medical device",
    "medical robotics", "clinical monitoring", "medical imaging",
    "hospital equipment", "therapeutic", "therapy device", "csf",
    "cerebrospinal", "shunt", "catheter for", "in vivo", "in-vivo",
    "fda class", "biocompatib", "steril", "disinfect patient",
    "biopsy", "dialysis", "ventilator", "stethoscope", "endoscop",
    "pacemaker", "defibrillator", "glucose monitor", "insulin",
    "wound dressing", "bandage", "suture", "stent", "graft",
    "cannula", "tracheal", "anesthesi", "radiotherapy", "chemotherapy",
    "medical", "medicinal", "healthcare device", "patient monitor",
    "wearable health", "hearing aid", "dental", "ophthalmic device",
    "orthopedic implant", "spinal implant", "neurosurg",
]

# Terms that indicate a NON-MEDICAL industrial/energy/... application —
# used to override weak matches when the dominant application context is
# clearly non-medical (e.g. "thermal management of medical data-center
# equipment" is not a thing, but "sensor for pipeline fouling" with a
# passing 'patient' collision in the evidence text is not medical either
# — the override only applies to the candidate's own application fields).
NON_MEDICAL_CONTEXT_TERMS = [
    "industrial", "pipeline", "power plant", "grid", "battery",
    "data center", "datacenter", "semiconductor", "manufacturing",
    "automotive", "aerospace", "marine", "mining", "agricultur",
    "construction", "hvac", "refrigerat", "heat exchanger", "boiler",
    "turbine", "compressor", "pump", "valve", "reactor", "distillation",
    "wastewater", "desalination", "cargo", "logistics", "warehouse",
    "steel", "cement", "glass", "paper mill", "food processing",
    "textile", "printing", "machining", "welding", "casting", "forging",
    "extrusion", "rolling", "conveyor", "crane", "excavator",
    "drilling", "fracking", "refinery", "petrochemical", "polymer",
    "photovoltaic", "wind turbine", "inverter", "motor", "generator",
    "transformer", "transmission line", "telecommunication", "antenna",
    "optical fiber", "laser machining", "lithography", "wafer",
    "cooling tower", "chiller", "thermal management", "electronics",
    "circuit board", "sensor network", "structural health monitoring",
    "corrosion protection", "fouling", "erosion", "cavitation",
]


def _hits(text: str, terms: List[str]) -> List[str]:
    found = []
    for t in terms:
        if re.search(re.escape(t), text, re.IGNORECASE):
            found.append(t)
    return found


def medical_exclusion_screen(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Screen ONE candidate's target application against the s1 exclusion.

    Evaluates the candidate's TARGET application fields (technology
    name, problem, intervention, target domain/customer, system
    context) — NOT its source-domain origin fields. The directive
    explicitly allows a technology whose physics originated in
    medicine, provided the FINAL COMMERCIAL APPLICATION is non-medical;
    medical vocabulary in the source-domain origin therefore does not
    exclude, while medical vocabulary in the target application does.

    Returns a record: {excluded: bool, verdict, matched_medical_terms,
    matched_non_medical_terms, basis}. The verdict vocabulary:
      EXCLUDED_MEDICAL       — medical application terms in the TARGET
      NON_MEDICAL            — no target-field medical terms
      MEDICAL_ADJACENT_FLAG  — mixed signals in target fields; NOT
                               excluded but flagged for human review
                               (honest middle state, Art. XXV)
    """
    target_text = " ".join(str(candidate.get(f) or "") for f in (
        "technology_name", "problem", "target_application",
        "target_customer", "system_context", "target_domain",
        "intervention",
    ))
    origin_text = " ".join(str(candidate.get(f) or "") for f in (
        "mechanism", "source_domain", "cross_domain_transition",
    ))
    med = _hits(target_text, MEDICAL_APPLICATION_TERMS)
    med_origin = _hits(origin_text, MEDICAL_APPLICATION_TERMS)
    nonmed = _hits(target_text, NON_MEDICAL_CONTEXT_TERMS)

    if not med:
        return {
            "excluded": False,
            "verdict": "NON_MEDICAL",
            "matched_medical_terms": [],
            "matched_non_medical_terms": nonmed,
            "medical_terms_in_origin_only": med_origin,
            "basis": "no medical-application vocabulary in the target "
                     "application fields"
                     + (f" (origin-field medical vocabulary present: "
                        f"{med_origin[:3]} — physics origin, allowed "
                        f"by s1)" if med_origin else ""),
        }
    strong_medical = [t for t in med if t in (
        "implantable", "implant", "surgical", "surgery", "prosthes",
        "prosthetic", "stent", "pacemaker", "medical device",
        "medical sensor", "clinical", "diagnostic", "diagnosis",
        "drug delivery", "drug-delivery", "medical", "therapeutic",
        "hospital equipment", "medical imaging", "clinical monitoring",
        "medical robotics", "dialysis", "ventilator", "endoscop",
    )]
    # fail-closed: strong target-field medical markers exclude unless
    # the target ALSO carries substantial non-medical context (>=2
    # non-medical context hits) — then flag for human review rather
    # than silently resolving either way
    if strong_medical and len(nonmed) >= 2:
        return {
            "excluded": False,
            "verdict": "MEDICAL_ADJACENT_FLAG",
            "matched_medical_terms": med,
            "matched_non_medical_terms": nonmed,
            "medical_terms_in_origin_only": med_origin,
            "basis": "strong medical vocabulary AND substantial "
                     "non-medical target context; flagged for human "
                     "review rather than silently resolved",
        }
    if strong_medical:
        return {
            "excluded": True,
            "verdict": "EXCLUDED_MEDICAL",
            "matched_medical_terms": med,
            "matched_non_medical_terms": nonmed,
            "medical_terms_in_origin_only": med_origin,
            "basis": "strong medical-application markers in the target "
                     "fields without substantial non-medical target "
                     "context",
        }
    return {
        "excluded": False,
        "verdict": "MEDICAL_ADJACENT_FLAG",
        "matched_medical_terms": med,
        "matched_non_medical_terms": nonmed,
        "medical_terms_in_origin_only": med_origin,
        "basis": "weak medical collision in target fields; flagged",
    }


def screen_pool(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Screen a candidate pool; returns per-candidate screens + counts."""
    screens = []
    for c in candidates:
        s = medical_exclusion_screen(c)
        s["candidate_id"] = c.get("candidate_id")
        c["medical_screen"] = s
        screens.append(s)
    excluded = [s for s in screens if s["excluded"]]
    flagged = [s for s in screens
               if s["verdict"] == "MEDICAL_ADJACENT_FLAG" and not s["excluded"]]
    return {
        "screened": len(screens),
        "excluded_medical": len(excluded),
        "medical_adjacent_flagged": len(flagged),
        "non_medical": len(screens) - len(excluded),
        "screens": screens,
    }
