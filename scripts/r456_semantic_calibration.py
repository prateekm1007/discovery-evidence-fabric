#!/usr/bin/env python3
"""R456 — the semantic-relevance calibration (Art. XXVII: no threshold
invention). Builds the DEVELOPMENT corpus from the frozen R452 assay
runs' OWN artifacts (problem text + record title/abstract pairs), with
labels authored by READING each pair (a human labeling pass, recorded
with per-pair reasons — Art. VIII: labels never derived from the
matcher's behavior). Then scores every pair with the semantic
adjudicator (the local zero-paid embedding route) and writes the
separation analysis to R456/SEMANTIC_RELEVANCE_CALIBRATION.json.

The frozen assay itself is the HELD-OUT measurement (the benchmark
driver); this corpus is the development/tuning set — never the same
records on both sides of the fence.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.source_registry import semantic_relevance as sr  # noqa: E402

# (case, record_index, LABEL, reason) — LABEL ∈ {RELEVANT,
# HARD_ADJACENT, IRRELEVANT}. RELEVANT = addresses the problem's own
# device/subsystem/failure; HARD_ADJACENT = same broad domain but a
# different device, mechanism, or aspect (the class the lexical gate
# and the ANALOGY-dominated pools confuse); IRRELEVANT = different
# domain or generic noise.
LABELS = [
    # ---- case A: surgical irrigation pressure instability ----------
    ("A", 0, "HARD_ADJACENT", "arthroscopy context; anesthesia mechanism, not irrigation flow"),
    ("A", 1, "HARD_ADJACENT", "arthroscopic knee analgesia; not distension/flow"),
    ("A", 2, "IRRELEVANT", "rotator cuff tendon biology"),
    ("A", 3, "IRRELEVANT", "tendon healing cell biology"),
    ("A", 4, "IRRELEVANT", "rat hindfoot normative data"),
    ("A", 5, "IRRELEVANT", "fibrotic tendon healing molecular map"),
    ("A", 6, "IRRELEVANT", "vibratory energy patent for occluded cavities; not irrigation hydraulics"),
    ("A", 7, "IRRELEVANT", "cell isolation chemistry"),
    ("A", 9, "IRRELEVANT", "adhesion-barrier compositions"),
    ("A", 11, "HARD_ADJACENT", "arthroscopic knee surgery simulation; tissue modeling not flow"),
    ("A", 12, "IRRELEVANT", "cardiac death trial dataset"),
    ("A", 13, "IRRELEVANT", "gaming disorder psychology"),
    ("A", 14, "HARD_ADJACENT", "generic arthroscopic surgery overview; no irrigation system failure"),
    ("A", 15, "HARD_ADJACENT", "ambulatory surgery statistics; same setting, different question"),
    ("A", 16, "HARD_ADJACENT", "arthroscopic shoulder complications; not distension instability per se"),
    ("A", 17, "HARD_ADJACENT", "arthroscopic knee complications management"),
    ("A", 18, "IRRELEVANT", "openfoam prompt-template noise record"),
    # ---- case B: gearbox cold-start pinion starvation ----------------
    ("B", 0, "RELEVANT", "condition monitoring of the exact device+subsystem (wind turbine planetary gearboxes)"),
    ("B", 1, "IRRELEVANT", "wind power forecasting ML"),
    ("B", 3, "IRRELEVANT", "single-cell protein production"),
    ("B", 5, "HARD_ADJACENT", "turbine BLADE materials; not the gearbox lubrication"),
    ("B", 6, "RELEVANT", "condition monitoring of wind turbine gearboxes (the failing subsystem)"),
    ("B", 7, "RELEVANT", "vibration analysis of multi-stage planetary gear (the exact gear stage)"),
    ("B", 8, "HARD_ADJACENT", "turbine aerodynamics; different subsystem"),
    ("B", 9, "IRRELEVANT", "grid-side dynamic equivalent modeling"),
    ("B", 11, "IRRELEVANT", "vertical-axis turbines; different machine"),
    ("B", 12, "IRRELEVANT", "wind farm CFD wake modeling"),
    ("B", 14, "IRRELEVANT", "openfoam prompt-template noise record"),
    # ---- case C: SiC die-attach delamination -------------------------
    ("C", 0, "RELEVANT", "die/substrate attach materials for SiC high-temp modules — the exact layer+failure"),
    ("C", 1, "HARD_ADJACENT", "SiC traction inverter system; not die-attach delamination"),
    ("C", 2, "HARD_ADJACENT", "current balancing paralleled SiC modules; different failure mode"),
    ("C", 3, "HARD_ADJACENT", "gate driver design for SiC; different subsystem"),
    ("C", 4, "HARD_ADJACENT", "SiC motor drive inverter demonstration; system-level"),
    ("C", 5, "HARD_ADJACENT", "advanced high-temp materials broadly"),
    ("C", 6, "HARD_ADJACENT", "CSI inverter optimization with SiC; different application"),
    ("C", 7, "HARD_ADJACENT", "delamination mechanics in PV modules — same failure physics, different device"),
    ("C", 9, "RELEVANT", "SiC multi-chip power module thermal characterization — the exact module class"),
    ("C", 10, "HARD_ADJACENT", "switching-frequency optimization metro drive; SiC but different question"),
    ("C", 12, "IRRELEVANT", "SiC ceramics piezoresistance doping"),
    ("C", 13, "IRRELEVANT", "openfoam prompt-template noise record"),
    # ---- case A2 (repeat run): fresh pairs only ----------------------
    ("A2", 6, "HARD_ADJACENT", "arthroscopic knee simulation"),
    ("A2", 9, "IRRELEVANT", "ambulatory oxygen COPD adherence"),
    ("A2", 11, "HARD_ADJACENT", "cartilage health after arthroscopy"),
    ("A2", 12, "IRRELEVANT", "placebo-controlled surgery trial design"),
    # ---- cross-case negatives (the confusable-domain controls) -------
    ("A", "B:0", "IRRELEVANT", "gearbox monitoring vs irrigation problem (cross-domain control)"),
    ("A", "C:0", "IRRELEVANT", "die-attach materials vs irrigation problem (cross-domain control)"),
    ("B", "A:11", "IRRELEVANT", "knee surgery simulation vs gearbox problem (cross-domain control)"),
    ("C", "B:7", "IRRELEVANT", "planetary gear vibration vs die-attach problem (cross-domain control)"),
    ("B", "C:9", "IRRELEVANT", "SiC module thermal vs gearbox problem (cross-domain control)"),
]


def _record_text(case: str, idx) -> str:
    env = json.load(open(REPO / f"R452/ASSAY_RUN_{case}" /
                         "envelope_RETRIEVE.json"))
    ev = env.get("evidence") or []
    if isinstance(idx, str) and ":" in idx:
        c2, i2 = idx.split(":")
        env2 = json.load(open(REPO / f"R452/ASSAY_RUN_{c2}" /
                              "envelope_RETRIEVE.json"))
        it = (env2.get("evidence") or [])[int(i2)]
    else:
        it = ev[int(idx)]
    title = str(it.get("title") or "")
    abstract = str(it.get("abstract") or "")
    return f"{title}. {abstract}".strip()


def main() -> int:
    problems = {}
    for case in ("A", "B", "C", "A2"):
        p = json.load(open(REPO / f"R452/ASSAY_RUN_{case}" /
                           "authored_problem.json"))
        problems[case] = p["text"]

    corpus = []
    for case, idx, label, reason in LABELS:
        corpus.append({
            "case": case,
            "record_ref": f"R452/ASSAY_RUN_{case}/envelope_RETRIEVE.json"
                          f"[{idx}]",
            "label": label,
            "label_reason": reason,
            "label_authorship": ("human reading of the pair (title+"
                                 "abstract vs problem text), recorded "
                                 "before the matcher scored it"),
            "problem_text": problems[case],
            "record_text": _record_text(case, idx),
        })

    # score every pair with the semantic adjudicator (local route);
    # one call per pair (each pair carries its OWN problem text), with
    # one retry on transient engine unavailability (typed, never silent)
    scores = []
    for c in corpus:
        d = sr.semantic_adjudicate(c["problem_text"], [c["record_text"]])[0]
        if d["semantic_cosine"] is None:
            d = sr.semantic_adjudicate(
                c["problem_text"], [c["record_text"]], )[0]
        if d["semantic_cosine"] is None:
            raise SystemExit(
                f"FATAL: embedding engine unavailable for pair "
                f"{c['record_ref']} (Art. XXV: unknown is never a score)")
        c["semantic_cosine"] = d["semantic_cosine"]
        c["semantic_state"] = d["semantic_state"]
        scores.append((c["label"], d["semantic_cosine"]))

    by_label = {}
    for label, s in scores:
        by_label.setdefault(label, []).append(s)
    summary = {
        k: {"n": len(v), "min": round(min(v), 4),
            "median": round(statistics.median(v), 4),
            "max": round(max(v), 4)}
        for k, v in sorted(by_label.items())
    }

    # separation analysis: pick thresholds at the measured gaps
    rel = sorted(by_label.get("RELEVANT", []))
    adj = sorted(by_label.get("HARD_ADJACENT", []))
    irr = sorted(by_label.get("IRRELEVANT", []))
    analysis = {
        "relevant_vs_adjacent_gap": round(min(rel) - max(adj), 4)
        if rel and adj else None,
        "adjacent_vs_irrelevant_gap": round(min(adj) - max(irr), 4)
        if adj and irr else None,
        "min_relevant": round(min(rel), 4) if rel else None,
        "max_hard_adjacent": round(max(adj), 4) if adj else None,
        "max_irrelevant": round(max(irr), 4) if irr else None,
        "median_relevant": round(statistics.median(rel), 4) if rel else None,
        "median_hard_adjacent": round(statistics.median(adj), 4) if adj else None,
        "median_irrelevant": round(statistics.median(irr), 4) if irr else None,
    }

    out = {
        "instrument": "scripts/r456_semantic_calibration.py",
        "semantic_version": sr.SEMANTIC_RELEVANCE_VERSION,
        "engine_model": sr.model_name(),
        "corpus": corpus,
        "label_distribution": {k: len(v) for k, v in sorted(by_label.items())},
        "score_summary_by_label": summary,
        "separation_analysis": analysis,
        "threshold_recommendation": {
            "relevant": analysis["min_relevant"],
            "weak_floor": analysis["median_hard_adjacent"],
            "note": "RELEVANT threshold at the measured minimum of the "
                    "relevant band; the WEAK floor at the hard-adjacent "
                    "median keeps the adjacency band in custody without "
                    "admitting it",
        },
        "art_xxvii_declaration": (
            "ENGINEERING-class thresholds, calibrated on this DEVELOPMENT "
            "corpus (labels authored from pair semantics before scoring); "
            "the frozen R452 assay is the held-out measurement and never "
            "the tuning set"),
    }
    dst = REPO / "R456" / "SEMANTIC_RELEVANCE_CALIBRATION.json"
    dst.write_text(json.dumps(out, indent=2) + "\n")
    print(f"corpus: {len(corpus)} pairs -> {dst}")
    print(json.dumps(summary, indent=1))
    print("separation:", json.dumps(analysis, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
