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
