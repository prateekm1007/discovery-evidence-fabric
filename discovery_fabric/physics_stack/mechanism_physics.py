"""mechanism_physics.py — deterministic mechanism terminology ->
physics-domain classification (R413, operator directive V2 Phases 2-3).

THE OPERATOR'S RULE (Phase 3):
    "Do not allow an LLM to be the sole solver selector."
    mechanism terminology -> physical phenomena -> required equations
    -> eligible solver domains -> registry lookup
    "An LLM may propose a classification, but the registry/rules must
     verify it."

This module is the deterministic rule layer. ZERO LLM anywhere (the
RETRIEVER-role discipline applied to physics classification). The
rule table is CLOSED and carries provenance; the classification rule
is PRE-REGISTERED here (before any corpus run):

CLASSIFICATION RULE (pre-registered):
    domain evidence = the set of DISTINCT term labels matched in the
    mechanism's own text fields (equations > unexploited_phenomenon >
    governing_variables > causal_chain > technology_name > problem >
    intervention > boundary_conditions > failure_modes >
    predicted_effect).
    strongly-evidenced domain  := >= 2 distinct matched terms
    weakly-evidenced domain   := exactly 1 distinct matched term
    classification:
        0 evidenced domains                     -> UNKNOWN
        exactly 1 evidenced (weak or strong)    -> that domain
        exactly 1 strong (others weak)          -> the strong domain
        >= 2 strongly-evidenced domains         -> multiphysics
    Justification (Art. XXVII, class MODEL_DERIVED): a domain claim
    needs >= 2 INDEPENDENT term hits to count as mechanism-level
    evidence; a single hit is mention-level evidence. The rule is the
    minimal deterministic standard that resists synonym stuffing
    (distinct labels, not match counts) and stays auditable.

HONESTY NOTES:
- The vocabulary is GENERAL physics terminology authored BEFORE the
  corpus run (not candidate-specific patterns; any calibration to the
  corpus is disclosed in the matrix artifact, never silent).
- Term labels are normalized matched concepts, so repeated matches of
  the same concept cannot inflate evidence (anti-gaming).
- UNKNOWN is a first-class output (Art. XXV) — a mechanism the rules
  cannot read is NOT forced onto a neighboring domain (Art. IV).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# The operator's domain vocabulary (directive V2 Phase 2, verbatim)
# ---------------------------------------------------------------------------
PHYSICS_DOMAINS: Tuple[str, ...] = (
    "hydraulic", "structural", "thermal", "electromagnetic", "acoustic",
    "multibody", "soft-body", "chemical", "optical",
)
MULTIPHYSICS = "multiphysics"
UNKNOWN = "UNKNOWN"
CLASSIFICATION_LABELS: Tuple[str, ...] = PHYSICS_DOMAINS + (
    MULTIPHYSICS, UNKNOWN)

#: The mechanism's own text fields, in priority order (equations
#: first: declared governing relations are the strongest physics
#: signal a mechanism record carries).
MECHANISM_TEXT_FIELDS: Tuple[str, ...] = (
    "equations",                # list of declared governing relations
    "unexploited_phenomenon",   # the mechanism's own phenomenon claim
    "governing_variables",
    "causal_chain",
    "technology_name",
    "problem",
    "intervention",
    "boundary_conditions",
    "failure_modes",
    "predicted_effect",
)

#: distinct-term threshold for mechanism-level evidence (pre-registered
#: — see module docstring for the Art. XXVII justification).
STRONG_EVIDENCE_MIN_DISTINCT_TERMS = 2


def _r(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.IGNORECASE)


def _rules(pairs: List[Tuple[str, str, str]]
           ) -> List[Tuple[re.Pattern, str, str]]:
    return [(_r(p), d, t) for p, d, t in pairs]


# ---------------------------------------------------------------------------
# DOMAIN TERM RULES — general physics terminology, closed vocabulary.
# (pattern, domain, normalized term label)
# ---------------------------------------------------------------------------
_DOMAIN_TERM_RULES = _rules([
    # ---------------- hydraulic ----------------
    (r"(?<!power )(?<!energy )(?<!data )(?<!signal )(?<!work )"
     r"(?<!information )(?<!traffic )(?<!heat )\bflow(?:s|ing)?\b",
     "hydraulic", "flow"),
    (r"pressure\s+drop|ΔP|\\Delta\s*P|\bdp\b", "hydraulic",
     "pressure_drop"),
    (r"\bviscos(?:ity|ous)\b", "hydraulic", "viscosity"),
    (r"permeab(?:ility|le)", "hydraulic", "permeability"),
    (r"\breynolds\b|\bRe\b(?=\s*[=,<,)]|\bRe\s)", "hydraulic",
     "reynolds"),
    (r"poiseuille|hagen", "hydraulic", "poiseuille"),
    (r"\b(?:pipe|pipes|channel|nozzle|tube|duct|impeller|pump)\w*",
     "hydraulic", "conduit"),
    (r"laminar|turbulen\w+|\bCFD\b|navier[-\s]?stokes", "hydraulic",
     "flow_regime_modeling"),
    (r"\b(?:liquid|fluid|coolant|slurry|water)\b", "hydraulic",
     "working_fluid"),
    (r"\bdarcy\b|ergun", "hydraulic", "darcy"),
    (r"flow[_\s]?(?:rate|velocity|ml|field)|volumetric\s+flow|"
     r"\bvelocity\s+v\b|\bv\b\s*=", "hydraulic", "flow_rate"),
    # ---------------- thermal ----------------
    (r"heat\s+transfer|heat\s+exchang\w*|heat\s+(?:flux|load|"
     r"generation|dissipat\w+|removal|recovery)", "thermal",
     "heat_transfer"),
    (r"thermal(?:\s|_|-)?(?:conductivity|efficiency|energy|management|"
     r"stress|expansion|interface|budget|insulation|performance|"
     r"gradient|field|cycling|design|model|simulation)", "thermal",
     "thermal_quantity"),
    (r"\bNusselt\b|\bNu\b\s*=|convective\s+heat|convection\b|"
     r"conduction\b|\bradiation\b|radiative", "thermal",
     "heat_transfer_mode"),
    (r"\bcooling\b|\bheating\b|\bcooler\b|\bchiller\b|cryogenic|"
     r"refrigerat\w*|evaporat\w*|condens(?:er|ation|e)\b|boiling",
     "thermal", "thermal_process"),
    (r"\btemperature\b|\bT_[ch]\b|\bΔT\b|junction\s+temperature",
     "thermal", "temperature"),
    (r"\bPrandtl\b|\bPr\b\s*=|\bGraetz\b|\bGrashof\b", "thermal",
     "thermal_dimensionless_group"),
    (r"\bCOP\b|coefficient\s+of\s+performance|carnot|"
     r"thermodynamic\w*|entropy|thermal\s+efficiency|η_?(?:thermal|TPV)",
     "thermal", "thermal_efficiency"),
    (r"\btherm\w+", "thermal", "thermal_general"),
    (r"\b(?:steam|waste\s+heat|heat\s+sink|thermal\s+oil)\b", "thermal",
     "thermal_hardware"),
    # ---------------- structural ----------------
    (r"\bstress(?:es)?\b|von\s+mises|\bσ\b|σ_?max|K_?t\b.*stress|"
     r"stress\s+concentration", "structural", "stress"),
    (r"\bstrain\b|elastic(?:ity|\s+modulus)?\b|young'?s?\s+modulus|"
     r"\bE\b\s*=|stiffness|compliance\s+matrix", "structural",
     "strain_elasticity"),
    (r"deflect\w*|deform\w*|displacement\b|\buckl\w+", "structural",
     "deformation"),
    (r"\bforces\b|\bF\b\s*=\s*|bending\s+moment\b|torque",
     "structural", "load"),
    (r"fatigue|endurance\s+limit|s-?n\s+curve|crack\b|fracture",
     "structural", "fatigue_fracture"),
    (r"\bbearing(?:s)?\b|misalign\w*|rotor|shaft|hub|blade\s+root",
     "structural", "machine_element"),
    (r"vibrat\w*|\bmodal\b|resonan\w*|natural\s+frequency",
     "structural", "vibration"),
    (r"(?:mechanical|wind|static|dynamic|bearing|axial|radial|"
     r"structural|bending|contact)\s+loads?\b|"
     r"loads?\s+(?:distribution|capacity|bearing|path)",
     "structural", "mechanical_load"),
    # ---------------- electromagnetic ----------------
    (r"electromagnetic|\bEM\b|eddy\s+current", "electromagnetic",
     "electromagnetic"),
    (r"\bmagnet(?:ic|s)?\b|\bB\b\s+field|flux\s+density|reluctance",
     "electromagnetic", "magnetic"),
    (r"electric(?:al)?\s+(?:field|current|power)|\bvoltage\b|"
     r"\bcurrent\b|\bI\b\s*=", "electromagnetic", "electric"),
    (r"\bPWM\b|\bfsw\b|\bEsw\b|\bPsw\b|\bVdc\b|\bIload\b|inverter|"
     r"switching\s+(?:loss|frequency)|power\s+electronics|converter|"
     r"\bMPPT\b", "electromagnetic", "power_electronics"),
    (r"induct\w*|capacit\w*|impedance|\bRLC\b|circuit\b", "electromagnetic",
     "circuit_elements"),
    (r"\bRF\b|antenna|waveguide|microwave|\bS-?parameters?\b", "electromagnetic",
     "rf"),
    (r"piezoelectric|electroactive|dielectric(?:\s+loss)?|"
     r"electrostrict\w*", "electromagnetic", "electromech_conversion"),
    (r"induction\s+(?:motor|heating|generator)|motor\s+windings|"
     r"generator\b|transformer\b|winding\b", "electromagnetic",
     "electrical_machine"),
    # ---------------- acoustic ----------------
    (r"\bacoustic\w*", "acoustic", "acoustic"),
    (r"ultrason\w*|sonication|sono-?\w*|\bMHz\b|kHz", "acoustic",
     "ultrasonic"),
    (r"\bsound\b|noise\s+(?:level|emission|reduction|control)|"
     r"decibel|\bdB\b", "acoustic", "sound"),
    (r"cavitation|acoustic\s+(?:streaming|field|power|emitter|"
     r"transducer)|resonance\s+driving", "acoustic",
     "acoustic_phenomenon"),
    # ---------------- multibody ----------------
    (r"mechanism\s|linkage|kinemat\w*|\bjoint(?:s)?\b|articulat\w*",
     "multibody", "mechanism_kinematics"),
    (r"actuat\w*|servo|robot\w*|\bmotion\b|trajectory|multibody|"
     r"gimbal|steering", "multibody", "motion_actuation"),
    (r"contact\b|friction(?:\s+coefficient)?|tribolog\w*|\bwear\b|"
     r"abras\w*|lubric\w*|\bmu_s\b|grinding\s+wheel|cutting\s+(?:"
     r"force|speed|tool)", "multibody", "contact_friction"),
    (r"\bmechanical\s+(?:power|energy|advantage)|drivetrain|gear\w*|"
     r"cam\b", "multibody", "mechanical_transmission"),
    # ---------------- soft-body ----------------
    (r"soft\s+(?:body|matter|material|robot\w*)|elastomer\w*|tissue\b|"
     r"hyperelastic|viscoelastic|neo-?hookean|membrane\s+deflect",
     "soft-body", "soft_matter"),
    # ---------------- chemical ----------------
    (r"react(?:ion|or|ivity|ions)?\b|catalys\w*|kinetics\b|"
     r"reaction\s+rate", "chemical", "reaction"),
    (r"adsorpt\w*|desorpt\w*|amine\b|amine-?\w*|sorbent",
     "chemical", "sorption"),
    (r"\bCO2\b|carbon\s+(?:capture|dioxide)|amino\s+acid|"
     r"electrochem\w*|redox|corrosion|oxidative|reductive|synthesis",
     "chemical", "chemistry"),
    (r"chemi(?:cal|stry)|\bmolar\b|molar\s+concentration|"
     r"concentration\s+gradient|chemical\s+concentration|"
     r"\bpH\b|dissolut\w*|precipitat\w*|solution\s+pH",
     "chemical", "chemical_quantity"),
    (r"selectivity\b|yield\s*%|conversion\s*%|reaction\s+(?:order|"
     r"equilibrium)", "chemical", "reaction_metric"),
    # ---------------- optical ----------------
    (r"optical|photonic|laser|lens|fiber[-\s]?optic|mirror\b|prism",
     "optical", "optical_element"),
    (r"wavelength|spectral|spectro\w*|photoluminesc\w*", "optical",
     "spectral"),
    (r"photovoltaic|\bPV\b|solar\s+(?:cell|irradiance|thermal|driven|"
     r"collector)|\bTPV\b|thermophotovoltaic|\bG\b\s*=", "optical",
     "photonic_conversion"),
    (r"\blight\s+(?:source|emission|output|intensity|exposure)",
     "optical", "light"),
])

# ---------------------------------------------------------------------------
# PHENOMENON TERM RULES — evidence linking mechanism text to the
# coverage registry's phenomena (used by the Phase 3 router).
# (pattern, registry phenomenon, term label)
# ---------------------------------------------------------------------------
_PHENOMENON_TERM_RULES = _rules([
    (r"poiseuille|flow\s+network|network\s+flow|flow_ml_min",
     "laminar_incompressible_network_flow", "poiseuille_network"),
    (r"navier[-\s]?stokes|\bCFD\b|incompressible\s+(?:viscous\s+)?"
     r"flow|fluid\s+domain", "incompressible_viscous_flow",
     "navier_stokes"),
    (r"turbulen\w+|\bRANS\b|k-?epsilon|k-?omega", "turbulent_flow",
     "turbulence_modeling"),
    (r"\bNusselt\b|convective\s+heat\s+transfer|heat\s+transfer\s+"
     r"coefficient|\bh\b\s*=\s*|\bNu\b\s*=", "convective_heat_transfer",
     "nusselt_convection"),
    (r"darcy|permeab\w+|porous\w*|ergun", "porous_media_flow",
     "porous_media"),
    (r"\bstress\b|von\s+mises|stress\s+concentration|σ_?max",
     "structural_stress_strain", "stress_analysis"),
    (r"deflect\w*|deform\w*|elastic\s+modulus|strain\b|stiffness",
     "linear_elastic_deformation", "elastic_deformation"),
    (r"thermal\s+(?:stress|expansion|cycling)|CTE|coefficient\s+of\s+"
     r"thermal\s+expansion", "thermal_structural_multiphysics",
     "thermomechanical_coupling"),
    (r"heat\s+equation|conduction\b|thermal\s+conductivity|"
     r"temperature\s+(?:field|gradient)", "heat_transfer",
     "heat_conduction"),
    (r"hyperelastic|soft\s+body|elastomer|neo-?hookean|tissue",
     "soft_body_continuum_mechanics", "soft_body"),
    (r"biomech\w*|patient[-\s]specific|anatom\w*",
     "deformable_biomechanics", "biomechanics"),
    (r"rigid\s+body|collision\b|contact\s+dynamics",
     "rigid_body_contact_dynamics", "rigid_contact"),
    (r"actuat\w*|control\s+law|servo|closed[-\s]loop",
     "actuated_multibody_control", "actuated_control"),
    (r"kinemat\w*|linkage|joint\b|mechanism\s",
     "multibody_mechanisms", "mechanism"),
    (r"vehicle\b|suspension|tire\b|chassis", "vehicle_dynamics",
     "vehicle"),
    (r"friction\b|tribolog\w*|\bwear\b|lubric\w*|contact\b",
     "contact_friction_mechanics", "friction_contact"),
    (r"magnetostatic|magnet\w*|eddy\s+current|induct\w*|coil\b|"
     r"magnetic\s+field", "electromagnetic_fields_lowfreq",
     "low_frequency_em"),
    (r"\bRF\b|antenna|waveguide|microwave|FDTD|S-?parameters?",
     "electromagnetic_fields_highfreq", "high_frequency_em"),
])

_DOMAIN_RULE_TABLE = [
    {"pattern": p.pattern, "domain": d, "term": t}
    for p, d, t in _DOMAIN_TERM_RULES
]
_PHENOMENON_RULE_TABLE = [
    {"pattern": p.pattern, "phenomenon": ph, "term": t}
    for p, ph, t in _PHENOMENON_TERM_RULES
]


def _field_text(fields: Dict[str, Any]) -> Dict[str, str]:
    """Flatten the mechanism's text fields into one text per field
    (lists joined; None-safe)."""
    out: Dict[str, str] = {}
    for name in MECHANISM_TEXT_FIELDS:
        v = fields.get(name)
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            v = " ; ".join(str(x) for x in v if x is not None)
        elif isinstance(v, dict):
            v = json_flatten(v)
        out[name] = str(v)
    return out


def json_flatten(v: Any) -> str:
    import json
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def classify_mechanism(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic classification of one mechanism record.

    Returns a record with:
      domain                — the classification label (one of
                              CLASSIFICATION_LABELS)
      domain_evidence       — {domain: [distinct term labels]}
      strongly_evidenced    — domains with >= 2 distinct terms
      weakly_evidenced      — domains with exactly 1 term
      phenomenon_evidence   — {phenomenon: [distinct term labels]}
      matched_fields        — which mechanism fields produced hits
      rule_provenance       — the closed rule-table sizes
    """
    texts = _field_text(fields)
    domain_terms: Dict[str, List[str]] = {}
    phenomenon_terms: Dict[str, List[str]] = {}
    matched_fields: Dict[str, List[str]] = {}

    for fname, text in texts.items():
        for pat, domain, term in _DOMAIN_TERM_RULES:
            if pat.search(text) and term not in \
                    domain_terms.setdefault(domain, []):
                domain_terms[domain].append(term)
                matched_fields.setdefault(fname, []).append(
                    f"{domain}:{term}")
        for pat, pheno, term in _PHENOMENON_TERM_RULES:
            if pat.search(text) and term not in \
                    phenomenon_terms.setdefault(pheno, []):
                phenomenon_terms[pheno].append(term)

    strong = sorted(d for d, ts in domain_terms.items()
                    if len(ts) >= STRONG_EVIDENCE_MIN_DISTINCT_TERMS)
    weak = sorted(d for d, ts in domain_terms.items()
                  if len(ts) < STRONG_EVIDENCE_MIN_DISTINCT_TERMS)
    if not domain_terms:
        domain = UNKNOWN
    elif len(strong) >= 2:
        domain = MULTIPHYSICS
    elif len(strong) == 1:
        domain = strong[0]
    else:
        domain = weak[0]

    return {
        "domain": domain,
        "domain_evidence": {d: sorted(ts)
                            for d, ts in sorted(domain_terms.items())},
        "strongly_evidenced": strong,
        "weakly_evidenced": weak,
        "phenomenon_evidence": {p: sorted(ts) for p, ts in
                                sorted(phenomenon_terms.items())},
        "matched_fields": matched_fields,
        "rule_provenance": {
            "domain_rules": len(_DOMAIN_TERM_RULES),
            "phenomenon_rules": len(_PHENOMENON_TERM_RULES),
            "strong_evidence_min_distinct_terms":
                STRONG_EVIDENCE_MIN_DISTINCT_TERMS,
            "vocabulary": "closed, general physics terminology "
                          "(pre-registered; see module docstring)",
        },
    }


