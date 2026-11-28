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
    # R145S1 (DIR-6, the twin's extended families — the additive
    # extension: 12/30 v17 rows sat in the 5 new families the c-0243
    # lexicon extension added; without entries the inspiration lever
    # was inert on them. Same shape: real, checkable precedents.)
    "deposition_fouling": [
        {"from_domain": "membrane technology", "precedent": (
            "periodic osmotic backwash on RO trains"),
         "transfer": ("a short reverse-flux pulse lifts the "
                      "deposited layer without a full cleaning "
                      "shutdown")},
        {"from_domain": "power-plant chemistry", "precedent": (
            "condenser sponge-ball online cleaning"),
         "transfer": ("a circulating cleaning body continuously "
                      "sweeps the deposit-forming surface")},
    ],
    "mechanical_clogging": [
        {"from_domain": "wastewater screening", "precedent": (
            "self-cleaning step screens with upstream rake timing"),
         "transfer": ("the screen clears itself on a schedule "
                      "matched to the capture rate, before the "
                      "compaction threshold")},
        {"from_domain": "mining", "precedent": (
            "chute liners with vibration-assisted discharge"),
         "transfer": ("low-amplitude wall excitation keeps the "
                      "arched material flowing")},
    ],
    "electrochemical_corrosion": [
        {"from_domain": "marine engineering", "precedent": (
            "ICCP anode arrays zoned to current demand"),
         "transfer": ("distributed active potential control beats a "
                      "single bulk setting")},
        {"from_domain": "water treatment", "precedent": (
            "phosphate film-forming dosing at ppm levels"),
         "transfer": ("a nanoscale barrier film cuts the corrodant "
                      "flux at the surface")},
    ],
    "seal_leak_integrity": [
        {"from_domain": "hydraulics", "precedent": (
            "redundant O-ring stacks with a drain groove between"),
         "transfer": ("two cheap barriers in series with a tell-tale "
                      "path between them beat one premium barrier")},
        {"from_domain": "rotating machinery", "precedent": (
            "dry-gas seal separation pressure control"),
         "transfer": ("a clean buffer medium held slightly above "
                      "the process pressure keeps the contaminant "
                      "out of the seal faces")},
    ],
    "phase_carryover_liquid": [
        {"from_domain": "steam systems", "precedent": (
            "demister pads + swirl-vane separators in series"),
         "transfer": ("inertial separation staged after capture "
                      "removes the droplets gravity alone misses")},
        {"from_domain": "HVAC", "precedent": (
            "suction-line accumulators on refrigeration returns"),
         "transfer": ("a low-velocity sump gives the entrained "
                      "liquid a place to drop out before the "
                      "sensitive component")},
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


# ---------------------------------------------------------------------------
# R190S1 DIR 8 (owner merged-and-locked): the SCORE-7 REDISCOVERY wiring.
# The MOOSE-Chem-derived benchmark (eval/moose_chem/rediscovery_benchmark
# .json; 51 post-cutoff items,2024-01-10..2024-09-13, xlsx sha256
# 6ebd5c31...) + the typed PRE-DATE retrieval restriction. The rediscovery
# run: given ONLY the item's background question/survey and the pre-date
# evidence corpus, reproduce the paper's true hypothesis MECHANISM; the
# gate is >=30% mechanism-level rediscovery vs <=15% for the no-evidence
# baseline (blind panel distinct from the generator; never self-judged).
# ---------------------------------------------------------------------------

REDISCOVERY_BENCHMARK = (REPO / "eval" / "moose_chem" /
                         "rediscovery_benchmark.json")


def rediscovery_benchmark_items() -> list:
    """The >=20 post-cutoff benchmark items, typed-loaded (a missing or
    malformed benchmark is a typed failure, never an empty pass)."""
    try:
        doc = json.loads(
            REDISCOVERY_BENCHMARK.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise RuntimeError(
            "TYPED: the rediscovery benchmark is absent "
            f"({REDISCOVERY_BENCHMARK}); build it with scripts/"
            "r190s1_build_moose_benchmark.py")
    items = doc.get("items") or []
    if len(items) < 20:
        raise RuntimeError(
            f"TYPED: the rediscovery benchmark has {len(items)} items "
            "< 20 (the Score-7 gate needs N >= 20)")
    return items


def pre_date_corpus_filter(evidence_items: list, cutoff_iso: str) -> dict:
    """The typed pre-date restriction for one benchmark item: keep ONLY
    evidence whose publication date is STRICTLY BEFORE the item's
    public date. An item without a parseable date is EXCLUDED (fail
    closed — an undated span is not proven pre-date)."""
    from datetime import date
    cutoff = date.fromisoformat(cutoff_iso)
    kept, excluded = [], []
    for it in evidence_items:
        d = it.get("published") or it.get("date") or ""
        try:
            if date.fromisoformat(str(d)[:10]) < cutoff:
                kept.append(it)
            else:
                excluded.append({"item": str(it.get("source_id", ""))[:40],
                                 "why": f"post-cutoff {d}"})
        except ValueError:
            excluded.append({"item": str(it.get("source_id", ""))[:40],
                             "why": f"unparseable date {d!r} -> excluded"})
    return {"cutoff": cutoff_iso, "kept": len(kept),
            "excluded": excluded, "corpus": kept,
            "rule": ("retrieval restricted to literature STRICTLY "
                     "before the item's public date; the item's own "
                     "paper and anything citing it are excluded")}
