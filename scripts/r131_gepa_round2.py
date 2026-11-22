#!/usr/bin/env python3
"""R131 GEPA round 2 of 2 (claim c-0210, prereg
eval/r131_gepa_round2_prereg.json — typed BEFORE any run call).

The m5 directive (= the CURRENT canonical IMPROVED_DIRECTIVE post-fold,
== the r130 m5_minimal == the twin's c-0209 v2 bytes) draws FRESH over
the 48 committed F31e pre-review pairs (the headroom corpus). Zero
author legs (bills frozen to committed bytes), zero v1 legs (all v1
observations are committed bytes: pooled 4/96).

Pooling rule (preregistered): m5 pooled = the twin's committed v2 draw
(2/48) + this run (X/48). STRICTLY BEATS iff (2+X)/96 < 4/96 (X<=1);
TIE iff X=2; LOSE iff X>=3. The arm is DELETED unless strictly beats
(Art. 20 round 2). This draw trials MF-2 (the ~2/48-per-draw
directive-invariant rate floor).

Usage: python3 -I scripts/r131_gepa_round2.py
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
# byte-reuse the harness legs (the r130s3 pattern): review_leg, score_leg,
# ITEMS — all imported UNMODIFIED from the r130 instrument.
import r130_gepa_reviewer as g  # noqa: E402
from r130_gepa_reviewer import review_leg, score_leg  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "eval/r131_gepa_round2"
OUT.mkdir(exist_ok=True)

# the arm bytes: the CURRENT canonical directive (post-fold = v1 + M5).
# Sanity: assert the fold is present so the arm is exactly m5.
ARM = g.gate.IMPROVED_DIRECTIVE
assert "MINIMAL-DIFF RULE" in ARM, "the canonical directive lacks the folded M5 clause — the arm bytes are wrong"
assert len(ARM) == 762, f"canonical directive len {len(ARM)} != the c-0209 byte-verified 762"


def heldout_inputs():
    out = []
    for f in sorted((REPO / "eval" / "r125_f31e_run").glob("succ_d*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        ab, sf = d.get("authored_bill"), d.get("surfaced_findings")
        if ab and sf:
            out.append({"pid": d["problem_id"], "draw": d["draw"],
                        "bill": ab, "findings": sf})
    return out


def main() -> int:
    pairs = heldout_inputs()
    assert len(pairs) == 48, f"corpus census {len(pairs)} != 48"
    print(f"GEPA ROUND-2 DRAW: m5 (canonical, {len(ARM)} chars) over {len(pairs)} "
          f"committed pre-review pairs; 0 author legs, 0 v1 legs", flush=True)
    rows = []
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(review_leg, ARM, p["pid"], p["bill"], p["findings"],
                          "r2"): p for p in pairs}
        for fut in as_completed(futs):
            r = fut.result()
            rows.append(r)
            print(f"  r2/{r['pid']} {'ok' if r['ok'] else 'FAIL'} "
                  f"{r['latency_s']}s", flush=True)
    wall = round(time.monotonic() - t0, 1)
    # ---- the preregistered verdict ----
    defs, def_pids = [], []
    heals = 0
    for r in rows:
        if not r["ok"]:
            defs.append(("TYPED_FAIL", r["pid"]))
            continue
        s = score_leg(r["pid"], r["delivered"])
        if s["defects"]:
            def_pids.append(r["pid"])
        heals += 1 if s["healed"] else 0
    x = len(def_pids)
    m5_pooled = 2 + x           # the twin's committed v2 draw (2/48) + X
    v1_pooled = 4               # committed 2/48 + the twin's replay 2/48
    if m5_pooled / 96 < v1_pooled / 96:
        verdict = "STRICTLY_BEATS"
    elif m5_pooled / 96 == v1_pooled / 96:
        verdict = "TIE"
    else:
        verdict = "LOSE"
    summary = {
        "record": "R131_GEPA_ROUND2/1.0.0", "claim": "c-0210",
        "at": "2026-11-22 (sandbox clock, TRUE UTC)",
        "n_legs": len(rows),
        "typed_fails": sum(1 for r in rows if not r["ok"]),
        "parse_retries": 0,
        "this_draw_defect_rows": x, "this_draw_defect_pids": def_pids,
        "this_draw_healed_rows": heals,
        "m5_pooled_defect_rows": m5_pooled, "m5_pooled_rows": 96,
        "v1_pooled_defect_rows": v1_pooled, "v1_pooled_rows": 96,
        "verdict": verdict,
        "art20_outcome": {
            "STRICTLY_BEATS": "the arm ADOPTS (the BoN precedent); MF-2's directive-invariance REFUTED on the m5 side",
            "TIE": "the arm is DELETED (Art. 20: no strict beat within 2 rounds); MF-2 CONFIRMED for the m5 side",
            "LOSE": "the arm is DELETED (Art. 20); MF-2 CONFIRMED",
        }[verdict],
        "wall_s": wall,
    }
    (OUT / "round2_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    for r in rows:
        (OUT / f"r2_{r['pid']}.json").write_text(json.dumps(r, indent=1) + "\n")
    print("ROUND-2 VERDICT:", json.dumps({k: v for k, v in summary.items()
                                          if k != "art20_outcome"}), flush=True)
    print("ART. 20 OUTCOME:", summary["art20_outcome"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
