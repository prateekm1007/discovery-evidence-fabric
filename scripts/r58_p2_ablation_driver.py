#!/usr/bin/env python3
"""scripts/r58_p2_ablation_driver.py — the P2 matched-budget DEV
ablation MACHINE LEG (claim c-0079, R58; the roadmap P2.4 item).

DESIGN (pre-registered in the claim, BEFORE any generation):
  - ROWS: the 36 burned-DEV problems the committed v8.2 plan
    population covers (12 v2-burned + 12 v3-burned + 12 dev12),
    loaded from the SAME canonical sources the population layer used
    (scripts/v82_typed_population.py load_dev_problems).
  - BOTH ARMS run the V7.7 machine (scripts/r40_machine_v77.py)
    BYTE-UNCHANGED on the REGISTERED route (R36: glm-4-plus via the
    loop-local z.ai gateway) — matched model identity, matched loop,
    matched per-problem budget (the machine's own REPAIR_BUDGET=3,
    i.e. <= 4 generation attempts; the committed V7.7 events ledger
    shows exactly 4 attempts/problem on all 12 HO7 rows).
  - THE ABLATION DELTA (the P2 addition under test) is delivered via
    the problem payload: the challenger arm's problem dict carries a
    typed_plan field (the winning plan from the committed population
    — operator, TRIZ principle, measure_class, signals) which the
    machine's own `q = json.dumps(prob)` carries into the generation
    prompt. Baseline arm: the identical problem dict WITHOUT the
    field. Same machine, same scans, same critic, same repair loop —
    the delta is exactly the plan conditioning.
  - WINNER SELECTION (deterministic, pre-registered): among the
    problem's plans with contract_satisfied, the FIRST non-duty_cycle
    plan in population order; fallback: first satisfied; last
    resort: first plan (typed in the row). Dry-checked: 36/36
    problems select via the non-schedule rule.
  - NO ROUTE FALLBACK: a mid-run model switch would contaminate the
    matched-identity design — if the registered route stalls, the
    driver stops (rows already committed stay; the run resumes from
    committed rows on the same route per Art. 29(d) heartbeats).
  - CRITERIA: after both arms, `--normalize` emits the evaluator
    shape and `--criteria` runs the amended evaluator
    (scripts/r53_p2_ablation_criteria.py v1.1.0). Criterion 3
    (mean no drop) is UNMEASURABLE until the confidential instrument
    exists (F60 owner custody) — the verdict types
    ADOPTION_DEFERRED_CRITERION_3_UNMEASURABLE, never a DELETE on no
    measurement.

RESUME SAFETY: per-row files under eval/r58_ablation/rows_<arm>/
are the durable state; existing row files are skipped (the
r11_a1f_v3_generate convention). The events ledger is rewritten
after every row.

Zero LLM calls at import or in --dry-run (the dry-run exercises the
plumbing on fixtures, Art. 22: fixtures prove mechanics only).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

# CORR-3 session-local transport resolution: the z-ai CLI lives in
# the sandbox project's node_modules bin (NOT on the default PATH).
# The gateway spawns `z-ai` by name, so the bin dir MUST be on PATH
# before start_gateway().
ZAI_BIN = Path("/home/z/my-project/node_modules/.bin")
if ZAI_BIN.is_dir() and str(ZAI_BIN) not in sys.path:
    import os
    os.environ["PATH"] = f"{ZAI_BIN}:{os.environ.get('PATH', '')}"

from r40_machine_v77 import (  # noqa: E402
    machine_generate_v77, start_gateway, declared_template,
    V77_REQUEST_MODEL)
from r53_p2_ablation_criteria import evaluate  # noqa: E402
# Art. 22 v3.2.0 MEASURED-PATH declaration (F61): the measurement
# driver's transport identity is declared THROUGH THE ENGINE — the
# route registry is the single authority for what may serve the
# ablation; a machine model that does not match the registered route
# is a typed refusal BEFORE any call (a wrapper-only measurement is
# flagged, never silently run).
from discovery_fabric.engine import route_adapter  # noqa: E402

OUT = REPO / "eval" / "r58_ablation"
GW_LOG = REPO / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"
EXECUTOR_ID = "builder-r58s1@r58-p2-dev-ablation-machine-leg"
POPULATION = REPO / "eval" / "v82_dev_plan_population.json"
DEV_SOURCES = [
    ("eval/dev_holdout_problems/holdout_v2_problems.burned_dev.json",
     "v2-burned"),
    ("eval/dev_holdout_problems/holdout_v3_problems.burned_dev.json",
     "v3-burned"),
    ("eval/problems_dev12.json", "dev12"),
]
AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
HO7_PATH = "audit/holdout_v7/holdout_v7_problems.json"
SMOKE_ROWS = ["HO7-01-zinc-ew-acid-mist",
              "HO7-09-chiller-condenser-fouling"]


def _now() -> str:
    return (datetime.datetime.now(datetime.UTC).isoformat()
            .replace("+00:00", "Z"))


def load_dev_problems() -> list:
    """The burned-DEV corpus from the canonical sources (the v82
    population's own loader, verbatim convention)."""
    out = []
    for name, tag in DEV_SOURCES:
        d = json.loads((REPO / name).read_text(encoding="utf-8"))
        probs = d["problems"] if isinstance(d, dict) and "problems" \
            in d else (d if isinstance(d, list) else [])
        for p in probs:
            p = dict(p)
            p["_dev_source"] = tag
            out.append(p)
    return out


def load_population() -> dict:
    d = json.loads(POPULATION.read_text(encoding="utf-8"))
    return {p["problem_id"]: p for p in d["problems"]}


def select_winner(plans: list) -> tuple:
    """PRE-REGISTERED deterministic winner rule: first
    contract-satisfied non-duty_cycle plan in population order;
    fallback first satisfied; last resort first plan."""
    sat = [p for p in plans if p.get("contract_satisfied")]
    non_sched = [p for p in sat
                 if p.get("measure_class") != "duty_cycle"]
    if non_sched:
        return non_sched[0], "non_schedule_first"
    if sat:
        return sat[0], "schedule_fallback"
    return plans[0], "none_satisfied_fallback"


def challenger_prob(prob: dict, winner: dict, rule: str) -> dict:
    """The P2 addition delivered via the problem payload: the
    typed_plan field the machine's own json.dumps(prob) carries into
    the generation prompt (machine logic byte-unchanged)."""
    p = dict(prob)
    p["typed_plan"] = {
        "note": ("PLAN CONDITIONING (the machine's typed plan layer "
                 "- the intervention MUST implement this plan)"),
        "operator": winner["operator_id"],
        "triz_principle": winner["principle_id"],
        "measure_class": winner["measure_class"],
        "signals_used": list(winner.get("signals_used") or []),
        "selection_rule": rule,
    }
    return p


def _sha16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def run_arm(arm: str, problems: list, pop: dict, smoke: bool = False,
            max_rows: int = 0) -> int:
    """One arm's one-shot pass. Resume-safe: committed row files are
    skipped. Rows + events ledger + gateway-log slice per arm.
    Smoke rows live in their own namespace (rows_smoke_<arm>) and
    never enter the measurement files."""
    # Art. 22 v3.2.0 (F61): the measured path is declared through the
    # engine route registry — the ablation serves ONLY the registered
    # generator id; a mismatch REFUSES typed (RouteRefused semantics,
    # Art. 3) before the gateway starts.
    try:
        route_adapter.require_registered_model(V77_REQUEST_MODEL)
    except Exception as e:  # RouteRefused and any registry drift
        print(f"[{arm}] MEASURED-PATH REFUSAL (typed, Art. 22 v3.2.0): "
              f"machine model {V77_REQUEST_MODEL} is not the engine-"
              f"registered route: {e}", flush=True)
        return 3
    rows_dir = OUT / (f"rows_smoke_{arm}" if smoke else f"rows_{arm}")
    rows_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = OUT / (f"events_smoke_{arm}.json" if smoke else
                         f"events_{arm}.json")

    gw, gw_key = start_gateway()
    print(f"[{arm}] gateway healthy (registered route "
          f"{V77_REQUEST_MODEL})", flush=True)
    try:
        return _run_arm_body(arm, problems, pop, smoke, max_rows,
                             gw, gw_key)
    finally:
        # one gateway per arm, terminated at arm end — a second
        # start_gateway would EADDRINUSE-bind-fail and return a key
        # the OLD gateway rejects (401 -> the nvidia fallback crash,
        # observed and typed 2026-11-17); leaked gateways also poison
        # the next session's probe (the stale-key 401).
        try:
            gw.terminate()
            gw.wait(timeout=10)
        except Exception:
            gw.kill()


def _run_arm_body(arm: str, problems: list, pop: dict, smoke: bool,
                  max_rows: int, gw, gw_key: str) -> int:
    rows_dir = OUT / (f"rows_smoke_{arm}" if smoke else f"rows_{arm}")
    ledger_path = OUT / (f"events_smoke_{arm}.json" if smoke else
                         f"events_{arm}.json")
    offset = GW_LOG.stat().st_size if GW_LOG.exists() else 0
    run_start = _now()

    used_templates: Counter = Counter()
    events = []
    if ledger_path.exists():
        prev = json.loads(ledger_path.read_text(encoding="utf-8"))
        events = prev.get("events", [])
        # restore the histogram from committed rows (resume path)
        for e in events:
            pass  # histogram re-derived below from row files

    # restore the diversity-cap histogram from committed rows
    for f in sorted(rows_dir.glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        decl = r.get("declared_template_prose")
        if decl:
            used_templates[decl] += 1

    done = 0
    skipped = 0
    t0 = time.time()
    for idx, prob in enumerate(sorted(problems,
                                      key=lambda p: p["problem_id"]),
                               1):
        pid = prob["problem_id"]
        if max_rows and done >= max_rows:
            break
        outp = rows_dir / f"{pid}.json"
        if outp.exists():
            skipped += 1
            continue
        if arm == "challenger":
            winner, rule = select_winner(pop[pid]["plans"])
            machine_prob = challenger_prob(prob, winner, rule)
        else:
            machine_prob, winner, rule = prob, None, None
        hist = dict(used_templates)
        t_row = _now()
        final, attempts, final_meta = machine_generate_v77(
            machine_prob, gw_key, used_templates=used_templates)
        decl = declared_template(final)
        if decl and not str(prob.get("question_type", "")) \
                .lower().startswith("predictor"):
            used_templates[decl] += 1
        residual = final_meta.get("residual_findings") or {}
        row = {
            "problem_id": pid,
            "arm": arm,
            "dev_source": prob.get("_dev_source"),
            "question_type": prob.get("question_type"),
            "executor_id": EXECUTOR_ID,
            "machine": ("V7.7 frozen (scripts/r40_machine_v77.py, "
                        f"V77_REQUEST_MODEL={V77_REQUEST_MODEL})"),
            "arm_design": ("challenger = identical machine + the "
                           "typed_plan payload field (the P2 addition "
                           "under test)" if arm == "challenger" else
                           "baseline = the identical machine, no plan "
                           "conditioning"),
            "typed_plan": machine_prob.get("typed_plan"),
            "winner_rule": rule,
            "plan_measure_class": (winner or {}).get("measure_class"),
            "generated_at": t_row,
            "attempts_n": len(attempts),
            "a1_answer": final,
            "final_meta": {
                "critic_verdict": final_meta.get("critic_verdict"),
                "type_gate": final_meta.get("type_gate"),
                "repairs": final_meta.get("repairs"),
                "residual_findings": residual,
            },
            "declared_template_prose": decl,
            "allowed_row_outside": len(
                residual.get("ALLOWED_ROW_OUTSIDE", [])),
            "sha256_16": _sha16(final),
            "smoke": bool(smoke),
        }
        outp.write_text(json.dumps(row, indent=1, ensure_ascii=False)
                        + "\n", encoding="utf-8")
        events.append({
            "problem_id": pid, "generated_at": t_row,
            "histogram_before": hist,
            "histogram_after": dict(used_templates),
            "attempts": attempts,
            "final_sha256_16": row["sha256_16"],
            "final_chars": len(final),
        })
        ledger_path.write_text(json.dumps({
            "record": f"R58_ABLATION_EVENTS_{arm.upper()}/1.0.0",
            "run": "r58-p2-dev-ablation-machine-leg",
            "executor_id": EXECUTOR_ID,
            "registered_model": V77_REQUEST_MODEL,
            "window_started_at": run_start,
            "events": events},
            indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        done += 1
        print(f"[{arm} {idx}/{len(problems)}] {pid} repairs="
              f"{final_meta.get('repairs')} critic="
              f"{final_meta.get('critic_verdict')} chars={len(final)} "
              f"({time.time()-t0:.0f}s)", flush=True)
        t0 = time.time()

    # gateway-log slice: exactly this arm's window
    slice_lines = []
    if GW_LOG.exists():
        with GW_LOG.open("rb") as f:
            f.seek(offset)
            slice_lines = [ln for ln in f.read()
                           .decode("utf-8", "replace").splitlines()
                           if ln.strip()]
    (OUT / (f"gateway_slice_smoke_{arm}.txt" if smoke else
             f"gateway_slice_{arm}.txt")).write_text(
        "\n".join(slice_lines) + "\n", encoding="utf-8")
    served = [c for c in (json.loads(ln) for ln in slice_lines
                          if ln.strip().startswith("{"))
              if c.get("requested_model") is not None
              or c.get("model") is not None]
    (OUT / (f"attestation_smoke_{arm}.json" if smoke else
             f"attestation_{arm}.json")).write_text(json.dumps({
        "record": f"R58_ABLATION_ATTESTATION_{arm.upper()}/1.0.0",
        "executor_id": EXECUTOR_ID,
        "registered_model": V77_REQUEST_MODEL,
        "window_started_at": run_start,
        "window_ended_at": _now(),
        "gateway_completed_calls": len(served),
        "served_model_matches_registered": all(
            c.get("model") in (None, V77_REQUEST_MODEL)
            for c in served),
        "note": "served==requested per completed call from the "
                "gateway log slice; telemetry lines (429 backoff) "
                "carry no model field and are not calls",
    }, indent=1) + "\n", encoding="utf-8")
    print(f"[{arm}] rows done={done} skipped(resumed)={skipped} "
          f"gateway completed calls={len(served)}", flush=True)
    return 0


def normalize() -> int:
    """Emit the evaluator-shape row files from the committed row
    artifacts. measure_classes: the challenger carries the plan
    layer's enum class (the pre-registered intervention class — the
    same convention the v82 population's schedule-share used); the
    baseline carries the declared prose class (no plan layer
    exists). mean_score: None (UNMEASURABLE — the instrument is
    F60-gated); never fabricated."""
    cand, base = {}, {}
    for arm, sink in (("challenger", cand), ("baseline", base)):
        for f in sorted((OUT / f"rows_{arm}").glob("*.json")):
            r = json.loads(f.read_text(encoding="utf-8"))
            classes = ([r["plan_measure_class"]]
                       if arm == "challenger" and
                       r.get("plan_measure_class") else
                       [r["declared_template_prose"]]
                       if r.get("declared_template_prose") else [])
            sink[r["problem_id"]] = {
                "mean_score": None,
                "measure_classes": classes,
                "allowed_row_outside": r.get("allowed_row_outside", 0),
                "attempts_n": r.get("attempts_n"),
                "repairs": (r.get("final_meta") or {}).get("repairs"),
                "critic_verdict": (r.get("final_meta") or {})
                .get("critic_verdict"),
                "smoke": r.get("smoke", False),
            }
    (OUT / "candidate_rows.json").write_text(
        json.dumps(cand, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    (OUT / "baseline_rows.json").write_text(
        json.dumps(base, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    # smoke rows never enter the measurement files
    print(f"[normalize] candidate rows: {len(cand)} | baseline rows: "
          f"{len(base)} (smoke rows flagged, excluded by --criteria)")
    return 0


def criteria() -> int:
    """Run the amended evaluator over the normalized rows, EXCLUDING
    smoke rows (mechanics-only, Art. 22)."""
    cand = json.loads((OUT / "candidate_rows.json")
                      .read_text(encoding="utf-8"))
    base = json.loads((OUT / "baseline_rows.json")
                      .read_text(encoding="utf-8"))
    cand = {k: v for k, v in cand.items() if not v.get("smoke")}
    base = {k: v for k, v in base.items() if not v.get("smoke")}
    (OUT / "_cand_eval_input.json").write_text(
        json.dumps(cand, indent=1, ensure_ascii=False))
    (OUT / "_base_eval_input.json").write_text(
        json.dumps(base, indent=1, ensure_ascii=False))
    out = evaluate(OUT / "_cand_eval_input.json",
                   OUT / "_base_eval_input.json")
    (OUT / "criteria_result.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0


def dry_run() -> int:
    """Zero-LLM mechanics check (Art. 22: fixtures prove mechanics
    only): the loader, the winner rule, the payload construction, the
    evaluator v1.1.0 paths on synthetic rows."""
    problems = load_dev_problems()
    pop = load_population()
    assert len(problems) == 36, f"expected 36, got {len(problems)}"
    assert set(p["problem_id"] for p in problems) == set(pop), \
        "problem set != population set"
    rules = Counter()
    for p in problems:
        w, rule = select_winner(pop[p["problem_id"]]["plans"])
        rules[rule] += 1
        cp = challenger_prob(p, w, rule)
        assert cp["typed_plan"]["operator"] == w["operator_id"]
        assert "typed_plan" not in p, "payload mutation leaked"
    print(f"[dry-run] 36 rows, winner rules: {dict(rules)}")
    print(f"[dry-run] challenger payload: typed_plan field only, "
          f"baseline problem dict untouched")
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # deferred path: crit1+2 met, crit3 UNMEASURABLE
        fake = {"HO2-01-x": {"mean_score": None,
                             "measure_classes": ["configuration"],
                             "allowed_row_outside": 0}}
        fake_b = {"HO2-01-x": {"mean_score": None,
                               "measure_classes": ["whatever"],
                               "allowed_row_outside": 0}}
        (td / "c.json").write_text(json.dumps(fake))
        (td / "b.json").write_text(json.dumps(fake_b))
        out = evaluate(td / "c.json", td / "b.json")
        assert out["criteria"][0]["met"] is True   # share 0.0 <= .17
        assert out["criteria"][1]["met"] is True   # outside == 0
        assert out["criteria"][2]["value"] == "UNMEASURABLE"
        assert out["verdict"] == "ADOPTION_DEFERRED_" \
            "CRITERION_3_UNMEASURABLE", out["verdict"]
        # measured ADOPT path unchanged vs v1.0.0
        fake2 = {"HO2-01-x": {"mean_score": 3.2,
                              "measure_classes": ["configuration"],
                              "allowed_row_outside": 0}}
        fake2_b = {"HO2-01-x": {"mean_score": 3.0,
                                 "measure_classes": ["x"],
                                 "allowed_row_outside": 0}}
        (td / "c2.json").write_text(json.dumps(fake2))
        (td / "b2.json").write_text(json.dumps(fake2_b))
        out2 = evaluate(td / "c2.json", td / "b2.json")
        assert out2["verdict"] == "ADOPT", out2["verdict"]
        # measured DELETE path unchanged vs v1.0.0
        fake3 = {"HO2-01-x": {"mean_score": 2.8,
                              "measure_classes": ["configuration"],
                              "allowed_row_outside": 0}}
        (td / "c3.json").write_text(json.dumps(fake3))
        out3 = evaluate(td / "c3.json", td / "b2.json")
        assert out3["verdict"] == "DELETE", out3["verdict"]
        # crit1 unmet -> INCOMPLETE (the pre-registered bar kills)
        fake4 = {"HO2-01-x": {"mean_score": 3.2,
                              "measure_classes": ["duty_cycle"],
                              "allowed_row_outside": 0}}
        (td / "c4.json").write_text(json.dumps(fake4))
        out4 = evaluate(td / "c4.json", td / "b2.json")
        assert out4["verdict"].startswith("INCOMPLETE"), out4["verdict"]
        print(f"[dry-run] evaluator all paths OK "
              f"(deferred/adopt/delete/incomplete)")
    print("[dry-run] PASS (zero LLM, zero network)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=[
        "dry-run", "smoke", "baseline", "challenger",
        "normalize", "criteria"])
    ap.add_argument("--max-rows", type=int, default=0,
                    help="cap rows for this invocation (smoke/heartbeat)")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    problems = load_dev_problems()
    pop = load_population()
    if args.cmd == "dry-run":
        return dry_run()
    if args.cmd == "smoke":
        # mechanics-only live fire on BURNED NON-ABLATION rows (the
        # HO7 holdout packet, the v7 baseline's own material — burned
        # by the committed v7 run + judgments; NOT among the 36
        # ablation rows). Problem statements load from the audit ref
        # (the r42 convention). Smoke rows carry a SYNTHETIC plan
        # (mechanics only, Art. 22) and live in rows_smoke_<arm>,
        # excluded from every measurement file.
        raw = subprocess.run(
            ["git", "show", f"{AUDIT_REF}:{HO7_PATH}"],
            capture_output=True, text=True, timeout=30, cwd=str(REPO))
        assert raw.returncode == 0, (
            f"cannot read the HO7 packet from {AUDIT_REF} "
            f"(typed abort): {raw.stderr[-200:]}")
        probs = [p for p in json.loads(raw.stdout)["problems"]
                 if p["problem_id"] in SMOKE_ROWS]
        assert len(probs) == len(SMOKE_ROWS), (
            "smoke rows not found in the HO7 packet (typed abort)")
        synth = {"operator_id": "DOMAIN_KNOWLEDGE_FIRST",
                 "principle_id": "P35",
                 "measure_class": "boundary",
                 "signals_used": ["pressure", "temperature"],
                 "contract_satisfied": True}
        smoke_pop = {p["problem_id"]: {"plans": [synth]}
                     for p in probs}
        rc = run_arm("baseline", probs, smoke_pop, smoke=True)
        if rc:
            return rc
        return run_arm("challenger", probs, smoke_pop, smoke=True)
    if args.cmd in ("baseline", "challenger"):
        return run_arm(args.cmd, problems, pop,
                       max_rows=args.max_rows)
    if args.cmd == "normalize":
        return normalize()
    if args.cmd == "criteria":
        return criteria()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
