#!/usr/bin/env python3
"""R130 GEPA-on-reviewer compile (claim c-0207, prereg
eval/r130_gepa_prereg.json, Art. 20 round 1 of 2).

Replays the REVIEWER stage only: author bills FROZEN to the twin's
committed bon_run candidates (clean pre-fix — the honest reviewer
input); the ONLY variable is the reviewer directive text (K=6:
the incumbent + 5 typed mutations). Model pin, FIX_SCHEMA, detector
bytes, transport policy all frozen.

Stage 1 (compile, 12 items): each candidate directive re-reviews the
12 frozen bills -> Pareto front on (introduced defects, heal rate,
length ratio); deterministic selection rule (preregistered).
Stage 2 (validation, 24 items): the winner re-reviews all 24; the
incumbent side is RECOMPUTED from the twin's committed delivered
bills (zero re-run).

Usage: python3 -I scripts/r130_gepa_reviewer.py [stage1|stage2|both]
"""
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import r127_phaseA_gate as gate  # FIX_SCHEMA, call_with_transport_backoff, check_layer
from r125_f31e_run import IMPROVED_DIRECTIVE
from r121_successor_score import bill_defect_classes

REPO = Path(__file__).resolve().parent.parent
ITEMS = {json.loads(l)["problem_id"]: json.loads(l)
         for l in (REPO / "eval/r125_f31e_set/items.jsonl").read_text().splitlines() if l.strip()}
ORDER = list(ITEMS)  # items.jsonl order = the compile slice definition
COMPILE_N = 12
OUT = REPO / "eval/r130_gepa_compile"
OUT.mkdir(exist_ok=True)

# ---- the K=6 directive candidates (preregistered mutations) --------------
M1 = ("\n\nDUTY-CYCLE/PWM PRICING RULE: every duty-cycle, PWM frequency, "
      "or pulse-timing figure in your corrected proposal must either "
      "(a) state the formula that derives it from the permitted "
      "measurements, with the numbers plugged in, or (b) cite the "
      "datasheet parameter it is taken from by name. If you cannot do "
      "either, DELETE the figure rather than asserting it.")
M2 = ("\n\nNO-INTRODUCTION RULE: the fix must NOT introduce any new "
      "numeric claim, parameter, rating, or operating point that is "
      "absent from the ORIGINAL proposal. Derive from what is there "
      "or remove; never add.")
M3 = ("\n\nSENSOR-SOURCE CHECKLIST: before returning, walk every input "
      "and signal in your corrected proposal against this checklist: "
      "(1) which permitted sensor or measurement provides it; (2) if "
      "derived, the formula and its inputs; (3) if neither answers it, "
      "the item is DELETED. Perform the walk explicitly and silently "
      "drop anything that fails.")
M5 = ("\n\nMINIMAL-DIFF RULE: change ONLY the sentences the findings "
      "touch. Every other sentence of the ORIGINAL proposal is carried "
      "over verbatim. Do not restate, reorganize, or reword untouched "
      "content.")
CANDS = {
    "incumbent": IMPROVED_DIRECTIVE,
    "m1_duty_rule": IMPROVED_DIRECTIVE + M1,
    "m2_no_intro": IMPROVED_DIRECTIVE + M2,
    "m3_sensor_cl": IMPROVED_DIRECTIVE + M3,
    "m4_m1m2": IMPROVED_DIRECTIVE + M1 + M2,
    "m5_minimal": IMPROVED_DIRECTIVE + M5,
}
REVIEWER_TARGET = 4000


def frozen_inputs(pid: str):
    """The reviewer's input pair from the twin's committed record: the
    SELECTED candidate's authored_bill + its surfaced findings."""
    d = json.loads((REPO / f"eval/r129_bon_run/bon_{pid}.json").read_text())
    sel = str(d["selected_candidate"])  # 'c1'/'c2' (string form)
    c = [x for x in d["candidates"] if str(x["candidate"]) == sel][0]
    return c["authored_bill"], c["surfaced_findings"]


