#!/usr/bin/env python3
"""r19_a1w2_pilot.py — AM19 D2 (F30 iteration 3): V4 hard-7 pilot.

PRE-REGISTERED before any measurement (this file + the V4 contract are
committed before the results exist):
  - SUBSET (pre-declared): the intervention-question pairs of battery
    r11 with feasibility_abs_gap >= 2 — exactly 7 pairs (the HARD-7:
    bench-p03/p06 fgap=4, p05/p09/p11 fgap=3, eval-new05,
    eval-sofc-thermal-cycling fgap=2). Selection is from COMMITTED
    bytes (eval/battery_a1w_r11.json), typed in the record.
  - CONTRACT: SYS_A1_INT_V4 (scripts/r19_a1w_v4_contract.py) — the
    no-development/procurement rule; predictor arm UNCHANGED and NOT
    re-generated (the change is isolated to the intervention arm, as
    r16 isolated it).
  - JUDGING: the CANONICAL battery metric, unchanged (Art. 16):
    eval/run._rubric_prompt + scripts/_f28_axis_suffix_v2.txt +
    crowllm/qwen-3.8-max:free at t=0, K=3 draws, eval/battery_metrics
    parse_axes/row_metrics (strict plurality).
  - TYPE: MECHANICS_PILOT — a direction probe on 7 pairs; NOT the
    gate battery (>=30 pairs pre-registered elsewhere); acceptance
    rides committed real bytes only (Art. 22).
  - REPAIR BUDGET: 2 (standing machine budget), incl. the new V4
    ledger scan (DEV_NEED_MARKERS): a draft whose bill concedes a
    development program is repaired with the offending lines quoted.
"""
import datetime
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

from r19_a1w_v4_contract import SYS_A1_INT_V4, DEV_NEED_MARKERS  # noqa: E402
from r11_a1f_v3_generate import start_gateway  # noqa: E402
from r13_a1t_generate import _gen, critic  # noqa: E402
from r13_question_type_gate import gate_question_type  # noqa: E402
from eval.run import _rubric_prompt, _judge_judgment_call  # noqa: E402
from discovery_fabric.engine import llm_economy as econ  # noqa: E402
from eval.battery_metrics import parse_axes, row_metrics  # noqa: E402

OUT_DIR = REPO / "eval" / "pairs" / "r19_a1w2_pilot"
R11 = REPO / "eval" / "battery_a1w_r11.json"
PILOT_OUT = REPO / "eval" / "battery_a1w2_pilot_r19.json"
PILOT_PARTIAL = REPO / "eval" / "battery_a1w2_pilot_r19.partial.json"
JUDGE = (os.environ.get("R12_JUDGE_PROVIDER", "crowllm"),
         os.environ.get("R12_JUDGE_MODEL", "qwen-3.8-max:free"))
PACE_S = float(os.environ.get("R12_PACE_S", "13.0"))
K = 3
REPAIR_BUDGET = 2
AXIS_SUFFIX = (REPO / "scripts" / "_f28_axis_suffix_v2.txt").read_text()
now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

# --- pre-declared subset from committed r11 bytes --------------------
r11rows = {r["problem_id"]: r for r in json.loads(
    R11.read_text(encoding="utf-8"))["results"]}
HARD7 = sorted(
    pid for pid, r in r11rows.items()
    if str(r.get("question_type") or "").startswith("intervention")
    and (r.get("feasibility_abs_gap") or 0) >= 2)
assert len(HARD7) == 7, f"pre-declared hard-7 drifted: {HARD7}"

# --- pair assembly (identical baseline sourcing as battery r11) ------
plist = json.loads((REPO / "eval" / "problems.json").read_text())
plist = plist if isinstance(plist, list) else plist.get("problems", [])
probs = {str(p.get("problem_id") or p.get("id")): p for p in plist}
for p in json.loads((REPO / "eval" / "problems_dev12.json")
                    .read_text())["problems"]:
    probs.setdefault(p["problem_id"], p)


def baseline_for(pid):
    d12 = REPO / "eval" / "pairs" / "dev12_fresh" / f"{pid}.json"
    if d12.exists():
        base = str(json.loads(d12.read_text()).get(
            "baseline_answer") or "")
        if base.strip():
            return base, "CURATED_COMMITTED_dev12"
    cur = REPO / "eval" / "baselines_curated" / f"{pid}.json"
    if cur.exists():
        base = str(json.loads(cur.read_text()).get(
            "baseline_answer") or "")
        if base.strip():
            return base, "CURATED_STANDARD_REFERENCE_builder"
    return "", ""


def ledger_scan(ans):
    hits = sorted({m.group(0).lower() for m in
                   DEV_NEED_MARKERS.finditer(ans)})
    return hits


