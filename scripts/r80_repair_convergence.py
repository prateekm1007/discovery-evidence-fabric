#!/usr/bin/env python3
"""R80 DEV prototype (AM79 roadmap P2, c-0105-pattern DEV lane): repair-loop
CONVERGENCE layer — Reflexion-style verbal reflection MEMORY (noahshinn/
reflexion, MIT; see NOTICE.md) + Self-Refine-style structured STOP criterion
(madaan/self-refine, Apache-2.0), copied as PATTERNS (our own code, the
papers' mechanisms, no upstream bytes).

Defect class attacked (measured, typed, never hidden): the repair loop burns
its full budget without converging — v10 27/30 = 90%, v11 26/30 = 86.7%
full-budget burn (the AM78-P2 concern, confirmed on fresh sealed rows). The
frozen loop (scripts/r40_machine_v77.py, REPAIR_BUDGET = 3) rebuilds the
SAME neutral directive from the SAME findings every attempt and carries no
memory between attempts.

This module is NON-FROZEN and zero-LLM: it provides the mechanics
(signature -> memory -> enriched directive -> structured stop) for (a) the
CI-wired deterministic acceptance tests, (b) the matched-budget DEV ablation
harness. The FROZEN-SIDE wiring is a typed next step (a frozen edit under
the CI-gated re-freeze discipline) — not done silently here (Art. 5).

Ethics unchanged: every directive quote-back stays NEUTRAL and findings-
based (the machine's own rule); no outcome feedback, no judge signal, no
hidden repair assistance beyond the disclosed findings themselves.
"""
from __future__ import annotations

import hashlib
import json
from typing import Iterable

# ---------------------------------------------------------------- signature


def _attempt_problems(attempt: dict) -> list[str]:
    """The typed problems an attempt exposed — the union of the disclosed
    findings, the critic/type-gate verdicts (when not CLEAN) and the scan
    violations. Deterministic, order-insensitive."""
    out: list[str] = []
    if attempt.get("critic_verdict") not in (None, "CLEAN"):
        out.append(f"critic={attempt['critic_verdict']}")
    tg = attempt.get("type_gate") or {}
    if tg.get("verdict") == "MISMATCH":
        out.append(f"type_gate={tg.get('reason')}")
    for k, v in (attempt.get("scan") or {}).items():
        out.extend(f"scan={k}:{x}" for x in v)
    out.extend(str(x) for x in (attempt.get("findings_disclosed") or []))
    dc = attempt.get("direction_check")
    if isinstance(dc, dict) and dc.get("verdict") not in (None, "CLEAN"):
        out.append(f"direction={dc.get('verdict')}")
    return sorted(str(p) for p in out if p)


