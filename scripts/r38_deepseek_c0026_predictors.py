#!/usr/bin/env python3
"""r38_deepseek_c0026_predictors.py — the c-0026 PREDICTOR axis on the
deepseek rung (claim c-0043; R-JUDGE authorised the rung after gold
>=0.8 — GATE: eval/deepseek_rung_qualification_r38.json gate==PASS).

Discipline (the peer's c-0042 rules, mirrored): the pre-registered
r29 harness is NOT edited — this sibling IMPORTS its functions so the
prompt bytes (v3 suffix substitution), transport ladder, K and pace
are IDENTICAL; the judge route comes from the harness's own env
override (R12_JUDGE_PROVIDER / R12_JUDGE_MODEL set BEFORE import).
Row selector = the packet complement (12 predictor rows, asserted).
The auditor's 12 predictor anchors ride `git show` from the audit tip
015340a3c (auditor bytes never copied into the queue tree).

Output: eval/c0026_predictor_axis_deepseek.json
Acceptance (AM34/35 D2): within +/-1 of the auditor on >=10/12
predictors (and >=16/18 interventions — the interventions run via the
unedited harness in the same claim).
"""
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# the route must be set BEFORE importing the harness (its module
# constants read the env at import time)
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
from eval.battery_metrics import parse_axes  # noqa: E402

AUDIT_TIP = "015340a3c"
ANCHOR_PATH = "eval/auditor_predictor_row_anchors.json"
OUT = REPO / "eval" / "c0026_predictor_axis_deepseek.json"
LOG = REPO / "ENGINE_RUNS" / "r38_deepseek_predictors.log"
ACCEPT_MIN = 10  # of 12
QUAL_GATE = REPO / "eval" / "deepseek_rung_qualification_r38.json"


def _log(msg):
    line = f"[{datetime.datetime.now(datetime.UTC).isoformat()}] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _predictor_rows():
    packet = json.loads(r29.PACKET.read_text(encoding="utf-8"))
    rows = [r for r in packet["rows"]
            if not str(r.get("question_type", "")).startswith(
                "intervention")]
    assert len(rows) == 12, f"expected 12 predictor rows: {len(rows)}"
    return rows


