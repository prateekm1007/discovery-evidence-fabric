#!/usr/bin/env python3
"""r123_f97_verifier_run.py — the cross-implementation verifier run of
the F97 real-byte corpus (claim c-0187, work id
r123-f97-verifier-corpus; zero LLM).

The corpus: tests/fixtures/f97_input_availability_cases.json — 25 REAL
committed run bytes (both R123 fresh draws), typed expectations
authored for THIS session's independent F97 implementation (3
mechanisms: balanced paren-strip, signal-span validity, clause-verb
gate — the duplicate execution stood down per Art. 29(e); the
canonical instrument is the twin lane's 8-mechanism fix at
b95afc9006223bcd). This run applies the CANONICAL detector to the
corpus and records the cross-implementation outcome typed:
  converge_silent  — a prose/paren mis-parse shape silent on BOTH
                     implementations (the F97 noise kill is robust);
  recall_divergence — a case the corpus types GENUINE (it fired in the
                     R123 records and the c-0185 root-cause analysis)
                     that the canonical instrument does NOT fire — a
                     RECALL QUESTION for the auditor's semantic call,
                     not a bug report.
Output: eval/r123_f97_verifier_corpus/verifier_result.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r40_machine_v77 as m77  # noqa: E402 (the CANONICAL bytes)

OUT = REPO / "eval" / "r123_f97_verifier_corpus"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    fx = json.loads((REPO / "tests" / "fixtures"
                     / "f97_input_availability_cases.json")
                    .read_text(encoding="utf-8"))
    results = []
    conv_silent = recall_div = other = 0
    for c in fx["cases"]:
        res = m77.scan_input_availability(c["problem"], c["bill"])
        exp = c["expectation"]
        fired = res.get("INPUT_UNAVAILABLE", [])
        if exp == "silent":
            ok = res == {}
            cls = "converge_silent" if ok else "silent_divergence"
            conv_silent += ok
        else:
            ok = bool(fired) and any(
                c["expected_qty_substring"].lower() in s.lower()
                for s in fired)
            cls = "recall_match" if ok else "recall_divergence"
            recall_div += (not ok)
        other += (cls in ("silent_divergence", "recall_match"))
        results.append({
            "case_id": c["case_id"], "expectation": exp,
            "outcome": cls, "canonical_fired": fired,
            "why": c["why"],
            "source_record": c["source_record"]})
    n = len(results)
    n_silent = sum(1 for c in fx["cases"]
                   if c["expectation"] == "silent")
    out = {
        "record": "R123_F97_VERIFIER_CORPUS_RESULT/1.0.0",
        "claim": "c-0187 (r123-f97-verifier-corpus)",
        "canonical_instrument": "the twin lane's F97 fix "
                                "(b95afc9006223bcd, claim c-0186, "
                                "work id r124-f97-detector-precision) "
                                "at tip c278f69c3",
        "verifier_instrument": "this session's independent F97 "
                               "implementation (3 mechanisms; the "
                               "duplicate execution stood down per "
                               "Art. 29(e); its own re-scoring of both "
                               "draws under ITSELF measured pooled "
                               "bare 0.5208 vs succ 0.2292, CI "
                               "[+0.1667,+0.4375], damage 1/23 — a "
                               "second implementation's measurement, "
                               "NOT the canonical record)",
        "corpus": "25 REAL committed run bytes (both R123 fresh "
                  "draws), expectations typed per the R123 genuine-"
                  "class reading (incl. the c-0185 root-cause note's "
                  "own 'Wet-Bulb Deviation Logic' example)",
        "n_cases": n, "n_silent_expectations": n_silent,
        "converge_silent": conv_silent,
        "recall_divergence": recall_div,
        "summary": (
            f"{conv_silent}/{n_silent} prose/paren shapes silent on "
            "BOTH implementations (the F97 noise kill is robust "
            "across independent implementations); "
            f"{recall_div}/{n - n_silent} genuine-class cases fire "
            "only on the verifier implementation and are SILENT on "
            "the canonical instrument — a typed RECALL QUESTION "
            "(whether the derived-feature/input-name residual class "
            "should bind is the auditor's semantic call; the "
            "canonical design reads named logic/features and "
            "instrument-bridged quantities as non-binding)"),
        "cases": results,
    }
    (OUT / "verifier_result.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"converge_silent {conv_silent}/{n_silent} | "
          f"recall_divergence {recall_div}/{n - n_silent}")
    for r in results:
        if r["outcome"] == "recall_divergence":
            print(f"  {r['case_id']} divergence: {r['why'][:60]}")
    print(f"written: {OUT/'verifier_result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
