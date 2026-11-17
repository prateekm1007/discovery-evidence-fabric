"""discovery_fabric/engine/triz_principles.py — the AM42 D2 TRIZ
seeding table (claim c-0065), migrated from scripts/ into the engine
per the F63 remedy (R52: capability logic lives IN discovery_fabric,
not in script harnesses). Self-encoded classical Altshuller table +
a deterministic contradiction-keyword → principle mapping used to
seed mechanistically distinct candidates. Zero-LLM, zero-network;
typed and testable.

The mapping is deliberately CONSERVATIVE: each mechanism-class keyword
maps to the 2-3 principles the TRIZ literature most strongly
associates with that contradiction family. The machine requires the
selected candidates to carry DISTINCT principles (no two candidates on
one principle) — the principled-diversity bind.
"""
import json
import re
from pathlib import Path

PRINCIPLES = {
    1: "Segmentation", 2: "Taking out", 3: "Local quality",
    4: "Asymmetry", 5: "Merging", 6: "Universality", 7: "Nesting",
    8: "Anti-weight", 9: "Preliminary anti-action", 10: "Preliminary action",
    11: "Beforehand cushioning", 12: "Equipotentiality",
    13: "The other way round", 14: "Spheroidality",
    15: "Dynamics", 16: "Partial or excessive actions",
    17: "Another dimension", 18: "Mechanical vibration",
    19: "Periodic action", 20: "Continuity of useful action",
    21: "Rushing through", 22: "Blessing in disguise", 23: "Feedback",
    24: "Intermediary", 25: "Self-service", 26: "Copying",
    27: "Cheap short-living objects", 28: "Mechanics substitution",
    29: "Pneumatics and hydraulics", 30: "Flexible shells and thin films",
    31: "Porous materials", 32: "Color changes", 33: "Homogeneity",
    34: "Discarding and recovering", 35: "Transformation of properties",
    36: "Phase transitions", 37: "Thermal expansion",
    38: "Strong oxidants", 39: "Inert atmosphere", 40: "Composite materials",
}

# mechanism-class keyword families -> (principles, the class the
# candidate generator targets). ORDER MATTERS: first match wins — the
# mapping table is deterministic and testable.
CONTRADICTION_MAP = [
    (r"thermal load|overheat|scorch|burn|thermal degradation",
     (35, 19, 36), "thermal-load relief"),
    (r"fouling|deposit|scaling|clog",
     (3, 34, 31), "surface-condition management"),
    (r"cavitation|npsh|suction|pump",
     (13, 29, 10), "suction-side conditioning"),
    (r"fatigue|vibration|resonance|crack",
     (18, 1, 31), "dynamic-load dispersal"),
    (r"corrosion|oxidation|rust",
     (39, 30, 40), "interface isolation"),
    (r"moisture|humidity|frost|condensat",
     (32, 36, 30), "moisture-phase management"),
    (r"wear|erosion|abrasion|particle",
     (40, 4, 16), "surface-durability engineering"),
    (r"pressure surge|waterhammer|transient",
     (11, 10, 15), "transient-energy management"),
    (r"seal|leak|gasket|emission",
     (30, 33, 7), "containment integrity"),
    (r"efficiency|energy|consumption|cop",
     (35, 20, 15), "energy-path optimization"),
    (r"contamination|purity|sterile|particle count",
     (3, 24, 34), "contamination-source control"),
    (r"temperature uniformity|gradient|hot spot",
     (3, 14, 37), "thermal-field shaping"),
]

DUTY_CYCLE_FAMILY_RX = re.compile(
    r"duty[- ]?cycle|schedul\w*|periodic\w*|setpoint[ -]?(modulat|retun)"
    r"|cyclic\w*|interval\w*|puls\w*", re.I)


# ---------------------------------------------------------------------------
# R53 (claim c-0073, ROADMAP P2.1): the FULL corpus — 40 principles with
# self-authored descriptions/examples + the classical 39x39 Altshuller
# contradiction matrix — lives in discovery_fabric/engine/triz_matrix.json
# (our own JSON; the MIT-licensed SharathSPhD/triz-engine data was the
# machine-checkable cross-check for the matrix cells — NOTICE.md carries
# the attribution). The 12-family keyword map above STAYS the fast path
# (seed_for is untouched — committed regressions and plan populations
# stay byte-stable); the matrix becomes the PRINCIPLED RESOLVER used by
# the P2 typed-operator population.
# ---------------------------------------------------------------------------
CORPUS_PATH = Path(__file__).resolve().parent / "triz_matrix.json"
_CORPUS_CACHE: dict | None = None