def failure_signature(attempt: dict) -> str:
    """A stable hash of the attempt's problem set — the Reflexion
    'failure signature' used for the stop criterion and the memory key."""
    probs = _attempt_problems(attempt)
    blob = json.dumps(probs, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def signature_improved(prev: dict, curr: dict) -> bool:
    """True iff the current attempt's problem set is a STRICT subset-problem
    (strictly fewer problems than the previous attempt). The stop criterion
    NEVER stops an improving sequence (safety property, CI-tested)."""
    return len(_attempt_problems(curr)) < len(_attempt_problems(prev))


# ------------------------------------------------------------------ lessons

# The residual taxonomy is the MEASURED one (v11 committed rows: the
# residual_finding_keys histogram; the burn is dominated by BILL_UNTAGGED).
LESSONS: dict[str, str] = {
    "BILL_UNTAGGED":
        "every numeric quantity in the answer must carry an explicit unit "
        "and a tagged bill line; an untagged quantity is a finding",
    "APPARATUS_ROW":
        "each apparatus item must map to exactly one bill row with its own "
        "quantity and basis; no shared or lumped rows",
    "PHYSICS_DIRECTION_UNSTATED":
        "state the expected direction of change (increase/decrease) of "
        "every governing variable explicitly, with the physical reason",
    "DIRECTION_CHECK_UNAVAILABLE":
        "when a direction check is unavailable, state the direction from "
        "first principles and flag it as first-principles-only",
    "DEV_NEED":
        "a demand/need statement must accompany every proposed "
        "intervention; an intervention without a need is a finding",
    "REASONING_THRASH_LEAK":
        "deliver the final answer only; internal deliberation, "
        "alternatives and self-correction chatter must not leak into the "
        "delivered text",
    "PREDICTOR_VIOLATION":
        "a predictor-design answer must not prescribe interventions; it "
        "states leading indicators, thresholds and observation windows only",
    "UNPRICED_DUTY_CYCLE":
        "price every duty cycle explicitly (load factor, idle periods, "
        "start/stop transients); an unpriced duty cycle is a finding",
    "INVERTED_EQUILIBRIUM":
        "check the claimed chemical direction against the computed "
        "equilibrium; an inverted direction is a typed kill",
    "STATED_REACTION_ELEMENT_PHANTOM":
        "every element in a stated reaction product must trace to a "
        "source species; phantom elements are typed kills",
}


def lesson_for(problems: Iterable[str]) -> list[str]:
    """The corrective lesson lines for the classes named in the problems
    (matching by class token inside the problem string)."""
    seen: list[str] = []
    for p in problems:
        for cls, text in LESSONS.items():
            if cls in p and text not in seen:
                seen.append(text)
    return seen


# ----------------------------------------------------------------- reflexion


class ReflectionMemory:
    """Verbal self-reflection memory carried ACROSS repair attempts
    (the Reflexion pattern): each non-improving attempt contributes its
    failure signature + the lesson lines; the next attempt's directive
    quotes the accumulated memory back neutrally."""

    def __init__(self) -> None:
        self.entries: list[dict] = []

    def observe(self, attempt: dict) -> dict | None:
        """Record an attempt; returns the entry only when it taught
        something NEW (a signature not seen before)."""
        sig = failure_signature(attempt)
        if any(e["signature"] == sig for e in self.entries):
            return None
        probs = _attempt_problems(attempt)
        entry = {"signature": sig, "problems": probs,
                 "lessons": lesson_for(probs)}
        self.entries.append(entry)
        return entry

    def note(self) -> str:
        """The verbal reflection note for the next attempt's directive —
        neutral, findings-quoted-back, no outcome feedback."""
        if not self.entries:
            return ""
        lines = []
        for e in self.entries:
            lessons = e["lessons"] or [
                "re-derive the answer from the stated findings"]
            lines.append("- still open: " + "; ".join(e["problems"][:4])
                         + " -> " + " ".join(lessons[:2]))
        return ("PRIOR-ATTEMPT REFLECTION (quoted findings, neutral): "
                + " | ".join(lines))


def build_repair_directive(problems: Iterable[str], memory: ReflectionMemory,
                           base_template: str,
                           base_findings_field: str = "findings") -> str:
    """The enriched repair directive: the caller's OWN base template (the
    frozen machine keeps its directive template — passed in, never
    duplicated here) + the reflection memory appended when non-empty."""
    findings = "; ".join(p for p in problems if p)
    base = base_template.format(**{base_findings_field: findings}) \
        if "{findings}" in base_template else base_template
    note = memory.note()
    return base + ("\n\n" + note if note else "")


# -------------------------------------------------- structured stop (Self-Refine)


def should_stop(attempts: list[dict], budget: int = 3) -> bool:
    """Self-Refine's structured STOP criterion, typed conservatively: stop
    only when the LATEST attempt reproduced EXACTLY the previous attempt's
    failure signature (same problem set — the repair provably added no new
    information and the identical directive was already quoted back once).
    NEVER stops: on the draft attempt, on an empty problem set (that is
    convergence, not a stop), or when the signature improved (fewer or
    different problems — the repair is still learning)."""
    if len(attempts) < 2:
        return False
    last, prev = attempts[-1], attempts[-2]
    if not _attempt_problems(last):
        return False
    if signature_improved(prev, last):
        return False
    return failure_signature(last) == failure_signature(prev)


# ------------------------------------------------------------ loop harness


def run_loop(row_model, budget: int = 3, convergence: bool = False) -> dict:
    """A deterministic, zero-LLM repair-loop simulation for tests and the
    DEV ablation. row_model(attempt_index, memory_note) -> (attempt dict,
    done: bool). Returns repairs-to-done and whether the budget burned."""
    memory = ReflectionMemory()
    attempts: list[dict] = []
    note = memory.note() if convergence else ""
    for i in range(budget + 1):
        att, _done = row_model(i, note)
        attempts.append(att)
        if not _attempt_problems(att):
            break  # converged — the machine's clean-at-delivery path
        if convergence:
            memory.observe(att)
            if should_stop(attempts, budget):
                break
        note = memory.note() if convergence else ""
    converged = bool(attempts and not _attempt_problems(attempts[-1]))
    # the machine's own semantics (the v11 ledger): repairs = attempts - 1
    repairs_used = len(attempts) - 1
    return {"repairs_used": repairs_used, "attempts": len(attempts),
            "converged": converged,
            "budget_burned_full": (repairs_used == budget and not converged),
            "memory_entries": len(memory.entries) if convergence else 0}
