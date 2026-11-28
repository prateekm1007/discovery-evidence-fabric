"""discovery_fabric/engine/holdout_gate.py — the INVENTION GATE for the
holdout (owner audit round R11, 2026-11-14, item 9).

The owner's measured finding: the previous holdout gate (wins+ties vs
baseline >= 50% with >= 1 win) is PASSABLE BY A BASELINE CLONE — it
measures format and labels, not invention. The gate is REPLACED:

  An arm must beat the baseline on invention-rubric NOVELTY by >= 0.5
  with feasibility within 0.25 of the baseline, AUDITOR-JUDGED on
  >= 10 pairs. Beating the baseline on format does not count.

The machine's role: prepare the gate QUANTITIES (the machine-measured
novelty deltas and feasibility gaps per pair, the blind-comparison
records) and type the gate state. The GATE ITSELF is
AUDITOR-JUDGED (Art. XXVI: no self-certification) — machine judgments
are inputs, never the gate verdict. When auditor judgments are
absent, the gate state is PENDING_AUDITOR_JUDGMENTS (never MET, never
inferred — Art. XXV).

Threshold provenance (Art. XXVII — no threshold invention): both
numbers are the OWNER's directive (2026-11-14, item 9), class
BUYER_DEFINED, uncertainty disclosed (n >= 10 pairs; the delta is a
mean over pairs), justification: the audited baseline-clone pass of
the old gate.

Serves: Art. XIX (the audited clone-passable gate decides this one),
Art. XXVI (auditor-judged, machine prepares), Art. XXVII (owner-set
thresholds with provenance), Art. LXXVII (invention is judged on the
deliverable).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

HOLDOUT_GATE_VERSION = "holdout_invention_gate/1.0.0"

#: the owner's thresholds (BUYER_DEFINED, 2026-11-14 directive item 9)
NOVELTY_DELTA_MIN = 0.5
FEASIBILITY_GAP_MAX = 0.25
MIN_PAIRS = 10

OLD_GATE = ("wins+ties vs baseline >= 50% with >= 1 win")
OLD_GATE_STATE = "RETIRED_BY_OWNER_DIRECTIVE_2026-11-14"


def evaluate_holdout_gate(
        pairs: Optional[List[Dict[str, Any]]],
        auditor_judged: bool = False) -> Dict[str, Any]:
    """Evaluate the invention gate for the holdout.

    pairs: one record per judged pair, each carrying the AUDITOR's
    novelty score for the arm and for the baseline (0-4) and both
    feasibility scores. auditor_judged=True marks that these scores
    are the auditor's (the gate requires it).

    Returns {state, ...} where state is one of:
      MET                  — all conditions hold on auditor-judged pairs
      NOT_MET_NOVELTY      — the novelty delta fails
      NOT_MET_FEASIBILITY  — the feasibility gap fails
      NOT_MET_INSUFFICIENT_PAIRS — fewer than 10 judged pairs
      PENDING_AUDITOR_JUDGMENTS — the pairs are machine-judged (or
                             absent): the gate never self-certifies
    """
    rec: Dict[str, Any] = {
        "gate_version": HOLDOUT_GATE_VERSION,
        "definition": ("an arm must beat the baseline on "
                       "invention-rubric NOVELTY by >= "
                       f"{NOVELTY_DELTA_MIN} with feasibility within "
                       f"{FEASIBILITY_GAP_MAX} of the baseline, "
                       f"auditor-judged on >= {MIN_PAIRS} pairs; "
                       "beating the baseline on format does not "
                       "count (owner R11 item 9)"),
        "thresholds": {
            "novelty_delta_min": NOVELTY_DELTA_MIN,
            "novelty_delta_class": "BUYER_DEFINED",
            "novelty_delta_provenance": "owner directive 2026-11-14 "
                                        "item 9 (verbatim)",
            "feasibility_gap_max": FEASIBILITY_GAP_MAX,
            "feasibility_gap_class": "BUYER_DEFINED",
            "feasibility_gap_provenance": "owner directive "
                                          "2026-11-14 item 9",
            "min_pairs": MIN_PAIRS,
            "uncertainty": "mean over >= 10 judged pairs; per-pair "
                           "scores disclosed"},
        "replaced_gate": {
            "definition": OLD_GATE,
            "state": OLD_GATE_STATE,
            "why": ("the audited defect: a baseline clone passes the "
                    "old gate — it measures format and labels, not "
                    "invention (Art. LXIV: retired, not silently "
                    "dropped)")},
    }
    pairs = pairs or []
    if not auditor_judged or len(pairs) < MIN_PAIRS:
        rec["state"] = "PENDING_AUDITOR_JUDGMENTS"
        rec["n_pairs"] = len(pairs)
        rec["why"] = ("the gate is AUDITOR-judged (Art. XXVI: no "
                      "self-certification); machine judgments are "
                      "inputs — the state stays pending until >= "
                      f"{MIN_PAIRS} auditor-judged pairs exist "
                      "(Art. XXV: never inferred)")
        return rec
    deltas: List[float] = []
    gaps: List[float] = []
    for p in pairs:
        arm_n = p.get("arm_novelty")
        base_n = p.get("baseline_novelty")
        arm_f = p.get("arm_feasibility")
        base_f = p.get("baseline_feasibility")
        if None in (arm_n, base_n, arm_f, base_f):
            rec["state"] = "PENDING_AUDITOR_JUDGMENTS"
            rec["why"] = "a judged pair carries incomplete scores"
            return rec
        deltas.append(float(arm_n) - float(base_n))
        gaps.append(abs(float(arm_f) - float(base_f)))
    mean_delta = round(sum(deltas) / len(deltas), 3)
    mean_gap = round(sum(gaps) / len(gaps), 3)
    rec.update({"n_pairs": len(pairs),
                "mean_novelty_delta": mean_delta,
                "mean_feasibility_gap": mean_gap,
                "per_pair": [{"novelty_delta": round(d, 2),
                              "feasibility_gap": round(g, 2)}
                             for d, g in zip(deltas, gaps)]})
    if mean_delta < NOVELTY_DELTA_MIN:
        rec["state"] = "NOT_MET_NOVELTY"
        return rec
    if mean_gap > FEASIBILITY_GAP_MAX:
        rec["state"] = "NOT_MET_FEASIBILITY"
        return rec
    rec["state"] = "MET"
    return rec
