#!/usr/bin/env python3
"""aide_tree_search/1.0.0 — the AIDE tree-search controller (claim
c-0110; AM82 direction 2; the R92 roadmap's convergence-gap leg).

THE MEASURED GAP (committed bytes, not prose): the c-0106 ablation
typed the repair loop's failure mode as prompt-refractory on the
structural BILL_UNTAGGED class and showed reflection memory alone
cannot zero it (NOT_ADOPTED: zero-residual 6.67% vs 13.33% incumbent,
mean attempts 3.97 vs 3.8). The roadmap's named next leverage after
tool-grounding is AIDE tree search — attack the convergence gap with
DIVERSITY, not just memory: a best-first POPULATION search over
diverse repair candidates, metric-pruned, instead of the single-chain
repair loop that burns its budget on one chain.

THE PATTERN COPY (WecoAI/aideml, MIT — NOTICE.md; zero upstream code
bytes, the upstream implementation is an agent framework): draft +
improve nodes in a tree, parent sampled best-first by a trusted
metric, weak branches pruned, refinement budget concentrated on the
best frontier. Here the TRUSTED METRIC is the machine's OWN finding
surface (the scan battery + critic + type gate the frozen loop
already computes — nothing new is judged, no rubric information
flows anywhere); the candidates are the repair slots' outputs; the
pruning is metric-only.

DESIGN INVARIANTS (typed, CI-tested in
tests/test_r95_aide_tree_search.py):
  1. BUDGET-MATCHED: the controller adds ZERO LLM calls — the repair
     slots are exactly the incumbent's (draft + REPAIR_BUDGET=3);
     next_slot() returns None once the budget is used; it can only
     REDIRECT a slot's parent and angle, never add a slot.
  2. BEST-FIRST parent selection: each slot refines the live node
     with the LOWEST metric (residual finding count, critic verdict,
     type-gate verdict — lexicographic); ties break to the LATEST
     node (greedy refinement, the AIDE journal ordering).
  3. METRIC-PRUNED population: after every node the live frontier is
     pruned to the top-K nodes by metric (K=2: best + latest); every
     pruned node stays in the trajectory with a typed pruned_reason
     (the record is the audit surface — Art. 5: never hidden).
  4. DIVERSE ANGLES: each slot carries a DISTINCT structural repair
     angle from the roster (process-only instructions — the same
     vocabulary the machine's own scans already produce; no outcome
     feedback, no judged numbers, no rubric information). An angle
     never repeats within a row while unused angles remain.
  5. INCUMBENT PARITY: population=False reduces EXACTLY to the
     frozen single chain — parent is always the latest node, no
     angle text exists, the node sequence is the incumbent chain
     n0->n1->n2->n3 (the c-0106 invariant-7 pattern; the ablation's
     single-variable proof at the controller level).
  6. DETERMINISM: node metrics are canonical (sorted-key JSON
     digests, sha256_16 — Art. 15: no hash-order containers, no
     wall-clock bytes); the angle rotation is seeded from the
     problem key's CONTENT via sha256 (never Python hash()).
  7. >=3 DISTINCT CANDIDATES per intervention row when the budget is
     used: the trajectory records every node and the distinct-
     candidate count is computed from (signature, angle) pairs
     (the AM82 roadmap acceptance surface, CI-encoded).

COMPOSITION (typed): this controller does not replace the critic and
does not touch the frozen machine — the per-round driver composes it
AT THE DRIVER LEVEL (the r93 byte-mirror + insertion-point pattern).
TOOLS FIRST, TREE SECOND: the c-0109 corrector
(discovery_fabric/engine/tool_grounded_critic.py) mechanically
corrects a candidate BEFORE it is scored; the controller scores what
the driver hands it and stays agnostic to the tool leg (the CI
battery proves the composition on a mock).

Zero LLM, zero network, zero frozen bytes.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

RECORD = "AIDE_TREE_SEARCH/1.0.0"

# --- the diverse-angle roster (process-only structural strategies) -------
ANGLE_ROSTER: Tuple[str, ...] = (
    "ANGLE RESTRUCTURE: rebuild the flagged sections from scratch as "
    "compact rows, each carrying its required class tag; keep the "
    "mechanism statement verbatim in intent.",
    "ANGLE MINIMAL EDIT: keep the answer body untouched except for "
    "the smallest edits that clear the listed findings; no "
    "reorganization.",
    "ANGLE MECHANISM FIRST: state the governing relation and its sign "
    "in one opening line, then rebuild the flagged sections around "
    "that statement.",
    "ANGLE PARITY COMPRESS: compress every flagged section to "
    "standard-practice parity — procurable, minimal, tagged; delete "
    "speculative rows.",
)


def _sha16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def candidate_metric(scan: Optional[Dict[str, Any]],
                     critic_verdict: str,
                     type_gate_verdict: str) -> Tuple[int, int, int]:
    """The trusted metric — the machine's OWN finding surface,
    lexicographic (lower is better):
      (residual finding count, critic != CLEAN, type gate MISMATCH).
    A None scan is typed as an empty surface (converged candidate) —
    the driver passes the machine's scan battery dict per attempt."""
    findings_n = sum(1 for v in (scan or {}).values() if v)
    return (findings_n,
            0 if str(critic_verdict or "") == "CLEAN" else 1,
            1 if str(type_gate_verdict or "") == "MISMATCH" else 0)


