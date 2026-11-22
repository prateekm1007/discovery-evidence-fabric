#!/usr/bin/env python3
"""r125_generalization.py — dir 3 (the R125 verdict): the F97 fix's
generalization check. Collects committed bill corpora NEVER in the
F97 calibration corpus (the calibration = eval/r124_f97/firings
.jsonl's four corpora: r123_fresh_confirmation_run, r123_fresh_run,
r118_authoring_run, r121_successor_run), runs the FIXED detector
over every bill-leg, and emits each firing with context for hand
classification.

Zero LLM. Output: eval/r125_f31d/generalization.jsonl
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r40_machine_v77 as m77  # noqa: E402

OUT = REPO / "eval" / "r125_f31d"
OUT.mkdir(parents=True, exist_ok=True)

# the calibration corpora (excluded by path)
CALIB = {"eval/r123_fresh_confirmation_run", "eval/r123_fresh_run",
         "eval/r118_authoring_run", "eval/r121_successor_run"}

# items sets for problem lookup
SETFILES = ["eval/r123_fresh_set/items.jsonl",
            "eval/r118_authoring_set/items.jsonl",
            "eval/r116_f30_set/items.jsonl",
            "eval/r119_holdout_v3/items.jsonl",
            "eval/r124_f31d_set/items.jsonl"]


def load_sets():
    items = {}
    for sp in SETFILES:
        p = REPO / sp
        if not p.exists():
            continue
        for l in p.read_text(encoding="utf-8").strip().split("\n"):
            if not l.strip():
                continue
            rec = json.loads(l)
            items[rec["problem_id"]] = rec
    return items


def discover_bills():
    """(corpus_dir, path, pid, bill_text) for every committed bill
    outside the calibration corpora."""
    for rund in sorted((REPO / "eval").glob("*run*")) + \
            sorted((REPO / "eval").glob("*_run")):
        rel = str(rund.relative_to(REPO))
        if rel in CALIB or not rund.is_dir():
            continue
        for p in sorted(rund.glob("*.json")) + sorted(
                rund.glob("*.jsonl")) + sorted(rund.glob("*.txt")):
            if p.name in ("scoring.json", "key.json"):
                continue
            try:
                if p.suffix == ".txt":
                    txt = p.read_text(encoding="utf-8")
                    if len(txt) > 200 and ("NOVELTY" in txt
                                           or "Mitigation" in txt
                                           or "mechanism" in txt
                                           .lower()):
                        pid = p.stem.replace("bare_", "")
                        yield rel, p, pid, txt
                    continue
                if p.suffix == ".jsonl":
                    for l in p.read_text(encoding="utf-8") \
                            .strip().split("\n"):
                        if not l.strip():
                            continue
                        rec = json.loads(l)
                        pid = rec.get("problem_id")
                        for k, v in rec.items():
                            if (isinstance(v, str) and len(v) > 200
                                    and ("bill" in k
                                         or "proposal" in k)):
                                yield rel, p, pid, v
                else:
                    rec = json.loads(p.read_text(encoding="utf-8"))
                    pid = rec.get("problem_id") or p.stem
                    for k, v in rec.items():
                        if (isinstance(v, str) and len(v) > 200
                                and ("bill" in k or "proposal" in k
                                     or "answer" in k)):
                            yield rel, p, pid, v
            except Exception:  # noqa: BLE001
                continue


def main() -> int:
    items = load_sets()
    rows, legs = [], 0
    per_corpus = {}
    for rel, p, pid, bill in discover_bills():
        prob = items.get(pid)
        if prob is None:
            continue  # no constraint to check against
        legs += 1
        per_corpus[rel] = per_corpus.get(rel, 0) + 1
        try:
            r = m77.scan_input_availability(prob, bill)
        except Exception as e:  # noqa: BLE001
            rows.append({"corpus": rel, "path": p.name, "pid": pid,
                         "error": str(e)[:100]})
            continue
        for msg in r.get("INPUT_UNAVAILABLE", []):
            q = msg.split("'")[1] if "'" in msg else ""
            ctx = ""
            if q:
                m = bill.find(q[:20])
                if m < 0:
                    m = bill.lower().find(q[:12].lower())
                if m >= 0:
                    ctx = bill[max(0, m - 150):m + 170] \
                        .replace("\n", " ")
            rows.append({"corpus": rel, "path": p.name, "pid": pid,
                         "firing": msg, "quoted": q, "context": ctx})
    with (OUT / "generalization.jsonl").open("w",
                                             encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"held-out bill-legs scored: {legs} "
          f"over {len(per_corpus)} corpora")
    for k, v in sorted(per_corpus.items()):
        print(f"  {k}: {v} legs")
    print(f"\nFIXED-detector firings: {len(rows)} -> "
          f"eval/r125_f31d/generalization.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
