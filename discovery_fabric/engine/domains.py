"""discovery_fabric/engine/domains.py — E6 automatic engineering-domain
detection and per-domain engineering reasoning templates.

CEO E6: the engine must determine the engineering domain automatically and
select the appropriate engineering reasoning template — not generic prose.

Detection is keyword-signal based and is recorded as MODEL_DERIVED: the
matched signals travel with the decision so a human can audit WHY the domain
was chosen (Art. XXI: relevance must be independently established, and any
relevance decision must be recorded).

Standards references emitted by templates are EXTERNAL_PRECEDENT candidates
with explicit verify_applicability flags — the generator never asserts that
a standard IS applicable (Art. II: exact evidence beats plausibility).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------
# Domain registry. Each template: disciplines, architecture blocks, materials,
# manufacturing candidates, verification methods, standards candidates.
# All content is ENGINEERING_PROPOSED unless traced to evidence by callers.
# --------------------------------------------------------------------------

DOMAIN_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "fluidics_hydraulic": {
        "label": "Fluid mechanics / hydraulics",
        "signals": ["fluid", "hydraulic", "catheter", "shunt", "valve",
                    "pressure drop", "flow rate", "lumen", "csf",
                    "cerebrospinal", "perfusion", "pump", "orifice",
                    "drainage", "osmotic", "viscos"],
        "disciplines": ["fluid mechanics", "mechanical engineering",
                        "biomedical engineering", "materials science"],
        "architecture_blocks": [
            "flow path / lumen architecture",
            "pressure regulation element",
            "sensing / feedback element (if closed-loop)",
            "termination interfaces (patient / reservoir)"],
        "materials_candidates": [
            {"material": "medical-grade silicone elastomer",
             "precedent": "standard CSF shunt catheter material",
             "verify_applicability": True},
            {"material": "polycarbonate / PSU rigid components",
             "precedent": "standard shunt valve housings",
             "verify_applicability": True}],
        "manufacturing_candidates": [
            {"process": "medical extrusion (catheter body)",
             "status": "ENGINEERING_PROPOSED"},
            {"process": "injection molding (housings, precision features)",
             "status": "ENGINEERING_PROPOSED"}],
        "verification_methods": [
            "bench flow-loop characterization across operating range",
            "pressure-drop mapping vs flow (identify regime transitions)",
            "accelerated occlusion / fouling challenge testing"],
        "standards_candidates": [
            {"standard": "ISO 13485 (QMS)", "verify_applicability": True},
            {"standard": "ISO 14971 (risk management)",
             "verify_applicability": True},
            {"standard": "ASTM F2394 (silicone elastomers for medical use)",
             "verify_applicability": True}],
    },
    "optical_photonic": {
        "label": "Optical transport / photonic power",
        "signals": ["optical", "laser", "photonic", "near-infrared", "nir",
                    "photovoltaic", "fiber", "wavelength", "fluence",
                    "lumen output", "led", "absorption coefficient"],
        "disciplines": ["optics", "photonic engineering", "thermal management",
                        "electrical engineering"],
        "architecture_blocks": [
            "source (emitter / external illuminator)",
            "transport medium (free-space / fiber / tissue)",
            "receiver / conversion element",
            "thermal path and safety interlocks"],
        "materials_candidates": [
            {"material": "GaAs / III-V photovoltaic converter",
             "precedent": "NIR power-over-fiber practice",
             "verify_applicability": True},
            {"material": "biocompatible optical window (sapphire / PDMS)",
             "precedent": "implant optical interfaces",
             "verify_applicability": True}],
        "manufacturing_candidates": [
            {"process": "die bonding + wire bonding on carrier",
             "status": "ENGINEERING_PROPOSED"},
            {"process": "hermetic encapsulation of optical window",
             "status": "ENGINEERING_PROPOSED"}],
        "verification_methods": [
            "fluence / irradiance mapping at target depth (tissue phantom)",
            "conversion efficiency vs wavelength and alignment",
            "thermal load rise measurement at interface"],
        "standards_candidates": [
            {"standard": "IEC 60825 (laser product safety)",
             "verify_applicability": True},
            {"standard": "ISO 10993 (biocompatibility)",
             "verify_applicability": True}],
    },
    "ml_data": {
        "label": "Data architecture / machine learning",
        "signals": ["machine learning", "neural", "predictor", "model",
                    "training data", "classifier", "bayesian", "forecast",
                    "algorithm", "neuromorphic", "inference"],
        "disciplines": ["data engineering", "machine learning",
                        "software engineering", "statistics"],
        "architecture_blocks": [
            "data ingestion and labeling pipeline",
            "feature / representation layer",
            "model + uncertainty quantification",
            "deployment target + monitoring loop"],
        "materials_candidates": [],
        "manufacturing_candidates": [
            {"process": "MLOps pipeline (CI for data + model)",
             "status": "ENGINEERING_PROPOSED"}],
        "verification_methods": [
            "held-out + temporal validation splits",
            "calibration and decision-threshold analysis",
            "failure-mode stress tests (distribution shift)"],
        "standards_candidates": [
            {"standard": "FDA GMLP (Good Machine Learning Practice) guiding principles",
             "verify_applicability": True}],
    },
    "rf_wireless": {
        "label": "RF / wireless link",
        "signals": ["rf", "wireless", "antenna", "uwb", "link budget",
                    "sar", "telemetry", "transceiver", "bandwidth",
                    "localization", "ghz", "mhz"],
        "disciplines": ["RF engineering", "antenna design",
                        "signal processing", "EMC"],
        "architecture_blocks": [
            "transmit chain + power limits",
            "channel / tissue path (path loss model)",
            "receive chain + detection",
            "regulatory exposure constraint (SAR)"],
        "materials_candidates": [
            {"material": "biocompatible antenna dielectric",
             "precedent": "implant telemetry practice",
             "verify_applicability": True}],
        "manufacturing_candidates": [
            {"process": "PCB + chip-scale RF front end",
             "status": "ENGINEERING_PROPOSED"}],
        "verification_methods": [
            "link-budget verification in tissue-equivalent phantom",
            "SAR simulation + measurement against limit",
            "bit-error-rate vs distance/depth curve"],
        "standards_candidates": [
            {"standard": "IEEE C95.1 (RF exposure)",
             "verify_applicability": True},
            {"standard": "FCC Part 15", "verify_applicability": True}],
    },
    "acoustic": {
        "label": "Acoustics / ultrasonics",
        "signals": ["acoustic", "ultrasound", "transducer", "piezoelectric",
                    "sonic", "echo", "impedance contrast", "resonan"],
        "disciplines": ["acoustics", "transducer engineering",
                        "signal processing", "materials science"],
        "architecture_blocks": [
            "transducer element + matching layer",
            "excitation / receive electronics",
            "signal chain (detection criterion)",
            "coupling path to target medium"],
        "materials_candidates": [
            {"material": "PZT / PVDF active element",
             "precedent": "standard ultrasonic transducers",
             "verify_applicability": True}],
        "manufacturing_candidates": [
            {"process": "diced ceramic + backing assembly",
             "status": "ENGINEERING_PROPOSED"}],
        "verification_methods": [
            "impedance-contrast detection threshold in phantom",
            "crosstalk and noise floor characterization",
            "durability under cyclic excitation"],
        "standards_candidates": [
            {"standard": "IEC 60601-2-37 (ultrasound therapy/monitoring safety)",
             "verify_applicability": True}],
    },
    "mri_nmr": {
        "label": "MRI physics / NMR sensing",
        "signals": ["mri", "nmr", "larmor", "gradient coil", "rf coil",
                    "b0", "relaxation", "phase contrast", "tesla",
                    "magnetometer", "proton density"],
        "disciplines": ["MRI physics", "RF coil engineering",
                        "magnetics", "signal processing"],
        "architecture_blocks": [
            "magnet / field source (if active)",
            "RF transmit/receive chain",
            "gradient or encoding mechanism",
            "reconstruction / estimation pipeline"],
        "materials_candidates": [
            {"material": "non-ferromagnetic structural materials (MR-conditional)",
             "precedent": "MR-conditional implant practice",
             "verify_applicability": True}],
        "manufacturing_candidates": [
            {"process": "precision micro-coil winding",
             "status": "ENGINEERING_PROPOSED"}],
        "verification_methods": [
            "SNR characterization vs field strength at scale",
            "MR-safety testing (torque, heating) in scanner",
            "flow-quantization accuracy vs reference MRI"],
        "standards_candidates": [
            {"standard": "ASTM F2502 / MR-conditional marking practice",
             "verify_applicability": True},
            {"standard": "IEC 60601-2-33 (MR safety)",
             "verify_applicability": True}],
    },
    "enzyme_biocatalytic": {
        "label": "Reaction kinetics / enzyme engineering",
        "signals": ["enzyme", "kinetic", "substrate", "catalytic", "immobiliz",
                    "michaelis", "active site", "cleave", "proteolytic",
                    "amyloid", "nep "],
        "disciplines": ["biochemical engineering", "enzyme kinetics",
                        "surface chemistry", "mass transport"],
        "architecture_blocks": [
            "catalytic surface (immobilization chemistry)",
            "substrate transport path (convection + diffusion)",
            "contact-time control element",
            "stability / leaching containment"],
        "materials_candidates": [
            {"material": "enzyme immobilization on functionalized polymer",
             "precedent": "biocatalytic reactor practice",
             "verify_applicability": True}],
        "manufacturing_candidates": [
            {"process": "surface functionalization + enzyme coupling (GMP)",
             "status": "ENGINEERING_PROPOSED"}],
        "verification_methods": [
            "residual activity vs time in target fluid",
            "mass-transfer-limited rate measurement",
            "leaching / immunogenic byproduct assays"],
        "standards_candidates": [
            {"standard": "ISO 10993 (biocompatibility + degradation)",
             "verify_applicability": True}],
    },
    "phage_microbio": {
        "label": "Microbiology / phage anti-biofilm",
        "signals": ["phage", "antibiofilm", "biofilm", "bacteriophag",
                    "antimicrobial", "s. aureus", "infection", "cfu",
                    "microbi"],
        "disciplines": ["microbiology", "surface engineering",
                        "pharmacodynamics", "materials science"],
        "architecture_blocks": [
            "phage loading / immobilization layer",
            "release or contact-kill mechanism",
            "surface substrate (coating architecture)",
            "stability preservation element"],
        "materials_candidates": [
            {"material": "electrospun + metal-coated catheter surface",
             "precedent": "anti-infective device coatings",
             "verify_applicability": True}],
        "manufacturing_candidates": [
            {"process": "electrospinning + phage immobilization dip",
             "status": "ENGINEERING_PROPOSED"}],
        "verification_methods": [
            "phage infectivity retention vs time on surface",
            "biofilm prevention CFU challenge assay",
            "host-range and resistance-emergence check"],
        "standards_candidates": [
            {"standard": "ISO 22196 (antimicrobial surface activity)",
             "verify_applicability": True}],
    },
    "mechanical_structural": {
        "label": "Mechanics / structures",
        "signals": ["buckling", "stiffness", "fatigue", "structural",
                    "steer", "flexur", "beam", "torque", "mechanical",
                    "kink", "shaft", "articulat"],
        "disciplines": ["mechanical engineering", "structural analysis",
                        "fatigue and fracture", "materials science"],
        "architecture_blocks": [
            "load path / structural backbone",
            "actuation or compliance element",
            "guidance / bearing interfaces",
            "fatigue-critical features register"],
        "materials_candidates": [
            {"material": "nitinol / polymer composite members",
             "precedent": "minimally invasive device practice",
             "verify_applicability": True}],
        "manufacturing_candidates": [
            {"process": "laser-cut hypotube / braided polymer composite",
             "status": "ENGINEERING_PROPOSED"}],
        "verification_methods": [
            "buckling / kink margin tests across duty cycle",
            "fatigue life (run-out) testing",
            "friction and wear characterization"],
        "standards_candidates": [
            {"standard": "ASTM F2516 (nitinol tension)",
             "verify_applicability": True}],
    },
    "thermal": {
        "label": "Thermal management / heat transfer",
        "signals": ["thermal", "heat", "temperature rise", "cooling",
                    "conduction", "convection coefficient", "hotspot"],
        "disciplines": ["heat transfer", "thermal engineering",
                        "materials science"],
        "architecture_blocks": [
            "heat source characterization",
            "conduction path / spreader",
            "reject interface",
            "safety limit interlock"],
        "materials_candidates": [
            {"material": "biocompatible thermal spreader (graphite/AlN)",
             "precedent": "implant electronics thermal practice",
             "verify_applicability": True}],
        "manufacturing_candidates": [
            {"process": "bonded spreader + encapsulation",
             "status": "ENGINEERING_PROPOSED"}],
        "verification_methods": [
            "temperature-rise mapping at max duty",
            "interface resistance characterization",
            "worst-case ambient soak test"],
        "standards_candidates": [
            {"standard": "IEC 60601-1 (general electrical safety, thermal)",
             "verify_applicability": True}],
    },
}

GENERIC_TEMPLATE: Dict[str, Any] = {
    "label": "NOT ESTABLISHED — generic engineering template",
    "signals": [],
    "disciplines": ["systems engineering"],
    "architecture_blocks": [
        "input interface", "transformation element", "output interface",
        "failure containment"],
    "materials_candidates": [],
    "manufacturing_candidates": [],
    "verification_methods": [
        "function-level bench verification",
        "boundary-condition stress testing"],
    "standards_candidates": [],
}


# --------------------------------------------------------------------------
def detect_domain(text: str) -> Dict[str, Any]:
    """Score keyword signals across templates; return the detected domain with
    its matched signals (recorded for audit, MODEL_DERIVED). Ties are broken
    by (hit count, template declaration order). No hits -> generic template
    with domain UNKNOWN — recorded honestly, not guessed."""
    t = f" {text.lower()} "
    scores: List[Tuple[str, int, List[str]]] = []
    for domain_id, tpl in DOMAIN_TEMPLATES.items():
        hits = [s for s in tpl["signals"] if s in t]
        if hits:
            scores.append((domain_id, len(hits), hits))
    if not scores:
        return {"domain": "UNKNOWN",
                "template": GENERIC_TEMPLATE,
                "matched_signals": [],
                "epistemic_class": "MODEL_DERIVED",
                "note": "no domain signals matched; generic template with "
                        "domain NOT ESTABLISHED (Art. XXV: unknown stays "
                        "unknown)"}
    scores.sort(key=lambda x: -x[1])
    best_id, best_n, hits = scores[0]
    return {
        "domain": best_id,
        "template": DOMAIN_TEMPLATES[best_id],
        "matched_signals": hits,
        "runner_up": {"domain": scores[1][0], "hits": scores[1][1]}
        if len(scores) > 1 else None,
        "epistemic_class": "MODEL_DERIVED",
        "note": f"{best_n} distinct domain signals matched",
    }


def domain_label(domain_id: str) -> str:
    if domain_id == "UNKNOWN":
        return GENERIC_TEMPLATE["label"]
    return DOMAIN_TEMPLATES.get(domain_id, GENERIC_TEMPLATE)["label"]
