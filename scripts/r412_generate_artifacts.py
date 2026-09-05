#!/usr/bin/env python3
"""scripts/r412_generate_artifacts.py — R412 gradient v2 artifact generator.

Generates (by MEASUREMENT, not assertion):
  1. R412/GRADIENT_V2/V1_OUTPUT_REPARSE_MEASUREMENT.json — the Step 4
     record: the mandated measurement (re-parse the 34 v1 proposals) is
     honestly NOT_MEASURABLE (the proposals are not present in this
     workspace); what IS measured is the corpus-level instrument
     comparison (v1 strict schema vs v2 canonical parser over the frozen
     calibration corpus).
  2. R412/GRADIENT_V2/TRANSPORT_PROBE.json — the measured LLM transport
     liveness state (one tiny pinned probe call; R401-WC2 discipline).
  3. R412/GRADIENT_V2/R412_GRADIENT_V2_PREREGISTRATION.json — the Step 7
     seal: sha256 of every sealed artifact, honest NOT_VERIFIABLE states
     for every v1-dependent input, and the BLOCKED run gate.

The script FAILS LOUDLY (exit 1, no artifacts written) if the parser
disagrees with the frozen calibration corpus on any case or fixture —
a corpus disagreement is a parser defect, never a corpus edit.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/home/z/my-project/audit_ws/repo")
V2DIR = REPO / "R412" / "GRADIENT_V2"
sys.path.insert(0, str(V2DIR))

from tvm_v2 import (  # noqa: E402
    CanonicalValue,
    CONTEXT_VALUE,
    SPAN_AMBIGUOUS_REQUIRES_INDEX,
    SPAN_INDEX_OUT_OF_RANGE,
    SPAN_NOT_FOUND,
    SPAN_VERIFIED,
    V1_PREDICATE_LABEL,
    classify_signal,
    parse_value_span,
    signal_vocabulary_report,
    validate_family_map,
    v1_value_admissible,
    v1_year_admissible,
    verify_span_binding,
)
from tvm_v2.value_parser import METHOD_REGISTRY  # noqa: E402

UTC = datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Calibration measurement (parser vs frozen corpus; no LLM anywhere)
# ---------------------------------------------------------------------------

def run_calibration() -> dict:
    corpus = json.loads(
        (V2DIR / "TVM_V2_PARSER_CALIBRATION_CORPUS.json").read_text(
            encoding="utf-8"))
    results = []
    failures = []
    for case in corpus["cases"]:
        exp = case["expected"]
        got = parse_value_span(case["raw_span"],
                               case["field_context"]).to_dict()
        ok = True
        detail = {"case_id": case["id"], "category": case["category"],
                  "raw_span": case["raw_span"],
                  "expected_representation": exp["representation"],
                  "got": got}
        for key in ("representation", "normalization_method", "unit",
                    "year", "year_min", "year_max",
                    "approximation_marker", "open_bound",
                    "qualitative_term", "malformed_reason"):
            if key in exp and exp[key] != got.get(key):
                ok = False
        for key in ("normalized_value", "normalized_min",
                    "normalized_max"):
            if key in exp:
                ev, gv = exp[key], got.get(key)
                if (ev is None) != (gv is None) or (
                        ev is not None and abs(float(ev) - float(gv)) > 1e-9):
                    ok = False
        if got.get("raw_source_span") != case["raw_span"]:
            ok = False
        # Determinism: parse twice, require byte-identical dicts.
        again = parse_value_span(case["raw_span"],
                                 case["field_context"]).to_dict()
        if again != got:
            ok = False
        if not ok:
            failures.append(case["id"])
        results.append({**detail, "pass": ok})

    fixture_results = []
    for fx in corpus["verification_fixtures"]:
        sv = verify_span_binding(fx["span"], fx["source_text"],
                                 fx["occurrence_index"])
        ok = (sv.verdict == fx["expected_verdict"]
              and sv.occurrences == fx["expected_occurrences"])
        if not ok:
            failures.append(fx["id"])
        fixture_results.append({"fixture_id": fx["id"],
                                "verdict": sv.verdict,
                                "occurrences": sv.occurrences,
                                "pass": ok})

    if failures:
        print("CALIBRATION FAILURES: " + ", ".join(failures))
        for r in results:
            if not r["pass"]:
                print(json.dumps(r, ensure_ascii=False))
        for r in fixture_results:
            if not r["pass"]:
                print(json.dumps(r))
        sys.exit(1)

    by_cat = {}
    for r in results:
        by_cat.setdefault(r["category"], 0)
        by_cat[r["category"]] += 1
    return {
        "corpus_sha256": sha256_file(
            V2DIR / "TVM_V2_PARSER_CALIBRATION_CORPUS.json"),
        "total_cases": len(results),
        "cases_passed": sum(1 for r in results if r["pass"]),
        "verification_fixtures_total": len(fixture_results),
        "verification_fixtures_passed": sum(
            1 for r in fixture_results if r["pass"]),
        "category_counts": by_cat,
        "llm_judge_used": False,
        "determinism_check": "every case parsed twice; byte-identical",
        "per_case": results,
        "per_fixture": fixture_results,
    }


# ---------------------------------------------------------------------------
# 2. Corpus-level v1-strict vs v2 instrument comparison (Step 4, measured)
# ---------------------------------------------------------------------------

def run_instrument_comparison() -> dict:
    corpus = json.loads(
        (V2DIR / "TVM_V2_PARSER_CALIBRATION_CORPUS.json").read_text(
            encoding="utf-8"))
    value_cases = [c for c in corpus["cases"]
                   if c["field_context"] == CONTEXT_VALUE]
    year_cases = [c for c in corpus["cases"] if c["field_context"] == "YEAR"]

    v1_admitted = []
    v1_rejected = []
    for c in value_cases:
        span = c["raw_span"]
        if v1_value_admissible(span):
            v1_admitted.append(c["id"])
        else:
            v1_rejected.append(c["id"])

    v2_admitted = []
    v2_rejected = []
    for c in value_cases:
        rep = c["expected"]["representation"]
        # v2 admits any representation that is a measured numeric claim
        # (POINT/RANGE/INEQUALITY); qualitative and NOT_NUMERIC are
        # admissible PARSE results but not measured values; MALFORMED is
        # rejected outright.
        if rep in ("POINT", "RANGE", "INEQUALITY"):
            v2_admitted.append(c["id"])
        else:
            v2_rejected.append(c["id"])

    recovered = [cid for cid in v1_rejected if cid in v2_admitted]
    v1_year_admitted = [c["id"] for c in year_cases
                        if v1_year_admissible(c["raw_span"])]

    return {
        "comparison_scope": "CORPUS_LEVEL_INSTRUMENT_COMPARISON",
        "v1_predicate_label": V1_PREDICATE_LABEL,
        "value_context_cases": len(value_cases),
        "v1_strict_schema_admits": len(v1_admitted),
        "v1_strict_schema_admits_ids": v1_admitted,
        "v1_strict_schema_rejects": len(v1_rejected),
        "v1_strict_schema_rejects_ids": v1_rejected,
        "v2_canonical_parser_admits_measured": len(v2_admitted),
        "v2_canonical_parser_admits_ids": v2_admitted,
        "serialization_failure_class_size_on_corpus": len(recovered),
        "serialization_failure_class_ids": recovered,
        "serialization_failure_class_detail": (
            "These spans are exactly the class a strict POINT-only "
            "schema rejects as VALUE_OR_YEAR_NOT_NUMERIC and the v2 "
            "canonical parser admits as measured evidence after "
            "lossless deterministic normalization (range, uncertainty, "
            "approximation, inequality, scientific notation, "
            "unit-bearing forms)."
        ),
        "year_context_cases": len(year_cases),
        "v1_strict_year_admits": len(v1_year_admitted),
        "v1_strict_year_admits_ids": v1_year_admitted,
        "never_manufactured_precision_check": (
            "approximation cases (C005, C022) admit as POINT with "
            "approximation_marker=true; they are NEVER widened to ranges"
        ),
        "interpretation_guard": (
            "This corpus-level comparison is an INSTRUMENT measurement. "
            "It is NOT the mandated Step 4 measurement (which requires "
            "the 34 actual v1 proposals, not present in this workspace) "
            "and it does NOT establish that any specific fraction of the "
            "34 would recover."
        ),
    }


# ---------------------------------------------------------------------------
# 3. Transport probe record (measured earlier this session; facts below)
# ---------------------------------------------------------------------------

def build_transport_probe() -> dict:
    return {
        "artifact": "R412_TRANSPORT_PROBE",
        "probe_time_utc": "2026-09-06T00:27:37Z",
        "probe_class": "LLM_TRANSPORT_LIVENESS (R401-WC2 discipline: tiny pinned call per provider; dead/absent = recorded absent; this is an infrastructure probe, NOT a gradient/discovery model call)",
        "gateway_script": "scripts/zai_gateway.mjs",
        "gateway_script_sha256": sha256_file(REPO / "scripts" / "zai_gateway.mjs"),
        "endpoint": "127.0.0.1:8790 (probe instance)",
        "healthz": {"status": "ok"},
        "probe_call": {
            "model": "glm-4-plus",
            "messages": 1,
            "max_tokens": 10,
            "completion": "TRANSPORT_ALIVE",
            "usage": {"prompt_tokens": 17, "completion_tokens": 5,
                      "total_tokens": 22},
        },
        "verdict": "LIVE",
        "gradient_model_calls_made": 0,
        "discovery_model_calls_made": 0,
        "note": "The gateway is process-scoped (the sandbox reaps detached processes); a real run must start the gateway for the duration of the run per scripts/zai_gw_run.sh. The engine's other providers have no credentials in this session (.env.keys absent).",
    }


# ---------------------------------------------------------------------------
# 4. Preregistration (Step 7 seal)
# ---------------------------------------------------------------------------

def build_preregistration(calib: dict, comparison: dict) -> dict:
    prompt_files = sorted((V2DIR / "PROMPTS").glob("*.json"))
    prompt_hashes = {
        p.stem: sha256_file(p) for p in prompt_files
    }
    return {
        "artifact": "R412_GRADIENT_V2_PREREGISTRATION",
        "preregistration_version": "1.0.0",
        "sealed": utc_now(),
        "directive": "CODER directive (operator), R412 gradient v2, Step 7: seal v2 BEFORE any v2 discovery calls",

        "v1_provenance": {
            "claimed_v1_seal_commit": "5084673f",
            "verification_state": "NOT_VERIFIABLE_IN_THIS_WORKSPACE",
            "v1_figures_provenance": "OPERATOR_DIRECTIVE_REPORTED",
            "v1_figures": {"seeds": 10, "frontier_entries": 0,
                           "proposals": 34,
                           "value_or_year_not_numeric_failures": 31},
            "v1_result_modified": False,
            "v1_preregistration_modified": False,
            "temporal_control_arm_modified": False,
            "v1_instrument_finding": {
                "path": "R412/R412_GRADIENT_V1_INSTRUMENT_FINDING.json",
                "sha256": sha256_file(
                    REPO / "R412" / "R412_GRADIENT_V1_INSTRUMENT_FINDING.json"),
            },
            "full_evidence": "See R412/R412_GRADIENT_V1_INSTRUMENT_FINDING.json v1_provenance_verification: exhaustive filesystem/git/reflog/fsck searches found no R411/R412 artifacts; the claimed seal commits are not valid objects; the remote is unreachable without credentials (private repo).",
        },

        "v2_parser_specification": {
            "module": "R412/GRADIENT_V2/tvm_v2/value_parser.py",
            "sha256": sha256_file(V2DIR / "tvm_v2" / "value_parser.py"),
            "canonical_representations": ["POINT", "RANGE", "INEQUALITY",
                                          "ORDINAL_QUALITATIVE",
                                          "NOT_NUMERIC", "MALFORMED"],
            "canonical_value_fields": [
                "raw_source_span", "normalized_value", "normalized_min",
                "normalized_max", "unit", "unit_raw", "year", "year_min",
                "year_max", "normalization_method",
                "approximation_marker", "open_bound",
                "qualitative_term", "malformed_reason", "parse_context",
            ],
            "method_registry": METHOD_REGISTRY,
            "invariants": [
                "deterministic pure function",
                "exact decimal arithmetic",
                "never manufactures precision",
                "raw span retained byte-exactly",
                "fail-closed with explicit malformed reasons",
            ],
        },

        "parser_calibration_corpus": {
            "path": "R412/GRADIENT_V2/TVM_V2_PARSER_CALIBRATION_CORPUS.json",
            "sha256": calib["corpus_sha256"],
            "total_cases": calib["total_cases"],
            "verification_fixtures": calib["verification_fixtures_total"],
            "all_passed": True,
            "llm_judge_used": False,
            "ground_truth_authority": "operator directive exemplars + pre-specified ruleset (authored before the parser; Constitution Article VIII)",
        },

        "normalization_rules": {
            "path": "R412/GRADIENT_V2/NORMALIZATION_RULES.json",
            "sha256": sha256_file(V2DIR / "NORMALIZATION_RULES.json"),
            "core_rules": [
                "uncertainty to range is lossless (± bound IS the interval)",
                "approximation is retained, never widened to a range",
                "inequalities keep their open bound open",
                "no unit conversion, no rounding, no digit extension",
                "double separators / inverted ranges / dangling connectors are MALFORMED",
            ],
        },

        "capability_family_layer": {
            "path": "R412/GRADIENT_V2/CAPABILITY_FAMILY_MAP.json",
            "sha256": sha256_file(V2DIR / "CAPABILITY_FAMILY_MAP.json"),
            "module": "R412/GRADIENT_V2/tvm_v2/capability_family.py",
            "module_sha256": sha256_file(
                V2DIR / "tvm_v2" / "capability_family.py"),
            "families_seeded": 1,
            "seed_source": "OPERATOR_DIRECTIVE_EXAMPLE only; no families invented (Constitution Article XLIII)",
        },

        "signal_policy": {
            "module": "R412/GRADIENT_V2/tvm_v2/signal_policy.py",
            "module_sha256": sha256_file(
                V2DIR / "tvm_v2" / "signal_policy.py"),
            "primary_technical": ["performance", "cost", "efficiency",
                                   "reliability", "manufacturing",
                                   "deployment"],
            "explanatory_only": ["investment", "talent",
                                 "experimental_concentration"],
            "rule": "An explanatory-class signal can NEVER appear as a TVM entry's capability evidence; the validator rejects it deterministically.",
        },

        "evidence_contract": {
            "module": "R412/GRADIENT_V2/tvm_v2/evidence_contract.py",
            "module_sha256": sha256_file(
                V2DIR / "tvm_v2" / "evidence_contract.py"),
            "span_binding": "byte-exact substring occurrence; case-insensitive fallback is FORBIDDEN for numerical spans (stricter than the a2 mechanism-span check, per Constitution Article II)",
            "ambiguity": "recorded as SPAN_AMBIGUOUS_REQUIRES_INDEX, never silently first-matched",
            "tvm_entry_schema": "v1 13-field contract (unchanged) + canonical_value + signal_class + trajectory_dimension + capability_family_ref + occurrence_index",
        },

        "prompt_hashes": {
            "provenance": "NEW_V2_PROMPTS; the v1 prompt files are NOT recoverable in this workspace (recorded, not fabricated)",
            "files": prompt_hashes,
        },

        "v1_output_reparse_measurement": {
            "path": "R412/GRADIENT_V2/V1_OUTPUT_REPARSE_MEASUREMENT.json",
            "sha256": sha256_file(V2DIR / "V1_OUTPUT_REPARSE_MEASUREMENT.json"),
            "mandated_measurement_state": "NOT_MEASURABLE_V1_OUTPUTS_NOT_PRESENT",
        },

        "transport_probe": {
            "path": "R412/GRADIENT_V2/TRANSPORT_PROBE.json",
            "sha256": sha256_file(V2DIR / "TRANSPORT_PROBE.json"),
            "verdict": "LIVE (measured; 1 liveness probe call, 0 gradient calls)",
        },

        "generator": {
            "script": "scripts/r412_generate_artifacts.py",
            "sha256": sha256_file(REPO / "scripts" / "r412_generate_artifacts.py"),
        },

        "population_hash": {
            "state": "NOT_VERIFIABLE",
            "reason": "The R411/R412 population artifacts (RAW_R411_ACCEPTED 550 -> UNIQUE_SCORED_CANDIDATES 400 -> 13 technical deaths, as reported in the recovery-arm directive) are NOT present in this workspace. No population may be invented (Constitution Articles VI, XLIII): the population defines which failure records the experiment recovers from.",
        },

        "seed_allocation": {
            "state": "NOT_VERIFIABLE",
            "reason": "The v1 frozen 10-seed allocation is NOT present in this workspace. The directive requires rerunning the SAME seeds for a clean instrument comparison; with no recorded seeds, any seeds chosen now would be a design change. A fresh allocation requires explicit operator authorization recorded as a new directive.",
        },

        "tvm_snapshot_hash": {
            "state": "NOT_BUILDABLE_YET",
            "reason": "A TVM snapshot requires (a) the population's limiting capabilities, (b) capability-family expansion, and (c) live retrieval with span-verified entries. (a) is absent; therefore no TVM snapshot may be frozen now. The v2 instrument (parser/verifier/policies) is frozen by this preregistration instead.",
        },

        "model_pin": {
            "provider": "zai",
            "model": "glm-4-plus",
            "transport": "sandbox-local OpenAI-compatible gateway (scripts/zai_gateway.mjs)",
            "gateway_script_sha256": sha256_file(
                REPO / "scripts" / "zai_gateway.mjs"),
            "substitution": "FORBIDDEN (max_preference_fallback=0 discipline; any provider change requires a new preregistration)",
            "transport_probe": "R412/GRADIENT_V2/TRANSPORT_PROBE.json (verdict LIVE, measured; sha256 recorded above)",
        },

        "cost_budget": {
            "gradient_calls_spent_before_seal": 0,
            "liveness_probe_calls": 1,
            "max_gradient_calls_per_seed": 40,
            "max_total_gradient_calls": 400,
            "max_usd_equivalent": 0.0,
            "note": "Zero gradient/discovery model calls have been made. The only model call in this session is the single 22-token transport liveness probe.",
        },

        "stopping_rules": [
            "STOP on 3 consecutive transport failures (recorded as TRANSPORT_BLOCKED, never as a scientific result)",
            "STOP when the cost budget is exhausted (recorded as BUDGET_EXHAUSTED)",
            "STOP if the seal verification fails at any checkpoint (Constitution Article XIV: red = stop)",
            "STOP if any TVM entry fails span verification twice with the same span (serialization defect class; instrument review, not evidence reinterpretation)",
            "NO quota on successes or survivors (operator directive: no quota; Article LVI: optimize information gain, not counts)"
        ],

        "success_criterion": {
            "chain": "REAL MEASURED FRONTIER -> CAUSAL MECHANISM BACKCAST -> TRANSFERABLE TO TARGET -> CAPABILITIES AVAILABLE TODAY -> NEW CAUSAL ARCHITECTURE",
            "explicitly_not_success": [
                "more descendants",
                "more TVM domains found",
                "candidates that look technologically sophisticated",
                "'use technology X in industry Y'",
                "better sensor/material/processor substitution",
                "did the model generate something clever"
            ],
            "central_report_question": "Did an existing technology from a faster-moving domain create a genuinely new architecture/application in the target field?",
        },

        "run_gate": {
            "state": "BLOCKED_PENDING_OPERATOR_INPUT",
            "blocking_fields": ["population_hash", "seed_allocation",
                                "tvm_snapshot_hash"],
            "fail_closed_rule": "No gradient/discovery model call may be made while any blocking field is unresolved (Constitution Article XIV; the operator's pre-seal constraint).",
            "unblock_paths": [
                "PATH_A: provide the GitHub PAT so the remote can be fetched and checked for the R407-R412 commits (the private remote may carry the sealed v1 artifacts from the workspace that produced them).",
                "PATH_B: restore/point this session at the workspace or repository state that contains the sealed R412 v1 artifacts (population, TVM-v0, prompts, model pins, 10-seed allocation, and the 34 v1 proposals).",
                "PATH_C: explicit operator authorization to constitute a NEW population and a NEW 10-seed allocation, recorded as a new directive and a new preregistration (this abandons the same-seeds instrument comparison by operator decision, not silently)."
            ],
        },

        "seal_verification": {
            "script": "scripts/r412_seal_verify.py",
            "command": "python3 scripts/r412_seal_verify.py",
            "expected_output": "SEAL_VERIFIED with RUN_GATE=BLOCKED_PENDING_OPERATOR_INPUT",
        },
    }


def main() -> int:
    print("[r412] running calibration (parser vs frozen corpus)...")
    calib = run_calibration()
    print(f"[r412] calibration: {calib['cases_passed']}/{calib['total_cases']} cases, "
          f"{calib['verification_fixtures_passed']}/{calib['verification_fixtures_total']} fixtures PASS")

    print("[r412] running corpus-level instrument comparison (v1 strict vs v2)...")
    comparison = run_instrument_comparison()
    print(f"[r412] v1 strict admits {comparison['v1_strict_schema_admits']}/"
          f"{comparison['value_context_cases']} value spans; v2 admits "
          f"{comparison['v2_canonical_parser_admits_measured']}; serialization-failure "
          f"class size on corpus: "
          f"{comparison['serialization_failure_class_size_on_corpus']}")

    fam_ok, fam_issues = validate_family_map()
    if not fam_ok:
        print("[r412] capability family map INVALID: " + str(fam_issues))
        return 1
    print("[r412] capability family map valid (1 seeded family, operator example)")

    measurement = {
        "artifact": "R412_V1_OUTPUT_REPARSE_MEASUREMENT",
        "directive_step": 4,
        "created": utc_now(),
        "mandated_measurement": {
            "question": "How many of the 34 v1 proposals become admissible after lossless deterministic normalization?",
            "measurement_state": "NOT_MEASURABLE",
            "reason": "V1_OUTPUTS_NOT_PRESENT_IN_REPOSITORY",
          "directive_quote": "Take the 34 v1 proposals. Ask: How many would become admissible after lossless deterministic normalization? This number is critical. ... Do not guess. Measure.",
            "honest_answer": "The 34 v1 proposals are not present in this workspace (verification in R412/R412_GRADIENT_V1_INSTRUMENT_FINDING.json). The number cannot be measured here. It is NOT guessed, NOT estimated, and NOT defaulted to any value (Constitution Articles VI, XXV: unknown stays unknown).",
            "what_would_unblock_it": "The 34 v1 proposal records (from the sealed v1 run) supplied via PATH_A/PATH_B in the preregistration run gate: a remote fetch with credentials, or the workspace that contains them.",
        },
        "what_was_measured_instead": {
            "description": "The same question answered at the INSTRUMENT level on the frozen calibration corpus: which value forms does a v1-class strict POINT-only schema reject as VALUE_OR_YEAR_NOT_NUMERIC that the v2 canonical parser admits as measured evidence after lossless deterministic normalization.",
            "result": comparison,
        },
        "calibration_summary": {
            "corpus_sha256": calib["corpus_sha256"],
            "cases": f"{calib['cases_passed']}/{calib['total_cases']}",
            "fixtures": f"{calib['verification_fixtures_passed']}/{calib['verification_fixtures_total']}",
            "llm_judge_used": False,
        },
        "alternative_explanations": [
            "If, when the v1 proposals are recovered, MOST recover under v2 normalization: the first run was primarily a serialization failure (the operator's hypothesis).",
            "If FEW recover: the evidence itself (retrieved spans) may be inadequate — a different defect class requiring retrieval/evidence work, not parser work.",
            "These alternatives CANNOT be ranked from this workspace; the measurement is pending the artifacts."
        ],
    }
    write_json(V2DIR / "V1_OUTPUT_REPARSE_MEASUREMENT.json", measurement)

    probe = build_transport_probe()
    write_json(V2DIR / "TRANSPORT_PROBE.json", probe)

    prereg = build_preregistration(calib, comparison)
    write_json(V2DIR / "R412_GRADIENT_V2_PREREGISTRATION.json", prereg)

    print("[r412] artifacts written:")
    for name in ("V1_OUTPUT_REPARSE_MEASUREMENT.json",
                 "TRANSPORT_PROBE.json",
                 "R412_GRADIENT_V2_PREREGISTRATION.json"):
        p = V2DIR / name
        print(f"       {p} (sha256 {sha256_file(p)[:16]}...)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
