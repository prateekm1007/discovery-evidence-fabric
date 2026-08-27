"""discovery_fabric/engine/candidate.py — D7 canonical candidate envelope.

Every stage of the integrated discovery loop consumes and produces this ONE
envelope. No stage may invent an incompatible structure. Every stage execution
is appended to `stage_log` with before/after envelope hashes and the exact
delta keys — this is what makes RUNTIME_BEHAVIORAL_PROOF (D10) mechanical
rather than asserted (Epistemic Constitution Art. XXIV: artifact beats prose).

Provenance rule (Art. VI): the engine never fabricates hashes, timestamps or
source ids. Failure states are recorded explicitly (Art. IV, XXV).
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

ENVELOPE_FIELDS = [
    "candidate_id", "problem_id", "problem",
    "evidence_ids", "evidence",
    "mechanism_ids", "mechanism_map",
    "prior_art_ids", "prior_art",
    "collision_results",
    "attack_results",
    "contradictions",
    "killer_experiment",
    "adjudication",
    "multi_source",
    "cemetery_check",
    "epistemic_state",
    "next_best_action",
    "ranking",
    "provenance",
    "stage_log",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


@dataclass
class Candidate:
    """Single canonical envelope flowing through all stages."""

    problem: Dict[str, Any]
    problem_id: str
    candidate_id: str = ""
    evidence_ids: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    mechanism_ids: List[str] = field(default_factory=list)
    mechanism_map: Dict[str, Any] = field(default_factory=dict)
    prior_art_ids: List[str] = field(default_factory=list)
    prior_art: Dict[str, Any] = field(default_factory=dict)
    collision_results: Dict[str, Any] = field(default_factory=dict)
    attack_results: Dict[str, Any] = field(default_factory=dict)
    contradictions: Dict[str, Any] = field(default_factory=dict)
    killer_experiment: Dict[str, Any] = field(default_factory=dict)
    adjudication: Dict[str, Any] = field(default_factory=dict)
    multi_source: Dict[str, Any] = field(default_factory=dict)
    cemetery_check: Dict[str, Any] = field(default_factory=dict)
    epistemic_state: Dict[str, Any] = field(default_factory=dict)
    next_best_action: Dict[str, Any] = field(default_factory=dict)
    ranking: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)
    stage_log: List[Dict[str, Any]] = field(default_factory=list)

    # ------------------------------------------------------------------
    def envelope_hash(self) -> str:
        payload = {k: getattr(self, k) for k in ENVELOPE_FIELDS
                   if k not in ("stage_log",)}
        return sha256_obj(payload)

    def to_dict(self) -> Dict[str, Any]:
        return {k: copy.deepcopy(getattr(self, k)) for k in ENVELOPE_FIELDS}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Candidate":
        kw = {k: copy.deepcopy(d.get(k)) for k in ENVELOPE_FIELDS
              if k != "problem"}
        kw["problem"] = copy.deepcopy(d.get("problem") or {})
        return cls(**kw)

    # ------------------------------------------------------------------
    def run_stage(self, stage_name: str, capability_id: str,
                  module_path: str, fn_name: str, fn, *args, **kwargs):
        """Execute one stage through the uniform envelope protocol.

        Captures before/after hashes, computes delta keys mechanically and
        appends a stage_log entry. Exceptions become explicit FAILED states —
        never silent skips (Art. IV) and never fabricated success (Art. VI).
        """
        before = self.envelope_hash()
        entry: Dict[str, Any] = {
            "stage": stage_name,
            "capability_id": capability_id,
            "module_path": module_path,
            "function": fn_name,
            "started_at": utc_now(),
            "before_envelope_hash": before,
        }
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - fail closed, recorded
            entry.update({
                "status": "FAILED_EXPLICIT",
                "error": f"{type(exc).__name__}: {exc}",
                "finished_at": utc_now(),
                "after_envelope_hash": before,
                "candidate_delta": [],
                "delta_real": False,
            })
            self.stage_log.append(entry)
            raise StageFailure(stage_name, entry["error"]) from exc

        delta_keys: List[str] = []
        result_meta: Dict[str, Any] = {}
        if isinstance(result, dict) and result.get("_engine_result") is True:
            applied = result.get("apply_to", {})
            for k, v in applied.items():
                before_val = canonical_json(getattr(self, k))
                setattr(self, k, copy.deepcopy(v))
                if canonical_json(getattr(self, k)) != before_val:
                    delta_keys.append(k)
            result_meta = {k2: v2 for k2, v2 in result.items()
                           if k2 not in ("_engine_result", "apply_to")}
        else:
            result_meta = {"raw_return_type": type(result).__name__}

        after = self.envelope_hash()
        entry.update({
            "status": "OK",
            "finished_at": utc_now(),
            "after_envelope_hash": after,
            "candidate_delta": delta_keys,
            "delta_real": after != before,
            "result_meta": result_meta,
        })
        self.stage_log.append(entry)
        return entry

    def last_stage_entry(self, stage_name: str) -> Optional[Dict[str, Any]]:
        for e in reversed(self.stage_log):
            if e["stage"] == stage_name:
                return e
        return None


class StageFailure(RuntimeError):
    def __init__(self, stage: str, error: str):
        super().__init__(f"stage {stage} failed: {error}")
        self.stage = stage
        self.error = error
