#!/usr/bin/env python3
"""r118_authoring_run.py — the F31a authoring-task run (claim c-0176,
work id r118-authoring-bind-value-run; the R118 direction 3, the
on-design bind-value test).

The prereg (eval/r118_authoring_bind_value_prereg.json) governs. Two
arms on eval/r118_authoring_set/items.jsonl (24 items):

  BARE_ONLY      — agnes-3.0-flash, ONE call per item: the scenario
                   JSON + the minimal authoring directive. Raw
                   completion committed verbatim. NO binds, NO repair.
  BARE_PLUS_BINDS — the SAME one-call bare authoring (byte-identical
                   prompt), then the bind CHECK layer over the
                   authored bill (the five binds' deterministic scans,
                   m77's own) and the frozen machine's repair loop
                   (V77_REPAIR_DIRECTIVE + regeneration, REPAIR_BUDGET
                   3): the binds check/repair text the bare model
                   wrote. The DELIVERED bill (after repair) is what
                   scores.

Byte-skip resume: an existing {arm}_{pid}.txt / .json is NEVER
re-requested (one generation per item per arm, ever — Art. 29(c)).
The gateway runs once for the binds arm's repair legs (the bare_only
arm uses the direct agnes transport, same registered model).

Usage: python3 scripts/r118_authoring_run.py [--bare-only|--binds-only]
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

SET = REPO / "eval" / "r118_authoring_set" / "items.jsonl"
OUT = REPO / "eval" / "r118_authoring_run"
OUT.mkdir(parents=True, exist_ok=True)

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

from discovery_fabric.engine import route_adapter as ra  # noqa: E402
import r40_machine_v77 as m77                  # noqa: E402
import r97_v12_one_shot as r97                 # noqa: E402

V = "agnes-3.0-flash"

AUTHORING_DIRECTIVE = (
    "You are an engineer. Propose ONE mitigation for the failure "
    "described in the problem, under the stated constraint. Answer "
    "with the mitigation proposal (mechanism, implementation, and the "
    "measures it relies on).")


def authoring_prompt(prob: dict) -> str:
    return (AUTHORING_DIRECTIVE + "\n\nPROBLEM:\n"
            + json.dumps({k: prob.get(k, "") for k in
                          ("problem_id", "device", "failure",
                           "constraint")}, ensure_ascii=False)
            + "\n\n" + prob["question"])


def bare_call(prob: dict) -> str:
    for attempt in (1, 2, 3, 4):
        try:
            return ra.agnes_chat(
                [{"role": "user", "content": authoring_prompt(prob)}],
                model=V, visible_target=1200,
                timeout_s=300.0).get("content") or ""
        except Exception as e:  # noqa: BLE001
            print(f"    bare attempt {attempt} FAILED "
                  f"{type(e).__name__}: {str(e)[:90]}", flush=True)
            if attempt == 4:
                raise
            time.sleep(120)


def run_bare_only(items: list) -> None:
    for prob in items:
        pid = prob["problem_id"]
        path = OUT / f"bare_{pid}.txt"
        if path.exists():
            print(f"  bare {pid}: SKIP (byte-resume)", flush=True)
            continue
        txt = bare_call(prob)
        path.write_text(txt, encoding="utf-8")
        print(f"  bare {pid}: {len(txt)}c", flush=True)
        time.sleep(8)


def run_binds_arm(items: list, gw_key: str) -> None:
    """The bare+binds arm: the SAME bare authoring call, then the
    frozen machine's bind check + repair loop over the authored bill.
    The machine's loop is driven with the authored bill as the START
    of the repair cycle: scan it, and if findings fire, run the
    machine's own repair directive + regeneration (budget 3)."""
    from r29_a1w_v72_contract import contract_for_v72
    contract = contract_for_v72("intervention-proposal")
    for prob in items:
        pid = prob["problem_id"]
        outp = OUT / f"binds_{pid}.json"
        if outp.exists():
            print(f"  binds {pid}: SKIP (byte-resume)", flush=True)
            continue
        # (1) the SAME one-call bare authoring (byte-identical prompt)
        try:
            authored = bare_call(prob)
        except Exception as e:  # noqa: BLE001
            (OUT / f"binds_{pid}.TYPED_FAIL").write_text(
                f"authoring leg: {type(e).__name__}: {str(e)[:200]}\n",
                encoding="utf-8")
            continue
        # (2) the frozen machine's bind scans over the authored bill
        q = json.dumps(prob, ensure_ascii=False)
        try:
            final, attempts, final_meta = _author_then_repair(
                prob, q, authored, contract, gw_key)
        except Exception as e:  # noqa: BLE001
            (OUT / f"binds_{pid}.TYPED_FAIL").write_text(
                f"repair leg: {type(e).__name__}: {str(e)[:200]}\n",
                encoding="utf-8")
            print(f"  binds {pid}: TYPED_FAIL {type(e).__name__}",
                  flush=True)
            time.sleep(60)
            continue
        rec = {
            "problem_id": pid,
            "registered_model": V,
            "arm": "bare_plus_binds (the bare authoring + the frozen "
                   "machine's bind check/repair over the authored bill)",
            "authored_bill": authored,
            "delivered_bill": final,
            "attempts": attempts,
            "final_meta": final_meta,
        }
        outp.write_text(json.dumps(rec, indent=1,
                                   ensure_ascii=False) + "\n",
                        encoding="utf-8")
        res = final_meta.get("residual_findings") or {}
        print(f"  binds {pid}: authored {len(authored)}c -> delivered "
              f"{len(final)}c, repairs {len(attempts)-1}, residual "
              f"{sorted(res.keys())}", flush=True)
        time.sleep(10)