def generate(pid, prob, gw_key):
    q = json.dumps(prob, ensure_ascii=False)
    attempts = []
    ans, lat = _gen(q, SYS_A1_INT_V4, gw_key)
    attempts.append({"kind": "generation", "latency_s": round(lat, 1),
                     "chars": len(ans)})
    final, meta = ans, {}
    for rep in range(REPAIR_BUDGET + 1):
        cr = critic(final, prob)
        tg = gate_question_type(final, prob)
        dev = ledger_scan(final)
        problems = []
        if cr["verdict"] != "CLEAN":
            problems += [c.get("anchor") for c in cr["checks"]
                         if c.get("verdict") != "CLEAN"]
        if tg["verdict"] == "MISMATCH":
            problems.append(tg["reason"])
        if dev:
            problems.append(
                "V4 NO-DEVELOPMENT RULE violation: the bill concedes "
                "a development program (" + "; ".join(dev) + "). "
                "Re-express the SAME mechanism through procurable "
                "classes (a)/(b)/(c) only: shipped products, existing "
                "materials used outside their common application, "
                "duty/procedure/configuration changes. The mechanism "
                "stays novel; the COMPONENTS must all exist today.")
        if not [p for p in problems if p]:
            meta = {"critic_verdict": cr["verdict"],
                    "type_gate": tg, "dev_scan": dev, "repairs": rep}
            return final, attempts, meta
        if rep == REPAIR_BUDGET:
            meta = {"critic_verdict": cr["verdict"],
                    "type_gate": tg, "dev_scan": dev,
                    "repairs": rep,
                    "residual_findings": [p for p in problems if p]}
            return final, attempts, meta
        directive = ("REPAIR DIRECTIVE (typed findings on the previous "
                     "draft, disclosed): "
                     + "; ".join(p for p in problems if p)
                     + ". Fix ONLY these defects; keep the proposal's "
                       "core otherwise intact. The ONLY USER CONSTRAINT "
                       "labels allowed are the user-stated variables.")
        final, lat2 = _gen(q + "\n\n" + directive, SYS_A1_INT_V4, gw_key)
        attempts.append({"kind": f"repair_{rep+1}",
                         "latency_s": round(lat2, 1),
                         "chars": len(final),
                         "findings_disclosed":
                             [p for p in problems if p]})
    raise RuntimeError("unreachable")


