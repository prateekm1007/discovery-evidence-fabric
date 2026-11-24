#!/usr/bin/env python3
"""r145s1 v17 SEALED one-shot — DIR-2 (TOP) + DIR-3: the sealed
validation of the generation-strength kit.

DISCIPLINE (typed): the delegated owner SEALED v17 (V111; the prereg
V17_SEALED_PREREG/1.0.0 at the audit tip babbaedd0cb5 — 30 fresh
problems across the 10 failure classes, the rubrics in PRIVATE custody
prateekm1007/def-rubric-custody:v17_sealed_rubrics.json, digest
1db1539e935038db, NEVER read by the builder). The three earlier
generation arms (eval/holdout_v17_generation/ rows/ + rows_pre_
inspiration/ + rows_inspiration_arm/) ran on the PRE-SEAL candidate
problem set (different domains — rail-shelling/choke-erosion/...) and
stand as DEV evidence, committed and never deleted (Art. 4). THIS is
the sealed one-shot on the OWNER's sealed bytes: one generation, burn
after (Art. 7/29(c)).

The strength kit wired into the authoring prompt per problem (the
engine/generation modules, one source of truth):
  1. generation.mechanism_map: classify_failure -> MechanismSelection
     (typed failure class + allowed mechanism classes + off-target
     rejections) and mechanism_prompt_block (the constraint block: the
     mechanism MUST use a mapped class, the prediction + falsification
     test REQUIRED);
  2. generation.quant_test: emit_prediction for the first mapped
     mechanism class that has a deterministic pint formula (the
     running unit-checked computation riding the prompt; typed
     no-formula/insufficient-parameters notes elsewhere — never
     invented numbers);
  3. generation.inspiration_retrieval: retrieve_inspiration +
     inspiration_prompt_block (the MOOSE-Chem-style cross-domain
     precedents; typed empty when none);
  4. the quantitative-testability + novelty-strength binds (the
     R144-F1 fix — the candidate runs measured their absence: kill
     conditions 2/30);
  5. the machine's landed scans stay live (scan_quantitative_
     testability -> QUANT_TEST_MISSING / PHYSICS_MAGNITUDE_MISSING;
     scan_off_target) — findings surfaced in final_meta, never a
     silent gate.
Post-hoc per row: generation.novelty_gate.gate(answer, selection)
recorded as the builder screen INPUT (never the verdict, Art. 14).

agnes-3.0-flash pinned; problem-only; byte-resume per row; the raw
rows commit with the run (Art. 18/22). The scoring is the AUDITOR's
act (PENDING-AUDITOR-SCORE, Art. 10/14).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r97_v12_one_shot as r97  # noqa: E402  (the v12 machine + the
# landed scans inside machine_generate_v79)
import r40_machine_v77 as m77  # noqa: E402
from discovery_fabric.generation import mechanism_map as mm  # noqa: E402
from discovery_fabric.generation import quant_test as qt  # noqa: E402
from discovery_fabric.generation import (  # noqa: E402
    inspiration_retrieval as ir)
from discovery_fabric.generation import novelty_gate as ng  # noqa: E402

OUT = REPO / "eval" / "holdout_v17_sealed_generation"
OUT.mkdir(exist_ok=True)
EXECUTOR_ID = os.environ.get(
    "V17_EXECUTOR_ID", "builder-r145s1@holdout-v17-sealed-generation")
AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
PROBLEMS_AUDIT_PATH = "eval/holdout_v17/problems.json"
MODEL_PIN = "agnes-3.0-flash"

MACHINE_RECORD = (
    "r145_v17_sealed_one_shot/1.0.0 — the SEALED one-shot (V111 "
    "prereg): the owner's 30-problem 10-failure-class set from the "
    "audit-branch bytes, problem-only, agnes-3.0-flash pinned; the "
    "FULL strength kit in the authoring prompt (mechanism_map "
    "constraint block + quant_test engine prediction where "
    "computable + inspiration precedents + the quantitative-"
    "testability and novelty-strength binds) and the machine's "
    "landed scans live; the scoring is the delegated owner's act "
    "(the private rubrics, digest 1db1539e935038db, never read by "
    "the builder). One generation, burn after.")


def _git_show_audit(path: str) -> str:
    out = subprocess.run(["git", "show", f"{AUDIT_REF}:{path}"],
                         capture_output=True, text=True)
    assert out.returncode == 0, (
        f"the sealed problems are unreadable at {AUDIT_REF} "
        f"(typed abort): {out.stderr[:200]}")
    return out.stdout


def load_sealed_problems() -> list:
    raw = json.loads(_git_show_audit(PROBLEMS_AUDIT_PATH))
    probs = raw.get("problems") if isinstance(raw, dict) else raw
    assert isinstance(probs, list) and len(probs) == 30, (
        f"expected 30 sealed problems, got {len(probs) if probs else 0}")
    # the sealed-bytes digest is typed in the run record (Art. 7:
    # counts from bytes)
    import hashlib
    digest16 = hashlib.sha256(
        json.dumps(probs, sort_keys=True, ensure_ascii=False)
        .encode()).hexdigest()[:16]
    reg_model = r97.route_adapter.ROUTE_REGISTRY["registered"]["model"]
    assert reg_model == MODEL_PIN, (
        f"the route registry's registered id is {reg_model!r} but "
        f"the instrument serves {MODEL_PIN!r} (typed abort)")
    mapped = []
    for p in probs:
        mapped.append({
            "problem_id": p["problem_id"],
            "domain": p.get("domain", ""),
            "device": "(stated in the problem)",
            "failure": str(p.get("problem", "")).strip(),
            "failure_mode": str(p.get("problem", "")).strip()[:120],
            "question": ("What engineering change, intervention, or "
                         "design would prevent or mitigate the stated "
                         "failure? Invent the mechanism."),
            "question_type": "invention",
            "user_variables": [],
            "constraint": "",
            "contamination_tag": "V17_SEALED",
            "_sealed_digest16": digest16,
        })
    return mapped, digest16


def _gateway_key() -> str:
    k = os.environ.get("ZAI_API_KEY")
    if not k:
        env_keys = REPO / ".env.keys"
        if env_keys.exists():
            for line in env_keys.read_text().splitlines():
                if line.startswith("ZAI_API_KEY="):
                    k = line.split("=", 1)[1].strip()
                    break
    return k or ""


def main() -> int:
    probs, sealed_digest16 = load_sealed_problems()
    print(f"v17 SEALED: {len(probs)} problems | digest {sealed_digest16}"
          f" | model pin {MODEL_PIN} | the full strength kit",
          flush=True)
    events = []
    ledger_path = OUT / "GENERATION_EVENTS.json"
    if ledger_path.exists():
        events = json.loads(
            ledger_path.read_text()).get("events", [])
    done = skipped = 0
    t0 = time.time()
    for idx, prob in enumerate(sorted(probs,
                                      key=lambda p: p["problem_id"]), 1):
        pid = prob["problem_id"]
        outp = OUT / f"{pid}.json"
        if outp.exists():  # byte-resume, same generation
            skipped += 1
            continue
        row_wall_start = time.time()
        print(f"=== v17-sealed {pid} ({idx}/30) ...", flush=True)
        problem_text = prob["failure"]
        sel = mm.classify_failure(problem_text)
        mprompt = mm.mechanism_prompt_block(problem_text)
        # the engine-side prediction leg: the first mapped mechanism
        # class that has a deterministic pint formula. The problem text
        # rarely carries the numeric inputs, so the HONEST shape is the
        # required-inputs manifest (the measurement plan the invention
        # must NAME and estimate) — the formula itself is computed by
        # the auditor-side recompute from the row's own numbers, never
        # invented here (Art. 9: no fabricated inputs).
        import inspect
        eng_pred = {"status": "no_formula_for_class",
                    "note": ("typed: no deterministic formula for the "
                             "mapped classes — the invention carries "
                             "the first-principles estimate (the "
                             "prediction is still REQUIRED)")}
        for mech in sel.allowed_mech_classes:
            if mech in qt.FORMULAS:
                fn = qt.FORMULAS[mech]
                required = [pname for pname, prm in
                            inspect.signature(fn).parameters.items()
                            if prm.default is inspect.Parameter.empty]
                eng_pred = {
                    "status": "parameters_required",
                    "mech_class": mech,
                    "formula": getattr(fn, "__name__", str(fn)),
                    "required_inputs": required,
                    "pint_unit_checked": True,
                    "note": ("typed: the deterministic pint-checked "
                             "formula for this mechanism class needs "
                             "these inputs — the invention MUST name "
                             "the measurement plan and the estimated "
                             "values for each (typed assumptions "
                             "allowed, Art. 9), and state the "
                             "prediction the formula computes"),
                }
                break
        insp = ir.retrieve_inspiration(sel.failure_class)
        row_out = r97.engine_route.run_row(prob)
        winner, wresult, rule = r97.v10m.select_winner(row_out)
        machine_prob = r97.v10m.challenger_prob(prob, winner, rule)
        machine_prob["typed_plan"]["failure_class"] = sel.failure_class
        machine_prob["typed_plan"]["mechanism_selection_block"] = mprompt
        machine_prob["typed_plan"]["engine_prediction"] = eng_pred
        machine_prob["typed_plan"]["inspiration"] = {
            "block": ir.inspiration_prompt_block(insp),
            "typed": insp.get("typed"),
        }
        machine_prob["typed_plan"]["quantitative_testability_bind"] = {
            "worked_calculation": (
                "the invention MUST carry ONE worked numeric "
                "calculation on its governing relation: inputs WITH "
                "units (problem-stated, stock datasheet, or a TYPED "
                "ASSUMPTION 'assumed: X because Y'), one substitution, "
                "one numeric result WITH unit"),
            "falsifiable_prediction": (
                "the invention MUST carry ONE falsifiable numeric "
                "prediction: the measurable quantity, its expected "
                "direction and magnitude with units, and the "
                "observation window"),
            "kill_condition": (
                "the invention MUST state its own KILL CONDITION "
                "(Art. 12): 'the mechanism is falsified if <metric> "
                "does not change by at least <N><unit> within "
                "<window>'"),
        }
        machine_prob["typed_plan"]["novelty_strength_bind"] = (
            "the departure from standard practice must be a NON-OBVIOUS "
            "arrangement with a stated physical reason the obvious "
            "knob fails here; the generic moves (increase/reduce flow, "
            "modulate pressure, add monitoring, insulate more, add a "
            "filter or a schedule) are NOT a mechanism when they are "
            "the whole departure — put the novelty in the arrangement")
        trace = r97.v10m.engine_trace(prob, row_out, winner, wresult,
                                      rule)
        trace["strength_kit"] = {
            "failure_class": sel.failure_class,
            "confidence": sel.confidence,
            "evidence_span": sel.evidence_span,
            "allowed_mech_classes": list(sel.allowed_mech_classes),
            "engine_prediction_status": eng_pred.get("status"),
            "engine_prediction_mech_class": eng_pred.get("mech_class"),
            "inspiration_analogies_n": len(insp.get("analogies") or []),
            "inspiration_spans_n": len(insp.get("evidence_spans") or []),
            "winner_measure_class": winner.get("measure_class"),
            "winner_rule": rule,
        }
        t_row = r97._now()
        final, attempts, final_meta = r97.machine_generate_v79(
            machine_prob, _gateway_key(), used_templates={})
        gate = ng.gate(final, sel)
        row_wall_s = round(time.time() - row_wall_start, 1)
        decl = m77.declared_template(final)
        row = {
            "problem_id": pid,
            "domain": prob.get("domain"),
            "question_type": prob.get("question_type"),
            "executor_id": EXECUTOR_ID,
            "registered_model": MODEL_PIN,
            "machine": MACHINE_RECORD,
            "run": "holdout-v17-sealed-generation (the SEALED one-shot, "
                   "problem-only, the full strength kit)",
            "sealed_problems_digest16": sealed_digest16,
            "engine_trace": trace,
            "generated_at": t_row,
            "attempts_n": len(attempts),
            "row_wall_s": row_wall_s,
            "a1_answer": final,
            "final_meta": {
                "critic_verdict": final_meta.get("critic_verdict"),
                "type_gate": final_meta.get("type_gate"),
                "repairs": final_meta.get("repairs"),
                "stop_reason": final_meta.get("stop_reason"),
                "residual_findings": final_meta.get(
                    "residual_findings"),
                "findings_disclosed": final_meta.get(
                    "findings_disclosed"),
                "novelty_gate": gate,
            },
            "declared_template_prose": decl,
            "sha256_16": r97._sha16(final),
        }
        outp.write_text(json.dumps(row, indent=1, ensure_ascii=False)
                        + "\n", encoding="utf-8")
        events.append({
            "problem_id": pid, "generated_at": t_row,
            "row_wall_s": row_wall_s, "attempts": len(attempts),
            "final_sha256_16": row["sha256_16"],
            "final_chars": len(final),
            "failure_class": sel.failure_class,
            "engine_prediction_status": eng_pred.get("status"),
            "novelty_gate": gate.get("novelty"),
            "residual_findings": sorted(
                (final_meta.get("residual_findings") or {}).keys()),
        })
        ledger_path.write_text(json.dumps({
            "record": "HOLDOUT_V17_SEALED_GENERATION_EVENTS/1.0.0",
            "run": "holdout-v17-sealed-generation",
            "executor_id": EXECUTOR_ID,
            "registered_model": MODEL_PIN,
            "sealed_problems_digest16": sealed_digest16,
            "events": events}, indent=1) + "\n")
        done += 1
        print(f"{pid}: wall {row_wall_s}s chars {len(final)} "
              f"class={sel.failure_class} "
              f"pred={eng_pred.get('status')} "
              f"novelty={gate.get('novelty')} "
              f"({done} done, {skipped} resumed)", flush=True)
    print(f"v17 SEALED generation: {done} generated, {skipped} resumed, "
          f"{round(time.time() - t0, 1)}s wall", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
