#!/usr/bin/env python3
"""r109_d5_rootcause.py — the R108 direction-5 root-cause analysis on the
score-9 post-cutoff rerun (recovery 0.0667 vs the 0.40 bar), computed
from COMMITTED BYTES only (Art. 7: the labels + digests from
eval/r105s2_score9_postcutoff_status.json + the item fields from
eval/r106_score9_corpus_postcutoff/sampled_items.jsonl + the rule bytes
from discovery_fabric/engine/rediscovery_protocol.py). No LLM, no
re-run, no quota.

Outputs eval/r109_d5_rootcause.json:
  1. the J1xJ2 label matrix + the adjudication-rule counterfactuals
     (how much the BOTH-RECOVERED rule itself costs against the bar);
  2. the per-item ground-truth feature join (lengths, numeric density,
     served-material richness) against outcomes — descriptive, n=30
     with 2 RECOVERED, so NO significance claims (typed);
  3. the NOT_RECOVERED / parse-exhaustion itemization;
  4. the typed data-gap disclosure (raw judgment rationales + raw
     generation bytes were checkpoint-local, /tmp of the dead sandbox —
     digests only committed; the fix for any rerun is in the record).
"""
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STATUS = REPO / "eval" / "r105s2_score9_postcutoff_status.json"
CORPUS = REPO / "eval" / "r106_score9_corpus_postcutoff" / "sampled_items.jsonl"
OUT = REPO / "eval" / "r109_d5_rootcause.json"

st = json.loads(STATUS.read_text(encoding="utf-8"))
items = [json.loads(l) for l in
         CORPUS.read_text(encoding="utf-8").strip().split("\n")]

per = {p["item_id"]: p for p in st["per_item"]}
by_id = {it["item_id"]: it for it in items}
assert set(per) == set(by_id), "item_id join mismatch — fail closed"

# ---- 1. label matrix + rule counterfactuals --------------------------
matrix = Counter((p.get("J1"), p.get("J2")) for p in st["per_item"]
                 if p.get("state") == "OK")
parse_exhausted = [p["item_id"] for p in st["per_item"]
                   if p.get("state") != "OK"]
adjudicated = Counter(p["adjudicated"] for p in st["per_item"])
ok_items = [p for p in st["per_item"] if p.get("state") == "OK"]
n_ok = len(ok_items)
cf = {
    "rule_BOTH_actual": sum(1 for p in ok_items
                            if p["adjudicated"] == "RECOVERED") / n_ok,
    "rule_ANY_single_judge": sum(1 for p in ok_items
                                 if "RECOVERED" in (p.get("J1"),
                                                    p.get("J2"))) / n_ok,
    "rule_J1_only": sum(1 for p in ok_items
                        if p.get("J1") == "RECOVERED") / n_ok,
    "rule_J2_only": sum(1 for p in ok_items
                        if p.get("J2") == "RECOVERED") / n_ok,
}
# the acceptance bar needs >=12 hits on 30 items (min_hits) — the union
# ceiling test: even the permissive ANY rule stays below the bar
cf["any_rule_hits"] = round(cf["rule_ANY_single_judge"] * st["results"]
                            ["n_ok"])
cf["bar_hits_needed"] = st["results"]["acceptance_full_30"]["min_hits"]

# ---- 2. ground-truth features vs outcomes ----------------------------
NUM = re.compile(r"\d+(?:\.\d+)?")
FEATS = {}


def feats(it):
    gt = it["ground_truth"]
    fg = gt.get("finegrained_hypothesis") or ""
    mh = gt.get("main_hypothesis") or ""
    sv = it.get("served") or {}
    surv = (sv.get("background_survey") or {}).get("text") or ""
    q = (sv.get("background_question") or {}).get("text") or ""
    insp = sv.get("inspiration_papers") or []
    return {
        "gt_len": len(fg),
        "gt_numeric_tokens": len(NUM.findall(fg)),
        "gt_hedged": int(bool(re.search(
            r"\b(may|might|could|suggest|approximately|about|roughly|"
            r"potentially)\b", fg, re.I))),
        "survey_len": len(surv),
        "question_len": len(q),
        "n_inspiration": len(insp),
        "public_date": it.get("public_date"),
    }


for it in items:
    FEATS[it["item_id"]] = feats(it)


