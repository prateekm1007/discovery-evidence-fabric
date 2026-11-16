#!/usr/bin/env python3
"""r38_deepseek_c0026_interventions.py — the c-0026 INTERVENTION axis
(18 rows) on the deepseek rung (claim c-0043), via the UNEDITED
pre-registered r29 harness: this wrapper sets the harness's own env
override (R12_JUDGE_PROVIDER/R12_JUDGE_MODEL) BEFORE import so
prompt bytes, ladder, K and pace are IDENTICAL, and reassigns the
harness's OUT/PARTIAL module constants to deepseek-named paths so
the committed qwen record (eval/judge_feasibility_calibration_r29.json)
is NEVER touched.

GATE: refuses to run unless the rung qualified
(eval/deepseek_rung_qualification_r38.json gate==PASS, R-JUDGE).
"""
import datetime
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
os.environ.setdefault("R12_JUDGE_PROVIDER", "crowllm")
os.environ.setdefault("R12_JUDGE_MODEL", "deepseek-v4-flash:free")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
os.environ.setdefault("FABRIC_BREAKER_THRESHOLD", "60")
os.environ.setdefault(
    "ZAI_GATEWAY_LOG",
    str(REPO / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"))

import r29_judge_calibration as r29  # noqa: E402

QUAL_GATE = REPO / "eval" / "deepseek_rung_qualification_r38.json"
DS_PARTIAL = REPO / "eval" / "judge_feasibility_calibration_r29_deepseek.partial.json"
DS_OUT = REPO / "eval" / "judge_feasibility_calibration_r29_deepseek.json"


def main() -> int:
    q = json.loads(QUAL_GATE.read_text(encoding="utf-8")) \
        if QUAL_GATE.exists() else {}
    if q.get("gate") != "PASS":
        print(f"[gate] rung NOT qualified ({q.get('gate')}) — run "
              f"refused; the deepseek rung stays retired (R-JUDGE)")
        return 2
    print(f"[gate] rung qualified: gold accuracy="
          f"{q['stages']['3_gold_calibration_engine'].get('accuracy')}")
    # route the harness's artifacts to the deepseek names — the
    # committed qwen record files are never opened for write
    r29.PARTIAL = DS_PARTIAL
    r29.OUT = DS_OUT
    r29.RUN_LOG = REPO / "ENGINE_RUNS" / "r38_deepseek_interventions.log"
    rc = r29.probe()
    if rc != 0:
        print(f"[probe] BLOCKED ({rc}) — typed; no judging")
        return rc
    rc = r29.run()
    if rc != 0:
        return rc
    rc = r29.assemble()
    if rc == 0:
        rec = json.loads(DS_OUT.read_text(encoding="utf-8"))
        rec["wrapper_provenance"] = {
            "claim": "c-0043 (builder-r20s2, base f85d0dbbf)",
            "authorization": ("R-JUDGE: deepseek rung ELIGIBLE (gold "
                              ">=0.8); c-0026 may run on it"),
            "harness": ("scripts/r29_judge_calibration.py UNEDITED; "
                        "route via its R12_JUDGE_* env override; the "
                        "harness's own record fields (claim c-0026/"
                        "builder-r29s1) are its pre-registration "
                        "constants — the operative claim is c-0043"),
            "qwen_record_integrity": ("the pre-registered qwen "
                                      "measurement file was never "
                                      "written by this run (the "
                                      "harness's OUT/PARTIAL were "
                                      "reassigned before any call)"),
            "at": datetime.datetime.now(datetime.UTC).isoformat()}
        DS_OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                          + "\n", encoding="utf-8")
        acc = rec.get("acceptance") or {}
        print(json.dumps({"out": str(DS_OUT),
                          "n_within_1": acc.get("n_within_1"),
                          "met": acc.get("met")}, indent=1))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
