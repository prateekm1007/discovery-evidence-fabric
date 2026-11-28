#!/usr/bin/env python3
"""r29_tune_battery.py — the AM27 D2 V7.2 CONVERSION tuning
generation: re-draw the adjudicated gap>=1 rows + bench-p10 under
SYS_A1_INT_V72 (V7.1 + the CONVERSION BIND).

Pre-registered under claim c-0025 (Art. 29(b) claim-before-work,
pushed BEFORE this module's first LLM call). The machine path is the
r27 path BYTE-UNCHANGED in logic (one generation pass under the
contract + critic + question-type gate + typed scans + the machine's
own NEUTRAL repair directives, REPAIR_BUDGET=2, K_GEN=1) with the
V7.2 additions, all pre-registered:

  1. the contract is contract_for_v72 (V7.2 = V7.1 + the CONVERSION
     BIND: premise validity J, forbidden classes 5-9, operational-
     loss pricing L);
  2. two new typed scan legs on interventions: the conversion scan
     (scripts/r29_conversion_scan.py — the six classes) and the
     operational-loss scan (scripts/r29_operational_loss_scan.py —
     F38), alongside the unchanged base + constraint-fit + catalog
     v2 + standard-bill legs;
  3. the repair directive is V72_REPAIR_DIRECTIVE (neutral: typed
     findings only, with the relocation instructions — NO outcome
     feedback, NO judged numbers in any prompt).

The pre-registered 10-row tuning set (the auditor's 18-row
re-judgment at d7540c6fe: 8 rows at gap 1 + bench-p06 at gap 2,
PLUS bench-p10 for the F38 pricing — the adjudication names p01
gap-1 in per_row, so the set covers both the verdict prose's
"seven" enumeration and the per-row record):

  bench-p01-pemfc-dehydration   (MATERIAL_FUNCTION_CLAIM + brand rows)
  bench-p04-pump-cavitation     (SURFACE_TREATMENT_DEV — the auditor's
                                 "micro-roughened vane")
  bench-p06-water-biofilm       (PREMISE_TOPOLOGY_INVALID — the
                                 auditor self-correction)
  bench-p08-mems-stiction       (SURFACE + ADDED_PROCESS — "MEMS
                                 dimples")
  bench-p09-packaging-barrier   (ADDED_PROCESS — "silica interlayer")
  bench-p10-pv-pid              (UNPRICED_OPERATIONAL_LOSS — F38,
                                 the ~33% daily curtailment)
  bench-p11-spindle-thermal-drift (BONDED_INTERFACE_DEV — "Al-on-
                                 steel sleeve")
  eval-new01-supercap-dryout    (MATERIAL_FUNCTION_CLAIM — "silica
                                 packet" solvent reabsorption)
  eval-new03-insulin-pump-occlusion (ADDED_SENSING_CHANNEL — "added
                                 sensor channel")
  eval-sofc-thermal-cycling     (the r27 CUSTOM_MATERIAL residual —
                                 "graded co-firing"; that scan leg
                                 stays wired and the V72 directive
                                 names the relocation)

The other 20 rows stay BYTE-FROZEN (never re-drawn, Art. 29(c)) —
per-row provenance typed in eval/battery_v7_2_catalog_r29.json by
the assembler. Tuned rows persist per-row to
eval/pairs/r29_v72_tuned/ (resumable: existing files are never
re-drawn; the r26/r27 sandbox-reaper lesson — foreground chunks,
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

from r29_a1w_v72_contract import (  # noqa: E402
    contract_for_v72, V72_REPAIR_DIRECTIVE)
from r29_conversion_scan import scan_conversion  # noqa: E402
from r29_operational_loss_scan import scan_operational_loss  # noqa: E402
from r27_standard_bill_scan import scan_standard_bill  # noqa: E402
from r26_catalog_scan import scan_catalog  # noqa: E402
from r24_constraint_scan import scan_constraint_fit  # noqa: E402
from r22_a1w_v5_repair import scan as base_scan  # noqa: E402
from r19_a1w_v4_contract import predictor_violations  # noqa: E402
from r11_a1f_v3_generate import start_gateway  # noqa: E402
from r13_a1t_generate import _gen, critic  # noqa: E402
from r13_question_type_gate import gate_question_type  # noqa: E402

OUT_DIR = REPO / "eval" / "pairs" / "r29_v72_tuned"
LEDGER = REPO / "eval" / "r29_tuning_generation.json"
REPAIR_BUDGET = 2

FLAGGED = [
    "bench-p01-pemfc-dehydration",
    "bench-p04-pump-cavitation",
    "bench-p06-water-biofilm",
    "bench-p08-mems-stiction",
    "bench-p09-packaging-barrier",
    "bench-p10-pv-pid",
    "bench-p11-spindle-thermal-drift",
    "eval-new01-supercap-dryout",
    "eval-new03-insulin-pump-occlusion",
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


def machine_generate_v72(prob: dict, gw_key: str):
    """The V7.2 machine: one generation pass under contract_for_v72 +
    critic + question-type gate + typed scans (base + constraint-fit +
    catalog v2 + standard-bill + operational-loss + conversion) +
    NEUTRAL repair directives (V72_REPAIR_DIRECTIVE, budget 2).
    Judge-blind: no outcome feedback, no judged numbers — the
    structural binds only."""
    qt = (prob.get("question_type") or "").lower()
    q = json.dumps(prob, ensure_ascii=False)
    contract = contract_for_v72(qt)
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
            sb = scan_standard_bill(final, qt)
            if sb:
                vio.update(sb)
            # the V7.2 typed legs (AM27 D1/D2)
            ol = scan_operational_loss(final, qt)
            if ol:
                vio.update(ol)
            cv = scan_conversion(final, qt, prob)
            if cv:
                vio.update(cv)
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
        directive = V72_REPAIR_DIRECTIVE.format(
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
    print(f"[r29-tune] gateway up; {len(FLAGGED)} rows to tune "
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
            ans, attempts, meta = machine_generate_v72(prob, gw_key)
            dst.write_text(
                json.dumps({"problem_id": pid,
                            "a1_source": "SYS_A1_INT_V72/r29_a1w_v72_contract",
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
        ledger["record"] = "R29_V72_TUNING_GENERATION/1.0.0"
        ledger["at"] = _now()
        ledger["machine"] = ("contract_for_v72 (V7.1 + CONVERSION BIND: "
                            "premise validity J, forbidden classes 5-9, "
                            "operational-loss pricing L) + critic + type "
                            "gate + typed scans (base + constraint-fit + "
                            "catalog v2 + standard-bill + operational-loss "
                            "r29 + conversion r29) + NEUTRAL repairs "
                            "budget 2 (V72_REPAIR_DIRECTIVE); K_GEN=1; "
                            "judge-blind (no outcome feedback, no judged "
                            "numbers in any prompt — the AM27 directions "
                            "are structural binds)")
        ledger["tuning_set"] = FLAGGED
        ledger["tuning_set_basis"] = (
            "the auditor's 18-row re-judgment at audit tip d7540c6fe:"
            "eval/auditor_r28_adjudication.json per_row — the gap>=1 "
            "set (8 rows at gap 1 incl. bench-p01 per the per-row "
            "record; bench-p06 at gap 2) PLUS bench-p10 for the F38 "
            "operational-loss pricing (AM27 D1); pins: tests/"
            "test_r29_conversion_scan.py (9 positive pins on the "
            "current-battery bytes) + tests/test_r29_operational_loss_"
            "scan.py (the bench-p10 pin)")
        ledger["frozen_rows_note"] = (
            "the other 20 rows stay BYTE-FROZEN (the 8 gap-0 "
            "intervention rows in eval/pairs/r26_v7_catalog/ and the "
            "12 predictor rows; never re-drawn, Art. 29(c)) — per-row "
            "provenance typed in eval/battery_v7_2_catalog_r29.json")
        LEDGER.write_text(json.dumps(ledger, indent=1,
                                     ensure_ascii=False) + "\n",
                          encoding="utf-8")
        print(f"[r29-tune] ledger -> {LEDGER.relative_to(REPO)}", flush=True)
    # non-zero disclosure if any row still carries V7.2 residuals —
    # the honest typed disclosure (the assembler discloses residuals;
    # the tuning does NOT silently accept them)
    bad = [pid for pid, r in ledger["rows"].items()
           if any(k in r["residual_findings"]
                  for k in ("STANDARD_BILL", "UNPRICED_OPERATIONAL_LOSS",
                            "CONVERSION", "NAMED_VARIANT"))]
    if bad:
        print(f"[r29-tune] V7.2 residuals remain on: {bad} "
              f"(typed, disclosed)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