def review_leg(directive: str, pid: str, bill: str, findings: list,
               tag: str) -> dict:
    """One reviewer replay: directive variant x frozen input pair."""
    prompt = (directive + "\n\nORIGINAL PROBLEM:\n"
              + json.dumps({k: ITEMS[pid].get(k, "") for k in
                            ("problem_id", "device", "failure", "constraint")},
                           ensure_ascii=False)
              + "\n\nPROPOSAL UNDER REVIEW:\n" + bill
              + "\n\nSURFACED FINDINGS (fix these):\n"
              + "\n".join(f"- {f}" for f in findings))
    att = []
    t0 = time.monotonic()
    try:
        resp = gate.call_with_transport_backoff(
            prompt, REVIEWER_TARGET, response_format=gate.FIX_SCHEMA,
            what=f"{pid}/{tag}", attempts_out=att)
        obj = json.loads(resp.get("content") or "")
        out = str(obj.get("corrected_proposal") or "")
        if not out.strip():
            raise ValueError("empty corrected_proposal")
        return {"pid": pid, "tag": tag, "ok": True, "delivered": out,
                "transport_attempts": len(att),
                "latency_s": round(time.monotonic() - t0, 1),
                "parse_first_try": True}
    except Exception as e:  # noqa: BLE001
        return {"pid": pid, "tag": tag, "ok": False,
                "typed_fail": f"{type(e).__name__}: {str(e)[:140]}",
                "transport_attempts": len(att),
                "latency_s": round(time.monotonic() - t0, 1)}


def score_leg(pid: str, delivered: str) -> dict:
    defects = sorted(bill_defect_classes(ITEMS[pid], delivered))
    healed = not gate.check_layer(ITEMS[pid], delivered, None) or not [
        v for v in gate.check_layer(ITEMS[pid], delivered, None).values() if v]
    return {"defects": defects, "healed": healed}


def run_stage1() -> dict:
    slice_pids = ORDER[:COMPILE_N]
    inputs = {pid: frozen_inputs(pid) for pid in slice_pids}
    # the incumbent directive's OWN delivered bytes are the committed
    # ones (recomputed, zero re-run) — only the 5 mutations run live.
    results = {k: {} for k in CANDS}
    jobs = []
    for name, directive in CANDS.items():
        if name == "incumbent":
            continue  # committed bytes, recomputed below
        for pid in slice_pids:
            bill, findings = inputs[pid]
            if not findings:
                continue  # reviewer never invoked on clean bills (chain contract)
            jobs.append((name, pid, bill, findings))
    print(f"stage 1: {len(jobs)} live reviewer legs "
          f"({len(CANDS)-1} mutations x up to {COMPILE_N} items)", flush=True)
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(review_leg, CANDS[n], pid, b, f, f"{n}"): (n, pid)
                for n, pid, b, f in jobs}
        for fut in as_completed(futs):
            r = fut.result()
            results[r["tag"]][r["pid"]] = r
            print(f"  {r['tag']}/{r['pid']} {'ok' if r['ok'] else 'FAIL'} "
                  f"{r['latency_s']}s", flush=True)
    # incumbent recomputed from the twin's committed delivered bytes
    inc = {}
    for pid in slice_pids:
        d = json.loads((REPO / f"eval/r129_bon_run/bon_{pid}.json").read_text())
        sel = str(d["selected_candidate"])
        c = [x for x in d["candidates"] if str(x["candidate"]) == sel][0]
        if c["surfaced_findings"]:
            inc[pid] = {"pid": pid, "tag": "incumbent", "ok": True,
                        "delivered": c["delivered_bill"],
                        "committed_bytes": True}
        else:
            inc[pid] = {"pid": pid, "tag": "incumbent", "ok": True,
                        "delivered": c["authored_bill"],
                        "committed_bytes": True, "reviewer_skipped": True}
    results["incumbent"] = inc

    # ---- Pareto scoring (the preregistered rule) -------------------------
    table = {}
    for name, rows in results.items():
        scored = []
        for pid, r in rows.items():
            if not r["ok"]:
                scored.append({"pid": pid, "fail": r.get("typed_fail")})
                continue
            s = score_leg(pid, r["delivered"])
            scored.append({"pid": pid, **s,
                           "len_ratio": round(len(r["delivered"]) /
                                              max(1, len(frozen_inputs(pid)[0])), 3)})
        defs = [x for x in scored if x.get("defects")]
        heals = [x for x in scored if x.get("healed")]
        table[name] = {
            "n_reviewed": len(scored),
            "n_failed_legs": sum(1 for x in scored if x.get("fail")),
            "introduced_defect_rows": len(defs),
            "defect_detail": [(x["pid"], x["defects"]) for x in defs],
            "healed_rows": len(heals),
            "heal_rate": round(len(heals) / len(scored), 3) if scored else None,
            "median_len_ratio": round(statistics.median(
                [x["len_ratio"] for x in scored if "len_ratio" in x]), 3)
            if any("len_ratio" in x for x in scored) else None,
            "rows": scored,
        }
        print(f"[stage1] {name}: defects={table[name]['introduced_defect_rows']} "
              f"heal={table[name]['heal_rate']} len={table[name]['median_len_ratio']} "
              f"fails={table[name]['n_failed_legs']}", flush=True)
    # Pareto front: (defects min, heal max, |len_ratio-1| min)
    def key(name):
        t = table[name]
        return (t["introduced_defect_rows"] + t["n_failed_legs"],
                -(t["heal_rate"] or 0), abs((t["median_len_ratio"] or 1) - 1))
    front = []
    for a in table:
        dominated = any(
            all(kb <= ka for kb, ka in zip(key(b), key(a))) and
            any(kb < ka for kb, ka in zip(key(b), key(a)))
            for b in table if b != a)
        if not dominated:
            front.append(a)
    # preregistered tie-break: fewest defects, then highest heal
    winner = sorted(front, key=key)[0] if front else "incumbent"
    stage1 = {"table_summary": {k: {kk: vv for kk, vv in v.items() if kk != "rows"}
                                for k, v in table.items()},
              "pareto_front": sorted(front), "winner": winner,
              "selection_rule": "preregistered: Pareto (defects+fails min, heal max, |len-1| min); tie -> fewest defects then highest heal"}
    (OUT / "stage1_summary.json").write_text(json.dumps(stage1, indent=1) + "\n")
    for name, rows in results.items():
        for pid, r in rows.items():
            (OUT / f"s1_{name}_{pid}.json").write_text(json.dumps(r, indent=1) + "\n")
    print("STAGE 1 WINNER:", winner, "| front:", sorted(front), flush=True)
    return stage1


