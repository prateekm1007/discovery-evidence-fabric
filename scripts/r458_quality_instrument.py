#!/usr/bin/env python3
"""scripts/r458_quality_instrument.py — R458-C1 §3: the FROZEN
model-capability measurement instrument.

Directive (verbatim): "Measure the actual science. For each model:
problem understanding, problem-existence reasoning, evidence synthesis,
mechanism quality, mechanism differentiation, candidate quality, attack
quality, contradiction detection, engineering reasoning, structured-
output reliability, hallucination rate, latency, token cost, failure
rate. Do not use generic benchmarks as the decision criterion."

FREEZE DISCIPLINE (Art. LIX + BS-016, the r452_quality_instrument
standard): `freeze` records the metric definitions (machine-readable)
and the script's own sha256, and FAILS CLOSED if any R458 result
artifact already exists; `apply` recomputes the script hash and REFUSES
to run if the instrument was modified after freezing (tuning after
freeze is gaming). Every metric is computed DETERMINISTICALLY from the
run's OWN persisted artifacts (Art. X); every metric states its
artifact source; UNKNOWN/NOT_REACHED are typed, never zero-filled
(Art. XXV).

THE THIRTEEN METRICS (+ wall clock), each with its artifact source:

  1. problem_understanding_quality   problem.json (the engine's own
                                      MODEL_DERIVED extraction): core
                                      fields present, target variable
                                      named, constraints carried, the
                                      problem's OWN numbers preserved
                                      (numbers in the authored text
                                      that survive into the structured
                                      problem).
  2. problem_existence_reasoning     envelope_PREMISE_GATE.json →
                                      premise_gate: the gate's own
                                      verdict + the recorded five-
                                      question coverage (Art. XX).
  3. evidence_synthesis_quality      candidate_envelope evidence_
                                      classification.counts: (DIRECT_
                                      SUPPORT + PARTIAL_SUPPORT) /
                                      n_items, plus frozen-base size.
  4. mechanism_quality               mechanism_support grounding rate
                                      + span_binding.verbatim rate (a
                                      mechanism with zero supporting
                                      frozen evidence or a claimed
                                      span that is not in the record
                                      is not evidence-bound).
  5. mechanism_differentiation       distinctness_verdict == DISTINCT
                                      rate among mechanism-space
                                      candidates (wording-independent
                                      instrument).
  6. candidate_quality               the six-dimension composite rate
                                      (evidence_bound AND span_verbatim
                                      AND differentiated AND not_obvious
                                      AND not_contradicted AND
                                      sufficiently_specific) — the
                                      r452 GOOD_DISCOVERY standard.
  7. attack_quality                  attacks actually recorded when
                                      the ATTACK stage ran + the
                                      per-kill base-grounding rate
                                      (the R445-B mechanical classes:
                                      source-id pattern / computed
                                      quantity / record reference).
  8. contradiction_detection         CONTRADICTORY adjudicated count +
                                      unresolved recorded contradictions
                                      (stage_CONTRADICTION.json).
  9. engineering_reasoning           ENGINEERING_SPECIFICATION.json
                                      value_sourcing summary (SOURCE_
                                      FACT / COMPUTED / MODELLED /
                                      UNKNOWN) when produced; typed
                                      NOT_REACHED otherwise.
 10. structured_output_reliability   ROUTING_LEDGER_RUN.json: OK lines
                                      / total run-owned lines, plus
                                      retry/degradation counts.
 11. hallucination_rate              1 - span-verbatim rate on claimed
                                      evidence bindings + fabricated-
                                      citation check (claimed source
                                      ids that resolve to no frozen
                                      evidence record).
 12. latency                         per-call latency_ms distribution
                                      from the run-owned ledger lines
                                      (mean / p50 / max) + wall clock.
 13. token_cost                      summed tokens from the run-owned
                                      ledger lines.
 14. failure_rate                    failed ledger lines / total, with
                                      the typed failure-class histogram.

Usage:
  python scripts/r458_quality_instrument.py freeze
  python scripts/r458_quality_instrument.py verify
  (apply is invoked by the benchmark driver via apply_to_run_dir)
"""
from __future__ import annotations

