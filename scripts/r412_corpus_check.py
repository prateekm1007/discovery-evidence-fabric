#!/usr/bin/env python3
"""Quick corpus conformance check for the TVM v2 value parser.

Runs every calibration corpus case through the parser and reports
disagreements. Corpus ground truths are authoritative (Article VIII:
certification corpus authored independently of the matcher); a
disagreement is a parser defect.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path("/home/z/my-project/audit_ws/repo")
sys.path.insert(0, str(REPO / "R412" / "GRADIENT_V2"))

from tvm_v2.value_parser import parse_value_span  # noqa: E402

CORPUS = REPO / "R412" / "GRADIENT_V2" / "TVM_V2_PARSER_CALIBRATION_CORPUS.json"


def norm_float(x):
    return None if x is None else round(float(x), 10)


def main() -> int:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    failures = []
    for case in corpus["cases"]:
        exp = case["expected"]
        got = parse_value_span(case["raw_span"], case["field_context"]).to_dict()
        # Compare the fields the corpus pins.
        problems = []
        for key in ("representation", "normalization_method", "unit",
                    "year", "year_min", "year_max",
                    "approximation_marker", "open_bound", "qualitative_term",
                    "malformed_reason"):
            if key in exp and exp[key] != got.get(key):
                problems.append(f"{key}: expected {exp[key]!r} got {got.get(key)!r}")
        for key in ("normalized_value", "normalized_min", "normalized_max"):
            if key in exp:
                if norm_float(exp[key]) != norm_float(got.get(key)):
                    problems.append(
                        f"{key}: expected {exp[key]!r} got {got.get(key)!r}")
        # Losslessness invariant on every case.
        if got.get("raw_source_span") != case["raw_span"]:
            problems.append("raw_source_span drift")
        if problems:
            failures.append((case["id"], case["raw_span"], problems))

    total = len(corpus["cases"])
    print(f"cases: {total}, failures: {len(failures)}")
    for cid, span, problems in failures:
        print(f"  FAIL {cid} {span!r}")
        for p in problems:
            print(f"       {p}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
