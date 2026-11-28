"""discovery_fabric/engine/failure_mechanism_map.py — the R144 DIR-3
lever: the failure-mode -> mechanism-class MAP (R143-F7's remedy).

The measured defect (from the committed v16 bytes, the 8 off-target
rows): the plan layer's operator-affinity table ordered the population
by a BLIND preference (DIRECT_TRANSFER -> configuration), so the
generator was plan-conditioned onto mechanism classes that contradict
the stated failure physics — chemical cathodic protection for GRIT
ABRASION, flow-modulation for TRAMP METAL removal, monitoring for
NUCLEATION control, passive insulation against nucleation-driven
collapse. The inventions followed the conditioning.

This module maps the stated failure mode to the mechanism classes
whose physics can actually act on that failure mode, and — as
important — carries the EXCLUDED classes per failure family (the
anti-classes): a plan whose measure_class is excluded for the
detected failure family is ordered AFTER plans whose class is
admitted. The pre-registered winner rule ("first contract-satisfied
non-duty_cycle plan in population order") stays BYTE-IDENTICAL; the
MAP only reorders the population it reads from — the same lever shape
as the AM63 chemistry elicitation (order, never rewrite).

The lexicon is deterministic and STRUCTURAL (failure-physics
vocabulary, closed word classes — the Art. XXV convention: no
corpus-word blacklists, no silent clamps). Every mapping is tagged
on the plan (map_source) — the reorder is measured, never assumed.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# The failure-physics lexicon: (family, detector regex, admitted
# classes, anti-classes). A problem matches a family when its failure
# text (failure + failure_mode + problem statement) hits the
# detector. Families are checked in order; the FIRST match wins
# (failure-physics specificity, not a vote).
#
# The classes are the engine's own measure_class enum
# (population_search.MEASURE_CLASSES) — no new claim kinds.
#
# Anti-classes are the measured off-target shapes: the class whose
# physics CANNOT act on the stated failure mode as stated. An
# anti-class plan is DEMOTED (ordered last, flagged), never deleted
# (the plan space is unchanged — the F54 monoculture kill stays the
# only plan-removal rule, and it is not one).
# ---------------------------------------------------------------------------
FAILURE_FAMILY_LEXICON: List[Tuple[str, re.Pattern, Tuple[str, ...],
                                  Tuple[str, ...]]] = [
    # -- deposition / fouling / scaling (R144s1 extension: the fresh
    #    v17 vocabulary — evap scale, slag shedding, EGR soot, MBR
    #    fouling; BEFORE abrasion so the DEPOSITION CAUSE routes, not
    #    the erosion SYMPTOM of the same row; chemistry admitted —
    #    the AM63 elicitation semantics, typed here)
    ("deposition_fouling",
     re.compile(r"\bfoul\w*|\bscal(?:e|es|ing|ed)\b|\bdeposit\w*|"
                r"\bbiofilm\w*|\bslag\w*|\bcoke(?:s|d|ing)?\b|"
                r"\bsoot\b|\bplugg(?:ing|ed|es)?\b", re.I),
     ("chemistry", "geometry", "configuration", "duty_cycle"),
     ("control",)),
    # -- mechanical clogging / blinding (R144s1 extension: sticky
    #    fines, clay, kinked tubing occlusion — the DEBRIS is
    #    mechanical, geometry leads, distinct from deposition
    #    chemistry above)
    ("mechanical_clogging",
     re.compile(r"\bclog(?:s|ging|ged)?\b|\bblind(?:s|ing|ed)?\b|"
                r"\bocclud\w*", re.I),
     ("geometry", "configuration", "chemistry"),
     ("control",)),
    # -- electrochemical corrosion (R144s1 extension: the v16-19
    #    pickling class had no family; corrode/corrosion verb+noun
    #    forms; AFTER abrasion is not needed — abrasion sits above
    #    via "fretting", the v16-18 shape)
    ("electrochemical_corrosion",
     re.compile(r"\bcorrod(?:e|es|ed|ing)\b|\bcorrosion\b|"
                r"galvanic\w*|\boxidiz(?:e|es|ed|ing)\b|"
                r"\brust(?:ing)?\b|\bover-?pickl\w*|\bsplash[- ]zone\b",
                re.I),
     ("chemistry", "material", "geometry"),
     ("control",)),
    # -- mechanical removal of surface material (the v16-02 class:
    #    chemical CP for abrasion — the anti-class). R144s1: the VERB
    #    forms (erodes/erode — "eros" is not a substring of "erodes")
    #    and the rolling-contact shapes (shelling, squatting, pitting)
    #    join the detector.
    ("abrasion_erosion",
     re.compile(r"\babras\w*|\berod(?:e|es|ed|ing)\b|\beros\w*|"
                r"scour\w*|wear(?:ing)?\b|"
                r"fretting|galling|scuffing|polishing\s+(?:of\s+)?"
                r"(?:the\s+)?(?:bearing|surface)|tribolog\w*|"
                r"third-body\s+particles?|grit\b|"
                r"\bshelling\b|\bshells\b|"
                r"\bsquat(?:s|ting|ted)?\b|"
                r"\bpit(?:s|ted|ting)?\b|"
                r"rolling\s+contact\s+fatigue", re.I),
     ("material", "geometry", "boundary", "configuration"),
     ("chemistry", "control")),
    # -- trapped foreign objects (the v16-03 class: flow-modulation
    #    for tramp metal — the anti-class)
    ("foreign_object",
     re.compile(r"tramp\s+metal|foreign\s+(?:object|material|debris)"
                r"|\btrapped\s+(?:object|debris|metal)|entrap\w*|"
                r"jam(?:s|ming|med)?\s+(?:by|with)\s+(?:metal|debris)"
                r"|contaminant\s+(?:lump|chunk|piece)", re.I),
     ("geometry", "configuration", "control", "material"),
     ("chemistry",)),
    # -- phase-change / nucleation physics (the v16-05 class:
    #    monitoring or passive insulation for nucleation — both
    #    anti-classes; the physics acts AT the nucleation event)
    ("nucleation_phase_change",
     re.compile(r"nucleat\w*|ice\s+crystal|freez\w*|solidif\w+|"
                r"re-crystalliz\w*|recrystalliz\w*|crystalliz\w*|"
                r"cake\s+collapse|supercool\w*|dendrite\s+growth|"
                r"phase\s+change", re.I),
     ("boundary", "duty_cycle", "configuration", "chemistry",
      "material"),
     ("control",)),
    # -- trapped residual stress (the v16-07 class: generic
    #    configuration for stress relief — the physics class is
    #    boundary/thermal or geometry, not blind reconfiguration)
    ("residual_stress_distortion",
     re.compile(r"residual\s+stress|distort\w*|warp\w*|spring-?back"
                r"|stress\s+(?:relief|redistribut\w+|concentrat\w+)"
                r"|thermal\s+gradient\s+stress|layer-?by-?layer\s+"
                r"(?:stress|distortion)", re.I),
     ("boundary", "duty_cycle", "geometry", "material"),
     ("chemistry", "control")),
    # -- hot-gas / thermal anchoring at a surface (the v16-23 class:
    #    monitoring for a burn — the anti-class). R144s1: the thermal
    #    dry-out shapes (electrolytic capacitors, grease depletion at
    #    tilt temperature) join the detector.
    ("thermal_attack_surface",
     re.compile(r"burn(?:s|ing|ed|out)?\b|hot[- ]gas|recirculat\w+\s+"
                r"(?:hot|combust)|flame\s+(?:hold|anchor|impinge)"
                r"|thermal\s+(?:attack|soak|spike)|heat\s+flux\s+"
                r"(?:to|on)\s+the\s+(?:face|wall|surface)|"
                r"red-?hot|"
                r"\bdry(?:ing)?\s+out\b|\bdry-?out\b|"
                r"\bbacklash\b|\bgrease\s+dri(?:es|ed|ing)\b|"
                r"\btraveler\s+heat\b", re.I),
     ("boundary", "geometry", "configuration", "material",
      "duty_cycle"),
     ("control",)),
    # -- liquid slugging / carryover / oil return (R144s1 extension:
    #    the v16-10 class and the fresh oil-logging vocabulary — the
    #    physics is two-phase return management)
    ("phase_carryover_liquid",
     re.compile(r"\bslug(?:ging|ged|s)?\b|liquid\s+(?:floodback|"
                r"carryover)|oil\s+logg(?:ing|ed)\b|oil\s+return\b|"
                r"\bpriming\b", re.I),
     ("geometry", "configuration", "boundary"),
     ("control",)),
    # -- seal / containment loss-of-condition (R144s1 extension: the
    #    v16-15 dry-running class and leak vocabulary)
    ("seal_leak_integrity",
     re.compile(r"\bleak(?:s|ing|ed)?\b|seal(?:s)?\s+(?:fail|leak|"
                r"degrad)|dry-?run\w*|loss\s+of\s+(?:seal|containment)",
                re.I),
     ("configuration", "geometry", "material"),
     ("control",)),
    # -- diffusion / intermetallic growth (the v16-25 class: the
    #    physics is diffusion-rate or interface-chemistry control)
    ("diffusion_intermetallic",
     re.compile(r"kirkendall|intermetallic\w*|diffusion\s+(?:flux|"
                r"rate|couple|void|barrier)|void\w*\s+(?:at|on)\s+"
                r"(?:the\s+)?(?:bond|interface)|interdiffus\w*", re.I),
     ("material", "boundary", "geometry"),
     ("control",)),
    # -- particle-bubble attachment physics (the v16-27 class: the
    #    hydrodynamic/attachment balance IS the failure physics)
    ("particle_attachment",
     re.compile(r"detachment\b|detach\w*|coarse[- ]particle|"
                r"particle[- ]bubble|bubble[- ]particle|"
                r"froth\s+(?:stability|drainage)|attachment\s+"
                r"(?:efficiency|force|probability)", re.I),
     ("chemistry", "duty_cycle", "geometry", "configuration"),
     ()),
    # -- channeled flow of hot granular material (the v16-13 class)
    ("granular_channeling",
     re.compile(r"channel\w*\s+(?:of|through)|river\w*\s+channel"
                r"|rathol\w*|granular\s+(?:flow|redistribut)"
                r"|clinker\s+cooler|grate\s+plate", re.I),
     ("geometry", "configuration", "duty_cycle", "boundary"),
     ("control",)),
    # -- fatigue cracking from thermal/mechanical cycling (the
    #    v16-01 class, which scored 3 — the map must keep it sound).
    #    R144s1: the crack-site vocabulary widens (bead/ligament/
    #    seam/root/fillet) and heat-cycling joins the detector.
    ("thermal_fatigue_crack",
     re.compile(r"thermal\s+(?:fatigue|cycling|shock)|crack\w*\s+"
                r"(?:at|from|near)\s+(?:clamp|weld|joint|notch|bead|"
                r"ligament|seam|root|fillet|sheave)"
                r"|cyclic\s+(?:thermal|stress)|low-?cycle\s+fatigue|"
                r"\bheat\s+cycl\w*|thermal\s+cycling",
                re.I),
     ("geometry", "material", "boundary", "duty_cycle",
      "configuration"),
     ()),
    # -- generic mechanical overload / tear / rip (the fallback
    #    mechanical family). R144s1: plain "fatigue", wire breaks and
    #    friction slip join the fallback (checked AFTER the specific
    #    families by list order).
    ("mechanical_overload",
     re.compile(r"\brip(?:s|ping|ped)?\b|\btear(?:s|ing|ing)?\b|"
                r"overload|tensile\s+failure|impact\s+(?:damage|"
                r"load)|mechanical\s+shock|"
                r"\bbreak(?:s|age|ing)?\b|\bfatigue\b|"
                r"\bslip(?:s|ping|ped)?\b", re.I),
     ("geometry", "material", "configuration", "control"),
     ()),
]

_FAMILY_CACHE: dict = {}


def detect_failure_family(problem: dict) -> Optional[str]:
    """The problem's failure family from its own text (failure +
    failure_mode + problem statement), or None when no family
    detector hits (the map is ADDITIVE: no detection means NO
    reorder — population_search's own ordering stands, Art. XXV)."""
    txt = " ".join(str(problem.get(k) or "") for k in
                   ("failure", "failure_mode", "problem", "question"))
    txt = txt[:4000]
    for fam, rx, _, _ in FAILURE_FAMILY_LEXICON:
        if rx.search(txt):
            return fam
    return None


def family_classes(family: Optional[str]) -> Tuple[Tuple[str, ...],
                                                    Tuple[str, ...]]:
    """(admitted, anti) classes for a family; empty tuples when the
    family is unknown (no-op contract)."""
    if family is None:
        return (), ()
    for fam, rx, adm, anti in FAILURE_FAMILY_LEXICON:
        if fam == family:
            return adm, anti
    return (), ()


def mechanism_class_fit(problem: dict, measure_class: str) -> dict:
    """The plan-layer fit record for one (problem, measure_class):
    does the stated failure physics admit this class? Structural,
    deterministic, tagged — the reorder consumes `rank`, the record
    rides the plan's map_source for measurement."""
    fam = detect_failure_family(problem)
    if fam is None:
        return {"family": None, "admitted": None, "rank": 0,
                "basis": "no failure-family detection — no reorder "
                         "(the engine's own ordering stands)"}
    adm, anti = family_classes(fam)
    if measure_class in adm:
        # rank by POSITION in the admitted tuple — the family's own
        # physics priority (e.g. foreign_object: geometry [physical
        # separation] before configuration [procedural]; the v16
        # off-target inventions came from generic-configuration
        # conditioning on families whose physics leads elsewhere)
        return {"family": fam, "admitted": True,
                "rank": adm.index(measure_class),
                "basis": f"{measure_class} is admitted class #"
                         f"{adm.index(measure_class) + 1} for the "
                         f"{fam} failure physics"}
    n_adm = len(adm)
    if measure_class in anti:
        return {"family": fam, "admitted": False, "rank": n_adm + 1,
                "basis": f"{measure_class} is an ANTI-class for the "
                         f"{fam} failure physics — its mechanism "
                         f"cannot act on the stated failure mode"}
    # neither admitted nor excluded: neutral, ranks after ALL
    # admitted classes but before the anti-classes
    return {"family": fam, "admitted": None, "rank": n_adm,
            "basis": f"{measure_class} is not an admitted class for "
                     f"the {fam} failure physics (demoted below the "
                     f"admitted classes, not excluded)"}