def _anchors():
    out = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{AUDIT_TIP}:{ANCHOR_PATH}"],
        capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def main() -> int:
    q = json.loads(QUAL_GATE.read_text(encoding="utf-8")) \
        if QUAL_GATE.exists() else {}
    if q.get("gate") != "PASS":
        _log(f"[gate] rung NOT qualified ({q.get('gate')}) — run "
             f"refused; the deepseek rung stays retired (R-JUDGE)")
        return 2
    _log(f"[gate] rung qualified: gold accuracy="
         f"{q['stages']['3_gold_calibration_engine'].get('accuracy')}")

    rows = _predictor_rows()
    anchors = {a["problem_id"]: a for a in _anchors()["rows"]}
    assert set(anchors) == {r["problem_id"] for r in rows}, \
        "anchor/packet row mismatch"

    partial = REPO / "eval" / "c0026_predictor_axis_deepseek.partial.json"
    prior = {}
    if partial.exists():
        for r in json.loads(partial.read_text(encoding="utf-8")):
            prior[r["problem_id"]] = r
    results = []
    t0 = time.time()
    for row in rows:
        pid = row["problem_id"]
        if pid in prior:
            results.append(prior[pid])
            continue
        prompt = r29._v3_prompt(row)
        assert prompt.endswith(r29.V3_SUFFIX)
        draws = []
        for k in range(r29.K):
            jc, outcome, atts = r29.judge_slot(pid, k, prompt)
            draws.append({"k": k, "outcome": outcome,
                          "axes": parse_axes(jc),
                          "transport_attempts": atts})
            if k < r29.K - 1:
                time.sleep(r29.PACE_S)
        valid = [d["axes"] for d in draws
                 if d["outcome"] == "JUDGE_VALID" and d["axes"]]
        f_vals = sorted(a["F_A"] for a in valid if "F_A" in a)
        n_vals = sorted(a["N_A"] for a in valid if "N_A" in a)
        rec = {"problem_id": pid,
               "question_type": row.get("question_type"),
               "judge": list(r29.JUDGE),
               "axis_suffix": "v3 (calibrated F pins)",
               "v3_prompt_sha256_16": r29._sha(prompt),
               "draws": draws,
               "n_valid_draws": len(valid),
               "machine_a1_feasibility_median":
                   f_vals[len(f_vals) // 2] if f_vals else None,
               "machine_a1_feasibility_values": f_vals,
               "machine_a1_novelty_median":
                   n_vals[len(n_vals) // 2] if n_vals else None}
        results.append(rec)
        partial.write_text(
            json.dumps(results, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
        _log(f"[run] {pid[:40]:<42} F_A={rec['machine_a1_feasibility_median']} "
             f"(vals {f_vals}) valid={rec['n_valid_draws']}/{r29.K} "
             f"({time.time()-t0:.0f}s)")
        _log(f"[run] rows done: {len(results)}/12")

    # ---- assemble vs the auditor's anchors ----
    comparison = []
    n_within = 0
    for r in results:
        a = anchors[r["problem_id"]]
        m_f = r["machine_a1_feasibility_median"]
        a_f = a["auditor_a1_feasibility"]
        entry = {"problem_id": r["problem_id"],
                 "machine_a1_feasibility": m_f,
                 "auditor_a1_feasibility": a_f,
                 "auditor_baseline_feasibility":
                     a.get("auditor_baseline_feasibility"),
                 "auditor_novelty_delta": a.get("auditor_novelty_delta"),
                 "machine_a1_novelty_median":
                     r["machine_a1_novelty_median"],
                 "n_valid_draws": r["n_valid_draws"]}
        if m_f is not None:
            d = m_f - a_f
            entry["delta"] = d
            entry["within_1"] = abs(d) <= r29.ACCEPT_WITHIN
            if entry["within_1"]:
                n_within += 1
        comparison.append(entry)

    acceptance = {
        "rule": ("c-0026 predictor axis: feasibility within +/-1 of "
                 "the auditor on >=10/12 predictor rows (AM34/35 D2), "
                 "against the published per-row anchors @015340a3c"),
        "n_rows": len(results),
        "n_compared": sum(1 for e in comparison
                          if e["machine_a1_feasibility"] is not None),
        "n_within_1": n_within,
        "met": n_within >= ACCEPT_MIN,
    }
    rec = {
        "record": "C0026_PREDICTOR_AXIS_DEEPSEEK/1.0.0",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "claim": "c-0043 (builder-r20s2, base f85d0dbbf)",
        "authorization": ("R-JUDGE: the deepseek rung is ELIGIBLE "
                          "(gold >=0.8) and c-0026 may run on it"),
        "rung_qualification": {"gate": q.get("gate"),
                               "gold_accuracy":
                                   q["stages"][
                                       "3_gold_calibration_engine"]
                                   .get("accuracy")},
        "judge": {"route": list(r29.JUDGE), "k": r29.K,
                  "pace_s": r29.PACE_S,
                  "axis_suffix": "v3 (calibrated F pins)",
                  "independence": ("crowllm/DeepSeek vs zai/GLM "
                                   "generator — provider AND family "
                                   "independent (Art. 10/26)")},
        "anchor": {"provenance": f"audit tip {AUDIT_TIP}:{ANCHOR_PATH}",
                   "n_rows": len(anchors)},
        "results": results,
        "comparison": comparison,
        "acceptance": acceptance,
        "generation": {"calls": 0,
                       "note": ("zero generator calls — pure judge "
                                "measurement on frozen packet bytes; "
                                "the builder never scores its own "
                                "generation (Art. 10)")},
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    _log(f"[assemble] {OUT.name}: within_1 {n_within}/12 -> "
         f"met={acceptance['met']}")
    print(json.dumps({"n_within_1": n_within, "met": acceptance["met"]},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