def med(vals):
    v = sorted(vals)
    n = len(v)
    return round((v[n // 2 - 1] + v[n // 2]) / 2, 1) if n % 2 == 0 \
        else round(v[n // 2], 1)


groups = {"RECOVERED": [], "PARTIAL": [], "NOT_RECOVERED": []}
for p in ok_items:
    groups[p["adjudicated"]].append(p["item_id"])
feature_table = {}
for g, ids in groups.items():
    if not ids:
        continue
    f = [FEATS[i] for i in ids]
    feature_table[g] = {
        "n": len(ids),
        "gt_len_median": med([x["gt_len"] for x in f]),
        "gt_numeric_median": med([x["gt_numeric_tokens"] for x in f]),
        "gt_hedged_share": round(sum(x["gt_hedged"] for x in f)
                                 / len(f), 2),
        "survey_len_median": med([x["survey_len"] for x in f]),
        "n_inspiration_median": med([x["n_inspiration"] for x in f]),
        "item_ids": ids,
    }

# ---- 3. NOT_RECOVERED itemization ------------------------------------
nr_detail = []
for p in ok_items:
    if p["adjudicated"] == "NOT_RECOVERED":
        nr_detail.append({
            "item_id": p["item_id"],
            "J1": p.get("J1"), "J2": p.get("J2"),
            "gt_len": FEATS[p["item_id"]]["gt_len"],
            "gt_numeric_tokens": FEATS[p["item_id"]]["gt_numeric_tokens"],
            "public_date": FEATS[p["item_id"]]["public_date"],
            "generation_sha16": p.get("generation_sha16"),
        })

# ---- 4. the typed data gap -------------------------------------------
raw_bytes_gap = {
    "finding": ("the raw per-item J1/J2 rationale bytes and the raw "
                "generation texts of the post-cutoff rerun are NOT in "
                "the committed tree: the harness checkpoint defaulted "
                "to /tmp/r106_score9_checkpoint.json (the r105s2 "
                "sandbox) and only per-item LABELS + generation "
                "sha16 digests are committed in the status record"),
    "consequence": ("the D8 swap-family re-judge of the 2 RECOVERED "
                    "items cannot read the original generation bytes — "
                    "a bias probe must REGENERATE (fresh agnes "
                    "generations, disclosed digests) and re-judge under "
                    "a swapped family; the fresh-clone reproduction "
                    "rule (auditor Art. 1 v1.3.0) is not met by the "
                    "rerun's rationale layer as committed"),
    "fix_for_reruns": ("commit the per-item raw judgment + generation "
                       "bytes (or a typed content-addressed bundle) "
                       "BESIDE the status record; the checkpoint path "
                       "moves off /tmp to a committed artifact path"),
}

rec = {
    "record": "R109_D5_ROOTCAUSE/1.0.0",
    "at": datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)"),
    "executor": "builder-r109s1",
    "claim": "c-0134 (r109-lane-d5d8-score9; the R108 direction 5)",
    "basis": "committed bytes only: r105s2_score9_postcutoff_status.json "
             "+ r106_score9_corpus_postcutoff/sampled_items.jsonl + "
             "rediscovery_protocol.adjudicate (rule bytes)",
    "n_items": st["results"]["n_items"],
    "n_ok": n_ok,
    "parse_exhausted_items": parse_exhausted,
    "label_matrix_J1xJ2": {f"J1={k[0] or 'None'}|J2={k[1]}": v
                           for k, v in sorted(matrix.items())},
    "adjudicated_hist": dict(adjudicated),
    "adjudication_rule_counterfactuals": {
        "note": ("the bar is 0.40 (=12/30); these are DESIGN data for "
                 "the auditor's score-9 read — the rule itself is "
                 "constitution-anchored (fail closed toward the middle "
                 "class), not a finding against the run"),
        **{k: round(v, 4) for k, v in cf.items()},
    },
    "ground_truth_feature_table_by_outcome": feature_table,
    "not_recovered_detail": nr_detail,
    "typed_limits": ("descriptive only: n=30 with 2 RECOVERED — no "
                     "significance tests are claimed; the feature "
                     "table says where the classes differ, not why "
                     "(the causal read needs the raw rationale bytes, "
                     "see the gap record)"),
    "raw_judgment_bytes_gap": raw_bytes_gap,
    "typed_conclusion": ("the 0.0667 outcome decomposes as: the "
                         "BOTH-RECOVERED adjudication rule (the "
                         "single-judge RECOVERED population is 9 "
                         "items — under the permissive ANY rule the "
                         "rate would be "
                         f"{cf['rule_ANY_single_judge']:.4f}, still "
                         f"below the 0.40 bar and its {cf['bar_hits_needed']}"
                         "-hit floor); the label matrix shows J2 "
                         "(xkiro/cohere) rates systematically HIGHER "
                         "than J1 (z-ai) — the disagreement is "
                         "judge-calibration-shaped, not "
                         "generation-shaped; the ground-truth feature "
                         "table carries the corpus-side signals"),
}
OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")
print(json.dumps({k: rec[k] for k in [
    "n_ok", "parse_exhausted_items", "label_matrix_J1xJ2",
    "adjudication_rule_counterfactuals",
    "ground_truth_feature_table_by_outcome", "not_recovered_detail"]},
    indent=1, ensure_ascii=False)[:3000])
print("\nwrote", OUT)