def load_corpus() -> dict:
    """The full TRIZ corpus (cached). {principles[], parameters[],
    matrix{improving_worsening: [principle ids]}, provenance, stats}."""
    global _CORPUS_CACHE
    if _CORPUS_CACHE is None:
        _CORPUS_CACHE = json.loads(CORPUS_PATH.read_text(
            encoding="utf-8"))
    return _CORPUS_CACHE


def resolve_contradiction(improving: int, worsening: int) -> list:
    """The classical matrix cell for (improving, worsening) parameter
    ids: the recommended principle ids, best-first order preserved.
    TYPED degenerate cases return [] (never a fallback guess): unknown
    ids, non-ids, or improving == worsening (a parameter against itself
    is not a contradiction)."""
    if not (isinstance(improving, int) and isinstance(worsening, int)):
        return []
    if not (1 <= improving <= 39 and 1 <= worsening <= 39):
        return []
    if improving == worsening:
        return []
    return list(load_corpus()["matrix"].get(
        f"{improving}_{worsening}", []))


# deterministic problem-text -> engineering-parameter hints (our own
# keyword table; the FIRST matching hint per side wins — same ordering
# discipline as CONTRADICTION_MAP)
PARAM_HINTS_IMPROVING = [
    (r"throughput|productivity|output rate|capacity", 39),
    (r"speed|velocity|faster|rate of", 9),
    (r"reliab\w*|uptime|availability|mtbf", 27),
    (r"strength|load-bearing|structural integrity", 14),
    (r"efficien\w*|energy consumption|energy use|cop", 19),
    (r"power density|power output", 21),
    (r"measurement|sensing|monitoring|detection", 28),
    (r"automation|unattended", 38),
]
PARAM_HINTS_WORSENING = [
    (r"energy (loss|waste|penalty)|friction loss|parasitic", 22),
    (r"emission|pollut\w*|harmful|noise|mist|aerosol|waste heat", 31),
    (r"corros\w*|erosion|wear|fouling|scaling|deposit|clog", 30),
    (r"fatigue|crack|vibration|resonance|transient|surge", 30),
    (r"temperature|thermal|heat|overheat|scorch|burn", 17),
    (r"stress|pressure|force|load", 11),
    (r"complexity|parts count|assembly", 36),
    (r"cost|expense|downtime|maintenance", 25),
    (r"material (loss|consumption)|leak|spill", 23),
    (r"weight|mass", 1),
    (r"time|duration|delay|cycle time", 25),
    (r"information|data (loss|gap)|observability", 24),
]


def contradiction_for(problem_text: str) -> dict:
    """The P2 resolver: problem text -> the typed contradiction pair +
    the matrix's candidate principles. Deterministic, zero-LLM. When no
    hint matches a side the field is None (typed — the caller falls back
    to the CONTRADICTION_MAP fast path; a missing parameter is never
    guessed)."""
    low = problem_text.lower()
    imp = wid = None
    for rx, pid in PARAM_HINTS_IMPROVING:
        if re.search(rx, low):
            imp = pid
            break
    for rx, pid in PARAM_HINTS_WORSENING:
        if re.search(rx, low):
            wid = pid
            break
    principles = (resolve_contradiction(imp, wid)
                  if imp is not None and wid is not None else [])
    return {"improving": imp, "worsening": wid,
            "principles": principles,
            "principle_names": [PRINCIPLES[p] for p in principles
                                if p in PRINCIPLES]}


def seed_for(problem_text: str) -> tuple:
    """Deterministic: (principle_ids, target_class) for the FIRST
    contradiction family matching the problem; (None, None) when no
    family matches (typed — the candidate generator then falls back to
    the machine's own candidate-class enumeration)."""
    low = problem_text.lower()
    for rx, principles, cls in CONTRADICTION_MAP:
        if re.search(rx, low):
            return principles, cls
    return None, None


def distinct_principles(seeds: list) -> bool:
    """The principled-diversity bind: no two candidate seeds share a
    primary principle."""
    primaries = [s[0][0] for s in seeds if s and s[0]]
    return len(primaries) == len(set(primaries))


__all__ = ["PRINCIPLES", "CONTRADICTION_MAP", "seed_for",
           "distinct_principles", "DUTY_CYCLE_FAMILY_RX",
           "load_corpus", "resolve_contradiction",
           "contradiction_for"]