def _author_then_repair(prob: dict, q: str, authored: str,
                        contract: str, gw_key: str):
    """The machine's own scan->repair cycle seeded with the AUTHORED
    bill (never re-authored from scratch): mirror of machine_generate_
    v79's loop body with the first _gen_fb call REPLACED by the bare
    authoring (the prereg's arm definition), the scans/directive/
    budget byte-identical to m77's."""
    from collections import Counter
    vio = m77.base_scan(authored)
    vio.update(m77.scan_deliverable_class(authored))
    vio.update(m77.scan_stated_formula_direction(authored))
    vio.update(m77.scan_constraint_fit(prob, authored))
    vio.update(m77.scan_catalog(prob, authored))
    sb = m77.scan_standard_bill(authored, "intervention-proposal")
    if sb:
        vio.update(sb)
    ol = m77.scan_operational_loss(authored,
                                   "intervention-proposal")
    if ol:
        vio.update(ol)
    cv = m77.scan_conversion(authored, "intervention-proposal", prob)
    if cv:
        vio.update(cv)
    vio.update(m77.scan_allowed_measures_class(prob, authored))
    vio.update(m77.scan_physics_direction(prob, authored))
    vio.update(m77.direction_lexicon_check(prob, authored))
    vio.update(m77.scan_input_availability(prob, authored))
    vio.update(m77.scan_duty_cycle_pricing(authored))
    findings = [f"{k}: {'; '.join(map(str, v))[:110]}"
                for k, v in vio.items() if v]
    final = authored
    attempts = [{
        "stage": "authored", "chars": len(authored),
        "scan": {k: list(v) for k, v in vio.items()},
    }]
    rep = 0
    residual = dict(vio)
    while findings and rep < m77.REPAIR_BUDGET:
        directive = m77.V77_REPAIR_DIRECTIVE.format(
            findings="; ".join(findings))
        final, gen_meta = m77._retry_call(
            m77._gen_fb, q + "\n\n" + directive, contract, gw_key)
        rep += 1
        # re-scan the repaired bill (the machine's own loop shape)
        vio2 = m77.base_scan(final)
        vio2.update(m77.scan_constraint_fit(prob, final))
        vio2.update(m77.scan_input_availability(prob, final))
        vio2.update(m77.scan_duty_cycle_pricing(final))
        vio2.update(m77.scan_allowed_measures_class(prob, final))
        vio2.update(m77.scan_physics_direction(prob, final))
        findings = [f"{k}: {'; '.join(map(str, v))[:110]}"
                    for k, v in vio2.items() if v]
        attempts.append({
            "stage": f"repair_{rep}", "chars": len(final),
            "scan": {k: list(v) for k, v in vio2.items()},
        })
        residual = dict(vio2)
    final_meta = {
        "stop_reason": ("CONVERGED_ZERO_FINDINGS"
                        if not findings else "BUDGET_EXHAUSTED"),
        "repairs": rep,
        "residual_findings": {k: list(v) for k, v in residual.items()
                              if v},
    }
    return final, attempts, final_meta


def main() -> int:
    which = "all"
    if "--bare-only" in sys.argv:
        which = "bare"
    if "--binds-only" in sys.argv:
        which = "binds"
    items = [json.loads(l) for l in
             SET.read_text(encoding="utf-8").strip().split("\n")]
    items.sort(key=lambda p: p["problem_id"])
    print(f"F31a authoring run: {len(items)} items, mode={which}",
          flush=True)

    if which in ("all", "bare"):
        print("--- BARE_ONLY arm ---", flush=True)
        run_bare_only(items)

    if which in ("all", "binds"):
        print("--- BARE_PLUS_BINDS arm (gateway start) ---",
              flush=True)
        if r97._gateway_alive():
            print("REFUSED (typed): a gateway is already listening on "
                  "127.0.0.1:8787 — kill it first", flush=True)
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
            run_binds_arm(items, gw_key)
        finally:
            gw.terminate()
            print("gateway terminated", flush=True)

    n_bare = len(list(OUT.glob("bare_*.txt")))
    n_binds = len(list(OUT.glob("binds_*.json")))
    print(f"\nDONE: bare {n_bare}/24, binds {n_binds}/24 "
          f"(typed fails: {len(list(OUT.glob('*.TYPED_FAIL')))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
