#!/usr/bin/env python3
"""r45_machine_v81.py — the V8.1 MACHINE (AM42 D1+D2 adoption, claim
c-0065): the frozen V8.0 machine (r43_machine_v8, BYTE-UNTOUCHED and
retired with Art. 16 accounting) transformed per the owner's
delete-list:
  - single-chain repair -> POPULATION SEARCH: every intervention gets
    >=3 mechanistically distinct candidate drafts (PHASE 1), each
    mapped to a DISTINCT TRIZ principle and a DISTINCT counted class
    (>=1 non-duty-cycle — the F54 frontier), best-first selected by
    the deterministic bind battery + the D1 computed-physics layer
    (PHASE 2), then the SELECTED candidate enters the frozen
    repair-budget loop (PHASE 3) — the candidate population is
    generation, the repair loop stays the frozen contract-compliance
    mechanism.
  - LLM-asserted magnitudes -> COMPUTED: scan_computed_physics
    (scripts/v81_physics.py) joins the battery in both phases; a
    COMPUTED_PHYSICS_INCONSISTENT candidate is scored down and a
    repair finding otherwise.
  - predictors keep the frozen V8.0 path unchanged (D5 conformal is
    later-round work).
Direction-LLM legs run ONLY on the selected candidate (quota
discipline; the deterministic battery governs selection)."""
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
from triz_principles import (  # noqa: E402
    PRINCIPLES, seed_for, distinct_principles, DUTY_CYCLE_FAMILY_RX)

REPAIR_BUDGET = 3

V81_REPAIR_DIRECTIVE = (
    "REPAIR — the same problem, fixing EXACTLY these findings and "
    "nothing else (keep everything that passed):\n{findings}\n"
    "Deliver the full answer again (all required sections), with the "
    "findings resolved and every number still labeled USER "
    "CONSTRAINT, CALCULATED, or ASSUMPTION.")

V81_CANDIDATE_DIRECTIVE = (
    "CANDIDATE PLAN {i}/3 (population search — AM42 D2):\n"
    "TARGET MECHANISM CLASS: {cls}\n"
    "TRIZ PRINCIPLE: #{pid} — {pname}. Your mechanism must "
    "Instantiate this principle explicitly and name it.\n"
    "POPULATION BIND: this candidate competes on deterministic bind "
    "cleanliness against two other mechanistically distinct "
    "candidates; obey every contract bind, declare the target "
    "MECHANISM CLASS line exactly, and give the PHYSICS CHECK with "
    "EXPLICIT number+unit inputs (temperature in K or degC, energies "
    "in kJ/mol, pressures in kPa, times in hours) so the computed "
    "physics layer can verify your magnitude from your own inputs.")

MACHINE_DESCRIPTOR = {
    "machine": "V8.1.1",
    "base": "V8.0 (r43_machine_v8, frozen) + AM42 D1 computed-physics "
            "layer (scripts/v81_physics.py) + D2 population search "
            "with TRIZ seeding (scripts/triz_principles.py)",
    "request_model": "glm-4-plus",
    "k_candidates": 3,
    "repair_budget": REPAIR_BUDGET,
    "direction_llm": "selected candidate only",
    "v81_1_fix": "candidate-plan enumeration dedupes INSIDE the loop "
                 "(always exactly 3 distinct (class, principle) "
                 "plans); the V8.1 attempt produced cands=2 on its "
                 "first row (HO8-01) — that run was stopped and its "
                 "single row VOIDED-BUILD-DEFECT "
                 "(eval/v81_run_voided_v81_defect/)",
}


