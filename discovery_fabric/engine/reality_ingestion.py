"""R407 — the first-reality-loop machinery.

Directive basis (CEO R407 directive — FIRST REALITY LOOP):
  R407-B — the REALITY_EVENT ingestion contract: no physical observation
           enters the system without provenance. Mandatory fields:
           experiment_id, package_id, timestamp, apparatus_id, operator,
           raw_data_hash, processed_data_hash, measurement_units,
           uncertainty, baseline_result, candidate_result,
           pre_registered_threshold, decision (on top of the Art. XXXVIII
           base: event_id, source_type, organization, custody_chain,
           attestation, provenance_validated).
  R407-A — the frozen P04 experiment contract; a pure function computes
           KEEP / MODIFY / KILL from the observation without human
           reinterpretation.
  R407-C/D — PREDICTION_BEFORE -> OBSERVATION -> MODEL_ERROR ->
           MODEL_UPDATE -> PREDICTION_AFTER; LEARNING_FAILED is a valid,
           recordable outcome; improvement is measured on a HELD-OUT
           condition (anti-learning-theatre: a field named
           model_updated=true is worthless).
  R407-E — loop closure on both outcomes. Success: physical observation ->
           evidence -> engineering model -> buyer package -> commercial
           maturity. Failure: KILL -> cemetery -> failure memory ->
           discovery constrained by the failure (Art. LI: a cemetery that
           is never read by the generator is a log, not a memory).

Constitutional basis: Art. VI (never manufacture provenance), Art. XXV
(unknown stays unknown), Art. XXXVII/XXXVIII (the Reality Boundary:
CONTROLLED_REHEARSAL never promotes and never counts as learning; AI may
compute verdicts but may never fabricate the observation), Art. LI
(learning must change future behavior), Art. LXI (infrastructure failure
is never scientific rejection — EXECUTION_BLOCKED is an execution state,
not a technology verdict), Art. LII (the falsification contract).

This module NEVER generates observation values. It validates, decides,
adjudicates, and closes loops. Numbers come from reality (or from a
rehearsal fixture that is labeled as such and can never promote).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# R407-B — the physical-observation ingestion contract
# ---------------------------------------------------------------------------

# The 13 R407-B directive fields (verbatim from the directive).
R407_B_MANDATORY_FIELDS: Tuple[str, ...] = (
    "experiment_id", "package_id", "timestamp", "apparatus_id", "operator",
    "raw_data_hash", "processed_data_hash", "measurement_units",
    "uncertainty", "baseline_result", "candidate_result",
    "pre_registered_threshold", "decision",
)

# The Art. XXXVIII provenance base that stays mandatory beneath them.
ART_XXXVIII_BASE_FIELDS: Tuple[str, ...] = (
    "event_id", "source_type", "organization", "custody_chain",
    "attestation", "provenance_validated",
)

REALITY_EVENT_V2_MANDATORY: Tuple[str, ...] = \
    R407_B_MANDATORY_FIELDS + ART_XXXVIII_BASE_FIELDS

REAL_SOURCE_TYPES = {"EXTERNAL_HUMAN", "EXTERNAL_INSTRUMENT",
                     "EXTERNAL_SYSTEM"}
ALL_SOURCE_TYPES = REAL_SOURCE_TYPES | {"CONTROLLED_REHEARSAL"}

_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_ALLOWED_VERDICTS = {"KEEP", "MODIFY", "KILL", "SUPPORTED", "KILLED",
                     "MIXED", "EXECUTION_INVALID", "EXECUTION_BLOCKED"}


def validate_reality_event_v2(event: Dict[str, Any]) -> List[str]:
    """R407-B validator. Returns a list of violations (empty = valid).

    A physical observation missing ANY mandatory field — including the
    provenance base — is rejected: no observation enters the system
    without provenance (directive R407-B + Art. XXXVIII).
    """
    problems: List[str] = []
    if not isinstance(event, dict):
        return ["REALITY_EVENT is not an object"]
    for field in REALITY_EVENT_V2_MANDATORY:
        if field not in event or event[field] is None:
            problems.append(f"missing mandatory field: {field}")
    if problems:
        return problems
    for hfield in ("raw_data_hash", "processed_data_hash"):
        if not isinstance(event[hfield], str) \
                or not _SHA256_RE.fullmatch(event[hfield]):
            problems.append(f"{hfield} is not a sha256 hex digest")
    if event.get("source_type") not in ALL_SOURCE_TYPES:
        problems.append(f"invalid source_type: {event.get('source_type')!r}")
    if event.get("provenance_validated") is not True:
        problems.append("provenance_validated is not true")
    cc = event.get("custody_chain")
    if not (isinstance(cc, list) and len(cc) > 0
            and all(isinstance(step, dict) and step.get("actor")
                    and step.get("action") for step in cc)):
        problems.append("custody_chain empty or malformed "
                        "(each step needs actor + action)")
    att = event.get("attestation")
    if not isinstance(att, dict) or not att.get("attestation_text") \
            or not att.get("attestation_hash"):
        problems.append("attestation missing text/hash")
    dec = event.get("decision")
    if not isinstance(dec, dict) or dec.get("verdict") \
            not in _ALLOWED_VERDICTS:
        problems.append(
            "decision must be an object with a machine verdict in "
            f"{sorted(_ALLOWED_VERDICTS)} (computed by the frozen contract, "
            "never free text)")
    mu = event.get("measurement_units")
    if not isinstance(mu, dict) or not mu:
        problems.append("measurement_units must be a non-empty mapping")
    unc = event.get("uncertainty")
    if not isinstance(unc, dict) or not unc:
        problems.append("uncertainty must be a non-empty mapping")
    ts = event.get("timestamp")
    if not isinstance(ts, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})",
            ts or ""):
        problems.append("timestamp is not an ISO-8601 instant")
    for field in ("experiment_id", "package_id", "apparatus_id", "operator"):
        v = event.get(field)
        if not isinstance(v, str) or not v.strip():
            problems.append(f"{field} must be a non-empty string "
                            "(UNKNOWN is a legitimate value; blank is not)")
    return problems


def _record_hash(record: Dict[str, Any]) -> str:
    blob = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def ingest_reality_event(event: Dict[str, Any], ledger_path: str) -> Dict:
    """Append a validated REALITY_EVENT to the append-only provenance
    ledger. The ledger is hash-chained: each entry carries
    entry_sha256 = H(prev_entry_sha256 | record). A tampered ledger is
    detectable by verify_ledger(). Re-ingesting the same event_id is
    rejected (double-entry guard)."""
    problems = validate_reality_event_v2(event)
    if problems:
        return {"ingested": False, "problems": problems}
    ledger: Dict[str, Any] = {"artifact_type": "REALITY_EVENT_LEDGER",
                              "entries": []}
    if os.path.exists(ledger_path):
        with open(ledger_path) as f:
            ledger = json.load(f)
    if any(e.get("event_id") == event["event_id"]
           for e in ledger.get("entries", [])):
        return {"ingested": False,
                "problems": [f"event_id {event['event_id']} already in the "
                             "ledger (double entry rejected)"]}
    prev = ledger["entries"][-1]["entry_sha256"] if ledger["entries"] else \
        "GENESIS"
    entry = {
        "event_id": event["event_id"],
        "package_id": event["package_id"],
        "experiment_id": event["experiment_id"],
        "source_type": event["source_type"],
        "timestamp": event["timestamp"],
        "reality_class": ("REAL" if event["source_type"] in REAL_SOURCE_TYPES
                          else "CONTROLLED_REHEARSAL"),
        "record": event,
        "prev_entry_sha256": prev,
    }
    entry["entry_sha256"] = _record_hash(
        {"prev": prev, "record": event})
    ledger["entries"].append(entry)
    ledger["entry_count"] = len(ledger["entries"])
    ledger["real_event_count"] = sum(
        1 for e in ledger["entries"] if e["reality_class"] == "REAL")
    os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)
    with open(ledger_path, "w") as f:
        json.dump(ledger, f, indent=1, sort_keys=True)
    return {"ingested": True, "entry_sha256": entry["entry_sha256"],
            "ledger_entry_count": ledger["entry_count"],
            "real_event_count": ledger["real_event_count"]}


def verify_ledger(ledger_path: str) -> Dict[str, Any]:
    """Recompute the hash chain. Any mutation of a past entry breaks it."""
    if not os.path.exists(ledger_path):
        return {"valid": False, "reason": "ledger not found"}
    with open(ledger_path) as f:
        ledger = json.load(f)
    prev = "GENESIS"
    for e in ledger.get("entries", []):
        if e.get("prev_entry_sha256") != prev:
            return {"valid": False, "reason": "chain break: prev hash "
                    f"mismatch at {e.get('event_id')}"}
        if e.get("entry_sha256") != _record_hash(
                {"prev": prev, "record": e.get("record")}):
            return {"valid": False, "reason": "record tampered at "
                    f"{e.get('event_id')}"}
        prev = e["entry_sha256"]
    return {"valid": True, "entries": len(ledger.get("entries", []))}


# ---------------------------------------------------------------------------
# R407-A — the frozen-contract decision functions (pure, no interpretation)
# ---------------------------------------------------------------------------

P04_G_RATIO_MODELLED = 0.0885          # (0.6/1.1)^4, frozen pre-registration
P04_G_RATIO_TOLERANCE = 0.30           # +/- 30%, ENGINEERING class, frozen
P04_Q_MIN_PASS = 0.4                   # mL/min, PHYSIOLOGICAL, frozen
P04_Q_MIN_KILL = 0.2                   # mL/min, PHYSIOLOGICAL, frozen
P04_COMMON_CAUSE_KILL_PCT = 90.0       # percent of cases, ENGINEERING, frozen
P04_PASS_HEADS_REQUIRED = 2            # of 3 pressure heads


def decide_p04(observation: Dict[str, Any]) -> Dict[str, Any]:
    """The frozen P04 contract decision rule, as a pure function.

    Input: the candidate_result block of a P04 REALITY_EVENT
      (residual_floor_flow_mL_min_by_head_mmHg, measured_G_ratio,
       common_cause_occlusion_rate_pct, void_trial_count,
       valid_trials_total, manufacturing_minwall_all_failed).

    Output: {verdict: KEEP|MODIFY|KILL|EXECUTION_INVALID, rule_id,
    rule_trace} — computed from the frozen thresholds ONLY. No threshold
    is a parameter: the rule IS the frozen contract (Art. XXVII).

    Mapping from the R406 pre-registration vocabulary:
      ACCEPT  -> KEEP     (advance with the first physical evidence)
      INDETERMINATE -> MODIFY (a registered model/design change and a
                            re-registered re-run; never a promotion)
      KILL    -> KILL     (cemetery path; Art. LIV)
    """
    cr = observation.get("candidate_result", observation)
    flows = cr.get("residual_floor_flow_mL_min_by_head_mmHg", {})
    g_ratio = cr.get("measured_G_ratio")
    occlusion = cr.get("common_cause_occlusion_rate_pct")
    valid = cr.get("valid_trials_total")
    voids = cr.get("void_trial_count", 0)
    mfg_fail = cr.get("manufacturing_minwall_all_failed", False)

    trace: List[str] = []

    # Protocol-validity gate first: a run where every trial is VOID is an
    # execution failure, not a technology verdict (Art. LXI).
    if not isinstance(valid, (int, float)) or valid <= 0:
        return {"verdict": "EXECUTION_INVALID", "rule_id": "P04-VOID-ALL",
                "rule_trace": ["valid_trials_total <= 0 — every trial "
                               "failed the false-pass rules; the run "
                               "cannot adjudicate the technology "
                               "(Art. LXI: infrastructure failure is "
                               "never scientific rejection)"]}

    # KILL channel c — manufacturing invariant (Art. XXIX design-space
    # clause as pre-registered).
    if mfg_fail:
        trace.append("manufacturing_minwall_all_failed=true -> KILL "
                     "(channel c: no sample passes the min-wall constraint "
                     "across the full attempt)")
        return {"verdict": "KILL", "rule_id": "P04-KILL-C-MFG",
                "rule_trace": trace}

    # KILL channel a — the mechanism's own common-cause kill condition.
    if isinstance(occlusion, (int, float)) and occlusion >= \
            P04_COMMON_CAUSE_KILL_PCT:
        trace.append(f"common_cause_occlusion_rate {occlusion}% >= "
                     f"{P04_COMMON_CAUSE_KILL_PCT}% -> KILL (channel a: the "
                     "safety floor is occluded in the common-cause mode)")
        return {"verdict": "KILL", "rule_id": "P04-KILL-A-COMMONCAUSE",
                "rule_trace": trace}

    # KILL channel b — no meaningful protection at any head.
    vals = [v for v in flows.values() if isinstance(v, (int, float))]
    if vals and all(v < P04_Q_MIN_KILL for v in vals):
        trace.append(f"residual floor flow < {P04_Q_MIN_KILL} mL/min at ALL "
                     f"{len(vals)} heads -> KILL (channel b: no meaningful "
                     "protection)")
        return {"verdict": "KILL", "rule_id": "P04-KILL-B-NOPROTECTION",
                "rule_trace": trace}

    pass_heads = sum(1 for v in vals if v >= P04_Q_MIN_PASS)
    g_ok = (isinstance(g_ratio, (int, float))
            and abs(g_ratio / P04_G_RATIO_MODELLED - 1.0)
            <= P04_G_RATIO_TOLERANCE)
    trace.append(f"heads at >= {P04_Q_MIN_PASS} mL/min: {pass_heads}/{len(vals)}"
                 f" (required {P04_PASS_HEADS_REQUIRED}); "
                 f"G_ratio={g_ratio} vs modelled {P04_G_RATIO_MODELLED} "
                 f"within +/-{P04_G_RATIO_TOLERANCE:.0%}: {g_ok}; "
                 f"void trials: {voids}")

    # KEEP — the ACCEPT rule, verbatim.
    if pass_heads >= P04_PASS_HEADS_REQUIRED \
            and (not isinstance(occlusion, (int, float))
                 or occlusion < P04_COMMON_CAUSE_KILL_PCT) and g_ok:
        trace.append("all ACCEPT conditions hold -> KEEP "
                     "(advance with the first PHYSICAL_OBSERVATION-class "
                     "evidence)")
        return {"verdict": "KEEP", "rule_id": "P04-KEEP-ACCEPT",
                "rule_trace": trace}

    # MODIFY — the INDETERMINATE band and the Poiseuille-validity miss:
    # both route to a REGISTERED change (design or model) plus a
    # re-registered re-run; never a promotion.
    if 0 < pass_heads < P04_PASS_HEADS_REQUIRED or \
            (vals and any(P04_Q_MIN_KILL <= v < P04_Q_MIN_PASS for v in vals)):
        trace.append("residual flow lands in the 0.2-0.4 INDETERMINATE band "
                     "or too few passing heads -> MODIFY")
    elif not g_ok:
        trace.append("flows pass but the measured G ratio is outside the "
                     "+/-30% Poiseuille-validity band -> MODIFY (the "
                     "engineering model must be updated through the "
                     "adjudication machinery, then re-registered)")
    else:
        trace.append("no KEEP condition set satisfied without a KILL "
                     "condition -> MODIFY (conservative default)")
    return {"verdict": "MODIFY", "rule_id": "P04-MODIFY-INDETERMINATE",
            "rule_trace": trace}


P11_SETTLING_KILL_PCT = 20.0    # % faster than ASD, MODEL_DERIVED, frozen
P11_MDD_S = 0.0253              # s, COMPUTATIONAL_RESULT, frozen


def decide_p11(observation: Dict[str, Any]) -> Dict[str, Any]:
    """The frozen P11 contract decision rule (R407-F), pure function.

    Input: candidate_result block with per-pressure paired means:
      settling_time_s_by_pressure (damper vs ASD),
      damper_flow_deviation_worse_than_asd (bool per endpoint-2 rule).
    Verdicts: SUPPORTED / MIXED / KILLED (the R406 pre-registration's own
    vocabulary; MIXED maps to MODIFY-class: recorded exactly, no partial
    promotion)."""
    cr = observation.get("candidate_result", observation)
    settle = cr.get("settling_time_s_by_pressure", {})
    endpoint2_worse = cr.get("damper_flow_deviation_worse_than_asd", None)
    trace: List[str] = []
    if not settle:
        return {"verdict": "EXECUTION_INVALID", "rule_id": "P11-NO-DATA",
                "rule_trace": ["no settling-time data supplied"]}
    faster_all = []
    for pressure, pair in settle.items():
        d, a = pair.get("damper"), pair.get("asd")
        if not isinstance(d, (int, float)) or not isinstance(a, (int, float)):
            return {"verdict": "EXECUTION_INVALID",
                    "rule_id": "P11-MALFORMED",
                    "rule_trace": [f"malformed pair at {pressure} mmHg"]}
        pct = (a - d) / a * 100.0 if a else 0.0
        faster_all.append(pct >= P11_SETTLING_KILL_PCT)
        trace.append(f"{pressure} mmHg: damper {d}s vs ASD {a}s "
                     f"({pct:+.1f}% faster; kill-A requires >= "
                     f"{P11_SETTLING_KILL_PCT}% at ALL pressures)")
    kill_a = not all(faster_all)
    if kill_a and endpoint2_worse is True:
        trace.append("kill condition A (speed) AND kill condition B "
                     "(accuracy) both triggered -> KILLED")
        return {"verdict": "KILLED", "rule_id": "P11-KILLED-AB",
                "rule_trace": trace}
    if kill_a:
        trace.append("kill condition A triggered; endpoint 2 not decisively "
                     "positive -> KILLED per the frozen rule "
                     "('KILL unless endpoint 2 is decisively positive')")
        return {"verdict": "KILLED", "rule_id": "P11-KILLED-A",
                "rule_trace": trace}
    if endpoint2_worse is True:
        trace.append("kill condition B (flow accuracy worse than ASD at any "
                     "pressure) -> KILLED")
        return {"verdict": "KILLED", "rule_id": "P11-KILLED-B",
                "rule_trace": trace}
    endpoint1_positive = all(faster_all)
    if endpoint1_positive and endpoint2_worse is False:
        trace.append("both kill conditions avoided AND endpoint 1 "
                     "decisively positive -> SUPPORTED")
        return {"verdict": "SUPPORTED", "rule_id": "P11-SUPPORTED",
                "rule_trace": trace}
    trace.append("one differentiator positive, the other null -> MIXED "
                 "(recorded exactly; no partial promotion)")
    return {"verdict": "MIXED", "rule_id": "P11-MIXED",
            "rule_trace": trace}


# ---------------------------------------------------------------------------
# R407-C/D — prediction-vs-measurement adjudication (anti-theatre)
# ---------------------------------------------------------------------------

ADJUDICATION_CHAIN_FILES: Tuple[str, ...] = (
    "PREDICTION_BEFORE.json", "OBSERVATION.json", "MODEL_ERROR.json",
    "MODEL_UPDATE.json", "PREDICTION_AFTER.json",
)

_LEARNING_VERDICTS = ("MODEL_IMPROVED", "LEARNING_FAILED",
                      "INSUFFICIENT_DATA")


def adjudicate_learning(prediction_before: Optional[float],
                        actual_measurement: Optional[float],
                        prediction_after: Optional[float],
                        held_out: Optional[Dict[str, Any]] = None,
                        reality_event: Optional[Dict[str, Any]] = None,
                        unit: Optional[str] = None) -> Dict[str, Any]:
    """R407-C/D: build the MODEL_ERROR / MODEL_UPDATE / PREDICTION_AFTER
    record and the learning verdict.

    Improvement is measured ON THE HELD-OUT CONDITION where applicable
    (R407-D): error_after < error_before there, plus the prediction must
    actually have moved. 'A new field called model_updated=true is
    worthless.' LEARNING_FAILED is a valid, honest, recordable outcome —
    the update ran on real data and demonstrably did not improve the
    model. CONTROLLED_REHEARSAL inputs may demonstrate the machinery
    (the comparison is computed and the verdict shown) but the record
    carries counts_as_learning=false and never enters the real learning
    count (Art. XXXVIII); INSUFFICIENT_DATA covers absent components.
    """
    ho = held_out or {}
    ho_actual = ho.get("actual")
    ho_pred_before = ho.get("prediction_before", prediction_before)
    ho_pred_after = ho.get("prediction_after", prediction_after)
    rec: Dict[str, Any] = {
        "prediction_before": prediction_before,
        "actual_measurement": actual_measurement,
        "prediction_after": prediction_after,
        "unit": unit,
        "error_before": (abs(prediction_before - actual_measurement)
                         if isinstance(prediction_before, (int, float))
                         and isinstance(actual_measurement, (int, float))
                         else None),
        "error_after": (abs(prediction_after - actual_measurement)
                        if isinstance(prediction_after, (int, float))
                        and isinstance(actual_measurement, (int, float))
                        else None),
        "held_out": ho,
        "held_out_error_before": (
            abs(ho_pred_before - ho_actual)
            if isinstance(ho_pred_before, (int, float))
            and isinstance(ho_actual, (int, float)) else None),
        "held_out_error_after": (
            abs(ho_pred_after - ho_actual)
            if isinstance(ho_pred_after, (int, float))
            and isinstance(ho_actual, (int, float)) else None),
        "reality_event_id": (reality_event or {}).get("event_id"),
        "reality_source_type": (reality_event or {}).get("source_type"),
    }
    if actual_measurement is None or reality_event is None:
        rec["verdict"] = "INSUFFICIENT_DATA"
        rec["reason"] = ("no physical measurement yet — the five-file "
                         "adjudication chain is armed; fields present, "
                         "unfilled (Art. XXV)")
        return rec
    rehearsal = reality_event.get("source_type") == "CONTROLLED_REHEARSAL"
    if rehearsal:
        # Art. XXXVIII: a rehearsal may exercise the machinery and even
        # compute the comparison, but it can NEVER count as a learning
        # event. The computed verdict below is machinery demonstration
        # only; counts_as_learning is false and callers/tests pin that.
        rec["counts_as_learning"] = False
        rec["rehearsal"] = True
        rec["reason_prefix"] = ("CONTROLLED_REHEARSAL — machinery "
                                "demonstration only; never a learning "
                                "event (Art. XXXVIII). ")
    else:
        rec["counts_as_learning"] = True
    missing = [k for k in ("prediction_before", "prediction_after")
               if not isinstance(rec[k], (int, float))]
    if missing or rec["error_before"] is None or rec["error_after"] is None:
        rec["verdict"] = "INSUFFICIENT_DATA"
        rec["insufficient_fields"] = missing
        rec["reason"] = "required numeric component(s) absent"
        return rec
    moved = prediction_after != prediction_before
    # R407-D: the decisive comparison is on the HELD-OUT condition where
    # one applies; otherwise on the measured condition itself.
    if rec["held_out_error_before"] is not None \
            and rec["held_out_error_after"] is not None:
        improved_held_out = (rec["held_out_error_after"]
                             < rec["held_out_error_before"])
        basis = "held_out"
    else:
        improved_held_out = rec["error_after"] < rec["error_before"]
        basis = ("measured_condition (no held-out condition supplied - "
                 "recorded, not assumed)")
    rec["improvement_basis"] = basis
    prefix = rec.pop("reason_prefix", "")
    if improved_held_out and moved:
        rec["verdict"] = "MODEL_IMPROVED"
        rec["reason"] = prefix + (
            f"error_after < error_before on the {basis}; the "
            "prediction moved — the reality event changed "
            "future model behavior (Art. LI)")
    else:
        # R407-D: LEARNING_FAILED is the honest, valid outcome.
        rec["verdict"] = "LEARNING_FAILED"
        rec["reason"] = prefix + (
            f"improved_on_basis={improved_held_out}, "
            f"prediction_moved={moved} — the update did NOT "
            "demonstrably improve the prediction; a field "
            "named model_updated=true would be worthless here")
    return rec


def learning_ledger_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """R407-D ledger rule: only REAL-source MODEL_IMPROVED records count
    as learning. Rehearsal records are visible in the count-by-class but
    NEVER contribute to real_learning_events (Art. XXXVIII)."""
    counts = {"MODEL_IMPROVED": 0, "LEARNING_FAILED": 0,
              "INSUFFICIENT_DATA": 0}
    real_improved = 0
    for r in records:
        v = r.get("verdict")
        if v in counts:
            counts[v] += 1
        if v == "MODEL_IMPROVED" and r.get("counts_as_learning") \
                and r.get("reality_source_type") in REAL_SOURCE_TYPES:
            real_improved += 1
    return {
        "counts_by_verdict": counts,
        "real_learning_events": real_improved,
        "learning_loop_operational": real_improved > 0,
        "rule": "a rehearsal verdict may demonstrate the machinery but "
                "never counts as learning (Art. XXXVIII); a reality event "
                "that does not change future behavior is not a learning "
                "loop (R407-D)",
    }


# ---------------------------------------------------------------------------
# R407-E — loop closure on both outcomes
# ---------------------------------------------------------------------------

SUCCESS_PATH_STAGES: Tuple[str, ...] = (
    "EVIDENCE_UPDATE", "ENGINEERING_MODEL_UPDATE", "BUYER_PACKAGE_UPDATE",
    "COMMERCIAL_MATURITY_UPDATE",
)


def success_path_steps(reality_event: Dict[str, Any]) -> Dict[str, Any]:
    """The KEEP/SUPPORTED closure: each downstream stage is a machine-
    readable event gated on the SAME reality event (Art. XXXVIII causal
    mutation chain: EVENT -> EVIDENCE -> BELIEF -> ... -> PACKAGE)."""
    steps = []
    for i, stage in enumerate(SUCCESS_PATH_STAGES, 1):
        steps.append({
            "step": i,
            "stage": stage,
            "trigger_event_id": reality_event.get("event_id"),
            "requires": "the same validated REALITY_EVENT + the adjudicated "
                        "model-error/model-update record",
            "guard": "stage is NOT applied while trigger_event_id is a "
                     "CONTROLLED_REHEARSAL or absent",
        })
    return {"path": "SUCCESS", "trigger": reality_event.get("event_id"),
            "reality_class": ("REAL" if reality_event.get("source_type")
                              in REAL_SOURCE_TYPES else "REHEARSAL"),
            "stages": steps,
            "note": "physical observation -> update evidence -> update "
                    "engineering model -> update buyer package -> update "
                    "commercial maturity (R407-E success branch)"}


# Kill channel -> cemetery epistemic class (frozen mapping, Art. LIV/LI).
KILL_CHANNEL_CLASSES = {
    "P04-KILL-A-COMMONCAUSE": {
        "epistemic_class": "STRONG_CONSTRAINT",
        "class_justification": "bench-measured mechanism defeat for the "
                               "dual-lumen common-cause mode; future "
                               "candidates in this architecture family "
                               "require explicit override justification",
    },
    "P04-KILL-B-NOPROTECTION": {
        "epistemic_class": "PROVEN_INVARIANT",
        "class_justification": "measured zero protection under verified "
                               "zero-leak anchors: the small-parallel-"
                               "lumen safety floor cannot deliver Q_min in "
                               "the tested regime — a physics-level "
                               "negative for this design class",
    },
    "P04-KILL-C-MFG": {
        "epistemic_class": "STRONG_CONSTRAINT",
        "class_justification": "manufacturing invariant across the full "
                               "attempt (Art. XXIX design-space clause)",
    },
}


def kill_path_entry(decision: Dict[str, Any],
                    reality_event: Dict[str, Any]) -> Dict[str, Any]:
    """Build the cemetery-entry payload for a KILL verdict (R407-E
    failure branch). The entry vocabulary is derived from the failure
    itself so check_candidate_against_cemetery can hard-block /
    warn future candidates in the same domain (Art. LI: the failed
    technology must change future discovery behavior)."""
    rule_id = decision.get("rule_id", "UNKNOWN-KILL")
    klass = KILL_CHANNEL_CLASSES.get(rule_id, {
        "epistemic_class": "STRONG_CONSTRAINT",
        "class_justification": "default engineering-class kill"})
    return {
        "entry_id": f"KA-{reality_event.get('package_id', 'PKG')}-"
                    f"{reality_event.get('experiment_id', 'EXP')}-001",
        "territory_id": f"territory-{reality_event.get('package_id', 'PKG')}",
        "mechanism_name": f"{reality_event.get('package_id', 'PKG')} "
                          "mechanism (killed by the frozen experiment "
                          "contract)",
        "proposed_version": "R407",
        "killed_at_version": "R407",
        "kill_reason": decision.get("rule_id"),
        "what_was_proposed": reality_event.get("experiment_id"),
        "why_it_failed": "; ".join(decision.get("rule_trace", [])),
        "reusable_lesson": (f"the {reality_event.get('package_id')} "
                            "experiment contract kill condition "
                            f"{rule_id} fired on measured data; any future "
                            "candidate reusing this architecture must "
                            "confront this measurement first"),
        "what_to_avoid": "re-proposing this mechanism family without new "
                         "physics or a design change that addresses the "
                         "measured kill channel",
        "physical_constraint": (
            f"the {reality_event.get('package_id')} kill condition "
            f"{rule_id} was measured to fire under the frozen protocol; "
            "treat as binding for this architecture class until "
            "independently refuted") if klass["epistemic_class"] == \
            "PROVEN_INVARIANT" else "",
        "evidence_sources": [reality_event.get("event_id", "unknown")],
        "epistemic_class": klass["epistemic_class"],
        "epistemic_class_justification": klass["class_justification"],
        "trigger_event_id": reality_event.get("event_id"),
    }


def apply_kill_path(decision: Dict[str, Any],
                    reality_event: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the failure branch: cemetery append + failure-memory
    artifact + the discovery-constraint check that PROVES the failure
    changes future behavior (Art. LI). Imports orchestrator lazily to
    keep the engine layer free of orchestrator imports."""
    from orchestrator import mechanism_cemetery as mc
    payload = kill_path_entry(decision, reality_event)
    entry = mc.CemeteryEntry(**{k: v for k, v in payload.items()
                                if k in mc.CemeteryEntry.__dataclass_fields__
                                and k != "epistemic_class_justification"})
    mc.append_entries_to_cemetery_file([entry])
    check = mc.check_candidate_against_cemetery(
        payload["what_to_avoid"] + " " + payload["reusable_lesson"])
    return {
        "path": "KILL",
        "cemetery_entry_id": payload["entry_id"],
        "epistemic_class": payload["epistemic_class"],
        "failure_memory": {
            "lesson": payload["reusable_lesson"],
            "failed_assumption": "the mechanism survived its own "
                                 "pre-registered kill condition",
            "affected_artifacts": [reality_event.get("package_id"),
                                   reality_event.get("experiment_id")],
            "tests_added": "the kill-path battery in "
                           "tests/test_r407_first_reality_loop.py",
        },
        "discovery_constraint_check": check["verdict"],
        "note": "physical observation -> KILL -> cemetery -> failure-memory "
                "-> discovery constrained by the failure (R407-E failure "
                "branch); the cemetery is READ by the generator "
                "(mechanism_space/adapters/run), not just written",
    }


