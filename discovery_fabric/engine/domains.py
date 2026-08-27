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
             "verify_applicability": True},
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
             "applicability": "newtonian, incompressible, laminar"},
            {"model": "orifice/restriction pressure drop",
             "equation_ids": ["EQ-FLUIDICS-ORIFICE"],
             "applicability": "discrete constrictions"},
            {"model": "Reynolds regime screening",
             "equation_ids": ["EQ-FLUIDICS-REYNOLDS"]}],
        "critical_parameters": [
            "lumen inner diameter", "lumen length", "surface roughness",
            "operating pressure head", "flow rate range",
            "viscosity of flowed medium", "occlusion growth tolerance"],
        "candidate_failure_modes": [
            "proximal occlusion by tissue ingrowth",
            "lumen collapse under external pressure (kink)",
            "encrustation / mineral deposition",
            "regime transition to turbulence altering calibration",
            "check-valve seat wear opening reverse leakage"],
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
             "equation_ids": ["EQ-OPTICS-BEERLAMBERT"]},
            {"model": "photovoltaic conversion at receiver",
             "equation_ids": ["EQ-OPTICS-PV-CONVERSION"]},
            {"model": "fluence and thermal load at target",
             "equation_ids": ["EQ-OPTICS-FLUENCE", "EQ-OPTICS-THERMAL"]}],
        "critical_parameters": [
            "source wavelength", "emitted optical power",
            "fiber/transport numerical aperture",
            "receiver active area", "conversion efficiency",
            "target-path absorption coefficient", "interface temperature rise"],
        "candidate_failure_modes": [
            "misalignment loss at couplings",
            "fiber bend radiative loss beyond limit",
            "photovoltaic conversion degradation with temperature",
            "thermal damage at tissue interface",
            "window fouling reducing delivered fluence"],
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
             "equation_ids": ["EQ-RF-LINKBUDGET"]},
            {"model": "free-space / in-body path loss",
             "equation_ids": ["EQ-RF-PATHLOSS"]},
            {"model": "SNR and BER at receiver",
             "equation_ids": ["EQ-RF-SNR"]},
            {"model": "SAR exposure constraint",
             "equation_ids": ["EQ-RF-SAR"]}],
        "critical_parameters": [
            "carrier frequency", "transmit power (regulatory-bounded)",
            "antenna gain and pattern", "path length and depth",
            "receiver noise figure", "required BER at data rate",
            "SAR at tissue interface"],
        "candidate_failure_modes": [
            "link margin collapse at maximum depth/orientation",
            "SAR exceedance at transmit power needed for link",
            "detuning from dielectric loading of nearby tissue",
            "interference in clinic RF environment",
            "antenna feed joint fatigue failure"],
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
             "equation_ids": ["EQ-ACOUSTIC-IMPEDANCE"]},
            {"model": "piezoelectric transduction resonance",
             "equation_ids": ["EQ-ACOUSTIC-RESONANCE"]}],
        "critical_parameters": [
            "operating frequency", "element aperture", "matching layer Z",
            "excitation voltage and duty", "detection threshold",
            "coupling-path attenuation"],
        "candidate_failure_modes": [
            "detection threshold missed at depth (attenuation)",
            "crosstalk between elements corrupting detection",
            "resonance drift with temperature",
            "bond-wire fatigue under cyclic excitation",
            "coupling loss at interface deairing failure"],
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
             "equation_ids": ["EQ-MRI-LARMOR"]},
            {"model": "induction signal (Faraday pickup)",
             "equation_ids": ["EQ-MRI-INDUCTION"]}],
        "critical_parameters": [
            "B0 field strength", "coil sensitivity profile",
            "acquisition bandwidth", "sample conductivity",
            "SAR from RF exposure", "gradient amplitude"],
        "candidate_failure_modes": [
            "RF heating at conductive interfaces",
            "torque/attraction on ferromagnetic component",
            "image artifact corrupting quantification",
            "SNR insufficient at required resolution",
            "gradient-induced vibration fatigue"],
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
             "equation_ids": ["EQ-ENZYME-MM"]}],
        "critical_parameters": [
            "immobilized activity density", "substrate contact time",
            "mass-transfer coefficient", "operating temperature",
            "pH window", "leaching rate"],
        "candidate_failure_modes": [
            "activity decay below functional floor",
            "mass-transfer limitation starving active sites",
            "enzyme leaching into flow stream",
            "immunogenic byproduct generation",
            "substrate competition reducing selectivity"],
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
             "before quantitative use"},
            {"model": "biofilm mass-balance with predation",
             "equation_ids": [], "note": "no registry equation yet; source "
             "before quantitative use"}],
        "critical_parameters": [
            "surface phage loading density", "infectivity retention half-life",
            "host range breadth", "moi at contact surface",
            "CFU challenge load", "resistance emergence rate"],
        "candidate_failure_modes": [
            "infectivity loss before clinical use window",
            "resistant strain emergence negating kill",
            "host-range mismatch to clinical isolate",
            "coating wear releasing loaded phage",
            "biofilm matrix blocking phage access"],
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
             "before quantitative use"},
            {"model": "expected information gain for data collection",
             "equation_ids": [], "note": "engine-native; see experiment "
             "selector"}],
        "critical_parameters": [
            "training data volume and provenance",
            "label quality rate", "target operating point (precision/recall)",
            "calibration error budget", "inference latency ceiling",
            "distribution-shift monitoring thresholds"],
        "candidate_failure_modes": [
            "distribution shift degrading accuracy post deployment",
            "label noise propagating to biased predictions",
            "overfitting to source-site artifacts",
            "calibration drift invalidating decision thresholds",
            "feedback-loop data contamination"],
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
             "equation_ids": ["EQ-MECH-BUCKLING"]},
            {"model": "fatigue life under cyclic load (S-N)",
             "equation_ids": ["EQ-MECH-FATIGUE"]}],
        "critical_parameters": [
            "member slenderness ratio", "yield/ultimate strength",
            "applied cyclic load amplitude", "required run-out cycles",
            "articulation radius", "friction coefficient at guides"],
        "candidate_failure_modes": [
            "kink/buckling below required push ability",
            "fatigue crack initiation at stress concentrator",
            "wear debris generation at sliding interfaces",
            "joint separation under overload",
            "set-release of superelastic shape after set"],
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
             "equation_ids": ["EQ-THERMAL-CONDUCTION"]}],
        "critical_parameters": [
            "heat generation at source", "spreader conductivity",
            "interface contact resistance", "reject-path area",
            "allowable temperature rise", "ambient worst case"],
        "candidate_failure_modes": [
            "hotspot exceeding material/safety limit",
            "interface delamination raising resistance over life",
            "coolant/flow path blockage (if active)",
            "thermal runaway coupling to electronics",
            "condensation at cold surfaces"],
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
             "before quantitative use"},
            {"model": "thermoelectric Seebeck conversion",
             "equation_ids": [], "note": "no registry equation yet; source "
             "before quantitative use"}],
        "critical_parameters": [
            "ambient source magnitude and spectrum",
            "transduction coefficient", "conditioning efficiency",
            "storage capacity and leakage", "load duty profile",
            "startup threshold power"],
        "candidate_failure_modes": [
            "harvested power below startup threshold",
            "transducer depoling/aging loss",
            "storage leakage draining buffer between events",
            "load transient collapsing supply rail",
            "encapsulation stress cracking transducer"],
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