def main() -> int:
    gw, gw_key = start_gateway()
    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        # ---------- phase 1: generate V4 answers (resume-safe) -------
        for pid in HARD7:
            dst = OUT_DIR / f"{pid}.json"
            if dst.exists():
                print(f"  [gen] {pid[:36]:<38} exists (rides)", flush=True)
                continue
            prob = probs[pid]
            t0 = time.time()
            ans, attempts, meta = generate(pid, prob, gw_key)
            rec = {"problem_id": pid,
                   "a1_source": "SYS_A1_INT_V4/r19_a1w2_pilot",
                   "question_type": prob.get("question_type"),
                   "a1_answer": ans, "attempts": attempts, "meta": meta,
                   "generated_at": now}
            dst.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                           + "\n", encoding="utf-8")
            print(f"  [gen] {pid[:36]:<38} "
                  f"verdict={meta['critic_verdict']} "
                  f"dev_scan={meta['dev_scan'] or 'CLEAN'} "
                  f"repairs={meta['repairs']} "
                  f"({time.time()-t0:.0f}s)", flush=True)
        # ---------- phase 2: judge (canonical metric, k=3) -----------
        prior = {}
        if PILOT_PARTIAL.exists():
            for r in json.loads(PILOT_PARTIAL.read_text(encoding="utf-8")):
                prior[r["problem_id"]] = r
        results = []
        for i, pid in enumerate(HARD7):
            if pid in prior:
                results.append(prior[pid])
                print(f"  [{i+1}/7] {pid[:36]:<38} resumed", flush=True)
                continue
            prob = probs[pid]
            a1 = str(json.loads(
                (OUT_DIR / f"{pid}.json").read_text(
                    encoding="utf-8"))["a1_answer"])
            base, b_src = baseline_for(pid)
            assert base.strip(), f"no baseline for {pid}"
            prompt = _rubric_prompt(prob, a1[:7000], base[:7000],
                                    None) + AXIS_SUFFIX
            draws = []
            for k in range(K):
                econ.reset_governor(f"r19pilot:{pid}:{k}")
                jc = _judge_judgment_call(JUDGE[0], JUDGE[1], prompt,
                                          max_tokens=4000)
                draws.append({"k": k, "outcome": jc.get("outcome"),
                              "axes": parse_axes(jc),
                              "prefer": (jc.get("valid") or {}).get(
                                  "prefer")})
                time.sleep(PACE_S)
            dec = row_metrics(draws)
            med = dec["median_axes"]
            row = {"problem_id": pid, "a1_arm": "SYS_A1_INT_V4",
                   "question_type": prob.get("question_type"),
                   "judge": list(JUDGE), "draws": draws,
                   "majority_prefer": dec["majority_prefer"],
                   "median_axes": med,
                   "baseline_source": b_src}
            if med:
                row["novelty_delta"] = med["N_A"] - med["N_B"]
                row["feasibility_abs_gap"] = abs(
                    med["F_A"] - med["F_B"])
                row["feasibility_signed_gap"] = med["F_A"] - med["F_B"]
            results.append(row)
            print(f"  [{i+1}/7] {pid[:36]:<38} "
                  f"nd={row.get('novelty_delta')} "
                  f"fgap={row.get('feasibility_abs_gap')} "
                  f"prefer={row.get('majority_prefer')}", flush=True)
            PILOT_PARTIAL.write_text(
                json.dumps(results, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
        # ---------- phase 3: compare vs r11 same-pair rows -----------
        cmp_rows = []
        for r in results:
            old = r11rows.get(r["problem_id"], {})
            cmp_rows.append({
                "problem_id": r["problem_id"],
                "r11_fgap": old.get("feasibility_abs_gap"),
                "v4_fgap": r.get("feasibility_abs_gap"),
                "r11_nd": old.get("novelty_delta"),
                "v4_nd": r.get("novelty_delta"),
                "r11_prefer": old.get("majority_prefer"),
                "v4_prefer": r.get("majority_prefer")})
        fg_v4 = [c["v4_fgap"] for c in cmp_rows
                 if c["v4_fgap"] is not None]
        nd_v4 = [c["v4_nd"] for c in cmp_rows if c["v4_nd"] is not None]
        fg_old = [c["r11_fgap"] for c in cmp_rows
                  if c["r11_fgap"] is not None]
        nd_old = [c["r11_nd"] for c in cmp_rows if c["r11_nd"] is not None]
        summary = {
            "n_pairs": len(cmp_rows),
            "r11_fgap_mean": round(sum(fg_old) / len(fg_old), 3),
            "v4_fgap_mean": round(sum(fg_v4) / len(fg_v4), 3),
            "r11_nd_mean": round(sum(nd_old) / len(nd_old), 3),
            "v4_nd_mean": round(sum(nd_v4) / len(nd_v4), 3),
            "fgap_improved": sum(
                1 for c in cmp_rows
                if (c["v4_fgap"] or 99) < (c["r11_fgap"] or 99)),
            "fgap_worsened": sum(
                1 for c in cmp_rows
                if (c["v4_fgap"] or -1) > (c["r11_fgap"] or -1)),
            "nd_collapsed_below_0.5": sum(
                1 for c in cmp_rows if (c["v4_nd"] or 0) < 0.5)}
        rec = {
            "record": "BATTERY_A1W2_PILOT_R19/1.0.0 — MECHANICS_PILOT "
                      "(direction probe on the pre-declared hard-7; NOT "
                      "the gate battery; acceptance rides committed real "
                      "bytes only — Art. 22)",
            "at": now,
            "pre_registration": {
                "contract": "SYS_A1_INT_V4 "
                            "(scripts/r19_a1w_v4_contract.py) — "
                            "committed before measurement",
                "subset_selection": "intervention-question pairs of "
                                    "battery r11 with "
                                    "feasibility_abs_gap >= 2, from "
                                    "COMMITTED bytes",
                "subset_pids": HARD7,
                "metric": "canonical battery metric unchanged (Art. 16): "
                          "eval/run._rubric_prompt + _f28_axis_suffix_v2 "
                          "+ crowllm/qwen-3.8-max:free t=0 K=3 + "
                          "eval/battery_metrics strict plurality",
                "purpose": "F30 D2 direction probe: does the "
                           "no-development/procurement rule pull the "
                           "hardest feasibility gaps down WITHOUT "
                           "collapsing novelty"},
            "generation_record": [
                {"problem_id": p["problem_id"],
                 "meta": {k: p[k] for k in
                          ("critic_verdict", "dev_scan", "repairs")
                          if k in p}}
                for p in (json.loads(
                    (OUT_DIR / f"{pid}.json").read_text(encoding="utf-8"))
                    for pid in HARD7)],
            "comparison_vs_r11_same_pairs": cmp_rows,
            "summary": summary,
            "reading_discipline": "the gate clause remains the "
                                  "OVERALL <=0.25 on >=30 pairs; this "
                                  "pilot neither passes nor fails the "
                                  "gate — it measures the V4 "
                                  "mechanism's direction on the "
                                  "hardest pairs"}
        PILOT_OUT.write_text(
            json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
        print(f"[r19pilot] r11 fgap {summary['r11_fgap_mean']} -> "
              f"V4 {summary['v4_fgap_mean']} | nd "
              f"{summary['r11_nd_mean']} -> {summary['v4_nd_mean']} "
              f"| improved {summary['fgap_improved']}/7 "
              f"worsened {summary['fgap_worsened']}/7 "
              f"nd<0.5 {summary['nd_collapsed_below_0.5']}/7",
              flush=True)
        print(f"-> {PILOT_OUT}")
        return 0
    finally:
        gw.terminate()


if __name__ == "__main__":
    raise SystemExit(main() or 0)
