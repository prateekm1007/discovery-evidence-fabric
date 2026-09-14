"""discovery_fabric/r412/stage_cost.py — P1: the stage-cost metric
(CEO R412 directive addition).

> For each candidate, record how much computation was spent before
> death: retrieval_cost, evidence_cost, mechanism_generation_cost,
> novelty_cost, engineering_cost, attack_cost, total_cost, death_stage.

The machine's objective becomes measurable:
> maximize surviving, experimentally decisive technology per unit of
> discovery cost
(Art. LVI — expected information gain per cost — made per-candidate
and per-stage).

SEMANTICS (pinned by tests):

- Costs are APPEND-ONLY per (candidate, stage): a stage that runs
  twice (retries, re-queues) accumulates; nothing is ever overwritten
  or silently rebased.
- Every cost value carries a provenance label:
    MEASURED              — wall-clock seconds actually observed at the
                            stage boundary (or a deterministic stage
                            re-timed read-only on frozen inputs)
    AMORTIZED_MEASURED    — a recorded shared cost (e.g. one domain
                            evidence-pool retrieval serving N
                            candidates), divided by N, arithmetic shown
    ENGINEERING_ESTIMATE  — a labeled estimate extrapolated from a
                            recorded measurement elsewhere (Art. LXVI:
                            the arithmetic and assumptions are shown;
                            an unlabeled estimate is a defect)
    MEASURED_CALL_COUNT   — LLM invocations recorded without latency
                            (an instrumentation gap, recorded as such)
    NOT_RECORDED          — the stage ran but no cost was recorded; the
                            gap itself is the finding (retrofit case)
  A cost with no label is rejected (fail closed).
- death_stage is set ONCE at the terminal event and is immutable
  (rewriting a death stage is history rewriting, Art. XI).
- total_cost = the sum of recorded seconds; costs recorded only as
  call counts do not silently add seconds — they are reported
  separately, never fabricated into seconds.
- The ledger is checkpointed as JSON (resumable; Art. LXII: the
  headline costs are regenerable from committed evidence).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

STAGE_COST_VERSION = "R412-STAGE-COST-V1"

STAGES = [
    "retrieval",
    "mechanism_generation",
    "evidence",
    "novelty",
    "engineering",
    "attack",
]

LABELS = (
    "MEASURED",
    "AMORTIZED_MEASURED",
    "ENGINEERING_ESTIMATE",
    "MEASURED_CALL_COUNT",
    "NOT_RECORDED",
)


class CostLabelError(ValueError):
    """A cost was recorded without a valid provenance label."""


class StageCostLedger:
    """Append-only per-candidate stage-cost ledger."""

    def __init__(self, ledger_path: Optional[Path] = None):
        self.path = ledger_path
        if self.path and self.path.exists():
            data = json.loads(self.path.read_text())
        else:
            data = {"candidates": {}, "version": STAGE_COST_VERSION}
        self._candidates: Dict[str, Dict[str, Any]] = data["candidates"]
        self._data = data

    # -- recording --------------------------------------------------------

    def add_cost(self, candidate_id: str, stage: str, seconds: float,
                 label: str, note: str = "") -> None:
        if stage not in STAGES:
            raise ValueError(f"unknown stage: {stage}")
        if label not in LABELS:
            raise CostLabelError(
                f"label '{label}' is not one of {LABELS} (Art. LXVI: "
                f"unlabeled or mislabeled costs are rejected)")
        entry = self._candidates.setdefault(candidate_id, {
            "stages": {s: {"seconds": 0.0, "entries": []}
                       for s in STAGES},
            "llm_calls": {},
            "death_stage": None,
            "death_note": None,
        })
        st = entry["stages"][stage]
        st["seconds"] = round(st["seconds"] + float(seconds), 4)
        st["entries"].append({
            "seconds": round(float(seconds), 4),
            "label": label,
            "note": note,
        })

    def add_llm_calls(self, candidate_id: str, stage: str, n: int,
                      note: str = "") -> None:
        """Record LLM invocation counts for a stage (latency-independent
        instrumentation; never converted into seconds silently)."""
        if stage not in STAGES:
            raise ValueError(f"unknown stage: {stage}")
        entry = self._candidates.setdefault(candidate_id, {
            "stages": {s: {"seconds": 0.0, "entries": []}
                       for s in STAGES},
            "llm_calls": {},
            "death_stage": None,
            "death_note": None,
        })
        c = entry["llm_calls"].setdefault(stage, {"calls": 0, "notes": []})
        c["calls"] += int(n)
        if note:
            c["notes"].append(note)

    def set_death(self, candidate_id: str, stage: str,
                  note: str = "") -> None:
        """Record the terminal death stage. IMMUTABLE: a second call
        with a different stage raises (history rewriting is forbidden,
        Art. XI)."""
        entry = self._candidates.setdefault(candidate_id, {
            "stages": {s: {"seconds": 0.0, "entries": []}
                       for s in STAGES},
            "llm_calls": {},
            "death_stage": None,
            "death_note": None,
        })
        if entry["death_stage"] is not None and \
                entry["death_stage"] != stage:
            raise ValueError(
                f"death_stage for {candidate_id} is already "
                f"'{entry['death_stage']}'; rewriting it to '{stage}' "
                f"is history rewriting (Art. XI)")
        entry["death_stage"] = stage
        entry["death_note"] = note

    # -- reporting --------------------------------------------------------

    def candidate_summary(self, candidate_id: str) -> Dict[str, Any]:
        entry = self._candidates.get(candidate_id)
        if entry is None:
            return {"candidate_id": candidate_id, "total_cost": 0.0,
                    "death_stage": None}
        out = {"candidate_id": candidate_id}
        total = 0.0
        for s in STAGES:
            seconds = entry["stages"][s]["seconds"]
            out[f"{s}_cost"] = seconds
            total += seconds
        out["llm_calls"] = {
            s: entry["llm_calls"][s]["calls"]
            for s in entry["llm_calls"]}
        out["total_cost"] = round(total, 4)
        out["death_stage"] = entry["death_stage"]
        out["death_note"] = entry["death_note"]
        labels = {s: sorted({e["label"] for e
                             in entry["stages"][s]["entries"]})
                  for s in STAGES if entry["stages"][s]["entries"]}
        out["cost_labels"] = labels
        return out

    def aggregate_by_death_stage(self) -> List[Dict[str, Any]]:
        """The economically measurable waste: cost spent before death,
        grouped by where the death happened (the directive's stage-cost
        view of the 6/11 self-defeating collisions)."""
        groups: Dict[str, Dict[str, Any]] = {}
        for cid in self._candidates:
            summary = self.candidate_summary(cid)
            ds = summary["death_stage"] or "ALIVE/UNSET"
            g = groups.setdefault(ds, {
                "death_stage": ds, "n_candidates": 0,
                "total_cost_before_death": 0.0,
                "cost_per_stage": {s: 0.0 for s in STAGES},
                "candidate_ids": [],
            })
            g["n_candidates"] += 1
            g["total_cost_before_death"] = round(
                g["total_cost_before_death"] +
                summary["total_cost"], 4)
            for s in STAGES:
                g["cost_per_stage"][s] = round(
                    g["cost_per_stage"][s] +
                    summary[f"{s}_cost"], 4)
            g["candidate_ids"].append(cid)
        return sorted(groups.values(),
                      key=lambda g: -g["total_cost_before_death"])

    def save(self) -> None:
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data, indent=1))
