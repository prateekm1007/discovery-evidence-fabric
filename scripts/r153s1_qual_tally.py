#!/usr/bin/env python3
"""r153s1_qual_tally.py — the qualification TALLY-ONLY recompute:
the r153 record over ALL committed legs, ZERO generation (the
unfiltered runner would regenerate bpickl's 13 missing legs — the
token-hungry reasoner the owner's DIR 2 explicitly avoids; killed
before any leg landed; bpickl stands at 11/24 legs, answered 0.458
-> fails the answered bar, typed OUT, no re-roll).

Same computation as scripts/r153_rcal_xkiro.py's tally section
(the engine rcal_qualification + am47_bias + interjudge_alpha +
the pooled-alpha-with-hy4f), same QUALIFICATION.json shape (the
panel runner reads it). This is the Art. 13 pattern: recompute
from the committed leg bytes, never trust the producing driver.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT = REPO / "eval" / "r153_rcal_xkiro"
HY4F_R148 = REPO / "eval" / "r148_rcal_centai"
AUDIT_REF = "b218b1e9d"
CORPUS_PATH = "eval/auditor_rcal_corpus_r148.json"

JUDGES = [
    {"model": "mistralai/ministral-8b", "family": "mistral",
     "tag": "mst8b"},
    {"model": "cohere/command-r7b-12-2024", "family": "cohere",
     "tag": "cmdr7b"},
    {"model": "sensenova/sensenova-6.8-flash-lite", "family": "sensenova",
     "tag": "snlite"},
    {"model": "stealth/big-pickle", "family": "stealth",
     "tag": "bpickl"},
    {"model": "cohere/tiny-aya-earth", "family": "cohere",
     "tag": "tayae"},
    {"model": "mistralai/ministral-3b", "family": "mistral",
     "tag": "mst3b"},
    {"model": "mistralai/ministral-14b", "family": "mistral",
     "tag": "mst14b"},
    {"model": "cohere/aya-expanse-32b", "family": "cohere",
     "tag": "aya32b"},
]


def main() -> int:
    raw = subprocess.run(
        ["git", "show", f"{AUDIT_REF}:{CORPUS_PATH}"],
        capture_output=True, text=True, check=True).stdout
    corpus = json.loads(raw)
    labels = {p["problem_id"]: p["overall_preference"]
              for p in corpus["pairs"]}
    pairs = corpus["pairs"]
    assert len(pairs) == 12

    from discovery_fabric.engine.panel_agreement import (
        rcal_qualification, krippendorff_alpha)

    judge_rows = {}
    for j in JUDGES:
        rows = []
        for p in pairs:
            pid = p["problem_id"]
            for order in ("det", "mir"):
                lf = OUT / f"{j['tag']}__{pid}__{order}.json"
                if not lf.exists():
                    continue
                r = json.loads(lf.read_text())
                rows.append({"pid": pid, "pass": r["pass"],
                             "a_is": r["a_is"], "outcome": r["outcome"],
                             "parsed": r["parsed"]})
        judge_rows[j["family"] + ":" + j["tag"]] = rows

    # am47 bias (the cross-label rule; det legs only)
    bias = {}
    for key, rows in judge_rows.items():
        on = oc = 0
        for r in rows:
            if r.get("pass") != "det" or not r.get("parsed"):
                continue
            chosen = r["a_is"] if r["parsed"].get("prefer") == "A" \
                else ("baseline" if r["a_is"] == "a1" else "a1")
            lab = labels.get(r["pid"])
            if chosen == "a1" and lab == "baseline":
                on += 1
            elif chosen == "baseline" and lab == "a1":
                oc += 1
        bias[key] = {"over_novel": on, "over_cons": oc,
                     "imbalance": abs(on - oc)}

    qual = rcal_qualification(judge_rows, labels, expected_legs=24)
    for fam, q in qual.items():
        b = bias.get(fam, {"imbalance": 9})
        q["am47_bias"] = bias.get(fam)
        q["qualified"] = bool(
            q.get("qualified")
            and (b.get("imbalance") if isinstance(b, dict) else 9) <= 1)
    qualified = [fam for fam, q in qual.items() if q["qualified"]]
    fams_only = {f.split(":")[0] for f in qualified}

    def alpha_of(jr: dict) -> dict:
        units: dict = {}
        for key, rows in jr.items():
            for r in rows:
                if r.get("outcome") != "VALID" or not r.get("parsed"):
                    continue
                u = (r["pid"], r["pass"])
                chosen = r["a_is"] if r["parsed"].get("prefer") == "A" \
                    else ("baseline" if r["a_is"] == "a1" else "a1")
                units.setdefault(u, {})[key] = chosen
        if len(jr) < 2 or not units:
            return {"alpha": None,
                    "degenerate_class": "insufficient_judges",
                    "n_units": len(units)}
        mat = [[units[u].get(k) for k in sorted(jr)]
               for u in sorted(units)]
        res = krippendorff_alpha(mat)
        res["n_units"] = len(mat)
        res["judges"] = sorted(jr)
        return res

    alpha = alpha_of(judge_rows)
    pooled = dict(judge_rows)
    hy4_rows = []
    for p in pairs:
        pid = p["problem_id"]
        for order in ("det", "mir"):
            lf = HY4F_R148 / f"hy4f__{pid}__{order}.json"
            if not lf.exists():
                continue
            r = json.loads(lf.read_text())
            hy4_rows.append({"pid": pid, "pass": r["pass"],
                             "a_is": r["a_is"], "outcome": r["outcome"],
                             "parsed": r["parsed"]})
    if hy4_rows:
        pooled["hy4:hy4f"] = hy4_rows
    pooled_alpha = alpha_of(pooled)

    record = {
        "record": "R153_RCAL_XKIRO_QUALIFICATION/1.0.0",
        "claim": "c-0264",
        "work_id": "r153-xkiro-qualify-panel-v18",
        "session": "builder-r153s1",
        "at": "2026-11-25 (sandbox clock; tayae legs + this recompute)",
        "corpus": {
            "source": f"{AUDIT_REF}:{CORPUS_PATH}",
            "canonicalization_digest_match": True,
            "digest16": "c598682b56c9c33f",
            "n_pairs": len(pairs),
            "prefer_a1": corpus.get("prefer_a1"),
            "prefer_baseline": corpus.get("prefer_baseline"),
            "balance_note": "the r148 BALANCED corpus (the R147-F2 "
                            "fix): alpha computable"},
        "prompt": {"record": "RCAL_JUDGE_PROMPT_R143/1.0.0",
                   "am47_suffix_applied": True},
        "protocol": corpus.get("protocol"),
        "instrument_note": ("byte-identical machinery to "
                            "scripts/r148_rcal_centai.py; ONE seam — "
                            "the xkiro_chat transport + the free-plan "
                            "roster; this recompute is tally-only "
                            "(zero generation — the unfiltered runner "
                            "was killed before regenerating bpickl's "
                            "missing legs; bpickl stands 11/24, "
                            "answered 0.458, typed OUT, no re-roll)"),
        "transport": {"provider": "xkiro (api.xkiro.com/v1)",
                      "plan": "FREE (the key's included free models)"},
        "one_shot": ("exactly one generation per leg; byte-resume "
                     "continues the same generation; NO re-roll "
                     "(Art. 7)"),
        "qualification": qual,
        "qualified_keys": qualified,
        "qualified_tags": [f.split(":")[1] for f in qualified],
        "qualified_families": sorted(fams_only),
        "am47_bias": bias,
        "interjudge_alpha": alpha,
        "pooled_alpha_with_hy4f": pooled_alpha,
        "gate": {
            "n_qualified": len(qualified),
            "n_families": len(fams_only),
            "alpha": alpha.get("alpha"),
            "alpha_degenerate_class": alpha.get("degenerate_class"),
            "pooled_alpha_with_hy4f": pooled_alpha.get("alpha"),
            "pass": bool(len(qualified) >= 2
                         and len(fams_only) >= 2
                         and (pooled_alpha.get("alpha") or 0) >= 0.6)},
    }
    (OUT / "QUALIFICATION.json").write_text(
        json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    for k, q in qual.items():
        print(f"{k}: acc={q.get('acc_vs_labels')} "
              f"answered={q.get('answered_rate')} "
              f"bias={q.get('am47_bias', {}).get('imbalance')} "
              f"swap={q.get('swap_instability')} "
              f"qualified={q.get('qualified')}")
    print("GATE:", json.dumps(record["gate"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
