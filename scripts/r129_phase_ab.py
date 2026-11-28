#!/usr/bin/env python3
"""R129 owner direction 2+3 (Phase A + Phase B round 1).

Phase A (speed, no capability risk): the Phase-A chain
(bare author -> bind check -> reviewer fix) runs over INDEPENDENT
problems in a bounded process pool — Anthropic's parallel-rule
adapted to our architecture: only the independent legs fan out, the
author->check->review chain stays sequential per problem. The 2-key
rotation doubles the sustained cap; per-leg transport_attempts (the
R128 field) is live in every record.

Phase B (ablation, Art. 20 clock starts this round): arm 'bon3' —
best-of-3 authoring with BIND-SELECT (the deterministic defect
count picks the delivered candidate; ties -> the fewest-defect then
longest bill) — against the incumbent single-shot arm on the same
24-item DEV slice (the F31e set — builder-authored DEV material, NOT
fresh; the fresh-material gate stays with the auditor's v16).

Usage: python3 -I scripts/r129_phase_ab.py [--items N] [--arms ss,bon3]
"""
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import r127_phaseA_gate as gate  # the committed chain: prompts, check_layer, backoff, FIX_SCHEMA

REPO = Path(__file__).resolve().parent.parent
SET = REPO / "eval" / "r125_f31e_set" / "items.jsonl"
OUT = REPO / "eval" / "r129_phase_ab"
POOL = 3          # bounded: 2 agnes keys x ~1.5 concurrent — no 429 storm
SPACING_S = 1.0   # per-thread polite spacing (the r127 runner used 3s serial)

items = [json.loads(l) for l in SET.read_text().splitlines() if l.strip()]
N = int(sys.argv[sys.argv.index("--items") + 1]) if "--items" in sys.argv else 24
ARMS = (sys.argv[sys.argv.index("--arms") + 1] if "--arms" in sys.argv
        else "ss,bon3").split(",")
items = items[:N]
print(f"items={len(items)} arms={ARMS} pool={POOL}", flush=True)

from r121_successor_score import bill_defect_classes  # canonical detector


def run_one(prob: dict, arm: str) -> dict:
    pid = prob["problem_id"]
    t0 = time.monotonic()
    # Phase A chain, per problem: author (1 or 3 draws) -> check -> fix
    n_draws = 3 if arm == "bon3" else 1
    cands = []
    for j in range(n_draws):
        ca = {"leg": f"author{j+1}", "attempts": 1}
        att: list = []
        try:
            ta = time.monotonic()
            resp = gate.call_with_transport_backoff(
                gate.authoring_prompt(prob), 1200,
                what=f"{pid}/a{j+1}", attempts_out=att)
            ca.update(latency_s=round(time.monotonic() - ta, 2),
                      transport_attempts=len(att), usage=gate.usage_snapshot(resp))
            cands.append(resp.get("content") or "")
        except Exception as e:  # noqa: BLE001
            ca["typed_fail"] = f"{type(e).__name__}: {str(e)[:120]}"
        globals().setdefault("_CALLS", []).append(ca)
        if arm == "bon3" and j < n_draws - 1:
            time.sleep(SPACING_S)
    if not cands:
        return {"problem_id": pid, "arm": arm, "status": "TYPED_CALL_FAIL",
                "wall_clock_s": round(time.monotonic() - t0, 2), "calls": _CALLS[-n_draws:]}
    # bind-select (deterministic): fewest delivered-defect classes, then longest bill
    scored = [(len(bill_defect_classes(prob, c)) or 0, -len(c), c) for c in cands]
    scored.sort()
    defects0, _, bill = scored[0]
    rec = {"problem_id": pid, "arm": arm, "n_candidates": len(cands),
           "selected_candidate_defects_pre_fix": defects0,
           "calls": _CALLS[-len(cands):]}
    # check -> reviewer fix (the incumbent chain, unchanged)
    vio = gate.check_layer(prob, bill, None)
    findings = [f"{k}: {'; '.join(map(str, v))[:110]}" for k, v in vio.items() if v]
    rec["surfaced_findings"] = findings
    rec["surfaced_scan"] = {k: list(v) for k, v in vio.items()}
    if not findings:
        rec.update(delivered_bill=bill, reviewer_skipped=True, post_review_scan={},
                   wall_clock_s=round(time.monotonic() - t0, 2), status="DELIVERED_BARE")
        return rec
    cr = {"leg": "reviewer", "attempts": 1}
    att2: list = []
    try:
        prompt = (gate.IMPROVED_DIRECTIVE + "\n\nORIGINAL PROBLEM:\n"
                  + json.dumps({k: prob.get(k, "") for k in
                                ("problem_id", "device", "failure", "constraint")},
                               ensure_ascii=False)
                  + "\n\nPROPOSAL UNDER REVIEW:\n" + bill
                  + "\n\nSURFACED FINDINGS (fix these):\n"
                  + "\n".join(f"- {f}" for f in findings))
        time.sleep(SPACING_S)
        tr = time.monotonic()
        resp = gate.call_with_transport_backoff(
            prompt, 4000, response_format=gate.FIX_SCHEMA,
            what=f"{pid}/rev", attempts_out=att2)
        cr.update(latency_s=round(time.monotonic() - tr, 2),
                  transport_attempts=len(att2), usage=gate.usage_snapshot(resp))
        obj = json.loads(resp.get("content") or "")
        delivered = str(obj.get("corrected_proposal") or "")
        if not delivered.strip():
            raise ValueError("empty corrected_proposal")
        cr["schema_parsed_first_try"] = True
        rec.update(delivered_bill=delivered, post_review_scan={}, calls=rec["calls"] + [cr],
                   wall_clock_s=round(time.monotonic() - t0, 2), status="DELIVERED")
        rec["post_review_scan"] = {k: list(v) for k, v in
                                   gate.check_layer(prob, delivered, None).items()}
    except Exception as e:  # noqa: BLE001
        cr["typed_fail"] = f"{type(e).__name__}: {str(e)[:120]}"
        rec.update(delivered_bill=None, calls=rec["calls"] + [cr],
                   wall_clock_s=round(time.monotonic() - t0, 2),
                   status="REVIEWER_FAIL_DELIVERED_BARE" if cands else "FAIL")
        rec["delivered_bill"] = bill  # deliver bare on reviewer failure (the chain contract)
    return rec