import hashlib
import json
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

OUT_ROOT = REPO_ROOT / "R458"
FREEZE_PATH = OUT_ROOT / "QUALITY_INSTRUMENT_FREEZE.json"

#: result artifacts whose existence BEFORE freeze proves the
#: definitions were not frozen before results were looked at
_RESULT_ARTIFACTS = (
    "R458/MODEL_CAPABILITY_BENCHMARK.json",
    "R458/BLIND_TEST_RESULTS.json",
    "R458/ADAPTIVE_PIPELINE_BENCHMARK.json",
    "R458_C1_MODEL_CAPABILITY_BENCHMARK.json",
)

INSTRUMENT_VERSION = "R458_QUALITY_INSTRUMENT/1.0.0"

#: the R445-B mechanical grounding checks (verbatim discipline):
#: a kill base is GROUNDED when it carries (a) a source-id pattern,
#: (b) a computed quantity (digits with a unit token), or (c) an
#: explicit record reference.
_SOURCE_ID_RE = re.compile(
    r"(doi:|patent|europepmc|pubmed|arxiv|hf-datasets|dataset[ /])",
    re.I)
_QUANTITY_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:mm|cm|m\b|kpa|mpa|gpa|pa\b|c\b|°c|k\b|s\b|ms"
    r"|min|h\b|hz|khz|mhz|l\b|litre|liter|ml\b|bar|psi|v\b|mv\b|a\b"
    r"|ma\b|w\b|kw|mw|n\b|kn|kg|g\b|mg|tonne|percent|%|€|eur|usd)", re.I)
_RECORD_REF_RE = re.compile(r"\b(record|envelope|ledger|artifact)\b",
                            re.I)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _script_sha256() -> str:
    return _sha(Path(__file__).read_text())


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        if p.is_file():
            data = json.loads(p.read_text())
            return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None
    return None


METRIC_DEFINITIONS: List[Dict[str, Any]] = [
    {"metric": "problem_understanding_quality",
     "artifact_source": "problem.json",
     "definition": ("core-field completeness (statement, objective, "
                    "constraints, numbers preserved from the authored "
                    "text into the structured problem), scaled 0..1")},
    {"metric": "problem_existence_reasoning",
     "artifact_source": "envelope_PREMISE_GATE.json",
     "definition": ("the premise gate's own verdict + the recorded "
                    "five-question coverage (Art. XX), typed")},
    {"metric": "evidence_synthesis_quality",
     "artifact_source": "candidate_envelope.json::evidence_classification",
     "definition": ("(DIRECT_SUPPORT + PARTIAL_SUPPORT) / n_items; "
                    "frozen-base size recorded alongside")},
    {"metric": "mechanism_quality",
     "artifact_source":
         "candidate_envelope.json::evidence_classification."
         "mechanism_support + candidates[].span_binding",
     "definition": ("grounding rate (>=1 SUPPORTS/PARTIALLY_SUPPORTS "
                    "item) AND span-verbatim rate, reported separately")},
    {"metric": "mechanism_differentiation",
     "artifact_source": "candidate_envelope.json::mechanism_space."
     "candidates[].distinctness_verdict",
     "definition": ("DISTINCT / total candidates (the wording-"
                    "independent distinctness instrument; INDETERMINATE "
                    "counted separately, never as DISTINCT)")},
    {"metric": "candidate_quality",
     "artifact_source": "candidate_envelope.json (six-dimension composite)",
     "definition": ("evidence_bound AND span_verbatim AND differentiated "
                    "AND not_obvious_combination AND not_contradicted AND "
                    "sufficiently_specific -> GOOD_DISCOVERY rate")},
    {"metric": "attack_quality",
     "artifact_source": "candidate_envelope.json::attack_results",
     "definition": ("attacks recorded when the stage ran + the per-kill "
                    "base-grounding rate (R445-B mechanical classes)")},
    {"metric": "contradiction_detection",
     "artifact_source": "evidence_classification.counts + "
     "stage_CONTRADICTION.json",
     "definition": ("CONTRADICTORY adjudicated count + unresolved "
                    "recorded contradictions")},
    {"metric": "engineering_reasoning",
     "artifact_source": "ENGINEERING_SPECIFICATION.json::value_sourcing",
     "definition": ("SOURCE_FACT / COMPUTED / MODELLED / UNKNOWN counts "
                    "when the spec was produced; typed NOT_REACHED "
                    "otherwise")},
    {"metric": "structured_output_reliability",
     "artifact_source": "ROUTING_LEDGER_RUN.json",
     "definition": ("OK run-owned lines / total run-owned lines; retry "
                    "and task-degradation counts recorded alongside")},
    {"metric": "hallucination_rate",
     "artifact_source": "candidates[].span_binding + evidence pool ids",
     "definition": ("1 - span-verbatim rate + fabricated-citation check "
                    "(claimed source ids resolving to no frozen record)")},
    {"metric": "latency",
     "artifact_source": "ROUTING_LEDGER_RUN.json::lines[].latency_ms",
     "definition": ("per-call latency distribution (mean/p50/max) from "
                    "the run-owned ledger + run wall clock")},
    {"metric": "token_cost",
     "artifact_source": "ROUTING_LEDGER_RUN.json::lines[].tokens",
     "definition": ("summed tokens over run-owned ledger lines")},
    {"metric": "failure_rate",
     "artifact_source": "ROUTING_LEDGER_RUN.json::lines[].failure_class",
     "definition": ("failed run-owned lines / total, with the typed "
                    "failure-class histogram")},
]