def _candidate_plans(prob: dict) -> list:
    """Three (class, principle_id) plans: the TRIZ seed first, then
    distinct alternates; classes distinct, principles distinct, >=1
    non-duty-cycle (the F54 frontier). Deterministic."""
    text = json.dumps(prob, ensure_ascii=False)
    seed_principles, seed_cls = seed_for(text)
    plans = []
    if seed_principles and seed_cls:
        plans.append((seed_cls, seed_principles[0]))
    from triz_principles import CONTRADICTION_MAP
    # dedupe INSIDE the loop (the V8.1.1 fix): the seed duplicate and
    # any repeat never occupy one of the three plan slots, so the
    # enumeration always yields exactly 3 distinct (class, principle)
    # plans — V8.1's pre-dedupe break could leave 2 (caught on the
    # first V8.1 row, HO8-01: cands=2; the run was stopped and the
    # single row VOIDED-BUILD-DEFECT; the machine bumped V8.1.1)
    seen = set(plans)
    used_cls = {cls for cls, _ in plans}
    used_pids = {pid for _, pid in plans}
    for rx, principles, cls in CONTRADICTION_MAP:
        if len(plans) >= 3:
            break
        if DUTY_CYCLE_FAMILY_RX.search(cls.lower()):
            continue
        if cls in used_cls:
            # mechanistic distinctness: one plan per class — a family
            # whose class is already seeded never contributes a second
            # same-class plan (V8.1.1: distinct CLASSES and distinct
            # principles across the three plans)
            continue
        # prefer a principle not already used by another plan (the
        # distinct-principles bind): families thermal-load and
        # efficiency both lead with 35; if every principle of this
        # family is already used, its first is taken (class
        # distinctness wins; the residual is disclosed in the row's
        # population facts)
        for pid in principles:
            if pid not in used_pids:
                used_pids.add(pid)
                seen.add((cls, pid))
                plans.append((cls, pid))
                break
        else:
            seen.add((cls, principles[0]))
            plans.append((cls, principles[0]))
        used_cls.add(cls)
    return plans[:3]


def _battery(prob: dict, final: str, qt: str,
             used_templates: Counter | None) -> dict:
    """The deterministic battery (NO direction-LLM): every V8.0
    intervention scan + the D1 computed-physics scan."""
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


def _score(vio: dict, final: str) -> tuple:
    """Best-first score (smaller wins): findings, duty penalty,
    computed penalty (a CONSISTENT computed check scores -1)."""
    n = len(vio)
    duty = 1 if any(DUTY_CYCLE_FAMILY_RX.search(k.lower()) or
                    "MONOCULTURE" in k for k in vio) else 0
    comp = 1 if "COMPUTED_PHYSICS_INCONSISTENT" in vio else (
        -1 if "COMPUTED_PHYSICS_CONSISTENT" in vio else 0)
    return (n, duty, comp)


def select_best(candidates: list, used_templates: Counter | None) -> dict:
    """Deterministic best-first: min score; ties broken by computed
    consistency then candidate order. The diversity cap is already
    enforced inside the battery (scan_mechanism_class_v8 with the
    in-run histogram)."""
    scored = sorted(candidates,
                    key=lambda c: (c["score"], c["computed_ok"],
                                   c["index"]))
    return scored[0]


