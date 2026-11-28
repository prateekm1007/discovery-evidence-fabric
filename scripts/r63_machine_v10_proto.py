#!/usr/bin/env python3
"""r63_machine_v10_proto.py — the V10 REPAIR-LOOP PROTOTYPE (claim c-0086,
plan layer, auditor Finding 1 / direction 7).

THE MEASURED BASIS (the V8.1 pre-run census at b8117977d, 9/9 rows):
every row burned the full repair budget (repairs=3) and 6/9 rows still
ended critic=FLAG — "no row converges; repairs ~ negative value" (the
auditor's Finding 1). The mechanism is visible in r40_machine_v77.py:
the repair pass appends the FULL static directive stack
(V76_REPAIR_DIRECTIVE.rstrip() + the four V7.7 clauses) to the ORIGINAL
question and regenerates the ENTIRE bill. Three defects follow:
  (a) UNTARGETED: the model re-rolls the whole answer; findings it
      already fixed can regress (churn), findings it cannot fix from a
      prose list stay unfixed;
  (b) NO CONVERGENCE DETECTION: nothing compares attempt N's finding
      set to attempt N-1's — a stuck axis keeps burning budget;
  (c) NO VALUE ACCOUNTING: nothing measures whether repair N reduced
      the violation load, so the loop cannot stop when marginal value
      <= 0 — the "repairs ~ negative value" tail.

THE V10 STRATEGY (this prototype, plan layer):
  1. TARGETED DIRECTIVES: findings map to per-finding remediation
     binds (each names its clause and quotes the offending anchor) and
     carry a byte-keep constraint: sections NOT named by a finding
     stay byte-identical — the rewrite is an edit, not a re-roll.
  2. CONVERGENCE GUARD: the finding SIGNATURE (normalized finding-key
     set) is compared across attempts; an identical signature two
     consecutive attempts is a STUCK AXIS -> typed EARLY_STOP with
     residual disclosure (never budget burn).
  3. VALUE LEDGER: each attempt records violations_n / critic_flags_n
     and the delta vs the previous attempt; two consecutive
     value-zero-or-worse repairs -> EARLY_STOP (the marginal-value
     rule, typed — never budget tuning).
  4. BUDGET UNCHANGED: REPAIR_BUDGET_V10 = REPAIR_BUDGET = 3, imported
     from the frozen machine — the guard does the work.

FREEZE DISCIPLINE: the V7.7 loop (r40_machine_v77.py) stays FROZEN for
the v9 one-shot — this module imports it BYTE-REUSED (the budget
constant and the scan stack) and defines the v10 strategy as a NEW,
stub-drivable loop; nothing here can affect the sealed instrument.
ZERO LLM PROBES: gen_fn/critic_fn/direction_fn are injected — the
offline tests drive stubs; the real wiring happens only after the 429
window clears (direction 1).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Callable, Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

# ---- byte-reused frozen machinery (imported, never modified) ----
from r40_machine_v77 import REPAIR_BUDGET  # noqa: E402
from r40_machine_v77 import (  # noqa: E402  (byte-reuse proof targets)
    scan_duty_cycle_pricing, scan_input_availability,
    scan_mechanism_template)

REPAIR_BUDGET_V10 = REPAIR_BUDGET  # the budget is NOT the mechanism

# ---- the real deterministic scan stack, composed once ----
from r22_a1w_v5_repair import scan as base_scan  # noqa: E402
from r24_constraint_scan import scan_constraint_fit  # noqa: E402
from r26_catalog_scan import scan_catalog  # noqa: E402
from r27_standard_bill_scan import scan_standard_bill  # noqa: E402
from r29_conversion_scan import scan_conversion  # noqa: E402
from r29_operational_loss_scan import scan_operational_loss  # noqa
from r30_allowed_class_scan import (  # noqa: E402
    scan_allowed_measures_class)
from r30_physics_direction_scan import (  # noqa: E402
    scan_physics_direction)


def v10_scan_stack(prob: dict, final: str,
                   used_templates: Optional[Counter] = None) -> dict:
    """The REAL scan composition of the frozen loop, factored into one
    injectable callable (mirrors r40_machine_v77.py's per-attempt scan
    block, interventions branch). The tests stub gen/critic but run
    THIS — the scans are the production bytes."""
    qt = (prob.get("question_type") or "").lower()
    vio: dict = {}
    vio.update(base_scan(final))
    vio.update(scan_constraint_fit(prob, final))
    if not qt.startswith("predictor"):
        vio.update(scan_catalog(prob, final))
        sb = scan_standard_bill(final, qt)
        if sb:
            vio.update(sb)
        ol = scan_operational_loss(final, qt)
        if ol:
            vio.update(ol)
        cv = scan_conversion(final, qt, prob)
        if cv:
            vio.update(cv)
        vio.update(scan_allowed_measures_class(prob, final))
        vio.update(scan_physics_direction(prob, final))
        vio.update(scan_input_availability(prob, final))
        vio.update(scan_duty_cycle_pricing(final))
        vio.update(scan_mechanism_template(final, used_templates))
    else:  # pragma: no cover — the set is interventions only
        from r19_a1w_v4_contract import predictor_violations
        pv = predictor_violations(final)
        if pv:
            vio.update({"PREDICTOR_VIOLATION": list(pv)})
        vio.update(scan_input_availability(prob, final))
    return vio


# ---- per-finding remediation binds (real keys from the real scans) ----
_V10_BINDS: Dict[str, str] = {
    "PHYSICS_DIRECTION_INVERTED":
        "the mechanism is INVERTED: replace the mechanism (different "
        "physics), never reword the claim — state the governing "
        "relation, the sign your ingredient imposes, and why the sign "
        "lowers the damage integral",
    "DIRECTION_UNPROVEN":
        "state the governing relation and the sign the mechanism "
        "imposes, in the PHYSICS CHECK section",
    "PHYSICS_DIRECTION_UNSTATED":
        "the PHYSICS CHECK section is missing the signed statement: "
        "name the driving quantity and the sign your mechanism imposes",
    "DIRECTION_INVERTED_ARITHMETIC":
        "the arithmetic sign of the stated relation is inverted — fix "
        "the relation's direction, not the wording",
    "DRIVER_AS_REMEDY":
        "the bill's active ingredient IS the failure's driver — replace "
        "the mechanism with physics of the OPPOSITE sign",
    "INPUT_UNAVAILABLE":
        "a required online input is not among the permitted measures — "
        "re-choose the mechanism so every required input is derivable "
        "from what the constraint permits; do not invent instrumentation",
    "UNPRICED_DUTY_CYCLE":
        "the bill modulates a setpoint/duty cycle without pricing it: "
        "add the OPERATIONAL COST line (what is given up, an "
        "order-of-magnitude bound, why the trade nets positive)",
    "UNPRICED_OPERATIONAL_LOSS":
        "an operational loss is introduced without its OPERATIONAL COST "
        "line — price the loss explicitly",
    "MECHANISM_CLASS_UNSTATED":
        'open the bill with "MECHANISM CLASS: <one phrase>"',
    "MECHANISM_TEMPLATE_MONOCULTURE":
        "the mechanism class repeats beyond the set cap — deliver a "
        "DIFFERENT mechanism class",
    "ALLOWED_MEASURE_TYPE_OUTSIDE":
        "a measure outside the constraint's permitted types is used — "
        "replace it with a permitted measure",
    "ALLOWED_LIST_OUTSIDE":
        "an action outside the constraint's allowed list is used — "
        "replace it with a listed action",
    "ALLOWED_ROW_OUTSIDE":
        "a catalog row outside the constraint's allowed list is used — "
        "replace it with a listed row",
    "CONSTRAINT_EXCLUSION":
        "the bill violates a named constraint exclusion — remove the "
        "excluded element",
    "STANDARD_BILL":
        "the STANDARD BILL carries a bespoke component/recipe — replace "
        "it with the catalog-standard alternative",
    "BESPOKE_COMPONENT":
        "a bespoke component is specified — replace with the "
        "catalog-standard part",
}


def finding_signature(vio: dict, critic_flags: List[str],
                      gate_mismatch: bool) -> frozenset:
    """The normalized finding-key set of one attempt (the convergence
    object: keys only — messages rephrase, keys recur)."""
    keys = {k for k, v in vio.items() if v}
    keys.update(f"CRITIC::{a}" for a in critic_flags)
    if gate_mismatch:
        keys.add("GATE::MISMATCH")
    return frozenset(keys)


def targeted_directive(vio: dict, critic_flags: List[str],
                       gate_mismatch: bool) -> str:
    """The v10 repair prompt: PER-FINDING binds with anchors + the
    byte-keep constraint. Replaces the full-stack re-quote."""
    lines: List[str] = ["REPAIR PASS (targeted — fix ONLY these):"]
    for k, v in sorted(vio.items()):
        if not v:
            continue
        bind = _V10_BINDS.get(k)
        if bind is None and k.startswith("CRITIC::"):
            bind = None  # critic anchors handled below
        detail = "; ".join(map(str, v))[:160]
        if bind:
            lines.append(f"- {k}: {bind} (found: {detail})")
        else:
            lines.append(f"- {k}: fix this finding (found: {detail})")
    for a in critic_flags:
        lines.append(f"- CRITIC anchor {a}: rewrite the passage it "
                     "names to answer the check it flags")
    if gate_mismatch:
        lines.append("- the answer's QUESTION TYPE does not match the "
                     "row's question_type: re-answer the asked question "
                     "kind")
    lines.append(
        "BYTE-KEEP CONSTRAINT: every section, line and clause NOT named "
        "by a finding above stays BYTE-IDENTICAL to the current answer; "
        "edit only the named parts. Do not restate the whole bill.")
    return "\n".join(lines)


def value_ledger_entry(prev: Optional[dict], vio: dict,
                       critic_flags: List[str],
                       gate_mismatch: bool) -> dict:
    """The per-repair value record: load + delta. A repair whose
    violation load does not DROP is value-zero-or-worse."""
    load = len([k for k, v in vio.items() if v]) + len(critic_flags) \
        + (1 if gate_mismatch else 0)
    e = {"violations_n": load,
         "critic_flags_n": len(critic_flags),
         "value_delta": None if prev is None
         else load - prev["violations_n"]}
    return e


def repair_guard(prev_sig: Optional[frozenset], ledger: dict,
                 prev_ledger: Optional[dict]) -> str:
    """The convergence rule (typed, not tuned):
    - identical signature on two consecutive attempts -> STUCK_AXIS
      (one repair pass changed NOTHING in the finding set)
    - two consecutive value-zero-or-worse repairs -> NO_MARGINAL_VALUE
      (delta of the previous attempt >= 0 AND of this attempt >= 0)
    - otherwise CONTINUE (until REPAIR_BUDGET_V10)."""
    if prev_sig is not None and ledger.get("sig") == prev_sig:
        return "EARLY_STOP:STUCK_AXIS"
    if (prev_ledger is not None
            and prev_ledger.get("value_delta") is not None
            and prev_ledger["value_delta"] >= 0
            and ledger.get("value_delta") is not None
            and ledger["value_delta"] >= 0):
        return "EARLY_STOP:NO_MARGINAL_VALUE"
    return "CONTINUE"


def machine_generate_v10_proto(
        prob: dict,
        gen_fn: Callable[[str], str],
        critic_fn: Callable[[str], dict],
        gate_fn: Callable[[str, dict], dict],
        direction_fn: Optional[Callable[[str, dict, str], dict]] = None,
        scans_fn: Callable[[dict, str, Optional[Counter]], dict]
        = v10_scan_stack,
        used_templates: Optional[Counter] = None):
    """The v10 loop skeleton (strategy injected, machinery byte-reused).

    gen_fn(question)->answer; critic_fn(answer)->{"verdict","checks"};
    gate_fn(answer,prob)->{"verdict",...}; direction_fn is the LLM
    direction check (None in offline mode — the deterministic
    scan_physics_direction still runs inside scans_fn).
    Returns (final, attempts, final_meta) — the frozen loop's shape."""
    q = json.dumps(prob, ensure_ascii=False)
    attempts: List[dict] = []
    final = gen_fn(q)
    prev_sig: Optional[frozenset] = None
    prev_ledger: Optional[dict] = None
    rep = 0
    while True:
        cr = critic_fn(final)
        tg = gate_fn(final, prob)
        vio = scans_fn(prob, final, used_templates)
        critic_flags = [c.get("anchor") for c in (cr.get("checks") or [])
                        if c.get("verdict") != "CLEAN"]
        gate_mismatch = tg.get("verdict") == "MISMATCH"
        sig = finding_signature(vio, critic_flags, gate_mismatch)
        ledger = value_ledger_entry(prev_ledger, vio, critic_flags,
                                    gate_mismatch)
        ledger["sig"] = sig
        attempts.append({
            "stage": ("draft" if rep == 0 else f"repair_{rep}"),
            "critic_verdict": cr.get("verdict"),
            "type_gate": tg,
            "scan": {k: list(v) for k, v in vio.items() if v},
            "sig_size": len(sig),
            "value": {k: v for k, v in ledger.items() if k != "sig"},
        })
        if not sig:
            return final, attempts, {
                "critic_verdict": cr.get("verdict"), "type_gate": tg,
                "repairs": rep, "residual_findings": {},
                "convergence": "CLEAN"}
        guard = repair_guard(prev_sig, ledger, prev_ledger)
        if guard.startswith("EARLY_STOP"):
            return final, attempts, {
                "critic_verdict": cr.get("verdict"), "type_gate": tg,
                "repairs": rep,
                "residual_findings": {k: list(v)
                                      for k, v in vio.items() if v},
                "convergence": guard.split(":", 1)[1],
                "value_ledger": ledger}
        if rep >= REPAIR_BUDGET_V10:
            return final, attempts, {
                "critic_verdict": cr.get("verdict"), "type_gate": tg,
                "repairs": rep,
                "residual_findings": {k: list(v)
                                      for k, v in vio.items() if v},
                "convergence": "BUDGET_EXHAUSTED",
                "value_ledger": ledger}
        final = gen_fn(q + "\n\n"
                       + targeted_directive(vio, critic_flags,
                                            gate_mismatch))
        prev_ledger = ledger
        prev_sig = sig
        rep += 1


__all__ = ["machine_generate_v10_proto", "v10_scan_stack",
           "finding_signature", "targeted_directive",
           "value_ledger_entry", "repair_guard", "REPAIR_BUDGET_V10"]