# ---------------------------------------------------------------------------
# R510 P0 — canonical production reality loop (entrypoint + executors).
#
# Closes the describe-vs-execute gap: success_path_steps() describes the
# KEEP chain and apply_kill_path() stops at the cemetery. This section
# EXECUTES both branches, records SEARCH-IMPACT, and launches the next
# search automatically — the missing constitutional loop (Art. LI).
#
# Design rules (auditor P0 directive, Constitution supreme):
#   - ONE entrypoint (execute_reality_event); no second subsystem.
#   - NOTHING here generates observation values (Art. XXXVII/XXXVIII).
#   - REHEARSAL executes machinery only: no cemetery append, no
#     learning count, no real child, permanently distinguishable.
#   - Thresholds, contracts, matcher: untouched (Cycle A banked).
#   - Canonical package/buyer schemas are never edited: mutations are
#     hash-chained sidecar records (new canonical state, versioned),
#     never foreign-schema edits (Art. IX).
# ---------------------------------------------------------------------------
REALITY_LOOP_VERSION = "reality_loop/1.0.0"

_KEEP_LAYERS = ("evidence", "engineering_model", "package_state",
                "commercial_state")


def _loop_now() -> str:
    import datetime as _dt
    return _dt.datetime.now(
        _dt.timezone.utc).isoformat(timespec="seconds") + "Z"


def _loop_sha(obj) -> str:
    return _record_hash(obj)


def _atomic_write_json(path: str, obj: Dict[str, Any]) -> None:
    """Durable write (repo R484 pattern): tmp sibling + flush + fsync +
    os.replace. A reader never sees a torn file."""
    import os as _os
    d = _os.path.dirname(path)
    if d:
        _os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
        f.flush()
        try:
            _os.fsync(f.fileno())
        except Exception:
            pass
    _os.replace(tmp, path)


def ledger_write_mechanism() -> Dict[str, str]:
    """Report the active ledger-write mechanism (observability for §3:
    callers/tests pin behavior, not internals)."""
    try:
        import fcntl  # noqa: F401
        return {"lock": "thread+fcntl.flock", "write": "tmp+fsync+replace"}
    except Exception:
        return {"lock": "thread-only-typed",
                "write": "tmp+fsync+replace",
                "note": "no POSIX flock on this platform; in-process "
                        "threads serialize via a per-path lock and every "
                        "write is atomic; concurrent multi-PROCESS "
                        "writers are NOT proven here (Art. XXV)"}


class _LedgerLocked:
    """Best-effort exclusive file lock around read-modify-write, reusing
    the repository's flock convention (mechanism_cemetery); degrades to
    a TYPED no-lock state where fcntl is unavailable (never silent).

    A per-path in-process threading lock ALWAYS applies (cheap,
    cross-platform): without it, two threads can read the same ledger
    state and last-writer-wins one entry away even though each write
    is atomic. Cross-process serialization additionally uses flock
    where the platform provides it."""

    _THREAD_LOCKS: Dict[str, object] = {}
    # Factory guard, created once at import (single-threaded) so lock
    # creation itself can never race (a lazily-created factory guard
    # would reintroduce the exact lost-update race this class exists
    # to prevent — caught by the concurrent-duplicate battery test).
    _FACTORY_GUARD = threading.Lock()

    def __init__(self, ledger_path: str):
        self._path = ledger_path + ".lock"
        self._fh = None
        self._tlock = None
        self.state = "UNLOCKED"

    def __enter__(self):
        import os as _os
        d = _os.path.dirname(self._path)
        if d:
            _os.makedirs(d, exist_ok=True)
        key = _os.path.abspath(self._path)
        with _LedgerLocked._FACTORY_GUARD:
            lock = self._THREAD_LOCKS.get(key)
            if lock is None:
                lock = threading.Lock()
                self._THREAD_LOCKS[key] = lock
        lock.acquire()
        self._tlock = lock
        try:
            import fcntl
            self._fh = open(self._path, "w")
            fcntl.flock(self._fh, fcntl.LOCK_EX)
            self.state = "FLOCK_EXCLUSIVE+THREAD"
        except Exception:
            self._fh = None
            self.state = "THREAD_ONLY_TYPED_SINGLE_PROCESS"
        return self

    def __exit__(self, *exc):
        try:
            if self._fh is not None:
                import fcntl
                fcntl.flock(self._fh, fcntl.LOCK_UN)
                self._fh.close()
        except Exception:
            pass
        try:
            if self._tlock is not None:
                self._tlock.release()
        except Exception:
            pass
        return False


def ingest_reality_event_durable(event: Dict[str, Any],
                                 ledger_path: str) -> Dict:
    """Durable variant of ingest_reality_event: identical validation,
    double-entry, hash-chain and return semantics; the read-modify-write
    runs under _LedgerLocked and persistence is atomic. The legacy
    function is preserved byte-for-behavior (R407 battery pins it)."""
    problems = validate_reality_event_v2(event)
    if problems:
        return {"ingested": False, "problems": problems}
    with _LedgerLocked(ledger_path) as _lk:
        ledger: Dict[str, Any] = {"artifact_type": "REALITY_EVENT_LEDGER",
                                   "entries": []}
        if os.path.exists(ledger_path):
            try:
                with open(ledger_path, encoding="utf-8") as f:
                    ledger = json.load(f)
            except Exception as exc:
                return {"ingested": False,
                        "problems": ["ledger CORRUPT_UNREADABLE: %s "
                                     "(typed; never parsed partially, "
                                     "never repaired silently)" %
                                     (type(exc).__name__,)],
                        "ledger_state": "CORRUPT_UNREADABLE"}
            if not isinstance(ledger, dict) or not isinstance(
                    ledger.get("entries", []), list):
                return {"ingested": False,
                        "problems": ["ledger MALFORMED: entries is not "
                                     "a list (typed)"],
                        "ledger_state": "MALFORMED"}
        if any(e.get("event_id") == event["event_id"]
               for e in ledger.get("entries", [])):
            return {"ingested": False,
                    "problems": [f"event_id {event['event_id']} already in "
                                 "the ledger (double entry rejected)"]}
        prev = ledger["entries"][-1]["entry_sha256"] \
            if ledger["entries"] else "GENESIS"
        entry = {
            "event_id": event["event_id"],
            "package_id": event["package_id"],
            "experiment_id": event["experiment_id"],
            "source_type": event["source_type"],
            "timestamp": event["timestamp"],
            "reality_class": ("REAL" if event["source_type"]
                              in REAL_SOURCE_TYPES
                              else "CONTROLLED_REHEARSAL"),
            "record": event,
            "prev_entry_sha256": prev,
        }
        entry["entry_sha256"] = _record_hash(
            {"prev": prev, "record": event})
        ledger["entries"].append(entry)
        ledger["entry_count"] = len(ledger["entries"])
        ledger["real_event_count"] = sum(
            1 for e in ledger["entries"] if e["reality_class"] == "REAL")
        _atomic_write_json(ledger_path, ledger)
    return {"ingested": True, "entry_sha256": entry["entry_sha256"],
            "ledger_entry_count": ledger["entry_count"],
            "real_event_count": ledger["real_event_count"]}


