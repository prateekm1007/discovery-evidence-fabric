#!/usr/bin/env python3
"""r30_tune_battery_v75.py — the AM29 D1+D2 verification round (claim
c-0031): re-draw the 3 residual gap-1 rows + the F40 row under the
V7.5 machine (the V7.4 machine path + the V75 CONVERSION directive,
pre-registered in scripts/r30_v75_directive.py and pushed BEFORE any
LLM call).

Pre-registered under claim c-0031 (Art. 29(b) claim-before-work).
The machine path is the V7.4 path BYTE-UNCHANGED in logic (one
generation pass under contract_for_v72 + critic + question-type gate
+ typed scans [base + constraint-fit + catalog-v2 + standard-bill +
operational-loss + conversion] + the machine's own NEUTRAL repair
directive, budget 3, K_GEN=1, judge-blind) with exactly ONE change:
the repair directive gains the three V75 conversion clauses
(EXEMPLAR-REALITY / PREMISE-VALIDITY / CERTIFIED-SYSTEM-AS-SOLD) on
top of the V7.4 DEPLOYED-PART clause, both pre-registered.

The 4-row re-draw set (the auditor's AM28 residuals + F40):
  bench-p09-packaging-barrier     (silica-nanoparticle sheet catalog
                                   reality unproven)
  bench-p11-spindle-thermal-drift ("existing hydraulic ports" premise
                                   assumption)
  eval-new03-insulin-pump-occlusion (0.1 mm bypass-lumen catheter =
                                   new infusion-set design +
                                   regulatory path)
  bench-p10-pv-pid                (F40: SentryGlas ionoplast
                                   misattributed as a sodium-barrier
                                   film — recompose on a real
                                   ion-barrier exemplar class,
                                   SiOx-coated PET, datasheet-sourced)

All other rows stay BYTE-FROZEN at their committed battery bytes.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
import os  # noqa: E402
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
os.environ.setdefault("FABRIC_BREAKER_THRESHOLD", "60")
os.environ.setdefault(
    "ZAI_GATEWAY_LOG",
    str(REPO / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"))

from r29_a1w_v72_contract import contract_for_v72  # noqa: E402
from r30_v76_directive import V76_REPAIR_DIRECTIVE  # noqa
from r30_allowed_class_scan import scan_allowed_measures_class  # noqa
from r30_physics_direction_scan import scan_physics_direction  # noqa
from r29_conversion_scan import scan_conversion  # noqa: E402
from r29_operational_loss_scan import scan_operational_loss  # noqa: E402
from r27_standard_bill_scan import scan_standard_bill  # noqa: E402
from r26_catalog_scan import scan_catalog  # noqa: E402
from r24_constraint_scan import scan_constraint_fit  # noqa: E402
from r22_a1w_v5_repair import scan as base_scan  # noqa: E402
from r11_a1f_v3_generate import start_gateway  # noqa: E402
from r13_a1t_generate import _gen, critic  # noqa: E402
from r30_nvidia_route import gen_with_fallback  # noqa: E402


def _gen_fb(prompt: str, contract: str, gw_key: str):
    """Typed transport: the primary local z.ai gateway first; on an
    auth error (the R31 401) fall back to the NVIDIA NIM route
    serving the same GLM-5.3-flash family. Returns
    (content, route_meta); the route that served every call is
    recorded in the row ledger (disclosed, never hidden)."""
    return gen_with_fallback(prompt, contract, gw_key, primary_gen=_gen)
from r13_question_type_gate import gate_question_type  # noqa: E402

OUT_DIR = REPO / "eval" / "pairs" / "r30_v76_tuned"
LEDGER = REPO / "eval" / "r30_v76_tuning_generation.json"
PACKET = REPO / "eval" / "r27_judge_packet.json"
REPAIR_BUDGET = 3


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _now() -> str:
    return (datetime.datetime.now(datetime.UTC).isoformat()
            .replace("+00:00", "Z"))


def _retry_call(f, *args, tries=5, backoff=(10.0, 30.0, 60.0, 120.0)):
    last = None
    for t in range(tries):
        try:
            return f(*args)
        except Exception as e:  # noqa: BLE001 — typed infra retry (Art. 15)
            last = e
            if t < tries - 1:
                time.sleep(backoff[t] if t < len(backoff)
                           else backoff[-1])
                print(f"    [retry {t+1}] {type(e).__name__}: "
                      f"{str(e)[:90]}", flush=True)
    raise last


def machine_generate_v76(prob: dict, gw_key: str):
    """The V7.5 machine: the V7.4 path with the V75 CONVERSION
    directive and budget 3. Judge-blind: no outcome feedback, no
    judged numbers — typed findings and clause relocations only."""
    qt = (prob.get("question_type") or "").lower()
    q = json.dumps(prob, ensure_ascii=False)
    contract = contract_for_v72(qt)
    attempts = []
    final, gen_meta = _retry_call(_gen_fb, q, contract, gw_key)
    lat = gen_meta["latency_s"]
    tries = 1
    final_meta = {}
    rep = 0
    while True:
        cr = _retry_call(critic, final, prob)
        tg = gate_question_type(final, prob)
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
        else:  # pragma: no cover — the set is interventions only
            from r19_a1w_v4_contract import predictor_violations
            pv = predictor_violations(final)
            if pv:
                vio.update({"PREDICTOR_VIOLATION": list(pv)})
        findings = [f"{k}: {'; '.join(map(str, v))[:110]}"
                    for k, v in vio.items() if v]
        problems: list = []
        if cr["verdict"] != "CLEAN":
            problems += [c.get("anchor") for c in cr["checks"]
                         if c.get("verdict") != "CLEAN"]
        if tg["verdict"] == "MISMATCH":
            problems.append(tg["reason"])
        problems += findings
        att = {"stage": ("draft" if rep == 0 else f"repair_{rep}"),
               "chars": len(final), "latency_s": round(lat, 1),
               "transport_tries": tries,
               "route": gen_meta.get("route"),
               "route_model": gen_meta.get("model"),
               "fallback_reason": gen_meta.get("fallback_reason"),
               "critic_verdict": cr["verdict"], "type_gate": tg,
               "scan": {k: list(v) for k, v in vio.items()},
               "sha256_16": _sha(final)}
        if rep:
            att["findings_disclosed"] = [p for p in problems if p]
        attempts.append(att)
        if not [p for p in problems if p]:
            final_meta = {"critic_verdict": cr["verdict"],
                          "type_gate": tg, "repairs": rep,
                          "residual_findings": {}}
            return final, attempts, final_meta
        if rep == REPAIR_BUDGET:
            final_meta = {"critic_verdict": cr["verdict"],
                          "type_gate": tg, "repairs": rep,
                          "residual_findings":
                              {k: list(v) for k, v in vio.items()}}
            return final, attempts, final_meta
        directive = V76_REPAIR_DIRECTIVE.format(
            findings="; ".join(p for p in problems if p))
        final, gen_meta = _retry_call(
            _gen_fb, q + "\n\n" + directive, contract, gw_key)
        lat = gen_meta["latency_s"]
        tries += 1
        rep += 1


def _prob_map() -> dict:
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    return {r["problem_id"]: r["problem"] for r in packet["rows"]}


def _intervention_ids() -> list:
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    return [r["problem_id"] for r in packet["rows"]
            if str(r["problem"].get("question_type", "")).startswith(
                "intervention")]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    probs = _prob_map()
    gw, gw_key = start_gateway()
    V76_ROWS = _intervention_ids()
    print(f"[r30-tune-v76] gateway up; {len(V76_ROWS)} rows to "
          f"convert (existing files skipped — never re-drawn)",
          flush=True)
    ledger = {"rows": {},
              "tuning_set": list(V76_ROWS),
              "claim": "c-0031 (pre-registered, pushed BEFORE any LLM "
                       "call; the directive module r30_v75_directive.py "
                       "is committed in the same push)",
              "directive": "V75 = V74 DEPLOYED-PART clause + "
                           "EXEMPLAR-REALITY + PREMISE-VALIDITY + "
                           "CERTIFIED-SYSTEM-AS-SOLD (pre-registered)"}
    try:
        for pid in V76_ROWS:
            dst = OUT_DIR / f"{pid}.json"
            if dst.exists():
                print(f"  [v76] {pid[:36]:<38} exists (skip)", flush=True)
                continue
            prob = probs[pid]
            assert prob, f"problem not found: {pid}"
            assert str(prob.get("question_type", "")).startswith(
                "intervention"), pid
            t0 = time.time()
            ans, attempts, meta = machine_generate_v76(prob, gw_key)
            dst.write_text(
                json.dumps({"problem_id": pid,
                            "a1_source":
                                "SYS_A1_INT_V72+V76/r30_v76_directive",
                            "question_type": prob.get("question_type"),
                            "a1_answer": ans, "meta": meta,
                            "attempts": attempts,
                            "generated_at": _now()},
                           indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            ledger["rows"][pid] = {
                "repairs": meta["repairs"],
                "residual_findings": meta["residual_findings"],
                "attempts": attempts}
            (REPO / "eval" / "r30_v76_tuning_generation.json").write_text(
                json.dumps(ledger, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            print(f"  [v76] {pid[:36]:<38} repairs={meta['repairs']} "
                  f"residual={list(meta['residual_findings']) or 'CLEAN'} "
                  f"({time.time()-t0:.0f}s)", flush=True)
    finally:
        gw.terminate()
    print(f"-> {OUT_DIR} + {LEDGER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main() or 0)