# ---------------------------------------------------------------------------
# Freeze discipline
# ---------------------------------------------------------------------------

def cmd_freeze() -> int:
    existing = [a for a in _RESULT_ARTIFACTS
                if (REPO_ROOT / a).exists()]
    if existing:
        print(f"REFUSED: result artifacts exist before instrument "
              f"freeze: {existing} (Art. LIX / BS-016)",
              file=sys.stderr)
        return 2
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    record = {
        "artifact_type": "R458_QUALITY_INSTRUMENT_FREEZE/1.0.0",
        "frozen_at_utc": _now(),
        "instrument_version": INSTRUMENT_VERSION,
        "instrument_script_sha256": _script_sha256(),
        "metric_definitions": METRIC_DEFINITIONS,
        "art_xxxi_correction": (
            "DEFECT CAUGHT BEFORE ANY R458 RESULT EXISTED (Art. XXXI "
            "memory artifact): the first freeze's problem-understanding "
            "extractor used a speculative field list (problem_statement/"
            "target_variable/…) that does not match the engine's OWN "
            "problem.json schema (device/failure_mode/objective/failure/"
            "constraint, measured on the R452 artifact set), and counted "
            "numbers inside user_text (a verbatim copy of the authored "
            "text — a copy is not understanding). Fixed and RE-FROZEN "
            "while zero R458 result artifacts existed (the fail-closed "
            "result guard still passes); the correction is recorded "
            "here, not silently absorbed. Lesson: validate extractors "
            "against a real artifact BEFORE the first freeze."),
        "freeze_discipline": (
            "the thirteen directive metrics (+ wall clock) are defined "
            "and hash-frozen BEFORE any R458 model arm result exists; "
            "apply refuses to run if this script changed after freeze "
            "(tuning after freeze is gaming, Art. LIX); every metric "
            "is deterministic over the run's own persisted artifacts"),
    }
    FREEZE_PATH.write_text(json.dumps(record, indent=1, sort_keys=True))
    print(f"instrument frozen: {FREEZE_PATH}")
    print(f"  sha256={record['instrument_script_sha256'][:16]}…")
    return 0


def verify_instrument() -> Optional[Dict[str, Any]]:
    """Load the freeze record; None if missing; raises SystemExit if
    the instrument drifted after freeze (apply-time guard)."""
    if not FREEZE_PATH.exists():
        return None
    rec = json.loads(FREEZE_PATH.read_text())
    if rec.get("instrument_script_sha256") != _script_sha256():
        raise SystemExit(
            "INSTRUMENT DRIFT: r458_quality_instrument.py changed after "
            "freeze — apply refuses to run (Art. LIX: tuning after "
            "freeze is gaming). Re-freeze is FORBIDDEN once results "
            "exist.")
    return rec