def machine_generate_v81(prob: dict, gw_key: str,
                         used_templates: Counter | None = None):
    """The V8.1 machine. Returns (final, attempts, final_meta) in the
    frozen machine's shape (the driver/verifier contract is
    unchanged); attempts carries the population phase as stage
    'cand_1..3' then the repair loop as 'draft'/'repair_N'."""
    qt = (prob.get("question_type") or "").lower()
    if qt.startswith("predictor"):
        # the frozen V8.0 predictor path, unchanged (D5 conformal is
        # later-round work)
        final, attempts, final_meta = machine_generate_v8(
            prob, gw_key, used_templates)
        return final, attempts, final_meta

    q = json.dumps(prob, ensure_ascii=False)
    contract = contract_for_v8(qt)
    plans = _candidate_plans(prob)
    attempts: list = []
    candidates: list = []
    for i, (cls, pid) in enumerate(plans, 1):
        directive = V81_CANDIDATE_DIRECTIVE.format(
            i=i, cls=cls, pid=pid,
            pname=PRINCIPLES.get(pid, "unnamed principle"))
        final, gen_meta = _retry_call(
            _gen_fb, q + "\n\n" + directive, contract, gw_key)
        vio = _battery(prob, final, qt, used_templates)
        score = _score(vio, final)
        candidates.append({
            "index": i - 1, "final": final, "cls": cls, "pid": pid,
            "vio": vio, "score": score,
            "computed_ok": (0 if "COMPUTED_PHYSICS_INCONSISTENT" in vio
                            else (1 if "COMPUTED_PHYSICS_CONSISTENT"
                                  in vio else 0)),
            "latency_s": gen_meta["latency_s"],
            "tries": gen_meta.get("tries", 1),
            "route": gen_meta.get("route"),
            "route_model": gen_meta.get("model")})
        attempts.append({
            "stage": f"cand_{i}", "chars": len(final),
            "latency_s": round(gen_meta["latency_s"], 1),
            "route": gen_meta.get("route"),
            "route_model": gen_meta.get("model"),
            "target_class": cls, "triz_principle": pid,
            "scan": {k: list(v) for k, v in vio.items()},
            "score": score,
            "sha256_16": __import__("hashlib").sha256(
                final.encode()).hexdigest()[:16]})
    if not candidates:
        raise RuntimeError("no candidate plans enumerated (typed)")
    best = select_best(candidates, used_templates)
    final = best["final"]
    lat = best["latency_s"]
    tries = best["tries"]
    gen_meta = {"route": best["route"], "model": best["route_model"]}
    rep = 0
    final_meta = {}
    while True:
        cr = _retry_call(critic, final, prob)
        tg = gate_question_type(final, prob)
        vio: dict = {}
        vio.update(_battery(prob, final, qt, used_templates))
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
        att = {"stage": ("draft" if rep == 0 else f"repair_{rep}"),
               "chars": len(final), "latency_s": round(lat, 1),
               "transport_tries": tries,
               "route": gen_meta.get("route"),
               "route_model": gen_meta.get("model"),
               "selected_from": f"cand_{best['index'] + 1}",
               "critic_verdict": cr["verdict"], "type_gate": tg,
               "scan": {k: list(v) for k, v in vio.items()},
               "direction_check": dc,
               "sha256_16": __import__("hashlib").sha256(
                   final.encode()).hexdigest()[:16]}
        if rep:
            att["findings_disclosed"] = [p for p in problems if p]
        attempts.append(att)
        if not [p for p in problems if p]:
            final_meta = {"critic_verdict": cr["verdict"],
                          "type_gate": tg, "repairs": rep,
                          "direction_check": dc,
                          "population": {
                              "n_candidates": len(candidates),
                              "selected": f"cand_{best['index'] + 1}",
                              "target_class": best["cls"],
                              "triz_principle": best["pid"],
                              "candidate_scores":
                                  [c["score"] for c in candidates]},
                          "residual_findings": {}}
            return final, attempts, final_meta
        if rep == REPAIR_BUDGET:
            final_meta = {"critic_verdict": cr["verdict"],
                          "type_gate": tg, "repairs": rep,
                          "direction_check": dc,
                          "population": {
                              "n_candidates": len(candidates),
                              "selected": f"cand_{best['index'] + 1}",
                              "target_class": best["cls"],
                              "triz_principle": best["pid"],
                              "candidate_scores":
                                  [c["score"] for c in candidates]},
                          "residual_findings":
                              {k: list(v) for k, v in vio.items()}}
            return final, attempts, final_meta
        directive = V81_REPAIR_DIRECTIVE.format(
            findings="; ".join(p for p in problems if p))
        final, gen_meta = _retry_call(
            _gen_fb, q + "\n\n" + directive, contract, gw_key)
        lat = gen_meta["latency_s"]
        tries = gen_meta.get("tries", 1)
        rep += 1


__all__ = ["machine_generate_v81", "select_best", "_candidate_plans",
           "_battery", "_score", "MACHINE_DESCRIPTOR"]
