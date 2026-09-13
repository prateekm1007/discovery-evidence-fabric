#!/usr/bin/env python3
"""scripts/r452_quality_instrument.py — R452 Phase 3: the FROZEN
deterministic discovery-quality evaluation instrument.

"Freeze a deterministic evaluation instrument before looking at the
final results."

FREEZE DISCIPLINE (Art. LIX — no benchmark gaming):
  - `freeze` records the metric definitions (machine-readable), the
    instrument's OWN sha256, and the freeze timestamp;
  - `freeze` FAILS CLOSED if any assay result artifact already exists
    (the instrument is frozen before results are looked at — this is
    enforced, not promised);
  - `apply` recomputes the script hash and REFUSES to run if the
    instrument was modified after freezing (tuning after freeze is
    gaming).

THE TEN METRICS (directive Phase 3, definitions frozen here — each is
computed DETERMINISTICALLY from the run's OWN persisted artifacts,
Art. X; every metric states its artifact source):

  1. evidence_relevance_rate
     = (DIRECT_SUPPORT + PARTIAL_SUPPORT) / n_items
     from evidence_classification.counts (the per-record relevance
     adjudication the engine itself records; IRRELEVANT/BACKGROUND/
     ANALOGY are adjudicated non-relevant, CONTRADICTORY is counted
     separately by metric 6).

  2. mechanism_grounding_rate
     = candidates with >= 1 SUPPORTS-or-PARTIALLY_SUPPORTS item in
     mechanism_support.counts / total candidates
     (a mechanism with zero supporting frozen evidence is not
     evidence-bound).

  3. mechanism_span_verbatim_support
     = candidates with span_binding.verbatim_in_record == true /
     total candidates (the R451-C1.1 50% span-verbatim honesty number,
     made a standing metric).

  4. differentiated_mechanism_rate
     = candidates with distinctness_verdict == DISTINCT AND
       testable_prediction_check.sufficiently_specific == true AND
       a non-empty novel_design_variable / total candidates
     (the machine's wording-independent distinctness instrument plus
     the engineering-specificity requirement — a renamed known
     mechanism or an vague one does not count).

  5. obvious_combination_rate
     = candidates with transformation_operator == DIRECT_TRANSFER OR
       distinctness_verdict in (EQUIVALENT, INDETERMINATE) OR empty
       novel_design_variable / total candidates
     (the machine-observable proxies for "renamed known mechanism /
     obvious combination masquerading as novelty" — BS-024 measured,
     not narrated).

  6. evidence_contradiction_rate
     = CONTRADICTORY / n_items (from evidence_classification.counts)
     plus the count of unresolved recorded contradictions
     (contradictions.contradictions with currently_unresolved).

  7. false_kill_rate
     = unsupported_kills / total_kills; a kill is UNSUPPORTED when
     NONE of its recorded bases carries (a) a source-id pattern
     (doi:/patent/europepmc/pubmed), (b) a computed quantity (digits
     with a unit token), or (c) an explicit record reference — the
     R445-B diagnosis classes made mechanical. WHEN total_kills == 0
     the metric is UNKNOWN_NO_KILLS (absence of kills is not a zero
     false-kill rate — Art. XXV).

  8. attack_completeness_rate
     = problems whose adversarial attack ACTUALLY produced attack
     records (attacks_recorded > 0) / problems that reached the ATTACK
     stage (the R451 defect — a stage that "executes" with zero
     challenges and EVIDENCE_GATE_FAILED — is measured as
     incomplete, never as executed).

  9. cross_domain_execution_rate
     = distinct families whose chain reached ADJUDICATION /
     families scoped (3: medical_device, energy_industrial,
     materials_electronics).

 10. repeated_run_variance
     = per-metric |value(A) - value(A2)| on the shared metric set
     plus terminal-outcome agreement, reported as measured (no
     threshold invented — Art. XXVII).

THE CRITICAL DISTINCTION (the directive's own words): "A candidate
surviving the pipeline is not automatically a good discovery." The
instrument therefore computes, per candidate, the six-dimension
discovery-quality composite:

  evidence_bound AND span_verbatim AND differentiated AND
  not_obvious_combination AND not_contradicted AND
  sufficiently_specific -> GOOD_DISCOVERY

and reports RAW SURVIVAL separately from QUALITY-WEIGHTED SURVIVAL
(survivors failing the composite are listed with their failing
dimensions — the failure mode earlier audits described narratively is
now MEASURED).

Usage:
  python scripts/r452_quality_instrument.py freeze
  python scripts/r452_quality_instrument.py apply
  python scripts/r452_quality_instrument.py verify
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

OUT_ROOT = REPO_ROOT / "R452"
FROZEN_RECORD = OUT_ROOT / "DISCOVERY_QUALITY_INSTRUMENT.json"
MEASUREMENT_RECORD = OUT_ROOT / "DISCOVERY_QUALITY_MEASUREMENT.json"

#: result artifacts that must NOT exist at freeze time
RESULT_ARTIFACTS = [
    OUT_ROOT / "ASSAY_CHAINS.json",
    OUT_ROOT / "DISCOVERY_QUALITY_MEASUREMENT.json",
]
for _c in ("A", "B", "C", "A2"):
    RESULT_ARTIFACTS.append(OUT_ROOT / f"ASSAY_RUN_{_c}" /
                            "final_state.json")

_SOURCE_ID_RE = re.compile(
    r"(doi:|patent|europepmc|pubmed|US\d{7,}|EP\d{6,}|WO\d{4}/)")
_COMPUTED_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(mm|millimetre|millimeter|cm|m|pa|kpa|mpa|bar|"
    r"psi|c|k|degrees|percent|%,|l|min|hour|second|hz|kg|g|n|w|kw|"
    r"mw|v|a|ohm|cst|cp)")
_RECORD_REF_RE = re.compile(
    r"(record|envelope|ledger|cemetery|classification|"
    r"evidence_classification|attack_results)", re.IGNORECASE)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _script_sha256() -> str:
    return hashlib.sha256(
        Path(__file__).read_bytes()).hexdigest()


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        if p.exists():
            d = json.loads(p.read_text())
            return d if isinstance(d, dict) else None
    except Exception:  # noqa: BLE001
        return None
    return None


# ---------------------------------------------------------------------------
# The frozen metric definitions (machine-readable)
# ---------------------------------------------------------------------------

METRIC_DEFINITIONS = [
    {"metric": "evidence_relevance_rate",
     "definition": "(DIRECT_SUPPORT + PARTIAL_SUPPORT) / n_items",
     "source": "envelope_ADJUDICATION.evidence_classification.counts",
     "direction": "higher_is_better"},
    {"metric": "mechanism_grounding_rate",
     "definition": "candidates with >=1 SUPPORTS-or-PARTIALLY_SUPPORTS "
                   "item / total candidates",
     "source": "mechanism_space.candidates[].mechanism_support.counts",
     "direction": "higher_is_better"},
    {"metric": "mechanism_span_verbatim_support",
     "definition": "candidates with span_binding.verbatim_in_record "
                   "== true / total candidates",
     "source": "mechanism_space.candidates[].span_binding",
     "direction": "higher_is_better"},
    {"metric": "differentiated_mechanism_rate",
     "definition": "candidates with distinctness_verdict == DISTINCT "
                   "AND testable_prediction_check.sufficiently_specific "
                   "== true AND non-empty novel_design_variable / total",
     "source": "mechanism_space.candidates[]",
     "direction": "higher_is_better"},
    {"metric": "obvious_combination_rate",
     "definition": "candidates with transformation_operator == "
                   "DIRECT_TRANSFER OR distinctness_verdict in "
                   "(EQUIVALENT, INDETERMINATE) OR empty "
                   "novel_design_variable / total",
     "source": "mechanism_space.candidates[]",
     "direction": "lower_is_better"},
    {"metric": "evidence_contradiction_rate",
     "definition": "CONTRADICTORY / n_items + unresolved recorded "
                   "contradictions count (reported jointly)",
     "source": "evidence_classification.counts + contradictions",
     "direction": "lower_is_better"},
    {"metric": "false_kill_rate",
     "definition": "unsupported_kills / total_kills; a kill is "
                   "UNSUPPORTED when none of its recorded bases "
                   "carries a source-id, a computed quantity, or an "
                   "explicit record reference; total_kills == 0 -> "
                   "UNKNOWN_NO_KILLS",
     "source": "attack_results.attacks[]",
     "direction": "lower_is_better"},
    {"metric": "attack_completeness_rate",
     "definition": "problems with attacks_recorded > 0 / problems "
                   "reaching the ATTACK stage",
     "source": "envelope_ATTACK.attack_results",
     "direction": "higher_is_better"},
    {"metric": "cross_domain_execution_rate",
     "definition": "distinct families reaching ADJUDICATION / "
                   "families scoped (3)",
     "source": "envelope_ADJUDICATION + assay problem families",
     "direction": "higher_is_better"},
    {"metric": "repeated_run_variance",
     "definition": "per-metric |value(A) - value(A2)| on the shared "
                   "metric set + terminal-outcome agreement; reported "
                   "as measured, no threshold",
     "source": "the A and A2 run artifacts",
     "direction": "reported"},
]

#: the six-dimension candidate composite (the critical distinction)
COMPOSITE_DIMENSIONS = [
    {"dimension": "evidence_bound",
     "check": "mechanism_support.counts.SUPPORTS + "
              "PARTIALLY_SUPPORTS >= 1"},
    {"dimension": "span_verbatim",
     "check": "span_binding.verbatim_in_record == true"},
    {"dimension": "differentiated",
     "check": "distinctness_verdict == DISTINCT AND "
              "sufficiently_specific AND novel_design_variable "
              "non-empty"},
    {"dimension": "not_obvious_combination",
     "check": "NOT (DIRECT_TRANSFER OR EQUIVALENT/INDETERMINATE OR "
              "empty novel_design_variable)"},
    {"dimension": "not_contradicted",
     "check": "no currently_unresolved HIGH-severity contradiction "
              "recorded against the candidate"},
    {"dimension": "sufficiently_specific",
     "check": "testable_prediction_check.sufficiently_specific == "
              "true"},
]


# ---------------------------------------------------------------------------
# freeze / verify / apply
# ---------------------------------------------------------------------------

def freeze() -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    existing = [str(p) for p in RESULT_ARTIFACTS if p.exists()]
    if existing:
        print("[r452-instrument] FREEZE FAIL-CLOSED — assay result "
              "artifacts already exist (the instrument must be frozen "
              "before results are looked at):")
        for p in existing:
            print("  -", p)
        return 2
    doc = {
        "artifact_type": "R452_DISCOVERY_QUALITY_INSTRUMENT",
        "frozen_at": _now(),
        "instrument_script": "scripts/r452_quality_instrument.py",
        "instrument_sha256": _script_sha256(),
        "freeze_enforcement": "apply() recomputes the script sha256 and "
                              "REFUSES to run on any post-freeze "
                              "modification (Art. LIX — no tuning "
                              "against the results)",
        "no_results_existed_at_freeze": True,
        "checked_result_artifacts": [str(p) for p in RESULT_ARTIFACTS],
        "metric_definitions": METRIC_DEFINITIONS,
        "candidate_composite": {
            "dimensions": COMPOSITE_DIMENSIONS,
            "good_discovery_rule": "ALL six dimensions true",
            "critical_distinction": "a candidate surviving the pipeline "
                                    "is NOT automatically a good "
                                    "discovery; raw survival is "
                                    "reported separately from "
                                    "quality-weighted survival",
        },
        "unknown_states_honest": ("any metric whose inputs do not "
                                  "exist is recorded UNKNOWN_<reason>, "
                                  "never 0.0 (Art. XXV)"),
    }
    FROZEN_RECORD.write_text(json.dumps(doc, indent=1))
    print(f"[r452-instrument] frozen -> {FROZEN_RECORD} "
          f"(script sha256 {_script_sha256()[:12]}…)")
    return 0


def verify_instrument() -> Optional[Dict[str, Any]]:
    """Load the frozen record and verify THIS script matches its
    frozen hash (fail-closed on post-freeze modification)."""
    doc = _read_json(FROZEN_RECORD)
    if doc is None:
        print("[r452-instrument] FAIL — no frozen instrument record; "
              "run `freeze` first")
        return None
    cur = _script_sha256()
    if cur != doc.get("instrument_sha256"):
        print("[r452-instrument] FAIL — instrument script was modified "
              "after freeze (frozen "
              f"{(doc.get('instrument_sha256') or '')[:12]}…, current "
              f"{cur[:12]}…); tuning after freeze is gaming (Art. LIX)")
        return None
    return doc


# ---------------------------------------------------------------------------
# The measurement (deterministic, from the runs' OWN artifacts)
# ---------------------------------------------------------------------------

def _case_metrics(case_dir: Path) -> Dict[str, Any]:
    """All ten metrics' inputs from ONE run directory's persisted
    artifacts (the latest envelope carrying the full state is
    envelope_ADJUDICATION; fall back through the envelope ladder)."""
    m: Dict[str, Any] = {}
    env = None
    for name in ("envelope_ADJUDICATION", "envelope_RANK",
                 "envelope_CLASSIFY", "envelope_KILLER_EXPERIMENT",
                 "envelope_ATTACK", "envelope_CONTRADICTION",
                 "envelope_COLLISION", "envelope_MULTI_SOURCE_DISCOVERY",
                 "envelope_MECHANISM_SPACE", "envelope_SYNTHESIZE",
                 "envelope_FREEZE"):
        env = _read_json(case_dir / f"{name}.json")
        if env:
            m["envelope_source"] = name
            break
    if env is None:
        return {"available": False,
                "reason": "no envelope artifacts in the run dir"}

    # 1. evidence relevance + 6. contradiction inputs
    ec = env.get("evidence_classification") or {}
    counts = ec.get("counts") or {}
    n_items = int(ec.get("n_items") or 0)
    if n_items > 0:
        direct = int(counts.get("DIRECT_SUPPORT") or 0)
        partial = int(counts.get("PARTIAL_SUPPORT") or 0)
        m["evidence_relevance_rate"] = round(
            (direct + partial) / n_items, 4)
        m["evidence_n_items"] = n_items
        m["evidence_counts"] = counts
        contradictory = int(counts.get("CONTRADICTORY") or 0)
        m["evidence_contradiction_rate"] = round(
            contradictory / n_items, 4)
    else:
        m["evidence_relevance_rate"] = "UNKNOWN_NO_CLASSIFIED_EVIDENCE"
        m["evidence_contradiction_rate"] = \
            "UNKNOWN_NO_CLASSIFIED_EVIDENCE"

    # contradictions recorded by the CONTRADICTION stage
    cons = (env.get("contradictions") or {}).get("contradictions") or []
    m["recorded_contradictions"] = len(cons)
    m["unresolved_high_contradictions"] = sum(
        1 for c in cons
        if c.get("currently_unresolved")
        and str(c.get("severity")).upper() in ("HIGH", "CRITICAL"))

    # candidates: metrics 2-5 + the composite
    cands = ((env.get("mechanism_space") or {})
             .get("candidates") or [])
    n_cand = len(cands)
    m["n_candidates"] = n_cand
    if n_cand > 0:
        grounded = span_ok = diff_ok = obvious = 0
        per_cand = []
        for c in cands:
            sup = (c.get("mechanism_support") or {}).get("counts") or {}
            sup_n = int(sup.get("SUPPORTS") or 0) + int(
                sup.get("PARTIALLY_SUPPORTS") or 0)
            vb = bool(((c.get("span_binding") or {})
                       .get("verbatim_in_record")))
            tpc = c.get("testable_prediction_check") or {}
            specific = bool(tpc.get("sufficiently_specific"))
            ndv = str(c.get("novel_design_variable") or "").strip()
            dv = c.get("distinctness_verdict")
            op = c.get("transformation_operator")
            evidence_bound = sup_n >= 1
            differentiated = (dv == "DISTINCT" and specific
                              and bool(ndv))
            is_obvious = (op == "DIRECT_TRANSFER"
                          or dv in ("EQUIVALENT", "INDETERMINATE")
                          or not ndv)
            not_contradicted = m["unresolved_high_contradictions"] == 0
            dims = {
                "evidence_bound": evidence_bound,
                "span_verbatim": vb,
                "differentiated": differentiated,
                "not_obvious_combination": not is_obvious,
                "not_contradicted": not_contradicted,
                "sufficiently_specific": specific,
            }
            good = all(dims.values())
            grounded += int(evidence_bound)
            span_ok += int(vb)
            diff_ok += int(differentiated)
            obvious += int(is_obvious)
            per_cand.append({
                "candidate_id": c.get("candidate_id"),
                "dimensions": dims,
                "good_discovery": good,
                "failing_dimensions": [k for k, v in dims.items()
                                       if not v],
            })
        m["mechanism_grounding_rate"] = round(grounded / n_cand, 4)
        m["mechanism_span_verbatim_support"] = round(
            span_ok / n_cand, 4)
        m["differentiated_mechanism_rate"] = round(
            diff_ok / n_cand, 4)
        m["obvious_combination_rate"] = round(obvious / n_cand, 4)
        m["candidate_composite"] = per_cand
        m["good_discovery_count"] = sum(
            1 for c in per_cand if c["good_discovery"])
    else:
        for k in ("mechanism_grounding_rate",
                  "mechanism_span_verbatim_support",
                  "differentiated_mechanism_rate",
                  "obvious_combination_rate"):
            m[k] = "UNKNOWN_NO_CANDIDATES"

    # 7. false-kill rate (from the adversarial attack records)
    atk = _read_json(case_dir / "envelope_ATTACK.json") or env
    ar = (atk.get("attack_results") or {})
    attacks = ar.get("attacks") or []
    kills = []
    for a in attacks:
        verdict = str(a.get("verdict") or a.get("overall") or "")
        if "KILL" in verdict.upper():
            kills.append(a)
    if kills:
        unsupported = 0
        for k in kills:
            bases = json.dumps(k)
            grounded_kill = bool(
                _SOURCE_ID_RE.search(bases)
                or _COMPUTED_RE.search(bases)
                or _RECORD_REF_RE.search(bases))
            if not grounded_kill:
                unsupported += 1
        m["false_kill_rate"] = round(unsupported / len(kills), 4)
        m["total_kills"] = len(kills)
        m["unsupported_kills"] = unsupported
    else:
        m["false_kill_rate"] = "UNKNOWN_NO_KILLS"
        m["total_kills"] = len(kills)

    # 8. attack completeness inputs
    m["adversarial_status"] = ar.get("adversarial_status")
    m["attacks_recorded"] = len(attacks)
    m["attack_reached"] = bool(atk)
    m["adversarial_not_run_reason"] = ar.get(
        "adversarial_not_run_reason")

    # adjudication occurrence (metric 9 input)
    adj_env = _read_json(case_dir / "envelope_ADJUDICATION.json")
    m["adjudication_occurred"] = bool(
        adj_env and (((adj_env.get("adjudication") or {})
                      .get("council") or {}).get("verdict")))

    # the terminal outcome (from the chains record when present)
    m["available"] = True
    return m


def apply() -> int:
    frozen = verify_instrument()
    if frozen is None:
        return 2
    chains = _read_json(OUT_ROOT / "ASSAY_CHAINS.json")
    if chains is None:
        print("[r452-instrument] FAIL — no ASSAY_CHAINS.json; run the "
              "assay first (scripts/r452_assay.py assess)")
        return 2

    per_case: Dict[str, Any] = {}
    for entry in chains.get("chains") or []:
        case = entry.get("case")
        case_dir = OUT_ROOT / f"ASSAY_RUN_{case}"
        per_case[case] = _case_metrics(case_dir)
        per_case[case]["terminal_outcome"] = entry.get(
            "terminal_outcome")
        per_case[case]["family"] = entry.get("family")

    # 8. attack completeness (across problems reaching ATTACK)
    reached = [c for c, m in per_case.items()
               if isinstance(m, dict) and m.get("attack_reached")]
    produced = [c for c in reached
                if (per_case[c].get("attacks_recorded") or 0) > 0]
    attack_completeness = (
        round(len(produced) / len(reached), 4) if reached
        else "UNKNOWN_ATTACK_NOT_REACHED")

    # 9. cross-domain execution
    families_scoped = ["medical_device", "energy_industrial",
                       "materials_electronics"]
    families_adj = sorted({
        per_case[c].get("family") for c in ("A", "B", "C")
        if isinstance(per_case.get(c), dict)
        and per_case[c].get("adjudication_occurred")})
    cross_domain = (
        round(len(families_adj) / len(families_scoped), 4)
        if families_adj else 0.0)

    # 10. repeated-run variance (A vs A2)
    variance: Dict[str, Any] = {}
    a, a2 = per_case.get("A"), per_case.get("A2")
    if isinstance(a, dict) and isinstance(a2, dict) and \
            a.get("available") and a2.get("available"):
        for k in ("evidence_relevance_rate",
                  "mechanism_grounding_rate",
                  "mechanism_span_verbatim_support",
                  "differentiated_mechanism_rate",
                  "obvious_combination_rate",
                  "evidence_contradiction_rate",
                  "false_kill_rate"):
            va, vb = a.get(k), a2.get(k)
            if isinstance(va, float) and isinstance(vb, float):
                variance[k] = {"run_A": va, "run_A2": vb,
                               "abs_difference": round(
                                   abs(va - vb), 4)}
            else:
                variance[k] = {"run_A": va, "run_A2": vb,
                               "abs_difference": "UNKNOWN"}
        variance["terminal_outcome_agreement"] = (
            a.get("terminal_outcome") == a2.get("terminal_outcome"))
        variance["evidence_n_items"] = {
            "run_A": a.get("evidence_n_items"),
            "run_A2": a2.get("evidence_n_items")}
    else:
        variance = "UNKNOWN_REPEAT_RUN_NOT_AVAILABLE"

    # the critical distinction: raw survival vs quality-weighted
    raw_survivors, good_discoveries = [], []
    for case in ("A", "B", "C"):
        m = per_case.get(case)
        if not isinstance(m, dict) or not m.get("available"):
            continue
        for c in m.get("candidate_composite") or []:
            entry = {"case": case,
                     "candidate_id": c.get("candidate_id")}
            if m.get("terminal_outcome") in (
                    "INVENTION_UNDER_DEVELOPMENT",):
                raw_survivors.append(entry)
            if c.get("good_discovery"):
                good_discoveries.append({**entry,
                                         "dimensions": c["dimensions"]})

    doc = {
        "artifact_type": "R452_DISCOVERY_QUALITY_MEASUREMENT",
        "measured_at": _now(),
        "instrument_frozen_at": frozen.get("frozen_at"),
        "instrument_sha256": frozen.get("instrument_sha256"),
        "instrument_verified_unchanged": True,
        "per_case": per_case,
        "aggregate_metrics": {
            "attack_completeness_rate": attack_completeness,
            "cross_domain_execution_rate": cross_domain,
            "families_reaching_adjudication": families_adj,
            "repeated_run_variance": variance,
        },
        "critical_distinction": {
            "raw_survivors": raw_survivors,
            "good_discoveries": good_discoveries,
            "rule": ("raw survival != good discovery; the composite "
                     "requires evidence_bound AND span_verbatim AND "
                     "differentiated AND not_obvious_combination AND "
                     "not_contradicted AND sufficiently_specific"),
            "survivors_failing_quality": [
                {"case": case,
                 "candidate_id": c.get("candidate_id"),
                 "failing_dimensions": c.get("failing_dimensions")}
                for case in ("A", "B", "C")
                for c in ((per_case.get(case) or {}).get(
                    "candidate_composite") or [])
                if (per_case.get(case) or {}).get("terminal_outcome")
                == "INVENTION_UNDER_DEVELOPMENT"
                and not c.get("good_discovery")],
        },
    }
    MEASUREMENT_RECORD.write_text(json.dumps(doc, indent=1))
    print(f"[r452-instrument] measurement -> {MEASUREMENT_RECORD}")
    # concise console summary (the honest numbers, never repaired)
    for case in ("A", "B", "C", "A2"):
        m = per_case.get(case)
        if isinstance(m, dict) and m.get("available"):
            print(f"  {case}: rel={m.get('evidence_relevance_rate')} "
                  f"span={m.get('mechanism_span_verbatim_support')} "
                  f"diff={m.get('differentiated_mechanism_rate')} "
                  f"obvious={m.get('obvious_combination_rate')} "
                  f"outcome={m.get('terminal_outcome')}")
    print(f"  attack_completeness={attack_completeness} "
          f"cross_domain={cross_domain}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == "freeze":
        return freeze()
    if cmd == "apply":
        return apply()
    if cmd == "verify":
        doc = verify_instrument()
        return 0 if doc else 2
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
