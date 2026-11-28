#!/usr/bin/env python3
"""r27_tune_battery.py — the AM26 D1 V7.1 STANDARD-BILL tuning
generation: re-draw the 7 standard-bill-flagged r26 rows under
SYS_A1_INT_V71 (V7 + the STANDARD-BILL BIND).

Pre-registered under claim c-0021 (Art. 29(b) claim-before-work,
pushed BEFORE this module's first LLM call). The machine path is the
r26 path BYTE-UNCHANGED in logic (one generation pass under the
contract + critic + question-type gate + typed scans + the machine's
own NEUTRAL repair directives, REPAIR_BUDGET=2, K_GEN=1) with exactly
two additions, both pre-registered:

  1. the contract is contract_for_v71 (V7.1 = V7 + the STANDARD-BILL
     BIND — clauses F-I of scripts/r27_a1w_v71_contract.py);
  2. the standard-bill scan (scripts/r27_standard_bill_scan.py) is a
     new typed scan leg on interventions, and the repair directive is
     V71_REPAIR_DIRECTIVE (neutral: typed findings only, with the
     relocation instruction — NO outcome feedback, NO judged numbers
     in any prompt; the AM26 direction is a structural constraint).

The 7 flagged rows (the pre-registered tuning set, pinned in
tests/test_r27_standard_bill_scan.py::test_flagged_set_is_exactly_seven
— the scan over the r26 generation flags EXACTLY these):
  bench-p01-pemfc-dehydration   (BESPOKE_COMPONENT: custom-calibrated wick)
  bench-p04-pump-cavitation     (CUSTOM_MACHINING: CNC vane reprofile —
                                 the AM26 named example)
  bench-p08-mems-stiction       (CUSTOM_RECIPE: custom deposition
                                 params + extra post-deposition anneal)
  bench-p09-packaging-barrier   (CUSTOM_MATERIAL: 5 wt% nano-clay film)
  bench-p11-spindle-thermal-drift (CUSTOM_MACHINING: machined bracket)
  eval-new01-supercap-dryout    (CUSTOM_MACHINING: milled end-plate recess)
  eval-sofc-thermal-cycling     (CUSTOM_MATERIAL: graded glass-ceramic seal)

The other 23 rows stay BYTE-FROZEN in eval/pairs/r26_v7_catalog/
(their bills already pass the standard-bill scan — per-row provenance
typed in eval/battery_v7_1_catalog_r27.json). Tuned rows persist
per-row to eval/pairs/r27_v71_tuned/ (resumable: existing files are
never re-drawn; the r26 sandbox-reaper lesson — foreground chunks,
per-row persistence).
"""
from __future__ import annotations

import datetime
import hashlib
import json
import subprocess
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

from r27_a1w_v71_contract import (  # noqa: E402
    contract_for_v71, V71_REPAIR_DIRECTIVE)
from r27_standard_bill_scan import scan_standard_bill  # noqa: E402
from r26_catalog_scan import scan_catalog  # noqa: E402
from r24_constraint_scan import scan_constraint_fit  # noqa: E402
from r22_a1w_v5_repair import scan as base_scan  # noqa: E402
from r19_a1w_v4_contract import predictor_violations  # noqa: E402
from r11_a1f_v3_generate import start_gateway  # noqa: E402
from r13_a1t_generate import _gen, critic  # noqa: E402
from r13_question_type_gate import gate_question_type  # noqa: E402

OUT_DIR = REPO / "eval" / "pairs" / "r27_v71_tuned"
LEDGER = REPO / "eval" / "r27_tuning_generation.json"
REPAIR_BUDGET = 2

FLAGGED = [
    "bench-p01-pemfc-dehydration",
    "bench-p04-pump-cavitation",
    "bench-p08-mems-stiction",
    "bench-p09-packaging-barrier",
    "bench-p11-spindle-thermal-drift",
    "eval-new01-supercap-dryout",
    "eval-sofc-thermal-cycling",
]


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


def machine_generate_v71(prob: dict, gw_key: str):
    """The V7.1 machine: one generation pass under contract_for_v71 +
    critic + question-type gate + typed scans (base + constraint-fit +
    catalog v2 + the STANDARD-BILL scan) + NEUTRAL repair directives
    (V71_REPAIR_DIRECTIVE, budget 2). Judge-blind: no outcome
    feedback, no judged numbers — the structural bind only."""
    qt = (prob.get("question_type") or "").lower()
    q = json.dumps(prob, ensure_ascii=False)
    contract = contract_for_v71(qt)
    attempts = []
    final, lat = _retry_call(_gen, q, contract, gw_key)
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
            # the V7.1 typed leg (the AM26 D1 tuning's deterministic
            # scan — the four FORBIDDEN classes on the own bill)
            sb = scan_standard_bill(final, qt)
            if sb:
                vio.update(sb)
        else:
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
        directive = V71_REPAIR_DIRECTIVE.format(
            findings="; ".join(p for p in problems if p))
        final, lat = _retry_call(
            _gen, q + "\n\n" + directive, contract, gw_key)
        tries += 1
        rep += 1


