#!/usr/bin/env python3
"""r124_collect_firings.py — the F97 calibration corpus builder
(zero LLM). Runs scan_input_availability over EVERY bill in the
committed corpora (both fresh draws: mine eval/r123_fresh_
confirmation_run + the twin's eval/r123_fresh_run; plus the seeded
battery: eval/r118_authoring_run bare bills + eval/r121_successor_
run reviewer bills, and the F30 battery under eval/ if present) and
emits EVERY firing with the bill text around each — the raw material
for the narration-vs-genuine classification.

Output: eval/r124_f97/firings.jsonl (one row per firing)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r40_machine_v77 as m77  # noqa: E402

SETS = {
    "fresh-draw-1 (mine, r123_fresh_confirmation_run)":
        (REPO / "eval" / "r123_fresh_set" / "items.jsonl",
         REPO / "eval" / "r123_fresh_confirmation_run",
         ["authored_bill", "delivered_bill"]),
    "fresh-draw-2 (twin, r123_fresh_run)":
        (REPO / "eval" / "r123_fresh_set" / "items.jsonl",
         REPO / "eval" / "r123_fresh_run",
         None),  # discovered below
    "seeded F31a bare (r118_authoring_run)":
        (REPO / "eval" / "r118_authoring_set" / "items.jsonl",
         REPO / "eval" / "r118_authoring_run",
         None),
    "F31b reviewer-delivered (r121_successor_run)":
        (REPO / "eval" / "r118_authoring_set" / "items.jsonl",
         REPO / "eval" / "r121_successor_run",
         None),
}

OUT = REPO / "eval" / "r124_f97"
OUT.mkdir(parents=True, exist_ok=True)


def discover_bills(d: Path) -> dict:
    """{pid: [(leg_label, bill_text)]} from a run dir."""
    out = {}
    for p in sorted(d.glob("*.json")) + sorted(d.glob("*.jsonl")):
        if p.name in ("scoring.json", "key.json"):
            continue
        try:
            if p.suffix == ".jsonl":
                for l in p.read_text(encoding="utf-8").strip().split("\n"):
                    if not l.strip():
                        continue
                    rec = json.loads(l)
                    pid = rec.get("problem_id")
                    for k, v in rec.items():
                        if isinstance(v, str) and len(v) > 200 and (
                                "bill" in k or "proposal" in k):
                            out.setdefault(pid, []).append((k, v))
            else:
                rec = json.loads(p.read_text(encoding="utf-8"))
                pid = rec.get("problem_id") or p.stem
                for k, v in rec.items():
                    if isinstance(v, str) and len(v) > 200 and (
                            "bill" in k or "proposal" in k):
                        out.setdefault(pid, []).append((k, v))
        except Exception:  # noqa: BLE001
            continue
    return out


def main() -> int:
    rows = []
    for label, (setp, rund, fixed) in SETS.items():
        if not setp.exists() or not rund.exists():
            print(f"skip {label}: missing dir")
            continue
        items = {json.loads(l)["problem_id"]: json.loads(l)
                 for l in setp.read_text(encoding="utf-8")
                 .strip().split("\n")}
        if fixed is not None:
            bills = {}
            for pid in items:
                p = rund / f"row_{pid}.json"
                if p.exists():
                    rec = json.loads(p.read_text(encoding="utf-8"))
                    bills[pid] = [(k, rec[k]) for k in fixed
                                  if k in rec]
        else:
            bills = discover_bills(rund)
        n_f = 0
        for pid, legs in sorted(bills.items()):
            prob = items.get(pid)
            if prob is None:
                continue
            for leg, bill in legs:
                try:
                    r = m77.scan_input_availability(prob, bill)
                except Exception as e:  # noqa: BLE001
                    rows.append({"corpus": label, "pid": pid,
                                 "leg": leg, "error": str(e)[:100]})
                    continue
                for msg in r.get("INPUT_UNAVAILABLE", []):
                    n_f += 1
                    # the bill text around the phrase the message
                    # names (first 50-60 chars of the quoted span)
                    q = msg.split("'")[1] if "'" in msg else ""
                    ctx = ""
                    if q:
                        for m in (bill.find(q[:20]),
                                  bill.lower().find(q[:12].lower())):
                            if m >= 0:
                                s = max(0, m - 130)
                                ctx = bill[s:m + 150].replace(
                                    "\n", " ")
                                break
                    rows.append({"corpus": label, "pid": pid,
                                 "leg": leg, "firing": msg,
                                 "context": ctx})
        print(f"{label}: {n_f} firings over "
              f"{sum(len(v) for v in bills.values())} bills")
    with (OUT / "firings.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\ntotal {len(rows)} firings -> "
          f"eval/r124_f97/firings.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
