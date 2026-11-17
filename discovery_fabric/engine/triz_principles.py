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
           "load_matrix", "matrix_principles"]


# ---------------------------------------------------------------------------
# The classical contradiction-matrix layer (P2, claim c-0071): the full
# 39 engineering parameters x 39 -> recommended-principle lists, landed
# as our own JSON under the MIT NOTICE (see NOTICE-triz-engine). The
# CONTRADICTION_MAP above stays the problem-text keyword layer; this
# matrix is the typed engineering-parameter layer.
# ---------------------------------------------------------------------------
_DATA_PATH = Path(__file__).resolve().parent / "data" /     "triz_classical_matrix.json"
_MATRIX_CACHE = None


def load_matrix() -> dict:
    """The full classical matrix record (cached). Raises a typed
    error naming the file when the data file is missing — a missing
    data file never degrades into a fabricated recommendation."""
    global _MATRIX_CACHE
    if _MATRIX_CACHE is None:
        if not _DATA_PATH.exists():
            raise FileNotFoundError(
                f"TRIZ matrix data missing: {_DATA_PATH}")
        _MATRIX_CACHE = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    return _MATRIX_CACHE


def matrix_principles(improving: int, worsening: int) -> list:
    """Recommended principle ids for the (improving, worsening)
    parameter pair. Unknown parameters raise a typed error; an empty
    cell returns [] (the classical matrix has no diagonal entries)."""
    if improving not in range(1, 40) or worsening not in range(1, 40):
        raise ValueError(
            f"engineering parameters must be 1..39, got "
            f"({improving}, {worsening})")
    return list(load_matrix()["matrix"].get(f"{improving}_{worsening}",
                                            []))
