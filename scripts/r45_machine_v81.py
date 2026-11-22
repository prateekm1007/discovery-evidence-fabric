#!/usr/bin/env python3
"""r45_machine_v81.py — the V8.1.3 MACHINE (the R120 Art. 20 remainder
strip, claim c-0178 re-scoped @ b4b2cf694): the V8.1.2 population
machine reduced to the R121 SUCCESSOR SHAPE — the same shape 78a4a57d3
landed for machine_generate_v79 (one bare authoring call + the frozen
bind CHECK layer + findings surfaced for a bare reviewer).

RETIRED AND DELETED from this machine (the F30 + F31a typed negatives;
two Art. 20 rounds lost):
  - the AM42 D2 candidate population (>=3 TRIZ-seeded mechanistically
    distinct candidates, best-first selection) and the D2 TRIZ seeding
    (the scripts/triz_principles shim — deleted in this change),
  - the autonomous repair loop (V81_REPAIR_DIRECTIVE regeneration,
    REPAIR_BUDGET 3) — the F31a damage gate failed it (a net-zero
    rewriter: it healed 4 clean bills and broke 4), the R121
    adjudication retired the rewrite point.
What remains (the delivered contract unchanged: (final, attempts,
final_meta); attempts carries exactly ONE entry):
  - ONE PLAIN authoring call (the problem JSON only — no candidate
    directive, no population ceremony),
  - the UNCHANGED deterministic battery (every V8.0 intervention scan
    + the D1 computed-physics layer, scripts/v81_physics.py),
  - critic + type gate + the LLM direction check,
  - the findings SURFACED in final_meta (residual_findings +
    stop_reason FINDINGS_SURFACED_FOR_REVIEWER) for a bare reviewer —
    the machine CHECKS, it does not rewrite.
Predictors keep the frozen V8.0 path unchanged (a historical
instrument; its own retirement is not this entry). The historical
v8.1 run records (eval/v81_run/, eval/v81_run_voided_v81_defect/) are
committed bytes — never rewritten, Art. 4."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r43_machine_v8 import (  # noqa: E402
    machine_generate_v8, base_scan, critic, scan_physics_direction,
    scan_allowed_measures_class, scan_conversion, scan_operational_loss,
    scan_standard_bill, scan_constraint_fit, direction_check_llm,
    _retry_call, _gen_fb, scan_candidate_classes_v8,
    scan_input_availability_v8, scan_duty_pricing_v8,
    scan_mechanism_class_v8, direction_lexicon_check,
    gate_question_type, counted_class, counted_template,
    contract_for_v8, scan_predictor_direction_v8, scan_catalog_v8,
    MACHINE_DESCRIPTOR as V80_DESCRIPTOR)
from v81_physics import scan_computed_physics  # noqa: E402

MACHINE_DESCRIPTOR = {
    "machine": "V8.1.3",
    "base": "V8.0 (r43_machine_v8, frozen) + AM42 D1 computed-physics "
            "layer (scripts/v81_physics.py); the AM42 D2 population "
            "search with TRIZ seeding RETIRED AND DELETED and the "
            "autonomous repair loop RETIRED (Art. 20 — the F30 + F31a "
            "typed negatives; the R121 adjudication, claim c-0178 "
            "re-scoped @ b4b2cf694)",
    "request_model": "glm-4-plus",
    "direction_llm": "delivered candidate only",
    "v81_1_fix": "candidate-plan enumeration dedupes INSIDE the loop "
                 "(always exactly 3 distinct (class, principle) "
                 "plans); the V8.1 attempt produced cands=2 on its "
                 "first row (HO8-01) — that run was stopped and its "
                 "single row VOIDED-BUILD-DEFECT "
                 "(eval/v81_run_voided_v81_defect/)",
    "v81_2_fix": "D1 computed-physics degenerate-input hardening: all "
                 "five relations return typed out_of_domain notes "
                 "instead of raising, and the Arrhenius exponent is "
                 "saturated beyond the double range — the V8.1.1 "
                 "unclamped math.exp crashed the transport "
                 "(OverflowError: math range error) on the first "
                 "resume attempt when a row text carried a near-zero "
                 "absolute temperature; in the sane regime the values "
                 "are bit-identical (rows 1-8 unaffected)",
    "v81_3_strip": "the D2 candidate population (k_candidates=3, the "
                   "TRIZ seeding, best-first selection) and the "
                   "autonomous repair loop retired: the machine "
                   "authors ONE plain bill, the bind battery CHECKS "
                   "it, the findings surface for a bare reviewer — "
                   "the R121 successor shape (78a4a57d3 is the v79 "
                   "twin of this strip); the population records in "
                   "eval/v81_run/ keep their history",
}


def _battery(prob: dict, final: str, qt: str,
             used_templates: Counter | None) -> dict:
    """The deterministic battery (NO direction-LLM): every V8.0
    intervention scan + the D1 computed-physics scan. UNCHANGED by the
    strip — the binds are the kept layer."""
    vio: dict = {}
    vio.update(base_scan(final))
    vio.update(scan_constraint_fit(prob, final))
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
    vio.update(direction_lexicon_check(prob, final))
    vio.update(scan_candidate_classes_v8(final))
    vio.update(scan_input_availability_v8(prob, final))
    vio.update(scan_duty_pricing_v8(final))
    vio.update(scan_mechanism_class_v8(final, used_templates))
    vio.update(scan_computed_physics(prob, final))
    return {k: v for k, v in vio.items() if v}


def machine_generate_v81(prob: dict, gw_key: str,
                         used_templates: Counter | None = None):
    """The V8.1.3 machine (bare + binds-check, the R121 successor
    shape). Returns (final, attempts, final_meta) in the frozen
    machine's shape; attempts carries exactly ONE entry (the plain
    authoring, 'authored'); the findings surface in final_meta for a
    bare reviewer — no autonomous repair, no population."""
    qt = (prob.get("question_type") or "").lower()
    if qt.startswith("predictor"):
        # the frozen V8.0 predictor path, unchanged (a historical
        # instrument; D5 conformal is later-round work)
        final, attempts, final_meta = machine_generate_v8(
            prob, gw_key, used_templates)
        return final, attempts, final_meta

    q = json.dumps(prob, ensure_ascii=False)
    contract = contract_for_v8(qt)
    # ONE PLAIN authoring call (the R120/R121 strip): the problem JSON
    # only — no candidate directive, no population ceremony, no repair
    final, gen_meta = _retry_call(_gen_fb, q, contract, gw_key)
    vio: dict = {}
    vio.update(_battery(prob, final, qt, used_templates))
    cr = _retry_call(critic, final, prob)
    tg = gate_question_type(final, prob)
    dc = direction_check_llm(prob, final, gw_key)
    if dc["direction"] == "INVERTED":
        vio["PHYSICS_DIRECTION_INVERTED"] = [
            f"the sign/integral check reads the mechanism "
            f"INVERTED: {dc.get('reason', '')[:160]}"]
    elif dc["direction"] == "UNCLEAR":
        vio["DIRECTION_UNPROVEN"] = [
            "the sign/integral check cannot judge the direction "
            "from the bill — state the governing relation and the "
            "sign the mechanism imposes"]
    elif dc["direction"] == "DIRECTION_CHECK_UNAVAILABLE":
        vio["DIRECTION_CHECK_UNAVAILABLE"] = [
            f"typed fail-open: {dc.get('reason', '')[:120]} "
            "(the authoritative read stays the auditor's)"]
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
    att = {"stage": "authored",
           "chars": len(final),
           "latency_s": round(gen_meta["latency_s"], 1),
           "transport_tries": gen_meta.get("tries", 1),
           "route": gen_meta.get("route"),
           "route_model": gen_meta.get("model"),
           "critic_verdict": cr["verdict"], "type_gate": tg,
           "scan": {k: list(v) for k, v in vio.items()},
           "direction_check": dc,
           "sha256_16": __import__("hashlib").sha256(
               final.encode()).hexdigest()[:16]}
    surfaced = [p for p in problems if p]
    if surfaced:
        att["findings_disclosed"] = surfaced
    final_meta = {"critic_verdict": cr["verdict"],
                  "type_gate": tg, "repairs": 0,
                  "direction_check": dc,
                  "residual_findings":
                      {k: list(v) for k, v in vio.items()},
                  "stop_reason": ("CONVERGED_ZERO_FINDINGS"
                                  if not surfaced else
                                  "FINDINGS_SURFACED_FOR_REVIEWER")}
    return final, [att], final_meta


__all__ = ["machine_generate_v81", "_battery", "MACHINE_DESCRIPTOR"]