def verify_proposed_classification(proposal: Dict[str, Any],
                                    fields: Dict[str, Any]
                                    ) -> Dict[str, Any]:
    """THE ART. XVIII GATE (operator directive V2 Phase 3):

    "An LLM may propose a classification, but the registry/rules must
    verify it."

    A proposal {domains: [...], phenomena: [...]} (optionally a
    primary_domain) is VERIFIED only where the deterministic evidence
    independently supports it:
      - every proposed domain must appear in the deterministic domain
        evidence (any term hit);
      - a proposed PRIMARY domain must be the deterministic primary,
        or (for multiphysics classifications) strongly evidenced;
      - every proposed phenomenon must appear in the deterministic
        phenomenon evidence.
    Anything else is REJECTED with machine-readable reasons. The
    verifier NEVER accepts an uncorroborated proposal (fail-closed,
    Art. IV) and NEVER silently amends it.
    """
    cls = classify_mechanism(fields)
    ev = cls["domain_evidence"]
    pev = cls["phenomenon_evidence"]
    reasons: List[str] = []
    verified_domains: List[str] = []
    rejected_domains: List[str] = []
    verified_phenomena: List[str] = []
    rejected_phenomena: List[str] = []

    for d in proposal.get("domains", []) or []:
        if d in ev:
            verified_domains.append(d)
        else:
            rejected_domains.append(d)
            reasons.append(
                f"proposed domain {d!r} has no deterministic term "
                "evidence in the mechanism's own fields — an "
                "uncorroborated proposal is never accepted (Art. IV/"
                "XVIII)")
    for ph in proposal.get("phenomena", []) or []:
        if ph in pev:
            verified_phenomena.append(ph)
        else:
            rejected_phenomena.append(ph)
            reasons.append(
                f"proposed phenomenon {ph!r} has no deterministic term "
                "evidence — the router may only route on verified "
                "phenomena")

    primary = proposal.get("primary_domain")
    primary_ok: Optional[bool] = None
    if primary is not None:
        if primary == cls["domain"]:
            primary_ok = True
        elif primary in cls["strongly_evidenced"]:
            primary_ok = True
            reasons.append(
                f"proposed primary {primary!r} is strongly evidenced "
                "but the deterministic primary is "
                f"{cls['domain']!r} — recorded as a DISCLOSED "
                "divergence, not a rejection (multiphysics "
                "classification)")
        else:
            primary_ok = False
            reasons.append(
                f"proposed primary domain {primary!r} is not the "
                f"deterministic primary {cls['domain']!r} and is not "
                "strongly evidenced — rejected (the deterministic "
                "layer is the selector, Art. XVIII)")

    accepted = (not rejected_domains and not rejected_phenomena
                and primary_ok is not False
                and (verified_domains or verified_phenomena
                     or primary_ok is True))
    return {
        "verdict": "VERIFIED" if accepted else "REJECTED",
        "reasons": reasons,
        "verified_domains": verified_domains,
        "rejected_domains": rejected_domains,
        "verified_phenomena": verified_phenomena,
        "rejected_phenomena": rejected_phenomena,
        "proposed_primary_domain": primary,
        "proposed_primary_verified": primary_ok,
        "deterministic_classification": {
            "domain": cls["domain"],
            "strongly_evidenced": cls["strongly_evidenced"],
        },
        "role_separation": {
            "proposer_role": "LLM PROPOSES domains/phenomena "
                             "(untrusted, Art. XVIII)",
            "verifier_role": "deterministic rule layer (this module; "
                             "zero LLM)",
        },
    }