def get_domain_module(domain_id: str) -> Dict[str, Any]:
    """Merged Directive-4 module view for one domain (base template +
    module depth). UNKNOWN domain returns the generic module honestly."""
    base = DOMAIN_TEMPLATES.get(domain_id, GENERIC_TEMPLATE)
    mod = DOMAIN_MODULES.get(domain_id, {})
    verification = list(base.get("verification_methods", []))
    seen = set(verification)
    for m in mod.get("verification_methods_extra", []):
        if m not in seen:
            verification.append(m)
            seen.add(m)
    return {
        "domain_id": domain_id if domain_id in DOMAIN_TEMPLATES else "UNKNOWN",
        "label": base.get("label", GENERIC_TEMPLATE["label"]),
        "signals": list(base.get("signals", [])),
        "disciplines": list(base.get("disciplines",
                                     GENERIC_TEMPLATE["disciplines"])),
        "governing_models": [dict(m) for m in mod.get("governing_models", [])],
        "critical_parameters": list(mod.get("critical_parameters", [])),
        "failure_modes": list(mod.get("candidate_failure_modes", [])),
        "design_input_patterns": list(mod.get("design_input_patterns", [])),
        "design_output_patterns": list(mod.get("design_output_patterns", [])),
        "verification_methods": verification,
        "validation_methods": list(mod.get("validation_methods", [])),
        "manufacturing_patterns": list(mod.get("manufacturing_patterns", []))
        or [{"process": p.get("process"), "status": p.get("status")}
            for p in base.get("manufacturing_candidates", [])],
        "architecture_blocks": list(base.get("architecture_blocks", [])),
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
    """Canonical ENGINEERING_DOMAIN_REGISTRY.json content (Directive 4)."""
    domains = {}
    for domain_id in DOMAIN_TEMPLATES:
        domains[domain_id] = get_domain_module(domain_id)
    domains["UNKNOWN"] = get_domain_module("UNKNOWN")
    return {
        "registry": "ENGINEERING_DOMAIN_REGISTRY",
        "version": "1.0.0",
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
            "epistemic_rule": ("module content is ENGINEERING_PROPOSED; "
                               "no parameter values are asserted; UNKNOWN "
                               "domain stays UNKNOWN (Art. XXV)"),
        },
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
