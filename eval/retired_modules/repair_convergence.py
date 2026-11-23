"""discovery_fabric/engine/repair_convergence.py — the repair-loop
CONVERGENCE CONTROLLER (R93, claim c-0104; the AM78-P2/P3 measured
defect class; the R92 roadmap's highest-leverage copy item).

THE MEASURED DEFECT (committed bytes, not prose):
  v10 run record (eval/r85_v10_run_record.json): repair budget
  distribution {3: 27, 2: 1, 1: 1, 0: 1} — 27/30 = 90% of rows burned
  the full repair budget without reaching zero findings.
  v11 events ledger (eval/holdout_v11_generation/events.json):
  repairs {1: 3, 2: 1, 3: 26} — 26/30 = 86.7% full-budget burn; the
  per-attempt signatures show finding keys PERSISTING across every
  repair (e.g. HO11-01: BILL_UNTAGGED present in draft, repair_1,
  repair_2 AND repair_3) while each repair re-receives only the
  CURRENT findings — the loop has no memory of what already failed
  and no stop criterion short of budget exhaustion.

THE PATTERN COPY (R92 roadmap integration discipline item 1:
attribution + NOTICE, see NOTICE.md):
  - Reflexion (noahshinn/reflexion, MIT): verbal self-reflection
    MEMORY that carries error patterns across attempts. Here: the
    per-row attempt history (which finding keys PERSISTED / were
    RESOLVED / are NEW since the previous attempt) is composed into a
    reflection addendum appended to the frozen repair directive from
    the second repair onward.
  - Self-Refine (madaan/self-refine, Apache-2.0): the structured STOP
    criterion — stop refining when the feedback signature stops
    changing, instead of burning the fixed budget on non-improving
    repairs. Here: when the finding signature is byte-identical
    across the stagnation window AND the latest attempt already
    carried the reflection addendum (the memory had its chance), the
    loop stops BEFORE budget exhaustion with a typed, disclosed
    stop_reason.
  No upstream code bytes are copied (both projects' implementations
  are agent-framework-specific); the PATTERNS are re-implemented
  against the frozen V7.7 loop's own finding surface (the scan-key
  signature), so the ablation against the incumbent is SINGLE
  VARIABLE: same scans, same critic, same contract, same directive —
  plus exactly two controller insertion points (the addendum and the
  stop check).

DESIGN INVARIANTS (typed, CI-tested in
tests/test_r93_repair_convergence.py):
  1. The FIRST repair prompt is byte-identical to the incumbent's
     (no addendum exists for a single-attempt history — reflection
     starts with something to reflect ON, i.e. from repair_2).
  2. Stagnation-stop fires ONLY when the identical signature survived
     a reflection-augmented repair (never on the first failure).
  3. The budget cap is never exceeded; stagnation-stop can only SAVE
     calls, never add them.
  4. Every stop carries a typed reason + the residual disclosure
     surface (Art. 3/5/23 — refusals and early stops are typed,
     never silent; residuals are disclosed, never hidden).
  5. The addendum is PROCESS feedback only (which keys persisted and
     the instruction to change the structural approach); it carries
     NO outcome feedback, no judged numbers, no rubric information
     (the machine convention: findings are quoted back, never
     adjudicated).
  6. Deterministic: signatures are sorted-key canonical JSON with a
     sha256_16 digest (Art. 15 — stable across hash seeds and
     wall-clock; no timestamps inside hashed inputs).
  7. INCUMBENT PARITY MODE: with reflection=False and
     stagnation_stop=False the controller's decisions reduce EXACTLY
     to the frozen V7.7 control flow (repair until zero findings or
     budget exhaustion; no addendum; no early stop) — the ablation's
     single-variable proof at the controller level.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

REPAIR_CONVERGENCE_SCHEMA = "repair_convergence/1.0.0"

__all__ = [
    "REPAIR_CONVERGENCE_SCHEMA",
    "findings_signature",
    "ConvergenceController",
]


def findings_signature(scan: Dict[str, Any],
                       critic_verdict: str,
                       type_gate_verdict: str) -> Dict[str, Any]:
    """The deterministic per-attempt finding signature.

    The signature is the SORTED set of violation keys that carry
    non-empty evidence — each with its evidence COUNT — plus the
    critic and type-gate verdicts: the exact finding surface the
    frozen loop already computes; nothing new is invented, only
    canonicalized. The per-key counts matter for stagnation
    honesty: a shrinking count within a persisting key class
    (5 untagged bill items -> 1) is IMPROVEMENT, not stagnation,
    and must change the digest. The digest is sha256_16 over the
    canonical JSON (sorted keys, compact separators — Art. 15:
    no hash-order containers, no wall-clock bytes).
    """
    evidence = sorted((k, len(list(v))) for k, v in (scan or {}).items()
                      if v)
    keys = [k for k, _ in evidence]
    blob = json.dumps(
        {"keys_with_counts": [[k, n] for k, n in evidence],
         "critic": str(critic_verdict or ""),
         "type_gate": str(type_gate_verdict or "")},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return {
        "keys": keys,
        "key_counts": {k: n for k, n in evidence},
        "critic": str(critic_verdict or ""),
        "type_gate": str(type_gate_verdict or ""),
        "digest": hashlib.sha256(blob.encode("utf-8"))
        .hexdigest()[:16],
        "schema": REPAIR_CONVERGENCE_SCHEMA,
    }


class ConvergenceController:
    """Per-row repair-loop convergence control.

    The driver (the loop executor) interacts at exactly three points:
      record(...)        — after each attempt's finding surface is
                           computed (the frozen loop's own scan
                           battery output);
      stop_decision()    — before composing the next repair (None =
                           continue);
      addendum()         — while composing the next repair prompt
                           (None = byte-identical incumbent prompt).

    Incumbent parity: reflection=False, stagnation_stop=False reduces
    to the frozen V7.7 control flow (design invariant 7).
    """

    def __init__(self,
                 *,
                 budget: int = 3,
                 stagnation_window: int = 2,
                 reflection: bool = True,
                 stagnation_stop: bool = True) -> None:
        if budget < 0:
            raise ValueError("budget must be >= 0")
        if stagnation_window < 2:
            raise ValueError("stagnation_window must be >= 2 "
                             "(a window of 1 would stop on the first "
                             "failure — design invariant 2)")
        self.budget = int(budget)
        self.stagnation_window = int(stagnation_window)
        self.reflection = bool(reflection)
        self.stagnation_stop = bool(stagnation_stop)
        self._history: List[Dict[str, Any]] = []
        self._addendum_pending: bool = False
        self._last_had_addendum: bool = False
        self._addendum_calls: int = 0

    # ------------------------------------------------------------------
    # history
    # ------------------------------------------------------------------
    @property
    def history(self) -> List[Dict[str, Any]]:
        """The recorded attempts (signatures; the finding texts stay
        with the driver's attempt records — the controller keeps only
        the canonical surface)."""
        return list(self._history)

    @property
    def last_had_addendum(self) -> bool:
        """Whether the prompt that produced the LATEST recorded
        attempt carried the reflection addendum (the stagnation-stop
        precondition — design invariant 2)."""
        return self._last_had_addendum

    def record(self, stage: str, scan: Dict[str, Any],
               critic_verdict: str, type_gate_verdict: str) -> Dict[
            str, Any]:
        """Record one evaluated attempt. Returns the signature (also
        appended to history)."""
        sig = findings_signature(scan, critic_verdict,
                                 type_gate_verdict)
        entry = {"stage": str(stage), **sig}
        self._history.append(entry)
        # the pending addendum (if any) belongs to the prompt that
        # produced THIS attempt
        self._last_had_addendum = self._addendum_pending
        self._addendum_pending = False
        return dict(entry)

    # ------------------------------------------------------------------
    # reflection memory (Reflexion pattern)
    # ------------------------------------------------------------------
    def _cross_attempt_analysis(self) -> Dict[str, List[str]]:
        """Persisted / resolved / new finding keys between the two
        most recent attempts."""
        if len(self._history) < 2:
            return {"persisted": [], "resolved": [], "new": []}
        prev, last = self._history[-2], self._history[-1]
        prev_keys, last_keys = set(prev["keys"]), set(last["keys"])
        return {
            "persisted": sorted(prev_keys & last_keys),
            "resolved": sorted(prev_keys - last_keys),
            "new": sorted(last_keys - prev_keys),
        }

    def addendum(self) -> Optional[str]:
        """The reflection-memory addendum for the NEXT repair prompt.

        None when reflection is disabled, when fewer than two attempts
        are recorded (the FIRST repair prompt stays byte-identical to
        the incumbent's — design invariant 1), or when there is
        nothing to reflect (no persisted, resolved or new keys).
        """
        if not self.reflection:
            return None
        if len(self._history) < 2:
            return None
        an = self._cross_attempt_analysis()
        if not (an["persisted"] or an["resolved"] or an["new"]):
            return None
        lines = [
            "REFLECTION MEMORY (process feedback from this row's "
            f"prior attempts; attempt {len(self._history)} recorded):"
        ]
        if an["persisted"]:
            lines.append(
                "- PERSISTED across the last repair — the previous "
                "fix wording did NOT remove these findings; do NOT "
                "rephrase the same sections, change the structural "
                "approach that produces them: "
                + ", ".join(an["persisted"]))
        if an["resolved"]:
            lines.append(
                "- RESOLVED since the previous attempt — keep the "
                "fix, do not reintroduce: "
                + ", ".join(an["resolved"]))
        if an["new"]:
            lines.append(
                "- NEW since the previous attempt — address per the "
                "directive above: " + ", ".join(an["new"]))
        lines.append(
            "For PERSISTED findings the same-shape repair has "
            "already failed at least once; take a structurally "
            "different approach to those sections.")
        self._addendum_pending = True
        self._addendum_calls += 1
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # stop criterion (Self-Refine pattern)
    # ------------------------------------------------------------------
    def stop_decision(self) -> Optional[Dict[str, Any]]:
        """The structured stop decision. None = continue repairing.

        STOP_STAGNATED fires only when (a) stagnation-stop is enabled,
        (b) the last `stagnation_window` signatures are identical,
        AND (c) the latest attempt already carried the reflection
        addendum (the memory had its chance — design invariant 2).
        """
        if not self.stagnation_stop:
            return None
        h = self._history
        if len(h) < self.stagnation_window:
            return None
        if not self._last_had_addendum:
            return None
        window = h[-self.stagnation_window:]
        digests = {w["digest"] for w in window}
        if len(digests) != 1:
            return None
        return {
            "action": "STOP_STAGNATED",
            "reason": "SIGNATURE_UNCHANGED_AFTER_REFLECTION",
            "schema": REPAIR_CONVERGENCE_SCHEMA,
            "stagnant_signature": window[-1]["digest"],
            "stagnant_keys": list(window[-1]["keys"]),
            "stagnant_critic": window[-1]["critic"],
            "stagnation_window": self.stagnation_window,
            "attempts_recorded": len(h),
            "disclosure": (
                "stopped before budget exhaustion: the identical "
                "finding signature survived a reflection-augmented "
                "repair; the remaining budget would repeat the same "
                "non-improving repair. Residual findings are "
                "disclosed in full (Art. 5/23); the delivery is the "
                "latest generation, never a best-of selection."),
        }

    # ------------------------------------------------------------------
    # budget guard + summary
    # ------------------------------------------------------------------
    def can_repair(self, repairs_used: int) -> bool:
        """Budget guard (design invariant 3): the loop may compose
        another repair only while repairs_used < budget AND no stop
        decision stands."""
        if repairs_used >= self.budget:
            return False
        return self.stop_decision() is None

    def summary(self) -> Dict[str, Any]:
        """The typed convergence summary for the row record."""
        an = self._cross_attempt_analysis()
        return {
            "schema": REPAIR_CONVERGENCE_SCHEMA,
            "mode": {
                "budget": self.budget,
                "stagnation_window": self.stagnation_window,
                "reflection": self.reflection,
                "stagnation_stop": self.stagnation_stop,
            },
            "attempts_recorded": len(self._history),
            "signatures": [
                {"stage": h["stage"], "digest": h["digest"],
                 "keys": list(h["keys"])}
                for h in self._history],
            "addendum_calls": self._addendum_calls,
            "last_had_addendum": self._last_had_addendum,
            "cross_attempt_analysis": an,
        }