def _cemetery_has_trigger(cemetery_path: str, event_id: str,
                          ledger_dir=None) -> Optional[str]:
    """Idempotency guard: has this event already produced a cemetery
    entry? Consults the loop's trigger sidecar first (exact linkage,
    written at append time), then falls back to scanning raw file
    entries (trigger linkage may not survive the dataclass projection;
    evidence_sources carries the event id). Returns the entry_id or
    None."""
    if ledger_dir is not None:
        sidecar = os.path.join(ledger_dir, "cemetery_links",
                               event_id + ".json")
        if os.path.exists(sidecar):
            try:
                return json.load(
                    open(sidecar, encoding="utf-8")).get(
                        "cemetery_entry_id")
            except Exception:
                pass
    if not os.path.exists(cemetery_path):
        return None
    try:
        data = json.load(open(cemetery_path, encoding="utf-8"))
    except Exception:
        return None
    for e in data.get("entries", []):
        if isinstance(e, dict) and (e.get("trigger_event_id") == event_id
                                    or event_id in
                                    (e.get("evidence_sources") or [])):
            return e.get("entry_id")
    return None


def _record_cemetery_link(ledger_dir: str, event_id: str,
                          entry_id: str) -> None:
    """Persist the event->entry linkage the dataclass projection drops
    (trigger_event_id is not a CemeteryEntry field). Without this, a
    re-execution cannot prove its own prior append (Art. XI)."""
    _atomic_write_json(os.path.join(
        ledger_dir, "cemetery_links", event_id + ".json"),
        {"trigger_event_id": event_id, "cemetery_entry_id": entry_id,
         "recorded_at": _loop_now()})


def _exec_path(ledger_dir: str, event_id: str) -> str:
    return os.path.join(ledger_dir, "executions", event_id + ".json")


class LauncherRejected(Exception):
    """A typed PROVEN pre-launch rejection: the launcher verified,
    before producing any execution effect, that the work was refused
    (bad request shape, unknown capability, refused admission). Only
    this type may become LAUNCH_FAILED. Every other launcher
    exception (timeout, disconnect, unknown remote result) is an
    AMBIGUOUS outcome -> UNKNOWN_LAUNCH, never FAILED (§6)."""


def _launch_id_for(trigger_event_id: str, child_run_id: str,
                   knowledge_record_id) -> str:
    """Deterministic launch identity (§3): derived from the durable
    child request fields, never from a random per-attempt value. The
    same request retries/restarts converge on the same id, so an
    idempotent launcher maps them to one execution effect."""
    return _loop_sha({"trigger": trigger_event_id,
                      "child_run_id": child_run_id,
                      "knowledge": knowledge_record_id})[:32]


def _verify_request(req: Dict) -> tuple:
    """Integrity gate (attack G): recompute the launch id from the
    request's own fields. Mismatch -> the record was tampered with
    (or written by a divergent writer) -> fail closed, never launch."""
    try:
        expect = _launch_id_for(req.get("trigger_event_id"),
                                req.get("child_run_id"),
                                req.get("knowledge_record_id"))
    except Exception:
        return False, "unreadable request fields (typed)"
    if req.get("launch_id") != expect:
        return False, ("launch_id mismatch: stored %r vs recomputed "
                       "%r (tamper or divergent writer; fail-closed, "
                       "never launch)" % (req.get("launch_id"), expect))
    return True, "integrity-ok"


def _ledger_entry(ledger_path: str, event_id: str) -> Optional[Dict]:
    """Read one ledger entry by id (resume path; read-only)."""
    if not os.path.exists(ledger_path):
        return None
    try:
        for e in json.load(
                open(ledger_path, encoding="utf-8")).get("entries", []):
            if e.get("event_id") == event_id:
                return e
    except Exception:
        pass
    return None


def _load_execution(ledger_dir: str, event_id: str) -> Optional[Dict]:
    p = _exec_path(ledger_dir, event_id)
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None


def _execution_is_corrupt(ledger_dir: str, event_id: str) -> bool:
    """True iff an execution record file exists but is unparseable.
    A corrupt record must NEVER be treated as absence (that would
    relaunch finalized work). Fail-closed UNKNOWN instead (§7)."""
    p = _exec_path(ledger_dir, event_id)
    if not os.path.exists(p):
        return False
    try:
        json.load(open(p, encoding="utf-8"))
        return False
    except Exception:
        return True


def _ledgers_verify(ledger_dir: str) -> Dict:
    """verify_ledger() as an actual precondition (§8): every ledger
    file present must chain-verify; a present-but-invalid ledger
    fails recovery closed. Absent files are not evidence either way
    (reported, never assumed)."""
    out = {}
    for name in ("REALITY_EVENT_LEDGER.json",
                 "REHEARSAL_EVENT_LEDGER.json"):
        p = os.path.join(ledger_dir, name)
        if not os.path.exists(p):
            out[name] = {"present": False}
            continue
        out[name] = dict({"present": True}, **verify_ledger(p))
    return out


def _ledgers_all_valid(ledger_dir: str):
    """(ok, detail): True iff every PRESENT ledger verifies."""
    detail = _ledgers_verify(ledger_dir)
    bad = {k: v for k, v in detail.items()
           if v.get("present") and not v.get("valid")}
    if bad:
        return False, {"invalid_ledgers": bad}
    return True, detail


def _default_session_store():
    """The approved application credential path, resolved lazily (same
    pattern as the cemetery import: no layer inversion at module load).
    Caller identity is the owner capability the server issues and the
    session store recognizes — never a new key type (nothing invented)."""
    from TOSCANINI import sessions as _sessions
    return _sessions


def _authorize_caller(auth, session_store=None):
    """Bind authenticated caller identity (§4). A caller-provided
    operator/organization STRING is provenance metadata, never
    authentication. Authentication = presenting the owner capability
    the session store issued for the claimed session id
    (TOSCANINI.sessions.session_access: OWNER | PUBLIC | DENY | None).

    Returns (ok, record). The record carries session_id + access
    verdict ONLY — key values are never persisted, printed, or
    returned (BS-021). Missing/invalid/unreachable capability ->
    fail-closed denial (typed, never a scientific verdict).
    """
    base = {"mode": "owner-capability", "authenticated": False}
    if not isinstance(auth, dict):
        return False, dict(base, reason="no caller capability presented "
                                        "(fail-closed)")
    sid, key = auth.get("session_id"), auth.get("owner_key")
    if not sid or not key:
        return False, dict(
            base, reason="session_id + owner_key both required",
            session_id=sid)
    try:
        store = session_store or _default_session_store()
        access = store.session_access(sid, key)
    except Exception as exc:  # noqa: BLE001 — typed (Art. XXV)
        return False, dict(
            base, session_id=sid,
            reason="credential store unreachable: %s (typed; not a "
                   "scientific verdict)" % (type(exc).__name__,))
    ok = access in ("OWNER", "PUBLIC")
    return ok, {"mode": "owner-capability", "session_id": sid,
                "access": access, "authenticated": ok}


def execute_reality_event(event: Dict[str, Any], ledger_dir: str,
                          run_launcher=None,
                          parent_problem: Optional[Dict] = None,
                          parent_run_id: Optional[str] = None,
                          cemetery_path: Optional[str] = None,
                          runs_root: Optional[str] = None,
                          auth=None, session_store=None,
                          parent_run_dir: Optional[str] = None) -> Dict:
    """THE canonical production reality entrypoint (P0 §A).

    validate -> authorize (provenance/attestation, from mandatory
    fields; no new auth infra) -> idempotency (stored execution
    returned, never re-executed) -> durable append -> adjudicate ->
    branch execution (KEEP/MODIFY/KILL) -> SEARCH-IMPACT ->
    child request -> launch-or-defer.

    cemetery_path: override for the canonical cemetery location
    (tests redirect to tmp; production omits it and uses the
    canonical file — canonical state never touched by tests, Art.
    IX). runs_root: where a default launcher materializes child
    runs (tests pass tmp or a fake launcher). auth: caller
    capability {"session_id", "owner_key"} bound via the approved
    owner-capability path (fail-closed; §4). session_store: injectable
    credential store (tests pass fakes; default is the production
    session surface). parent_run_dir: optional parent run directory
    for operator-region reads (else typed UNKNOWN).
    """
    evid = (event or {}).get("event_id", "unknown-event")
    problems = validate_reality_event_v2(event)
    if problems:
        return {"executed": False, "event_id": evid,
                "execution_state": "EXECUTION_INVALID",
                "problems": problems,
                "note": "ingestion failure is an execution state, never "
                        "a scientific verdict (Art. LXI)"}
    authed, auth_rec = _authorize_caller(auth, session_store)
    if not authed:
        return {"executed": False, "event_id": evid,
                "execution_state": "EXECUTION_BLOCKED",
                "auth": auth_rec,
                "note": "unauthenticated caller is refused before any "
                        "state is read or written (fail-closed; the "
                        "event's declared operator string is provenance "
                        "metadata, never authentication)"}
    rehearsal = event.get("source_type") == "CONTROLLED_REHEARSAL"
    prior = _load_execution(ledger_dir, event["event_id"])
    if prior is not None:
        replayed = dict(prior)
        replayed["duplicate"] = True
        replayed["replayed"] = True
        return replayed
    ledger_path = os.path.join(
        ledger_dir, "REHEARSAL_EVENT_LEDGER.json" if rehearsal
        else "REALITY_EVENT_LEDGER.json")
    ing = ingest_reality_event_durable(event, ledger_path)
    if not ing.get("ingested"):
        # Double-entry here is AMBIGUOUS by construction: it means a
        # crashed predecessor (resumable) OR an in-flight concurrent
        # ingester (must not be disturbed). The ingester cannot tell
        # them apart, so it BLOCKS with resumable:true and never
        # auto-continues (auto-continue turned 8 concurrent ingesters
        # into 8 executions — caught by the concurrent-duplicate
        # battery). Crash recovery is the explicit resume_execution()
        # path below, never re-execution.
        return {"executed": False, "event_id": event["event_id"],
                "execution_state": "EXECUTION_BLOCKED",
                "problems": ing.get("problems"),
                "resumable": _ledger_entry(ledger_path,
                                           event["event_id"]) is not None,
                "note": "ledger refused the event; nothing downstream "
                        "ran (Art. LXI). A durable-but-unfinalized event "
                        "is resumed explicitly, never by re-execution."}
    _mark_phase(ledger_dir, event["event_id"], "EVENT_PERSISTED")
    return _continue_execution(
        event, ledger_dir, ing, cemetery_path, run_launcher,
        parent_problem, parent_run_id, parent_run_dir, rehearsal,
        auth_rec, _cem_target=None, resumed=False)


def _resume_ledger_gate(ledger_dir: str, event_id: str):
    """verify_ledger() as a resume precondition (§8): locate the durable
    entry, then require its ledger file to chain-verify. Returns
    (ledger_path, entry, refusal). A present-but-invalid chain fails
    recovery closed — resume must not consume a parseable record whose
    hash chain is broken. A corrupt execution record fails closed too
    (never treated as absence: relaunching finalized work would fork
    execution)."""
    if _execution_is_corrupt(ledger_dir, event_id):
        return None, None, {"gate": "execution-record-corrupt",
                            "reason": "an execution record file exists "
                                      "but is unparseable; refusing to "
                                      "treat it as absence (fail-closed)"}
    for _ledger in ("REALITY_EVENT_LEDGER.json",
                    "REHEARSAL_EVENT_LEDGER.json"):
        _path = os.path.join(ledger_dir, _ledger)
        if not os.path.exists(_path):
            continue
        _entry = _ledger_entry(_path, event_id)
        if _entry is None:
            continue
        _verdict = verify_ledger(_path)
        if not _verdict.get("valid"):
            return None, None, {
                "gate": "ledger-invalid",
                "ledger": _ledger,
                "reason": _verdict.get("reason"),
                "note": "resume refuses to consume from a hash-broken "
                        "chain (fail-closed)"}
        return _path, _entry, None
    return None, None, {"gate": "no-durable-entry",
                        "reason": "no ledger entry for this event id; "
                                  "nothing to resume (Art. XXV)"}


def resume_execution(ledger_dir: str, event_id: str, run_launcher=None,
                     parent_problem: Optional[Dict] = None,
                     parent_run_id: Optional[str] = None,
                     cemetery_path: Optional[str] = None,
                     auth=None, session_store=None,
                     parent_run_dir: Optional[str] = None) -> Dict:
    """Explicit crash recovery (§12 boundaries C/D): continue a
    durable-but-unfinalized event. Auth enforced identically
    (fail-closed). Ledger entry absent -> UNKNOWN (nothing to resume,
    never invented). Execution record FINALIZED -> replay-return
    duplicate. Else re-run branch+finalize with re-supplied inputs;
    every non-idempotent step is guarded (cemetery sidecar, child
    claim, deterministic record overwrites). The event bytes come
    from the DURABLE ledger entry itself, never re-supplied."""
    _, auth_rec = _authorize_caller(auth, session_store)
    if not _authorize_caller(auth, session_store)[0]:
        return {"executed": False, "event_id": event_id,
                "execution_state": "EXECUTION_BLOCKED",
                "auth": auth_rec,
                "note": "resume requires the same capability as "
                        "execution (fail-closed)"}
    entry = None
    _lpath, _entry, _refusal = _resume_ledger_gate(ledger_dir, event_id)
    if _refusal is not None:
        return {"executed": False, "event_id": event_id,
                "execution_state": "UNKNOWN",
                "resume_gate": _refusal,
                "note": "resume refused at the ledger gate (fail-closed)"}
    entry = _entry
    prior = _load_execution(ledger_dir, event_id)
    if prior is not None and prior.get("executed"):
        replayed = dict(prior)
        replayed["duplicate"] = True
        replayed["replayed"] = True
        return replayed
    event = entry.get("record") or {}
    rehearsal = event.get("source_type") == "CONTROLLED_REHEARSAL"
    ing = {"ingested": True,
           "entry_sha256": entry.get("entry_sha256"),
           "ledger_entry_count": None, "real_event_count": None,
           "resumed_after_crash": True}
    return _continue_execution(
        event, ledger_dir, ing, cemetery_path, run_launcher,
        parent_problem, parent_run_id, parent_run_dir, rehearsal,
        auth_rec, _cem_target=None, resumed=True)


def _continue_execution(event, ledger_dir, ing, cemetery_path,
                        run_launcher, parent_problem, parent_run_id,
                        parent_run_dir, rehearsal, auth_rec,
                        _cem_target, resumed: bool) -> Dict:
    """Shared execution tail: verdict routing -> branch -> registry ->
    finalize -> execution record. Used by execute (fresh ingest) and
    resume (durable entry) alike."""
    from orchestrator import mechanism_cemetery as _mc
    if _cem_target is None:
        _cem_target = str(cemetery_path) if cemetery_path else str(
            _mc.CEMETERY_PATH)
    _cem_before = _cemetery_head(_cem_target)
    verdict = (event.get("decision") or {}).get("verdict")
    if verdict in ("EXECUTION_INVALID", "EXECUTION_BLOCKED"):
        rec = {"executed": False, "event_id": event["event_id"],
               "execution_state": verdict,
               "entry_sha256": ing["entry_sha256"],
               "note": "the frozen contract itself reports an execution "
                       "state; no scientific branch runs"}
        _atomic_write_json(_exec_path(ledger_dir, event["event_id"]), rec)
        return rec
    if verdict in ("KEEP", "SUPPORTED"):
        branch, out = "KEEP", _execute_keep(
            event, ledger_dir, parent_problem, parent_run_id, rehearsal)
    elif verdict == "MODIFY":
        branch, out = "MODIFY", _execute_modify(
            event, ledger_dir, parent_problem, parent_run_id, rehearsal)
    elif verdict in ("KILL", "KILLED"):
        branch, out = "KILL", _execute_kill(
            event, ledger_dir, parent_problem, parent_run_id, rehearsal,
            cemetery_path)
    else:  # MIXED or any other machine verdict: conservative superset
        branch, out = "MODIFY", _execute_modify(
            event, ledger_dir, parent_problem, parent_run_id, rehearsal)
        out["mixed_routing"] = (
            "verdict %r is ambiguous; MODIFY is the non-destructive "
            "superset path (never auto-KILL on ambiguity)"
            % (verdict,))
    counts_learning = _learning_countable(event, out)
    _mark_phase(ledger_dir, event["event_id"], "BRANCH_EXECUTED")
    if rehearsal:
        _reg_before = _reg_after = "REHEARSAL_NO_REGISTRY_WRITE"
    else:
        try:
            _reg_before, _reg_after = _apply_event_to_state(
                ledger_dir, event, branch, out)
        except _RealityStateCorrupt as exc:
            return {"executed": False, "event_id": event["event_id"],
                    "execution_state": "EXECUTION_BLOCKED",
                    "problems": [str(exc)],
                    "note": "canonical registry unreadable; refusing to "
                            "fork canonical state (typed, never a "
                            "scientific verdict)"}
    _cem_after = _cemetery_head(_cem_target)
    fin = _finalize_execution(
        event, ledger_dir, branch, out, run_launcher, parent_problem,
        rehearsal, parent_run_dir=parent_run_dir,
        cemetery_path=cemetery_path,
        registry_hashes={"before": _reg_before, "after": _reg_after},
        cemetery_bounds={"before": _cem_before, "after": _cem_after})
    rec = {"executed": True, "event_id": event["event_id"],
           "execution_state": ("EXECUTED_REHEARSAL" if rehearsal
                               else "EXECUTED_REAL"),
           "branch": branch,
           "resumed_after_crash": resumed,
           "entry_sha256": ing["entry_sha256"],
           "reality_class": ("CONTROLLED_REHEARSAL" if rehearsal
                             else "REAL"),
           "counts_as_physical_learning": counts_learning,
           "auth": auth_rec,
           "branch_record": out,
           "search_impact": fin["search_impact"],
           "child": fin["child"],
           "phase": "FINALIZED",
           "loop_version": REALITY_LOOP_VERSION,
           "reviewer_provenance": "AI_REVIEW"}
    _mark_phase(ledger_dir, event["event_id"], "FINALIZED")
    _atomic_write_json(_exec_path(ledger_dir, event["event_id"]), rec)
    return rec


def _learning_countable(event: Dict, branch_out: Dict) -> object:
    """counts_as_physical_learning (entrypoint rule, disclosed): False
    for rehearsal, ALWAYS. For REAL: True only when the adjudication
    verdict is MODEL_IMPROVED; INSUFFICIENT_DATA/LEARNING_FAILED stay
    False (a field named true would be worthless there). UNDETERMINED
    when no adjudication ran (never guessed).

    §18 separation: a legacy counts_as_learning flag carried inside an
    adjudication record is NEVER consulted here — only the verdict
    rules. The legacy helper keeps its historical semantics untouched;
    this rule is the explicit authoritative eligibility for physical-
    learning claims, and a regression test pins the separation."""
    if event.get("source_type") == "CONTROLLED_REHEARSAL":
        return False
    adj = (branch_out or {}).get("adjudication") or {}
    if not adj:
        return "UNDETERMINED"
    return True if adj.get("verdict") == "MODEL_IMPROVED" else False


def _adjudicate_if_numbered(event: Dict) -> Dict:
    """Run the existing adjudicator on the event's own numbers where
    present (optional prediction_before/prediction_after keys; the
    measurement is candidate_result when numeric). Absent numbers ->
    honest INSUFFICIENT_DATA (never invented)."""
    def _num(v):
        return v if isinstance(v, (int, float)) and v == v else None
    actual = _num(event.get("candidate_result"))
    before = _num(event.get("baseline_result"))
    after = _num(event.get("prediction_after"))
    held = event.get("held_out") if isinstance(
        event.get("held_out"), dict) else None
    return adjudicate_learning(before, actual, after, held_out=held,
                               reality_event=event,
                               unit=(event.get("measurement_units") or {})
                               .get("unit"))