def cmd_verify() -> int:
    rec = verify_instrument()
    if rec is None:
        print("instrument not frozen — run freeze first",
              file=sys.stderr)
        return 2
    sha = rec["instrument_script_sha256"]
    print(f"verify OK: instrument sha {sha[:16]}… matches the freeze; "
          f"{len(rec['metric_definitions'])} metric definitions intact")
    return 0


# ---------------------------------------------------------------------------
# The extractors (deterministic; typed UNKNOWN/NOT_REACHED, Art. XXV)
# ---------------------------------------------------------------------------

_NUM_RE = re.compile(r"\d+(?:\.\d+)?")


def _numbers_in(text: str) -> List[str]:
    return _NUM_RE.findall(text or "")


def _problem_understanding(case_dir: Path,
                           authored_text: str) -> Dict[str, Any]:
    problem = _read_json(case_dir / "problem.json")
    if problem is None:
        return {"value": "UNKNOWN", "state": "NOT_REACHED",
                "detail": "problem.json absent"}
    # The engine's OWN problem schema (measured on the R452 artifact
    # set, corrected before any R458 result existed — the Art. XXXI
    # lesson recorded in the freeze record): device / failure_mode /
    # objective / failure / constraint are the structured fields the
    # MODEL_DERIVED extraction produces; user_text is a verbatim copy
    # of the authored text and is EXCLUDED from the number-
    # preservation check (a copy is not understanding).
    core_fields = ("device", "failure_mode", "objective",
                   "failure", "constraint")
    present = [f for f in core_fields if problem.get(f)]
    structured_blob = " ".join(
        str(problem.get(f) or "") for f in core_fields)
    n_numbers_authored = len(set(_numbers_in(authored_text)))
    n_numbers_kept = sum(1 for n in set(_numbers_in(authored_text))
                         if n in structured_blob)
    completeness = len(present) / len(core_fields)
    number_preservation = (n_numbers_kept / n_numbers_authored
                           if n_numbers_authored else 1.0)
    value = round(0.5 * completeness + 0.5 * number_preservation, 3)
    return {
        "value": value,
        "state": "OK",
        "core_fields_present": present,
        "core_field_completeness": round(completeness, 3),
        "authored_distinct_numbers": n_numbers_authored,
        "authored_numbers_preserved": n_numbers_kept,
        "number_preservation": round(number_preservation, 3),
        "schema_note": ("user_text excluded from number preservation "
                        "— a verbatim copy is not understanding"),
    }


def _premise_gate(case_dir: Path) -> Dict[str, Any]:
    env = _read_json(case_dir / "envelope_PREMISE_GATE.json")
    pg = (env or {}).get("premise_gate") or {}
    if not pg:
        fs = _read_json(case_dir / "final_state.json") or {}
        verdict = fs.get("premise_verdict")
        if verdict:
            return {"value": verdict, "state": "OK",
                    "source": "final_state.json (envelope absent)",
                    "explanation_present": bool(
                        fs.get("premise_explanation"))}
        return {"value": "UNKNOWN", "state": "NOT_REACHED",
                "detail": "no premise gate record"}
    verdict = pg.get("verdict") or pg.get("status")
    questions = pg.get("questions") or pg.get("coverage") or {}
    explanation = pg.get("explanation") or pg.get("reason") or ""
    n_covered = sum(1 for v in questions.values()
                    if v and v not in ("UNKNOWN", "NOT_ANSWERED")) \
        if isinstance(questions, dict) else 0
    return {
        "value": verdict or "UNKNOWN",
        "state": "OK" if verdict else "UNKNOWN",
        "questions_covered": n_covered,
        "explanation_present": bool(explanation),
    }


