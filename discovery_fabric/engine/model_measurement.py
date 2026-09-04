"""R406 Step 11 — model-vs-measurement updating.

Directive: "For every physical experiment: prediction_before,
actual_measurement, error_before, model_update, prediction_after,
error_after, held_out_error. The system must prove whether the model
improved. A reality event that doesn't change future behavior is not a
learning loop."

Constitutional basis: Art. XXXVII (a REAL loop requires the posterior to
be updated by the external observation — not by coder narrative), Art.
LI (learning must change FUTURE behavior — measured, not asserted),
Art. LIII (reality cannot be simulated into existence: actual_measurement
must trace to a REALITY_EVENT), Art. XXV (missing components stay
INSUFFICIENT_DATA, never zero).

Verdicts:
  MODEL_IMPROVED      — error_after < error_before AND the held-out error
                        improved AND the prediction actually moved
                        (prediction_after != prediction_before).
  MODEL_NOT_IMPROVED  — the update ran on real data but the errors did
                        not improve (this is a legitimate, recordable
                        scientific outcome — not a failure of the
                        machinery).
  INSUFFICIENT_DATA   — any required component is absent (including the
                        pre-physical default state where no measurement
                        exists yet).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

_REQUIRED_FIELDS = (
    "prediction_before",
    "actual_measurement",
    "error_before",
    "model_update",
    "prediction_after",
    "error_after",
    "held_out_error",
)


def _num(x: Any) -> Optional[float]:
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    return None


def build_update_record(
    prediction_before: Optional[float],
    actual_measurement: Optional[float],
    model_update: Optional[Dict[str, Any]],
    prediction_after: Optional[float],
    error_before: Optional[float],
    error_after: Optional[float],
    held_out_error: Optional[float],
    reality_event: Optional[Dict[str, Any]],
    unit: Optional[str] = None,
    notes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Assemble the Step-11 record. The caller supplies the numbers; this
    function computes the verdict honestly and refuses to manufacture
    improvement."""
    rec: Dict[str, Any] = {
        "prediction_before": prediction_before,
        "actual_measurement": actual_measurement,
        "error_before": error_before,
        "model_update": model_update,
        "prediction_after": prediction_after,
        "error_after": error_after,
        "held_out_error": held_out_error,
        "unit": unit,
        "reality_event_id": (reality_event or {}).get("event_id"),
        "reality_source_type": (reality_event or {}).get("source_type"),
        "notes": notes or [],
    }
    missing = [f for f in _REQUIRED_FIELDS
               if f not in rec or rec[f] is None
               or (f in ("prediction_before", "prediction_after",
                         "error_before", "error_after", "held_out_error")
                   and _num(rec[f]) is None)]
    if actual_measurement is None or not reality_event:
        rec["verdict"] = "INSUFFICIENT_DATA"
        rec["insufficient_fields"] = missing + (
            [] if reality_event else ["reality_event"])
        rec["reason"] = ("no physical measurement yet — the machinery is "
                         "armed and the fields are present but unfilled; "
                         "this state can never be promoted (Art. XXV)")
        return rec
    if (reality_event or {}).get("source_type") == "CONTROLLED_REHEARSAL":
        rec["verdict"] = "INSUFFICIENT_DATA"
        rec["insufficient_fields"] = ["reality_event (CONTROLLED_REHEARSAL)"]
        rec["reason"] = ("a controlled rehearsal updates nothing about "
                         "reality; the record is rehearsal-class and may "
                         "not be presented as a learning event "
                         "(Art. XXXVIII)")
        return rec
    if missing:
        rec["verdict"] = "INSUFFICIENT_DATA"
        rec["insufficient_fields"] = missing
        rec["reason"] = "required component(s) absent"
        return rec
    moved = prediction_after != prediction_before
    improved = (error_after is not None and error_before is not None
                and error_after < error_before)
    held_out_ok = (held_out_error is not None and error_before is not None
                   and held_out_error < error_before)
    if improved and held_out_ok and moved:
        rec["verdict"] = "MODEL_IMPROVED"
        rec["reason"] = ("error_after < error_before, held-out error below "
                         "the pre-update error, and the prediction moved — "
                         "the reality event changed future behavior "
                         "(Art. LI)")
    else:
        rec["verdict"] = "MODEL_NOT_IMPROVED"
        rec["reason"] = (
            f"improved={improved} held_out_ok={held_out_ok} "
            f"prediction_moved={moved} — the update did not demonstrably "
            "improve the model; recorded as the honest outcome")
    return rec


def verdict_for_ledger(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Portfolio-level summary: counts by verdict; REAL learning is
    MODEL_IMPROVED records whose reality_source_type is external."""
    counts = {"MODEL_IMPROVED": 0, "MODEL_NOT_IMPROVED": 0,
              "INSUFFICIENT_DATA": 0}
    real_improved = 0
    for r in records:
        v = r.get("verdict")
        if v in counts:
            counts[v] += 1
        if v == "MODEL_IMPROVED" and r.get("reality_source_type") in (
                "EXTERNAL_HUMAN", "EXTERNAL_INSTRUMENT", "EXTERNAL_SYSTEM"):
            real_improved += 1
    return {
        "counts": counts,
        "model_improved_from_real_events": real_improved,
        "learning_loop_operational": real_improved > 0,
        "rule": ("a reality event that does not change future behavior is "
                 "not a learning loop (R406 Step 11)"),
    }
