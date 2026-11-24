"""R144 generation strength — DIR-8 lever: MOOSE-Chem-style inspiration
retrieval, integrated into the problem-aware selection stage.

The lever: before the generator proposes a mechanism, RETRIEVE
inspiration — (1) evidence spans from the frozen evidence corpus
(hash-verified: content_hash + verbatim span, the FullCite shape) and
(2) cross-domain analogies from a typed analogy table. The retrieved
context is injected into the mechanism-selection prompt, so the
selection is evidence- and precedent-grounded rather than blind.

Import-graph evidence: this module is imported by the strengthened
runner (scripts/r144s1_strength_run.py) and by the engine's machine
wiring — the integration is visible in the import graph
(tests/test_generation_strength.py pins it).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Typed cross-domain analogy table (the MOOSE-Chem "inspiration"
# pattern at engineering scale): a failure class retrieves analogies
# from OUTSIDE its own domain; each analogy names a real, checkable
# precedent — no invented cases.
CROSS_DOMAIN_ANALOGIES = {
    "abrasion_erosion": [
        {"from_domain": "aerospace", "precedent": ("helicopter rotor "
         "rain-erosion elastomer boots — the compliant-layer mechanism"),
         "transfer": ("a low-modulus polyurethane layer absorbs the "
                      "droplet/particle stress peak")},
        {"from_domain": "mineral processing", "precedent": ("slurry "
         "pump impellers with sacrificial ceramic inserts"),
         "transfer": ("move the wear site to a renewable element")},
    ],
    "fouling_deposition": [
        {"from_domain": "biomimetics", "precedent": ("carnivorous-plant "
         "SLIPS surfaces — slippery liquid-infused porous films"),
         "transfer": ("infuse a textured surface with an immiscible "
                      "lubricant so foulants do not adhere")},
        {"from_domain": "marine engineering", "precedent": ("ultrasonic "
         "antifouling transducers on hulls"),
         "transfer": ("acoustic microstreaming detaches early-stage "
                      "biofilms without biocides")},
    ],
    "nucleation_phase_change": [
        {"from_domain": "pharmaceutical processing", "precedent": (
            "sonocrystallization — ultrasonic nucleation control"),
         "transfer": ("trigger nucleation ON DEMAND instead of "
                      "stochastic supercooling bursts")},
        {"from_domain": "thermal engineering", "precedent": (
            "engineered boiling surfaces (reentrant cavities)"),
         "transfer": ("pin the nucleation sites and the onset "
                      "temperature")},
    ],
    "contamination_separation": [
        {"from_domain": "recycling", "precedent": ("eddy-current "
         "separators for non-ferrous metals"),
         "transfer": ("a time-varying field repels conductive tramp "
                      "without contact")},
        {"from_domain": "food processing", "precedent": ("self-cleaning "
         "rotating drum screens"),
         "transfer": ("continuous screen cleaning prevents the "
                      "clog-death spiral")},
    ],
    "corrosion_chemical": [
        {"from_domain": "offshore energy", "precedent": ("ICCP systems "
         "with distributed anodes sized to current demand"),
         "transfer": ("active potential control beats passive "
                      "coatings alone")},
        {"from_domain": "water treatment", "precedent": ("film-forming "
         "inhibitor programs at ppm dosing"),
         "transfer": ("nanoscale barrier films cut the corrodant flux")},
    ],
}


def _frozen_evidence_spans(failure_class: str, corpus_path: str = "",
                           max_spans: int = 3) -> list:
    """Retrieve verbatim inspiration spans from a committed corpus file
    (the frozen evidence custody). Hash-verified: each span carries
    sha256[:16] of its content (the FullCite shape). corpus_path is a
    REPO-relative committed file; a missing/unreadable corpus is a
    typed empty result, never an invented span."""
    spans = []
    p = REPO / corpus_path if corpus_path else None
    if not p or not p.exists():
        return spans
    try:
        raw = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return spans
    keys = json.loads(json.dumps(
        __import__("discovery_fabric.generation.mechanism_map",
                   fromlist=["FAILURE_CLASSES"])
        .FAILURE_CLASSES[failure_class]["keywords"]))
    paras = [x.strip() for x in raw.split("\n\n") if len(x.strip()) > 120]
    for para in paras:
        low = para.lower()
        if any(kw in low for kw in keys):
            h = hashlib.sha256(para.encode()).hexdigest()[:16]
            spans.append({"source_id": f"{corpus_path}#{len(spans)}",
                          "span": para[:400],
                          "content_hash": h})
            if len(spans) >= max_spans:
                break
    return spans


def retrieve_inspiration(failure_class: str, corpus_path: str = "") -> dict:
    """The typed inspiration bundle for the selection prompt."""
    analogies = CROSS_DOMAIN_ANALOGIES.get(failure_class, [])
    spans = _frozen_evidence_spans(failure_class, corpus_path)
    return {"failure_class": failure_class,
            "analogies": analogies,
            "evidence_spans": spans,
            "typed": ("MOOSE-Chem-style inspiration retrieval: "
                      "cross-domain analogies + hash-verified evidence "
                      "spans; a missing corpus is a typed empty set, "
                      "never an invented precedent")}


def inspiration_prompt_block(inspiration: dict) -> str:
    """The prompt block that grounds the selection in precedents."""
    lines = ["INSPIRATION CONTEXT (retrieved precedents; use them to "
             "ground the mechanism choice, never as a license to copy "
             "blindly):"]
    for a in inspiration.get("analogies", [])[:2]:
        lines.append(f"- from {a['from_domain']}: {a['precedent']} — "
                     f"transfer: {a['transfer']}")
    for s in inspiration.get("evidence_spans", [])[:2]:
        lines.append(f"- evidence [{s['source_id']}|{s['content_hash']}]: "
                     f"\"{s['span'][:220]}\"")
    if len(lines) == 1:
        lines.append("- (typed empty: no analogies for this failure "
                     "class; proceed on the mapped mechanism classes)")
    return "\n".join(lines)