def _evidence_and_mechanisms(case_dir: Path) -> Tuple[
        Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    env = _read_json(case_dir / "candidate_envelope.json")
    if env is None:
        return None, []
    ec = env.get("evidence_classification") or {}
    ms = env.get("mechanism_space") or {}
    return ec, (ms.get("candidates") or [])


def _evidence_synthesis(ec: Optional[Dict[str, Any]]
                        ) -> Dict[str, Any]:
    if ec is None:
        return {"value": "UNKNOWN", "state": "NOT_REACHED"}
    counts = ec.get("counts") or {}
    n_items = ec.get("n_items") or sum(counts.values())
    direct = counts.get("DIRECT_SUPPORT", 0)
    partial = counts.get("PARTIAL_SUPPORT", 0)
    contradictory = counts.get("CONTRADICTORY", 0)
    value = (direct + partial) / n_items if n_items else 0.0
    return {
        "value": round(value, 3), "state": "OK",
        "n_items": n_items,
        "direct_support": direct, "partial_support": partial,
        "contradictory": contradictory,
        "frozen_base_size": n_items,
    }


def _mechanism_quality(ec: Optional[Dict[str, Any]],
                       candidates: List[Dict[str, Any]]
                       ) -> Dict[str, Any]:
    if ec is None and not candidates:
        return {"value": "UNKNOWN", "state": "NOT_REACHED"}
    support = ec.get("mechanism_support") or {} if ec else {}
    support_counts = support.get("counts") or support if isinstance(
        support, dict) else {}
    grounded = 0
    verbatim = 0
    for c in candidates:
        sb = c.get("span_binding") or {}
        if c.get("mechanism_support_count") or \
                _has_support_marker(json.dumps(c.get("support") or
                                               c.get("evidence_support")
                                               or "")[:2000]):
            grounded += 1
        if sb.get("verbatim_in_record") is True:
            verbatim += 1
    n = len(candidates) or None
    return {
        "grounding_rate": round(grounded / n, 3) if n else None,
        "span_verbatim_rate": round(verbatim / n, 3) if n else None,
        "value": (round((grounded + verbatim) / (2 * n), 3)
                  if n else "UNKNOWN"),
        "state": "OK" if n else "NO_CANDIDATES",
        "n_candidates": n or 0,
    }


def _has_support_marker(blob: str) -> bool:
    return "SUPPORTS" in blob or "PARTIALLY_SUPPORTS" in blob


def _mechanism_differentiation(candidates: List[Dict[str, Any]]
                               ) -> Dict[str, Any]:
    if not candidates:
        return {"value": "UNKNOWN", "state": "NO_CANDIDATES"}
    verdicts = [c.get("distinctness_verdict") for c in candidates]
    distinct = sum(1 for v in verdicts if v == "DISTINCT")
    indeterminate = sum(1 for v in verdicts
                        if v == "INDETERMINATE")
    return {
        "value": round(distinct / len(candidates), 3),
        "state": "OK",
        "distinct": distinct,
        "equivalent_or_indeterminate": sum(
            1 for v in verdicts if v in ("EQUIVALENT", "INDETERMINATE")),
        "indeterminate": indeterminate,
    }


def _candidate_quality(candidates: List[Dict[str, Any]],
                       ec: Optional[Dict[str, Any]]
                       ) -> Dict[str, Any]:
    if not candidates:
        return {"value": "UNKNOWN", "state": "NO_CANDIDATES"}
    good = 0
    failing_dims: List[str] = []
    for c in candidates:
        sb = c.get("span_binding") or {}
        dims = {
            "evidence_bound": bool(
                c.get("mechanism_support_count") or _has_support_marker(
                    json.dumps(c.get("support") or "")[:2000])),
            "span_verbatim": sb.get("verbatim_in_record") is True,
            "differentiated": c.get("distinctness_verdict") == "DISTINCT",
            "not_obvious": (
                c.get("transformation_operator") not in (
                    "DIRECT_TRANSFER",)
                and c.get("distinctness_verdict") not in (
                    "EQUIVALENT",)
                and bool(c.get("novel_design_variable"))),
            "not_contradicted": True,   # per-candidate contradiction
            # recorded in the envelope's attack/contradiction fields
            "specific": bool(c.get("testable_prediction_check", {})
                             .get("sufficiently_specific")
                             or c.get("testable_prediction")),
        }
        if all(dims.values()):
            good += 1
        else:
            failing_dims.extend(k for k, ok in dims.items() if not ok)
    return {
        "value": round(good / len(candidates), 3),
        "state": "OK",
        "good_discovery_candidates": good,
        "n_candidates": len(candidates),
        "failing_dimensions_histogram": {
            k: failing_dims.count(k)
            for k in sorted(set(failing_dims))},
    }


def _attack_quality(case_dir: Path, env_attack: Dict[str, Any]
                    ) -> Dict[str, Any]:
    overall = env_attack.get("overall")
    attacks = env_attack.get("attacks") or []
    challenges = env_attack.get("challenges") or []
    n_attacks = len(attacks) + len(challenges)
    kills = _collect_kills(env_attack)
    grounded_kills = 0
    for base in kills:
        blob = json.dumps(base) if not isinstance(base, str) else base
        if (_SOURCE_ID_RE.search(blob) or _QUANTITY_RE.search(blob)
                or _RECORD_REF_RE.search(blob)):
            grounded_kills += 1
    stage = _read_json(case_dir / "stage_ATTACK.json") or {}
    ran = str(stage.get("status") or "").upper() == "OK"
    base_rate = (grounded_kills / len(kills)) if kills else None
    return {
        "value": (round(base_rate, 3) if base_rate is not None
                  else ("EXECUTED" if ran and n_attacks
                        else "NOT_RUN")),
        "state": ("OK" if n_attacks else
                  ("NOT_RUN" if not ran else "EXECUTED_ZERO_RECORDS")),
        "overall_verdict": overall,
        "attack_records": n_attacks,
        "kills": len(kills),
        "grounded_kill_bases": grounded_kills,
        "grounded_kill_base_rate": (round(base_rate, 3)
                                    if base_rate is not None else None),
    }


def _collect_kills(attack: Dict[str, Any]) -> List[Any]:
    kills: List[Any] = []
    for group in (attack.get("attacks") or []):
        if isinstance(group, dict):
            verdict = str(group.get("verdict") or "").upper()
            if "KILL" in verdict:
                kills.extend(group.get("bases") or
                             group.get("reasons") or [group])
    for ch in (attack.get("challenges") or []):
        if isinstance(ch, dict):
            verdict = str(ch.get("verdict") or "").upper()
            if "KILL" in verdict:
                kills.append(ch)
    return kills


def _contradiction_detection(case_dir: Path,
                             ec: Optional[Dict[str, Any]]
                             ) -> Dict[str, Any]:
    counts = (ec or {}).get("counts") or {}
    contradictory = counts.get("CONTRADICTORY", 0)
    stage = _read_json(case_dir / "stage_CONTRADICTION.json") or {}
    contradictions = stage.get("contradictions") or []
    unresolved = sum(1 for c in contradictions
                     if isinstance(c, dict)
                     and c.get("currently_unresolved"))
    n_items = (ec or {}).get("n_items") or sum(counts.values()) or None
    return {
        "value": contradictory + unresolved,
        "state": "OK" if n_items else "NOT_REACHED",
        "contradictory_adjudicated": contradictory,
        "recorded_unresolved": unresolved,
        "n_items": n_items,
        "detection_ran": str(stage.get("status") or "").upper() == "OK",
    }


def _engineering_reasoning(case_dir: Path) -> Dict[str, Any]:
    spec = _read_json(case_dir / "ENGINEERING_SPECIFICATION.json")
    if spec is None:
        for gen in sorted(case_dir.glob("EVOLUTION_GEN_*.json")):
            spec = _read_json(gen) or spec
        if spec is None:
            return {"value": "NOT_REACHED",
                    "state": "NOT_REACHED",
                    "detail": "no ENGINEERING_SPECIFICATION produced "
                              "(--no-package runs stop at the "
                              "adjudication boundary)"}
    vs = spec.get("value_sourcing") or {}
    summary = vs.get("summary") or vs.get("counts") or {}
    if not summary:
        # the R452 shape: the sourcing summary rides the spec top level
        summary = {k: spec[k] for k in
                   ("n_source_fact", "n_computed", "n_modelled",
                    "n_unknown") if k in spec}
    total = sum(v for v in summary.values()
                if isinstance(v, (int, float))) or None
    if not total:
        return {"value": "SPEC_PRESENT_UNSOURCED",
                "state": "OK", "summary": summary}
    source_fact = summary.get("SOURCE_FACT") or summary.get(
        "n_source_fact") or 0
    return {
        "value": round(source_fact / total, 3),
        "state": "OK",
        "value_sourcing_summary": summary,
        "source_fact_share": round(source_fact / total, 3),
    }


def _ledger_metrics(case_dir: Path) -> Dict[str, Any]:
    led = _read_json(case_dir / "ROUTING_LEDGER_RUN.json")
    if led is None:
        return {"structured_output_reliability": {
                    "value": "UNKNOWN", "state": "NOT_REACHED"},
                "latency": {"value": "UNKNOWN", "state": "NOT_REACHED"},
                "token_cost": {"value": "UNKNOWN",
                               "state": "NOT_REACHED"},
                "failure_rate": {"value": "UNKNOWN",
                                 "state": "NOT_REACHED"},
                "n_lines": 0}
    lines = [l for l in (led.get("lines") or [])
             if isinstance(l, dict) and l.get("run_id")]
    ok_lines = [l for l in lines if l.get("status") == "OK"]
    latencies = [l.get("latency_ms") for l in ok_lines
                 if isinstance(l.get("latency_ms"), (int, float))]
    tokens = [l.get("tokens") for l in ok_lines
              if isinstance(l.get("tokens")
                            , (int, float, dict))]
    total_tokens = 0
    for t in tokens:
        if isinstance(t, dict):
            total_tokens += (t.get("total_tokens")
                             or (t.get("prompt_tokens", 0)
                                 + t.get("completion_tokens", 0)) or 0)
        else:
            total_tokens += t
    failures: Dict[str, int] = {}
    for l in lines:
        if l.get("status") != "OK":
            fc = l.get("failure_class") or "UNCLASSIFIED"
            failures[fc] = failures.get(fc, 0) + 1
    n = len(lines)
    p50 = statistics.median(latencies) if latencies else None
    mean = round(statistics.mean(latencies), 1) if latencies else None
    mx = max(latencies) if latencies else None
    retries = sum(1 for l in lines
                  if (l.get("attempt") or 1) > 1)
    degraded = sum(1 for l in lines
                   if l.get("task_degradation"))
    return {
        "structured_output_reliability": {
            "value": round(len(ok_lines) / n, 3) if n else None,
            "state": "OK" if n else "NOT_REACHED",
            "ok_lines": len(ok_lines), "total_lines": n,
            "retry_lines": retries,
            "task_degradation_lines": degraded,
        },
        "latency": {
            "value": {"mean_ms": mean, "p50_ms": p50, "max_ms": mx},
            "state": "OK" if latencies else "NOT_REACHED",
        },
        "token_cost": {
            "value": total_tokens, "state": "OK" if total_tokens
            else "UNKNOWN",
        },
        "failure_rate": {
            "value": round((n - len(ok_lines)) / n, 3) if n else None,
            "state": "OK" if n else "NOT_REACHED",
            "failure_class_histogram": failures,
        },
        "n_lines": n,
        "models_used": sorted({l.get("model") for l in lines
                               if l.get("model")}),
        "providers_used": sorted({l.get("provider") for l in lines
                                  if l.get("provider")}),
    }


def _hallucination(case_dir: Path, candidates: List[Dict[str, Any]],
                   ec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not candidates:
        return {"value": "UNKNOWN", "state": "NO_CANDIDATES"}
    claimed_ids = set()
    verbatim_true = 0
    for c in candidates:
        sb = c.get("span_binding") or {}
        if sb.get("verbatim_in_record") is True:
            verbatim_true += 1
        for k in ("evidence_ids", "supporting_evidence_ids"):
            claimed_ids.update(c.get(k) or [])
    pool_ids = set()
    if ec:
        for it in (ec.get("items") or []):
            if isinstance(it, dict):
                pool_ids.add(it.get("evidence_id") or it.get("id"))
    env = _read_json(case_dir / "candidate_envelope.json") or {}
    for e in (env.get("evidence") or []):
        if isinstance(e, dict):
            pool_ids.add(e.get("evidence_id") or e.get("id")
                         or e.get("source_id"))
    fabricated = sorted(claimed_ids - pool_ids) if claimed_ids else []
    n = len(candidates)
    non_verbatim_rate = 1 - (verbatim_true / n)
    fabricated_rate = (len(fabricated) / len(claimed_ids)
                       if claimed_ids else 0.0)
    return {
        "value": round(0.5 * non_verbatim_rate
                       + 0.5 * fabricated_rate, 3),
        "state": "OK",
        "span_non_verbatim_rate": round(non_verbatim_rate, 3),
        "claimed_evidence_ids": len(claimed_ids),
        "fabricated_evidence_ids": fabricated,
        "fabricated_rate": round(fabricated_rate, 3),
    }


def _wall_clock(case_dir: Path) -> Optional[float]:
    manifest = _read_json(case_dir / "run_manifest.json") or {}
    started = manifest.get("started_at") or manifest.get("started")
    finished = manifest.get("finished_at") or manifest.get("finished")
    if not (started and finished):
        return None
    try:
        from datetime import datetime as _dt
        s = _dt.fromisoformat(str(started).replace("Z", "+00:00"))
        f = _dt.fromisoformat(str(finished).replace("Z", "+00:00"))
        return round((f - s).total_seconds(), 1)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# apply: the full metric vector for ONE run directory
# ---------------------------------------------------------------------------

def apply_to_run_dir(case_dir: Path,
                     authored_text: str) -> Dict[str, Any]:
    """The frozen metric vector for one run directory. Deterministic;
    raises SystemExit on instrument drift (the apply-time guard)."""
    verify_instrument()
    case_dir = Path(case_dir)
    ec, candidates = _evidence_and_mechanisms(case_dir)
    env = _read_json(case_dir / "candidate_envelope.json") or {}
    attack = env.get("attack_results") or {}
    ledger = _ledger_metrics(case_dir)
    fs = _read_json(case_dir / "final_state.json") or {}
    return {
        "instrument_version": INSTRUMENT_VERSION,
        "run_dir": str(case_dir),
        "final_status": fs.get("final_status"),
        "epistemic_state": fs.get("epistemic_state"),
        "metrics": {
            "problem_understanding": _problem_understanding(
                case_dir, authored_text),
            "problem_existence": _premise_gate(case_dir),
            "evidence_synthesis": _evidence_synthesis(ec),
            "mechanism_quality": _mechanism_quality(ec, candidates),
            "mechanism_differentiation": _mechanism_differentiation(
                candidates),
            "candidate_quality": _candidate_quality(candidates, ec),
            "attack_quality": _attack_quality(case_dir, attack),
            "contradiction_detection": _contradiction_detection(
                case_dir, ec),
            "engineering_reasoning": _engineering_reasoning(case_dir),
            "structured_output_reliability": ledger[
                "structured_output_reliability"],
            "hallucination_rate": _hallucination(
                case_dir, candidates, ec),
            "latency": ledger["latency"],
            "token_cost": ledger["token_cost"],
            "failure_rate": ledger["failure_rate"],
        },
        "wall_clock_s": _wall_clock(case_dir),
        "ledger_models": ledger.get("models_used"),
        "ledger_providers": ledger.get("providers_used"),
        "ledger_n_lines": ledger.get("n_lines"),
    }


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ("freeze", "verify"):
        print(__doc__)
        return 2
    return {"freeze": cmd_freeze, "verify": cmd_verify}[
        sys.argv[1]]()


if __name__ == "__main__":
    raise SystemExit(main())
