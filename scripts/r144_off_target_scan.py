#!/usr/bin/env python3
"""r144_off_target_scan.py — the OFF-TARGET bind (R144 DIR-3 lever
(c), claim c-0243, the R143-F7 remedy). Deterministic, no LLM.

The measured defect (the 8 v16 off-target rows): the delivered
mechanism acts on physics that CANNOT address the stated failure
mode — chemical cathodic protection for GRIT ABRASION, flow-modulation
for TRAMP METAL, monitoring for NUCLEATION, passive insulation
against nucleation-driven collapse. The failure-mode map (lever (a),
discovery_fabric/engine/failure_mechanism_map.py) fixes the PLAN
layer; this scan types the TEXT layer — the delivered mechanism's
own vocabulary must not be an ANTI-class mechanism for the detected
failure family.

Typed lexical net (structural vocabulary, closed classes — the Art.
XXV convention): the scan fires ONLY when (1) a failure family is
detected, (2) the delivered mechanism vocabulary matches that
family's ANTI-class mechanism vocabulary, and (3) no ADMITTED-class
mechanism vocabulary co-occurs (the invention names an on-physics
mechanism too — no false fire). Findings feed the neutral repair
directive; never silent, never a bar change.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from discovery_fabric.engine.failure_mechanism_map import (  # noqa: E402
    FAILURE_FAMILY_LEXICON)

# the delivered-mechanism sections (the V4 NOVELTY STATEMENT +
# IMPLEMENTATION BILL carry the mechanism prose; fall back to the
# whole answer when neither section header is present)
# the mechanism-DEFINING section only (the NOVELTY STATEMENT) —
# the EXECUTABLE TEST's instruments and the IMPLEMENTATION BILL's
# procurement rows are not the mechanism (the v16-26 lesson: a
# high-speed camera as a test instrument fired the anti-net while
# the mechanism itself was on-physics)
_MECH_SECTION = re.compile(
    r"NOVELTY\s+STATEMENT[^\n]*(.*?)"
    r"(?=PHYSICS\s+CHECK|IMPLEMENTATION\s+BILL|BURDEN\s+LEDGER"
    r"|EXECUTABLE\s+TEST|\Z)",
    re.I | re.S)

# per failure family: (admitted-mechanism vocabulary, anti-class
# mechanism vocabulary) — the TEXT-level physics vocabulary of the
# mechanism CLASSES the family admits/excludes. Structural, closed
# word classes; derived from the same failure physics as the map.
FAMILY_MECHANISM_VOCAB = {
    "abrasion_erosion": (
        # admitted: material/geometry/boundary mechanics (harder
        # facing, lubricant FILM geometry, load spreading)
        re.compile(r"hard(?:er)?\s+facing|face\s+material|bearing\s+"
                   r"material|composite\s+(?:bearing|liner)|self-"
                   r"lubricat\w+|lubricant\s+(?:film|layer|groove)"
                   r"|load\s+(?:spread|distribut\w+)|contact\s+"
                   r"pressure|hydrodynamic\s+(?:film|lift)|surface\s+"
                   r"hardness|runout\s+clearance|shaft\s+alignment",
                   re.I),
        # anti: electrochemical/corrosion-inhibition mechanisms
        re.compile(r"cathodic\s+protection|sacrificial\s+anode|"
                   r"impressed\s+current|passivat\w+|corrosion\s+"
                   r"inhibit\w*|potential\s+(?:vs|relative)|pH\s+"
                   r"(?:suppress|control|adjust)|micro-?galvanic",
                   re.I)),
    "foreign_object": (
        # admitted: physical separation/extraction/reconfiguration
        re.compile(r"magnet\w*|detector|separator|diverter|skimmer|"
                   r"screende?ck|grizzly|chute\s+(?:angle|geometry)|"
                   r"transfer\s+(?:point\s+)?(?:geometry|realign)"
                   r"|belt\s+(?:tracker|alignment|training)|drop\s+"
                   r"height|impact\s+(?:bed|cradle|idler)", re.I),
        # anti: chemistry mechanisms on an inert metal object
        re.compile(r"dosing|additive|inhibit\w+|coagul\w+|floccul\w+"
                   r"|surfactant|pH\s+adjust|chemical\s+treatment",
                   re.I)),
    "nucleation_phase_change": (
        # admitted: acting AT the nucleation event (seeding, controlled
        # cooling, nucleation-agent chemistry, energy-input schedules)
        re.compile(r"seed\w*|nucleat\w+(?:\s+agent)?|controlled\s+"
                   r"(?:cooling|freez\w+|solidif\w+)|ramp(?:ing)?\s+"
                   r"rate|anneal\w*|hold\s+(?:temperature|time)|"
                   r"supercool\w*|ice\s+(?:structure|modifier)|"
                   r"induced\s+nucleation|thermal\s+profile|shelf\s+"
                   r"(?:temperature|ramp)", re.I),
        # anti: monitoring/indication schemes that watch nucleation
        re.compile(r"monitor\w*|indicat\w+|detect\w+|alarm|threshold"
                   r"\s+alert|camera|sensor\s+(?:network|array)|"
                   r"predictive\s+maintenance", re.I)),
    "residual_stress_distortion": (
        # admitted: stress management (thermal profiles, preheat/
        # post-heat, scan strategy = duty/geometry of the energy
        # input, constraint fixtures)
        re.compile(r"preheat\w*|post-?(?:heat|weld)\s+(?:treatment|"
                   r"soak)|stress\s+relie\w+|scan\s+strategy|build\s+"
                   r"orientation|layer\s+(?:thickness|sequence)|"
                   r"thermal\s+(?:profile|gradient\s+control)|"
                   r"constraint\w*|fixture\s+(?:pre-?load|stiffness)",
                   re.I),
        # anti: chemistry/corrosion mechanisms
        re.compile(r"coating\s+application|chemical\s+(?:treatment|"
                   r"inhibit)|passivat\w+|dosing", re.I)),
    "thermal_attack_surface": (
        # admitted: film cooling, thermal barriers, flow-field
        # geometry at the attacked surface, duty derates
        re.compile(r"film\s+cooling|cooling\s+(?:film|hole|channel)"
                   r"|thermal\s+(?:barrier|coating\s+of\s+the\s+"
                   r"attacked)|backside\s+cool\w*|convective\s+"
                   r"(?:cooling|heat\s+removal)|recirculation\s+"
                   r"(?:zone|pocket)\s+(?:geometry|elimination)"
                   r"|injector\s+(?:face|pattern)\s+(?:geometry|"
                   r"recess)|derate\w*", re.I),
        # anti: monitoring the burn
        re.compile(r"monitor\w*|indicat\w+|detect\w+|thermocouple\s+"
                   r"array|pyrometer|alarm", re.I)),
    "diffusion_intermetallic": (
        # admitted: diffusion barriers, interface materials, bonding
        # geometry, temperature duty
        re.compile(r"diffusion\s+barrier|barrier\s+(?:layer|metal)"
                   r"|nickel\s+(?:plating|barrier)|palladium\s+"
                   r"(?:plating|flash)|bond\s+(?:line|geometry|"
                   r"thickness)|wire\s+material|metalliz\w+|"
                   r"(?:bonding|process)\s+temperature\s+(?:profile|"
                   r"cycle)|duty\s+(?:temperature|derate)", re.I),
        # anti: monitoring the void growth
        re.compile(r"monitor\w*|indicat\w+|detect\w+|nondestructive"
                   r"\s+test\w*|shear\s+test\s+(?:sampling|program)",
                   re.I)),
    "particle_attachment": (
        # admitted: chemistry at the bubble-particle interface,
        # hydrodynamic duty, cell geometry
        re.compile(r"collect\w+\s+(?:agent|chemistry|dos\w+)|frother"
                   r"\w*|surface\s+(?:tension|hydrophobicity)|"
                   r"contact\s+angle|gas\s+(?:rate|holdup|dispersion)"
                   r"|impeller\s+(?:speed|geometry)|cell\s+(?:duty|"
                   r"geometry)|conditioning\s+(?:time|intensity)",
                   re.I),
        None),
    "granular_channeling": (
        # admitted: redistribution geometry, duty schedules,
        # boundary control at the grate
        re.compile(r"redistribut\w+|spreader|grate\s+(?:geometry|"
                   r"opening|pattern)|air\s+(?:distribution|knife)|"
                   r"baffl\w+|bed\s+(?:depth|height)\s+control|"
                   r"clinker\s+(?:flow\s+)?distribut\w+|duty\s+"
                   r"(?:cycle|schedule)", re.I),
        None),
    "thermal_fatigue_crack": (
        re.compile(r"thermal\s+(?:expansion\s+)?(?:compensat\w+|"
                   r"accommodat\w+)|flexib\w+\s+(?:joint|mount|"
                   r"hanger)|damping\s+mount|stress\s+concentration"
                   r"\s+reduc\w+|radius|fillet|bellows|slip\s+joint",
                   re.I),
        None),
    "mechanical_overload": (
        re.compile(r"reinforc\w+|strengthen\w+|load\s+(?:path|limit)"
                   r"|guard\s+beam|rip\s+detection|reinforcement|"
                   r"impact\s+(?:resistance|bed)", re.I),
        None),
}

# families where the ANTI mechanism vocabulary lives in the map's
# anti-class list only (no text-level anti net) -> no text scan
_FAMILY_TEXT_ANTIS = {
    "abrasion_erosion", "foreign_object", "nucleation_phase_change",
    "residual_stress_distortion", "thermal_attack_surface",
    "diffusion_intermetallic",
}


def scan_off_target(prob: dict, a: str) -> dict:
    """The off-target typed finding for one answer: the delivered
    mechanism is an ANTI-class mechanism for the stated failure
    family. Deterministic; fires only on the three-condition
    conjunction (family detected + anti-vocabulary hit + NO admitted
    vocabulary co-occurrence)."""
    txt = " ".join(str(prob.get(k) or "") for k in
                   ("failure", "failure_mode", "problem", "question"))
    from discovery_fabric.engine.failure_mechanism_map import (
        detect_failure_family)
    fam = detect_failure_family({"failure": txt, "failure_mode": txt,
                                 "problem": txt, "question": ""})
    if fam is None or fam not in _FAMILY_TEXT_ANTIS:
        return {}
    adm_rx, anti_rx = FAMILY_MECHANISM_VOCAB.get(fam, (None, None))
    if anti_rx is None:
        return {}
    mech_parts = []
    for m in _MECH_SECTION.finditer(a):
        mech_parts.append(m.group(1) or "")
    mech = "\n".join(mech_parts) or a
    anti_hit = anti_rx.search(mech)
    adm_hit = adm_rx.search(mech) if adm_rx else None
    if anti_hit and not adm_hit:
        return {"OFF_TARGET_MECHANISM": [
            f"the stated failure family is {fam}; the delivered "
            f"mechanism vocabulary (\"{anti_hit.group(0)[:80]}\") "
            f"acts on physics that cannot address the stated failure "
            f"mode — recompose on the family's admitted mechanism "
            f"classes (the plan conditioning names them)"]}
    return {}
