#!/usr/bin/env python3
"""r43_machine_v8.py — the V8 machine (claim c-0060, the R42 verdict
D1/D2/D5): the V7.7 path with the GENERATION binds and the
structured-extraction scans.

WHAT CHANGES VS V7.7 (everything else byte-carried):
  contract  : SYS_A1_INT_V72 -> SYS_A1_INT_V8 (the four generation
              binds M-P); SYS_A1F_V5 -> SYS_A1F_V8 (the input
              inventory + detection-framed direction binds Q-R).
  scans     : the free-prose input/measure regex hunting (the v7.7
              scan_input_availability over the mechanism span) is
              RETIRED and replaced by scan_input_availability_v8
              (SIGNALS USED / INPUT INVENTORY + the closure check);
              scan_duty_cycle_pricing -> scan_duty_pricing_v8 (the
              quantified-cost requirement; the phrase-only escape
              closed); scan_mechanism_template ->
              scan_mechanism_class_v8 (emphasis-stripped declaration,
              INFERRED classes counted toward the cap — F58); the
              r26 free-prose allowed-rows leg -> scan_allowed_rows_v8
              (structured head-object extraction); NEW
              scan_candidate_classes_v8 (D1a) and
              scan_predictor_direction_v8 (D5).
  histogram : the driver counts counted_class() — declared when
              present, INFERRED otherwise (an omitted declaration no
              longer escapes the diversity cap).

WHAT IS BYTE-CARRIED FROM V7.7: the transport (_gen_v77 + the NVIDIA
fallback chain, R-REQID glm-4-plus), the critic, the question-type
gate, the base/constraint-fit/standard-bill/operational-loss/
conversion/allowed-class(r30)/physics-direction(r30) scans, the
direction-lexicon check, the direction-LLM with the code-derived
verdict, REPAIR_BUDGET=3, K_GEN=1, judge-blind (no outcome feedback,
no judged numbers in any prompt).

The V7.7 machine file (r40_machine_v77.py) stays byte-frozen as the
instrument of record for the v7 run (Art. 4/16: superseded
implementations retired with accounting, never silently rewritten;
the v7 rows' scan recomputes cite it at the run SHAs).

The v8 one-shot itself waits for the auditor's sealed v8
preregistration (D3/D4); this module is built and calibrated on
burned/labelled bytes only (zero LLM calls in this claim).
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r40_machine_v77 import (  # noqa: E402
    _gen_fb, _retry_call, _sha, critic, direction_check_llm,
    direction_lexicon_check, V77_REQUEST_MODEL, start_gateway)
from r13_question_type_gate import gate_question_type  # noqa: E402
from r22_a1w_v5_repair import scan as base_scan  # noqa: E402
from r24_constraint_scan import scan_constraint_fit  # noqa: E402
from r26_catalog_scan import scan_apparatus, scan_named_variant  # noqa
from r27_standard_bill_scan import scan_standard_bill  # noqa: E402
from r29_operational_loss_scan import scan_operational_loss  # noqa
from r29_conversion_scan import scan_conversion  # noqa: E402
from r30_allowed_class_scan import scan_allowed_measures_class  # noqa
from r30_physics_direction_scan import scan_physics_direction  # noqa
from r43_v8_binds import (  # noqa: E402
    V8_REPAIR_DIRECTIVE, contract_for_v8, scan_candidate_classes_v8,
    scan_mechanism_class_v8, scan_duty_pricing_v8,
    scan_input_availability_v8, scan_allowed_rows_v8,
    scan_predictor_direction_v8, counted_class)

REPAIR_BUDGET = 3

MACHINE_DESCRIPTOR = {
    "machine": "V8.0",
    "base": "V7.7 (r40_machine_v77) with the R42-verdict generation "
            "binds (claims c-0060)",
    "request_model": V77_REQUEST_MODEL,
    "repair_budget": REPAIR_BUDGET,
    "k_gen": 1,
}


def scan_catalog_v8(prob: dict, a: str) -> dict:
    """The catalog scan with the structured allowed-rows leg (the
    r26 free-prose _added_spans hunt retired; the apparatus and
    named-variant legs byte-carried)."""
    out = {}
    for partial in (scan_allowed_rows_v8(prob, a),
                    scan_apparatus(a),
                    scan_named_variant(a)):
        out.update(partial)
    return out


def machine_generate_v8(prob: dict, gw_key: str,
                        used_templates: Counter | None = None):
    """The V8 machine: the V7.7 loop with the v8 scans and contract.
    used_templates is the driver-supplied histogram of the COUNTED
    classes (declared when present, inferred otherwise) already
    committed in this set — the cap binds against it (F58)."""
    qt = (prob.get("question_type") or "").lower()
    q = __import__("json").dumps(prob, ensure_ascii=False)
    contract = contract_for_v8(qt)
    attempts = []
    final, gen_meta = _retry_call(_gen_fb, q, contract, gw_key)
    lat = gen_meta["latency_s"]
    tries = 1
    final_meta = {}
    rep = 0
    while True:
        dc = None
        cr = _retry_call(critic, final, prob)
        tg = gate_question_type(final, prob)
        vio: dict = {}
        vio.update(base_scan(final))
        vio.update(scan_constraint_fit(prob, final))
        if not qt.startswith("predictor"):
            vio.update(scan_catalog_v8(prob, final))
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
            # ---- the byte-carried V7.7 checks ----
            vio.update(direction_lexicon_check(prob, final))
            # ---- the V8 generation binds (D1/D2) ----
            vio.update(scan_candidate_classes_v8(final))
            vio.update(scan_input_availability_v8(prob, final))
            vio.update(scan_duty_pricing_v8(final))
            vio.update(scan_mechanism_class_v8(final, used_templates))
            dc = direction_check_llm(prob, final, gw_key)
            if dc["direction"] == "INVERTED":
                vio["PHYSICS_DIRECTION_INVERTED"] = [
                    f"the sign/integral check reads the mechanism "
                    f"INVERTED: {dc.get('reason', '')[:160]}"]
            elif dc["direction"] == "UNCLEAR":
                vio["DIRECTION_UNPROVEN"] = [
                    "the sign/integral check cannot judge the "
                    "direction from the bill — state the governing "
                    "relation and the sign the mechanism imposes"]
            elif dc["direction"] == "DIRECTION_CHECK_UNAVAILABLE":
                vio["DIRECTION_CHECK_UNAVAILABLE"] = [
                    f"typed fail-open: {dc.get('reason', '')[:120]} "
                    "(the authoritative read stays the auditor's)"]
        else:
            from r19_a1w_v4_contract import predictor_violations
            pv = predictor_violations(final)
            if pv:
                vio.update({"PREDICTOR_VIOLATION": list(pv)})
            # ---- the V8 predictor binds (D2/D5) ----
            vio.update(scan_input_availability_v8(prob, final))
            vio.update(scan_predictor_direction_v8(final))
        findings = [f"{k}: {'; '.join(map(str, v))[:110]}"
                    for k, v in vio.items() if v]
        problems: list = []
        if cr["verdict"] != "CLEAN":
            problems += [c.get("anchor") for c in cr["checks"]
                         if c.get("verdict") != "CLEAN"]
        if tg["verdict"] == "MISMATCH":
            problems.append(tg["reason"])
        problems += findings
        if not (final or "").strip():
            problems.append("EMPTY_ANSWER_TRANSPORT")
        att = {"stage": ("draft" if rep == 0 else f"repair_{rep}"),
               "chars": len(final), "latency_s": round(lat, 1),
               "transport_tries": tries,
               "route": gen_meta.get("route"),
               "route_model": gen_meta.get("model"),
               "fallback_reason": gen_meta.get("fallback_reason"),
               "critic_verdict": cr["verdict"], "type_gate": tg,
               "scan": {k: list(v) for k, v in vio.items()},
               "direction_check": (dc if not qt.startswith("predictor")
                                   else None),
               "sha256_16": _sha(final)}
        if rep:
            att["findings_disclosed"] = [p for p in problems if p]
        attempts.append(att)
        if not [p for p in problems if p]:
            final_meta = {"critic_verdict": cr["verdict"],
                          "type_gate": tg, "repairs": rep,
                          "direction_check": dc,
                          "residual_findings": {}}
            return final, attempts, final_meta
        if rep == REPAIR_BUDGET:
            final_meta = {"critic_verdict": cr["verdict"],
                          "type_gate": tg, "repairs": rep,
                          "direction_check": dc,
                          "residual_findings":
                              {k: list(v) for k, v in vio.items()}}
            return final, attempts, final_meta
        directive = V8_REPAIR_DIRECTIVE.format(
            findings="; ".join(p for p in problems if p))
        final, gen_meta = _retry_call(
            _gen_fb, q + "\n\n" + directive, contract, gw_key)
        lat = gen_meta["latency_s"]
        tries += 1
        rep += 1


def counted_template(final: str) -> str:
    """The class the driver's set histogram counts for a committed
    row: declared (emphasis-stripped) when present, INFERRED
    otherwise — the F58 bind (an omitted declaration no longer
    escapes the diversity cap)."""
    return counted_class(final)


__all__ = ["machine_generate_v8", "counted_template",
           "scan_catalog_v8", "MACHINE_DESCRIPTOR",
           "V77_REQUEST_MODEL", "start_gateway", "contract_for_v8"]
