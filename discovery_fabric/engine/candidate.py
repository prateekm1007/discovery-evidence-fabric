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
import inspect
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import llm_economy as _econ

ENVELOPE_FIELDS = [
    "candidate_id", "problem_id", "problem",
    "evidence_ids", "evidence",
    "mechanism_ids", "mechanism_map",
    # R394 s6: the premise-gate verdict travels in the envelope (a
    # false premise is a first-class recorded outcome, not a log line)
    "premise_gate",
    # R394 s5: claim-level evidence classification (per-item classes
    # + five relevance dimensions) travels with the evidence
    "evidence_classification",
    # R401: the structured mechanism space (structured evidence, five
    # transformation operators, distinctness, per-candidate
    # mechanism-level verification) — first-class stage output
    "mechanism_space",
    "prior_art_ids", "prior_art",
    "collision_results",
    # R397 Phase 2: the PHYSICS stage verdict block (first-class stage
    # between COLLISION and ATTACK — lifecycle-affecting, not a report)
    "physics",
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
    premise_gate: Dict[str, Any] = field(default_factory=dict)
    evidence_classification: Dict[str, Any] = field(default_factory=dict)
    # R401: the structured mechanism space stage output
    mechanism_space: Dict[str, Any] = field(default_factory=dict)
    prior_art_ids: List[str] = field(default_factory=list)
    prior_art: Dict[str, Any] = field(default_factory=dict)
    collision_results: Dict[str, Any] = field(default_factory=dict)
    physics: Dict[str, Any] = field(default_factory=dict)
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

        R6 A1 stage memoization (owner round 2026-11-12): when the cache
        store is enabled (FABRIC_LLM_CACHE=rw|ro), a stage whose canonical
        upstream state (envelope snapshot, volatile stamps stripped, the
        stage's own code identity included) was already executed is served
        from the gitignored memo store with ZERO re-execution — the
        leave-one-out and A/B ablation arms recompute only the stages
        downstream of what actually changed. A memo hit is RECORDED
        (memo_hit=true on the stage_log entry, an events.jsonl line) — never
        a silent reuse (Art. XXV). Memo misses execute the normal path; the
        replay contract (unrecorded LLM calls fail typed in ro mode) is
        enforced at the flavor-transport layer, not here.
        """
        before = self.envelope_hash()
        # A1: memo lookup BEFORE any execution (zero spend on a hit)
        _memo_key: Optional[str] = None
        if _econ.cache_mode() != "off":
            try:
                _fn_src = inspect.getsource(getattr(fn, "__func__", fn))
            except (OSError, TypeError):
                _fn_src = None  # un-sourceable fn: no memo for this stage
            if _fn_src is not None:
                _snap = {k: getattr(self, k) for k in ENVELOPE_FIELDS
                         if k != "stage_log"}
                _memo_key = _econ.stage_memo_key(
                    stage_name, capability_id, module_path, fn_name,
                    _fn_src, _econ.strip_volatile(_snap))
                _memo = _econ.stage_memo_lookup(_memo_key)
                if _memo is not None:
                    return self._apply_memo_hit(
                        stage_name, capability_id, module_path, fn_name,
                        before, _memo_key, _memo)
        # Monotonic high-resolution stage timing (dry-run performance
        # measurement; Art. LXXXIII funnel durations). ADDITIVE ONLY:
        # started_at/finished_at provenance timestamps are unchanged.
        _mono_start = time.perf_counter()
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
                "duration_monotonic_s": time.perf_counter() - _mono_start,
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
            "duration_monotonic_s": time.perf_counter() - _mono_start,
            "after_envelope_hash": after,
            "candidate_delta": delta_keys,
            "delta_real": after != before,
            "result_meta": result_meta,
        })
        self.stage_log.append(entry)
        # A1 record: the stage's apply_to + result_meta are memoized under
        # the canonical upstream key (rw mode only; only successful
        # executions are recorded)
        if _memo_key is not None and isinstance(result, dict) \
                and result.get("_engine_result") is True:
            _econ.stage_memo_put(_memo_key, {
                "apply_to": result.get("apply_to") or {},
                "result_meta": {
                    k2: v2 for k2, v2 in result_meta.items()
                    if k2 != "raw_return_type"}})
        return entry

    def _apply_memo_hit(self, stage_name: str, capability_id: str,
                        module_path: str, fn_name: str, before: str,
                        memo_key: str, memo: Dict[str, Any]) -> Dict[str, Any]:
        """Restore a memoized stage output: apply the recorded apply_to
        block, compute the delta keys mechanically (the same rule as the
        live path) and log the entry with memo_hit=true — the reuse is
        recorded, never silent (Art. XXV)."""
        _t0 = time.perf_counter()
        applied = memo.get("apply_to") or {}
        delta_keys: List[str] = []
        for k, v in applied.items():
            before_val = canonical_json(getattr(self, k))
            setattr(self, k, copy.deepcopy(v))
            if canonical_json(getattr(self, k)) != before_val:
                delta_keys.append(k)
        after = self.envelope_hash()
        entry: Dict[str, Any] = {
            "stage": stage_name,
            "capability_id": capability_id,
            "module_path": module_path,
            "function": fn_name,
            "started_at": utc_now(),
            "before_envelope_hash": before,
            "status": "OK",
            "finished_at": utc_now(),
            "duration_monotonic_s": time.perf_counter() - _t0,
            "after_envelope_hash": after,
            "candidate_delta": delta_keys,
            "delta_real": after != before,
            "result_meta": memo.get("result_meta") or {},
            "memo_hit": True,
            "memo_key": memo_key[:16],
        }
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
