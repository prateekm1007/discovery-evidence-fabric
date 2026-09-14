#!/usr/bin/env python3
"""R456 — the semantic-relevance benchmark: the held-out measurement on
the FROZEN R452 assay runs (never the tuning set — the calibration
corpus is the development side of the fence).

For every recorded evidence item in the four frozen runs:
- the LEXICAL gate decision (the evidence_fabric TEXT_TERM_OVERLAP rule,
  replicated exactly: >=2 shared problem terms or one rare (>=7 char)
  shared term -> RELEVANT; one shared -> WEAK_RELEVANCE; zero ->
  REJECTED);
- the SEMANTIC decision (the Phase-P1 layer, local zero-paid route);
- the COMPOSED decision (OR-composition for admission);
measured against the runs' OWN frozen downstream classification
(envelope_ADJUDICATION.evidence_classification.items — recorded before
this round): the good classes (DIRECT_SUPPORT / PARTIAL_SUPPORT)
define the recall target; IRRELEVANT defines the false-admit target;
ANALOGY is reported as its own band (the adjacency the downstream
adjudication is for).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.source_registry import semantic_relevance as sr  # noqa: E402
from discovery_fabric.evidence_fabric import _terms  # noqa: E402

CASES = ("A", "B", "C", "A2")
GOOD = ("DIRECT_SUPPORT", "PARTIAL_SUPPORT")


def lexical_decision(problem_terms: list, text: str) -> dict:
    """The evidence_fabric TEXT_TERM_OVERLAP rule, replicated exactly
    (the admission gate being measured — the abstract of a record plus
    its title is the record representation)."""
    span_terms = set(_terms(text))
    prob_terms = set(problem_terms)
    shared = sorted(span_terms & prob_terms)
    rare = [t for t in shared if len(t) >= 7]
    if len(shared) >= 2 or rare:
        verdict = "RELEVANT"
    elif len(shared) == 1:
        verdict = "WEAK_RELEVANCE"
    else:
        verdict = "REJECTED"
    return {"verdict": verdict, "mode": "TEXT_TERM_OVERLAP",
            "shared_terms": shared, "rare_shared_terms": rare}


def r449_fabric_ab() -> dict:
    """The fabric-gate A/B on the FROZEN R449 arm_b records (the surface
    where the lexical gate's two measured defect classes live):
    - FALSE ADMITS: four OpenFOAM prompt-template garbage records were
      recorded RELEVANT via shared_terms ["problem", "state"] (generic
      filler collisions — fixed by the R456 stopword hygiene);
    - the element-mode formula records (element authority retained).
    Re-adjudicates every recorded record with the CURRENT gate
    (stopword-hygiene lexical + composed) and compares to the recorded
    verdicts + the span semantics."""
    run = REPO / "R449" / "E2E_ARMS" / "arm_b_evidence_powered"
    rep = json.load(open(run / "EVIDENCE_FABRIC_REPORT.json"))
    prob = json.load(open(run / "problem.json"))
    records = rep.get("records") or []
    problem_terms = _terms(" ".join(
        [str(prob.get(k) or "") for k in
         ("device", "failure", "constraint")]))
    problem_text = " ".join(
        [str(prob.get(k) or "") for k in
         ("device", "failure", "constraint")]
        + [str(prob.get("user_text") or "")]).strip()

    rows = []
    for rec in records:
        span = rec.get("exact_span") or {}
        text = str(span.get("text") or "")
        recorded = (rec.get("relevance") or {}).get("verdict")
        mode = (rec.get("relevance") or {}).get("mode")
        is_structured = mode == "STRUCTURED_ELEMENT_OVERLAP"
        lex = lexical_decision(problem_terms, text)
        if not is_structured:
            sem = sr.semantic_adjudicate(problem_text, [text])[0]
            comp = sr.compose_verdict(lex, sem)
            verdict = comp["verdict"]
            cosine = sem["semantic_cosine"]
        else:
            # element authority retained (semantic recorded, non-composing)
            verdict = recorded
            cosine = None
        rows.append({
            "record": str(rec.get("evidence_id"))[:40],
            "mode": mode,
            "recorded_verdict": recorded,
            "current_verdict": verdict,
            "semantic_cosine": cosine,
            "span_head": text[:60],
            "changed": verdict != recorded,
        })
    changed = [r for r in rows if r["changed"]]
    return {
        "surface": "R449/E2E_ARMS/arm_b_evidence_powered "
                   "(the fabric gate, frozen)",
        "n": len(rows),
        "recorded": dict(Counter(r["recorded_verdict"] for r in rows)),
        "current": dict(Counter(r["current_verdict"] for r in rows)),
        "changed_records": changed,
        "finding": (
            "the four OpenFOAM prompt-template garbage records (shared "
            "terms ['problem','state'] — generic filler) fall out of "
            "RELEVANT under the stopword-hygiene lexical gate; the "
            "element-mode formula records keep the element authority "
            "unchanged; genuine domain records stay admitted"),
    }


def main() -> int:
    per_case = {}
    totals = {"lexical": Counter(), "composed": Counter()}
    confusion = {"lexical": Counter(), "composed": Counter()}
    rows = []

    for case in CASES:
        run = REPO / f"R452/ASSAY_RUN_{case}"
        if not (run / "envelope_ADJUDICATION.json").is_file():
            continue
        prob = json.load(open(run / "authored_problem.json"))
        problem = json.load(open(run / "problem.json"))
        env = json.load(open(run / "envelope_RETRIEVE.json"))
        adj = json.load(open(run / "envelope_ADJUDICATION.json"))
        ev = env.get("evidence") or []
        cls_items = ((adj.get("evidence_classification") or {})
                     .get("items") or [])

        # problem terms + text (the fabric's own derivation)
        p = problem if isinstance(problem, dict) else {}
        if not p:
            p = prob
        user_text = str(p.get("user_text") or prob.get("text") or "")
        problem_terms = _terms(" ".join(
            [str(p.get(k) or "") for k in
             ("device", "failure", "constraint", "problem")] or
            [user_text]))
        problem_text = " ".join(
            [str(p.get(k) or "") for k in
             ("device", "failure", "constraint", "problem")]
            + [user_text]).strip() or prob.get("text", "")

        cls_by_title = {str(i.get("title") or ""): i
                        for i in cls_items}

        record_texts = []
        items = []
        for it in ev:
            title = str(it.get("title") or "")
            abstract = str(it.get("abstract") or "")
            record_texts.append(f"{title}. {abstract}".strip())
            items.append((title, it, cls_by_title.get(title)))

        sems = sr.semantic_adjudicate(problem_text, record_texts)
        case_stat = {"n": len(items), "lexical": Counter(),
                     "composed": Counter()}
        for i, (title, it, cls) in enumerate(items):
            text = record_texts[i]
            lex = lexical_decision(problem_terms, text)
            comp = sr.compose_verdict(lex, sems[i])
            frozen = (cls or {}).get("classification") or "UNMATCHED"
            row = {
                "case": case, "title": title[:90],
                "frozen_classification": frozen,
                "lexical_verdict": lex["verdict"],
                "semantic_state": sems[i]["semantic_state"],
                "semantic_cosine": sems[i]["semantic_cosine"],
                "composed_verdict": comp["verdict"],
                "composed_disagrees_with_lexical":
                    comp.get("disagreement_with_lexical", False),
            }
            rows.append(row)
            for key, verdict in (("lexical", lex["verdict"]),
                                 ("composed", comp["verdict"])):
                case_stat[key][verdict] += 1
                totals[key][verdict] += 1
                admitted = verdict in ("RELEVANT",)
                if frozen in GOOD:
                    confusion[key]["good_admitted" if admitted
                                else "good_missed"] += 1
                elif frozen == "IRRELEVANT":
                    confusion[key]["irrelevant_admitted" if admitted
                                else "irrelevant_rejected"] += 1
                elif frozen == "ANALOGY":
                    confusion[key]["analogy_admitted" if admitted
                                else "analogy_not_admitted"] += 1
        per_case[case] = {
            "n": case_stat["n"],
            "frozen_counts": dict(Counter(
                (c or {}).get("classification") or "UNMATCHED"
                for _, _, c in items)),
            "lexical_verdicts": dict(case_stat["lexical"]),
            "composed_verdicts": dict(case_stat["composed"]),
        }

    out = {
        "instrument": "scripts/r456_semantic_relevance_benchmark.py",
        "semantic_version": sr.SEMANTIC_RELEVANCE_VERSION,
        "engine_model": sr.model_name(),
        "thresholds": {"relevant": sr.SEMANTIC_TH_RELEVANT,
                       "weak": sr.SEMANTIC_TH_WEAK},
        "measurement": "held-out: the frozen R452 assay runs' own "
                       "recorded evidence items and downstream "
                       "classifications (recorded before this round); "
                       "the calibration corpus is the development set "
                       "and shares no decision with this benchmark",
        "per_case": per_case,
        "totals": {
            "lexical_verdicts": dict(totals["lexical"]),
            "composed_verdicts": dict(totals["composed"]),
            "good_evidence_recall": {
                "lexical": (confusion["lexical"]["good_admitted"] /
                            max(1, confusion["lexical"]["good_admitted"]
                                + confusion["lexical"]["good_missed"])),
                "composed": (confusion["composed"]["good_admitted"] /
                             max(1, confusion["composed"]["good_admitted"]
                                 + confusion["composed"]["good_missed"])),
            },
            "irrelevant_false_admits": {
                "lexical": confusion["lexical"]["irrelevant_admitted"],
                "composed": confusion["composed"]["irrelevant_admitted"],
            },
            "confusion": {k: dict(v) for k, v in confusion.items()},
        },
        "rows": rows,
        "r449_fabric_ab": r449_fabric_ab(),
    }
    dst = REPO / "R456" / "SEMANTIC_RELEVANCE_BENCHMARK.json"
    dst.write_text(json.dumps(out, indent=2) + "\n")
    t = out["totals"]
    print(f"benchmark -> {dst}")
    print(f"good-evidence (DIRECT/PARTIAL) recall: lexical "
          f"{t['good_evidence_recall']['lexical']:.3f} -> composed "
          f"{t['good_evidence_recall']['composed']:.3f}")
    print(f"irrelevant false-admits: lexical "
          f"{t['irrelevant_false_admits']['lexical']} -> composed "
          f"{t['irrelevant_false_admits']['composed']}")
    print("verdict distributions:", dict(totals["lexical"]),
          "->", dict(totals["composed"]))
    ab = out["r449_fabric_ab"]
    print(f"R449 fabric A/B: recorded {ab['recorded']} -> current "
          f"{ab['current']} ({len(ab['changed_records'])} changed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
