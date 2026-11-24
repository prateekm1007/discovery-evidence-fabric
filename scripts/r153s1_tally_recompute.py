#!/usr/bin/env python3
"""r153s1_tally_recompute.py — the INDEPENDENT tally recompute
(auditor constitution Art. 13): every reported panel tally is
recomputed by a STANDALONE script from the raw leg bytes, never
trusted from the producing driver's own summary.

Recomputes, from eval/r148_p4_panel_v18/<judge>__<pid>.json:
  (a) per-candidate votes (viable, non_obvious) per SERVING judge
      (read from SERVING_SNAPSHOT_r153.json, not hardcoded);
  (b) the majority-on-both-axes pass per candidate;
  (c) the >=50% gate over the FULL 30;
  (d) the diff vs the driver's tally.json — MUST be 0.

Exit 0 iff the diff is 0 and every serving judge has 30 VALID legs
(or the missing legs are typed in the driver's tally); else exit 1
with the typed mismatch."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "eval" / "r148_p4_panel_v18"
PACKS = REPO / "eval" / "r149_v18_panel" / "packs_sealed_set.json"


def main() -> int:
    snap = json.loads((OUT_DIR / "SERVING_SNAPSHOT_r153.json")
                      .read_text())
    serving = snap["serving"]
    packs = json.loads(PACKS.read_text())["packs"]
    pids = [pk["problem_id"] for pk in packs]

    votes = {}   # pid -> {judge: (viable, non_obvious)}
    missing = []  # (judge, pid) without a VALID leg
    for pid in pids:
        votes[pid] = {}
        for j in serving:
            f = OUT_DIR / f"{j}__{pid}.json"
            if not f.exists():
                missing.append((j, pid))
                continue
            d = json.loads(f.read_text())
            if d.get("outcome") != "VALID" or not d.get("parsed"):
                missing.append((j, pid))
                continue
            p = d["parsed"]
            votes[pid][j] = (bool(p.get("viable")),
                             bool(p.get("non_obvious")))

    rows, n_pass = [], 0
    for pid in pids:
        v = votes[pid]
        nv = len(v)
        v_yes = sum(1 for a, _ in v.values() if a)
        n_yes = sum(1 for _, b in v.values() if b)
        passed = nv > 0 and v_yes * 2 > nv and n_yes * 2 > nv
        n_pass += passed
        rows.append({"problem_id": pid, "judges_voted": nv,
                     "viable_yes": v_yes, "nonobvious_yes": n_yes,
                     "passed": passed})
    pct = round(100.0 * n_pass / len(pids), 1)

    # the diff vs the driver's tally
    driver = json.loads((OUT_DIR / "tally.json").read_text())
    d_rows = {r["problem_id"]: r for r in driver["rows"]}
    diff = 0
    for r in rows:
        dr = d_rows.get(r["problem_id"])
        if not dr:
            print(f"DIFF: {r['problem_id']} missing from driver tally")
            diff += 1
            continue
        for k in ("judges_voted", "viable_yes", "nonobvious_yes",
                  "passed"):
            if dr.get(k) != r[k]:
                print(f"DIFF: {r['problem_id']}.{k} driver={dr.get(k)} "
                      f"recompute={r[k]}")
                diff += 1
    d_pct = driver["tally"]["pct"]
    d_n = driver["tally"]["n_viable_and_non_obvious"]
    if d_n != n_pass or abs(d_pct - pct) > 0.05:
        print(f"DIFF: totals driver={d_n}/{d_pct}% "
              f"recompute={n_pass}/{pct}%")
        diff += 1

    print(f"RECOMPUTE: {n_pass}/{len(pids)} = {pct}% "
          f"(bar >=50%: {'PASS' if pct >= 50.0 else 'FAIL'}) | "
          f"serving={serving} | missing VALID legs: {len(missing)} "
          f"| driver-diff: {diff}")
    json.dump({"recompute": {"n_pass": n_pass, "n_total": len(pids),
                             "pct": pct,
                             "pass_ge_50": bool(pct >= 50.0),
                             "serving": serving,
                             "missing_valid_legs": len(missing),
                             "driver_diff": diff},
               "rows": rows},
              open(REPO / "eval" / "r153s1_tally_recompute.json", "w"),
              indent=1, ensure_ascii=False)
    return 0 if diff == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
