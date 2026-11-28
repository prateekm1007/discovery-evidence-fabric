#!/usr/bin/env python3
"""r29_tune_battery_v74.py — the AM27 D2 continuation round 2 (claim
c-0028, the V7.4 DEPLOYED-PART-NO-MODIFICATION micro-round): re-draw
the ONE V7.3 row whose residual evidence is a modification of the
stated device (bench-p04 — the groove), under the BYTE-UNCHANGED
SYS_A1_INT_V72 contract with the pre-registered V74 directive and
REPAIR_BUDGET=3.

Pre-registered under claim c-0027 (Art. 29(b) claim-before-work,
pushed BEFORE this module's first LLM call). The set is EXACTLY the
V7.2 rows whose final CONVERSION scan read is non-clean (pinned by
tests/test_r29_v73_round.py, which recomputes the set from the
committed r29_v72_tuned bytes):

  bench-p04-pump-cavitation     (SURFACE_TREATMENT_DEV intact)
  bench-p08-mems-stiction       (ADDED_PROCESS_STEP intact)
  bench-p11-spindle-thermal-drift (BONDED_INTERFACE_DEV intact)
  eval-new01-supercap-dryout    (MATERIAL_FUNCTION_CLAIM intact)
  eval-new03-insulin-pump-occlusion
                                (ADDED_SENSING_CHANNEL intact)

The machine path is the V7.2 path BYTE-UNCHANGED in logic (one
generation pass under contract_for_v72 + critic + question-type
gate + typed scans [base + constraint-fit + catalog-v2 +
standard-bill + operational-loss + conversion] + NEUTRAL repair
directives, K_GEN=1, judge-blind) with two pre-registered deltas:
the V73_RELOCATION_DIRECTIVE (blunter about what a CONVERSION
finding means — the mechanism class itself is out of scope, never a
relabel) and REPAIR_BUDGET=3 (measured basis on the claim: 5/10
rows exhausted budget 2 with the class intact).

The 5 clean-converted V7.2 rows and the 20 frozen rows are never
re-drawn (Art. 29(c)). Tuned rows persist per-row to
eval/pairs/r29_v73_tuned/ (resumable; existing files skipped).
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
from r29_v74_directive import (  # noqa: E402
    V74_FLAGGED, V74_REPAIR_DIRECTIVE)
from r29_conversion_scan import scan_conversion  # noqa: E402
from r29_operational_loss_scan import scan_operational_loss  # noqa: E402
from r27_standard_bill_scan import scan_standard_bill  # noqa: E402
from r26_catalog_scan import scan_catalog  # noqa: E402
from r24_constraint_scan import scan_constraint_fit  # noqa: E402
from r22_a1w_v5_repair import scan as base_scan  # noqa: E402
from r11_a1f_v3_generate import start_gateway  # noqa: E402
from r13_a1t_generate import _gen, critic  # noqa: E402
from r13_question_type_gate import gate_question_type  # noqa: E402

OUT_DIR = REPO / "eval" / "pairs" / "r29_v74_tuned"
LEDGER = REPO / "eval" / "r29_v74_tuning_generation.json"
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


def machine_generate_v74(prob: dict, gw_key: str):
    """The V7.3 machine: the V7.2 path with the V73 relocation
    directive and budget 3. Judge-blind: no outcome feedback, no
    judged numbers — typed findings and class relocations only."""
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
            ol = scan_operational_loss(final, qt)
            if ol:
                vio.update(ol)
            cv = scan_conversion(final, qt, prob)
            if cv:
                vio.update(cv)
        else:  # pragma: no cover — the V7.3 set is interventions only
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
        directive = V74_REPAIR_DIRECTIVE.format(
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
    print(f"[r29-tune-v74] gateway up; {len(V74_FLAGGED)} rows to tune "
          f"(existing files skipped — never re-drawn)", flush=True)
    ledger = {"rows": {}}
    try:
        for pid in V74_FLAGGED:
            dst = OUT_DIR / f"{pid}.json"
            if dst.exists():
                print(f"  [tune] {pid[:36]:<38} exists (skip)", flush=True)
                continue
            prob = probs[pid]
            assert prob, f"problem not found: {pid}"
            assert str(prob.get("question_type", "")).startswith(
                "intervention"), pid
            t0 = time.time()
            ans, attempts, meta = machine_generate_v74(prob, gw_key)
            dst.write_text(
                json.dumps({"problem_id": pid,
                            "a1_source": "SYS_A1_INT_V72/r29_a1w_v72_contract"
                                         "+V74_DIRECTIVE",
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
        ledger["record"] = "R29_V74_TUNING_GENERATION/1.0.0"
        ledger["at"] = _now()
        ledger["machine"] = ("contract_for_v72 BYTE-UNCHANGED + critic + "
                            "type gate + typed scans (base + constraint-"
                            "fit + catalog v2 + standard-bill + "
                            "operational-loss r29 + conversion r29) + the "
                            "V74 directive (the V73 RELOCATION directive "
                            "+ the DEPLOYED-PART clause: the stated "
                            "device's parts are used AS-IS — no "
                            "machining/grooving/cutting/grinding/texturing/"
                            "coating/reprofiling of the deployed part in "
                            "any form; catalog parts AS-SOLD on the "
                            "SURROUNDING system + schedules/duty cycles/"
                            "operating-point changes) + NEUTRAL repairs "
                            "budget 3 (same pre-registered basis as "
                            "c-0027); K_GEN=1; judge-blind")
        ledger["tuning_set"] = V74_FLAGGED
        ledger["tuning_set_basis"] = (
            "EXACTLY the V7.3 rows whose residual evidence row is a "
            "MODIFICATION of the stated device (bench-p04: the "
            "circumferential-groove machining row; recomputed from the "
            "committed r29_v73_tuned bytes; pinned in tests/"
            "test_r29_v74_round.py)")
        ledger["frozen_rows_note"] = (
            "the 4 clean-converted V7.3 rows (bench-p08, bench-p11, "
            "eval-new01, eval-new03) stay byte-frozen in eval/pairs/"
            "r29_v73_tuned/; the 5 clean-converted V7.2 rows stay in "
            "eval/pairs/r29_v72_tuned/; the 20 frozen battery rows "
            "stay in eval/pairs/r26_v7_catalog/; never re-drawn "
            "(Art. 29(c))")
        LEDGER.write_text(json.dumps(ledger, indent=1,
                                     ensure_ascii=False) + "\n",
                          encoding="utf-8")
        print(f"[r29-tune-v74] ledger -> {LEDGER.relative_to(REPO)}",
              flush=True)
    bad = [pid for pid, r in ledger["rows"].items()
           if any(k in r["residual_findings"]
                  for k in ("STANDARD_BILL", "UNPRICED_OPERATIONAL_LOSS",
                            "CONVERSION", "NAMED_VARIANT"))]
    if bad:
        print(f"[r29-tune-v74] V7.3 residuals remain on: {bad} "
              f"(typed, disclosed)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
