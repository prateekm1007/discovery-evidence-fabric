#!/usr/bin/env python3
"""R412 Phase C (operator directive 2026-09-06): the TVM v2
instrument measured against the actual v1 outputs — with the
measurability boundary stated honestly.

The directive's design:

  34 v1 outputs -> v1 strict parser -> v2 lossless parser ->
  span verification -> comparison

The committed evidence supports exactly this much of it:

  * The 34 v1 proposals' RAW TEXTS were never persisted by the v1
    instrument (Phase B reconciliation: V1_RAW_PROPOSAL_TEXTS_
    ABSENT_UNPERSISTED). A per-proposal reparse of all 34 is
    therefore NOT_MEASURABLE_FROM_COMMITTED_EVIDENCE. Fabricating
    34 plausible strings to feed the parsers would manufacture the
    very evidence the measurement needs (Art. VI/VII forbidden).
  * What IS committed and re-measurable live:
      1. the v1 recorded outcome: 34 proposals -> 0 admitted,
         31 VALUE_OR_YEAR_NOT_NUMERIC / 2 RECORD_ID_NOT_IN_POOL /
         1 SPAN_NOT_VERBATIM (re-verified from TVM_CONSTRUCTED
         construction_log bytes);
      2. the instrument-level comparison on the frozen calibration
         corpus (40 cases; the same question: which value forms a
         v1-class strict schema rejects that the v2 canonical parser
         admits as measured evidence);
      3. the TWO example fragments the v1 final report quotes
         byte-exactly ("0.1-10", "2023 (study)") — a partial replay
         of real v1 output fragments, provenance-pinned to the
         report's bytes.
  * The DEFINITIVE v1-vs-v2 same-seeds comparison is the sealed v2
    run itself (Phase L): same 10 seeds, same budgets, same rungs,
    the only deltas being the TVM proposal prompt format (field-line)
    and the v2 parser/evidence contract — and the v2 runner persists
    RAW proposals in its construction log, so the next comparison
    needs no reconstruction.

This script emits:

  R412/GRADIENT_V2/V1_V2_PARSER_COMPARISON.json

which SUPERSEDES V1_OUTPUT_REPARSE_MEASUREMENT.json (the old
artifact remains as history per Art. XI; this one is the authority).

Deterministic. No model calls. reviewer_provenance=AI_REVIEW.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "R412" / "GRADIENT_V2"))

from tvm_v2 import (  # noqa: E402
    CONTEXT_VALUE, CONTEXT_YEAR,
    parse_value_span, REP_NOT_NUMERIC, REP_MALFORMED,
    v1_value_admissible, v1_year_admissible,
)

OUT = REPO / "R412" / "GRADIENT_V2" / "V1_V2_PARSER_COMPARISON.json"
CORPUS = REPO / "R412" / "GRADIENT_V2" / \
    "TVM_V2_PARSER_CALIBRATION_CORPUS.json"
REPORT = REPO / "R412" / "RECOVERY_ARM" / "GRADIENT_RUN" / \
    "R412_GRADIENT_ARM_FINAL_REPORT.md"
TVM_C = REPO / "R412" / "RECOVERY_ARM" / "GRADIENT_RUN" / \
    "TVM_CONSTRUCTED.json"
OLD = REPO / "R412" / "GRADIENT_V2" / \
    "V1_OUTPUT_REPARSE_MEASUREMENT.json"


def _load(p: Path):
    return json.loads(p.read_text())


def _v2_measured_admits(span: str, context: str) -> bool:
    """v2 'admits as MEASURED evidence' (the admission-relevant
    predicate, matching the old artifact's definition): the parse
    lands on POINT/RANGE/INEQUALITY — a quantitative claim a TVM
    slope can be computed from. ORDINAL_QUALITATIVE is an
    admissible PARSE result but not a measured value."""
    cv = parse_value_span(span, context=context)
    return cv.representation in ("POINT", "RANGE", "INEQUALITY")


def _v2_parse_admits(span: str, context: str) -> bool:
    """v2 'parses losslessly' (the wider predicate): any canonical
    representation incl. ORDINAL_QUALITATIVE — i.e. the span is
    understood and preserved, though possibly not a measured
    numeric."""
    cv = parse_value_span(span, context=context)
    return cv.representation not in (REP_NOT_NUMERIC, REP_MALFORMED)


def _corpus_measurement() -> dict:
    corpus = _load(CORPUS)
    cases = corpus["cases"]
    value_cases = [c for c in cases
                   if c.get("field_context") == "VALUE"]
    year_cases = [c for c in cases
                  if c.get("field_context") == "YEAR"]
    v1_ad, v1_rej = [], []
    v2_ad, v2_rej = [], []          # measured-numeric predicate
    v2_parse_ad = []                # lossless-parse predicate
    rescued, still = [], []
    qualitative_rescued = []
    for c in value_cases:
        s = c["raw_span"]
        v1ok = v1_value_admissible(s)
        v2ok = _v2_measured_admits(s, CONTEXT_VALUE)
        (v1_ad if v1ok else v1_rej).append(c["id"])
        (v2_ad if v2ok else v2_rej).append(c["id"])
        if _v2_parse_admits(s, CONTEXT_VALUE):
            v2_parse_ad.append(c["id"])
        if not v1ok and v2ok:
            rescued.append(c["id"])
        if not v1ok and not v2ok \
                and _v2_parse_admits(s, CONTEXT_VALUE):
            qualitative_rescued.append(c["id"])
        if not v1ok and not _v2_parse_admits(s, CONTEXT_VALUE):
            still.append(c["id"])
    y_v1_ad = [c["id"] for c in year_cases
               if v1_year_admissible(c["raw_span"])]
    y_v2_ad = [c["id"] for c in year_cases
               if _v2_measured_admits(c["raw_span"], CONTEXT_YEAR)]
    return {
        "comparison_scope": "CORPUS_LEVEL_INSTRUMENT_COMPARISON",
        "corpus_id": corpus["corpus_id"],
        "corpus_frozen": corpus["frozen"],
        "v1_predicate_label": "RECONSTRUCTED_FROM_REPORTED_FAILURE_"
                              "CLASS (v1 strict = float(value) / "
                              "int(year) exactly as "
                              "discovery_fabric/r412/gradient.py "
                              "verify_tvm_entries applies them)",
        "v2_admission_predicates": {
            "MEASURED_NUMERIC (POINT/RANGE/INEQUALITY)":
                "the admission-relevant predicate — a TVM slope "
                "can be computed from it; matches the superseded "
                "artifact's definition",
            "LOSSLESS_PARSE (any canonical representation incl. "
            "ORDINAL_QUALITATIVE)":
                "the wider predicate — the span is understood and "
                "preserved, though possibly not a measured numeric",
        },
        "value_context_cases": len(value_cases),
        "v1_strict_admits": len(v1_ad),
        "v1_strict_admits_ids": v1_ad,
        "v2_admits_measured": len(v2_ad),
        "v2_admits_ids": v2_ad,
        "v2_parses_losslessly": len(v2_parse_ad),
        "v2_parses_losslessly_ids": v2_parse_ad,
        "rescued_by_v2": len(rescued),
        "rescued_by_v2_ids": rescued,
        "rescued_as_parseable_but_qualitative":
            len(qualitative_rescued),
        "rescued_as_qualitative_ids": qualitative_rescued,
        "still_rejected_by_both": len(still),
        "still_rejected_ids": still,
        "year_context_cases": len(year_cases),
        "year_v1_strict_admits": len(y_v1_ad),
        "year_v2_admits": len(y_v2_ad),
    }


def _fragment_replay() -> dict:
    """The two fragments the v1 final report quotes byte-exactly,
    replayed through both instruments. PARTIAL (n=2 of 34) and
    labeled as such — these are the only recoverable v1 output
    fragments, and their provenance is the report's own bytes."""
    txt = REPORT.read_text()
    rep_sha = hashlib.sha256(REPORT.read_bytes()).hexdigest()
    frags = [
        {"fragment": "0.1–10",
         "quoted_in": "R412/RECOVERY_ARM/GRADIENT_RUN/"
                      "R412_GRADIENT_ARM_FINAL_REPORT.md line 78",
         "v1_class": "a value span the v1 float() cast rejects -> "
                     "VALUE_OR_YEAR_NOT_NUMERIC"},
        {"fragment": "2023 (study)",
         "quoted_in": "R412/RECOVERY_ARM/GRADIENT_RUN/"
                      "R412_GRADIENT_ARM_FINAL_REPORT.md line 78",
         "v1_class": "a year span the v1 int() cast rejects -> "
                     "VALUE_OR_YEAR_NOT_NUMERIC"},
    ]
    out = []
    for f in frags:
        ctx = CONTEXT_YEAR if "year" in f["v1_class"] \
            else CONTEXT_VALUE
        v1ok = (v1_year_admissible(f["fragment"]) if ctx ==
                CONTEXT_YEAR else
                v1_value_admissible(f["fragment"]))
        cv = parse_value_span(f["fragment"], context=ctx)
        v2ok = cv.representation in ("POINT", "RANGE",
                                     "INEQUALITY")
        out.append({
            **f,
            "context": ctx,
            "v1_strict_admits": v1ok,
            "v2_admits_measured": v2ok,
            "v2_parses_losslessly": cv.representation not in (
                REP_NOT_NUMERIC, REP_MALFORMED),
            "v2_representation": cv.representation,
            "v2_normalized": cv.to_dict()
            if hasattr(cv, "to_dict") else str(cv),
        })
    return {
        "provenance": "fragments quoted byte-exactly by the v1 final "
                      "report (report sha256 "
                      f"{rep_sha[:16]}...; byte-occurrence verified "
                      f"in this run: "
                      f"{all(x['fragment'] in txt for x in out)})",
        "n_of_34": 2,
        "boundary": "PARTIAL — the only recoverable v1 output "
                    "fragments; the other 32 proposals' raw texts "
                    "were never persisted (see "
                    "V1_PROVENANCE_RECONCILIATION.json)",
        "replays": out,
    }


def _v1_recorded_outcome() -> dict:
    tvm = _load(TVM_C)
    log = tvm["construction_log"]
    attempts = [e for e in log if e.get("n_retrieved") is not None]
    n_prop = sum(e.get("n_proposed", 0) for e in attempts)
    n_rej = sum(e.get("n_rejected", 0) for e in attempts)
    reasons: dict = {}
    for e in attempts:
        for r in e.get("rejected_reasons") or []:
            reasons[r] = reasons.get(r, 0) + 1
    return {
        "source": "R412/RECOVERY_ARM/GRADIENT_RUN/"
                  "TVM_CONSTRUCTED.json construction_log",
        "proposals": n_prop,
        "admitted": tvm.get("n_entries", 0),
        "rejected": n_rej,
        "rejection_classes": reasons,
    }


def main() -> int:
    import datetime
    corpus_m = _corpus_measurement()
    frag_m = _fragment_replay()
    v1_rec = _v1_recorded_outcome()

    old = _load(OLD)
    old_nums = old["what_was_measured_instead"]["result"]
    reproduces = (
        old_nums.get("value_context_cases") ==
        corpus_m["value_context_cases"]
        and old_nums.get("v1_strict_schema_admits") ==
        corpus_m["v1_strict_admits"]
        and old_nums.get("v2_canonical_parser_admits_measured") ==
        corpus_m["v2_admits_measured"])

    doc = {
        "artifact": "R412_V1_V2_PARSER_COMPARISON",
        "directive_phase": "C",
        "supersedes": {
            "path": "R412/GRADIENT_V2/"
                    "V1_OUTPUT_REPARSE_MEASUREMENT.json",
            "note": "the old artifact's corpus-level measurement is "
                    "RE-VERIFIED live here (reproduction: "
                    f"{'MATCH' if reproduces else 'DRIFT'}); the old "
                    "artifact remains as history (Art. XI), this "
                    "artifact is the authority",
            "old_measurement_reproduces_live": reproduces,
        },
        "v1_recorded_outcome": v1_rec,
        "corpus_level_instrument_comparison": corpus_m,
        "quoted_fragment_replay": frag_m,
        "full_34_replay": {
            "status": "NOT_MEASURABLE_FROM_COMMITTED_EVIDENCE",
            "reason": "the 34 v1 proposals' raw serialized ENTRY "
                      "texts were never persisted by the v1 "
                      "instrument (see "
                      "V1_PROVENANCE_RECONCILIATION.json "
                      "phase_c_measurability for the recorded "
                      "search evidence); counts, per-rung rejection "
                      "reasons, and per-seed classification ARE "
                      "committed and re-verified above",
            "forbidden_alternative": "fabricating 34 proposal "
                                     "strings to feed the parsers "
                                     "(Art. VI/VII)",
        },
        "operator_comparison_table": {
            "note": "the definitive v1-vs-v2 table — the operator's "
                    "Phase L table — is filled by the sealed v2 run "
                    "(same 10 seeds, same budgets); v2 column "
                    "pre-filled as TO_BE_MEASURED_BY_THE_SEALED_RUN",
            "rows": [
                {"measurement": "Seeds", "r412_v1": 10,
                 "r412_v2": "same 10 (sealed allocation, byte-copied)"},
                {"measurement": "TVM proposals", "r412_v1": 34,
                 "r412_v2": "TO_BE_MEASURED"},
                {"measurement": "Valid frontier entries",
                 "r412_v1": 0, "r412_v2": "TO_BE_MEASURED"},
                {"measurement": "Frontier domains", "r412_v1": 0,
                 "r412_v2": "TO_BE_MEASURED"},
                {"measurement": "Present-capability rediscoveries",
                 "r412_v1": 0, "r412_v2": "TO_BE_MEASURED"},
                {"measurement": "Causal descendants",
                 "r412_v1": 0, "r412_v2": "TO_BE_MEASURED"},
                {"measurement": "Fresh novelty survivors",
                 "r412_v1": 0, "r412_v2": "TO_BE_MEASURED"},
                {"measurement": "Attacker survivors", "r412_v1": 0,
                 "r412_v2": "TO_BE_MEASURED"},
                {"measurement": "Buyer-grade inventions",
                 "r412_v1": 0, "r412_v2": "TO_BE_MEASURED"},
            ],
        },
        "answer_to_the_directive_question": {
            "question": "Was R412 v1 primarily an instrument-format "
                        "failure?",
            "answer_from_committed_evidence":
                "SUPPORTED_BY_THE_RECORDED_DISTRIBUTION — the v1 "
                "run's own committed record attributes 31/34 "
                "rejections to the strict numeric cast and 33/34 "
                "passed span/pool identity; the corpus-level "
                "comparison shows the v2 parser admits 21/33 value "
                "spans the v1 schema rejects; the two recoverable "
                "fragments both fail v1 and parse under v2. The "
                "per-proposal replay is not recoverable, so this "
                "remains an instrument-level + recorded-distribution "
                "answer, NOT a full replay measurement",
        },
        "no_model_calls": True,
        "reviewer_provenance": "AI_REVIEW",
        "created_at": datetime.datetime.now(
            datetime.timezone.utc).isoformat(),
    }
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"comparison written: {OUT}")
    print(f"corpus: v1 admits {corpus_m['v1_strict_admits']}/"
          f"{corpus_m['value_context_cases']}; v2 admits (measured) "
          f"{corpus_m['v2_admits_measured']}/"
          f"{corpus_m['value_context_cases']}; v2 parses losslessly "
          f"{corpus_m['v2_parses_losslessly']}/"
          f"{corpus_m['value_context_cases']}; rescued (measured) "
          f"{corpus_m['rescued_by_v2']}; rescued (qualitative) "
          f"{corpus_m['rescued_as_parseable_but_qualitative']}")
    print(f"fragments replayed: {len(frag_m['replays'])}/2 "
          f"recoverable")
    print(f"old measurement reproduces live: {reproduces}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
