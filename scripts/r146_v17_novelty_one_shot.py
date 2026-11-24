#!/usr/bin/env python3
"""r146s1 v17 NOVELTY one-shot — DIR-2/3/6: the novelty-strength
engine measured on the SAME problem-only set, fresh rows.

Lane discipline (Art. 29(e), typed): this lane is the DISJOINT
follow-up the V112 verdict types as open ("novelty 13%<30%, mean
borderline; P4 rated v16 not v17; quant post-hoc"). It does NOT
duplicate any landed lever: the r144 one-shot (c-0245/c-0247) carried
the failure_physics + quantitative_testability + novelty_strength
binds; THIS lane ADDS three completions on the same measured path:

  (1) the EPO problem-solution scaffold bind (DIR-2): the invention
      must state closest prior art -> distinguishing feature ->
      objective technical problem -> why the obvious knob fails;
  (2) the MOOSE-Chem inspiration lever ON the measured path (DIR-6):
      inspiration_retrieval.retrieve_inspiration keyed by the
      failure class rides the typed_plan (cross-domain analogies +
      hash-verified evidence spans);
  (3) the generation-time quant contract (DIR-3): the runner demands
      the DESIGN_POINT at generation and computes the pint-checked
      prediction via quant_generic.emit_prediction_generic AT
      GENERATION TIME — the quant record lands IN the row (0
      invented numbers: only the row's own stated numbers).

One-shot, byte-resume per problem, agnes-3.0-flash pinned; raw rows
commit with the run (Art. 18/22). Fresh output dir — the sealed
r144 rows are never overwritten.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r97_v12_one_shot as r97  # noqa: E402
import r40_machine_v77 as m77  # noqa: E402
from discovery_fabric.engine.failure_mechanism_map import (  # noqa: E402
    detect_failure_family, family_classes)
from discovery_fabric.generation import mechanism_map as mm  # noqa: E402
from discovery_fabric.generation import quant_generic as qg  # noqa: E402
from discovery_fabric.generation import novelty_gate as ng  # noqa: E402
from discovery_fabric.generation import (  # noqa: E402
    inspiration_retrieval as ir)

OUT = REPO / "eval" / "holdout_v17_generation_r146"
OUT.mkdir(exist_ok=True)
EXECUTOR_ID = os.environ.get(
    "V17_EXECUTOR_ID", "builder-r146s1@v17-novelty-one-shot")
PROBLEMS_PATH = REPO / "eval" / "holdout_v17" / "problems.json"
MODEL_PIN = "agnes-3.0-flash"

MACHINE_RECORD = (
    "r146_v17_novelty_one_shot/1.0.0 — the novelty-strength one-shot "
    "on the LANDED engine (the r144 binds ride unchanged) with THIS "
    "lane's three completions: the EPO problem-solution scaffold "
    "bind, the MOOSE-Chem inspiration lever on the measured path, "
    "and the generation-time quant contract (the pint prediction "
    "computed in-process from the row's own stated design point; "
    "typed insufficient_parameters where none is stated — never "
    "invented numbers). Problem-only, agnes-3.0-flash pinned, "
    "one-shot; the seal + rubrics + scoring stay the AUDITOR's act.")

EPO_BIND = (
    "NON-OBVIOUSNESS SCAFFOLD (the EPO problem-solution approach): "
    "the invention MUST state, in order — "
    "(a) CLOSEST PRIOR ART: the closest standard practice for this "
    "failure, described concretely (what a competent shop does "
    "today); "
    "(b) DISTINGUISHING FEATURE: what the proposed mechanism does "
    "that the closest prior art does NOT — one feature, stated "
    "physically; "
    "(c) OBJECTIVE TECHNICAL PROBLEM: the technical effect the "
    "distinguishing feature achieves, phrased as the problem it "
    "solves (not 'improve durability'); "
    "(d) WHY THE OBVIOUS KNOB FAILS: the physical reason the "
    "standard practice's obvious knob (more material, harder surface, "
    "lower load, better lubrication, more monitoring) cannot achieve "
    "the same effect here. "
    "A mechanism that cannot fill (a)-(d) is not a mechanism — "
    "strengthen the ARRANGEMENT, not the adjectives.")

DESIGN_POINT_BIND = (
    "DESIGN POINT (mandatory for testability): the invention MUST "
    "carry a 'DESIGN_POINT' paragraph stating the numbers the "
    "mechanism acts through — at least ONE explicit magnitude (a "
    "percentage effect or a parameter with a unit: MPa, kPa, mm, "
    "mm/s, Hz, K, kV, m/s, W/mK, m^2, HV). Numbers come from the "
    "problem statement, stock datasheet values, or a TYPED "
    "assumption ('assumed: X because Y') — never invented as "
    "measured facts.")

DESIGN_POINT_KEYS = ("DESIGN_POINT", "design point", "Design point")


def load_v17_problems() -> list:
    raw = json.loads(PROBLEMS_PATH.read_text())
    probs = raw.get("problems") if isinstance(raw, dict) else raw
    assert isinstance(probs, list) and len(probs) == 30, (
        f"expected 30 v17 problems, got {len(probs) if probs else 0}")
    reg_model = r97.route_adapter.ROUTE_REGISTRY["registered"]["model"]
    assert reg_model == MODEL_PIN, (
        f"route registry registered {reg_model!r} != {MODEL_PIN!r}")
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
            "contamination_tag": p.get("split", "V17"),
        })
    return mapped


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
    probs = load_v17_problems()
    print(f"r146 v17 novelty one-shot: {len(probs)} problems | "
          f"pin {MODEL_PIN} | EPO scaffold + inspiration lever + "
          f"generation-time quant", flush=True)
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
        if outp.exists():
            skipped += 1
            continue
        row_wall_start = time.time()
        print(f"=== r146 {pid} ({idx}/30) ...", flush=True)
        try:
            fam = detect_failure_family(prob)
            sel = mm.classify_failure(prob["failure"])
            fc = sel.failure_class
            insp = ir.retrieve_inspiration(fc)
            insp_block = ir.inspiration_prompt_block(insp)
            row_out = r97.engine_route.run_row(prob)
            winner, wresult, rule = r97.v10m.select_winner(row_out)
            machine_prob = r97.v10m.challenger_prob(prob, winner, rule)
        except Exception as e:  # noqa: BLE001
            print(f"{pid}: ROUTE FAIL {type(e).__name__}: "
                  f"{str(e)[:120]} — skipped (byte-resume picks up)",
                  flush=True)
            continue
        # the r144 bind rides UNCHANGED (one source of truth)
        if fam is not None:
            adm, anti = family_classes(fam)
            machine_prob["typed_plan"]["failure_physics"] = {
                "family": fam,
                "admitted_mechanism_classes": list(adm),
                "excluded_mechanism_classes": list(anti),
                "directive": (
                    "the stated failure mode is of this family — the "
                    "mechanism MUST act on this failure physics via "
                    "the admitted classes; the excluded classes "
                    "cannot address it"),
            }
        machine_prob["typed_plan"]["quantitative_testability_bind"] = {
            "worked_calculation": (
                "the invention MUST carry ONE worked numeric "
                "calculation on its governing relation: inputs WITH "
                "units, one substitution, one numeric result WITH "
                "unit"),
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
        # THIS lane's completion (1): the EPO problem-solution scaffold
        machine_prob["typed_plan"]["epo_problem_solution_bind"] = EPO_BIND
        # THIS lane's completion (3): the generation-time design point
        machine_prob["typed_plan"]["design_point_bind"] = DESIGN_POINT_BIND
        # THIS lane's completion (2): the MOOSE-Chem inspiration lever
        machine_prob["typed_plan"]["inspiration_conditioning"] = {
            "failure_class": fc,
            "prompt_block": insp_block,
            "n_analogies": len(insp.get("analogies", [])),
            "n_evidence_spans": len(insp.get("evidence_spans", [])),
            "typed": insp.get("typed"),
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
        trace["failure_physics"] = {
            "family": fam,
            "winner_measure_class": winner.get("measure_class"),
            "winner_principle_id": winner.get("principle_id"),
            "winner_rule": rule,
        }
        trace["inspiration"] = {
            "failure_class": fc,
            "n_analogies": len(insp.get("analogies", [])),
            "evidence_hashes": [s["content_hash"] for s in
                                insp.get("evidence_spans", [])],
            "route": ("discovery_fabric.generation."
                      "inspiration_retrieval.retrieve_inspiration"),
        }
        t_row = r97._now()
        try:
            final, attempts, final_meta = r97.machine_generate_v79(
                machine_prob, _gateway_key(), used_templates={})
        except Exception as e:  # noqa: BLE001
            print(f"{pid}: GEN FAIL {type(e).__name__}: "
                  f"{str(e)[:140]} — skipped (byte-resume picks up)",
                  flush=True)
            continue
        row_wall_s = round(time.time() - row_wall_start, 1)
        # THIS lane's completion (3): the generation-time quant record
        # (the pint computation runs HERE, on the row's own text only)
        quant = qg.emit_prediction_generic(fc, final)
        sel_check = mm.select_mechanism(prob["failure"], final)
        gate = ng.gate(final, sel_check)
        decl = m77.declared_template(final)
        row = {
            "problem_id": pid,
            "domain": prob.get("domain"),
            "question_type": prob.get("question_type"),
            "executor_id": EXECUTOR_ID,
            "registered_model": MODEL_PIN,
            "machine": MACHINE_RECORD,
            "run": "v17-novelty-one-shot (one-shot, problem-only, "
                   "the novelty-strength engine)",
            "engine_trace": trace,
            "generated_at": t_row,
            "attempts_n": len(attempts),
            "row_wall_s": row_wall_s,
            "a1_answer": final,
            "quant_prediction": quant,
            "generation_checks": {
                "failure_class": fc,
                "selected_mech_class": sel_check.selected_mech_class,
                "off_target": bool(sel_check.off_target),
                "novelty": gate["novelty"],
            },
            "final_meta": {
                "critic_verdict": final_meta.get("critic_verdict"),
                "type_gate": final_meta.get("type_gate"),
                "repairs": final_meta.get("repairs"),
                "stop_reason": final_meta.get("stop_reason"),
                "residual_findings": final_meta.get(
                    "residual_findings"),
                "findings_disclosed": final_meta.get(
                    "findings_disclosed"),
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
            "failure_family": fam, "failure_class": fc,
            "winner_measure_class": winner.get("measure_class"),
            "quant_status": quant.get("status"),
            "quant_route": quant.get("route"),
            "off_target": row["generation_checks"]["off_target"],
            "novelty": row["generation_checks"]["novelty"],
        })
        ledger_path.write_text(json.dumps({
            "record": "HOLDOUT_V17_GENERATION_EVENTS_R146/1.0.0",
            "run": "v17-novelty-one-shot",
            "executor_id": EXECUTOR_ID,
            "registered_model": MODEL_PIN,
            "events": events}, indent=1) + "\n")
        done += 1
        print(f"{pid}: wall {row_wall_s}s chars {len(final)} "
              f"fc={fc} quant={quant.get('status')} "
              f"novelty={gate['novelty']} "
              f"({done} done, {skipped} resumed)", flush=True)
    print(f"r146 generation: {done} generated, {skipped} resumed, "
          f"{round(time.time() - t0, 1)}s wall", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