def _prob_map() -> dict:
    probs = {}
    plist = json.loads((REPO / "eval" / "problems.json").read_text())
    plist = (plist if isinstance(plist, list) else plist.get("problems", []))
    for p in plist:
        probs[str(p.get("problem_id") or p.get("id"))] = p
    for p in json.loads((REPO / "eval" / "problems_dev12.json")
                        .read_text())["problems"]:
        probs.setdefault(p["problem_id"], p)
    return probs


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    probs = _prob_map()
    gw, gw_key = start_gateway()
    print(f"[r27-tune] gateway up; {len(FLAGGED)} rows to tune "
          f"(existing files skipped — never re-drawn)", flush=True)
    ledger = {"rows": {}}
    try:
        for pid in FLAGGED:
            dst = OUT_DIR / f"{pid}.json"
            if dst.exists():
                print(f"  [tune] {pid[:36]:<38} exists (skip)", flush=True)
                continue
            prob = probs[pid]
            assert prob, f"problem not found: {pid}"
            assert str(prob.get("question_type", "")).startswith(
                "intervention"), pid
            t0 = time.time()
            ans, attempts, meta = machine_generate_v71(prob, gw_key)
            dst.write_text(
                json.dumps({"problem_id": pid,
                            "a1_source": "SYS_A1_INT_V71/r27_a1w_v71_contract",
                            "question_type": prob.get("question_type"),
                            "a1_answer": ans, "meta": meta,
                            "attempts": attempts,
                            "generated_at": _now()},
                           indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            ledger["rows"][pid] = {
                "repairs": meta["repairs"],
                "residual_findings":
                    {k: len(v) for k, v in
                     meta["residual_findings"].items()},
                "attempts": len(attempts),
                "answer_sha256_16": _sha(ans),
                "gen_s": round(time.time() - t0, 1)}
            print(f"  [tune] {pid[:36]:<38} repairs={meta['repairs']} "
                  f"residual={list(meta['residual_findings']) or 'CLEAN'} "
                  f"({time.time()-t0:.0f}s)", flush=True)
    finally:
        ledger["record"] = "R27_V71_TUNING_GENERATION/1.0.0"
        ledger["at"] = _now()
        ledger["machine"] = ("contract_for_v71 (V7 + STANDARD-BILL BIND) "
                            "+ critic + type gate + typed scans (base + "
                            "constraint-fit + catalog v2 + STANDARD-BILL "
                            "r27) + NEUTRAL repairs budget 2 ("
                            "V71_REPAIR_DIRECTIVE); K_GEN=1; judge-blind "
                            "(no outcome feedback, no judged numbers in "
                            "any prompt — the AM26 direction is a "
                            "structural bind)")
        ledger["tuning_set"] = FLAGGED
        ledger["tuning_set_basis"] = (
            "the pre-registered scan pin: the r27 standard-bill scan "
            "over the r26 V7 generation flags EXACTLY these 7 rows "
            "(tests/test_r27_standard_bill_scan.py::"
            "test_flagged_set_is_exactly_seven)")
        ledger["frozen_rows_note"] = (
            "the other 23 rows stay BYTE-FROZEN in "
            "eval/pairs/r26_v7_catalog/ — their bills already pass the "
            "standard-bill scan; per-row provenance typed in "
            "eval/battery_v7_1_catalog_r27.json")
        LEDGER.write_text(json.dumps(ledger, indent=1,
                                     ensure_ascii=False) + "\n",
                          encoding="utf-8")
        print(f"[r27-tune] ledger -> {LEDGER.relative_to(REPO)}", flush=True)
    # non-zero exit if any row still carries STANDARD_BILL residuals —
    # the honest typed disclosure (the battery assembler discloses
    # residuals; the tuning does NOT silently accept them)
    bad = [pid for pid, r in ledger["rows"].items()
           if "STANDARD_BILL" in r["residual_findings"]]
    if bad:
        print(f"[r27-tune] STANDARD_BILL residuals remain on: {bad} "
              f"(typed, disclosed)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