def measure(rec: dict) -> dict:
    """Delivered-defect classes under the canonical detector."""
    if not rec.get("delivered_bill"):
        return {"defects": None}
    return {"defects": sorted(bill_defect_classes(
        items_by_pid[rec["problem_id"]], rec["delivered_bill"]))}


items_by_pid = {p["problem_id"]: p for p in items}
OUT.mkdir(exist_ok=True)
all_recs = []
for arm in ARMS:
    t_arm = time.monotonic()
    with ThreadPoolExecutor(max_workers=POOL) as ex:
        futs = {ex.submit(run_one, p, arm): p["problem_id"] for p in items}
        for fut in as_completed(futs):
            r = fut.result()
            r["delivered_defects"] = measure(r)["defects"]
            all_recs.append(r)
            (OUT / f"{arm}_{r['problem_id']}.json").write_text(json.dumps(r, indent=1) + "\n")
            print(f"  [{arm}] {r['problem_id']} {r['status']} "
                  f"{r['wall_clock_s']}s defects={r['delivered_defects']}", flush=True)
    print(f"arm {arm} done in {time.monotonic()-t_arm:.0f}s", flush=True)

# ---- summary ----------------------------------------------------------------
summary = {"record": "R129_PHASE_AB/1.0.0", "pool": POOL, "items": len(items),
           "arms": ARMS, "per_arm": {}}
for arm in ARMS:
    rs = [r for r in all_recs if r["arm"] == arm]
    wc = sorted(r["wall_clock_s"] for r in rs)
    d = [r for r in rs if r.get("delivered_bill")]
    dn = sum(1 for r in d if r["delivered_defects"])
    ta = [c.get("transport_attempts", 1) for r in rs for c in r.get("calls", [])]
    pr = sum(1 for r in rs for c in r.get("calls", [])
             if c.get("leg") == "reviewer" and c.get("schema_parsed_first_try"))
    rv = sum(1 for r in rs for c in r.get("calls", []) if c.get("leg") == "reviewer")
    cu = [c.get("usage", {}).get("cached_tokens") for r in rs
          for c in r.get("calls", []) if c.get("usage")]
    summary["per_arm"][arm] = {
        "n": len(rs), "delivered": len(d),
        "median_wall_s": round(statistics.median(wc), 1),
        "worst_wall_s": round(max(wc), 1),
        "delivered_defect_rate": round(dn / len(d), 4) if d else None,
        "defective_rows": dn,
        "transport_attempts_total": sum(ta),
        "transport_backoffs_absorbed": sum(t - 1 for t in ta if t > 1),
        "reviewer_first_try_parses": f"{pr}/{rv}",
        "cached_tokens_seen": sum(x for x in cu if x) or 0,
        "parse_retries_nonfirst": rv - pr,
    }
    print(arm, "->", json.dumps(summary["per_arm"][arm]))
(OUT / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
print("summary written:", OUT / "summary.json")