def _parent_hashes(parent_problem, parent_run_id) -> Dict:
    if not isinstance(parent_problem, dict):
        return {"parent_problem": "NOT_SUPPLIED"}
    blob = json.dumps(parent_problem, sort_keys=True, separators=(",", ":"))
    return {"parent_problem_sha256": hashlib.sha256(
        blob.encode()).hexdigest(),
        "parent_run_id": parent_run_id}


def _execute_keep(event, ledger_dir, parent_problem, parent_run_id,
                  rehearsal: bool) -> Dict:
    """KEEP/SUPPORTED executor: evidence link + model-error adjudication
    + package/commercial MUTATION sidecars (new hash-chained canonical
    records; foreign schemas never edited — Art. IX). Layers without
    bound parents record NOT_APPLICABLE with reason (never fabricated).
    """
    scope = "rehearsal" if rehearsal else "real"
    layers = {}
    layers["evidence"] = {
        "state": "LINKED",
        "link": {"event_id": event["event_id"],
                 "package_id": event["package_id"],
                 "experiment_id": event["experiment_id"],
                 **_parent_hashes(parent_problem, parent_run_id)},
    }
    adj = _adjudicate_if_numbered(event)
    layers["model_error"] = {
        "state": ("ADJUDICATED" if adj.get("verdict") !=
                  "INSUFFICIENT_DATA" else "NOT_APPLICABLE"),
        "adjudication": adj,
        "reason": (None if adj.get("verdict") != "INSUFFICIENT_DATA"
                   else "no numeric prediction_before/after on the event; "
                        "measurement alone is not a model update"),
    }
    for layer in ("package_state", "commercial_state"):
        if parent_run_id is None:
            layers[layer] = {"state": "NOT_APPLICABLE",
                             "reason": "no parent run bound; nothing to "
                                       "mutate (Art. XXV)"}
            continue
        mut = {"artifact_type": "REALITY_MUTATION/1.0.0",
               "mutation_id": "MUT-%s-%s" % (event["event_id"], layer),
               "event_id": event["event_id"],
               "package_id": event["package_id"],
               "experiment_id": event["experiment_id"],
               "layer": layer,
               "parent": _parent_hashes(parent_problem, parent_run_id),
               "new_state": "REALITY_CONFIRMED",
               "scope": scope,
               "recorded_at": _loop_now()}
        mut["mutation_sha256"] = _loop_sha(mut)
        if not rehearsal:
            _atomic_write_json(os.path.join(
                ledger_dir, "mutations",
                event["event_id"] + "." + layer + ".json"), mut)
        layers[layer] = {"state": "MUTATED", "mutation_id":
                         mut["mutation_id"],
                         "mutation_sha256": mut["mutation_sha256"]}
    return {"path": "KEEP", "scope": scope, "layers": layers,
            "adjudication": adj}


def _delta_rendering(event: Dict) -> Dict:
    """Deterministic delta from the event's own numbers (arithmetic
    only, never prose): candidate vs baseline with the pre-registered
    threshold. Non-numeric inputs stay UNKNOWN (never coerced)."""
    def _num(v):
        return v if isinstance(v, (int, float)) and v == v else None
    cand, base = _num(event.get("candidate_result")), _num(
        event.get("baseline_result"))
    thr = _num(event.get("pre_registered_threshold"))
    if cand is None or base is None:
        return {"direction": "UNKNOWN",
                "reason": "non-numeric candidate/baseline on the event"}
    direction = "up" if cand > base else (
        "down" if cand < base else "equal")
    met = (cand >= thr) if thr is not None else "UNKNOWN"
    return {"candidate": cand, "baseline": base, "direction": direction,
            "threshold": thr, "threshold_met": met}


def _execute_modify(event, ledger_dir, parent_problem, parent_run_id,
                    rehearsal: bool) -> Dict:
    """MODIFY executor: registered hypothesis (deterministic delta) +
    next-search request. The hypothesis is a record, never an assertion
    of improvement."""
    scope = "rehearsal" if rehearsal else "real"
    hyp = {"artifact_type": "REALITY_HYPOTHESIS/1.0.0",
           "hypothesis_id": "HYP-" + str(event["event_id"]),
           "event_id": event["event_id"],
           "package_id": event["package_id"],
           "experiment_id": event["experiment_id"],
           "delta": _delta_rendering(event),
           "decision_trace": (event.get("decision") or {}),
           "parent": _parent_hashes(parent_problem, parent_run_id),
           "scope": scope,
           "recorded_at": _loop_now()}
    hyp["hypothesis_sha256"] = _loop_sha(hyp)
    if not rehearsal:
        _atomic_write_json(os.path.join(
            ledger_dir, "hypotheses", event["event_id"] + ".json"), hyp)
    adj = _adjudicate_if_numbered(event)
    child = _request_child(event, ledger_dir, parent_problem,
                           parent_run_id, hyp["hypothesis_id"],
                           "MODIFY", rehearsal,
                           knowledge_artifact=_knowledge_canonical(hyp))
    return {"path": "MODIFY", "scope": scope, "hypothesis": hyp,
            "adjudication": adj, "child_request": child}


def _append_cemetery_entries(entries, cemetery_path: str) -> None:
    """Append cemetery entries atomically to an EXPLICIT path (the loop's
    own append — never the canonical file by accident). Semantics mirror
    the canonical append (history-preserving extend + _chain_extend +
    counts) with atomic tmp+replace writes and best-effort locking.
    Rationale (recorded): the canonical append hardcodes CEMETERY_PATH
    (untestable without touching canonical state, Art. IX) and crashes
    where fcntl is unavailable; this path-parameterized variant keeps
    byte-compatible semantics. No matcher logic lives here (Cycle A
    banked)."""
    import dataclasses as _dc
    from orchestrator import mechanism_cemetery as mc
    with _LedgerLocked(cemetery_path):
        if os.path.exists(cemetery_path):
            with open(cemetery_path, encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"description": "Library of impossibilities — every "
                                   "killed invention with reusable "
                                   "lessons.",
                    "entries": []}
        data.setdefault("entries", []).extend(
            _dc.asdict(e) for e in entries)
        mc._chain_extend(data)
        data["entry_count"] = len(data["entries"])
        data["updated_at"] = _loop_now()
        _atomic_write_json(cemetery_path, data)


def _cemetery_entry_by_id(cemetery_path: str,
                          entry_id: str) -> Optional[Dict]:
    """Read one cemetery entry by id (verbatim bytes for knowledge
    binding). None when absent/unreadable (typed by callers, never
    guessed)."""
    if not os.path.exists(str(cemetery_path)):
        return None
    try:
        data = json.load(open(str(cemetery_path), encoding="utf-8"))
    except Exception:
        return None
    for e in data.get("entries", []):
        if isinstance(e, dict) and e.get("entry_id") == entry_id:
            return e
    return None


def _knowledge_canonical(artifact) -> Dict:
    """Canonical knowledge bytes for binding: the artifact dict minus
    chain-bookkeeping keys (prev_entry_sha256 and friends) that
    append-time chaining adds AFTER the request binds its hash. Both
    the binder (_request_child inputs) and the verifier strip the
    same keys, so file-round-tripped entries still match (Art. X:
    one canonical byte form)."""
    if not isinstance(artifact, dict):
        return artifact
    return {k: v for k, v in artifact.items()
            if k != "prev_entry_sha256"}


def _execute_kill(event, ledger_dir, parent_problem, parent_run_id,
                  rehearsal: bool, cemetery_path=None) -> Dict:
    """KILL executor: cemetery append (REAL only — rehearsal NEVER
    appends, recorded as rehearsal_cemetery_skipped) + failure memory
    + search constraint + child request. Idempotent: an existing entry
    with this trigger is reused, never double-appended."""
    scope = "rehearsal" if rehearsal else "real"
    from orchestrator import mechanism_cemetery as mc
    cpath = str(cemetery_path) if cemetery_path else None
    if rehearsal:
        payload = kill_path_entry(event.get("decision") or {},
                                  event)
        return {"path": "KILL", "scope": scope,
                "rehearsal_cemetery_skipped": {
                    "reason": "CONTROLLED_REHEARSAL must never append "
                              "real negative knowledge (Art. "
                              "XXXVII/XXXVIII)",
                    "would_be_entry": payload.get("entry_id"),
                    "would_be_class": payload.get("epistemic_class")},
                "failure_memory": {
                    "lesson": payload.get("reusable_lesson"),
                    "rehearsal": True},
                "search_constraint": None,
                "child_request": _request_child(
                    event, ledger_dir, parent_problem, parent_run_id,
                    None, "KILL", True)}
    target = cpath or str(mc.CEMETERY_PATH)
    existing = _cemetery_has_trigger(target, event["event_id"], ledger_dir)
    if existing is not None:
        entry_id, appended = existing, False
        check_verdict = "REUSED_EXISTING_ENTRY"
        knowledge_artifact = _cemetery_entry_by_id(target, entry_id)
    else:
        payload = kill_path_entry(event.get("decision") or {}, event)
        artifact_view = {
            k: v for k, v in payload.items()
            if k in mc.CemeteryEntry.__dataclass_fields__
            and k != "epistemic_class_justification"}
        entry = mc.CemeteryEntry(**artifact_view)
        _append_cemetery_entries([entry], target)
        _record_cemetery_link(ledger_dir, event["event_id"],
                              payload.get("entry_id"))
        check = mc.check_candidate_against_cemetery(
            payload["what_to_avoid"] + " " + payload["reusable_lesson"])
        entry_id, appended = payload.get("entry_id"), True
        check_verdict = check.get("verdict")
        knowledge_artifact = artifact_view
    constraint = {
        "excluded_cemetery_entry": entry_id,
        "trigger_event_id": event["event_id"],
        "rule": "future candidates matching this entry consult it "
                "through the existing cemetery gate (no new matcher)",
    }
    child = _request_child(event, ledger_dir, parent_problem,
                           parent_run_id, entry_id, "KILL", False,
                           knowledge_artifact=_knowledge_canonical(
                               knowledge_artifact))
    adj = _adjudicate_if_numbered(event)
    return {"path": "KILL", "scope": scope, "cemetery_entry_id": entry_id,
            "cemetery_appended": appended, "search_constraint": constraint,
            "cemetery_check_verdict": check_verdict,
            "failure_memory": {
                "lesson": ("kill condition fired on measured data; "
                           "see cemetery entry %s" % (entry_id,)),
                "failed_assumption": "the mechanism survived its own "
                                     "pre-registered kill condition",
                "affected_artifacts": [event.get("package_id"),
                                       event.get("experiment_id")]},
            "adjudication": adj, "child_request": child}


def _child_problem(parent_problem, event, knowledge_id, branch,
                   parent_run_id=None, parent_problem_sha256=None,
                   knowledge_artifact_sha256=None):
    """Deterministic child problem: parent bytes preserved verbatim;
    ONE appended reality-constraint clause (delimited, sourced) plus a
    reality_constraints block carrying full lineage (trigger, knowledge
    id + artifact hash, parent run id + problem hash). No other byte
    changes. The block is what the child execution path reads to
    produce its consumption receipt — lineage travels in the problem,
    never in side channels."""
    import copy as _copy
    child = _copy.deepcopy(parent_problem)
    clause = "[REALITY %s: %s knowledge %s constrains this search]" % (
        event["event_id"], branch, knowledge_id)
    prior = str(child.get("constraint") or "")
    child["constraint"] = (prior + " " + clause).strip()
    child["reality_constraints"] = {
        "trigger_event_id": event["event_id"],
        "knowledge_record_id": knowledge_id,
        "knowledge_artifact_sha256": knowledge_artifact_sha256,
        "parent_run_id": parent_run_id,
        "parent_problem_sha256": parent_problem_sha256,
        "branch": branch,
        "constraint_clause": clause,
    }
    pid = str(child.get("problem_id") or "problem")
    child["problem_id"] = pid + "+reality-" + str(
        event["event_id"])[-8:]
    return child


def _request_child(event, ledger_dir, parent_problem, parent_run_id,
                   knowledge_id, branch, rehearsal: bool,
                   knowledge_artifact=None) -> Dict:
    """Persist the child-search request BEFORE any launch (restart
    recovery reads these). Exactly one request per trigger: existing
    file is reused. Rehearsal requests are launchable:false, forever.
    A missing parent problem makes the request UNLAUNCHABLE (typed —
    no fabricated problem, Art. XXV). The knowledge artifact hash is
    bound here (not reconstructed later) so consumption receipts can
    verify identity without re-derivation.
    """
    req_path = os.path.join(ledger_dir, "child_requests",
                            event["event_id"] + ".json")
    if os.path.exists(req_path):
        try:
            prior = json.load(open(req_path, encoding="utf-8"))
            prior["duplicate"] = True
            return prior
        except Exception:
            pass
    if not isinstance(parent_problem, dict):
        req = {"trigger_event_id": event["event_id"], "branch": branch,
               "knowledge_record_id": knowledge_id,
               "launchable": False, "status": "UNLAUNCHABLE",
               "reason": "no parent problem supplied; no problem is "
                         "fabricated (Art. XXV)",
               "rehearsal": rehearsal}
        if not rehearsal:
            _atomic_write_json(req_path, req)
        return req
    child_problem = _child_problem(
        parent_problem, event, knowledge_id, branch,
        parent_run_id=parent_run_id,
        parent_problem_sha256=_loop_sha(parent_problem),
        knowledge_artifact_sha256=_loop_sha(
            _knowledge_canonical(knowledge_artifact))
        if isinstance(knowledge_artifact, dict) else "NOT_SUPPLIED")
    child_run_id = "engrun:%s:%s" % (
        child_problem.get("problem_id"),
        event["event_id"][-8:])
    req = {"trigger_event_id": event["event_id"], "branch": branch,
           "knowledge_record_id": knowledge_id,
           "parent_run_id": parent_run_id,
           "parent_problem_sha256": _loop_sha(parent_problem),
           "child_problem": child_problem,
           "child_problem_sha256": _loop_sha(child_problem),
            "child_run_id": child_run_id,
            "launch_id": _launch_id_for(event["event_id"], child_run_id,
                                        knowledge_id),
            "knowledge_artifact_sha256": _loop_sha(
                _knowledge_canonical(knowledge_artifact))
            if isinstance(knowledge_artifact, dict) else "NOT_SUPPLIED",
            "launch_attempts": 0,
           "reconciliation_history": [],
           "launchable": not rehearsal, "status": "REQUESTED",
           "rehearsal": rehearsal,
           "requested_at": _loop_now()}
    if not rehearsal:
        _atomic_write_json(req_path, req)
    return req


def _search_impact_record(event, branch_out, child_req,
                          parent_problem, parent_run_dir,
                          cemetery_before, cemetery_after,
                          registry_before, registry_after,
                          consumption) -> Dict:
    """Canonical SEARCH-IMPACT (§G/§9): BEFORE/AFTER derived from actual
    canonical records (hashes/references, never narrative). Unknowns
    stay typed (Art. XXV)."""
    before = _loop_sha(parent_problem) if isinstance(
        parent_problem, dict) else "NO_PARENT_SUPPLIED"
    after = child_req.get("child_problem_sha256", "NO_CHILD_PROBLEM")
    knowledge_id = child_req.get("knowledge_record_id")
    regions = _parent_operator_regions(parent_run_dir)
    return {"artifact_type": "SEARCH_IMPACT/1.0.0",
            "parent_run_id": child_req.get("parent_run_id"),
            "trigger_event_id": event["event_id"],
            "knowledge_delta_id": knowledge_id,
            "knowledge_record_id": knowledge_id,
            "search_state_before": {
                "parent_problem_sha256": before,
                "parent_constraint": (parent_problem or {}).get(
                    "constraint")},
            "knowledge_added": {"branch": branch_out.get("path"),
                                "record_id": knowledge_id},
            "search_state_after": {
                "child_problem_sha256": after,
                "child_constraint": (child_req.get("child_problem")
                                     or {}).get("constraint")},
            "operator_region_before": regions.get("operator_ids",
                                                  regions.get("state")),
            "operator_region_after": "PENDING_CHILD_EXECUTION",
            "cemetery_constraints_before": cemetery_before,
            "cemetery_constraints_after": cemetery_after,
            "query_policy_before": "UNKNOWN_NO_QUERY_REGISTRY",
            "query_policy_after": "UNKNOWN_NO_QUERY_REGISTRY",
            "behavioral_change_expected": _expected_change(
                branch_out.get("path")),
            "behavioral_change_observed": (
                "PENDING_CHILD_LAUNCH" if child_req.get("launchable")
                else "NO_CHILD_EXPECTED"),
            "child_run_id": child_req.get("child_run_id"),
            "child_consumed_delta": consumption,
            "measurement_basis": "sha256 over canonical record bytes "
                                 "before/after; consumption read from "
                                 "the child request + launch receipt",
            "recorded_at": _loop_now()}


def _expected_change(branch_path: str) -> str:
    return {"KILL": "previous mechanism family suppressed / failure "
                    "territory excluded via the appended reality clause; "
                    "cemetery gate consults the new entry on every "
                    "candidate",
            "MODIFY": "new boundary/hypothesis admitted via the appended "
                      "reality clause; hypothesis record bound to the "
                      "child",
            "KEEP": "none-expected (success path performs mutations, "
                    "no search modification)"}.get(
                        branch_path, "unknown branch")


def _mark_phase(ledger_dir: str, event_id: str, phase: str) -> None:
    """Persist a restart-recovery phase marker (§12 boundaries A-D).
    Markers are informational waypoints; the idempotency guards do the
    real resume work. The marker write is serialized like any ledger
    write (concurrent markers collide on Windows otherwise) and is
    best-effort: a marker that cannot be written must never fail the
    execution it describes (markers serve execution, not vice versa)."""
    path = os.path.join(ledger_dir, "executions", event_id + ".phase")
    try:
        with _LedgerLocked(path):
            _atomic_write_json(path, {"event_id": event_id,
                                      "phase": phase, "at": _loop_now()})
    except Exception:
        pass


def _claim_child(ledger_dir: str, event_id: str):
    """Atomically claim the child-launch right (§10): under the request
    file's lock, transition REQUESTED -> CLAIMED with a unique claim
    token. Returns (True, req) on claim, else (False, reason). The lock
    is released before any launch (never held across EngineRun
    execution or remote calls). CLAIMED means exactly one thing: a
    unique worker owns the launch right. It does NOT mean safe to
    reclaim — reclamation goes through reconcile_unknown_launch only.
    Integrity is verified before claiming (attack G)."""
    req_path = os.path.join(ledger_dir, "child_requests",
                            event_id + ".json")
    with _LedgerLocked(req_path):
        try:
            req = json.load(open(req_path, encoding="utf-8"))
        except Exception:
            return False, "unreadable request (typed; left untouched)"
        if req.get("rehearsal"):
            return False, "rehearsal requests never launch"
        if req.get("status") != "REQUESTED" or not req.get("launchable"):
            return False, "status=%s (only REQUESTED launchable claims)" \
                % (req.get("status"),)
        ok, why = _verify_request(req)
        if not ok:
            req["status"] = "UNKNOWN_TAMPERED"
            req.setdefault("reconciliation_history", []).append(
                {"at": _loop_now(), "action": "claim-refused",
                 "reason": why})
            _atomic_write_json(req_path, req)
            return False, why
        attempt = len(req.get("reconciliation_history", [])) + 1
        req["status"] = "CLAIMED"
        req["claim"] = {"token": "claim-%s-%d" % (
            req.get("launch_id", "noid"), attempt),
            "claimed_at": _loop_now(),
            "note": "launch right claimed; lock released before "
                    "worker execution (§10)"}
        req.setdefault("reconciliation_history", []).append(
            {"at": _loop_now(), "action": "claimed",
             "token": req["claim"]["token"]})
        _atomic_write_json(req_path, req)
        _refresh_impact(ledger_dir, event_id)
        return True, req


