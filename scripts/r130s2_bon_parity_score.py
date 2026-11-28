#!/usr/bin/env python3
"""r130s2_bon_parity_score.py — the committed scorer for the BoN
round-2 parity (claim c-0208; the prereg
eval/r130s2_bon2_parity_prereg.json governs).

Recomputes ALL tallies from committed bytes BEFORE the gate is read:
  incumbent  <- eval/r125_f31e_run/succ_d*.json          (pin 2/48)
  round-1    <- eval/r129_bon_run/bon_*.json             (pin 0/24)
  rep-2      <- eval/r130s2_bon_parity_run/rep2_*.json   (this run)
pools the arm (24 + 24 = 48 rows), applies the preregistered round-2
gate (ADOPT iff POOLED arm defect rows < incumbent's 2 STRICTLY, else
DELETE — Art. 20), reports the item-clustered width (descriptive only,
Art. 14; deterministic seed), a second-construction crosscheck, and
writes eval/r130s2_bon_parity_scoring.json whose `gate` object is a
defect_rows/rows DICT so the Art. 20 CI recompute actually bites.

Fail-closed: pin drift (incumbent != 2/48 with both duty_pricing d1,
or round-1 != 0/24) or a coverage breach (>2 typed-fail items) ->
exit 2, NO scoring file written. Zero LLM, zero network.

Usage: python3 scripts/r130s2_bon_parity_score.py [--preview]
(--preview prints the tallies and exits WITHOUT writing the file —
used mid-run; the gate is only ever read on the complete run.)
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r121_successor_score import bill_defect_classes  # noqa: E402

CLASSES = ["input_availability", "duty_pricing", "constraint_violation",
           "physics_direction_inversion"]
SEED = 20261122
BOOTSTRAP_N = 10000

items = {}
for line in (REPO / "eval" / "r125_f31e_set" / "items.jsonl") \
        .read_text(encoding="utf-8").strip().split("\n"):
    if line:
        p = json.loads(line)
        items[p["problem_id"]] = p


def per_class(defects: list) -> dict:
    out = {c: 0 for c in CLASSES}
    for d in defects:
        for c in d["classes"]:
            if c in out:
                out[c] += 1
    return out


def tally_succ() -> dict:
    """Incumbent: the committed F31e succ records (48 rows)."""
    rows = 0
    defects = []
    indicators = {}
    for f in sorted((REPO / "eval" / "r125_f31e_run")
                    .glob("succ_d*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        rows += 1
        cls = bill_defect_classes(items[d["problem_id"]],
                                  d["delivered_bill"])
        indicators.setdefault(d["problem_id"], []).append(
            1 if cls else 0)
        if cls:
            defects.append({"pid": d["problem_id"],
                            "draw": d["draw"], "classes": cls})
    return {"rows": rows, "defects": defects, "ind": indicators}


def tally_bon(pattern: str, subdir: str = "") -> dict:
    """A bon2 arm replication: selected rows re-tallied from the
    committed per-item records (delivered bills)."""
    base = REPO / "eval" / subdir if subdir else REPO / "eval"
    rows = 0
    fail_items = []
    defects = []
    indicators = {}
    sel_dist = {}
    usage = {"author_prompt": 0, "author_completion": 0,
             "author_cached": 0, "reviewer_prompt": 0,
             "reviewer_completion": 0, "reviewer_cached": 0}
    transport = {"legs": 0, "backoff_legs": 0, "max_attempts": 1}
    for f in sorted(base.glob(pattern)):
        rec = json.loads(f.read_text(encoding="utf-8"))
        pid = rec["problem_id"]
        scores = rec.get("selection_scores") or []
        sel_dist[str(scores)] = sel_dist.get(str(scores), 0) + 1
        for c in rec.get("candidates") or []:
            for call in c.get("calls") or []:
                leg = call.get("leg")
                att = call.get("transport_attempts") or 1
                transport["legs"] += 1
                if att > 1:
                    transport["backoff_legs"] += 1
                transport["max_attempts"] = max(
                    transport["max_attempts"], att)
                u = call.get("usage") or {}
                if leg == "author":
                    usage["author_prompt"] += u.get("prompt_tokens") or 0
                    usage["author_completion"] += \
                        u.get("completion_tokens") or 0
                    usage["author_cached"] += \
                        u.get("cached_tokens") or 0
                elif leg == "reviewer":
                    usage["reviewer_prompt"] += \
                        u.get("prompt_tokens") or 0
                    usage["reviewer_completion"] += \
                        u.get("completion_tokens") or 0
                    usage["reviewer_cached"] += \
                        u.get("cached_tokens") or 0
        bill = rec.get("delivered_bill")
        if not bill:
            fail_items.append(pid)
            indicators.setdefault(pid, []).append(1)  # +inf excluded
            continue
        rows += 1
        cls = bill_defect_classes(items[pid], bill)
        indicators.setdefault(pid, []).append(1 if cls else 0)
        if cls:
            defects.append({"pid": pid, "classes": cls})
    return {"rows": rows, "defects": defects, "ind": indicators,
            "fail_items": fail_items, "sel_dist": sel_dist,
            "usage": usage, "transport": transport}


def cluster_width(arm_ind: dict, inc_ind: dict) -> dict:
    """Item-clustered bootstrap on the defect-RATE difference —
    DESCRIPTIVE width only (Art. 14; never a significance claim)."""
    pids = sorted(inc_ind)
    diffs = []
    rng = random.Random(SEED)
    for _ in range(BOOTSTRAP_N):
        da = di = na = ni = 0
        for pid in rng.choices(pids, k=len(pids)):
            da += sum(arm_ind.get(pid, [0]))
            na += len(arm_ind.get(pid, [0, 0]))
            di += sum(inc_ind[pid])
            ni += len(inc_ind[pid])
        diffs.append((da / na if na else 0.0)
                     - (di / ni if ni else 0.0))
    diffs.sort()
    lo = diffs[int(0.025 * BOOTSTRAP_N)]
    hi = diffs[min(BOOTSTRAP_N - 1, int(0.975 * BOOTSTRAP_N))]
    point = (sum(sum(v) for v in arm_ind.values())
             / max(1, sum(len(v) for v in arm_ind.values()))
             - sum(sum(v) for v in inc_ind.values())
             / max(1, sum(len(v) for v in inc_ind.values())))
    return {"method": "item-clustered bootstrap on the defect-rate "
                      "difference (24 item clusters, resampled with "
                      "replacement)",
            "seed": SEED, "resamples": BOOTSTRAP_N,
            "point_diff": round(point, 6),
            "ci95_descriptive_only": [round(lo, 6), round(hi, 6)]}


def crosscheck(pooled: dict, inc: dict) -> dict:
    """Second-construction tally (explicit-index loops, the round-1
    Art. 19-lite pattern) — must MATCH the primary construction."""
    def alt(indicators: dict) -> int:
        n = 0
        for pid in indicators:
            for i in range(len(indicators[pid])):
                if indicators[pid][i] == 1:
                    n = n + 1
        return n
    return {"pooled_arm_second_construction": alt(pooled["ind"]),
            "incumbent_second_construction": alt(inc["ind"]),
            "match": (alt(pooled["ind"]) == len(pooled["defects"])
                      and alt(inc["ind"]) == len(inc["defects"]))}


def main() -> int:
    preview = "--preview" in sys.argv
    inc = tally_succ()
    r1 = tally_bon("bon_*.json", "r129_bon_run")
    r2 = tally_bon("rep2_*.json", "r130s2_bon_parity_run")

    print(f"incumbent: rows={inc['rows']} defect_rows={len(inc['defects'])} "
          f"{json.dumps(inc['defects'])}")
    print(f"round-1 arm: rows={r1['rows']} defect_rows={len(r1['defects'])} "
          f"fail_items={r1['fail_items']}")
    print(f"rep-2 arm: rows={r2['rows']} defect_rows={len(r2['defects'])} "
          f"fail_items={r2['fail_items']} sel_dist={r2['sel_dist']}")
    print(f"rep-2 usage: {json.dumps(r2['usage'])}")
    print(f"rep-2 transport: {json.dumps(r2['transport'])}")

    # fail-closed pins BEFORE any gate logic (the prereg requirement)
    pin_inc = (inc["rows"] == 48 and len(inc["defects"]) == 2
               and all(d["classes"] == ["duty_pricing"]
                       and d["draw"] == "d1" for d in inc["defects"]))
    pin_r1 = (r1["rows"] == 24 and len(r1["defects"]) == 0
              and not r1["fail_items"])
    if not (pin_inc and pin_r1):
        print(f"FAIL-CLOSED: PIN DRIFT (incumbent_ok={pin_inc}, "
              f"round1_ok={pin_r1}) — NO gate is read, exit 2")
        return 2
    if len(r2["fail_items"]) > 2:
        print("FAIL-CLOSED: INVALID_COVERAGE (>2 typed-fail items) "
              "— NO gate is read, exit 2")
        return 2

    pooled_rows = r1["rows"] + r2["rows"]
    pooled_defects = r1["defects"] + r2["defects"]
    pooled_ind = {pid: (r1["ind"].get(pid, []) + r2["ind"].get(pid, []))
                  for pid in set(r1["ind"]) | set(r2["ind"])}
    print(f"POOLED arm: rows={pooled_rows} "
          f"defect_rows={len(pooled_defects)} {json.dumps(pooled_defects)}")

    beats = len(pooled_defects) < len(inc["defects"])
    verdict = "ADOPT" if beats else "DELETE"
    print(f"GATE (round 2, preregistered): pooled "
          f"{len(pooled_defects)}/{pooled_rows} vs incumbent "
          f"{len(inc['defects'])}/{inc['rows']} -> {verdict}")

    width = cluster_width(pooled_ind, inc["ind"])
    print(f"descriptive width: {json.dumps(width)}")
    xc = crosscheck({"ind": pooled_ind, "defects": pooled_defects}, inc)
    print(f"crosscheck: {json.dumps(xc)}")
    if not xc["match"]:
        print("FAIL-CLOSED: crosscheck MISMATCH — exit 2")
        return 2

    if preview:
        print("PREVIEW ONLY — no scoring file written")
        return 0

    out = {
        "record": "R130S2_BON_PARITY_SCORING/1.0.0",
        "claim": "c-0208",
        "session": "builder-r130s2",
        "arm": "bon2-bindselect (byte-identical to round 1; pooled "
               "over the round-1 committed rows + this replication)",
        "n_items": 24,
        "rep1_rows_recomputed": r1["rows"],
        "rep1_defect_rows_recomputed": len(r1["defects"]),
        "rep2_rows": r2["rows"],
        "rep2_defect_rows": len(r2["defects"]),
        "rep2_typed_fail_items": r2["fail_items"],
        "rep2_selection_score_dist": r2["sel_dist"],
        "rep2_usage_totals": r2["usage"],
        "rep2_transport": r2["transport"],
        "pooled_arm_rows": pooled_rows,
        "pooled_arm_defect_rows": len(pooled_defects),
        "pooled_arm_defect_rows_detail": pooled_defects,
        "pooled_per_class": per_class(pooled_defects),
        "incumbent_rows": inc["rows"],
        "incumbent_defect_rows": len(inc["defects"]),
        "incumbent_defect_rows_detail": inc["defects"],
        "incumbent_per_class": per_class(inc["defects"]),
        "prereg_incumbent_pin_2_of_48": pin_inc,
        "prereg_round1_pin_0_of_24": pin_r1,
        "width_descriptive_art14": width,
        "crosscheck": xc,
        "gate": {
            "defect_rows": len(pooled_defects),
            "rows": pooled_rows,
            "verdict": verdict,
            "beats_incumbent": beats,
            "incumbent_defect_rows": len(inc["defects"]),
            "note": "the preregistered round-2 gate: ADOPT iff pooled "
                    "arm defect rows < incumbent 2/48 strictly, else "
                    "DELETE (Art. 20); no score claims (Art. 14)",
        },
    }
    path = REPO / "eval" / "r130s2_bon_parity_scoring.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"scoring written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
