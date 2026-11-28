#!/usr/bin/env python3
"""R143s3-b VERIFIER: independent recompute of the R-CAL panel one-shot
tally from the raw leg bytes (auditor Art. 13 — never trust the producing
driver's own summary; a diff > 0 is a finding before any verdict).

Recomputes, from eval/r143_panel/<judge>__<pid>__<order>.json alone:
  - per-judge answered rate (VALID outcome with a parsed prefer)
  - per-judge accuracy vs the sealed labels (det pass)
  - AM47 bias counters (over_novel / over_cons, det pass)
  - inter-judge agreement + Cohen's kappa (det pass, pairwise mean)
and compares with eval/r143_panel_qualification.json.
"""
import json
import math
from pathlib import Path

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
OUT = REPO / "eval" / "r143_panel"
QUAL = REPO / "eval" / "r143_panel_qualification.json"

# sealed labels from the audit branch corpus
import subprocess
raw = subprocess.run(
    ["git", "show",
     "origin/audit/r11-auditor-verdict-20261114:eval/auditor_rcal_corpus_r143.json"],
    capture_output=True, text=True, check=True).stdout
corpus = json.loads(raw)
labels = {p["problem_id"]: p["overall_preference"] for p in corpus["pairs"]}
print(f"corpus pairs: {len(labels)} | labels: "
      f"a1={sum(1 for v in labels.values() if v=='a1')} "
      f"baseline={sum(1 for v in labels.values() if v=='baseline')}")

import hashlib
def blind_order(pid: str) -> str:
    h = hashlib.sha256(f"{pid}::pair".encode()).hexdigest()
    return "a1_first" if int(h, 16) % 2 == 0 else "base_first"

# collect legs
judges = {}
for f in sorted(OUT.glob("*__*__*.json")):
    tag, pid, order = f.stem.split("__")
    r = json.loads(f.read_text())
    judges.setdefault(tag, {})[f"{pid}::{order}"] = r

# per-judge metrics (det pass = the voting legs)
metrics = {}
for tag, legs in sorted(judges.items()):
    det = [r for r in legs.values() if r["pass"] == "det"]
    n = len(det)
    answered = sum(1 for r in det if r["outcome"] == "VALID"
                   and (r.get("parsed") or {}).get("prefer") in ("A", "B"))
    correct = 0
    on = oc = 0
    for r in det:
        p = (r.get("parsed") or {}).get("prefer")
        if p not in ("A", "B"):
            continue
        chosen = r["a_is"] if p == "A" else (
            "baseline" if r["a_is"] == "a" else "a1")
        # normalize: a_is is 'a1' or 'baseline'
        chosen = r["a_is"] if p == "A" else (
            "baseline" if r["a_is"] == "a1" else "a1")
        if chosen == labels.get(r["pid"]):
            correct += 1
        if chosen == "a1" and labels.get(r["pid"]) == "baseline":
            on += 1
        elif chosen == "baseline" and labels.get(r["pid"]) == "a1":
            oc += 1
    metrics[tag] = {
        "n_det": n,
        "answered": answered,
        "answered_rate": round(answered / n, 3) if n else None,
        "accuracy": round(correct / answered, 3) if answered else None,
        "over_novel": on, "over_cons": oc,
        "imbalance": abs(on - oc),
    }

print(f"\n{'judge':9} | {'n':>3} | {'answ':>4} | {'rate':>5} | {'acc':>5} | on/oc | imb")
for tag, m in metrics.items():
    print(f"{tag:9} | {m['n_det']:3} | {m['answered']:4} | "
          f"{str(m['answered_rate']):>5} | {str(m['accuracy']):>5} | "
          f"{m['over_novel']}/{m['over_cons']} | {m['imbalance']}")

# inter-judge agreement (det, pairwise over common answered pairs)
tags = [t for t, m in metrics.items() if m["answered"]]
def vote(r):
    p = (r.get("parsed") or {}).get("prefer")
    if p not in ("A", "B"):
        return None
    return r["a_is"] if p == "A" else (
        "baseline" if r["a_is"] == "a1" else "a1")

pairs_agree = []
kappas = []
for i, t1 in enumerate(tags):
    for t2 in tags[i+1:]:
        common = []
        for key, r1 in judges[t1].items():
            if r1["pass"] != "det":
                continue
            r2 = judges[t2].get(key)
            if not r2:
                continue
            v1, v2 = vote(r1), vote(r2)
            if v1 and v2:
                common.append((v1, v2))
        if not common:
            continue
        agree = sum(1 for a, b in common if a == b) / len(common)
        pairs_agree.append(agree)
        # Cohen's kappa
        cats = ["a1", "baseline"]
        n = len(common)
        po = agree
        pe = sum(
            (sum(1 for a, b in common if a == c) / n) *
            (sum(1 for a, b in common if b == c) / n) for c in cats)
        k = (po - pe) / (1 - pe) if pe < 1 else 0.0
        kappas.append(k)

print(f"\npairwise agreement mean: "
      f"{round(sum(pairs_agree)/len(pairs_agree), 3) if pairs_agree else None} "
      f"over {len(pairs_agree)} pairs")
print(f"kappa mean: "
      f"{round(sum(kappas)/len(kappas), 3) if kappas else None}")

# compare with the driver's record
rec = json.loads(QUAL.read_text())
print("\n=== driver record vs recompute ===")
print("driver qualified:", rec.get("qualified_tags"))
print("driver kappa_mean:", rec.get("gates", {}).get("kappa_mean"))
print("driver panel_agreement:", rec.get("gates", {}).get("panel_agreement"))
drv_bias = rec.get("am47_bias", {})
for tag, m in metrics.items():
    db = drv_bias.get(f"deepseek:{tag}") or drv_bias.get(f"qwen:{tag}") \
        or drv_bias.get(f"cent-ai:{tag}") or {}
    match = (db.get("over_novel") == m["over_novel"]
             and db.get("over_cons") == m["over_cons"])
    print(f"  {tag}: driver bias {db.get('over_novel')}/{db.get('over_cons')}"
          f" vs recomputed {m['over_novel']}/{m['over_cons']} "
          f"{'MATCH' if match else 'DIFF'}")

# the acceptance gates (DIR-3 / AM47)
qual = []
for tag, m in metrics.items():
    if (m["accuracy"] is not None and m["accuracy"] >= 0.8
            and m["answered_rate"] is not None and m["answered_rate"] >= 0.9
            and m["imbalance"] <= 1):
        qual.append(tag)
print(f"\nRECOMPUTED qualified judges (acc>=0.8, answered>=0.9, |imb|<=1): {qual}")
fams = {t: ("deepseek" if t in ("dsr1", "dsv32")
            else "qwen" if t in ("qw32b", "qwen235b") else "cent-ai")
        for t in qual}
print(f"RECOMPUTED distinct non-agnes families: {len(set(fams.values()))}")
km = round(sum(kappas)/len(kappas), 3) if kappas else None
print(f"RECOMPUTED kappa_mean: {km} (gate >= 0.6: {km is not None and km >= 0.6})")
print(f"GATE: >=3 qualified: {len(qual) >= 3} | >=2 families: "
      f"{len(set(fams.values())) >= 2} | kappa>=0.6: {km is not None and km >= 0.6}")
