"""discovery_fabric/engine/domains.py — E6 + CEO Directive 4: automatic
engineering-domain detection and per-domain engineering reasoning modules.

CEO E6: the engine must determine the engineering domain automatically and
select the appropriate engineering reasoning template — not generic prose.

CEO Directive 4: a canonical ENGINEERING_DOMAIN_REGISTRY.json maps
evidence/mechanism characteristics (signals) to engineering modules. Every
domain module specifies governing_models, critical_parameters, failure_modes,
design_input_patterns, design_output_patterns, verification_methods,
validation_methods and manufacturing_patterns. This is what lets a newly
discovered invention reach the depth of the 15 existing dossiers
automatically. The published registry artifact is generated from this module
by `export_registry_json()`; a sync test pins them together (single code
authority, one published canonical artifact).

Detection is keyword-signal based and is recorded as MODEL_DERIVED: the
matched signals travel with the decision so a human can audit WHY the domain
was chosen (Art. XXI: relevance must be independently established, and any
relevance decision must be recorded).

Standards references and candidate parameters emitted by templates are
EXTERNAL_PRECEDENT / ENGINEERING_PROPOSED candidates with explicit
verify_applicability flags — the generator never asserts that a standard IS
applicable or that a candidate parameter IS the design value (Art. II:
exact evidence beats plausibility; Art. XXVII: no threshold invention).
"""
from __future__ import annotations

import re

