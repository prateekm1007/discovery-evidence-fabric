#!/usr/bin/env python3
"""r158_p5_smoke.py — one-item plumbing validation BEFORE the real
run (pc-01 end-to-end; writes NO checkpoint bytes: a smoke record is
not a measurement). Validates: the extended prompt's size/parse, the
canary scan, T1/T2, both judge seats, the adjudication."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import r158_p5_tokenrouter_run as R

items = [json.loads(l) for l in R.CORPUS.read_text().splitlines() if l.strip()]
it = items[0]
print("item:", it["item_id"], "|", it.get("public_date"))

p = R.gen_prompt(it)
print(f"prompt: {len(p)} chars (~{len(p)//4} tokens)")

raw, st = R.tr_chat(p)
print("gen:", st, "| raw len:", len(raw))
if not raw:
    print("RAW TAIL:", raw[:200] if raw else "(empty)")
    sys.exit(1)

try:
    parsed = R.parse_gen(raw)
    print("parsed keys:", sorted(parsed.keys()))
    print("hypothesis:", str(parsed.get("hypothesis"))[:150])
    print("t1:", json.dumps(parsed.get("t1_falsifier"), default=str)[:200])
    print("t2:", json.dumps(parsed.get("t2_citations"), default=str)[:250])
except Exception as e:
    print("PARSE FAIL:", e)
    print("RAW TAIL:", raw[-400:])
    sys.exit(1)

lure = {l["item_id"]: l for l in R.LURES}[it["item_id"]]
hits = R.canary_scan(raw, [lure])
print("canary hits:", hits)

t1v = R.t1_valid(parsed.get("t1_falsifier"))
print("t1_valid:", t1v)

t2_recs = [R.resolve_citation(c.get("citation", ""), parsed.get("key_mechanism", ""))
           for c in (parsed.get("t2_citations") or [])[:3]]
print("t2:", json.dumps(t2_recs, default=str)[:400])
print("t2_valid:", R.t2_valid(t2_recs))

jp = R.judge_prompt(it, parsed)
j1s, s1 = R.j1_chat(jp)
print("J1:", s1, "|", (j1s or "")[:120])
j2s, s2 = R.j2_chat(jp)
print("J2:", s2, "|", (j2s or "")[:120])
try:
    j1v = R.parse_judge_output(j1s)["recovery"]
except Exception as e:
    j1v = None; print("J1 parse fail:", str(e)[:100])
try:
    j2v = R.parse_judge_output(j2s)["recovery"]
except Exception as e:
    j2v = None; print("J2 parse fail:", str(e)[:100])
print("adjudicated:", R.adjudicate(j1v, j2v))
print("SMOKE OK" if (j1v or j2v) else "SMOKE: judges failed")