def signature_digest(scan: Optional[Dict[str, Any]],
                     critic_verdict: str,
                     type_gate_verdict: str) -> str:
    """Canonical per-attempt signature (the sorted-key convention of
    the committed convergence work): finding keys with evidence
    counts + the two verdicts, sha256_16 over sorted-key compact
    JSON. Deterministic across hash seeds by construction."""
    evidence = sorted((k, len(list(v))) for k, v in (scan or {}).items()
                      if v)
    blob = json.dumps(
        {"keys_with_counts": [[k, n] for k, n in evidence],
         "critic": str(critic_verdict or ""),
         "type_gate": str(type_gate_verdict or "")},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return _sha16(blob)


class AideTreeSearch:
    """Per-row best-first population search over the repair slots.

    The driver interacts at exactly three points (the r93 controller
    convention):
      record_draft(...)   — the frozen loop's draft attempt (node n0);
      next_slot()         — before each repair slot: {slot, parent_id,
                            angle} (None = budget used; parity mode
                            carries angle=None);
      record_node(...)    — after each repair attempt's finding
                            surface is computed;
      trajectory()        — the committed record surface (Art. 5).
    """

    def __init__(self,
                 *,
                 budget: int = 3,
                 population: bool = True,
                 angles: Tuple[str, ...] = ANGLE_ROSTER,
                 seed_key: str = "",
                 frontier_k: int = 2) -> None:
        if budget < 0:
            raise ValueError("budget must be >= 0")
        if frontier_k < 1:
            raise ValueError("frontier_k must be >= 1")
        self.budget = int(budget)
        self.population = bool(population)
        self.angles = tuple(angles)
        self.seed_key = str(seed_key)
        self.frontier_k = int(frontier_k)
        self._nodes: List[Dict[str, Any]] = []
        self._slots_used = 0
        self._angle_cursor = self._seeded_start()
        self._closed = False

    # --- determinism: content-seeded angle rotation (never hash()) ------
    def _seeded_start(self) -> int:
        if not self.population:
            return 0
        return int(_sha16("aide-angles:" + self.seed_key), 16) % 8

    def _next_angle(self) -> Optional[str]:
        if not self.angles:
            return None
        idx = (self._angle_cursor + self._slots_used) % len(self.angles)
        return self.angles[idx]

    # --- node bookkeeping ------------------------------------------------
    def _live_frontier(self) -> List[Dict[str, Any]]:
        """Top-K live nodes by (metric asc, node order desc — latest
        wins ties). The frontier is the metric-pruned population."""
        ranked = sorted(
            enumerate(self._nodes),
            key=lambda t: (t[1]["metric"], -t[0]))
        return [n for _, n in ranked[:self.frontier_k]]

    def _best_node(self) -> Dict[str, Any]:
        """Best-first choice: the lowest-metric node; ties break to
        the LATEST (AIDE journal ordering) — the loop keeps the later
        candidate on an equal metric, so refinement concentrates on
        the freshest best frontier."""
        best = None
        for n in self._nodes:
            if (best is None or n["metric"] <= best["metric"]):
                best = n
        return best  # type: ignore[return-value]

    # --- driver surface ---------------------------------------------------
    def record_draft(self, *, scan: Optional[Dict[str, Any]],
                     critic_verdict: str,
                     type_gate_verdict: str) -> str:
        assert not self._nodes, "the draft is recorded exactly once"
        node = {
            "node_id": "n0", "slot": 0, "parent_id": None,
            "angle": None,
            "metric": list(candidate_metric(scan, critic_verdict,
                                            type_gate_verdict)),
            "signature": signature_digest(scan, critic_verdict,
                                          type_gate_verdict),
            "pruned": False, "pruned_reason": None,
        }
        self._nodes.append(node)
        return "n0"

    def next_slot(self) -> Optional[Dict[str, Any]]:
        """The next repair slot's redirect: which node to refine and
        which diverse angle to carry. None when the budget is used
        (invariant 1 — the controller only redirects, never adds)."""
        if not self._nodes or self._closed:
            return None
        if self._slots_used >= self.budget:
            return None
        if self.population:
            parent = self._best_node()
            angle = self._next_angle()
        else:
            parent = self._nodes[-1]
            angle = None
        return {"slot": self._slots_used + 1,
                "parent_id": parent["node_id"],
                "angle": angle}

    def record_node(self, *, slot: int, parent_id: str,
                    angle: Optional[str], scan: Optional[Dict[str, Any]],
                    critic_verdict: str,
                    type_gate_verdict: str) -> str:
        assert self._nodes, "record_draft first"
        assert slot == self._slots_used + 1, "slots are sequential"
        assert any(n["node_id"] == parent_id
                   for n in self._nodes), "parent must be a known node"
        node_id = f"n{len(self._nodes)}"
        node = {
            "node_id": node_id, "slot": int(slot),
            "parent_id": str(parent_id), "angle": angle,
            "metric": list(candidate_metric(scan, critic_verdict,
                                            type_gate_verdict)),
            "signature": signature_digest(scan, critic_verdict,
                                          type_gate_verdict),
            "pruned": False, "pruned_reason": None,
        }
        self._nodes.append(node)
        self._slots_used = int(slot)
        self._prune()
        return node_id

    def close(self) -> None:
        """Close the row's search (converged or budget exhausted):
        freezes the final selection = the best live node."""
        self._closed = True

    def _prune(self) -> None:
        live_ids = {n["node_id"] for n in self._live_frontier()}
        for n in self._nodes:
            if n["node_id"] not in live_ids and not n["pruned"]:
                n["pruned"] = True
                n["pruned_reason"] = "metric_pruned"

    # --- the committed record surface -------------------------------------
    def distinct_candidate_count(self) -> int:
        """Distinct candidates = distinct (signature, angle) pairs
        (two slots that produced identical finding surfaces from
        DIFFERENT angles are still distinct candidates — invariant
        7)."""
        pairs = {(n["signature"],
                  n["angle"] if n["angle"] is not None else "")
                 for n in self._nodes}
        return len(pairs)

    def trajectory(self) -> Dict[str, Any]:
        frontier = self._live_frontier()
        final = self._best_node()
        return {
            "schema": RECORD,
            "seed_key_digest": _sha16(self.seed_key),
            "budget": self.budget,
            "population": self.population,
            "frontier_k": self.frontier_k,
            "slots_used": self._slots_used,
            "budget_respected": self._slots_used <= self.budget,
            "angles_used": [n["angle"] for n in self._nodes
                            if n["angle"]],
            "nodes": [dict(n) for n in self._nodes],
            "live_frontier": [n["node_id"] for n in frontier],
            "final_node_id": final["node_id"] if final else None,
            "final_metric": list(final["metric"]) if final else None,
            "distinct_candidate_count": self.distinct_candidate_count(),
            "closed": self._closed,
        }


__all__ = [
    "RECORD",
    "ANGLE_ROSTER",
    "candidate_metric",
    "signature_digest",
    "AideTreeSearch",
]