from typing import Any, Dict, List, Optional, Sequence, Tuple

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
            "termination interfaces (application-context-specific: "
            "source and sink boundaries)"],
        # R443 context de-conflation: medical-context architecture
        # lives in the parallel list and participates ONLY when the
        # canonical applicability is medical (applicability.py filter).
        "architecture_blocks_medical": [
            "termination interfaces (patient / reservoir)"],
        "materials_candidates": [
            {"material": "medical-grade silicone elastomer",
             "precedent": "standard CSF shunt catheter material",
             "verify_applicability": True,
             "applicability_context": "MEDICAL"},
            {"material": "polycarbonate / PSU rigid components",
             "precedent": "standard shunt valve housings",
             "verify_applicability": True,
             "applicability_context": "MEDICAL"},
            {"material": "engineering polymers / elastomers (PPS, PEEK, "
                          "EPDM) per fluid compatibility",
             "precedent": "general industrial fluid-handling practice",
             "verify_applicability": True,
             "applicability_context": "GENERAL"},
            {"material": "stainless steel / copper alloys for wetted "
                          "paths per fluid compatibility",
             "precedent": "general industrial fluid-handling practice",
             "verify_applicability": True,
             "applicability_context": "GENERAL"}],
        "manufacturing_candidates": [
            {"process": "medical extrusion (catheter body)",
             "status": "ENGINEERING_PROPOSED",
             "applicability_context": "MEDICAL"},
            {"process": "injection molding (housings, precision features)",
             "status": "ENGINEERING_PROPOSED"},
            {"process": "general extrusion / machining / welding of "
                        "fluid-handling components",
             "status": "ENGINEERING_PROPOSED",
             "applicability_context": "GENERAL"}],
        "verification_methods": [
            "bench flow-loop characterization across operating range",
            "pressure-drop mapping vs flow (identify regime transitions)",
            "accelerated occlusion / fouling challenge testing"],
        "standards_candidates": [
            {"standard": "ISO 13485 (medical QMS)",
             "verify_applicability": True,
             "applicability_context": "MEDICAL"},
            {"standard": "ISO 14971 (medical risk management)",
             "verify_applicability": True,
             "applicability_context": "MEDICAL"},
            {"standard": "ASTM F2394 (silicone elastomers for medical use)",
             "verify_applicability": True,
             "applicability_context": "MEDICAL"},
            {"standard": "ASME B31 / EN 13445 (pressure piping and "
                          "vessels, per installation jurisdiction)",
             "verify_applicability": True,
             "applicability_context": "GENERAL"}],
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
             "verify_applicability": True,
             "applicability_context": "MEDICAL"},
            {"material": "fused silica / borosilicate optical windows "
                          "and standard fiber assemblies",
             "precedent": "general optical practice",
             "verify_applicability": True,
             "applicability_context": "GENERAL"}],
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
             "verify_applicability": True,
             "applicability_context": "MEDICAL"},
            {"standard": "IEC 62471 (photobiological safety) / product "
                          "applicable optical standards (jurisdiction-"
                          "dependent)",
             "verify_applicability": True,
             "applicability_context": "GENERAL"}],
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
                    "localization", "ghz", "mhz", "interference", "emi",
                    "electromagnetic", "emc", "oversensing",
                    "pacing inhibition", "cross-coupling"],
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
             "verify_applicability": True,
             "applicability_context": "MEDICAL"},
            {"material": "standard RF laminates / dielectric substrates",
             "precedent": "general RF practice",
             "verify_applicability": True,
             "applicability_context": "GENERAL"}],
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
             "verify_applicability": True, "applicability_context": "MEDICAL"}],
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
             "verify_applicability": True, "applicability_context": "MEDICAL"}],
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
        # R443 context de-conflation (see fluidics_hydraulic note)
        "architecture_blocks_medical": [],
        "materials_candidates": [
            {"material": "biocompatible thermal spreader (graphite/AlN)",
             "precedent": "implant electronics thermal practice",
             "verify_applicability": True,
             "applicability_context": "MEDICAL"},
            {"material": "copper / aluminum alloys and graphite "
                          "thermal spreaders",
             "precedent": "general heat-transfer practice",
             "verify_applicability": True,
             "applicability_context": "GENERAL"},
            {"material": "stainless steel / titanium wetted-path "
                          "components per fluid compatibility",
             "precedent": "general industrial heat-exchanger practice",
             "verify_applicability": True,
             "applicability_context": "GENERAL"}],
        "manufacturing_candidates": [
            {"process": "bonded spreader + encapsulation",
             "status": "ENGINEERING_PROPOSED",
             "applicability_context": "MEDICAL"},
            {"process": "brazed / welded / plate-fabricated heat "
                        "exchanger core and shell",
             "status": "ENGINEERING_PROPOSED",
             "applicability_context": "GENERAL"}],
        "verification_methods": [
            "temperature-rise mapping at max duty",
            "interface resistance characterization",
            "worst-case ambient soak test"],
        "standards_candidates": [
            {"standard": "IEC 60601-1 (medical electrical equipment "
                          "safety, thermal)",
             "verify_applicability": True,
             "applicability_context": "MEDICAL"}],
    },
    "energy_harvesting": {
        "label": "Energy harvesting / power conversion",
        "signals": ["energy harvest", "piezoelectric energy", "thermoelectric",
                    "triboelectric", "induction charging", "power harvest",
                    "kinetic energy", "photovoltaic energy", "battery life",
                    "self-powered", "energy autonomy", "watt", "milliwatt",
                    "power budget"],
        "disciplines": ["energy conversion", "power electronics",
                        "materials science", "mechanical engineering"],
        "architecture_blocks": [
            "ambient source characterization element",
            "transduction stage (piezo / thermo / inductive)",
            "power conditioning and storage buffer",
            "load interface + duty-cycle governor"],
        "materials_candidates": [
            {"material": "PZT / AlN piezoelectric stack",
             "precedent": "implantable energy harvester practice",
             "verify_applicability": True, "applicability_context": "MEDICAL"},
            {"material": "BiTe thermoelectric couple",
             "precedent": "body-heat harvesting practice",
             "verify_applicability": True}],
        "manufacturing_candidates": [
            {"process": "thin-film deposition + laser dicing of transducers",
             "status": "ENGINEERING_PROPOSED"},
            {"process": "hermetic encapsulation of power electronics",
             "status": "ENGINEERING_PROPOSED"}],
        "verification_methods": [
            "transduced power vs source excitation sweep",
            "conditioning-chain conversion efficiency mapping",
            "duty-cycle endurance under worst-case load"],
        "standards_candidates": [
            {"standard": "IEC 60601-1 (electrical safety)",
             "verify_applicability": True},
            {"standard": "ISO 10993 (biocompatibility)",
             "verify_applicability": True,
             "applicability_context": "MEDICAL"},
            {"standard": "IEC 62471 (photobiological safety) / product "
                          "applicable optical standards (jurisdiction-"
                          "dependent)",
             "verify_applicability": True,
             "applicability_context": "GENERAL"}],
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


# ==========================================================================
# R445 — THE CANONICAL DOMAIN-FAMILY VOCABULARY (the one semantic namespace)
# ==========================================================================
# Prior state (the F1 defect, R444): the domain-family identity was
# declared in DIFFERENT vocabularies at different layers — the ENGINE
# routing domain ('thermal', 'fluidics_hydraulic'...), the BRIDGE family
# vocabulary ('THERMAL_SYSTEM', 'GENERIC_ARCHITECTURE'...), the gate's
# private coarse set, and the benchmark's hyphenated labels — so one
# field name meant different things at different layers and the R440
# identity gate correctly blocked every fresh package
# (A-INTERNAL-DIVERGENT: ['GENERIC_ARCHITECTURE', 'thermal']).
#
# This registry is the SINGLE authority (Art. X): the canonical family
# id is the ONE domain identity that flows unchanged through
# USER PROBLEM -> PROBLEM CONTEXT -> DOMAIN SPEC -> ENGINEERING SPEC ->
# GEOMETRY -> CIO -> DOSSIER -> PACKAGE. Every layer resolves its
# family HERE; no downstream component invents another namespace. The
# engine routing domain (DOMAIN_TEMPLATES, the E21-D phenomena/physics
# authority) and the bridge geometry archetypes (presentation routing)
# remain what they are — internal routing vocabularies — and are
# DECLARED as such by their mapping into this registry. The mapping is
# declared in ONE direction only: routing id -> canonical family.
#
# Two orthogonal axes are kept orthogonal (the R443 applicability
# precedent): the canonical family is the APPLICATION family of the
# technology (thermal / fluid / materials / biomedical / software_ml /
# ...), resolved from the PROBLEM's own text; the engine domain is the
# MECHANISM-PHYSICS routing (a catheter is biomedical as a family and
# fluidics as physics; both are recorded, neither is promoted to the
# other).
#
# Epistemic contract (Art. XXVII): family resolution is deterministic
# keyword routing with the FULL score table recorded; below the minimum
# form score the honest 'generic' family is selected and labeled —
# never a guess. 'generic' is a legitimate family id (the F1-era
# GENERIC_ARCHITECTURE / GENERIC_FALLBACK fallbacks canonicalize here),
# not an error.
# ==========================================================================

#: The canonical family ids — THE closed domain-family vocabulary.
#: Extending this set is a contract change (same discipline as
#: applicability.CONTEXT_CLASSES).
CANONICAL_DOMAIN_FAMILIES: Dict[str, Dict[str, Any]] = {
    "thermal": {
        "label": "Thermal & heat-transfer systems",
        "engine_domains": ["thermal"],
        "bridge_archetypes": ["THERMAL_SYSTEM"],
    },
    "fluid": {
        "label": "Fluid systems",
        "engine_domains": ["fluidics_hydraulic"],
        "bridge_archetypes": ["FLUID_DEVICE"],
    },
    "materials": {
        "label": "Materials & chemical systems",
        "engine_domains": [],
        "bridge_archetypes": [],
    },
    "biomedical": {
        "label": "Biomedical & life-science systems",
        "engine_domains": ["mri_nmr", "enzyme_biocatalytic",
                           "phage_microbio"],
        "bridge_archetypes": ["MEDICAL_DEVICE"],
    },
    "software_ml": {
        "label": "Software & machine-learning systems",
        "engine_domains": ["ml_data"],
        "bridge_archetypes": [],
    },
    "mechanical": {
        "label": "Mechanical & structural systems",
        "engine_domains": ["mechanical_structural"],
        "bridge_archetypes": ["VEHICLE", "MECHANICAL_COMPONENT"],
    },
    "electronic": {
        "label": "Electronic & RF systems",
        "engine_domains": ["rf_wireless"],
        "bridge_archetypes": ["ELECTRONIC_SYSTEM"],
    },
    "energy": {
        "label": "Energy harvesting & storage systems",
        "engine_domains": ["energy_harvesting"],
        "bridge_archetypes": ["ENERGY_STORAGE"],
    },
    "optical_photonic": {
        "label": "Optical & photonic systems",
        "engine_domains": ["optical_photonic"],
        "bridge_archetypes": [],
    },
    "acoustic": {
        "label": "Acoustic systems",
        "engine_domains": ["acoustic"],
        "bridge_archetypes": [],
    },
    "generic": {
        "label": "Not established (generic architecture)",
        "engine_domains": ["UNKNOWN"],
        "bridge_archetypes": ["GENERIC_ARCHITECTURE"],
    },
}

#: Application-family keyword routing (the canonicalization layer).
#: Signals absorbed from the bridge's former _FAMILY_SIGNALS (whole-form
#: discipline kept: a problem that asks for a vehicle is a mechanical
#: family problem even when subsystems mention batteries/thermal) plus
#: the families the bridge never had (materials, software_ml,
#: optical_photonic, acoustic). Weights follow the bridge precedent;
#: the full score table is always returned with the decision (Art.
#: XXVII — no magic thresholds).
_CANONICAL_FAMILY_SIGNALS: List[Tuple[str, List[Tuple[str, int]]]] = [
    ("biomedical", [
        ("catheter", 6), ("shunt", 5), ("stent", 5), ("lumen", 4),
        ("medical device", 5), ("implant", 4), ("implantable", 5),
        ("intravascular", 4), ("surgical", 3), ("venous", 3),
        ("patient", 1), ("clinical", 1), ("biocompatibility", 6),
        ("in vivo", 6), ("in-vivo", 6), ("biosensor", 5),
        ("bioreactor", 5), ("enzyme therapy", 5), ("assay", 4),
        ("diagnostic test", 4), ("ventricular", 4), ("hydrocephalus", 6),
        ("neurosurgery", 6), ("sterilization", 4),
    ]),
    ("thermal", [
        ("heat sink", 4), ("heat exchanger", 5), ("heat transfer", 5),
        ("thermal management", 4), ("thermal runaway", 5),
        ("cooling", 4), ("heating", 3), ("thermal", 3), ("heat", 2),
        ("radiator", 3), ("cold plate", 4), ("condenser", 4),
        ("evaporator", 4), ("hvac", 4), ("refrigeration", 4),
        ("boiler", 4), ("district heating", 5),
    ]),
    ("fluid", [
        ("pump", 6), ("valve", 5), ("microfluidic", 6), ("nozzle", 4),
        ("chamber", 3), ("channel", 2), ("flow sensor", 5),
        ("fluid", 2), ("flow control", 4), ("diaphragm", 3),
        ("impeller", 4), ("metering", 3), ("turbo", 4),
        ("compressor", 4), ("filtration", 4),
        ("desalination", 5), ("reverse osmosis", 5), ("permeate flux", 4),
        # NOTE: 'pipe'/'pipeline' deliberately EXCLUDED — polysemous
        # with software data pipelines and thermal heat pipes (Art. XXI:
        # substring noise is not relevance)
    ]),
    ("materials", [
        ("corrosion", 5), ("coating", 5), ("alloy", 5), ("composite", 4),
        ("polymer", 4), ("metallurg", 5), ("electrode", 4),
        ("electrolyte", 4), ("cathode", 4), ("anode", 4),
        ("delamination", 5), ("material degradation", 5),
        ("fatigue crack", 4), ("wear rate", 4), ("film", 2),
        ("substrate", 3), ("sintering", 5), ("curing", 4),
        ("adhesive", 4), ("surface treatment", 4),
    ]),
    ("software_ml", [
        ("machine learning", 6), ("neural network", 5), ("deep learning", 5),
        ("classifier", 4), ("recommender", 5), ("reinforcement learning", 6),
        ("inference", 4), ("training data", 4), ("model drift", 5),
        ("dataset", 3), ("software architecture", 4), ("latency budget", 3),
        ("model serving", 4), ("forecasting model", 5), ("reward hacking", 5),
        ("policy training", 4), ("microservice", 4), ("software system", 4),
    ]),
    ("mechanical", [
        ("electric vehicle", 6), ("solar vehicle", 6), ("solar car", 6),
        ("vehicle", 5), ("automotive", 5), ("car", 3), ("truck", 4),
        ("bus", 4), ("chassis", 2), ("drivetrain", 2), ("wheel", 2),
        ("traction", 2), ("road", 1), ("bearing", 5), ("shaft", 4),
        ("spring", 4), ("fastener", 4), ("gear", 4), ("rail", 4),
        ("joint", 2), ("structural", 2), ("load path", 3), ("damper", 3),
        ("suspension", 3), ("fatigue", 1), ("fracture", 1),
        ("rotor imbalance", 4), ("centrifuge", 5), ("vibration", 3),
    ]),
    ("electronic", [
        ("circuit", 4), ("electronics", 4), ("board", 3), ("pcba", 5),
        ("inverter", 4), ("converter", 3), ("power electronics", 5),
        ("module electronics", 2), ("controller", 2), ("antenna", 3),
        ("sensor node", 3), ("battery management", 2), ("pcb", 4),
        ("rf front end", 4), ("transceiver", 4), ("semiconductor", 3),
    ]),
    ("energy", [
        ("battery pack", 5), ("battery module", 5), ("battery cell", 4),
        ("cell", 2), ("battery", 3), ("energy storage", 4),
        ("supercapacitor", 5), ("pack", 2), ("photovoltaic", 5),
        ("solar panel", 5), ("solar farm", 5), ("wind turbine", 5),
        ("energy harvesting", 6), ("fuel cell", 5), ("grid-scale", 4),
        ("lithium", 4), ("state of charge", 4),
    ]),
    ("optical_photonic", [
        ("lens", 4), ("optical", 4), ("photonics", 5), ("laser", 5),
        ("waveguide", 5), ("fiber optic", 5), ("optical fiber", 5),
        ("spectrometer", 5), ("lithography", 4), ("photodetector", 5),
        ("display pixel", 4), ("imaging optics", 5), ("lidar", 5),
    ]),
    ("acoustic", [
        ("acoustic", 5), ("ultrasound", 5), ("sonar", 5),
        ("transducer", 4), ("noise cancellation", 5), ("speaker", 4),
        ("microphone array", 5), ("piezo", 4), ("audio", 3),
        ("underwater sound", 5), ("acoustic emission", 5),
    ]),
]

#: whole-form device identity (the bridge whole-form precedent: a
#: problem that asks for a vehicle builds a vehicle even when its
#: subsystems mention batteries). When the problem's own device/site
#: statement declares an implantable or medical-device form, the
#: application family is biomedical — component mentions (batteries,
#: photovoltaics, telemetry, flow sensing) never turn an implant into
#: an energy/optical/fluid product. Device-identity terms only; the
#: DEPLOYMENT words (hospital, clinical, patient...) are deliberately
#: NOT here (a hospital dashboard stays software_ml; hospital HVAC
#: stays thermal — where a device is USED is not what it IS).
_BIOMEDICAL_FORM_SIGNALS: List[str] = [
    "implant", "implantable", "implanted", "catheter", "shunt", "stent",
    "intravascular", "prosthesis", "prosthetic", "biosensor",
    "bioreactor", "neurostimulator", "pacemaker", "defibrillator",
    "dialysis", "dialyzer", "endoscope", "ventilator", "biopsy",
    "medical device", "mr-conditional", "ventriculostomy", " cannula",
    "surgical instrument", "diagnostic assay", "point-of-care test",
]

#: the honest floor — a whole-family form needs real signal, not one
#: weak keyword (same rule and provenance as the bridge's former
#: min_form_score = 3; Art. XXVII).
MIN_CANONICAL_FAMILY_SCORE = 3

#: reverse routing maps (declared ONCE, derived from the registry —
#: never hand-maintained duplicates).
_ENGINE_DOMAIN_TO_FAMILY: Dict[str, str] = {}
_BRIDGE_ARCHETYPE_TO_FAMILY: Dict[str, str] = {}
for _fam, _spec in CANONICAL_DOMAIN_FAMILIES.items():
    for _d in _spec["engine_domains"]:
        _ENGINE_DOMAIN_TO_FAMILY[_d] = _fam
    for _a in _spec["bridge_archetypes"]:
        _BRIDGE_ARCHETYPE_TO_FAMILY[_a] = _fam
#: bridge-internal representation labels (never canonical families;
#: they canonicalize to the resolved family or 'generic' — see
#: canonical_family_of_bridge_archetype).
_BRIDGE_REPRESENTATION_LABELS = {
    "PROCESS_FLOW", "GENERIC_FALLBACK", "ENGINEERING_PARAMETRIC",
}


def is_canonical_family(value: Any) -> bool:
    """True iff value is exactly a canonical family id."""
    return isinstance(value, str) and value in CANONICAL_DOMAIN_FAMILIES


def canonical_family_of_engine_domain(domain_id: Any) -> str:
    """Engine physics-routing domain -> canonical family (UNKNOWN ->
    'generic'; an unmapped id is NOT silently coerced to another
    family — it resolves to 'generic' honestly)."""
    return _ENGINE_DOMAIN_TO_FAMILY.get(str(domain_id or ""), "generic")


def canonical_family_of_bridge_archetype(archetype: Any) -> str:
    """Bridge geometry archetype -> canonical family. The bridge's
    representation labels (PROCESS_FLOW / GENERIC_FALLBACK /
    ENGINEERING_PARAMETRIC) are NOT families — they canonicalize to
    'generic' (their run carries the resolved family separately)."""
    a = str(archetype or "")
    if a in _BRIDGE_REPRESENTATION_LABELS:
        return "generic"
    return _BRIDGE_ARCHETYPE_TO_FAMILY.get(a, "generic")


def canonical_family_label(family_id: Any) -> str:
    return CANONICAL_DOMAIN_FAMILIES.get(
        str(family_id or ""), CANONICAL_DOMAIN_FAMILIES["generic"])["label"]


def canonical_family_archetypes(family_id: Any) -> List[str]:
    """The bridge geometry archetypes routed by a canonical family."""
    return list(CANONICAL_DOMAIN_FAMILIES.get(
        str(family_id or "generic"), {})["bridge_archetypes"])


def resolve_canonical_family(problem_text: str,
                             intervention_site: str = "",
                             subsystems: Sequence[Any] = (),
                             ) -> Dict[str, Any]:
    """R445: resolve the ONE canonical domain family from the problem's
    own text (application-family axis).

    Deterministic keyword routing with the FULL score table recorded
    (Art. XXVII): every keyword hit (family, keyword, weight, count)
    is returned so the choice is auditable from the artifact alone.
    Whole-form signals outrank component signals (the bridge
    precedent). Ties resolve by the fixed registry order; below the
    minimum form score the honest 'generic' family is selected and
    labeled as such (Art. XXV: unknown stays unknown).
    """
    text = " ".join([
        str(problem_text or ""),
        str(intervention_site or ""),
        " ".join(str(s) for s in (subsystems or [])),
    ]).lower()
    form_text = f"{str(problem_text or '')} {str(intervention_site or '')}".lower()
    # Layer 1 — whole-form device identity: an implantable/medical
    # device form dominates component mentions (recorded, never silent)
    form_hits = [s.strip() for s in _BIOMEDICAL_FORM_SIGNALS
                 if s.strip() in form_text]
    scores: List[Dict[str, Any]] = []
    best_family, best_score = "generic", 0
    for family, signals in _CANONICAL_FAMILY_SIGNALS:
        total = 0
        hits: List[Dict[str, Any]] = []
        for keyword, weight in signals:
            kw = keyword.lower()
            if len(kw) >= 5 or " " in kw:
                count = text.count(kw)
            else:
                count = len(re.findall(rf"\b{re.escape(kw)}\b", text))
            if count:
                total += weight * count
                hits.append({"keyword": keyword, "weight": weight,
                             "count": count})
        scores.append({"family": family, "score": total, "hits": hits})
        if total > best_score:
            best_family, best_score = family, total
    if best_score < MIN_CANONICAL_FAMILY_SCORE:
        best_family = "generic"
    if form_hits:
        return {
            "canonical_family": "biomedical",
            "label": canonical_family_label("biomedical"),
            "score": best_score,
            "min_form_score": MIN_CANONICAL_FAMILY_SCORE,
            "score_table": scores,
            "whole_form_basis": {
                "matched_form_signals": form_hits,
                "rule": ("whole-form device identity: the problem's own "
                         "device/site statement declares an implantable "
                         "or medical-device form — the application family "
                         "is biomedical and dominates component-mention "
                         "keyword scores (the bridge whole-form "
                         "precedent; deployment words are deliberately "
                         "excluded: a hospital dashboard stays "
                         "software_ml)"),
                "keyword_runner_up": best_family,
            },
            "basis": {
                "derived_from": ["problem text", "intervention site",
                                 "recorded subsystem names"],
                "rule": "whole-form device identity layer, then highest "
                        "keyword score; ties resolve by registry order; "
                        "below the form threshold the generic family is "
                        "selected and labeled",
                "authority": ("discovery_fabric/engine/domains.py::"
                              "CANONICAL_DOMAIN_FAMILIES (R445 — the one "
                              "canonical domain-family vocabulary)"),
                "deterministic": True,
            },
        }
    return {
        "canonical_family": best_family,
        "label": canonical_family_label(best_family),
        "score": best_score,
        "min_form_score": MIN_CANONICAL_FAMILY_SCORE,
        "score_table": scores,
        "basis": {
            "derived_from": ["problem text", "intervention site",
                             "recorded subsystem names"],
            "rule": "highest keyword score wins; ties resolve by "
                    "registry order; below the form threshold the "
                    "generic family is selected and labeled",
            "authority": ("discovery_fabric/engine/domains.py::"
                          "CANONICAL_DOMAIN_FAMILIES (R445 — the one "
                          "canonical domain-family vocabulary)"),
            "deterministic": True,
        },
    }


def resolve_run_canonical_family(run_result: Any,
                                 eng: Any = None) -> Dict[str, Any]:
    """R445: the canonical family for a RECORDED run state — the ONE
    consumer ladder every downstream layer uses (the bridge domain
    spec, the bridge representation fallbacks, the package compiler):

        1. engineering_specification.why_this_domain.canonical_family
           (the fresh upstream decision — consumed, never re-derived)
        2. engineering_specification.applicability.canonical_domain.
           canonical_family (the alternate upstream shape)
        3. registry resolution over the run's own recorded problem
           words (user_text / problem fields / device / title)
        4. the engine-domain registry mapping (the E21-D physics
           decision — the most upstream domain decision a legacy state
           carries; physics axis mapped through the SAME registry)
        5. the honest 'generic' family

    Cross-layer agreement is BY CONSTRUCTION: every consumer calls this
    one function with the same inputs (the run record + the resolved
    engineering specification — run-dir persisted files are the
    authority per resolve_final_state, Art. X), so no layer can
    re-derive a different family in a different vocabulary (the F1
    defect class).
    """
    rr = run_result if isinstance(run_result, dict) else {}
    eng = eng if isinstance(eng, dict) else {}
    wd = eng.get("why_this_domain") if isinstance(
        eng.get("why_this_domain"), dict) else {}
    cf = wd.get("canonical_family")
    if isinstance(cf, str) and is_canonical_family(cf):
        return {
            "canonical_family": cf,
            "label": wd.get("canonical_family_label")
            or canonical_family_label(cf),
            "basis": {
                "source": ("engineering_specification.why_this_domain."
                           "canonical_family (the upstream R445 "
                           "authority — consumed, never re-derived)"),
                "ladder_step": 1,
                "upstream_record": True,
            },
        }
    ap = eng.get("applicability") if isinstance(
        eng.get("applicability"), dict) else {}
    cd = ap.get("canonical_domain") if isinstance(
        ap.get("canonical_domain"), dict) else {}
    cf2 = cd.get("canonical_family")
    if isinstance(cf2, str) and is_canonical_family(cf2):
        return {
            "canonical_family": cf2,
            "label": cd.get("canonical_family_label")
            or canonical_family_label(cf2),
            "basis": {
                "source": ("engineering_specification.applicability."
                           "canonical_domain.canonical_family (alternate "
                           "upstream shape — consumed, never re-derived)"),
                "ladder_step": 2,
                "upstream_record": True,
            },
        }
    # step 3: the run's own recorded problem words (the application
    # axis's proper source)
    problem = rr.get("problem") if isinstance(rr.get("problem"), dict) \
        else {}
    text = " ".join(str(x or "") for x in (
        rr.get("user_text"), problem.get("text"), problem.get("device"),
        problem.get("failure"), problem.get("constraint"),
        problem.get("failure_mode"), rr.get("device"), rr.get("title")))
    res = resolve_canonical_family(text)
    if res["canonical_family"] != "generic":
        res = dict(res)
        res["basis"] = dict(res["basis"])
        res["basis"]["ladder_step"] = 3
        res["basis"]["source"] = ("registry resolution over the run's "
                                  "own recorded problem words (no "
                                  "upstream canonical field — legacy "
                                  "state)")
        return res
    # step 4: the engine-domain registry mapping (legacy physics axis)
    domain = wd.get("domain") or eng.get("technology_domain") \
        or rr.get("domain")
    if domain and str(domain) not in ("UNKNOWN", "NOT ESTABLISHED", ""):
        fam = canonical_family_of_engine_domain(domain)
        return {
            "canonical_family": fam,
            "label": canonical_family_label(fam),
            "basis": {
                "source": (f"registry mapping of the recorded engine "
                           f"domain {str(domain)!r} (the E21-D physics "
                           "decision — legacy state, mapped through the "
                           "same registry)"),
                "ladder_step": 4,
            },
        }
    # step 5: the honest generic family
    generic = resolve_canonical_family("")
    generic = dict(generic)
    generic["basis"] = dict(generic["basis"])
    generic["basis"]["ladder_step"] = 5
    generic["basis"]["source"] = ("no upstream canonical field, no "
                                  "problem-word signal, no engine "
                                  "domain — the honest generic family")
    return generic


# --------------------------------------------------------------------------
def _signal_hit(text_padded: str, signal: str) -> bool:
    """Exact-substring match for multiword/long signals; WORD-BOUNDARY
    match for short tokens (length < 5) so an acronym like 'sar' or 'rf'
    cannot match inside an unrelated word (Art. XXI: relevance must be
    independently established, and substring noise is not relevance)."""
    if len(signal) >= 5 or " " in signal:
        return signal in text_padded
    return re.search(rf"\b{re.escape(signal)}\b", text_padded) is not None


def detect_domain(text: str) -> Dict[str, Any]:
    """Score keyword signals across templates; return the detected domain with
    its matched signals (recorded for audit, MODEL_DERIVED). Ties are broken
    by (hit count, template declaration order). No hits -> generic template
    with domain UNKNOWN — recorded honestly, not guessed."""
    import re as _re_mod
    t = f" {text.lower()} "
    scores: List[Tuple[str, int, List[str]]] = []
    for domain_id, tpl in DOMAIN_TEMPLATES.items():
        hits = [s for s in tpl["signals"] if _signal_hit(t, s)]
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


# --------------------------------------------------------------------------
# CEO Directive 4 — per-domain ENGINEERING MODULE depth. These are the
# domain-generic reasoning contents that let a newly discovered invention
# reach the structural depth of the 15 frozen dossiers automatically.
# EPISTEMIC CONTRACT: every item emitted from these tables is
# ENGINEERING_PROPOSED (a domain-generic candidate requiring design work and
# verification) unless a caller explicitly traces it to custodied evidence.
# Parameter VALUES are UNKNOWN — the registry proposes WHICH parameters
# matter, never WHAT their values are (Art. XXVII: no threshold invention).
# --------------------------------------------------------------------------
DOMAIN_MODULES: Dict[str, Dict[str, Any]] = {
    "fluidics_hydraulic": {
        "governing_models": [
            {"model": "Poiseuille pressure-flow relation for laminar lumen "
                      "flow", "equation_ids": ["EQ-FLUIDICS-POISEUILLE"],
             "applicability": "newtonian, incompressible, laminar",
             "model_assumptions": [
                 "fluid is newtonian at operating temperature",
                 "flow stays laminar across the operating envelope",
                 "lumen cross-section stays circular and rigid",
                 "flow is fully developed (entrance effects negligible)"]},
            {"model": "orifice/restriction pressure drop",
             "equation_ids": ["EQ-FLUIDICS-ORIFICE"],
             "applicability": "discrete constrictions",
             "model_assumptions": [
                 "restriction is sharp-edged and its length is small vs "
                 "diameter",
                 "discharge coefficient treated as MODEL_DERIVED until "
                 "measured on the actual geometry"]},
            {"model": "Reynolds regime screening",
             "equation_ids": ["EQ-FLUIDICS-REYNOLDS"],
             "applicability": "single-phase circular-section flow",
             "model_assumptions": [
                 "single-phase flow (no gas emboli)",
                 "transition criterion Re~2300 is an engineering rule of "
                 "thumb, not a device-specific measurement"]}],
        "critical_parameters": [
            "lumen inner diameter", "lumen length", "surface roughness",
            "operating pressure head", "flow rate range",
            "viscosity of flowed medium", "occlusion growth tolerance"],
        "candidate_failure_modes": [
            {"mode": "proximal occlusion by tissue ingrowth",
             "physical_mechanism": "cells proliferate across the lumen "
                 "inlet; the growing tissue mass reduces the free flow "
                 "area, so delivered flow falls as roughly the square of "
                 "the open diameter fraction at constant pressure head",
             "trigger": "chronic tissue contact with the inlet surface; "
                 "inflammatory response to material or edge geometry",
             "detectability": "delivered-flow trend below baseline in a "
                         "flow-loop or animal model; pressure-head rise at "
                          "constant flow",
             "severity_basis": "flow loss is progressive and can reach "
                 "complete obstruction silently",
             "design_control_direction": "inlet geometry and surface finish; "
                 "anti-ingrowth surface architecture",
             "applicability_signals": ["occlusion", "ingrowth", "lumen",
                                       "inlet", "patency", "flow"]},
            {"mode": "lumen collapse under external pressure (kink)",
             "physical_mechanism": "external pressure or bending moment "
                 "exceeds the lumen's collapse resistance; the thin-wall "
                 "section buckles, the cross-section ovalling shuts the "
                 "bore and flow stops discontinuously",
             "trigger": "device bending, external compression, or suction "
                 "beyond the wall's critical pressure",
             "detectability": "kink/collapse test across duty cycle; "
                          "flow-stoppage signature under applied load",
             "severity_basis": "loss of function is sudden and complete",
             "design_control_direction": "wall thickness and reinforcement; "
                 "minimum bend radius; support architecture",
             "applicability_signals": ["kink", "collapse", "bend", "catheter",
                                       "lumen", "compression", "flex"]},
            {"mode": "encrustation / mineral deposition",
             "physical_mechanism": "mineral species precipitate on the lumen "
                 "wall where local chemistry or flow stagnation favors "
                 "nucleation; deposits roughen the wall and progressively "
                 "narrow the effective diameter",
             "trigger": "supersaturated solutes in the flowed medium; "
                 "stagnation zones; pH or temperature shifts at the wall",
             "detectability": "long-duration patency soak with particulate/"
                          "mineral challenge; pressure-flow drift",
             "severity_basis": "calibration drifts and occlusion risk grow "
                 "with implant time",
             "design_control_direction": "surface energy/coating selection; "
                 "eliminate stagnation zones in flow-path geometry",
             "applicability_signals": ["encrustation", "deposition",
                                       "fouling", "patency", "drainage",
                                       "flow"]},
            {"mode": "regime transition to turbulence altering calibration",
             "physical_mechanism": "above the laminar-transition point the "
                 "pressure-flow relation departs from the laminar model, so "
                 "a flow element calibrated in one regime misestimates in "
                 "the other",
             "trigger": "operating point pushed past critical Reynolds by "
                 "pressure, viscosity or geometry changes",
             "detectability": "pressure-flow mapping across the full "
                          "envelope showing regime-break curvature",
             "severity_basis": "quantification errors propagate to dosing/"
                 "pressure decisions",
             "design_control_direction": "operating-envelope definition; "
                 "regime-margin verification in the flow loop",
             "applicability_signals": ["turbulence", "reynolds", "regime",
                                       "calibration", "flow rate", "laminar"]},
            {"mode": "check-valve seat wear opening reverse leakage",
             "physical_mechanism": "repeated seating cycles erode the seat "
                 "face; the closing line degrades and a leak path opens, "
                 "so backflow occurs at each pressure reversal",
             "trigger": "cyclic pressure reversals; particulate wear; "
                 "material creep at the seat",
             "detectability": "reverse-leakage rate measurement after "
                          "accelerated cycling",
             "severity_basis": "backflow defeats the pressure regulation "
                 "function the invention depends on",
             "design_control_direction": "seat material and geometry; "
                 "cycle-life margin; filtration of particulates",
             "applicability_signals": ["valve", "check valve", "leakage",
                                       "backflow", "seat", "regurgit"]}],
        "design_input_patterns": [
            "required flow window at available pressure head",
            "medium viscosity and particulate load",
            "anatomic connection geometry",
            "device-lifetime duty profile"],
        "design_output_patterns": [
            "flow-path geometry (diameter/length schedule)",
            "pressure-regulation element definition",
            "anti-occlusion surface architecture",
            "termination connectors and seals"],
        "verification_methods_extra": [
            "pressure-flow mapping across full operating envelope",
            "long-duration patency bench soak with particulate challenge"],
        "validation_methods": [
            "animal-model patency study at device lifetime",
            "multi-site clinical performance evaluation"],
        "manufacturing_patterns": [
            "medical extrusion with inner-diameter tolerance control",
            "injection molding of valve/housing features",
            "laser drilling of calibrated orifices"],
    },
    "optical_photonic": {
        "governing_models": [
            {"model": "Beer-Lambert attenuation through medium",
             "equation_ids": ["EQ-OPTICS-BEERLAMBERT"],
             "applicability": "homogeneous medium, effective coefficient",
             "model_assumptions": [
                 "tissue treated as homogeneous with a MODEL_DERIVED "
                 "effective attenuation coefficient",
                 "scattering folded into the effective coefficient — "
                 "invalid for precise dosimetry without measurement"]},
            {"model": "photovoltaic conversion at receiver",
             "equation_ids": ["EQ-OPTICS-PV-CONVERSION"],
             "applicability": "below saturation, at operating wavelength",
             "model_assumptions": [
                 "converter efficiency quoted at solar spectrum does not "
                 "transfer to monochromatic operation — must be re-measured",
                 "cell temperature stays within the quoted-efficiency "
                 "envelope"]},
            {"model": "fluence and thermal load at target",
             "equation_ids": ["EQ-OPTICS-FLUENCE", "EQ-OPTICS-THERMAL"],
             "applicability": "continuous-wave or long-pulse exposure",
             "model_assumptions": [
                 "thermal load computed for steady state; pulsed operation "
                 "needs a transient model before quantitative use"]}],
        "critical_parameters": [
            "source wavelength", "emitted optical power",
            "fiber/transport numerical aperture",
            "receiver active area", "conversion efficiency",
            "target-path absorption coefficient", "interface temperature rise"],
        "candidate_failure_modes": [
            {"mode": "misalignment loss at couplings",
             "physical_mechanism": "lateral or angular offset between source, "
                 "fiber and receiver reduces the coupled power per the "
                 "overlap integral; delivered energy falls below the "
                 "receiver's operating threshold",
             "trigger": "mechanical shift from handling, thermal cycling or "
                 "implant micromotion",
             "detectability": "coupled-power monitoring vs alignment sweep "
                          "in phantom; tolerance characterization",
             "severity_basis": "power delivery degrades below functional "
                 "threshold without total failure",
             "design_control_direction": "kinematic coupling tolerance; "
                 "alignment-insensitive optics; capture margin",
             "applicability_signals": ["alignment", "coupling", "fiber",
                                       "coupler", "optical", "power"]},
            {"mode": "fiber bend radiative loss beyond limit",
             "physical_mechanism": "bending below the critical radius makes "
                 "the guided mode radiate; guided power leaks through the "
                 "cladding before reaching the receiver",
             "trigger": "routing through a tight curve; device packaging or "
                 "implant motion forcing radius below specification",
             "detectability": "bend-loss curve vs radius; output power drop "
                          "at packaged geometry",
             "severity_basis": "delivered energy collapses with route "
                 "changes that are hard to control in use",
             "design_control_direction": "minimum bend-radius routing rule; "
                 "bend-insensitive fiber selection; strain relief",
             "applicability_signals": ["fiber", "bend", "loss", "optical",
                                       "routing", "cable"]},
            {"mode": "photovoltaic conversion degradation with temperature",
             "physical_mechanism": "converter output voltage falls roughly "
                 "linearly with rising cell temperature, so delivered "
                 "electrical power drops exactly when thermal load is "
                 "highest",
             "trigger": "sustained high delivered optical power; poor "
                 "thermal path at the receiver",
             "detectability": "conversion efficiency vs temperature sweep; "
                          "thermal-rise mapping at max duty",
             "severity_basis": "negative power/temperature feedback can "
                 "spiral into functional loss",
             "design_control_direction": "thermal spreading path at "
                 "receiver; derating and interlock thresholds",
             "applicability_signals": ["photovoltaic", "conversion", "thermal",
                                       "temperature", "efficiency", "cell"]},
            {"mode": "thermal damage at tissue interface",
             "physical_mechanism": "absorbed optical power that misses the "
                 "converter heats the surrounding tissue; local temperature "
                 "crosses the injury threshold at the interface",
             "trigger": "misalignment plus high emitted power; failed "
                 "thermal path; exposure beyond sourced safety limits",
             "detectability": "interface temperature-rise measurement vs "
                          "sourced safety ceilings in phantom and animal",
             "severity_basis": "patient injury — the highest-consequence "
                 "class for this domain",
             "design_control_direction": "interlock and shutter concept; "
                 "exposure ceilings from sourced limits; thermal spreader",
             "applicability_signals": ["thermal", "tissue", "safety",
                                       "damage", "interface", "fluence",
                                       "exposure"]},
            {"mode": "window fouling reducing delivered fluence",
             "physical_mechanism": "biofilm or protein layer deposits on the "
                 "optical window; the fouling layer scatters and absorbs "
                 "before light enters the transport path",
             "trigger": "chronic implantation in bioactive fluid; surface "
                 "energy favoring protein adsorption",
             "detectability": "transmitted-power trend through fouled "
                          "windows in chronic soaks",
             "severity_basis": "gradual power budget erosion over device "
                 "life",
             "design_control_direction": "anti-fouling window coating; "
                 "power margin sized to fouling budget",
             "applicability_signals": ["fouling", "window", "biofilm",
                                       "fluence", "coating", "implant"]}],
        "design_input_patterns": [
            "required delivered energy/fluence at target",
            "transport-path geometry and access constraint",
            "receiver electrical load profile",
            "safety exposure limits (to be sourced)"],
        "design_output_patterns": [
            "source/receiver selection and derating",
            "optical window and coupling architecture",
            "thermal spreading path definition",
            "interlock and shutter concept"],
        "verification_methods_extra": [
            "tissue-phantom fluence mapping at target depth",
            "alignment-tolerance characterization"],
        "validation_methods": [
            "chronic implant optical-path performance study",
            "end-use thermal safety evaluation under max duty"],
        "manufacturing_patterns": [
            "die/wire bonding of converter on carrier",
            "hermetic optical-window encapsulation",
            "precision fiber termination and polishing"],
    },
    "rf_wireless": {
        "governing_models": [
            {"model": "link budget with path loss and margins",
             "equation_ids": ["EQ-RF-LINKBUDGET"],
             "applicability": "far-field link; in-body path adds loss terms",
             "model_assumptions": [
                 "free-space path loss underestimates in-body loss — an "
                 "additional tissue-loss margin is MODEL_DERIVED until "
                 "phantom-measured",
                 "polarization and orientation statistics accounted as "
                 "margin, not as measured distribution"]},
            {"model": "free-space / in-body path loss",
             "equation_ids": ["EQ-RF-PATHLOSS"],
             "applicability": "frequency-dependent tissue penetration",
             "model_assumptions": [
                 "tissue dielectric parameters are frequency- and "
                 "patient-dependent; values must be sourced per band"]},
            {"model": "SNR and BER at receiver",
             "equation_ids": ["EQ-RF-SNR"],
             "applicability": "defined detection bandwidth and modulation",
             "model_assumptions": [
                 "noise figure and interference budgeted explicitly; "
                 "clinic RF environment adds time-varying interference"]},
            {"model": "SAR exposure constraint",
             "equation_ids": ["EQ-RF-SAR"],
             "applicability": "transmit operation near tissue",
             "model_assumptions": [
                 "exposure ceiling must come from a sourced regulatory "
                 "limit; simulated SAR requires measurement confirmation"]}],
        "critical_parameters": [
            "carrier frequency", "transmit power (regulatory-bounded)",
            "antenna gain and pattern", "path length and depth",
            "receiver noise figure", "required BER at data rate",
            "SAR at tissue interface"],
        "candidate_failure_modes": [
            {"mode": "link margin collapse at maximum depth/orientation",
             "physical_mechanism": "at the worst-case combination of depth, "
                 "antenna orientation and tissue loading the received "
                 "power falls below the sensitivity floor and the link "
                 "drops",
             "trigger": "implant orientation change; maximum implant depth; "
                 "patient tissue-variance at percentiles not measured",
             "detectability": "BER-vs-distance/depth curves in "
                          "tissue-equivalent phantom across orientations",
             "severity_basis": "total telemetry loss at exactly the use "
                 "conditions the device exists for",
             "design_control_direction": "antenna geometry and pattern; "
                 "link-margin budget with measured tissue loss",
             "applicability_signals": ["link", "margin", "depth", "telemetry",
                                       "range", "orientation", "antenna"]},
            {"mode": "SAR exceedance at transmit power needed for link",
             "physical_mechanism": "the transmit power required to close "
                 "the link deposits local power density in tissue above "
                 "the sourced exposure ceiling",
             "trigger": "link-margin shortfall solved by raising power; "
                 "antenna detuning concentrating near-fields",
             "detectability": "SAR simulation plus phantom measurement "
                          "against the sourced regulatory limit",
             "severity_basis": "regulatory non-compliance plus patient "
                 "safety exposure",
             "design_control_direction": "transmit power schedule and duty "
                 "cycle; exposure-compliant antenna and enclosure design",
             "applicability_signals": ["sar", "exposure", "safety", "power",
                                       "transmit", "regulatory"]},
            {"mode": "detuning from dielectric loading of nearby tissue",
             "physical_mechanism": "high-permittivity tissue couples into "
                 "the antenna's near field, shifting its resonant frequency "
                 "and pattern so that radiated power drops at the carrier",
             "trigger": "implantation environment differs from bench "
                 "characterization; tissue-property variance across "
                 "patients",
             "detectability": "resonance-frequency and efficiency "
                          "measurement in tissue-equivalent media",
             "severity_basis": "design-to-use mismatch silently erases "
                 "the calibrated link budget",
             "design_control_direction": "loading-tolerant antenna "
                 "topology; characterization across dielectric range",
             "applicability_signals": ["detuning", "antenna", "resonance",
                                       "tissue", "dielectric", "implant"]},
            {"mode": "interference in clinic RF environment",
             "physical_mechanism": "external transmitters inject in-band "
                 "energy, raising the noise floor so the demodulated "
                 "error rate exceeds the decision threshold",
             "trigger": "co-located electrosurgery, telemetry, or "
                 "institutional RF emitters",
             "detectability": "BER performance under injected "
                          "interference scenarios; spectrum survey",
             "severity_basis": "telemetry integrity loss in exactly the "
                 "deployed environment",
             "design_control_direction": "channel selection, filtering, "
                 "error coding; interference-inclusive noise budget",
             "applicability_signals": ["interference", "rf", "noise",
                                       "band", "clinic", "coexist"]},
            {"mode": "antenna feed joint fatigue failure",
             "physical_mechanism": "cyclic micromotion stresses the feed "
                 "solder/weld joint; crack initiation propagates until the "
                 "feed opens and the antenna becomes an open circuit",
             "trigger": "lead micro-motion at the feed point over device "
                 "life; assembly residual stress",
             "detectability": "accelerated fatigue run-out of feed "
                          "assemblies; post-cycle network analysis",
             "severity_basis": "mechanical failure ends all communication "
                 "and cannot be serviced in situ",
             "design_control_direction": "strain relief at feed; fatigue-"
                 "rated joint design and verification",
             "applicability_signals": ["feed", "joint", "fatigue",
                                       "antenna", "lead", "reliability"]}],
        "design_input_patterns": [
            "required data rate and latency",
            "implant depth and body geometry",
            "regulatory exposure ceiling (to be sourced)",
            "battery/power budget for transmit duty"],
        "design_output_patterns": [
            "antenna geometry and feed architecture",
            "transmit power schedule and duty cycle",
            "receiver sensitivity budget",
            "exposure-compliance enclosure concept"],
        "verification_methods_extra": [
            "tissue-equivalent phantom link characterization",
            "SAR simulation and measurement against sourced limit"],
        "validation_methods": [
            "end-to-end telemetry reliability study in animal model",
            "worst-case exposure compliance demonstration"],
        "manufacturing_patterns": [
            "high-density PCB with chip-scale RF front end",
            "implant-grade antenna integration and feed sealing"],
    },
    "acoustic": {
        "governing_models": [
            {"model": "acoustic impedance contrast reflection",
             "equation_ids": ["EQ-ACOUSTIC-IMPEDANCE"],
             "applicability": "normal incidence, plane wave, lossless media",
             "model_assumptions": [
                 "oblique incidence and attenuation modify detectability — "
                 "normal-incidence reflection is an idealization",
                 "target and medium impedances must be sourced, not "
                 "assumed"]},
            {"model": "piezoelectric transduction resonance",
             "equation_ids": ["EQ-ACOUSTIC-RESONANCE"],
             "applicability": "thickness-mode resonance of the active layer",
             "model_assumptions": [
                 "resonance frequency shifts with temperature and bonding — "
                 "shift must be characterized, not assumed negligible"]}],
        "critical_parameters": [
            "operating frequency", "element aperture", "matching layer Z",
            "excitation voltage and duty", "detection threshold",
            "coupling-path attenuation"],
        "candidate_failure_modes": [
            {"mode": "detection threshold missed at depth (attenuation)",
             "physical_mechanism": "two-way attenuation through the medium "
                 "scales exponentially with depth; the echoed contrast "
                 "falls below the detector's noise floor before "
                 "discrimination",
             "trigger": "target deeper than characterized range; "
                 "attenuating medium variance; low excitation duty",
             "detectability": "phantom detection-threshold mapping vs "
                          "depth and medium composition",
             "severity_basis": "missed detection defeats the sensing "
                 "purpose exactly at required operating depth",
             "design_control_direction": "aperture and frequency selection; "
                 "excitation budget; detection-threshold logic with margin",
             "applicability_signals": ["detection", "depth", "attenuation",
                                       "threshold", "echo", "contrast"]},
            {"mode": "crosstalk between elements corrupting detection",
             "physical_mechanism": "acoustic and electrical energy leaks "
                 "between adjacent elements; the leaked signal appears in "
                 "the wrong channel and corrupts the detection criterion",
             "trigger": "element pitch too small; array operation without "
                 "isolation; high excitation voltage",
             "detectability": "channel-isolation characterization; "
                          "crosstalk matrix measurement",
             "severity_basis": "spatial false positives corrupt the "
                 "measurement the device exists to make",
             "design_control_direction": "element isolation (kerf/dicing); "
                 "electrical decoupling; detection logic robustness",
             "applicability_signals": ["crosstalk", "array", "element",
                                       "isolation", "channel"]},
            {"mode": "resonance drift with temperature",
             "physical_mechanism": "the piezoelectric coupling and sound "
                 "speed shift with temperature, moving the resonance peak; "
                 "a fixed-tuned excitation loses transfer efficiency",
             "trigger": "body-temperature range; self-heating at duty; "
                 "sterilization exposure",
             "detectability": "resonance tracking across the temperature "
                          "envelope",
             "severity_basis": "sensitivity loss across exactly the "
                 "in-use temperature range",
             "design_control_direction": "matching-layer temperature "
                 "compensation; wide-band design; warm-up characterization",
             "applicability_signals": ["resonance", "temperature", "drift",
                                       "piezoelectric", "tuning"]},
            {"mode": "bond-wire fatigue under cyclic excitation",
             "physical_mechanism": "each excitation cycle strains the bond "
                 "wires through element expansion; thermal-mechanical "
                 "fatigue initiates cracks that eventually open the "
                 "connection",
             "trigger": "high duty cycle; high excitation voltage; element "
                 "geometry concentrating strain",
             "detectability": "accelerated cyclic-excitation run-out with "
                          "impedance monitoring",
             "severity_basis": "element loss is permanent and silent "
                 "until detection degrades",
             "design_control_direction": "bond geometry and redundancy; "
                 "duty-cycle limits; fatigue verification",
             "applicability_signals": ["bond", "fatigue", "cyclic",
                                       "excitation", "duty", "duty cycle"]},
            {"mode": "coupling loss at interface deairing failure",
             "physical_mechanism": "an air gap at the acoustic interface "
                 "reflects nearly all incident energy (impedance mismatch "
                 "to air), so almost nothing reaches the medium",
             "trigger": "incomplete coupling; interface motion; gas "
                 "evolution at the interface",
             "detectability": "transmitted-energy check with deliberate "
                 "deairing challenge; interface inspection protocol",
             "severity_basis": "near-total signal loss from a trivially "
                 "preventable interface state",
             "design_control_direction": "coupling geometry and materials; "
                 "integrated deairing/detector of interface quality",
             "applicability_signals": ["coupling", "air", "interface",
                                       "gel", "deair", "contact"]}],
        "design_input_patterns": [
            "target contrast and depth",
            "allowed excitation energy (safety ceiling to be sourced)",
            "detection latency requirement"],
        "design_output_patterns": [
            "transducer stack definition",
            "excitation/receive electronics concept",
            "detection-criterion and threshold logic",
            "coupling interface geometry"],
        "verification_methods_extra": [
            "phantom detection-threshold mapping vs depth",
            "cyclic-excitation durability run-out"],
        "validation_methods": [
            "in-vivo detectability demonstration",
            "clinical use detection performance evaluation"],
        "manufacturing_patterns": [
            "diced-ceramic + backing assembly",
            "matching-layer lamination and bonding"],
    },
    "mri_nmr": {
        "governing_models": [
            {"model": "Larmor precession and resonance condition",
             "equation_ids": ["EQ-MRI-LARMOR"],
             "applicability": "single species, weak-field linear regime",
             "model_assumptions": [
                 "gyromagnetic ratio is species-fixed (H-1 constant is "
                 "sourced, not invented)",
                 "field value at the sample, not the nominal scanner "
                 "field, governs the resonance"]},
            {"model": "induction signal (Faraday pickup)",
             "equation_ids": ["EQ-MRI-INDUCTION"],
             "applicability": "conducting sample inside a receive coil",
             "model_assumptions": [
                 "signal scales with coil sensitivity at the sample — "
                 "sensitivity profile must be characterized",
                 "quasi-static approximation valid at Larmor frequencies"]}],
        "critical_parameters": [
            "B0 field strength", "coil sensitivity profile",
            "acquisition bandwidth", "sample conductivity",
            "SAR from RF exposure", "gradient amplitude"],
        "candidate_failure_modes": [
            {"mode": "RF heating at conductive interfaces",
             "physical_mechanism": "the transmit field induces currents in "
                 "conductors; at tips and high-impedance junctions the "
                 "current density concentrates and local deposition heats "
                 "tissue",
             "trigger": "conductive element length near resonant fraction; "
                 "high flip-angle sequences; contact geometry",
             "detectability": "MR-safety heating protocol in phantom at "
                          "worst-case sequences",
             "severity_basis": "patient burn — a hard safety failure with "
                 "regulatory consequence",
             "design_control_direction": "conductor length management; "
                 "MR-conditional materials and marking; sequence limits",
             "applicability_signals": ["heating", "rf", "conductive",
                                       "safety", "mri", "burn", "tip"]},
            {"mode": "torque/attraction on ferromagnetic component",
             "physical_mechanism": "the static field gradient exerts force "
                 "and torque on any ferromagnetic mass; the component "
                 "migrates or rotates against tissue",
             "trigger": "ferromagnetic material inclusion; unlabeled "
                 "component substitution in manufacturing",
             "detectability": "ASTM torque/attraction test in scanner",
             "severity_basis": "catastrophic patient injury scenario; "
                 "absolute design-out requirement",
             "design_control_direction": "non-ferromagnetic bill of "
                 "materials with lot-level verification",
             "applicability_signals": ["ferromagnetic", "torque",
                                       "attraction", "mri", "magnet",
                                       "safety"]},
            {"mode": "image artifact corrupting quantification",
             "physical_mechanism": "susceptibility jumps and metal-induced "
                 "field distortion bias the local phase and magnitude, so "
                 "the derived measurement deviates systematically from "
                 "truth",
             "trigger": "device material susceptibility mismatch; sequence "
                 "parameters sensitive to B0 inhomogeneity",
             "detectability": "accuracy vs reference in controlled "
                          "phantoms across sequences",
             "severity_basis": "the measurement is wrong while appearing "
                 "plausible — silent corrupt output",
             "design_control_direction": "low-susceptibility materials; "
                 "sequence and reconstruction co-design",
             "applicability_signals": ["artifact", "susceptibility",
                                       "quantification", "accuracy",
                                       "phase", "distortion"]},
            {"mode": "SNR insufficient at required resolution",
             "physical_mechanism": "signal scales with voxel volume and "
                 "coil sensitivity; shrinking voxels for resolution "
                 "starves SNR below the detection requirement",
             "trigger": "resolution targets raised; small sensitive "
                 "volume; noise-limited receive chain",
             "detectability": "SNR-vs-resolution characterization in "
                          "scanner at required geometry",
             "severity_basis": "specification miss at the primary "
                 "performance metric",
             "design_control_direction": "coil geometry and coupling; "
                 "acquisition time and averaging budget",
             "applicability_signals": ["snr", "resolution", "sensitivity",
                                       "coil", "noise"]},
            {"mode": "gradient-induced vibration fatigue",
             "physical_mechanism": "Lorentz forces from switched gradients "
                 "shake conductive members acoustically; millions of "
                 "cycles drive fatigue at clamped interfaces",
             "trigger": "high-duty gradient sequences; rigid clamps at "
                 "stress concentrators",
             "detectability": "vibration endurance scan protocol; "
                          "post-scan integrity inspection",
             "severity_basis": "mechanical loosening or particle "
                 "generation over clinical use",
             "design_control_direction": "fatigue-rated fixation design; "
                 "resonance-avoiding mounting",
             "applicability_signals": ["gradient", "vibration", "fatigue",
                                       "lorentz", "acoustic noise"]}],
        "design_input_patterns": [
            "target measurement quantity and accuracy",
            "scanner environment constraints (field, bore)",
            "MR-safety marking requirement"],
        "design_output_patterns": [
            "MR-conditional material selection",
            "coil/encoding geometry",
            "reconstruction/estimation pipeline definition"],
        "verification_methods_extra": [
            "scanner SNR characterization at required resolution",
            "MR-safety torque/heating protocol"],
        "validation_methods": [
            "accuracy vs reference MRI in phantom then animal",
            "multi-scanner reproducibility evaluation"],
        "manufacturing_patterns": [
            "precision micro-coil winding",
            "non-ferromagnetic assembly and MR-conditional marking"],
    },
    "enzyme_biocatalytic": {
        "governing_models": [
            {"model": "Michaelis-Menten kinetics with mass transport",
             "equation_ids": ["EQ-ENZYME-MM"],
             "applicability": "steady state, single substrate, stable enzyme",
             "model_assumptions": [
                 "immobilization shifts Km/Vmax — parameters must be "
                 "re-measured on the actual surface",
                 "bulk substrate concentration equals surface "
                 "concentration only below the mass-transfer limit",
                 "enzyme activity stays within the stability window"]}],
        "critical_parameters": [
            "immobilized activity density", "substrate contact time",
            "mass-transfer coefficient", "operating temperature",
            "pH window", "leaching rate"],
        "candidate_failure_modes": [
            {"mode": "activity decay below functional floor",
             "physical_mechanism": "protein denaturation and active-site "
                 "degradation reduce immobilized activity over time; rate "
                 "output falls below the conversion the use case needs",
             "trigger": "operating temperature/pH outside stability "
                 "window; proteases in the medium; long storage",
             "detectability": "residual-activity vs time assay in the "
                          "target fluid",
             "severity_basis": "function decays silently over device life",
             "design_control_direction": "stabilization chemistry; "
                 "operating-window definition with sourced stability data",
             "applicability_signals": ["activity", "decay", "stability",
                                       "enzyme", "denatur", "half-life"]},
            {"mode": "mass-transfer limitation starving active sites",
             "physical_mechanism": "when consumption outpaces diffusive/"
                 "convective supply, the surface substrate concentration "
                 "collapses; observed rate reflects transport, not "
                 "kinetics, and efficiency drops",
             "trigger": "high activity density with low flow; boundary "
                 "layer thickening; channel geometry starving flow",
             "detectability": "rate vs flow sweep showing transport "
                          "plateau; mass-transfer coefficient measurement",
             "severity_basis": "design calibrated on kinetics fails at "
                 "operating flow",
             "design_control_direction": "contact-time geometry (bed/"
                 "channel); flow-path design against transport limit",
             "applicability_signals": ["mass transfer", "diffusion",
                                       "transport", "flow", "contact time"]},
            {"mode": "enzyme leaching into flow stream",
             "physical_mechanism": "weakly bound enzyme molecules detach "
                 "and wash out; activity density falls while released "
                 "protein appears downstream",
             "trigger": "immobilization chemistry instability; pH/ionic "
                 "shifts; shear at the surface",
             "detectability": "downstream protein/immunogenicity assays; "
                          "activity retention over run time",
             "severity_basis": "both efficacy loss and a safety exposure "
                 "(released protein)",
             "design_control_direction": "covalent immobilization "
                 "chemistry; containment barrier; leaching verification",
             "applicability_signals": ["leaching", "immobiliz", "wash out",
                                       "release", "coupling"]},
            {"mode": "immunogenic byproduct generation",
             "physical_mechanism": "degradation products or detached "
                 "conjugates enter the circulation and elicit an immune "
                 "response",
             "trigger": "proteolytic cleavage of immobilized species; "
                 "contaminants from coupling chemistry",
             "detectability": "immunogenicity and byproduct identity "
                          "assays across device life",
             "severity_basis": "patient immune response — safety "
                 "regulatory blocker class",
             "design_control_direction": "byproduct characterization; "
                 "purge/capture stage; material qualification",
             "applicability_signals": ["immunogenic", "byproduct",
                                       "immune", "proteolytic", "safety"]},
            {"mode": "substrate competition reducing selectivity",
             "physical_mechanism": "in a real medium, competing substrates "
                 "occupy active sites; the target conversion rate falls "
                 "and side products form",
             "trigger": "medium composition differs from single-substrate "
                 "characterization",
             "detectability": "selectivity assay in representative medium "
                          "vs simplified buffer",
             "severity_basis": "performance gap between characterization "
                 "and deployed medium",
             "design_control_direction": "selectivity verification in "
                 "realistic medium; site-density tuning",
             "applicability_signals": ["competition", "selectivity",
                                       "substrate", "medium", "side product"]}],
        "design_input_patterns": [
            "target substrate conversion per pass",
            "flow medium composition and temperature",
            "device-lifetime activity requirement"],
        "design_output_patterns": [
            "immobilization chemistry and surface architecture",
            "contact-time geometry (bed/channel)",
            "containment/leaching barrier concept"],
        "verification_methods_extra": [
            "residual-activity vs time assay in target fluid",
            "mass-transfer-limited rate characterization"],
        "validation_methods": [
            "chronic exposure biocompatibility and leaching study",
            "end-use efficacy demonstration in intended medium"],
        "manufacturing_patterns": [
            "GMP surface functionalization and enzyme coupling",
            "aseptic final assembly and packaging"],
    },
    "phage_microbio": {
        "governing_models": [
            {"model": "phage-host population dynamics (kill kinetics)",
             "equation_ids": [], "note": "no registry equation yet; source "
             "before quantitative use",
             "model_assumptions": [
                 "kill kinetics measured in planktonic culture do not "
                 "transfer to surface-immobilized systems without "
                 "re-measurement"]},
            {"model": "biofilm mass-balance with predation",
             "equation_ids": [], "note": "no registry equation yet; source "
             "before quantitative use",
             "model_assumptions": [
                 "biofilm growth rate and penetration depth are "
                 "strain- and surface-specific and must be measured"]}],
        "critical_parameters": [
            "surface phage loading density", "infectivity retention half-life",
            "host range breadth", "moi at contact surface",
            "CFU challenge load", "resistance emergence rate"],
        "candidate_failure_modes": [
            {"mode": "infectivity loss before clinical use window",
             "physical_mechanism": "desiccation, temperature and surface "
                 "chemistry denature phage particles; titer falls below "
                 "the protective loading density",
             "trigger": "storage and supply-chain duration; sterilization "
                 "exposure; hostile surface microenvironment",
             "detectability": "infectivity retention vs time on the "
                          "processed surface under storage and use profiles",
             "severity_basis": "protection expires before the clinical "
                 "use window closes",
             "design_control_direction": "stabilization/lyophilization; "
                 "loading over-engineering sized to retention half-life",
             "applicability_signals": ["infectivity", "stability", "titer",
                                       "storage", "half-life", "viability"]},
            {"mode": "resistant strain emergence negating kill",
             "physical_mechanism": "bacteria mutate or acquire resistance "
                 "to the phage receptors used; the kill mechanism loses "
                 "its target population",
             "trigger": "single-phage dependence; sub-protective dosing "
                 "selecting for survivors",
             "detectability": "serial-passage resistance emergence assay; "
                          "cocktail coverage testing",
             "severity_basis": "mechanism defeat is adaptive and "
                 "progressive under use",
             "design_control_direction": "multi-phage cocktail with "
                 "distinct receptors; dosing above resistance-selection "
                 "threshold",
             "applicability_signals": ["resistance", "mutation", "escape",
                                       "cocktail", "host range"]},
            {"mode": "host-range mismatch to clinical isolate",
             "physical_mechanism": "the phage's receptor recognition fails "
                 "on strains whose surface chemistry differs from the "
                 "laboratory target; no attachment, no kill",
             "trigger": "clinical isolate diversity vs characterized "
                 "panel; geographic/strain variation",
             "detectability": "multi-isolate clinical panel efficacy "
                          "study before any efficacy claim",
             "severity_basis": "efficacy absent on the actual pathogen "
                 "population",
             "design_control_direction": "host-range breadth "
                 "specification; isolate-panel verification gate",
             "applicability_signals": ["host range", "isolate", "strain",
                                       "spectrum", "coverage"]},
            {"mode": "coating wear releasing loaded phage",
             "physical_mechanism": "mechanical wear of the coating matrix "
                 "liberates immobilized phage particles; loading drops "
                 "while particles shed downstream",
             "trigger": "abrasion at the device surface; flow shear; "
                 "handling during deployment",
             "detectability": "wear-challenge particle-shed assay plus "
                          "post-wear loading measurement",
             "severity_basis": "dose loss and uncontrolled biological "
                 "release both occur",
             "design_control_direction": "wear-resistant immobilization "
                 "matrix; mechanical verification of retention",
             "applicability_signals": ["coating", "wear", "release",
                                       "shed", "immobiliz", "abrasion"]},
            {"mode": "biofilm matrix blocking phage access",
             "physical_mechanism": "mature biofilm extracellular matrix "
                 "bars phage penetration; kill occurs only at the surface "
                 "layer while protected cells persist beneath",
             "trigger": "established biofilm at deployment; matrix-"
                 "producing strains",
             "detectability": "CFU challenge assay against established "
                          "biofilm, not only planktonic culture",
             "severity_basis": "efficacy overclaimed by planktonic-only "
                 "characterization",
             "design_control_direction": "matrix-degrading co-agent; "
                 "prevention-vs-treatment claim boundary",
             "applicability_signals": ["biofilm", "matrix", "penetration",
                                       "cfu", "established"]}],
        "design_input_patterns": [
            "target organism and biofilm mode of growth",
            "device surface and exposure environment",
            "stability requirement through supply chain"],
        "design_output_patterns": [
            "immobilization/release coating architecture",
            "phage cocktail selection rationale",
            "stability preservation approach"],
        "verification_methods_extra": [
            "CFU biofilm-prevention challenge assay",
            "infectivity retention vs time on processed surface"],
        "validation_methods": [
            "animal infection-prevention model",
            "multi-isolate clinical panel efficacy study"],
        "manufacturing_patterns": [
            "electrospinning + immobilization dip under aseptic control",
            "lyophilization/storage stabilization"],
    },
    "ml_data": {
        "governing_models": [
            {"model": "Bayesian decision rule with calibration",
             "equation_ids": [], "note": "no registry equation yet; source "
             "before quantitative use",
             "model_assumptions": [
                 "posterior probabilities are calibrated on the "
                 "deployment distribution, not merely on the test split",
                 "utility weights are BUYER_DEFINED/MODEL_DERIVED and "
                 "never presented as measured"]},
            {"model": "expected information gain for data collection",
             "equation_ids": [], "note": "engine-native; see experiment "
             "selector",
             "model_assumptions": [
                 "prior predictive distributions reflect reality closely "
                 "enough to rank data-collection actions"]}],
        "critical_parameters": [
            "training data volume and provenance",
            "label quality rate", "target operating point (precision/recall)",
            "calibration error budget", "inference latency ceiling",
            "distribution-shift monitoring thresholds"],
        "candidate_failure_modes": [
            {"mode": "distribution shift degrading accuracy post deployment",
             "physical_mechanism": "the deployment input distribution "
                 "departs from the training distribution; learned "
                 "decision boundaries stop corresponding to reality and "
                 "error rates rise",
             "trigger": "site, population, hardware or protocol changes "
                 "after training; temporal drift",
             "detectability": "input-distribution monitoring with "
                          "pre-registered shift alarms; silent-trial "
                          "error tracking",
             "severity_basis": "performance is validated in one world "
                 "and used in another",
             "design_control_direction": "monitoring and retraining "
                 "trigger definition; shift stress testing pre-deployment",
             "applicability_signals": ["distribution shift", "drift",
                                       "deployment", "monitor", "domain"]},
            {"mode": "label noise propagating to biased predictions",
             "physical_mechanism": "systematic mislabeling teaches the "
                 "model the wrong input-output mapping; the bias "
                 "concentrates exactly on the confounded sub-population",
             "trigger": "weak label provenance; annotator disagreement; "
                 "proxy-label construction",
             "detectability": "label-quality audit against adjudicated "
                          "gold subset; disagreement analysis",
             "severity_basis": "errors are systematic, not random — "
                 "worst case for decision support",
             "design_control_direction": "label provenance requirements; "
                 "gold-subset verification; noise-robust training",
             "applicability_signals": ["label", "noise", "annotation",
                                       "bias", "provenance"]},
            {"mode": "overfitting to source-site artifacts",
             "physical_mechanism": "the model keys on acquisition "
                 "fingerprints (device signatures, protocols) instead of "
                 "the intended signal; site-swap evaluation collapses",
             "trigger": "single-site data; strong acquisition fingerprints; "
                 "insufficient augmentation",
             "detectability": "leave-one-site-out evaluation; "
                          "fingerprint-removal ablation",
             "severity_basis": "apparent performance that cannot "
                 "transfer",
             "design_control_direction": "multi-site training data; "
                 "transfer evaluation gate before any performance claim",
             "applicability_signals": ["overfit", "site", "generaliz",
                                       "transfer", "fingerpr", "augment"]},
            {"mode": "calibration drift invalidating decision thresholds",
             "physical_mechanism": "score-to-probability mapping drifts "
                 "with input change; a threshold that meant a specific "
                 "risk level now means something else while remaining "
                 "numerically unchanged",
             "trigger": "post-deployment input drift; recalibration "
                 "absent; pipeline version changes",
             "detectability": "calibration error monitoring with "
                          "reliability diagrams on live data",
             "severity_basis": "decision thresholds silently lose their "
                 "meaning",
             "design_control_direction": "calibration error budget; "
                 "recalibration procedure; threshold governance",
             "applicability_signals": ["calibration", "threshold",
                                       "probability", "drift", "score"]},
            {"mode": "feedback-loop data contamination",
             "physical_mechanism": "model outputs influence future "
                 "training labels (automation bias, exclusion of "
                 "disconfirmed cases); the training set stops being "
                 "independent evidence of reality",
             "trigger": "closed-loop deployment without external "
                 "adjudication; model-in-the-loop labeling",
             "detectability": "data-lineage audit separating "
                 "model-seen vs independently-labeled records",
             "severity_basis": "the system manufactures its own "
                 "confirming evidence — an epistemic failure",
             "design_control_direction": "external adjudication sampling; "
                 "data-lineage custody requirements",
             "applicability_signals": ["feedback", "contamination", "loop",
                                       "automation bias", "lineage"]}],
        "design_input_patterns": [
            "decision the predictor must support",
            "available labeled/unlabeled data inventory",
            "latency and compute envelope"],
        "design_output_patterns": [
            "feature/representation architecture",
            "model family + uncertainty quantification",
            "monitoring and retraining trigger definition"],
        "verification_methods_extra": [
            "held-out + temporal split evaluation",
            "stress test under injected distribution shift"],
        "validation_methods": [
            "prospective silent-trial evaluation on live data",
            "multi-site external validation"],
        "manufacturing_patterns": [
            "MLOps CI for data and model",
            "versioned artifact registry with rollback"],
    },
    "mechanical_structural": {
        "governing_models": [
            {"model": "Euler column buckling of slender members",
             "equation_ids": ["EQ-MECH-BUCKLING"],
             "applicability": "elastic, slender column, small deflection",
             "model_assumptions": [
                 "effective-length factor K for constrained catheter-like "
                 "conditions is MODEL_DERIVED until measured",
                 "material stays elastic — no post-yield redistribution"]},
            {"model": "fatigue life under cyclic load (S-N)",
             "equation_ids": ["EQ-MECH-FATIGUE"],
             "applicability": "constant-amplitude cycling below yield",
             "model_assumptions": [
                 "S-N curve must come from the actual material and finish; "
                 "variable-amplitude service needs a damage model",
                 "run-out definition is an engineering convention to be "
                 "pre-registered, not a measured limit"]}],
        "critical_parameters": [
            "member slenderness ratio", "yield/ultimate strength",
            "applied cyclic load amplitude", "required run-out cycles",
            "articulation radius", "friction coefficient at guides"],
        "candidate_failure_modes": [
            {"mode": "kink/buckling below required push ability",
             "physical_mechanism": "axial compression on the slender member "
                 "reaches the critical buckling load; the member bows "
                 "sideways, kinks at the weakest section and transmits no "
                 "further push force",
             "trigger": "delivery path curvature plus push force; wall "
                 "thin-down; guide slack",
             "detectability": "buckling/kink margin test across the duty "
                          "cycle and path geometry",
             "severity_basis": "loss of deliverability exactly in the "
                 "anatomy the device targets",
             "design_control_direction": "cross-section schedule; "
                 "slenderness and support spacing; material selection",
             "applicability_signals": ["kink", "buckling", "push", "column",
                                       "slender", "delivery"]},
            {"mode": "fatigue crack initiation at stress concentrator",
             "physical_mechanism": "cyclic stress at notches, laser-cut "
                 "edges or crimp zones exceeds the fatigue endurance "
                 "limit; micro-cracks initiate and propagate to fracture",
             "trigger": "cyclic load amplitude over device life; surface "
                 "defects; residual stress from manufacturing",
             "detectability": "fatigue run-out at worst-case loading plus "
                          "fractographic inspection",
             "severity_basis": "fracture releases debris and loses "
                 "function irrecoverably",
             "design_control_direction": "concentrator-free geometry; "
                 "surface finish control; proof and run-out testing",
             "applicability_signals": ["fatigue", "crack", "cyclic",
                                       "concentrator", "notch", "life"]},
            {"mode": "wear debris generation at sliding interfaces",
             "physical_mechanism": "repeated relative motion at guides "
                 "abrades surfaces; debris particles shed into the "
                 "device and environment while clearances grow",
             "trigger": "sliding contact under load; rough surfaces; "
                 "long duty life",
             "detectability": "friction/wear characterization with debris "
                          "collection and count",
             "severity_basis": "progressive looseness plus particulate "
                 "safety concern",
             "design_control_direction": "material pairing and coatings; "
                 "contact-pressure reduction; wear-life verification",
             "applicability_signals": ["wear", "debris", "friction",
                                       "sliding", "guide", "abrasion"]},
            {"mode": "joint separation under overload",
             "physical_mechanism": "load at a joined interface exceeds the "
                 "retention mechanism's capacity; the joint disengages "
                 "and the load path is lost",
             "trigger": "operator force exceeding specification; "
                 "retention feature undersized; creep relaxation",
             "detectability": "overload margin demonstration to "
                          "worst-case force with safety factor",
             "severity_basis": "instantaneous loss of control over the "
                 "delivered component",
             "design_control_direction": "retention margin sizing; "
                 "overload-tested joint design",
             "applicability_signals": ["joint", "separation", "overload",
                                       "retention", "detach", "coupling"]},
            {"mode": "set-release of superelastic shape after set",
             "physical_mechanism": "the superelastic member stored in a "
                 "deformed configuration relaxes toward a new equilibrium "
                 "(time-dependent set); delivered geometry drifts from "
                 "the shape the design assumed",
             "trigger": "sustained storage strain; elevated temperature; "
                 "cycling beyond the stable plateau",
             "detectability": "shape-retention measurement over storage "
                          "and duty profiles",
             "severity_basis": "deployed geometry silently differs from "
                 "design intent",
             "design_control_direction": "shape-set process control; "
                 "storage-strain limits; geometry verification at use",
             "applicability_signals": ["superelastic", "nitinol", "set",
                                       "shape", "relaxation", "drift"]}],
        "design_input_patterns": [
            "delivery-path geometry and curvature",
            "actuation force available at user interface",
            "duty cycle and load history"],
        "design_output_patterns": [
            "structural backbone cross-section schedule",
            "compliance/actuation element definition",
            "fatigue-critical feature register"],
        "verification_methods_extra": [
            "buckling/kink margin test across duty cycle",
            "fatigue run-out at worst-case loading"],
        "validation_methods": [
            "simulated-use full-lifetime functional study",
            "worst-case overload margin demonstration"],
        "manufacturing_patterns": [
            "laser-cut hypotube / braided composite shaft",
            "passivation and surface finish control"],
    },
    "thermal": {
        "governing_models": [
            {"model": "conduction network and interface resistance",
             "equation_ids": ["EQ-THERMAL-CONDUCTION"],
             "applicability": "steady state, isotropic conduction",
             "model_assumptions": [
                 "interface resistances dominate at small scales and must "
                 "be measured, not assumed zero",
                 "transient operation needs a thermal-capacitance model "
                 "before quantitative claims"]}],
        "critical_parameters": [
            "heat generation at source", "spreader conductivity",
            "interface contact resistance", "reject-path area",
            "allowable temperature rise", "ambient worst case"],
        "candidate_failure_modes": [
            {"mode": "hotspot exceeding material/safety limit",
             "physical_mechanism": "local heat generation outpaces lateral "
                 "spreading; temperature at the hotspot climbs past the "
                 "material or tissue limit while averages stay fine",
             "trigger": "power density concentration; spreader "
                 "discontinuity; degraded interface",
             "detectability": "temperature-rise mapping at maximum duty "
                          "with IR or embedded sensing",
             "severity_basis": "local damage or safety breach hidden by "
                 "healthy averages",
             "design_control_direction": "spreader geometry; heat-source "
                 "spreading; interlock at sourced ceilings",
             "applicability_signals": ["hotspot", "temperature", "thermal",
                                       "limit", "safety", "power density"]},
            {"mode": "interface delamination raising resistance over life",
             "physical_mechanism": "cyclic expansion mismatch opens gaps at "
                 "bonded interfaces; contact resistance grows with age so "
                 "the same power produces rising temperatures",
             "trigger": "thermal cycling; poor wetting; outgassing; "
                 "mechanical shock",
             "detectability": "thermal-resistance trend over accelerated "
                          "cycling",
             "severity_basis": "margin erodes silently over device life",
             "design_control_direction": "TIM selection and cure control; "
                 "cycle-life verification with resistance tracking",
             "applicability_signals": ["delamin", "interface", "resistance",
                                       "bond", "cycle", "tim"]},
            {"mode": "coolant/flow path blockage (if active)",
             "physical_mechanism": "particulate or bubble obstructs the "
                 "active cooling channel; convective term vanishes and "
                 "temperatures jump to conduction-only levels",
             "trigger": "contamination; gas evolution; kinked tube; pump "
                 "failure",
             "detectability": "flow-rate sensing with pre-registered "
                          "alarm; blockage challenge test",
             "severity_basis": "step-change loss of the primary cooling "
                 "mechanism",
             "design_control_direction": "filtration; flow interlock; "
                 "fail-safe conduction backup path",
             "applicability_signals": ["coolant", "blockage", "flow",
                                       "pump", "active cooling", "occlus"]},
            {"mode": "thermal runaway coupling to electronics",
             "physical_mechanism": "rising temperature raises leakage or "
                 "losses, which raise temperature further; the feedback "
                 "runs away until failure of the electronic element",
             "trigger": "marginally-cooled power components; ambient "
                 "extremes; derating absent",
             "detectability": "worst-case ambient soak with staged power "
                          "steps and stability monitoring",
             "severity_basis": "self-accelerating failure mode",
             "design_control_direction": "derating policy; thermal "
                 "margin analysis; cutoff interlocks",
             "applicability_signals": ["runaway", "electronics", "leakage",
                                       "feedback", "derating"]},
            {"mode": "condensation at cold surfaces",
             "physical_mechanism": "surfaces below the local dew point "
                 "collect condensate; moisture bridges conductors and "
                 "corrodes interfaces",
             "trigger": "cold-path operation in humid environment; "
                 "transient cool-down",
             "detectability": "dew-point-margin analysis plus humidity "
                          "chamber soak",
             "severity_basis": "electrical leakage and corrosion emerge "
                 "after field exposure",
             "design_control_direction": "dew-point margin in operating "
                 "envelope; conformal protection; drainage design",
             "applicability_signals": ["condensation", "humidity", "dew",
                                       "cold", "moisture"]}],
        "design_input_patterns": [
            "dissipation budget by subsystem",
            "ambient and coupling boundary conditions",
            "safety temperature ceilings (to be sourced)"],
        "design_output_patterns": [
            "conduction path and spreader geometry",
            "reject interface definition",
            "safety interlock and cutoff concept"],
        "verification_methods_extra": [
            "temperature-rise mapping at maximum duty",
            "worst-case ambient soak"],
        "validation_methods": [
            "long-duration thermal endurance study",
            "safety compliance thermal evaluation"],
        "manufacturing_patterns": [
            "bonded spreader + encapsulation",
            "thermal interface material application control"],
    },
    "energy_harvesting": {
        "governing_models": [
            {"model": "piezoelectric transduction constitutive relations",
             "equation_ids": [], "note": "no registry equation yet; source "
             "before quantitative use",
             "model_assumptions": [
                 "coupling coefficients are frequency-, load- and "
                 "temperature-dependent; quoted values are not design "
                 "values until measured in situ"]},
            {"model": "thermoelectric Seebeck conversion",
             "equation_ids": [], "note": "no registry equation yet; source "
             "before quantitative use",
             "model_assumptions": [
                 "output scales with the maintained temperature difference "
                 "across the couple — not with ambient temperature alone"]}],
        "critical_parameters": [
            "ambient source magnitude and spectrum",
            "transduction coefficient", "conditioning efficiency",
            "storage capacity and leakage", "load duty profile",
            "startup threshold power"],
        "candidate_failure_modes": [
            {"mode": "harvested power below startup threshold",
             "physical_mechanism": "at the actual ambient excitation the "
                 "transduced power never exceeds the conditioning chain's "
                 "startup requirement; the system stays dormant",
             "trigger": "weaker-than-assumed ambient source; "
                 "conditioning overhead underestimated",
             "detectability": "power vs excitation sweep with startup "
                          "threshold overlaid at realistic excitation",
             "severity_basis": "the value proposition fails entirely at "
                 "realistic excitation",
             "design_control_direction": "source characterization at use "
                 "site; conditioning-chain overhead reduction; startup "
                 "circuit design",
             "applicability_signals": ["startup", "threshold", "harvest",
                                       "power", "excitation", "ambient"]},
            {"mode": "transducer depoling/aging loss",
             "physical_mechanism": "field, temperature and mechanical "
                 "stress progressively depole or degrade the active "
                 "material; coupling coefficient falls over life",
             "trigger": "operating point beyond safe field/temperature; "
                 "shock exposure; time",
             "detectability": "coupling trend over accelerated aging with "
                          "intermittent output measurement",
             "severity_basis": "output decays below load needs over "
                 "device life",
             "design_control_direction": "operating-limit derating; "
                 "aging-margin in sizing; shock isolation",
             "applicability_signals": ["depol", "aging", "piezo",
                                       "coupling", "degrad"]},
            {"mode": "storage leakage draining buffer between events",
             "physical_mechanism": "buffer self-discharge and quiescent "
                 "draw exceed harvested energy between source events; "
                 "stored charge trends to empty despite harvesting",
             "trigger": "long inter-event intervals; leaky storage "
                 "chemistry; high quiescent electronics",
             "detectability": "energy-balance measurement over the "
                          "worst-case inter-event profile",
             "severity_basis": "autonomy claim fails at the duty cycle "
                 "the use case implies",
             "design_control_direction": "storage chemistry selection; "
                 "quiescent-power budget; duty-cycle governor",
             "applicability_signals": ["leakage", "storage", "buffer",
                                       "self-discharge", "quiescent",
                                       "autonomy"]},
            {"mode": "load transient collapsing supply rail",
             "physical_mechanism": "a load current step exceeds the "
                 "conditioning chain's transient capability; the supply "
                 "rail dips below reset threshold and the system "
                 "brownouts",
             "trigger": "radio or actuator activation; capacitor ESR; "
                 "cold-temperature derating",
             "detectability": "rail-ripple measurement under worst-case "
                          "load steps at temperature extremes",
             "severity_basis": "intermittent resets corrupt function "
                 "unpredictably",
             "design_control_direction": "storage sizing for transients; "
                 "soft-start and load scheduling",
             "applicability_signals": ["transient", "rail", "brownout",
                                       "reset", "load step", "esr"]},
            {"mode": "encapsulation stress cracking transducer",
             "physical_mechanism": "encapsulation cure shrinkage and "
                 "thermal mismatch load the brittle active element; "
                 "microcracks disconnect sections and cut output",
             "trigger": "encapsulant modulus mismatch; thermal cycling; "
                 "over-molded geometry",
             "detectability": "acoustic micro-imaging plus output check "
                          "after cure and cycling",
             "severity_basis": "manufacturing-latent failure appears as "
                 "field output loss",
             "design_control_direction": "compliant encapsulation "
                 "materials; cure-profile control; post-cure screening",
             "applicability_signals": ["encapsulat", "crack", "stress",
                                       "cure", "mold", "brittle"]}],
        "design_input_patterns": [
            "available ambient energy at use site",
            "load power and duty requirements",
            "recharge/maintenance constraints"],
        "design_output_patterns": [
            "transducer selection and sizing",
            "power-conditioning chain definition",
            "storage buffer and governor concept"],
        "verification_methods_extra": [
            "power vs excitation sweep characterization",
            "end-to-end conversion efficiency mapping"],
        "validation_methods": [
            "worst-case ambient endurance run",
            "integrated system power autonomy demonstration"],
        "manufacturing_patterns": [
            "thin-film transducer deposition and dicing",
            "hermetic electronics encapsulation"],
    },
}

MODULE_REQUIRED_KEYS = ("governing_models", "critical_parameters",
                        "candidate_failure_modes", "design_input_patterns",
                        "design_output_patterns", "verification_methods_extra",
                        "validation_methods", "manufacturing_patterns")

# CEO A4/A6: every domain module additionally carries invention-reasoning
# fields; get_domain_module guarantees them for every domain (UNKNOWN
# included, honestly empty).
MODULE_REASONING_KEYS = ("why_this_domain_basis", "model_applicability",
                         "model_assumptions", "failure_mode_detail",
                         "manufacturing_routes")


def _structured_failure_modes(mod: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normalize candidate failure modes to the A6 physical-detail shape.
    Legacy string entries (if any) are wrapped honestly as candidates whose
    physical mechanism is NOT ESTABLISHED — never silently promoted."""
    out: List[Dict[str, Any]] = []
    for f in mod.get("candidate_failure_modes", []):
        if isinstance(f, dict):
            out.append({
                "mode": f.get("mode", "UNKNOWN"),
                "physical_mechanism": f.get("physical_mechanism",
                                            "NOT ESTABLISHED"),
                "trigger": f.get("trigger", "NOT ESTABLISHED"),
                "detectability": f.get("detectability", "NOT ESTABLISHED"),
                "severity_basis": f.get("severity_basis",
                                        "NOT ESTABLISHED"),
                "design_control_direction": f.get(
                    "design_control_direction", "NOT ESTABLISHED"),
                "applicability_signals": list(
                    f.get("applicability_signals", [])),
            })
        else:
            out.append({
                "mode": str(f),
                "physical_mechanism": "NOT ESTABLISHED",
                "trigger": "NOT ESTABLISHED",
                "detectability": "NOT ESTABLISHED",
                "severity_basis": "NOT ESTABLISHED",
                "design_control_direction": "NOT ESTABLISHED",
                "applicability_signals": []})
    return out


def get_domain_module(domain_id: str) -> Dict[str, Any]:
    """Merged Directive-4 + A4/A6 module view for one domain (base template +
    module depth). UNKNOWN domain returns the generic module honestly.
    CEO A4 requires every domain module to answer:
      why_this_domain (basis) / governing_models / model_applicability /
      model_assumptions / critical_parameters / failure_modes /
      design_input_patterns / design_output_patterns /
      verification_methods / validation_methods / manufacturing_routes.
    """
    base = DOMAIN_TEMPLATES.get(domain_id, GENERIC_TEMPLATE)
    mod = DOMAIN_MODULES.get(domain_id, {})
    verification = list(base.get("verification_methods", []))
    seen = set(verification)
    for m in mod.get("verification_methods_extra", []):
        if m not in seen:
            verification.append(m)
            seen.add(m)
    governing = []
    for m in mod.get("governing_models", []):
        g = dict(m)
        # A4: applicability and assumptions surface as first-class fields
        g.setdefault("model_applicability",
                     g.get("applicability", "NOT ESTABLISHED"))
        g.setdefault("model_assumptions", [])
        governing.append(g)
    failure_detail = _structured_failure_modes(mod)
    return {
        "domain_id": domain_id if domain_id in DOMAIN_TEMPLATES else "UNKNOWN",
        "label": base.get("label", GENERIC_TEMPLATE["label"]),
        "signals": list(base.get("signals", [])),
        "disciplines": list(base.get("disciplines",
                                     GENERIC_TEMPLATE["disciplines"])),
        # A4: WHY this domain exists (the basis the engine cites when it
        # answers "why did you choose this engineering domain/model")
        "why_this_domain_basis": {
            "signal_mapping": ("domain selected by matching the invention's "
                               "mechanism/problem text against this domain's "
                               "characteristic signals; the matched signals "
                               "travel with the decision"),
            "characteristic_signals": list(base.get("signals", [])),
            "epistemic_class": "MODEL_DERIVED",
        },
        "governing_models": governing,
        # A4 direct-view keys (registry contract naming)
        "model_applicability": [
            {"model": g["model"],
             "applicability": g.get("model_applicability",
                                    g.get("applicability",
                                          "NOT ESTABLISHED"))}
            for g in governing],
        "model_assumptions": [
            {"model": g["model"], "assumptions": list(
                g.get("model_assumptions", []))}
            for g in governing],
        "critical_parameters": list(mod.get("critical_parameters", [])),
        "failure_modes": failure_detail,
        "failure_mode_detail": failure_detail,
        "design_input_patterns": list(mod.get("design_input_patterns", [])),
        "design_output_patterns": list(mod.get("design_output_patterns", [])),
        "verification_methods": verification,
        "validation_methods": list(mod.get("validation_methods", [])),
        "manufacturing_patterns": list(mod.get("manufacturing_patterns", []))
        or [{"process": p.get("process"), "status": p.get("status")}
            for p in base.get("manufacturing_candidates", [])],
        "manufacturing_routes": list(mod.get("manufacturing_patterns", []))
        or [p.get("process") for p in
            base.get("manufacturing_candidates", [])],
        "architecture_blocks": list(base.get("architecture_blocks", [])),
        # R443: medical-context architecture participates only when the
        # canonical applicability is medical (applicability.py filter)
        "architecture_blocks_medical": list(
            base.get("architecture_blocks_medical", [])),
        "manufacturing_candidates": [dict(m) for m in
                                     base.get("manufacturing_candidates",
                                              [])],
        "materials_candidates": [dict(m) for m in
                                 base.get("materials_candidates", [])],
        "standards_candidates": [dict(s) for s in
                                 base.get("standards_candidates", [])],
        "epistemic_note": ("all module content is ENGINEERING_PROPOSED "
                           "domain-generic candidate material; parameter "
                           "VALUES are UNKNOWN until sourced (Art. "
                           "XXVII)"),
    }


def export_registry_json() -> Dict[str, Any]:
    """Canonical ENGINEERING_DOMAIN_REGISTRY.json content (Directive 4;
    R445: also publishes THE canonical domain-family vocabulary)."""
    domains = {}
    for domain_id in DOMAIN_TEMPLATES:
        domains[domain_id] = get_domain_module(domain_id)
    domains["UNKNOWN"] = get_domain_module("UNKNOWN")
    canonical_families = {}
    for family_id, spec in CANONICAL_DOMAIN_FAMILIES.items():
        canonical_families[family_id] = {
            "label": spec["label"],
            "engine_domains": list(spec["engine_domains"]),
            "bridge_archetypes": list(spec["bridge_archetypes"]),
        }
    return {
        "registry": "ENGINEERING_DOMAIN_REGISTRY",
        "version": "1.1.0",
        "generated_by": "discovery_fabric/engine/domains.py::export_registry_json",
        "contract": {
            "maps": "evidence/mechanism characteristics (signals) -> "
                    "engineering module",
            "per_domain_required": ["governing_models", "critical_parameters",
                                    "failure_modes", "design_input_patterns",
                                    "design_output_patterns",
                                    "verification_methods",
                                    "validation_methods",
                                    "manufacturing_patterns"],
            "per_domain_reasoning_required": [
                "why_this_domain_basis", "model_applicability",
                "model_assumptions", "failure_mode_detail",
                "manufacturing_routes"],
            "failure_mode_required_fields": [
                "mode", "physical_mechanism", "trigger", "detectability",
                "severity_basis", "design_control_direction",
                "applicability_signals"],
            "epistemic_rule": ("module content is ENGINEERING_PROPOSED; "
                               "no parameter values are asserted; UNKNOWN "
                               "domain stays UNKNOWN (Art. XXV)"),
            "canonical_domain_families_rule": (
                "R445: the canonical_domain_families section is THE one "
                "authoritative domain-family vocabulary (Art. X). The "
                "canonical family id is the ONE domain identity that "
                "flows unchanged through USER PROBLEM -> PROBLEM CONTEXT "
                "-> DOMAIN SPEC -> ENGINEERING SPEC -> GEOMETRY -> CIO -> "
                "DOSSIER -> PACKAGE; engine routing domains and bridge "
                "geometry archetypes are internal routing vocabularies "
                "declared here by their mapping into canonical families "
                "— never a second semantic namespace"),
        },
        "canonical_domain_families": canonical_families,
        "domains": domains,
        "exported_at": utc_now_iso(),
    }


def utc_now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def domain_label(domain_id: str) -> str:
    if domain_id == "UNKNOWN":
        return GENERIC_TEMPLATE["label"]
    return DOMAIN_TEMPLATES.get(domain_id, GENERIC_TEMPLATE)["label"]