def reconcile_unknown_launch(ledger_dir: str, event_id: str,
                             run_launcher, execution_checker=None):
    """Reconcile an ambiguous launch outcome (§5/§6/§10). Valid from
    UNKNOWN_LAUNCH or receipt-less CLAIMED states only. Steps: verify
    integrity (tamper -> UNKNOWN_TAMPERED, never launch); ask the
    checker for the launch_id's execution effect; found -> adopt it
    (LAUNCHED + reconciliation record, zero new executions);
    absent + checker present -> relaunch the SAME launch_id (the
    idempotent launcher converges); absent + no checker -> stay
    UNKNOWN_LAUNCH (refusing blind relaunch is the safe action).
    Every path appends a reconciliation record (§10)."""
    req_path = os.path.join(ledger_dir, "child_requests",
                            event_id + ".json")
    with _LedgerLocked(req_path):
        try:
            req = json.load(open(req_path, encoding="utf-8"))
        except Exception:
            return {"reconciled": False, "state": "UNKNOWN_UNREADABLE",
                    "reason": "request unreadable; left untouched"}
        if req.get("status") == "LAUNCHED":
            return {"reconciled": True, "state": "LAUNCHED",
                    "note": "already launched; duplicate reconcile is "
                            "a no-op"}
        if _execution_is_corrupt(ledger_dir, event_id):
            return {"reconciled": False, "state": "UNKNOWN",
                    "reason": "execution record corrupt; never treated "
                              "as absence (§7)"}
        _lpath, _entry, _refusal = _resume_ledger_gate(
            ledger_dir, event_id)
        if _refusal is not None:
            return {"reconciled": False, "state": "UNKNOWN",
                    "reason": "ledger gate refused: %s" %
                              (_refusal.get("gate"),),
                    "resume_gate": _refusal}
        if req.get("status") not in ("UNKNOWN_LAUNCH", "CLAIMED",
                                      "LAUNCHING", "LAUNCH_FAILED"):
            return {"reconciled": False, "state": req.get("status"),
                    "reason": "only UNKNOWN_LAUNCH/CLAIMED/LAUNCHING/"
                              "LAUNCH_FAILED reconcile (retry of a proven "
                              "rejection reuses the same launch id)"}
        ok, why = _verify_request(req)
        if not ok:
            req["status"] = "UNKNOWN_TAMPERED"
            req.setdefault("reconciliation_history", []).append(
                {"at": _loop_now(), "action": "reconcile-refused",
                 "reason": why})
            _atomic_write_json(req_path, req)
            return {"reconciled": False, "state": "UNKNOWN_TAMPERED",
                    "reason": why}
        lid = req.get("launch_id")
        found = None
        if execution_checker is not None:
            try:
                found = execution_checker(
                    lid, {"child_run_id": req.get("child_run_id"),
                          "ledger_dir": ledger_dir})
            except Exception as exc:
                req.setdefault("reconciliation_history", []).append(
                    {"at": _loop_now(), "action": "checker-failed",
                     "reason": "%s: %s" % (
                         type(exc).__name__, str(exc)[:200])})
                _atomic_write_json(req_path, req)
                return {"reconciled": False, "state": "UNKNOWN_LAUNCH",
                        "reason": "checker failed; staying ambiguous "
                                  "(never guess)"}
        if found:
            req["status"] = "LAUNCHED"
            req["launch_receipt"] = {
                "reconciled": True,
                "child_execution": found,
                "reconciled_at": _loop_now(),
                "note": "effect already existed under this launch id; "
                        "adopted, zero new executions (§9)"}
            req.setdefault("reconciliation_history", []).append(
                {"at": _loop_now(), "action": "adopted-existing",
                 "launch_id": lid,
                 "child_execution": found.get("child_run_id",
                                              found if isinstance(
                                                  found, str) else None)})
            _atomic_write_json(req_path, req)
            _refresh_impact(ledger_dir, event_id)
            return {"reconciled": True, "state": "LAUNCHED",
                    "child_run_id": req.get("child_run_id")}
        if execution_checker is None:
            req.setdefault("reconciliation_history", []).append(
                {"at": _loop_now(), "action": "reconcile-deferred",
                 "reason": "no execution checker supplied; refusing "
                           "blind relaunch (stays UNKNOWN_LAUNCH)"})
            _atomic_write_json(req_path, req)
            return {"reconciled": False, "state": "UNKNOWN_LAUNCH",
                    "reason": "no checker; blind relaunch refused"}
        req["launch_attempts"] = int(req.get("launch_attempts", 0)) + 1
        req.setdefault("reconciliation_history", []).append(
            {"at": _loop_now(), "action": "relaunch-same-id",
             "launch_id": lid,
             "recovered_from": req.get("status"),
             "attempt": req["launch_attempts"]})
        _atomic_write_json(req_path, req)
        _refresh_impact(ledger_dir, event_id)
    try:
        receipt = run_launcher(req)
    except LauncherRejected as exc:
        with _LedgerLocked(req_path):
            try:
                cur = json.load(open(req_path, encoding="utf-8"))
            except Exception:
                return {"reconciled": False, "state": "UNKNOWN_UNREADABLE",
                        "reason": "request unreadable post-rejection"}
            cur["status"] = "LAUNCH_FAILED"
            cur["launch_error"] = "LauncherRejected: %s" % (str(exc)[:200],)
            cur.setdefault("reconciliation_history", []).append(
                {"at": _loop_now(), "action": "relaunch-rejected",
                 "reason": cur["launch_error"]})
            _atomic_write_json(req_path, cur)
        _refresh_impact(ledger_dir, event_id)
        return {"reconciled": False, "state": "LAUNCH_FAILED",
                "reason": cur["launch_error"]}
    except Exception as exc:
        with _LedgerLocked(req_path):
            try:
                cur = json.load(open(req_path, encoding="utf-8"))
            except Exception:
                return {"reconciled": False, "state": "UNKNOWN_UNREADABLE",
                        "reason": "request unreadable post-ambiguity"}
            cur.setdefault("reconciliation_history", []).append(
                {"at": _loop_now(), "action": "relaunch-ambiguous",
                 "error": "%s: %s" % (
                     type(exc).__name__, str(exc)[:200])})
            _atomic_write_json(req_path, cur)
        _refresh_impact(ledger_dir, event_id)
        return {"reconciled": False, "state": "UNKNOWN_LAUNCH",
                "reason": "relaunch outcome ambiguous; stays unknown"}
    with _LedgerLocked(req_path):
        try:
            cur = json.load(open(req_path, encoding="utf-8"))
        except Exception:
            return {"reconciled": False, "state": "UNKNOWN_UNREADABLE",
                    "reason": "request unreadable post-launch"}
        cur["status"] = "LAUNCHED"
        cur["launch_receipt"] = receipt
        cur.setdefault("reconciliation_history", []).append(
            {"at": _loop_now(), "action": "relaunched-ok",
             "launch_id": lid})
        _atomic_write_json(req_path, cur)
    _refresh_impact(ledger_dir, event_id)
    return {"reconciled": True, "state": "LAUNCHED",
            "child_run_id": cur.get("child_run_id")}


def _note_launch_attempt(ledger_dir: str, event_id: str) -> int:
    """Increment the persisted launch-attempt counter. Attempt counting
    is part of the §10 reconciliation record (how many times the
    launcher was invoked for this launch id)."""
    req_path = os.path.join(ledger_dir, "child_requests",
                            event_id + ".json")
    with _LedgerLocked(req_path):
        try:
            req = json.load(open(req_path, encoding="utf-8"))
        except Exception:
            return 0
        req["launch_attempts"] = int(req.get("launch_attempts", 0)) + 1
        _atomic_write_json(req_path, req)
        return req["launch_attempts"]


def _mark_launching(ledger_dir: str, event_id: str) -> None:
    """Persist LAUNCHING immediately before invoking the launcher.
    CLAIMED means the launch right is owned but the launcher was never
    invoked (safe to invoke once); LAUNCHING means invocation started
    with unknown outcome (reconcile only, never blind-invoke). The
    distinction is the entire crash-boundary semantics (§3)."""
    req_path = os.path.join(ledger_dir, "child_requests",
                            event_id + ".json")
    with _LedgerLocked(req_path):
        try:
            req = json.load(open(req_path, encoding="utf-8"))
        except Exception:
            return
        if req.get("status") != "CLAIMED":
            return
        req["status"] = "LAUNCHING"
        req.setdefault("reconciliation_history", []).append(
            {"at": _loop_now(), "action": "launch-invoked"})
        _atomic_write_json(req_path, req)


def _refresh_impact(ledger_dir: str, event_id: str) -> bool:
    """Rewrite the persisted SEARCH-IMPACT artifact from current
    durable request state (§9: no stale PENDING after a receipt
    exists). Locks the impact path only (distinct from the request
    path, so callers holding the request lock cannot deadlock; lock
    ordering is always request-then-impact). Returns False when
    there is no impact file yet (nothing stale to fix)."""
    imp_path = os.path.join(ledger_dir, "search_impact",
                            event_id + ".json")
    if not os.path.exists(imp_path):
        return False
    with _LedgerLocked(imp_path):
        try:
            impact = json.load(open(imp_path, encoding="utf-8"))
        except Exception:
            return False
        req_path = os.path.join(ledger_dir, "child_requests",
                                event_id + ".json")
        try:
            req = json.load(open(req_path, encoding="utf-8")) \
                if os.path.exists(req_path) else {}
        except Exception:
            req = {}
        status = req.get("status")
        impact["child_run_id"] = req.get("child_run_id")
        impact["request_status"] = status
        impact["launch_receipt"] = req.get("launch_receipt")
        impact["launch_attempts"] = req.get("launch_attempts", 0)
        impact["reconciliation_history"] = req.get(
            "reconciliation_history", [])
        _cons = ((req.get("launch_receipt") or {}).get("consumption")
                 or {})
        _crec = (_cons.get("receipt")
                 if isinstance(_cons, dict) else None) or {}
        _ver = (req.get("launch_receipt") or {}).get(
            "artifact_verification",
            _cons.get("artifact_verification",
                      _crec.get("artifact_verification")))
        if isinstance(_ver, dict):
            _ver = _ver.get("artifact_verification")
        if status == "LAUNCHED" and _cons.get("consumed") is True:
            impact["behavioral_change_observed"] = \
                "CHILD_CONSUMED_VERIFIED" if _ver in (
                    "RESOLVED", "CARRIED_NOT_REVERIFIED") else \
                "CHILD_CONSUMED_UNVERIFIED"
            impact["child_consumed_delta"] = {
                "knowledge_record_id":
                    _crec.get("knowledge_record_id"),
                "artifact_verification": _ver,
                "operator_region_evidence":
                    _crec.get("operator_region_evidence"),
                "constraint_clause_present":
                    _crec.get("constraint_clause_present"),
                "child_problem_sha256":
                    _crec.get("child_problem_sha256")}
        elif status == "LAUNCHED":
            impact["behavioral_change_observed"] = \
                "CHILD_LAUNCHED_AWAITING_EXECUTION_EVIDENCE"
        elif status == "LAUNCH_FAILED":
            impact["behavioral_change_observed"] = \
                "NO_CHILD_LAUNCHED_FAILED"
        elif status in ("UNKNOWN_LAUNCH", "UNKNOWN_TAMPERED"):
            impact["behavioral_change_observed"] = \
                "UNKNOWN_LAUNCH_OUTCOME"
        _cons2 = ((req.get("launch_receipt") or {}).get("consumption")
                 or {})
        _crec2 = (_cons2.get("receipt")
                 if isinstance(_cons2, dict) else None) or {}
        if _crec2.get("operator_region_evidence"):
            impact["operator_region_after"] = \
                _crec2["operator_region_evidence"]
        impact["impact_refreshed_at"] = _loop_now()
        _atomic_write_json(imp_path, impact)
        return True


def _mark_launched(ledger_dir: str, event_id: str, receipt) -> None:
    req_path = os.path.join(ledger_dir, "child_requests",
                            event_id + ".json")
    with _LedgerLocked(req_path):
        try:
            req = json.load(open(req_path, encoding="utf-8"))
        except Exception:
            return
        req["status"] = "LAUNCHED"
        req["launch_receipt"] = receipt
        req.setdefault("reconciliation_history", []).append(
            {"at": _loop_now(), "action": "launched"})
        _atomic_write_json(req_path, req)
    _refresh_impact(ledger_dir, event_id)


def _mark_launch_unknown(ledger_dir: str, event_id: str,
                         error: str) -> None:
    """Ambiguous launch outcome (timeout, disconnect, unknown remote
    result): UNKNOWN_LAUNCH, never FAILED. Reconciliation (not blind
    relaunch) decides next."""
    req_path = os.path.join(ledger_dir, "child_requests",
                            event_id + ".json")
    with _LedgerLocked(req_path):
        try:
            req = json.load(open(req_path, encoding="utf-8"))
        except Exception:
            return
        req["status"] = "UNKNOWN_LAUNCH"
        req["launch_error"] = error
        req.setdefault("reconciliation_history", []).append(
            {"at": _loop_now(), "action": "launch-ambiguous",
             "error": error})
        _atomic_write_json(req_path, req)
    _refresh_impact(ledger_dir, event_id)


def _mark_launch_failed(ledger_dir: str, event_id: str,
                        error: str) -> None:
    req_path = os.path.join(ledger_dir, "child_requests",
                            event_id + ".json")
    with _LedgerLocked(req_path):
        try:
            req = json.load(open(req_path, encoding="utf-8"))
        except Exception:
            return
        req["status"] = "LAUNCH_FAILED"
        req["launch_error"] = error
        req.setdefault("reconciliation_history", []).append(
            {"at": _loop_now(), "action": "launch-failed-typed",
             "error": error})
        _atomic_write_json(req_path, req)
    _refresh_impact(ledger_dir, event_id)


def _reality_state_path(ledger_dir: str) -> str:
    return os.path.join(ledger_dir, "REALITY_STATE.json")


def _read_reality_state(ledger_dir: str) -> Dict:
    """Canonical reality-derived state (versioned registry). DERIVED
    state: rebuildable byte-identically from the ledger +
    executions/ via rebuild_reality_state() (Art. X: the ledger is
    the authority; this registry is its materialized view)."""
    p = _reality_state_path(ledger_dir)
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            pass
    return {"artifact_type": "REALITY_STATE/1.0.0", "packages": {}}


class _RealityStateCorrupt(Exception):
    """The canonical reality-state registry exists but is unparseable.
    Never reset silently (that would lose package reality status);
    never proceed (that would fork canonical state). Typed refusal."""


def _apply_event_to_state(ledger_dir: str, event, branch: str,
                          out: Dict) -> tuple:
    """Apply one executed event to the canonical registry. Returns
    (before_hash, after_hash) over the registry bytes — the
    canonical_state_before/after pair (§5). Commercial maturity is
    NEVER advanced here (no buyer/commercial gates move on reality
    reception alone, §6); package reality status is recorded."""
    with _LedgerLocked(_reality_state_path(ledger_dir)):
        _reg_path = _reality_state_path(ledger_dir)
        if os.path.exists(_reg_path):
            try:
                json.load(open(_reg_path, encoding="utf-8"))
            except Exception as exc:
                raise _RealityStateCorrupt(
                    "REALITY_STATE.json CORRUPT_UNREADABLE: %s "
                    "(refusing to overwrite canonical state)"
                    % (type(exc).__name__,))
        state = _read_reality_state(ledger_dir)
        before = _loop_sha(state)
        pkg = state["packages"].setdefault(event["package_id"], {})
        pkg["status"] = "OBSERVED_%s" % (branch,)
        pkg["last_event_id"] = event["event_id"]
        pkg["last_branch"] = branch
        pkg.setdefault("mutation_ids", [])
        pkg.setdefault("knowledge_ids", [])
        if branch == "KEEP":
            for layer, rec in (out.get("layers") or {}).items():
                if isinstance(rec, dict) and rec.get("mutation_id"):
                    pkg["mutation_ids"].append(rec["mutation_id"])
        kid = None
        if branch == "KILL":
            kid = (out.get("search_constraint") or {}).get(
                "excluded_cemetery_entry")
        elif branch == "MODIFY":
            kid = (out.get("hypothesis") or {}).get("hypothesis_id")
        if kid:
            pkg["knowledge_ids"].append(kid)
        # Canonical order (Art. X): these lists cross a sort_keys
        # JSON round-trip between live construction and rebuild-from-
        # ledger. Unsorted insertion order would make identical sets
        # hash differently — a canonicalization defect, not a data
        # difference. Sorted here, sorted in rebuild.
        pkg["mutation_ids"] = sorted(pkg["mutation_ids"])
        pkg["knowledge_ids"] = sorted(pkg["knowledge_ids"])
        state["updated_at"] = _loop_now()
        _atomic_write_json(_reality_state_path(ledger_dir), state)
        return before, _loop_sha(state)


def rebuild_reality_state(ledger_dir: str) -> Dict:
    """Re-derive the registry from durable records (proves derived
    status): replay REAL ledger entries in order through the same
    transition used live. Returns {match, rebuilt_hash, live_hash}.
    Comparison projects out updated_at (a volatile timestamp, never
    state) on both sides."""
    live = _read_reality_state(ledger_dir)
    live_hash = _loop_sha(
        {"artifact_type": live.get("artifact_type"),
         "packages": live.get("packages", {})})
    led_path = os.path.join(ledger_dir, "REALITY_EVENT_LEDGER.json")
    entries = []
    if os.path.exists(led_path):
        try:
            entries = json.load(
                open(led_path, encoding="utf-8")).get("entries", [])
        except Exception:
            entries = []
    state: Dict = {"artifact_type": "REALITY_STATE/1.0.0",
                   "packages": {}}
    for e in entries:
        rec = _load_execution(ledger_dir, e.get("event_id", ""))
        if rec is None or not rec.get("executed"):
            continue
        branch = rec.get("branch")
        out = rec.get("branch_record") or {}
        pkg = state["packages"].setdefault(
            e.get("package_id", ""), {})
        pkg["status"] = "OBSERVED_%s" % (branch,)
        pkg["last_event_id"] = e.get("event_id")
        pkg["last_branch"] = branch
        pkg.setdefault("mutation_ids", [])
        pkg.setdefault("knowledge_ids", [])
        if branch == "KEEP":
            for _layer, _rec in (out.get("layers") or {}).items():
                if isinstance(_rec, dict) and _rec.get("mutation_id"):
                    pkg["mutation_ids"].append(_rec["mutation_id"])
        _kid = None
        if branch == "KILL":
            _kid = (out.get("search_constraint") or {}).get(
                "excluded_cemetery_entry")
        elif branch == "MODIFY":
            _kid = (out.get("hypothesis") or {}).get("hypothesis_id")
        if _kid:
            pkg["knowledge_ids"].append(_kid)
        pkg["mutation_ids"] = sorted(pkg["mutation_ids"])
        pkg["knowledge_ids"] = sorted(pkg["knowledge_ids"])
    rebuilt_hash = _loop_sha(
        {"artifact_type": state["artifact_type"],
         "packages": state["packages"]})
    live_core = _loop_sha(
        {"artifact_type": live.get("artifact_type"),
         "packages": live.get("packages", {})})
    out = {"match": rebuilt_hash == live_core,
           "rebuilt_hash": rebuilt_hash, "live_hash": live_core}
    if not out["match"]:
        # Diagnosability (Art. XV): a mismatch without both sides is
        # undebuggable. Both package maps ride the record (hashes
        # already leak nothing beyond equality).
        out["rebuilt_packages"] = state["packages"]
        out["live_packages"] = live.get("packages", {})
    return out


