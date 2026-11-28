#!/usr/bin/env python3
"""R189S1 DIR-2/DIR-3 byte verification (owner-R189 directions).

DIR 2: r184 holdout re-verify from pair bytes (count, outcome-by-outcome,
wins+ties, Wilson CI, gate >=15/24 AND ci_lower > 0.50).
DIR 3: problem_router actual routing from bytes (does it route ALL classes
to CHEAP_ARM as the direction states, or the split the ship committed?);
kill decision doc; collider ablation record.

Zero generator/judge calls. Session: builder-r189s1.
"""
import json, glob, os, math

REPO = "/home/z/my-project/discovery-evidence-fabric"

def wilson(k, n, z=1.959963985):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    hw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0.0, c - hw), 3), round(p, 3), round(min(1.0, c + hw), 3))

print("=" * 72)
print("DIR 2 — r184 HOLDOUT VERIFY FROM BYTES")
print("=" * 72)
pairs = sorted(glob.glob(f"{REPO}/eval/r184_holdout_run/pair_*.json"))
print(f"1. pair_*.json files present: {len(pairs)} (claim 24)")
w = t = l = bad = 0
outcomes = []
for f in pairs:
    d = json.load(open(f))
    o = d.get("outcome")
    outcomes.append((os.path.basename(f).replace("pair_", "").replace(".json", ""), o))
    if o == "WIN": w += 1
    elif o == "TIE": t += 1
    elif o == "LOSS": l += 1
    else: bad += 1
wt = w + t
lo, p, hi = wilson(wt, len(pairs))
print(f"2. per-pair outcome read: WIN {w} / TIE {t} / LOSS {l} / unparsed {bad}")
losses = [pid for pid, o in outcomes if o == "LOSS"]
print(f"   LOSS pids: {losses}")
print(f"3. wins+ties = {wt}/{len(pairs)} (claim 22)")
print(f"   Wilson 95% CI = [{lo}, {p}, {hi}] (claim lower 0.742)")
print(f"4. GATE: wins+ties >= 15/24? {'YES' if wt >= 15 else 'NO'} ({wt} >= 15)")
print(f"   GATE: ci_lower > 0.50? {'YES' if lo > 0.50 else 'NO'} ({lo} > 0.50)")
print(f"   -> DIR-2 ACCEPT {'MET' if (len(pairs) == 24 and wt == 22 and lo > 0.50) else 'CHECK ABOVE'}")

print()
print("=" * 72)
print("DIR 3 — ROUTER + KILL DECISION + COLLIDER FROM BYTES")
print("=" * 72)
# 3a. the router's actual routing table
import importlib.util
spec = importlib.util.spec_from_file_location(
    "pr", f"{REPO}/discovery_fabric/engine/problem_router.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
attrs = [a for a in dir(m) if not a.startswith("_")]
print(f"problem_router module attrs: {attrs[:20]}")
# find the route function/table
for name in ["route", "route_problem", "classify", "ROUTE", "ROUTE_TABLE", "CLASSES"]:
    if hasattr(m, name):
        obj = getattr(m, name)
        if callable(obj):
            # probe each declared class through the router
            classes = getattr(m, "KNOWN_QUESTION_TYPES", None) or \
                      getattr(m, "QUESTION_TYPES", None) or \
                      ["intervention-proposal", "novel-mechanism", "unknown", ""]
            print(f"routing via {name}():")
            for qt in classes:
                try:
                    print(f"   question_type={qt!r:28s} -> {obj(qt)}")
                except Exception as e:
                    print(f"   question_type={qt!r:28s} -> ERR {type(e).__name__}")
        else:
            print(f"{name} = {json.dumps(obj, default=str)[:400]}")

# 3b. kill decision doc
kd = f"{REPO}/eval/r183_kill_decision.json"
print()
print(f"kill decision doc: {kd}")
print(f"  exists: {os.path.exists(kd)}")
if os.path.exists(kd):
    d = json.load(open(kd))
    print(f"  record: {d.get('record', '?')}")
    print(f"  keys: {list(d.keys())}")
    for k in ["decision", "kill", "genuine", "genuine_wins", "n", "wilson",
              "kill_math", "shipped", "retired", "conclusion"]:
        if k in d:
            print(f"  {k}: {json.dumps(d[k], default=str)[:300]}")

# 3c. collider ablation record
print()
collider_sources = [
    f"{REPO}/eval/r183_collider_run/SUMMARY.json",
    f"{REPO}/eval/r185_judge_audit/tally.json",
]
for src in collider_sources:
    print(f"collider record: {src}")
    print(f"  exists: {os.path.exists(src)}")
if os.path.exists(collider_sources[0]):
    d = json.load(open(collider_sources[0]))
    print(f"  SUMMARY keys: {list(d.keys())[:12]}")
    for k in ["record", "genuine", "delta", "collider_delta", "verdict",
              "conclusion", "kill"]:
        if k in d:
            print(f"  {k}: {json.dumps(d[k], default=str)[:300]}")