def run_stage2(winner: str) -> dict:
    if winner == "incumbent":
        return {"skipped": "the incumbent directive won stage 1 — nothing "
                           "to validate; the arm is typed NOT-BEATEN at round 1 "
                           "(Art. 20 round 2 = R131 unless re-designed)"}
    directive = CANDS[winner]
    jobs = []
    for pid in ORDER:
        bill, findings = frozen_inputs(pid)
        if findings:
            jobs.append((pid, bill, findings))
    print(f"stage 2: {len(jobs)} live legs, winner={winner}", flush=True)
    out_rows = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(review_leg, directive, pid, b, f, "s2"): (pid)
                for pid, b, f in jobs}
        for fut in as_completed(futs):
            r = fut.result()
            out_rows[r["pid"]] = r
            print(f"  s2/{r['pid']} {'ok' if r['ok'] else 'FAIL'} {r['latency_s']}s",
                  flush=True)
    # incumbent side: recomputed from committed bytes on ALL 24
    inc_def = 0
    for pid in ORDER:
        d = json.loads((REPO / f"eval/r129_bon_run/bon_{pid}.json").read_text())
        sel = str(d["selected_candidate"])
        c = [x for x in d["candidates"] if str(x["candidate"]) == sel][0]
        if c["surfaced_findings"] and bill_defect_classes(ITEMS[pid], c["delivered_bill"]):
            inc_def += 1
    arm_def = sum(1 for r in out_rows.values()
                  if r["ok"] and bill_defect_classes(ITEMS[r["pid"]], r["delivered"]))
    stage2 = {"winner": winner, "n_legs": len(jobs),
              "arm_delivered_defect_rows": arm_def,
              "incumbent_delivered_defect_rows": inc_def,
              "note": "incumbent side recomputed from the committed bon_run "
                      "delivered bytes (zero re-run, Art. 29(c)); arm = the "
                      "compiled directive replaying the same frozen inputs"}
    for pid, r in out_rows.items():
        (OUT / f"s2_{winner}_{pid}.json").write_text(json.dumps(r, indent=1) + "\n")
    (OUT / "stage2_summary.json").write_text(json.dumps(stage2, indent=1) + "\n")
    print("STAGE 2:", json.dumps({k: v for k, v in stage2.items() if k != "note"}),
          flush=True)
    return stage2


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"
    s1 = run_stage1() if mode in ("stage1", "both") else \
        json.loads((OUT / "stage1_summary.json").read_text())
    s2 = run_stage2(s1["winner"]) if mode in ("stage2", "both") else None
    print("DONE", json.dumps({"stage1_winner": s1["winner"],
                              "stage2": s2 and {k: v for k, v in s2.items()
                                                if k != "note"}}))
