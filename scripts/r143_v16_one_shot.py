#!/usr/bin/env python3
"""r115s1-style v16 one-shot — DIR-3: the v16 sealed-set generation
(problem-only, one-shot, agnes-3.0-flash pinned).

The delegated owner authored v16: 30 fresh cluster-disjoint problems
(eval/holdout_v16/problems.json — audit-branch bytes, MINIMAL shape:
{problem_id, domain, problem, split} — deliberately problem-only), the
rubrics sealed in the PRIVATE custody repo (unauth 404; the builder
never reads them — the auditor scores).

The generation instrument: r105's pipeline UNCHANGED (r97's frozen v12
machine + m77's [c-0109] tool_grounded_critic + the engine route) —
the v16 problems map into the pipeline's expected fields WITHOUT
invention: device = "(stated in the problem)", failure = the problem
text (verbatim), question = the standard invention question,
question_type = "invention", user_variables = [] (problem-only by the
prereg's design; the missing variables are the point — the sealed
rubrics score the invention, not constraint compliance).

One-shot: byte-resume per problem (Art. 15 — a resumed problem
continues the SAME generation); the raw rows commit with the run.
Burn after (the auditor scores; no re-roll).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r97_v12_one_shot as r97  # noqa: E402  (the frozen v12 machine)
import r40_machine_v77 as m77  # noqa: E402

OUT = REPO / "eval" / "holdout_v16_generation"
OUT.mkdir(exist_ok=True)
EXECUTOR_ID = "builder-r121s1@holdout-v16-generation"
AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
PROBLEMS_PATH = "eval/holdout_v16/problems.json"
PREREG_PATH = "eval/holdout_v16/PREREG.json"
MODEL_PIN = "agnes-3.0-flash"

MACHINE_RECORD = (
    "r143_v16_one_shot/1.0.0 — the sealed v16 one-shot (the delegated "
    "owner's 30-problem cluster-disjoint set, problem-only): r105's "
    "pipeline UNCHANGED (the frozen v12 machine_generate_v79 + the "
    "[c-0109] tool_grounded_critic + the engine route), the v16 "
    "problems mapped without invention (device='(stated in the "
    "problem)', failure=the problem text verbatim, question=the "
    "standard invention question, user_variables=[] — problem-only by "
    "the prereg's design; the sealed rubrics score the invention)")


def _git_show_audit(path: str) -> str:
    import subprocess
    out = subprocess.run(["git", "show", f"{AUDIT_REF}:{path}"],
                         capture_output=True, cwd=REPO)
    assert out.returncode == 0, (
        f"the v16 custody file {path} is not readable at the pinned "
        f"audit ref (typed abort — custody comes from committed bytes "
        f"only)")
    return out.stdout.decode("utf-8")


def load_v16_problems() -> list:
    """Problems ONLY, from committed audit-ref bytes, fail-closed on
    the prereg's model pin. The auditor's PRIVATE rubric is never
    touched (unauth 404 — the custody discipline)."""
    prereg = json.loads(_git_show_audit(PREREG_PATH))
    assert str(prereg.get("model_pin") or "") == MODEL_PIN, (
        f"the prereg's model_pin is {prereg.get('model_pin')!r} but "
        f"the instrument serves {MODEL_PIN!r} (typed abort)")
    assert int(prereg.get("n") or 0) == 30, (
        "the prereg pins n=30 (typed abort)")
    reg_model = r97.route_adapter.ROUTE_REGISTRY["registered"]["model"]
    assert reg_model == MODEL_PIN, (
        f"the route registry's registered id is {reg_model!r} but "
        f"the instrument serves {MODEL_PIN!r} (typed abort)")
    raw = json.loads(_git_show_audit(PROBLEMS_PATH))
    probs = raw.get("problems", raw if isinstance(raw, list) else [])
    assert len(probs) == 30, f"expected 30 v16 problems, got {len(probs)}"
    # the problem-only mapping (no invention — the fields the pipeline
    # needs, filled from the problem text or typed defaults)
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
            "contamination_tag": p.get("split", "V16"),
        })
    return mapped


def main() -> int:
    probs = load_v16_problems()
    print(f"v16: {len(probs)} problems | model pin {MODEL_PIN} | "
          f"problem-only one-shot", flush=True)
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
        print(f"=== v16 {pid} ({idx}/30) ...", flush=True)
        row_out = r97.engine_route.run_row(prob)
        winner, wresult, rule = r97.v10m.select_winner(row_out)
        machine_prob = r97.v10m.challenger_prob(prob, winner, rule)
        trace = r97.v10m.engine_trace(prob, row_out, winner, wresult,
                                      rule)
        t_row = r97._now()
        final, attempts, final_meta = r97.machine_generate_v79(
            machine_prob, None, used_templates={})
        row_wall_s = round(time.time() - row_wall_start, 1)
        decl = m77.declared_template(final)
        row = {
            "problem_id": pid,
            "domain": prob.get("domain"),
            "question_type": prob.get("question_type"),
            "executor_id": EXECUTOR_ID,
            "registered_model": MODEL_PIN,
            "machine": MACHINE_RECORD,
            "run": "holdout-v16-generation (sealed one-shot, "
                   "problem-only)",
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
                "delivered_node_id":
                    final_meta.get("delivered_node_id"),
                "delivery_rule": final_meta.get("delivery_rule"),
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
        })
        ledger_path.write_text(json.dumps({
            "record": "HOLDOUT_V16_GENERATION_EVENTS/1.0.0",
            "run": "holdout-v16-generation",
            "executor_id": EXECUTOR_ID,
            "registered_model": MODEL_PIN,
            "events": events}, indent=1) + "\n")
        done += 1
        print(f"{pid}: wall {row_wall_s}s chars {len(final)} "
              f"({done} done, {skipped} resumed)", flush=True)
    print(f"v16 generation: {done} generated, {skipped} resumed, "
          f"{round(time.time() - t0, 1)}s wall", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
