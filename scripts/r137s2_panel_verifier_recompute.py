#!/usr/bin/env python3
"""r137s2_panel_verifier_recompute — the VERIFIER-side panel recompute
(Art. 29(c): the verifier never re-runs; it recomputes from committed
bytes). The twin (builder-r121s1-3e8a41d7) holds claim c-0218 EXECUTOR
over the tally script + the 23-leg resume; THIS record is the
independent verifier lane on the CURRENT committed 97 v2 legs + the v1
raw records, under the auditor's DIR-2 measurement rules:

  1. the AUTHORITATIVE pids + labels come from the frozen r5 dataset
     bytes (009ce91a8:eval/auditor_judgments_r11_r5.json), never from
     result files (DIR 2.1);
  2. the expected denominator is PINNED at 20 legs per judge and passed
     EXPLICITLY into the engine rcal_qualification (DIR 2.2);
  3. ALL SIX judges are represented; a zero-leg judge scores 0/20
     (answered 0.0, acc None-equivalent 0.0, qualified False) and never
     disappears (DIR 2.3);
  4. the v1/v2 comparison is recomputed from the committed raw v1
     records (eval/r134_panel + eval/r135_panel) — NO hard-coded
     baselines; per-judge sample sizes reported; paired differences on
     COMMON observations only (DIR 2.5; the dsr1 7/9-vs-7/10 sample
     mismatch is typed, never averaged away);
  5. the engine two-code-path check vs THIS verifier recompute, and a
     cross-check against the twin's committed interim calibration.

Zero LLM calls. Output: eval/r137s2_panel_verifier_recompute.json
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

V2 = REPO / "eval" / "r136_panel_v2"
V1_DIRS = {"dsr1": REPO / "eval" / "r134_panel",
           "qw32b": REPO / "eval" / "r134_panel",
           "qwen235b": REPO / "eval" / "r134_panel",
           "dsv32": REPO / "eval" / "r134_panel",
           "llama4mav": REPO / "eval" / "r134_panel",
           "hy4f": REPO / "eval" / "r135_panel"}
TWIN_CALIB = REPO / "eval" / "r136_panel_v2_calibration.json"
OUT = REPO / "eval" / "r137s2_panel_verifier_recompute.json"
TAGS = ["dsr1", "qw32b", "qwen235b", "dsv32", "llama4mav", "hy4f"]
EXPECTED = 20  # 10 pairs x 2 orders, PINNED (DIR 2.2)
FAM = {"dsr1": "deepseek", "dsv32": "deepseek", "qw32b": "qwen",
       "qwen235b": "qwen", "llama4mav": "meta-llama", "hy4f": "cent-ai"}

AUTHORITY = "009ce91a8:eval/auditor_judgments_r11_r5.json"


def load_authoritative():
    """The frozen r5 dataset: the 10 pids + the auditor's forced-choice
    labels, from the COMMITTED dataset bytes (git show), never from
    result files."""
    blob = subprocess.run(["git", "show", AUTHORITY], capture_output=True,
                          text=True, check=True).stdout
    doc = json.loads(blob)
    labels, dropped = {}, []
    for p in doc["pairs"]:
        lab = p.get("overall_preference")
        if lab in ("a1", "baseline"):
            labels[p["problem_id"]] = lab
        else:
            dropped.append({"pid": p["problem_id"], "label": lab})
    return labels, dropped


def load_legs(d: Path, tag: str):
    rows = []
    for f in sorted(d.glob(f"{tag}__*.json")):
        r = json.loads(f.read_text())
        rows.append({"pid": r["problem_id"], "pass": r["pass"],
                     "a_is": r["a_is"], "outcome": r["outcome"],
                     "parsed": r.get("parsed")})
    return rows


def vote(leg):
    p = leg.get("parsed") or {}
    pref = str(p.get("prefer") or "")
    if pref not in ("A", "B") or leg.get("outcome") != "VALID":
        return None
    a_is = leg["a_is"]
    return a_is if pref == "A" else ("baseline" if a_is == "a1" else "a1")


def indep_tally(rows, labels):
    """The independent recompute (separate code from the engine)."""
    votes, mirrors = {}, {}
    n_valid = 0
    for l in rows:
        if l["outcome"] == "VALID":
            n_valid += 1
        v = vote(l)
        if v is None:
            continue
        (votes if l["pass"] == "det" else mirrors)[l["pid"]] = v
    hits = sum(1 for p, v in votes.items()
               if p in labels and v == labels[p])
    n_cmp = sum(1 for p in votes if p in labels)
    flips = sum(1 for p, v in votes.items()
                if p in mirrors and mirrors[p] != v)
    return {"legs": len(rows), "valid": n_valid,
            "expected_legs": EXPECTED,
            "answered_rate": round(n_valid / EXPECTED, 3),
            "hits": hits, "n_cmp": n_cmp,
            "acc_vs_labels": round(hits / n_cmp, 3) if n_cmp else 0.0,
            "swap_instability": round(flips / len(votes), 3)
            if votes else None,
            "vote_pids": sorted(votes),
            "qualified": bool(n_cmp and hits / n_cmp >= 0.8
                              and n_valid / EXPECTED >= 0.9)}


def main() -> int:
    labels, dropped = load_authoritative()
    assert len(labels) == 10, f"authoritative corpus != 10 pairs: {len(labels)}"

    arms = {}
    for tag in TAGS:
        arms.setdefault("v2", {})[tag] = load_legs(V2, tag)
        arms.setdefault("v1", {})[tag] = load_legs(V1_DIRS[tag], tag)

    from discovery_fabric.engine.panel_agreement import (
        rcal_qualification, swap_robust_panel)

    out = {"record": "R137S2_PANEL_VERIFIER_RECOMPUTE/1.0.0",
           "role": "VERIFIER (Art. 29(c)); the executor lane is the "
                   "twin's c-0218 (r137-panel-fixes-live-multi-mechanism)",
           "session": "builder-r134s2",
           "at": "2026-11-23 (sandbox clock)",
           "authority_dataset": AUTHORITY,
           "authority_labels": labels,
           "authority_dropped_non_forced_choice": dropped,
           "expected_legs_pinned": EXPECTED,
           "arms": {}, "engine_vs_indep_diffs": [],
           "twin_calibration_crosscheck": [], "v1_vs_v2_paired": {},
           "qualified_judges": [], "qualified_families": [],
           "panel_guard": None}

    for arm, jd in arms.items():
        # ALL SIX judges passed to the engine — zero-leg judges stay
        # represented (DIR 2.3); the engine scores an empty judge
        # answered 0.0 / qualified False.
        engine_q = rcal_qualification(jd, labels, expected_legs=EXPECTED)
        indep = {t: indep_tally(jd[t], labels) for t in TAGS}
        for t in TAGS:
            e, i = engine_q.get(t, {}), indep[t]
            for k in ("answered_rate", "acc_vs_labels", "hits", "n_cmp",
                      "valid"):
                ev, iv = e.get(k), i.get(k)
                if ev is None:
                    continue
                if isinstance(ev, (int, float)) and abs(ev - iv) > 1e-9:
                    out["engine_vs_indep_diffs"].append(
                        f"{arm}.{t}.{k}: engine {ev} vs indep {iv}")
        out["arms"][arm] = {"engine": engine_q, "independent": indep}

    # the >=2-qualified guard on the V2 arm (the acceptance arm)
    q2 = [t for t in TAGS if out["arms"]["v2"]["independent"][t]["qualified"]]
    out["qualified_judges"] = q2
    out["qualified_families"] = sorted({FAM[t] for t in q2})
    if len(q2) >= 2:
        panel = swap_robust_panel(
            {t: arms["v2"][t] for t in TAGS}, q2, labels)
        out["panel_guard"] = {"state": ">=2 qualified — agreement computable",
                              "panel": panel}
    else:
        out["panel_guard"] = {
            "state": "TYPED REFUSAL: fewer than 2 qualified judges — "
                     f"{len(q2)} qualified {q2}; panel agreement "
                     "undefined (no gate claim possible)"}

    # the v1/v2 PAIRED comparison on COMMON observations (DIR 2.5)
    for t in TAGS:
        v1, v2 = out["arms"]["v1"]["independent"][t], \
            out["arms"]["v2"]["independent"][t]
        v1_votes = {p: None for p in v1["vote_pids"]}
        # rebuild vote maps for the common-observation diff
        def votes_of(rows):
            vv = {}
            for l in rows:
                v = vote(l)
                if v is not None and l["pass"] == "det":
                    vv[l["pid"]] = v
            return vv
        m1 = votes_of(arms["v1"][t])
        m2 = votes_of(arms["v2"][t])
        common = sorted(set(m1) & set(m2) & set(labels))
        h1 = sum(1 for p in common if m1[p] == labels[p])
        h2 = sum(1 for p in common if m2[p] == labels[p])
        out["v1_vs_v2_paired"][t] = {
            "v1": {"acc": v1["acc_vs_labels"], "n_cmp": v1["n_cmp"],
                   "answered": v1["answered_rate"]},
            "v2": {"acc": v2["acc_vs_labels"], "n_cmp": v2["n_cmp"],
                   "answered": v2["answered_rate"]},
            "common_n": len(common), "common_pids": common,
            "v1_hits_on_common": h1, "v2_hits_on_common": h2,
            "paired_diff_common": round(h2 - h1, 3) if common else None,
            "sample_mismatch_typed": v1["n_cmp"] != v2["n_cmp"],
        }

    # cross-check vs the twin's committed interim calibration
    if TWIN_CALIB.exists():
        tc = json.loads(TWIN_CALIB.read_text())
        for t, tj in (tc.get("judges") or {}).items():
            mine = out["arms"]["v2"]["independent"].get(t, {})
            for k in ("answered_rate", "acc_vs_labels"):
                if k in tj and k in mine and tj[k] != mine[k]:
                    out["twin_calibration_crosscheck"].append(
                        f"{t}.{k}: twin {tj[k]} vs verifier {mine[k]}")

    OUT.write_text(json.dumps(out, indent=1) + "\n")
    summary = {
        "authoritative_n_pairs": len(labels),
        "v2_judges": {t: {k: out["arms"]["v2"]["independent"][t][k]
                          for k in ("legs", "valid", "answered_rate",
                                    "n_cmp", "acc_vs_labels",
                                    "qualified")}
                      for t in TAGS},
        "v1_judges": {t: {k: out["arms"]["v1"]["independent"][t][k]
                          for k in ("legs", "valid", "n_cmp",
                                    "acc_vs_labels")}
                      for t in TAGS},
        "qualified_judges": q2,
        "panel_guard_state": out["panel_guard"]["state"],
        "engine_vs_indep_diffs": out["engine_vs_indep_diffs"] or "IDENTICAL",
        "twin_calibration_crosscheck":
            out["twin_calibration_crosscheck"] or "IDENTICAL",
        "v1_vs_v2_paired": {t: {k: v[k] for k in
                                ("common_n", "v1_hits_on_common",
                                 "v2_hits_on_common", "paired_diff_common",
                                 "sample_mismatch_typed")}
                            for t, v in out["v1_vs_v2_paired"].items()},
    }
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
