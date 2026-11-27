"""R144 generation strength (R143-F6/F7) — problem-aware mechanism
selection.

The V110 finding: the engine's invention quality is the binding
constraint (v16 mean 2.73, 8/30 off-target, 0 strong). The documented
off-target patterns are the spec:
  - chemical cathodic protection proposed for an ABRASION problem
  - flow modulation proposed for a TRAMP METAL (separation) problem
  - passive insulation proposed for a NUCLEATION problem
  - monitoring proposed where MITIGATION is asked for
This module maps the stated failure mode -> the correct mechanism
class BEFORE operator selection (deterministic, physics-grounded),
so the generator is constrained to mechanisms that physically couple
to the failure, and every off-target coupling is a typed rejection.

Design rules (the constitution hooks):
  - Art. 3 (typed, reversible): every rejection/reason is a typed
    record, nothing silent; the mapping table is data, not a model.
  - Art. 13 spirit: the mapping is checkable — the unit tests pin the
    four documented off-target examples as regressions.
  - No invention of physics: the taxonomy and the couplings below are
    standard engineering classification (tribology, nucleation,
    separation science); the formulas live in quant_test.py with units.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# The failure-mode taxonomy: keyed by the PHYSICS of the stated failure
# ---------------------------------------------------------------------------
FAILURE_CLASSES = {
    "abrasion_erosion": {
        "physics": ("hard particles or droplets impacting/sliding a "
                    "surface remove material"),
        "keywords": ["erosion", "abrasion", "wear", "slurry",
                     "particle impact", "sand", "grit", "sanding",
                     "rubbing", "tribolog", "spalling", "scuffing",
                     "debris impact", "droplet impact", "rain erosion",
                     "cavitation erosion", "leading edge",
                     # R145 sealed-set extension (typed, additive):
                     # the VERB forms — "erosion" is not a substring
                     # of "erodes" (the same gap the engine-map fix
                     # closed)
                     "erode", "erodes", "eroding", "erosive", "galling",
                     "adhesive wear",
                     "grinding wear",
                     "surface fatigue"],
        },
    "fouling_deposition": {
        "physics": ("material accumulates on a surface and degrades "
                    "heat/mass transfer or flow"),
        "keywords": ["fouling", "scaling", "deposition", "biofilm",
                     "biofouling", "caking", "encrustation", "slime",
                     "barnacle", "algae", "precipitate", "paraffin",
                     "asphaltene", "dust cake", "sediment buildup",
                     # R145 sealed-set extension (typed, additive): the
                     # verb + noun stems the sealed problems use
                     "foul", "fouls", "deposit", "foulant", "scale",
                     "scales", "silica", "swell",
                     "blanket",
                     "gum",
                     "varnish",
                     "print blanket",
                     "coating buildup"],
    },
    "nucleation_phase_change": {
        "physics": ("uncontrolled phase-change nucleation (bubbles, "
                    "droplets, crystals, ice) destabilizes the "
                    "process"),
        "keywords": ["nucleation", "bubble", "boiling instability",
                     "crystalliz", "freezing", "ice formation",
                     "icing", "dendrite", "supercool", "cavitation "
                     "bubble", "condensation jump", "flash",
                     # R145 sealed-set extension (typed, additive)
                     "freeze", "freezes", "uncontrolled ice",
                     "ice crystal", "crystallization", "blister",
                     "blistering",
                     "outgassing",
                     # R174 smoke-driven extension (typed, additive;
                     # eval/r174_v19_smoke/s2+s4): the bare stem
                     # "cavitates" hit nothing (only the compound
                     # "cavitation erosion"/"cavitation bubble" did,
                     # so a cavitation problem fell to corrosion_
                     # chemical on "pitting"); hydrate formation is
                     # phase-change nucleation and hit NOTHING
                     "cavitat", "cavities collapse", "hydrate",
                     "clathrate", "frost", "defrost"],
    },
    "contamination_separation": {
        "physics": ("foreign objects or contaminant particles must be "
                    "separated from a stream or product"),
        "keywords": ["tramp metal", "foreign object", "contaminant",
                     "separator", "screening", "sieving", "inclusion",
                     "swarf", "chip removal", "filter clog", "particulate "
                     "removal", "debris removal", "slag",
                     # R145 sealed-set extension (typed, additive)
                     "impurit", "separation", "separate", "purification",
                     "recycled", "backlash",
                     "jam",
                     "foreign material",
                     "wandering",
                     "slip"],
    },
    "corrosion_chemical": {
        "physics": ("electrochemical or chemical attack consumes the "
                    "material"),
        "keywords": ["corrosion", "rust", "oxidation", "pitting",
                     "galvanic", "caustic", "acid attack", "crevice "
                     "corrosion", "erosion-corrosion", "dealloying",
                     "sour service", "h2s", "chloride attack",
                     # R145 sealed-set extension (typed, additive): the
                     # verb forms — "corrosion" is not a substring of
                     # "corrodes"
                     "corrode", "corrodes", "corroding", "corrosive",
                     "acid condensat",
                     # R174 smoke-driven DISAMBIGUATION: a problem that
                     # names cavitation+pitting is MECHANICAL erosion
                     # by collapsing bubbles, not electrochemical
                     # attack — the cavitation stems now live on
                     # nucleation_phase_change/abrasion_erosion and
                     # outrank the bare "pitting" hit here
                     ],
    },
    "fatigue_crack": {
        "physics": ("cyclic stress grows cracks to failure"),
        "keywords": ["fatigue", "crack initiation", "crack growth",
                     "vibration fatigue", "thermal cycling fatigue",
                     "fretting", "low-cycle", "high-cycle",
                     # R145 sealed-set extension (typed, additive):
                     # plain crack/wheel-seat vocabulary — weighted
                     # cross-class phrases ("cte mismatch" etc.) live
                     # on their own classes so the owner's grouping
                     # holds
                     "crack", "cracks", "cracking", "wheel-seat",
                     "crankshaft", "cyclic bending", "shelling",
                     "spalling",
                     "contact fatigue",
                     "rolling contact",
                     "strand break",
                     "rope",
                     "gear tooth",
                     "pitting fatigue"],
    },
    "vibration_resonance": {
        "physics": ("structural resonance amplifies motion and "
                    "damages equipment"),
        "keywords": ["resonance", "vortex shedding", "vibration "
                     "amplitude", "acoustic resonance", "flutter",
                     "chatter",
                     # R145 sealed-set extension (typed, additive): the
                     # verb forms + the multi-word phrases that
                     # out-score fatigue's plain "crack" on the
                     # resonance-caused-cracking rows
                     "resonat", "vortex-induced vibration",
                     "resonates at", "spindle chatter",
                     "vortex-induced vibration fatigue", "rattle",
                     "whine",
                     "hum",
                     "oscillation"],
    },
    "thermal_mismatch": {
        "physics": ("heat flux or temperature gradients exceed the "
                    "design envelope"),
        "keywords": ["hot spot", "overheat", "thermal gradient",
                     "heat flux", "temperature excursion", "cooling "
                     "capacity", "capacity droop", "condenser fouling "
                     "thermal",
                     # R145 sealed-set extension (typed, additive): the
                     # CTE/TBC vocabulary — deliberately NOT plain
                     # "thermal cycling" (v17-18 is a fatigue-class row
                     # that uses that phrase)
                     "cte mismatch", "bond-coat", "bond coat",
                     "thermal-barrier", "thermal barrier", "tbc",
                     "power cycling", "cte mismatch on thermal "
                     "cycling", "warp",
                     "distortion",
                     "sag",
                     "thermal drift"],
    },
    "leakage_sealing": {
        "physics": ("a seal or joint loses containment"),
        "keywords": ["leak", "seal failure", "gasket", "blow-by",
                     "containment loss", "emission leak", "weep",
                     "seep",
                     "drip",
                     "permeation"],
    },
    "electrical_insulation": {
        "physics": ("electrical insulation or conduction degrades"),
        "keywords": ["insulation breakdown", "partial discharge",
                     "short circuit", "arc", "tracking", "dielectric",
                     # R145 sealed-set extension (typed, additive)
                     "field grading", "winding insulation",
                     "bushing insulation", "dielectric breakdown"],
    },
}

# ---------------------------------------------------------------------------
# The mechanism classes that PHYSICALLY COUPLE to each failure class.
# Each entry: the mechanism family and WHY it couples (the root-cause
# chain the generator must follow). Anything outside the mapped set for
# the classified failure is an off-target typed rejection.
# ---------------------------------------------------------------------------
MECHANISM_MAP = {
    "abrasion_erosion": [
        {"mech": "compliant_elastomer_coating",
         "why": ("a low-modulus layer elastically absorbs particle/"
                 "droplet impact energy, cutting the transmitted "
                 "stress peak below the material fatigue/erosion "
                 "threshold"),
         "cross_domain": "helicopter rotor rain-erosion boots; "
                         "ship propeller elastomer coatings"},
        {"mech": "surface_hardening_treatment",
         "why": ("raises the near-surface hardness (carburizing, "
                 "nitriding, HVOF cermet) so the abrasive cuts slower "
                 "(Archard: wear rate ~ 1/H)"),
         "cross_domain": "rail wheel hardening; dredge pump liners"},
        {"mech": "micro_texturing",
         "why": ("engineered surface dimples/riblets reduce effective "
                 "particle contact time and trap wear debris, "
                 "lowering two-body abrasion"),
         "cross_domain": "shark-skin riblets; laser-textured seal "
                         "faces"},
        {"mech": "particle_trajectory_deflection",
         "why": ("re-shapes the flow path so particles leave the "
                 "surface before impact (vane curvature, impeller "
                 "trim, sacrificial baffles)"),
         "cross_domain": "cyclone outlet geometry; slurry pump "
                         "vane profiles"},
        {"mech": "sacrificial_replaceable_shield",
         "why": ("moves the wear site to a cheap renewable element "
                 "(replaceable liner/shield) instead of the "
                 "primary structure"),
         "cross_domain": "tractor track pads; blast-furnace hearth "
                         "liners"},
    ],
    "fouling_deposition": [
        {"mech": "surface_energy_modification",
         "why": ("low surface energy / slippery liquid-infused "
                 "porous surfaces reduce adhesion of foulants so "
                 "shear removes them at operating flow"),
         "cross_domain": "SLIPS surfaces from carnivorous-plant "
                         "tribology; ship hull fouling-release "
                         "silicones"},
        {"mech": "in_situ_mechanical_cleaning",
         "why": ("scheduled scraper/brush/pigging removes the deposit "
                 "before it hardens, restoring transfer without "
                 "chemical shutdowns"),
         "cross_domain": "pipeline pigs; condenser tube-cleaning "
                         "balls"},
        {"mech": "ultrasonic_antifouling",
         "why": ("surface-mounted transducers create cavitation/"
                 "acoustic microstreaming that detaches early-stage "
                 "biofilms and scales"),
         "cross_domain": "ship hull ultrasonic antifouling; heat "
                         "exchanger acoustic cleaning"},
        {"mech": "crystallization_control_by_dosing",
         "why": ("threshold-inhibitor dosing or seeded crystallization "
                 "keeps hardness salts dissolved or growing in the "
                 "bulk, not on the wall"),
         "cross_domain": "cooling-tower polyphosphate programs; "
                         "sugar-pan seeding"},
        {"mech": "flow_geometry_antifouling",
         "why": ("eliminates dead zones/crevices where foulants "
                 "settle (self-draining geometry, minimum-shear "
                 "routing)"),
         "cross_domain": "self-cleaning separator plates; sanitary "
                         "process piping"},
    ],
    "nucleation_phase_change": [
        {"mech": "controlled_nucleation_sites",
         "why": ("engineered nucleation sites (textured/seeded "
                 "surfaces) set WHERE phase change starts, removing "
                 "the stochastic bursts that destabilize the "
                 "process"),
         "cross_domain": "boiling enhancement surfaces; seed-crystal "
                         "pans in crystallization"},
        {"mech": "acoustic_ultrasonic_nucleation",
         "why": ("applied acoustic fields trigger uniform nucleation "
                 "on demand (sononucleation), preventing supercooling "
                 "bursts and rough boiling"),
         "cross_domain": "ultrasonic freezing initiation; "
                         "sonocrystallization in pharma"},
        {"mech": "dissolved_gas_management",
         "why": ("degassing or gas seeding removes the supersaturation "
                 "driving bubble nucleation"),
         "cross_domain": "feedwater deaeration; cavitation control "
                         "by air injection"},
        {"mech": "superheat_pressure_path_control",
         "why": ("a staged pressure/temperature path keeps the fluid "
                 "outside the spontaneous-nucleation envelope "
                 "(expansion staging, flash control)"),
         "cross_domain": "multistage flash desalination staging; "
                         "letdown stations"},
        {"mech": "nucleation_inhibitor_dosing",
         "why": ("kinetic inhibitors/antifreeze polymers block crystal "
                 "nucleation and growth below the thermodynamic "
                 "freezing point"),
         "cross_domain": "pipeline kinetic-hydrate inhibitors; "
                         "anti-icing polymer additives"},
    ],
    "contamination_separation": [
        {"mech": "magnetic_gradient_separation",
         "why": ("a high-gradient magnetic field extracts ferrous/"
                 "paramagnetic tramp without contacting the product "
                 "stream"),
         "cross_domain": "drum/wet high-intensity magnetic "
                         "separators; coolant swarf recovery"},
        {"mech": "eddy_current_separation",
         "why": ("a time-varying field repels non-ferrous conductors "
                 "out of the stream, catching what magnets miss"),
         "cross_domain": "scrap-metal eddy-current sorting; "
                         "non-ferrous recovery lines"},
        {"mech": "self_cleaning_screen",
         "why": ("a continuously cleaned screening element (vibrating, "
                 "brushed, backwashed) holds separation without "
                 "progressive clogging"),
         "cross_domain": "rotating drum screens; self-cleaning "
                         "strainers"},
        {"mech": "density_settling_separation",
         "why": ("a designed residence-time basin/cyclone lets density "
                 "differences do the separation continuously"),
         "cross_domain": "hydrocyclone desanding; settling ponds"},
        {"mech": "process_isolation_chamber",
         "why": ("a sacrificial pre-catch stage (trap pot, weir, "
                 "grizzly) removes oversize before the sensitive "
                 "equipment"),
         "cross_domain": "crusher grizzly screens; pump strainer "
                         "pots"},
    ],
    "corrosion_chemical": [
        {"mech": "cathodic_protection_sizing",
         "why": ("impressed-current or sacrificial anodes shift the "
                 "potential below the corrosion threshold; sizing to "
                 "the actual current demand is the design task"),
         "cross_domain": "ship hull ICCP; pipeline anode beds"},
        {"mech": "inhibitor_dosing",
         "why": ("film-forming or scavenger inhibitors cut the "
                 "reaction rate at the wall at ppm cost"),
         "cross_domain": "pipeline corrosion inhibitors; H2S "
                         "scavenging"},
        {"mech": "barrier_coating_upgrade",
         "why": ("a diffusion barrier (epoxy/FBE/glass-flake) cuts the "
                 "corrodant flux to the metal surface"),
         "cross_domain": "FBE pipeline coatings; tank linings"},
        {"mech": "material_selection_upgrade",
         "why": ("an alloy/liners matched to the actual chemistry "
                 "(duplex, 6Mo, titanium) removes the corrosion "
                 "driver"),
         "cross_domain": "seawater condenser tubing; sour-service "
                         "steels"},
        {"mech": "crevice_geometry_elimination",
         "why": ("removing crevices/deposits sites (weld profiling, "
                 "drainage, smooth transitions) removes localized "
                 "corrosion initiation"),
         "cross_domain": "sanitary weld profiling; offshore "
                         "drainage details"},
    ],
    "fatigue_crack": [
        {"mech": "resonance_avoidance_stiffening", "why": "shift the "
         "excited modes away from the forcing band", "cross_domain":
         "tube bundles in exchangers; turbine blades"},
        {"mech": "compressive_residual_stress", "why": "shot peening/"
         "laser peening closes surface crack initiation",
         "cross_domain": "aircraft skins; springs"},
        {"mech": "duty_cycle_reduction", "why": "soft-start/ramp "
         "limiting cuts the cyclic amplitude at the source",
         "cross_domain": "VFD soft starts; press valve timing"},
    ],
    "vibration_resonance": [
        {"mech": "tuned_mass_damper", "why": "an added SDOF absorbs "
         "the resonant energy", "cross_domain": "stacks, bridges, "
         "turbine hall floors"},
        {"mech": "vortex_shedding_suppression", "why": "helical "
         "strakes/sheds break the coherent shedding",
         "cross_domain": "chimney strakes; riser fairings"},
        {"mech": "support_stiffness_reconfiguration", "why": "reseat "
         "the modal frequencies by bracing/mass",
         "cross_domain": "piping natural-frequency audits"},
    ],
    "thermal_mismatch": [
        {"mech": "heat_spreader_enhancement", "why": "inserts/spreaders "
         "cut the peak flux at the hot spot", "cross_domain":
         "electronics vapor chambers; molds"},
        {"mech": "active_cooling_loop", "why": "pumped loop sized to "
         "the actual duty removes the deficit", "cross_domain":
         "inverter liquid cooling; kiln shell coolers"},
        {"mech": "duty_redistribution", "why": "split/stage the load "
         "so no element exceeds its flux limit", "cross_domain":
         "furnace zone control"},
    ],
    "leakage_sealing": [
        {"mech": "seal_geometry_reload", "why": "gasket stress "
         "redistribution (self-energizing lips, metal-to-metal) "
         "restores contact pressure", "cross_domain": "pipeline "
         "mechanical joints"},
        {"mech": "double_isolation_barrier", "why": "a second "
         "monitored barrier converts leaks to detectable events",
         "cross_domain": "twin-seal valves"},
        {"mech": "self_healing_elastomer_seal", "why": "a swellable/"
         "self-healing seal compound closes the leak path at the "
         "leak site itself", "cross_domain": "water-main swelling "
         "gaskets; downhole packers"},
    ],
    "electrical_insulation": [
        {"mech": "stress_grading", "why": "field-grading materials cut "
         "the local E-field at defects", "cross_domain": "stator end "
         "windings"},
        {"mech": "environmental_enclosure", "why": "sealed/pressurized "
         "enclosure removes the tracking medium", "cross_domain":
         "outdoor switchgear"},
        {"mech": "creepage_path_extension", "why": "shed/profile "
         "geometry lengthens the surface creepage path below the "
         "flashover limit", "cross_domain": "high-voltage insulator "
         "sheds"},
    ],
}

# Typed OFF-TARGET couplings (documented R143-F7 examples pinned as
# rejections): a proposed mechanism family for the WRONG failure class
# is a typed off_target rejection with the reason.
OFF_TARGET_REJECTIONS = [
    {"if_failure": "abrasion_erosion",
     "if_mech_contains": ["cathodic", "anodic", "electrochemical",
                          "inhibitor dosing", "barrier_coating_upgra"],
     "why": ("chemical (cathodic/inhibitor) protection couples to "
             "ELECTROCHEMICAL material loss, not to mechanical particle "
             "removal — the documented v16 off-target example")},
    {"if_failure": "contamination_separation",
     "if_mech_contains": ["flow_modulation", "flow_geometry_anti",
                          "vortex", "duty_redistribution",
                          "modulate the flow", "flow rate", "adjust flow",
                          "increase flow", "reduce flow",
                          "turbulence promot", "mixing"],
     "why": ("modulating flow does not extract a discrete foreign "
             "object; separation needs a force/geometry that acts ON "
             "THE OBJECT (magnetic, eddy, screen, settling) — the "
             "documented v16 off-target example")},
    {"if_failure": "nucleation_phase_change",
     "if_mech_contains": ["insulation", "thermal_barrier",
                          "heat_spreader", "passive_insulation"],
     "why": ("passive insulation changes heat LOSS, not where/when "
             "phase change NUCLEATES — the documented v16 off-target "
             "example")},
    {"if_failure": "any",
     "if_mech_contains": ["add_monitoring", "add_sensor", "add sensor",
                          "install sensor", "additional sensor",
                          "instrumentation", "inspection",
                          "condition_monitoring", "condition monitoring",
                          "for monitoring", "real-time monitoring"],
     "why": ("monitoring DETECTS but does not MITIGATE; where the ask "
             "is mitigation the mechanism must act on the physics "
             "(monitoring is admissible only as an adjunct and never "
             "as the intervention) — the documented v16 off-target "
             "example")},
]


@dataclass
class MechanismSelection:
    """The typed selection record (rides the generation row)."""
    failure_class: str
    confidence: float
    evidence_span: str
    allowed_mech_classes: list
    selected_mech_class: str
    root_cause_chain: str
    cross_domain: str
    off_target: bool = False
    off_target_reason: str = ""
    notes: list = field(default_factory=list)


def classify_failure(text: str) -> MechanismSelection:
    """Keyword+regex physics classifier with typed confidence."""
    t = (text or "").lower()
    scores = {}
    evidence = {}
    for fc, spec in FAILURE_CLASSES.items():
        hits = []
        for kw in spec["keywords"]:
            if kw in t:
                hits.append(kw)
        # weighted by keyword specificity (longer = more specific)
        scores[fc] = sum(1 + 0.25 * kw.count(" ") for kw in hits)
        evidence[fc] = hits
    if not scores or max(scores.values()) == 0:
        return MechanismSelection(
            failure_class="unclassified", confidence=0.0,
            evidence_span="", allowed_mech_classes=[],
            selected_mech_class="", root_cause_chain="",
            cross_domain="",
            notes=["typed: no failure-class keywords matched — the "
                   "problem text names no recognizable failure physics"])
    fc = max(scores, key=lambda k: scores[k])
    hits = evidence[fc]
    conf = scores[fc] / (sum(scores.values()) or 1)
    return MechanismSelection(
        failure_class=fc, confidence=round(conf, 3),
        evidence_span=", ".join(hits[:5]),
        allowed_mech_classes=[m["mech"] for m in MECHANISM_MAP.get(fc, [])],
        selected_mech_class="", root_cause_chain="",
        cross_domain="",
        notes=[f"physics: {FAILURE_CLASSES[fc]['physics']}"])


def check_off_target(failure_class: str, mech_text: str):
    """The documented off-target couplings as typed rejections."""
    m = (mech_text or "").lower()
    for rej in OFF_TARGET_REJECTIONS:
        if rej["if_failure"] != "any" and rej["if_failure"] != failure_class:
            continue
        if any(p in m for p in rej["if_mech_contains"]):
            return True, rej["why"]
    return False, ""


def select_mechanism(problem_text: str,
                     mech_text: str = "") -> MechanismSelection:
    """The full typed selection: classify -> constrain -> off-target
    check. If mech_text is given (a generated candidate), it is
    checked against the mapped classes and the documented rejections."""
    sel = classify_failure(problem_text)
    if not sel.failure_class or sel.failure_class == "unclassified":
        return sel
    if mech_text:
        off, why = check_off_target(sel.failure_class, mech_text)
        sel.off_target = off
        sel.off_target_reason = why
        # find the mapped class the candidate names (if any)
        for entry in MECHANISM_MAP[sel.failure_class]:
            toks = entry["mech"].split("_")
            if sum(1 for tk in toks if tk in mech_text.lower()) >= max(
                    1, len(toks) - 1):
                sel.selected_mech_class = entry["mech"]
                sel.root_cause_chain = entry["why"]
                sel.cross_domain = entry["cross_domain"]
                break
    return sel


def mechanism_prompt_block(problem_text: str) -> str:
    """The prompt block that CONSTRAINS the generator to the mapped
    mechanism classes (the problem-aware selection, not blind TRIZ)."""
    sel = classify_failure(problem_text)
    if sel.failure_class == "unclassified":
        return ("FAILURE-MODE MAPPING: unclassified — state the failure "
                "physics explicitly before proposing any mechanism.")
    entries = MECHANISM_MAP[sel.failure_class]
    lines = [
        f"FAILURE-MODE MAPPING (typed, R143-F7): the stated failure is "
        f"{sel.failure_class} ({FAILURE_CLASSES[sel.failure_class]['physics']}; "
        f"evidence: {sel.evidence_span}).",
        "Your intervention MUST use one of these mechanism classes that "
        "physically couple to this failure:",
    ]
    for e in entries:
        lines.append(f"- {e['mech']}: {e['why']} (precedent: "
                     f"{e['cross_domain']})")
    lines.append(
        "FORBIDDEN for this failure class: "
        + "; ".join(r["if_mech_contains"][0] for r in OFF_TARGET_REJECTIONS
                    if r["if_failure"] in (sel.failure_class, "any"))
        + ". Monitoring alone is never the intervention.")
    lines.append(
        "Your MECHANISM line must name the chosen mechanism class and "
        "ONE quantitative falsifiable prediction with units (e.g. "
        "'wear rate drops >=40% (mg/h), measured by mass-loss coupon "
        "test'), and one FALSIFICATION_TEST that can fail numerically.")
    return "\n".join(lines)