def _cemetery_head(cemetery_path) -> Dict:
    """Count + head hash of a cemetery file (UNKNOWN-typed when
    unreadable; never guessed)."""
    if cemetery_path is None or not os.path.exists(str(cemetery_path)):
        return {"state": "UNKNOWN_NO_CEMETERY_PATH"}
    try:
        data = json.load(open(str(cemetery_path), encoding="utf-8"))
        entries = data.get("entries", [])
        return {"state": "READ", "entry_count": len(entries),
                "head_sha256": _loop_sha(entries[-1]) if entries else
                "EMPTY"}
    except Exception as exc:
        return {"state": "UNKNOWN_UNREADABLE",
                "error": type(exc).__name__}


def _parent_operator_regions(parent_run_dir) -> Dict:
    """Operator regions of the parent run's mechanism space, if a
    parent run dir is supplied (else typed UNKNOWN)."""
    if not parent_run_dir:
        return {"state": "UNKNOWN_NO_PARENT_RUN_DIR"}
    ms_path = os.path.join(str(parent_run_dir), "envelope_MECHANISM_SPACE.json")
    if not os.path.exists(ms_path):
        alt = os.path.join(str(parent_run_dir), "mechanism_space.json")
        ms_path = alt if os.path.exists(alt) else ms_path
    try:
        d = json.load(open(ms_path, encoding="utf-8"))
        space = d.get("mechanism_space", d)
        ops = space.get("operator_results") or []
        return {"state": "READ",
                "operator_ids": space.get("operator_ids"),
                "operators_examined": [
                    {"operator": o.get("operator"),
                     "state": o.get("state")} for o in ops]}
    except Exception as exc:
        return {"state": "UNKNOWN_UNREADABLE",
                "error": type(exc).__name__}


def _finalize_execution(event, ledger_dir, branch, branch_out,
                        run_launcher, parent_problem, rehearsal,
                        parent_run_dir=None, cemetery_path=None,
                        registry_hashes=None, cemetery_bounds=None):
    """SEARCH-IMPACT + child request + claim-launch-or-defer, shared by
    all branches (KEEP requests no child: success path mutates state).

    Launch discipline (§10): the launch right is CLAIMED atomically
    first; the lock is released before any worker execution; the
    launcher runs outside every lock."""
    if branch == "KEEP":
        impact = {"artifact_type": "SEARCH_IMPACT/1.0.0",
                  "parent_run_id": None,
                  "trigger_event_id": event["event_id"],
                  "knowledge_delta_id": None,
                  "knowledge_record_id": None,
                  "search_state_before": "NOT_APPLICABLE_KEEP_PATH",
                  "knowledge_added": {"branch": "KEEP"},
                  "search_state_after": "NOT_APPLICABLE_KEEP_PATH",
                  "operator_region_before": "NOT_APPLICABLE_KEEP_PATH",
                  "operator_region_after": "NOT_APPLICABLE_KEEP_PATH",
                  "cemetery_constraints_before":
                      (cemetery_bounds or {}).get("before",
                                                 "UNKNOWN_UNREAD"),
                  "cemetery_constraints_after":
                      (cemetery_bounds or {}).get("after",
                                                 "UNKNOWN_UNREAD"),
                  "query_policy_before": "UNKNOWN_NO_QUERY_REGISTRY",
                  "query_policy_after": "UNKNOWN_NO_QUERY_REGISTRY",
                  "behavioral_change_expected":
                      _expected_change("KEEP"),
                  "behavioral_change_observed": "NO_CHILD_EXPECTED",
                  "child_run_id": None,
                  "child_consumed_delta": None,
                  "measurement_basis": "mutation sidecars hash-chained "
                                       "to parent refs",
                  "recorded_at": _loop_now()}
        if not rehearsal:
            _atomic_write_json(os.path.join(
                ledger_dir, "search_impact",
                event["event_id"] + ".json"), impact)
            _mark_phase(ledger_dir, event["event_id"], "IMPACT_PERSISTED")
        return {"search_impact": impact, "child": None}
    child_req = branch_out.get("child_request") or {}
    consumption = {"reality_state_hash_read":
                   (registry_hashes or {}).get("after"),
                   "knowledge_record_id":
                   child_req.get("knowledge_record_id")}
    impact = _search_impact_record(
        event, branch_out, child_req, parent_problem, parent_run_dir,
        (cemetery_bounds or {}).get("before", "UNKNOWN_UNREAD"),
        (cemetery_bounds or {}).get("after", "UNKNOWN_UNREAD"),
        (registry_hashes or {}).get("before"),
        (registry_hashes or {}).get("after"), consumption)
    if not rehearsal:
        _atomic_write_json(os.path.join(
            ledger_dir, "search_impact", event["event_id"] + ".json"),
            impact)
        _mark_phase(ledger_dir, event["event_id"], "IMPACT_PERSISTED")
    child_out, receipt = None, None
    if child_req.get("launchable") and run_launcher is not None:
        claimed, req_or_reason = _claim_child(ledger_dir,
                                              event["event_id"])
        if claimed:
            _mark_phase(ledger_dir, event["event_id"], "CHILD_CLAIMED")
            _note_launch_attempt(ledger_dir, event["event_id"])
            try:
                receipt = run_launcher(req_or_reason)
                consumption["launch_receipt"] = receipt
                consumption["reality_state_hash_read"] = (
                    registry_hashes or {}).get("after")
                _mark_launched(ledger_dir, event["event_id"], receipt)
                _mark_phase(ledger_dir, event["event_id"],
                            "CHILD_LAUNCHED")
                child_out = req_or_reason.get("child_run_id")
            except LauncherRejected as exc:
                _mark_launch_failed(
                    ledger_dir, event["event_id"],
                    "LauncherRejected: %s" % (str(exc)[:200],))
                _mark_phase(ledger_dir, event["event_id"],
                            "CHILD_LAUNCH_FAILED")
            except Exception as exc:  # ambiguous outcome (§6)
                _mark_launch_unknown(
                    ledger_dir, event["event_id"], "%s: %s" % (
                        type(exc).__name__, str(exc)[:200]))
                _mark_phase(ledger_dir, event["event_id"],
                            "CHILD_LAUNCH_UNKNOWN")
    status_now = _load_execution_child_status(ledger_dir,
                                              event["event_id"])
    return {"search_impact": impact,
            "child": {"child_run_id": child_out,
                      "launch_receipt": receipt,
                      "consumption": consumption,
                      "request_status": status_now}}


def _load_execution_child_status(ledger_dir, event_id):
    req_path = os.path.join(ledger_dir, "child_requests",
                            event_id + ".json")
    if not os.path.exists(req_path):
        return "NO_REQUEST"
    try:
        return json.load(
            open(req_path, encoding="utf-8")).get("status")
    except Exception:
        return "UNKNOWN_UNREADABLE"


def resume_pending_children(ledger_dir: str, run_launcher,
                            execution_checker=None) -> Dict:
    """Restart recovery (Art. LXXIV) with unknown-outcome discipline
    (§5/§6): REQUESTED requests go through claim+launch (LauncherRejected
    -> LAUNCH_FAILED and retryable; any other launcher outcome ->
    UNKNOWN_LAUNCH, never FAILED). CLAIMED-without-receipt is promoted
    to UNKNOWN_LAUNCH (an absent receipt after a claim interval is
    AMBIGUOUS, never safe to reclaim blindly) and reconciled.
    UNKNOWN_LAUNCH reconciles via the execution checker (adopt existing
    or relaunch the SAME launch id). LAUNCH_FAILED may retry (same id).
    LAUNCHED skips. UNKNOWN_TAMPERED never launches (fail-closed)."""
    import glob as _glob
    launched, skipped, failed = [], [], []
    for req_path in sorted(_glob.glob(os.path.join(
            ledger_dir, "child_requests", "*.json"))):
        try:
            req = json.load(open(req_path, encoding="utf-8"))
        except Exception:
            failed.append({"file": req_path,
                           "error": "unreadable request (typed; left "
                                    "untouched)"})
            continue
        trig = req.get("trigger_event_id")
        if req.get("rehearsal"):
            skipped.append({"trigger": trig,
                            "reason": "rehearsal requests never launch "
                                      "in the production path"})
            continue
        if not req.get("launchable"):
            skipped.append({"trigger": trig, "reason": "not launchable"})
            continue
        status = req.get("status")
        if status == "LAUNCHED":
            skipped.append({"trigger": trig,
                            "reason": "already LAUNCHED"})
            continue
        if status == "UNKNOWN_TAMPERED":
            skipped.append({"trigger": trig,
                            "reason": "integrity failure; fail-closed, "
                                      "never launch"})
            continue
        if status == "REQUESTED":
            _gl, _ge, _gr = _resume_ledger_gate(ledger_dir, trig or "")
            if _gr is not None:
                skipped.append({"trigger": trig,
                                "reason": "ledger gate refused: %s "
                                          "(fail-closed; no claim, no "
                                          "launch)" % (_gr.get("gate"),)})
                continue
            claimed, req_or_reason = _claim_child(ledger_dir, trig or "")
            if not claimed:
                skipped.append({"trigger": trig,
                                "reason": req_or_reason})
                continue
            _note_launch_attempt(ledger_dir, trig or "")
            _mark_phase(ledger_dir, trig or "", "CHILD_CLAIMED")
            try:
                receipt = run_launcher(req_or_reason)
                _mark_launched(ledger_dir, trig or "", receipt)
                _mark_phase(ledger_dir, trig or "", "CHILD_LAUNCHED")
                launched.append({"trigger": trig,
                                 "child_run_id": req_or_reason.get(
                                     "child_run_id")})
            except LauncherRejected as exc:
                _mark_launch_failed(
                    ledger_dir, trig or "",
                    "LauncherRejected: %s" % (str(exc)[:200],))
                _mark_phase(ledger_dir, trig or "", "CHILD_LAUNCH_FAILED")
                failed.append({"trigger": trig,
                               "error": "LauncherRejected"})
            except Exception as exc:
                _mark_launch_unknown(
                    ledger_dir, trig or "", "%s: %s" % (
                        type(exc).__name__, str(exc)[:200]))
                _mark_phase(ledger_dir, trig or "",
                            "CHILD_LAUNCH_UNKNOWN")
                failed.append({"trigger": trig,
                               "error": "ambiguous launch outcome; "
                                        "recorded UNKNOWN_LAUNCH"})
            continue
        if status in ("CLAIMED", "UNKNOWN_LAUNCH", "LAUNCHING",
                        "LAUNCH_FAILED"):
            if status == "CLAIMED":
                _promote_claimed_unknown(ledger_dir, trig or "")
            out = reconcile_unknown_launch(
                ledger_dir, trig or "", run_launcher,
                execution_checker)
            if out.get("state") == "LAUNCHED" and \
                    out.get("child_run_id"):
                launched.append({"trigger": trig,
                                 "child_run_id": out.get("child_run_id"),
                                 "reconciled": True})
            elif out.get("state") == "LAUNCH_FAILED":
                failed.append({"trigger": trig,
                               "error": out.get("reason")})
            else:
                skipped.append({"trigger": trig,
                                "reason": out.get("state") + ": " +
                                str(out.get("reason"))})
            continue
        skipped.append({"trigger": trig,
                        "reason": "status=%s (not resumable)" % (status,)})
    return {"launched": launched, "skipped": skipped, "failed": failed}


def _promote_claimed_unknown(ledger_dir: str, event_id: str) -> None:
    """A receipt-less CLAIMED request is AMBIGUOUS (crashed worker or
    slow worker): promote to UNKNOWN_LAUNCH with the reason recorded.
    Never silently reclaim (§5)."""
    req_path = os.path.join(ledger_dir, "child_requests",
                            event_id + ".json")
    with _LedgerLocked(req_path):
        try:
            req = json.load(open(req_path, encoding="utf-8"))
        except Exception:
            return
        if req.get("status") != "CLAIMED":
            return
        req["status"] = "UNKNOWN_LAUNCH"
        req.setdefault("reconciliation_history", []).append(
            {"at": _loop_now(), "action": "promote-claimed-unknown",
             "recovered_from": "CLAIMED",
             "reason": "claim without launch receipt after a claim "
                       "interval: crashed worker and slow worker are "
                       "indistinguishable; reconcile, never blindly "
                       "reclaim"})
        _atomic_write_json(req_path, req)


def record_child_consumption(child_run_dir: str, parent_event_id: str,
                             parent_run_id, knowledge_record_id: str,
                             knowledge_artifact_sha256: str,
                             parent_problem_sha256: str,
                             knowledge_artifact=None) -> Dict:
    """Machine-readable consumption receipt (§10/§11), produced FROM
    the child execution path (EngineRun post-run; default_run_launcher;
    tests call it against crafted run dirs). Binds parent event/run,
    knowledge id + artifact hash, child run/problem hashes, operator-
    region evidence, and before/after problem hashes. Unknowns stay
    typed (a disabled/experimental stage list is not evidence).

    Verification ladder for the knowledge artifact itself:
      RESOLVED — artifact bytes supplied and hash matches;
      TAMPERED — bytes supplied but hash differs (consumed=False);
      CARRIED_NOT_REVERIFIED — no bytes supplied (binding only).
    Lineage refs inside the child problem must agree with the passed
    ids; disagreement is consumed=False (fail-closed, never a
    same-ID-different-artifact consumption)."""
    child_run_dir = str(child_run_dir)
    problem_path = os.path.join(child_run_dir, "problem.json")
    manifest_path = os.path.join(child_run_dir, "run_manifest.json")
    try:
        child_problem = json.load(open(problem_path, encoding="utf-8"))
    except Exception as exc:
        return {"consumed": False,
                "reason": "child problem.json unreadable: %s (typed; "
                          "no consumption claimed)" % (type(exc).__name__,)}
    try:
        manifest = json.load(open(manifest_path, encoding="utf-8"))
    except Exception:
        manifest = {"manifest_state": "UNKNOWN_NO_MANIFEST"}
    rec = child_problem.get("reality_constraints") or {}
    if rec.get("trigger_event_id") != parent_event_id or \
            rec.get("knowledge_record_id") != knowledge_record_id:
        return {"consumed": False,
                "reason": "child lineage refs disagree with the claimed "
                          "parent/knowledge ids (fail-closed; tampered or "
                          "foreign child)",
                "lineage_refs": {
                    "trigger_event_id": rec.get("trigger_event_id"),
                    "knowledge_record_id":
                        rec.get("knowledge_record_id")}}
    if isinstance(knowledge_artifact, dict):
        if _loop_sha(knowledge_artifact) == knowledge_artifact_sha256:
            verification = "RESOLVED"
        else:
            return {"consumed": False,
                    "reason": "knowledge artifact bytes do not match "
                              "the bound hash (TAMPERED; fail-closed)",
                    "artifact_verification": "TAMPERED"}
    else:
        verification = "CARRIED_NOT_REVERIFIED"
    ms_path = os.path.join(child_run_dir, "envelope_MECHANISM_SPACE.json")
    if os.path.exists(ms_path):
        try:
            _ms = json.load(open(ms_path, encoding="utf-8"))
            _space = _ms.get("mechanism_space", _ms)
            regions = {"state": "READ",
                       "operator_ids": _space.get("operator_ids")}
        except Exception as exc:
            regions = {"state": "UNKNOWN_UNREADABLE",
                       "error": type(exc).__name__}
    else:
        regions = {"state": "UNKNOWN_NO_MECHANISM_SPACE"}
    receipt = {
        "artifact_type": "CHILD_CONSUMPTION/1.0.0",
        "parent_event_id": parent_event_id,
        "parent_run_id": parent_run_id,
        "knowledge_record_id": knowledge_record_id,
        "knowledge_artifact_sha256": knowledge_artifact_sha256,
        "artifact_verification": verification,
        "child_run_id": manifest.get("run_id",
                                     child_problem.get("problem_id")),
        "child_input_manifest_hash": _loop_sha({
            "problem": child_problem,
            "manifest_run_id": manifest.get("run_id")}),
        "parent_problem_sha256": parent_problem_sha256,
        "child_problem_sha256": _loop_sha(child_problem),
        "constraint_clause_present": "[REALITY %s:" % (parent_event_id,)
        in str(child_problem.get("constraint") or ""),
        "lineage_refs": {
            "trigger_event_id": rec.get("trigger_event_id"),
            "knowledge_record_id": rec.get("knowledge_record_id")},
        "operator_region_evidence": regions,
        "consumed_at": _loop_now(),
    }
    _atomic_write_json(os.path.join(child_run_dir, "CONSUMPTION.json"),
                       receipt)
    return {"consumed": True, "receipt": receipt}


