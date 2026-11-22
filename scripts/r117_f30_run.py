#!/usr/bin/env python3
"""r117_f30_run.py — the F30 bind-value generation run (claim c-0172,
work id r117-f30-generation-run; the R117 direction 2, the DECISIVE
engine-value test).

The prereg (eval/r116_f30_bind_value_prereg.json) + amendment 1
(eval/r117_f30_prereg_amendment_1.json) govern. Two arms on the v1.1.0
seeded battery (eval/r116_f30_set/items_v1_1.jsonl, 24 items):

  BARE  — agnes-3.0-flash, ONE call per item: the problem JSON (the
          same fields the engine arm's prompt carries) + a minimal
          review directive. Raw completion committed verbatim.
  ENGINE — the frozen machine path per item: engine_route.run_row
          (the integrated route, zero LLM) -> v10m.select_winner ->
          challenger_prob -> machine_generate_v79 (r97's frozen V7.9
          loop: all five binds + the repair loop, budget 3) through
          the loop-local zai gateway (ZAI_GATEWAY_UPSTREAM=agnes, the
          R67s2 2-key rotation inside altComplete).

Byte-skip resume at every level: an existing {arm}_{pid}.txt / .json
is NEVER re-requested (one generation per item per arm, ever — Art.
29(c)). The gateway is started once; the events ledger accumulates.
Zero LLM in the scoring driver (deterministic detector); the judge
calls (disagreement class only) are a SEPARATE step.

Usage: python3 scripts/r117_f30_run.py [--bare-only|--engine-only]
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

SET = REPO / "eval" / "r116_f30_set" / "items_v1_1.jsonl"
OUT = REPO / "eval" / "r116_f30_run"
OUT.mkdir(parents=True, exist_ok=True)

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

from discovery_fabric.engine import route_adapter as ra  # noqa: E402
from discovery_fabric.engine import engine_route as er  # noqa: E402
import r85_v10_one_shot as v10m                # noqa: E402
import r97_v12_one_shot as r97                 # noqa: E402
import r40_machine_v77 as m77                  # noqa: E402

V = "agnes-3.0-flash"


def bare_prompt(prob: dict) -> str:
    return ("You are reviewing an engineering mitigation proposal. "
            "Problem and draft below. Does the draft violate any "
            "constraint, rely on anything unavailable, invert any "
            "physical direction, or misprice a duty cycle? Answer "
            "with your verdict and reasoning.\n\n"
            "PROBLEM:\n"
            + json.dumps({k: prob.get(k, "") for k in
                          ("problem_id", "device", "failure",
                           "constraint")}, ensure_ascii=False)
            + "\n\n" + prob["question"])


def run_bare(items: list) -> None:
    for prob in items:
        pid = prob["problem_id"]
        path = OUT / f"bare_{pid}.txt"
        if path.exists():
            print(f"  bare {pid}: SKIP (byte-resume)", flush=True)
            continue
        for attempt in (1, 2, 3, 4):
            try:
                txt = ra.agnes_chat(
                    [{"role": "user",
                      "content": bare_prompt(prob)}],
                    model=V, visible_target=1200,
                    timeout_s=300.0).get("content") or ""
                path.write_text(txt, encoding="utf-8")
                print(f"  bare {pid}: {len(txt)}c "
                      f"(attempt {attempt})", flush=True)
                break
            except Exception as e:  # noqa: BLE001
                print(f"  bare {pid}: attempt {attempt} FAILED "
                      f"{type(e).__name__}: {str(e)[:100]}",
                      flush=True)
                if attempt == 4:
                    (OUT / f"bare_{pid}.TYPED_FAIL").write_text(
                        f"{type(e).__name__}: {str(e)[:300]}\n",
                        encoding="utf-8")
                time.sleep(120)
        time.sleep(10)


def run_engine(items: list, gw_key: str) -> None:
    used_templates = {}
    for prob in items:
        pid = prob["problem_id"]
        outp = OUT / f"engine_{pid}.json"
        if outp.exists():
            print(f"  engine {pid}: SKIP (byte-resume)",
                  flush=True)
            continue
        # (1) the integrated route (zero LLM)
        row_out = er.run_row(prob)
        # (2) the winner rule + the challenger problem payload
        winner, wresult, rule = v10m.select_winner(row_out)
        machine_prob = v10m.challenger_prob(prob, winner, rule)
        # (3) the frozen machine loop (gateway LLM calls)
        try:
            final, attempts, final_meta = r97.machine_generate_v79(
                machine_prob, gw_key,
                used_templates=used_templates)
        except Exception as e:  # noqa: BLE001
            (OUT / f"engine_{pid}.TYPED_FAIL").write_text(
                f"{type(e).__name__}: {str(e)[:300]}\n",
                encoding="utf-8")
            print(f"  engine {pid}: TYPED_FAIL "
                  f"{type(e).__name__}: {str(e)[:120]}", flush=True)
            time.sleep(90)
            continue
        decl = m77.declared_template(final)
        if decl and not str(prob.get("question_type",
                                     "")).lower().startswith(
                "predictor"):
            used_templates[decl] = used_templates.get(decl, 0) + 1
        rec = {
            "problem_id": pid,
            "question_type": prob.get("question_type"),
            "registered_model": V,
            "machine": "r117_f30_run/engine-arm "
                       "(machine_generate_v79 UNCHANGED)",
            "winner": {"operator": winner.get("operator_id"),
                       "principle": winner.get("principle_id"),
                       "rule": rule},
            "a1_answer": final,
            "attempts_n": len(attempts),
            "final_meta": final_meta,
            "engine_trace": {"route": "engine_route.run_row",
                             "plans_n": len(row_out.get(
                                 "plans", []))},
        }
        outp.write_text(json.dumps(rec, indent=1,
                                   ensure_ascii=False) + "\n",
                        encoding="utf-8")
        res = final_meta.get("residual_findings") or {}
        print(f"  engine {pid}: {len(final)}c, attempts "
              f"{len(attempts)}, stop "
              f"{final_meta.get('stop_reason')}, residual classes "
              f"{sorted(res.keys())}", flush=True)
        time.sleep(12)


def main() -> int:
    which = "all"
    if "--bare-only" in sys.argv:
        which = "bare"
    if "--engine-only" in sys.argv:
        which = "engine"
    items = [json.loads(l) for l in
             SET.read_text(encoding="utf-8").strip().split("\n")]
    items.sort(key=lambda p: p["problem_id"])
    print(f"F30 run: {len(items)} items, mode={which}", flush=True)

    if which in ("all", "bare"):
        print("--- BARE arm ---", flush=True)
        run_bare(items)

    if which in ("all", "engine"):
        print("--- ENGINE arm (gateway start) ---", flush=True)
        if r97._gateway_alive():
            print("REFUSED (typed): a gateway is already listening "
                  "on 127.0.0.1:8787 — kill it first", flush=True)
            return 3
        if ra.resolve_vault_key("AGNES_API_KEY") is None:
            print("REFUSED (typed INFRA_CREDENTIAL_MISSING): "
                  "AGNES_API_KEY absent", flush=True)
            return 3
        ra.require_registered_model(V)
        os.environ["ZAI_GATEWAY_UPSTREAM"] = "agnes"
        os.environ["AGNES_MODEL_ID"] = V
        from r11_a1f_v3_generate import start_gateway
        gw, gw_key = start_gateway()
        print("gateway healthy (upstream=agnes)", flush=True)
        try:
            run_engine(items, gw_key)
        finally:
            gw.terminate()
            print("gateway terminated", flush=True)

    n_bare = len(list(OUT.glob("bare_*.txt")))
    n_eng = len(list(OUT.glob("engine_*.json")))
    print(f"\nDONE: bare {n_bare}/24, engine {n_eng}/24 "
          f"(typed fails: "
          f"{len(list(OUT.glob('*.TYPED_FAIL')))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
