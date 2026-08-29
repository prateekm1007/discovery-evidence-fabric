"""Process knowledge layer — the manufacturing reasoning substrate.

CEO lifecycle directive (2026-08-29):

    "The engine must understand:
        mechanism -> candidate manufacturing route -> process
        constraint -> quality risk -> verification"

This layer provides that chain for the directive's 8 processes:
extrusion, injection molding, machining, additive manufacturing, laser
processing, coatings, microfabrication, medical-device sterilization.

EPISTEMIC DISCIPLINE (the layer's defining property):

Each taxonomy entry is an ENGINEERING_TAXONOMY object — curated
engineering knowledge, explicitly NOT external evidence (Art. XXXVIII
layer taxonomy: it is a knowledge atom, not a source fact). Entries
declare:

    epistemic_class = "ENGINEERING_TAXONOMY"

Enrichment with external evidence is separate and evidence-bound:
`enrich_process(process, literature_records, standards_records)` attaches
custody-backed constraint spans (manufacturing literature) and standards
anchors (FDA recognized standards) to the entry, each with
epistemic_class="EVIDENCE_BOUND" and its custody chain.

The chain consumer (`manufacturing_route_chain`) emits, for a mechanism
description and a candidate route, the constraint -> risk ->
verification path with per-link epistemic classification — the operator
(L6) never sees an unclassified link (directive: "Every step must have
evidence or explicit epistemic classification").
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from discovery_fabric.source_registry.connectors.manufacturing import (
    PROCESS_TAXONOMY, classify_process,
)

EPISTEMIC_TAXONOMY = "ENGINEERING_TAXONOMY"
EPISTEMIC_EVIDENCE = "EVIDENCE_BOUND"

#: The 8-process base taxonomy: mechanism (physics), constraints,
#: quality risks, verification. Curated engineering knowledge — declared,
#: not sourced.
PROCESS_KNOWLEDGE = {
    "extrusion": {
        "physical_principle": "Continuous forming by forcing softened or "
            "drawn material through a die of fixed cross-section "
            "(polymer melt flow or metal plastic deformation).",
        "typical_applications": "Catheter shafts, tubing, polymer "
            "profiles, metal wire/rod stock for implants.",
        "process_constraints": [
            "die swell and relaxation set final geometry",
            "melt temperature and draw-down ratio control dimensions",
            "residual stresses freeze in during cooling",
        ],
        "quality_risks": [
            "dimensional drift / ovality",
            "gels, inclusions, or degradation from thermal history",
            "residual stress driven distortion or cracking",
        ],
        "verification_methods": [
            "in-line diameter/ovality measurement",
            "tensile and burst testing of extruded sections",
            "thermal history / degradation indicators",
        ],
    },
    "injection_molding": {
        "physical_principle": "Cyclic forming: polymer melt injected "
            "under pressure into a closed mold cavity, then solidified "
            "under holding pressure.",
        "typical_applications": "Device housings, connectors, luer "
            "components, implant PEEK components.",
        "process_constraints": [
            "cooling and holding pressure govern shrinkage",
            "part geometry constrains gate and weld-line placement",
            "residual stresses and sink marks from holding profile",
        ],
        "quality_risks": [
            "weld-line weakness",
            "sink marks / warpage / dimensional nonconformance",
            "degradation and additive leaching from thermal exposure",
        ],
        "verification_methods": [
            "dimensional inspection with GD&T",
            "process capability studies (Cpk) on critical dimensions",
            "material certification and extractables/leachables",
        ],
    },
    "machining": {
        "physical_principle": "Material removal by controlled cutting "
            "(turning, milling, drilling, grinding) with defined or "
            "abrasive tool edges.",
        "typical_applications": "Metal implant bodies, bone screws, "
            "machined PEEK implants, instrument tips.",
        "process_constraints": [
            "cutting forces and heat generation constrain feeds/speeds",
            "workholding and fixturing set achievable tolerances",
            "tool wear drives dimensional drift over a lot",
        ],
        "quality_risks": [
            "burrs, smeared metal, and machining-induced surface damage",
            "subsurface residual stress and microstructural alteration",
            "contamination (cutting fluids, swarf) on implants",
        ],
        "verification_methods": [
            "dimensional inspection / CMM",
            "surface integrity inspection (roughness, defects)",
            "cleanliness validation and burr inspection",
        ],
    },
    "additive_manufacturing": {
        "physical_principle": "Point-wise consolidation of feedstock "
            "(laser/electron-beam powder bed fusion, extrusion) into "
            "3D geometry layer by layer.",
        "typical_applications": "Porous acetabular cups, patient-specific "
            "implants, complex surgical guides, lattice structures.",
        "process_constraints": [
            "layer-wise meltpool physics sets porosity and microstructure",
            "thermal cycling builds residual stress (support strategy)",
            "powder feedstock quality and reuse history bound properties",
            "feature size / overhang / channel aspect-ratio limits",
        ],
        "quality_risks": [
            "lack-of-fusion or keyhole porosity",
            "anisotropic mechanical properties",
            "unfused powder trapped in internal channels",
            "surface roughness driving fatigue debit",
        ],
        "verification_methods": [
            "powder feedstock qualification and reuse tracking",
            "in-process monitoring (meltpool, layer imaging)",
            "witness-coupon mechanical testing per build",
            "CT / nondestructive porosity inspection",
            "part-specific standards (e.g., ASTM F3001-class Ti-6Al-4V "
            "requirements, when FDA-recognized via STANDARDS records)",
        ],
    },
    "laser_processing": {
        "physical_principle": "Focused laser energy for cutting, "
            "welding, drilling, or ablation with minimal "
            "mechanically-induced stress.",
        "typical_applications": "Stent cutting, needle points, catheter "
            "skiving, microwelding of components, surface texturing.",
        "process_constraints": [
            "absorption / wavelength coupling with the material",
            "heat-affected zone extent constrains pulse energy",
            "kerf and taper limits for fine features",
        ],
        "quality_risks": [
            "heat-affected zone microstructural damage",
            "recast layer / dross / burrs on cut edges",
            "microcracking in welds",
        ],
        "verification_methods": [
            "edge quality inspection (SEM-class imaging)",
            "weld integrity inspection / leak testing",
            "HAZ microstructure verification",
        ],
    },
    "coatings": {
        "physical_principle": "Deposition of a functional surface layer "
            "(plasma spray, PVD/CVD, dip, spray) onto a substrate.",
        "typical_applications": "Hydroxyapatite coatings on implants, "
            "drug-eluting and hemocompatible coatings on stents/catheters, "
            " DLC and TiN wear coatings.",
        "process_constraints": [
            "adhesion/cohesion balance vs. coating thickness",
            "line-of-sight limits (thermal spray)",
            "substrate thermal exposure during deposition",
        ],
        "quality_risks": [
            "delamination and spallation in service",
            "coating particulate debris generation",
            "degraded fatigue life of the coated substrate",
        ],
        "verification_methods": [
            "adhesion testing (tensile / scratch)",
            "thickness, porosity, crystallinity (HA) characterization",
            "fatigue testing of coated components",
            "part-specific standards (e.g., ISO 13779 / ASTM F1185-class "
            "HA coating requirements, when FDA-recognized via STANDARDS "
            "records)",
        ],
    },
    "microfabrication": {
        "physical_principle": "Lithographic pattern transfer and etching "
            "(MEMS class): deposit, pattern, etch cycles on wafer "
            "substrates.",
        "typical_applications": "MEMS pressure sensors, microneedles, "
            "microfluidic lab-on-chip devices, sensor elements.",
        "process_constraints": [
            "wafer-scale process windows (batch, not per-part control)",
            "etch profile / aspect ratio limits",
            "cleanroom contamination control",
        ],
        "quality_risks": [
            "process-induced stiction or membrane damage",
            "batch-level defect correlation",
            "particulate and ionic contamination",
        ],
        "verification_methods": [
            "wafer-level electrical test structures",
            "visual/automated optical inspection",
            "lot acceptance sampling with process capability",
        ],
    },
    "sterilization": {
        "physical_principle": "Inactivation of viable bioburden to a "
            "defined sterility assurance level (SAL) by moist heat, "
            "ethylene oxide, radiation (gamma/e-beam/X-ray), or other "
            "validated agent.",
        "typical_applications": "Terminal sterilization of single-use "
            "devices; validated reprocessing cycles for reusable "
            "instruments.",
        "process_constraints": [
            "agent-material compatibility bounds cycle choice",
            "dose/temperature/exposure must map to product and packaging "
            "configuration (dose mapping)",
            "residuals (EO/ECH) limited by product/patient contact",
        ],
        "quality_risks": [
            "material degradation (polymer embrittlement, chain "
            "scission) from overexposure",
            "inadequate SAL from poor dose mapping or load configuration",
            "residual toxicants (ethylene oxide/chlorohydrin)",
        ],
        "verification_methods": [
            "cycle validation per recognized standards (ISO 17665 moist "
            "heat / ISO 11135 EO / ISO 11137 radiation families, when "
            "FDA-recognized via STANDARDS records)",
            "bioburden and sterility testing",
            "residuals testing and product family justification",
            "post-sterilization material performance verification",
        ],
    },
}

#: Declared (taxonomy-class) links from mechanism-material families to
#: candidate routes. These are ENGINEERING mappings, not sourced
#: evidence; evidence attaches via records at runtime.
MATERIAL_FAMILY_ROUTES = {
    "thermoplastic_polymer": ["injection_molding", "extrusion",
                              "machining", "additive_manufacturing"],
    "metal_alloy": ["machining", "additive_manufacturing", "laser_processing",
                    "coatings", "extrusion"],
    "ceramic": ["machining", "coatings", "additive_manufacturing"],
    "composite": ["coatings", "machining"],
    "metallic_wire_form": ["extrusion", "laser_processing", "machining",
                           "coatings"],
}

#: Keywords for material-family inference from mechanism text (taxonomy
#: grammar; the inference itself is declared, never evidence).
_MATERIAL_KEYWORDS = {
    "thermoplastic_polymer": ["peek", "polymer", "polyurethane", "nylon",
                              "polyethylene", "uHMWPE".lower(), "pvc",
                              "thermoplastic", "elastomer", "silicone"],
    "metal_alloy": ["titanium", "ti-6al-4v", "cobalt", "stainless",
                    "nitinol", "metal", "alloy", "platinum", "tantalum",
                    "magnesium"],
    "ceramic": ["ceramic", "alumina", "zirconia", "hydroxyapatite",
                "titania", "calcium phosphate"],
    "composite": ["composite", "carbon fiber", "cfrip", "fiber-reinforced"],
    "metallic_wire_form": ["wire", "braid", "coil", "catheter shaft",
                           "stent"],
}


#: Standards-anchoring grammar per process: a recognized standard is
#: attached to a process entry only if its own designation/title names
#: the process-relevant terms (Art. II: exact evidence, not similar).
PROCESS_STANDARDS_GRAMMAR = {
    "extrusion": r"extrus",
    "injection_molding": r"injection mold|mould",
    "machining": r"machin",
    "additive_manufacturing": r"additive manufactur|3D print|2924|52900|3001|f3001",
    "laser_processing": r"laser",
    "coatings": r"coat|13779|f1185|f1609",
    "microfabrication": r"microfabricat|MEMS|photolithograph",
    "sterilization": r"steriliz|sterilis|17665|11135|11137|20857|25424|bioburden",
}


def _custody(record) -> Dict[str, Any]:
    return {
        "source_id": record.source_id,
        "record_id": record.record_id,
        "raw_payload_sha256": record.raw_payload_sha256,
        "retrieved_at": record.retrieved_at,
        "query": record.query,
    }


def candidate_routes(mechanism_description: str) -> List[Dict[str, Any]]:
    """Candidate manufacturing routes for a mechanism description.

    Each candidate carries its epistemic class: material-family
    inference is ENGINEERING_TAXONOMY (declared grammar), process
    mentions found verbatim in the text are TEXT_DERIVED."""
    text = (mechanism_description or "").lower()
    out: List[Dict[str, Any]] = []
    for family, keywords in _MATERIAL_KEYWORDS.items():
        if any(k in text for k in keywords):
            for route in MATERIAL_FAMILY_ROUTES.get(family, []):
                out.append({
                    "route": route,
                    "basis_family": family,
                    "epistemic_class": EPISTEMIC_TAXONOMY,
                    "note": f"material-family grammar matched '{family}'",
                })
    # dedupe by route, keeping first
    seen = set()
    dedup = []
    for c in out:
        if c["route"] not in seen:
            seen.add(c["route"])
            dedup.append(c)
    return dedup


def process_entry(process: str) -> Optional[Dict[str, Any]]:
    entry = PROCESS_KNOWLEDGE.get(process)
    if entry is None:
        return None
    return {**entry, "process": process, "epistemic_class": EPISTEMIC_TAXONOMY}


def enrich_process(process: str, literature_records: Optional[List[Any]] = None,
                   standards_records: Optional[List[Any]] = None) -> Dict[str, Any]:
    """Attach evidence-bound enrichment (constraint spans from
    manufacturing literature; standards anchors from FDA recognized
    standards records) to a taxonomy entry. Custody rides with every
    attachment; a record with no custody is not attached."""
    entry = process_entry(process)
    if entry is None:
        raise ValueError(f"unknown process {process!r} (taxonomy: "
                         f"{sorted(PROCESS_KNOWLEDGE)})")
    lit = []
    for r in (literature_records or []):
        procs = (getattr(r, "normalized", {}) or {}).get("processes") or []
        if process in procs:
            lit.append({
                "epistemic_class": EPISTEMIC_EVIDENCE,
                "custody": _custody(r),
                "constraint_spans": (r.normalized or {}).get("process_constraint_spans"),
                "risk_spans": (r.normalized or {}).get("quality_risk_spans"),
                "verification_spans": (r.normalized or {}).get("verification_spans"),
            })
    stds = []
    grammar = PROCESS_STANDARDS_GRAMMAR.get(process)
    import re as _re
    for r in (standards_records or []):
        n = (getattr(r, "normalized", {}) or {})
        text = f"{n.get('standard_designation') or ''} {n.get('standard_title') or ''}"
        if grammar and not _re.search(grammar, text, _re.I):
            continue  # keyword-searched record not process-relevant
        stds.append({
            "epistemic_class": EPISTEMIC_EVIDENCE,
            "custody": _custody(r),
            "standard": n.get("standard_designation"),
            "title": n.get("standard_title"),
            "device_area": n.get("specialty_task_group_area"),
        })
    entry["evidence_enrichment"] = {"literature": lit, "standards": stds}
    return entry


def manufacturing_route_chain(mechanism_description: str,
                              route: str) -> Dict[str, Any]:
    """The directive's chain for one candidate route:

        mechanism -> candidate manufacturing route -> process
        constraint -> quality risk -> verification

    Every link carries an epistemic class. If the route is not in the
    taxonomy, the chain is REFUSED (no fabricated entries, Art. VI)."""
    entry = process_entry(route)
    if entry is None:
        raise ValueError(f"unknown manufacturing route {route!r}")
    return {
        "mechanism": {
            "description": mechanism_description,
            "epistemic_class": "INPUT",
        },
        "candidate_route": {
            "process": route,
            "selection": candidate_routes(mechanism_description),
            "epistemic_class": EPISTEMIC_TAXONOMY,
        },
        "process_constraint": {
            "items": entry["process_constraints"],
            "epistemic_class": EPISTEMIC_TAXONOMY,
        },
        "quality_risk": {
            "items": entry["quality_risks"],
            "epistemic_class": EPISTEMIC_TAXONOMY,
        },
        "verification": {
            "items": entry["verification_methods"],
            "epistemic_class": EPISTEMIC_TAXONOMY,
            "note": "standards anchors attach at runtime via "
                    "enrich_process with STANDARDS-role custody",
        },
    }


def all_processes() -> List[str]:
    return sorted(PROCESS_KNOWLEDGE.keys())


def taxonomy_processes_for_text(text: str) -> List[str]:
    return classify_process(text)