def canonical_search_snapshot(space: Dict, constraint_text: str,
                              manifest: Dict) -> Dict:
    """Deterministic search-state snapshot from an EXECUTED
    mechanism-space record. §8-clean by construction: no candidate
    text, no LLM wording, no timestamps, no run/problem ids, no
    serialized-order dependence (all lists sorted). Carries WHAT the
    search decided (operator selection, examined states, cemetery
    kill decisions with entry ids, candidate decision multiset,
    consumed-constraint hash, selection policy) — never the wording
    that produced it."""
    import hashlib as _hl
    space = space or {}
    op_results = space.get("operator_results") or []
    examined = sorted(
        [{"operator": o.get("operator"), "state": o.get("state")}
         for o in op_results if isinstance(o, dict)],
        key=lambda d: str(d.get("operator")))
    sel = (space.get("operator_results") or [{}])
    evaluated = 0
    satisfied = 0
    selected_operator = None
    for o in op_results:
        if not isinstance(o, dict):
            continue
        _osel = o.get("operator_selection") or {}
        if isinstance(_osel, dict):
            if selected_operator is None and _osel.get(
                    "selected_operator"):
                selected_operator = _osel.get("selected_operator")
            _ev = _osel.get("contracts_evaluated") or []
            evaluated += len(_ev)
            satisfied += sum(1 for e in _ev if isinstance(e, dict)
                             and e.get("satisfied"))
    if selected_operator is None:
        _oids = sorted(space.get("operator_ids") or [])
        selected_operator = _oids[0] if _oids else None
    ccons = space.get("cemetery_consumption") or {}
    _blocked_ids = set()
    for b in (ccons.get("blocked") or []):
        for e in (b.get("entries") or []):
            if e:
                _blocked_ids.add(str(e))
    _warned_ids = set()
    _full_results = space.get("operator_candidates_full") or []
    for _or in (_full_results if isinstance(_full_results, list)
                else []):
        if not isinstance(_or, dict):
            continue
        for _c in (_or.get("candidates") or []):
            if not isinstance(_c, dict):
                continue
            for _w in (_c.get("cemetery_warnings") or []):
                if isinstance(_w, dict) and _w.get("cemetery_entry"):
                    _warned_ids.add(str(_w.get("cemetery_entry")))
    cands = space.get("candidates") or []

    def _cand_block_ids(c):
        ids = []
        for b in (c.get("cemetery_block") or []):
            if isinstance(b, dict) and b.get("cemetery_entry"):
                ids.append(str(b.get("cemetery_entry")))
        return sorted(ids)

    decisions = sorted(
        [{"state": c.get("candidate_state"),
          "blocked": _cand_block_ids(c)}
         for c in cands if isinstance(c, dict)],
        key=lambda d: (str(d.get("state")), ",".join(d.get("blocked"))))
    evaluated = 0
    satisfied = 0
    _op_sel = space.get("operator_selection") or {}
    if isinstance(_op_sel, dict):
        _ev = _op_sel.get("contracts_evaluated") or []
        evaluated = len(_ev)
        satisfied = sum(1 for e in _ev if isinstance(e, dict)
                        and e.get("satisfied"))
    else:
        for o in op_results:
            if isinstance(o, dict) and isinstance(
                    o.get("operator_selection"), dict):
                _ev = o["operator_selection"].get(
                    "contracts_evaluated") or []
                evaluated += len(_ev)
                satisfied += sum(
                    1 for e in _ev if isinstance(e, dict)
                    and e.get("satisfied"))
    snapshot = {
        "stage": "MECHANISM_SPACE",
        "space_state": space.get("state"),
        "space_version": space.get("mechanism_space_version"),
        "operator_ids": sorted(space.get("operator_ids") or []),
        "selected_operator": selected_operator,
        "contracts_evaluated": evaluated,
        "contracts_satisfied": satisfied,
        "operators_examined": examined,
        "cemetery_consultation": {
            "state": ccons.get("state"),
            "n_consulted": ccons.get("n_candidates_consulted", 0),
            "n_blocked": ccons.get("n_blocked", 0),
            "n_warned": ccons.get("n_warned", 0),
            "blocked_entry_ids": sorted(_blocked_ids),
            "warned_entry_ids": sorted(_warned_ids),
        },
        "candidates": {
            "n_retained": len(cands),
            "decisions": decisions,
        },
        "consumed_constraint_sha256": _hl.sha256(
            str(constraint_text or "").encode("utf-8",
                                              "replace")).hexdigest(),
        "candidate_selection_policy": {
            "disabled_stages": sorted(
                (manifest or {}).get("disabled_stages", [])),
            "stage_order": (manifest or {}).get("stage_order"),
        },
    }
    snapshot["snapshot_hash"] = _loop_sha(snapshot)
    return snapshot


def record_search_consumption(child_run_dir: str, block: Dict,
                              space: Dict) -> Dict:
    """Durable SEARCH_CONSUMPTION record (§4), emitted from the
    MECHANISM_SPACE stage's OWN persisted envelope (never
    re-derived, never synthesized). Binds child_run_id, parent
    reality event, knowledge id + artifact hash, consumed-constraint
    hash, stage name, operator/configuration used, timestamp, and
    the canonical search-state hash. Returns the record (and writes
    SEARCH_CONSUMPTION.json). Callers gate on block presence,
    non-rehearsal, and an executed stage."""
    child_run_dir = str(child_run_dir)
    try:
        manifest = json.load(open(os.path.join(
            child_run_dir, "run_manifest.json"), encoding="utf-8"))
    except Exception:
        manifest = {}
    try:
        problem = json.load(open(os.path.join(
            child_run_dir, "problem.json"), encoding="utf-8"))
    except Exception:
        problem = {}
    constraint_text = str(problem.get("constraint") or "")
    snapshot = canonical_search_snapshot(space, constraint_text,
                                         manifest)
    record = {
        "artifact_type": "SEARCH_CONSUMPTION/1.0.0",
        "stage": "MECHANISM_SPACE",
        "child_run_id": manifest.get("run_id"),
        "trigger_event_id": block.get("trigger_event_id"),
        "parent_run_id": block.get("parent_run_id"),
        "knowledge_record_id": block.get("knowledge_record_id"),
        "knowledge_artifact_sha256": block.get(
            "knowledge_artifact_sha256"),
        "consumed_constraint_sha256": snapshot[
            "consumed_constraint_sha256"],
        "operator_configuration": {
            "operator_ids": snapshot["operator_ids"],
            "selected_operator": snapshot["selected_operator"],
            "space_version": snapshot["space_version"],
            "space_state": snapshot["space_state"],
        },
        "search_snapshot": snapshot,
        "search_state_hash": snapshot["snapshot_hash"],
        "executed_at": _loop_now(),
    }
    _atomic_write_json(os.path.join(child_run_dir,
                                    "SEARCH_CONSUMPTION.json"), record)
    return record


def verify_consumption(child_run_dir: str, expected: Dict,
                       knowledge_resolver=None) -> Dict:
    """Independent consumption verifier (§2-§4): reconstructs consumption
    from INDEPENDENT durable artifacts, never from CONSUMPTION.json
    (a self-authored receipt MUST NEVER upgrade an unverified run).
    Reads, in order: run_manifest.json (run executed? knowledge refs
    bound by the run itself?), problem.json (lineage block + clause +
    bytes), artifact resolution (resolver or manifest-carried hash —
    absent means UNRESOLVED, never synthesized). Returns
    {"verified": bool, "contract": {...}, "checks": {...}, "reason"}.
    Every check records its own evidence; the first failing check
    decides, but all checks still run (no short-circuit hiding)."""
    child_run_dir = str(child_run_dir)
    expected = expected or {}
    checks: Dict[str, Any] = {}
    if expected.get("rehearsal"):
        return {"verified": False,
                "reason": "CONTROLLED_REHEARSAL is permanently excluded "
                          "from consumption proof (never a learning "
                          "claim)",
                "checks": {"rehearsal_excluded": True}}
    manifest_path = os.path.join(child_run_dir, "run_manifest.json")
    try:
        manifest = json.load(open(manifest_path, encoding="utf-8"))
        checks["manifest_readable"] = True
    except Exception as exc:
        return {"verified": False,
                "reason": "run manifest unreadable: %s (no manifest, "
                          "no verified run)" % (type(exc).__name__,),
                "checks": {"manifest_readable": False}}
    checks["run_executed"] = bool(manifest.get("run_id"))
    man_knowledge = manifest.get("knowledge_consumed") or {}
    checks["manifest_run_id_match"] = (
        manifest.get("run_id") == expected.get("child_run_id"))
    checks["manifest_trigger_match"] = (
        man_knowledge.get("trigger_event_id")
        == expected.get("trigger_event_id"))
    checks["manifest_knowledge_match"] = (
        man_knowledge.get("knowledge_record_id")
        == expected.get("knowledge_record_id"))
    checks["manifest_artifact_match"] = (
        man_knowledge.get("knowledge_artifact_sha256")
        == expected.get("knowledge_artifact_sha256"))
    checks["manifest_parent_run_match"] = (
        man_knowledge.get("parent_run_id")
        == expected.get("parent_run_id"))
    checks["manifest_parent_problem_match"] = (
        man_knowledge.get("parent_problem_sha256")
        == expected.get("parent_problem_sha256"))
    checks["manifest_branch_match"] = (
        man_knowledge.get("branch") == expected.get("branch"))
    checks["manifest_binds_knowledge"] = bool(
        checks["manifest_trigger_match"]
        and checks["manifest_knowledge_match"])
    problem_path = os.path.join(child_run_dir, "problem.json")
    try:
        problem = json.load(open(problem_path, encoding="utf-8"))
        checks["problem_readable"] = True
    except Exception as exc:
        return {"verified": False,
                "reason": "child problem.json unreadable: %s" %
                          (type(exc).__name__,),
                "checks": checks}
    block = problem.get("reality_constraints") or {}
    checks["block_trigger_match"] = \
        block.get("trigger_event_id") == expected.get("trigger_event_id")
    checks["block_knowledge_match"] = \
        block.get("knowledge_record_id") == expected.get(
            "knowledge_record_id")
    checks["clause_present"] = ("[REALITY %s:" %
                                (expected.get("trigger_event_id"),)
                                in str(problem.get("constraint") or ""))
    artifact_hash = block.get("knowledge_artifact_sha256",
                              "NOT_SUPPLIED")
    resolved, resolved_bytes = None, None
    if knowledge_resolver is not None:
        try:
            resolved = knowledge_resolver(
                block.get("knowledge_record_id"))
        except Exception as exc:
            resolved = None
            checks["resolver_error"] = "%s: %s" % (
                type(exc).__name__, str(exc)[:200])
    if isinstance(resolved, dict):
        if _loop_sha(_knowledge_canonical(resolved)) == artifact_hash:
            checks["artifact"] = "RESOLVED"
        else:
            checks["artifact"] = "TAMPERED"
    else:
        checks["artifact"] = "UNRESOLVED_ABSENT"
    failures = []
    if not checks["run_executed"]:
        failures.append("no run identity in manifest")
    if not checks["manifest_run_id_match"]:
        failures.append("manifest run_id != expected child_run_id")
    if not checks["manifest_trigger_match"]:
        failures.append("manifest trigger mismatch")
    if not checks["manifest_knowledge_match"]:
        failures.append("manifest knowledge mismatch")
    if not checks["manifest_artifact_match"]:
        failures.append("manifest artifact-hash mismatch")
    if not checks["manifest_parent_run_match"]:
        failures.append("manifest parent-run mismatch")
    if not checks["manifest_parent_problem_match"]:
        failures.append("manifest parent-problem-hash mismatch")
    if not checks["manifest_branch_match"]:
        failures.append("manifest branch mismatch")
    if not checks["manifest_binds_knowledge"]:
        failures.append("manifest does not bind the expected knowledge")
    if not checks["block_trigger_match"]:
        failures.append("problem lineage trigger mismatch")
    if not checks["block_knowledge_match"]:
        failures.append("problem lineage knowledge mismatch")
    if not checks["clause_present"]:
        failures.append("constraint clause absent from problem")
    if checks["artifact"] != "RESOLVED":
        failures.append("artifact %s" % (checks["artifact"],))
    contract = {
        "parent_event_id": expected.get("trigger_event_id"),
        "parent_run_id": expected.get("parent_run_id"),
        "child_run_id": manifest.get("run_id"),
        "knowledge_record_id": expected.get("knowledge_record_id"),
        "knowledge_artifact_sha256": artifact_hash,
        "child_problem_sha256": _loop_sha(problem),
        "child_input_manifest_hash": _loop_sha({
            "problem": problem,
            "manifest_run_id": manifest.get("run_id")}),
        "trigger_event_id": expected.get("trigger_event_id"),
        "launch_id": expected.get("launch_id"),
        "verified_at": _loop_now(),
        "verifier_provenance": "reality_ingestion.verify_consumption",
    }
    if failures:
        return {"verified": False,
                "reason": "consumption unproven: %s" % ("; ".join(
                    failures),),
                "checks": checks, "contract": contract}
    return {"verified": True, "checks": checks, "contract": contract,
            "reason": "all consumption checks green from independent "
                      "artifacts"}


def verify_search_consumption(child_run_dir: str, expected: Dict,
                              knowledge_resolver=None) -> Dict:
    """Independent search-consumption verifier (§5): proves manifest
    binding AND actual search-stage consumption. KNOWLEDGE_BOUND
    (verify_consumption) NEVER implies SEARCH_CONSUMPTION_VERIFIED.

    States:
      SEARCH_CONSUMPTION_VERIFIED — binding proven, record integrity
        proven, and an executed search decision is bound to THIS
        knowledge (cemetery kill citing the expected cemetery entry).
      SEARCH_CONSUMPTION_UNPROVEN — bound, but no (valid) record or
        no knowledge-bound decision (the honest cliff state: a
        correct manifest with no actual search consumption).
      SEARCH_CONSUMPTION_REJECTED — binding failed, or the record is
        forged/tampered (integrity mismatch), or rehearsal.

    A child receipt (CONSUMPTION.json) alone remains insufficient —
    it is never consulted here."""
    child_run_dir = str(child_run_dir)
    expected = expected or {}
    if expected.get("rehearsal"):
        return {"state": "SEARCH_CONSUMPTION_REJECTED",
                "knowledge_state": "KNOWLEDGE_UNBOUND",
                "reason": "CONTROLLED_REHEARSAL is permanently excluded "
                          "from consumption proof",
                "checks": {"rehearsal_excluded": True}}
    bound = verify_consumption(child_run_dir, expected,
                               knowledge_resolver)
    knowledge_state = ("KNOWLEDGE_BOUND" if bound.get("verified")
                       else "KNOWLEDGE_UNBOUND")
    checks: Dict[str, Any] = {"knowledge_binding": bound}
    if not bound.get("verified"):
        return {"state": "SEARCH_CONSUMPTION_REJECTED",
                "knowledge_state": knowledge_state,
                "reason": "knowledge not bound: %s" % (
                    bound.get("reason"),),
                "checks": checks}
    rec_path = os.path.join(child_run_dir, "SEARCH_CONSUMPTION.json")
    try:
        record = json.load(open(rec_path, encoding="utf-8"))
        checks["record_readable"] = True
    except Exception as exc:
        checks["record_readable"] = False
        return {"state": "SEARCH_CONSUMPTION_UNPROVEN",
                "knowledge_state": knowledge_state,
                "reason": "no search-consumption record: %s "
                          "(bound input, unproven search)" % (
                              type(exc).__name__,),
                "checks": checks}
    try:
        manifest = json.load(open(os.path.join(
            child_run_dir, "run_manifest.json"), encoding="utf-8"))
        problem = json.load(open(os.path.join(
            child_run_dir, "problem.json"), encoding="utf-8"))
    except Exception as exc:
        return {"state": "SEARCH_CONSUMPTION_REJECTED",
                "knowledge_state": knowledge_state,
                "reason": "run artifacts unreadable: %s" % (
                    type(exc).__name__,),
                "checks": checks}
    import hashlib as _hl
    constraint_hash = _hl.sha256(
        str(problem.get("constraint") or "").encode(
            "utf-8", "replace")).hexdigest()
    snapshot = record.get("search_snapshot") or {}
    checks["record_child_run_match"] = (
        record.get("child_run_id") == manifest.get("run_id")
        == expected.get("child_run_id"))
    checks["record_trigger_match"] = (
        record.get("trigger_event_id")
        == expected.get("trigger_event_id"))
    checks["record_knowledge_match"] = (
        record.get("knowledge_record_id")
        == expected.get("knowledge_record_id"))
    checks["record_artifact_match"] = (
        record.get("knowledge_artifact_sha256")
        == expected.get("knowledge_artifact_sha256"))
    checks["record_stage_match"] = (
        record.get("stage") == "MECHANISM_SPACE")
    checks["record_constraint_match"] = (
        record.get("consumed_constraint_sha256") == constraint_hash
        == snapshot.get("consumed_constraint_sha256"))
    checks["record_snapshot_integrity"] = (
        record.get("search_state_hash") == snapshot.get("snapshot_hash")
        == _loop_sha({k: v for k, v in snapshot.items()
                      if k != "snapshot_hash"}))
    integrity = bool(
        checks["record_child_run_match"]
        and checks["record_trigger_match"]
        and checks["record_knowledge_match"]
        and checks["record_artifact_match"]
        and checks["record_stage_match"]
        and checks["record_constraint_match"]
        and checks["record_snapshot_integrity"])
    checks["record_integrity"] = integrity
    if not integrity:
        bad = sorted(k for k, v in checks.items()
                     if k.startswith("record_") and not v)
        return {"state": "SEARCH_CONSUMPTION_REJECTED",
                "knowledge_state": knowledge_state,
                "reason": "search-consumption record forged or tampered "
                          "(%s)" % (", ".join(bad),),
                "checks": checks}
    ccons = (snapshot.get("cemetery_consultation") or {})
    blocked_ids = set(ccons.get("blocked_entry_ids") or [])
    warned_ids = set(ccons.get("warned_entry_ids") or [])
    entry_id = expected.get("cemetery_entry_id")
    knowledge_hash = expected.get("knowledge_artifact_sha256")
    record_hash = record.get("search_state_hash")
    space_state = snapshot.get("space_state")
    executed = space_state in ("BUILT", "BUILT_BELOW_MIN",
                               "NO_CANDIDATES")
    decisions = []
    if entry_id and entry_id in blocked_ids:
        decisions.append({"decision_type": "CEMETERY_KILL",
                          "decision_ref": entry_id,
                          "knowledge_hash": knowledge_hash,
                          "record_hash": record_hash})
    if entry_id and entry_id in warned_ids:
        decisions.append({"decision_type": "CEMETERY_WARNING",
                          "decision_ref": entry_id,
                          "knowledge_hash": knowledge_hash,
                          "record_hash": record_hash})
    if executed and snapshot.get("selected_operator") and int(
            snapshot.get("contracts_satisfied") or 0) >= 1:
        decisions.append({"decision_type": "OPERATOR_SELECTION",
                          "decision_ref": snapshot.get(
                              "selected_operator"),
                          "knowledge_hash": knowledge_hash,
                          "record_hash": record_hash})
    if executed and int((snapshot.get("candidates") or {}).get(
            "n_retained") or 0) >= 1:
        decisions.append({"decision_type": "CANDIDATE_SELECTION",
                          "decision_ref": "retained=%d" % (
                              (snapshot.get("candidates") or {}).get(
                                  "n_retained")),
                          "knowledge_hash": knowledge_hash,
                          "record_hash": record_hash})
    if executed and (snapshot.get("operators_examined") or []):
        decisions.append({"decision_type": "ADMISSION_MAP",
                          "decision_ref": "examined=%d" % (
                              len(snapshot.get("operators_examined"))),
                          "knowledge_hash": knowledge_hash,
                          "record_hash": record_hash})
    checks["decisions"] = [d["decision_type"] for d in decisions]
    checks["decision_n_blocked"] = int(ccons.get("n_blocked") or 0)
    checks["decision_n_warned"] = int(ccons.get("n_warned") or 0)
    if decisions:
        return {"state": "SEARCH_CONSUMPTION_VERIFIED",
                "knowledge_state": knowledge_state,
                "record_hash": record_hash,
                "decisions": decisions,
                "reason": "manifest binding plus %d executed "
                          "search-stage decision(s) bound to this "
                          "knowledge (%s)" % (
                              len(decisions),
                              ", ".join(d["decision_type"]
                                        for d in decisions)),
                "checks": checks, "record": record}
    return {"state": "SEARCH_CONSUMPTION_UNPROVEN",
            "knowledge_state": knowledge_state,
            "record_hash": record_hash,
            "decisions": decisions,
            "reason": "record integrity holds but no executed search "
                      "decision is bound to this knowledge "
                      "(n_blocked=%d, n_warned=%d; KNOWLEDGE_BOUND "
                      "does not imply consumption)" % (
                          checks["decision_n_blocked"],
                          checks["decision_n_warned"]),
            "checks": checks, "record": record}


def extract_search_state(run_dir: str, cemetery_path=None) -> Dict:
    """Machine-readable SEARCH_STATE (§6) extracted deterministically
    from a run dir (works on ANY run dir, parent or child). Fields
    that have no canonical source stay typed UNKNOWN (never prose,
    never invented)."""
    run_dir = str(run_dir)
    try:
        problem = json.load(open(os.path.join(
            run_dir, "problem.json"), encoding="utf-8"))
        prob_ok = True
    except Exception:
        problem, prob_ok = {}, False
    try:
        manifest = json.load(open(os.path.join(
            run_dir, "run_manifest.json"), encoding="utf-8"))
    except Exception:
        manifest = {}
    ms_path = os.path.join(run_dir, "envelope_MECHANISM_SPACE.json")
    if os.path.exists(ms_path):
        try:
            _ms = json.load(open(ms_path, encoding="utf-8"))
            _space = _ms.get("mechanism_space", _ms)
            regions: Dict[str, Any] = {
                "state": "READ",
                "operator_ids": _space.get("operator_ids"),
                "operators_examined": [
                    {"operator": o.get("operator"),
                     "state": o.get("state")}
                    for o in (_space.get("operator_results") or [])]}
        except Exception as exc:
            regions = {"state": "UNKNOWN_UNREADABLE",
                       "error": type(exc).__name__}
    else:
        regions = {"state": "UNKNOWN_NO_MECHANISM_SPACE"}
    if cemetery_path is not None and os.path.exists(str(cemetery_path)):
        try:
            _cem = json.load(open(str(cemetery_path), encoding="utf-8"))
            _entries = _cem.get("entries", [])
            cemetery = {"state": "READ",
                        "entry_count": len(_entries),
                        "head_sha256": _loop_sha(_entries[-1])
                        if _entries else "EMPTY"}
        except Exception as exc:
            cemetery = {"state": "UNKNOWN_UNREADABLE",
                        "error": type(exc).__name__}
    else:
        cemetery = {"state": "UNKNOWN_NO_CEMETERY_PATH"}
    block = (problem.get("reality_constraints") or {}) \
        if prob_ok else {}
    sc_path = os.path.join(run_dir, "SEARCH_CONSUMPTION.json")
    if os.path.exists(sc_path):
        try:
            _sc = json.load(open(sc_path, encoding="utf-8"))
            search_snapshot = _sc.get("search_snapshot")
            search_consumption = {
                "state": "RECORDED",
                "search_state_hash": _sc.get("search_state_hash"),
                "integrity": bool(
                    search_snapshot
                    and _sc.get("search_state_hash")
                    == search_snapshot.get("snapshot_hash")),
            }
        except Exception as exc:
            search_snapshot, search_consumption = None, {
                "state": "UNKNOWN_UNREADABLE",
                "error": type(exc).__name__}
    elif os.path.exists(ms_path):
        try:
            _ms2 = json.load(open(ms_path, encoding="utf-8"))
            _space2 = _ms2.get("mechanism_space", _ms2)
            search_snapshot = canonical_search_snapshot(
                _space2 if isinstance(_space2, dict) else {},
                str(problem.get("constraint") or "")
                if prob_ok else "", manifest)
            search_consumption = {"state": "UNRECORDED_STAGE_EXECUTED"}
        except Exception as exc:
            search_snapshot, search_consumption = None, {
                "state": "UNKNOWN_UNREADABLE",
                "error": type(exc).__name__}
    else:
        search_snapshot, search_consumption = None, {
            "state": "UNKNOWN_NO_SEARCH_EXECUTION"}
    state = {
        "artifact_type": "SEARCH_STATE/1.0.0",
        "run_id": manifest.get("run_id"),
        "problem_sha256": _loop_sha(problem) if prob_ok else "UNREADABLE",
        "constraint_text": str(problem.get("constraint") or "")
        if prob_ok else "",
        "knowledge_binding": {
            "trigger_event_id": block.get("trigger_event_id"),
            "knowledge_record_id": block.get("knowledge_record_id"),
            "knowledge_artifact_sha256":
                block.get("knowledge_artifact_sha256"),
        } if block else None,
        "operator_regions": regions,
        "candidate_selection_policy": {
            "disabled_stages": sorted(manifest.get("disabled_stages", [])),
            "stage_order": manifest.get("stage_order"),
        } if manifest else "UNKNOWN_NO_MANIFEST",
        "query_policy": "UNKNOWN_NO_QUERY_REGISTRY",
        "cemetery": cemetery,
        "search_snapshot": search_snapshot,
        "search_consumption": search_consumption,
        "active_hypotheses_constraints": [
            str(problem.get("constraint") or "")] if prob_ok else [],
    }
    state["canonical_state_hash"] = _loop_sha(
        {k: v for k, v in state.items() if k != "artifact_type"})
    return state


def measure_search_delta(s0: Dict, s1: Dict) -> Dict:
    """MEASURED_DELTA = DIFF(S0, S1) with substantive-field rules.
    A different problem_id, serialized constraint, clause TEXT,
    cemetery file change, or run-configuration change alone is
    NEVER substantive (wording, archival writes, and config are
    not learning). constraint_applied is substantive ONLY with
    record-linked executed-decision evidence: an entry-linked
    cemetery kill/warning, or a causal operator/candidate/region
    decision difference S0->S1 with S1's search-consumption record
    present and integrity-held. decision_evidence cites the exact
    supporting artifact (decision type, ref, knowledge hash, record
    hash, causal field) — never a bare boolean."""
    def _norm_constraint(text):
        import re as _re
        return _re.sub(r"\[REALITY [^\]]*\]", "", str(text or "")
                       ).strip()
    s0c = _norm_constraint((s0.get("active_hypotheses_constraints") or
                            [""])[0])
    s1c = _norm_constraint((s1.get("active_hypotheses_constraints") or
                            [""])[0])
    kb0 = (s0.get("knowledge_binding") or {})
    kb1 = (s1.get("knowledge_binding") or {})
    knowledge_bound = bool(
        kb1.get("trigger_event_id") and kb1.get("knowledge_record_id")
        and not kb0.get("trigger_event_id"))
    cem0, cem1 = s0.get("cemetery") or {}, s1.get("cemetery") or {}
    cemetery_flip = bool(
        cem0.get("state") == "READ" and cem1.get("state") == "READ"
        and cem0.get("head_sha256") != cem1.get("head_sha256"))
    pol0 = (s0.get("candidate_selection_policy") or {})
    pol1 = (s1.get("candidate_selection_policy") or {})
    policy_change = bool(
        isinstance(pol0, dict) and isinstance(pol1, dict)
        and (pol0.get("disabled_stages") != pol1.get("disabled_stages")
             or pol0.get("stage_order") != pol1.get("stage_order")))
    import re as _re2
    _clause = lambda t: bool(_re2.search(r"\[REALITY [^\]]*\]",
                                         str(t or "")))
    _s0raw = (s0.get("active_hypotheses_constraints") or [""])[0]
    _s1raw = (s1.get("active_hypotheses_constraints") or [""])[0]
    clause_text_present = bool(_clause(_s1raw) and not _clause(_s0raw))
    sn0 = (s0.get("search_snapshot") or {})
    sn1 = (s1.get("search_snapshot") or {})
    sc1 = (s1.get("search_consumption") or {})
    record_linked = bool(
        sc1.get("state") == "RECORDED"
        and sc1.get("integrity") is True
        and sc1.get("search_state_hash")
        == (sn1.get("snapshot_hash")))
    record_hash = sc1.get("search_state_hash")
    knowledge_hash = kb1.get("knowledge_artifact_sha256")
    _s1blocked = set(((sn1.get("cemetery_consultation") or {})
                      .get("blocked_entry_ids")) or [])
    _s0blocked = set(((sn0.get("cemetery_consultation") or {})
                      .get("blocked_entry_ids")) or [])
    _new_blocks = _s1blocked - _s0blocked
    _s1warned = set(((sn1.get("cemetery_consultation") or {})
                     .get("warned_entry_ids")) or [])
    _s0warned = set(((sn0.get("cemetery_consultation") or {})
                     .get("warned_entry_ids")) or [])
    _new_warned = _s1warned - _s0warned
    _entry_id = kb1.get("cemetery_entry_id")
    kill_decision_bound = bool(
        knowledge_bound and record_linked and _entry_id
        and _entry_id in _new_blocks)
    warning_decision_bound = bool(
        knowledge_bound and record_linked and _entry_id
        and _entry_id in _new_warned)
    kill_decision_unlinked = bool(
        knowledge_bound and _new_blocks
        and not kill_decision_bound)
    _op_sel = bool(
        sn0 and sn1
        and sn0.get("selected_operator") != sn1.get(
            "selected_operator")
        and sn1.get("selected_operator") is not None)
    _op_ids = bool(
        sn0 and sn1
        and (sn0.get("operator_ids") or []) != (
            sn1.get("operator_ids") or [])
        and (sn1.get("operator_ids") or []))
    _cand_dec = bool(
        sn0 and sn1
        and (sn0.get("candidates") or {}).get("decisions")
        != (sn1.get("candidates") or {}).get("decisions"))
    _reg0 = sorted((d.get("operator"), d.get("state"))
                   for d in (sn0.get("operators_examined") or [])
                   if isinstance(d, dict))
    _reg1 = sorted((d.get("operator"), d.get("state"))
                   for d in (sn1.get("operators_examined") or [])
                   if isinstance(d, dict))
    _reg_dec = bool(sn0 and sn1 and _reg0 != _reg1 and _reg1)
    operator_selection_diff = bool(
        knowledge_bound and record_linked and (_op_sel or _op_ids))
    candidate_decision_diff = bool(
        knowledge_bound and record_linked and _cand_dec)
    region_admission_diff = bool(
        knowledge_bound and record_linked and _reg_dec)
    constraint_applied = bool(
        kill_decision_bound or warning_decision_bound
        or operator_selection_diff or candidate_decision_diff
        or region_admission_diff)
    decision_evidence = None
    if kill_decision_bound:
        decision_evidence = {
            "decision_type": "CEMETERY_KILL",
            "decision_ref": _entry_id,
            "knowledge_hash": knowledge_hash,
            "record_hash": record_hash,
            "causal_field": "kill_decision_bound"}
    elif warning_decision_bound:
        decision_evidence = {
            "decision_type": "CEMETERY_WARNING",
            "decision_ref": _entry_id,
            "knowledge_hash": knowledge_hash,
            "record_hash": record_hash,
            "causal_field": "warning_decision_bound"}
    elif operator_selection_diff:
        decision_evidence = {
            "decision_type": "OPERATOR_SELECTION",
            "decision_ref": sn1.get("selected_operator"),
            "knowledge_hash": knowledge_hash,
            "record_hash": record_hash,
            "causal_field": "operator_selection_diff"}
    elif candidate_decision_diff:
        decision_evidence = {
            "decision_type": "CANDIDATE_SELECTION",
            "decision_ref": "decisions-changed",
            "knowledge_hash": knowledge_hash,
            "record_hash": record_hash,
            "causal_field": "candidate_decision_diff"}
    elif region_admission_diff:
        decision_evidence = {
            "decision_type": "ADMISSION_MAP",
            "decision_ref": "admission-changed",
            "knowledge_hash": knowledge_hash,
            "record_hash": record_hash,
            "causal_field": "region_admission_diff"}
    hypothesis_new = bool(s1c and s1c != s0c)
    changed = {
        "knowledge_bound": knowledge_bound,
        "record_linked": record_linked,
        "kill_decision_bound": kill_decision_bound,
        "warning_decision_bound": warning_decision_bound,
        "operator_selection_diff": operator_selection_diff,
        "candidate_decision_diff": candidate_decision_diff,
        "region_admission_diff": region_admission_diff,
        "constraint_applied": constraint_applied,
        "kill_decision_unlinked_informational_only":
            kill_decision_unlinked,
        "cemetery_flip_informational_only": cemetery_flip,
        "policy_change_informational_only": policy_change,
        "clause_text_present_informational_only": clause_text_present,
        "hypothesis_new_informational_only": hypothesis_new,
        "problem_only": (
            s0.get("problem_sha256") != s1.get("problem_sha256")
            and not (knowledge_bound or constraint_applied)),
    }
    substantive = bool(knowledge_bound and record_linked
                       and constraint_applied)
    out = {"substantive": substantive,
           "changed_fields": sorted(
               k for k, v in changed.items() if v),
           "all_fields": changed,
           "decision_evidence": decision_evidence,
           "falsifier": "problem_id/constraint/clause wording, "
                        "cemetery-file changes, and run configuration "
                        "are excluded by construction; hypothesis text "
                        "without binding is informational only"}
    return out


def adjudicate_search_learning(delta: Dict,
                               search_verification=None) -> Dict:
    """LEARNING ADJUDICATION over a MEASURED_DELTA (distinct from the
    candidate adjudicator adjudicate_learning() — that name is kept
    untouched). The chain is structural: KNOWLEDGE_BOUND alone is
    never enough; the delta alone is never enough.
      no verified search consumption -> NO_LEARNING;
      verified + no substantive delta -> NO_LEARNING;
      verified + substantive but delta evidence unlinked from the
        verified record -> NO_LEARNING;
      verified + substantive + record-linked causal evidence ->
        LEARNING_CANDIDATE.
    search_verification is {"state":..., "record_hash":...} from
    verify_search_consumption(). Deterministic, no I/O, no LLM."""
    delta = delta or {}
    changed = list(delta.get("changed_fields") or [])
    verification = search_verification or {}
    if verification.get("state") != "SEARCH_CONSUMPTION_VERIFIED":
        return {"verdict": "NO_LEARNING",
                "reason": "no verified search consumption (state=%s; "
                          "KNOWLEDGE_BOUND and raw deltas never imply "
                          "learning)" % (
                              verification.get("state"),),
                "changed_fields": changed}
    if delta.get("substantive") is not True:
        return {"verdict": "NO_LEARNING",
                "reason": "verified search consumption without a "
                          "measured substantive delta (changed: %s)" % (
                              ", ".join(changed) or "none",),
                "changed_fields": changed}
    evidence = delta.get("decision_evidence") or {}
    if evidence.get("record_hash") != verification.get("record_hash") \
            or not evidence.get("record_hash"):
        return {"verdict": "NO_LEARNING",
                "reason": "substantive delta is not linked to the "
                          "verified search-consumption record "
                          "(unlinked evidence never implies learning)",
                "changed_fields": changed}
    return {"verdict": "LEARNING_CANDIDATE",
            "reason": "verified search consumption %s plus "
                      "record-linked causal delta (%s: %s)" % (
                          verification.get("record_hash"),
                          evidence.get("decision_type"),
                          evidence.get("causal_field")),
            "changed_fields": changed,
            "decision_evidence": evidence}


def default_run_launcher(child_request: Dict, runs_root: str,
                         disabled_stages=None,
                         knowledge_resolver=None) -> Dict:
    """Production child launcher: materialize the child as a genuine
    EngineRun (canonical worker machinery — never a parallel engine)
    and execute it. Used in keyed environments; tests pass fakes.

    Launcher contract (§4/§11): construction-time validation failures
    (bad request shape) raise LauncherRejected (proven pre-launch
    refusal); a run() failure AFTER dispatch is AMBIGUOUS (the remote
    may have executed) and propagates as-is -> UNKNOWN_LAUNCH. Every
    production launcher MUST additionally be idempotent by launch_id:
    the same launch_id must converge on one execution effect."""
    from .run import EngineRun
    import os as _os
    try:
        problem = dict(child_request["child_problem"])
        child_run_id = child_request["child_run_id"]
        out_dir = _os.path.join(runs_root, child_run_id)
        run = EngineRun(problem=problem,
                        out_dir=out_dir,
                        run_id=child_run_id,
                        session_id=child_request.get("session_id"),
                        disabled_stages=disabled_stages)
    except (KeyError, TypeError, ValueError) as exc:
        raise LauncherRejected("invalid child request: %s" % (exc,))
    result = run.run()
    _cons_path = _os.path.join(out_dir, "CONSUMPTION.json")
    if _os.path.exists(_cons_path):
        try:
            _child_receipt = json.load(open(_cons_path, encoding="utf-8"))
            consumption = {"consumed": True,
                           "receipt": _child_receipt,
                           "note": "receipt authored by the child run "
                                   "itself (not synthesized by the "
                                   "parent)"}
        except Exception as exc:
            consumption = {"consumed": False,
                           "reason": "child receipt unreadable: %s" %
                                     (type(exc).__name__,)}
    else:
        consumption = record_child_consumption(
            out_dir,
            child_request.get("trigger_event_id"),
            child_request.get("parent_run_id"),
            child_request.get("knowledge_record_id"),
            child_request.get("knowledge_artifact_sha256",
                              "NOT_SUPPLIED"),
            child_request.get("parent_problem_sha256"))
    verification = {"artifact_verification": "UNRESOLVED_NO_RESOLVER",
                    "note": "no knowledge resolver supplied; artifact "
                            "hash carried, not independently re-verified"}
    if knowledge_resolver is not None:
        try:
            artifact = knowledge_resolver(
                child_request.get("knowledge_record_id"))
        except Exception as exc:
            artifact = None
            verification = {"artifact_verification": "UNRESOLVED",
                            "reason": "resolver failed: %s" %
                                      (type(exc).__name__,)}
        if artifact is None and \
                verification.get("artifact_verification") != "UNRESOLVED":
            verification = {"artifact_verification": "UNRESOLVED",
                            "reason": "knowledge artifact not resolvable; "
                                      "never synthesized (fail-closed)"}
        elif isinstance(artifact, dict):
            if _loop_sha(_knowledge_canonical(artifact)) == \
                    child_request.get("knowledge_artifact_sha256"):
                verification = {"artifact_verification": "RESOLVED"}
            else:
                verification = {"artifact_verification": "TAMPERED",
                                "reason": "resolved bytes do not match "
                                          "the bound hash; consumption "
                                          "rejected (fail-closed)"}
                consumption = {"consumed": False,
                               "artifact_verification": "TAMPERED",
                               "reason": verification["reason"]}
        _atomic_write_json(_os.path.join(
            out_dir, "CONSUMPTION_VERIFICATION.json"), verification)
    return {"child_run_id": child_request["child_run_id"],
            "launcher": "default_engine_run",
            "launched_at": _loop_now(),
            "run_state": (result or {}).get("state",
                                            "UNKNOWN_NO_RESULT"),
            "consumption": consumption,
            "artifact_verification": verification}


def default_execution_checker(runs_root: str):
    """Build the production execution checker for reconcile: given a
    launch_id + hint {child_run_id}, return the durable execution
    record if the child run exists on disk, else None. Read-only;
    never launches. (Tests use an equivalent identity-preserving
    double over an effect registry.)"""
    import os as _os

    def _check(launch_id, hint=None):
        hint = hint or {}
        child_run_id = hint.get("child_run_id")
        if not child_run_id:
            return None
        manifest = _os.path.join(str(runs_root), str(child_run_id),
                                 "run_manifest.json")
        if not _os.path.exists(manifest):
            return None
        try:
            data = json.load(open(manifest, encoding="utf-8"))
        except Exception:
            return None
        if data.get("run_id") != child_run_id:
            return None
        return {"child_run_id": child_run_id,
                "launch_id": launch_id,
                "manifest_state": "RUN_DIR_PRESENT",
                "run_manifest": data}
    return _check
