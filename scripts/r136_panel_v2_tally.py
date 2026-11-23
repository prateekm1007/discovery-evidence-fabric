#!/usr/bin/env python3
"""r136_panel_v2_tally — the PANEL-V2 qualification tally.

R137 CORRECTIONS (the coder directions, audited base 7caddfaa3):
1. The authoritative ten problem IDs + labels come from the FROZEN
   r5 dataset (git show 009ce91a8:eval/auditor_judgments_r11_r5.json)
   — never from whatever result files happen to exist on disk.
2. expected_legs=20 is PINNED EXPLICITLY into rcal_qualification.
3. All SIX judges are represented — a completely absent judge
   scores 0/20 and is NOT qualified; it never disappears from the
   calculation.
4. The v1/v2 comparison is RECOMPUTED from committed raw records
   (eval/r134_panel for the five HF judges, eval/r135_panel for
   hy4f) — no hard-coded V1_ACC. Paired differences are computed
   on COMMON observations only, with sample sizes reported
   (dsr1's v1 is 7/9 — one det leg transport-failed — its v2 is
   over 10; the raw percentages are NOT directly comparable).

Usage: python3 -I scripts/r136_panel_v2_tally.py
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

RAW_V2 = REPO / "eval" / "r136_panel_v2"
RAW_V1 = {"dsr1": REPO / "eval" / "r134_panel",
          "qw32b": REPO / "eval" / "r134_panel",
          "qwen235b": REPO / "eval" / "r134_panel",
          "dsv32": REPO / "eval" / "r134_panel",
          "llama4mav": REPO / "eval" / "r134_panel",
          "hy4f": REPO / "eval" / "r135_panel"}
OUT = REPO / "eval" / "r136_panel_v2_calibration.json"

# the six judges of the R136 prereg (fixed; none added or dropped)
TAGS = ["dsr1", "qw32b", "qwen235b", "dsv32", "llama4mav", "hy4f"]
FAM = {"dsr1": "deepseek", "dsv32": "deepseek",
       "qw32b": "qwen", "qwen235b": "qwen",
       "llama4mav": "meta-llama", "hy4f": "cent-ai"}
EXPECTED_LEGS = 20  # 10 frozen pairs x 2 orders — PINNED (R137 #2)


def frozen_r5_labels():
    """THE authoritative pids + labels (R137 #1): the frozen r5
    dataset bytes at 009ce91a8, not the on-disk result files."""
    out = subprocess.run(
        ["git", "show", "009ce91a8:eval/auditor_judgments_r11_r5.json"],
        capture_output=True, text=True, check=True).stdout
    r5 = json.loads(out)
    labels = {p["problem_id"]: p.get("overall_preference")
              for p in r5["pairs"]}
    frozen = {k: v for k, v in labels.items()
              if v in ("a1", "baseline")}
    if len(frozen) != 10:
        raise SystemExit(
            f"FROZEN-R5 SANITY FAIL: expected 10 labeled pairs, "
            f"got {len(frozen)} — refusing to tally")
    return frozen


def load_legs(d: Path, tag: str):
    """The raw per-leg records from a committed run dir (empty
    list when the judge has zero legs on disk — the caller keeps
    the judge in the table at 0/20)."""
    rows = []
    for f in sorted(d.glob(f"{tag}__*.json")):
        r = json.loads(f.read_text())
        rows.append({"pid": r["problem_id"], "order": r["order"],
                     "pass": r["pass"], "a_is": r["a_is"],
                     "outcome": r["outcome"],
                     "parsed": r.get("parsed")})
    return rows


def vote(leg):
    """The swap-robust read: prefer names the SLOT; a_is names the
    arm in slot A -> the voted ARM."""
    p = (leg.get("parsed") or {})
    pref = str(p.get("prefer") or "")
    if pref not in ("A", "B") or leg.get("outcome") != "VALID":
        return None
    a_is = leg["a_is"]
    if pref == "A":
        return a_is
    return "baseline" if a_is == "a1" else "a1"


def det_votes(rows):
    """pid -> voted arm, from the parity-drawn det legs only."""
    out = {}
    for l in rows:
        v = vote(l)
        if v is not None and l["pass"] == "det":
            out[l["pid"]] = v
    return out


def tally_judge(rows, labels):
    """One judge's honest row: expected=20 (pinned), valid legs,
    answered rate on the PINNED denominator, acc on the det votes
    that are comparable (VALID + a frozen-labeled pid), swap
    instability, the qualified flag."""
    valid = sum(1 for l in rows if l["outcome"] == "VALID")
    votes = det_votes(rows)
    comparable = [p for p in votes if p in labels]
    hits = sum(1 for p in comparable
               if votes[p] == labels[p])
    mir = {l["pid"]: vote(l) for l in rows
           if l["pass"] == "mir" and vote(l) is not None}
    flips = sum(1 for p, v in votes.items()
                if p in mir and mir[p] != v)
    answered = valid / EXPECTED_LEGS
    acc = (hits / len(comparable)) if comparable else None
    return {
        "legs": len(rows), "valid": valid,
        "expected_legs": EXPECTED_LEGS,
        "answered_rate": round(answered, 3),
        "answered_rate_basis": "expected legs PINNED at 20 "
                               "(10 frozen pairs x 2 orders)",
        "acc_vs_labels": round(acc, 3) if acc is not None else None,
        "hits": hits, "n_cmp": len(comparable),
        "missing_pids": sorted(set(labels) - set(votes)),
        "swap_instability": round(flips / len(votes), 3)
        if votes else None,
        "qualified": bool(acc is not None and acc >= 0.8
                          and answered >= 0.9),
    }


def main() -> int:
    labels = frozen_r5_labels()
    v2_rows = {t: load_legs(RAW_V2, t) for t in TAGS}
    v1_rows = {t: load_legs(RAW_V1[t], t) for t in TAGS}

    # ALL SIX judges represented (R137 #3): an absent judge has
    # rows=[] and scores 0/20 — never dropped from the table
    judges, engine_in = {}, {}
    for t in TAGS:
        judges[t] = tally_judge(v2_rows[t], labels)
        engine_in[t] = v2_rows[t]  # the engine sees the same rows

    # THE ENGINE TALLY (the fixed denominator PINNED explicitly)
    from discovery_fabric.engine.panel_agreement import (
        rcal_qualification, swap_robust_panel)
    engine_q = rcal_qualification(engine_in, labels,
                                  expected_legs=EXPECTED_LEGS)

    # the two-code-path check (engine vs this independent recompute)
    diffs = []
    for t in TAGS:
        e = engine_q.get(t, {})
        for k in ("answered_rate", "acc_vs_labels", "qualified"):
            ev, iv = e.get(k), judges[t].get(k)
            if ev == iv or (ev is None and iv is None):
                continue
            # the convention pair: the engine types acc as 0.0
            # when n_cmp==0 (hits/0 guarded to 0.0); the
            # independent recompute types it None (undefined).
            # Both mean "no comparable votes" and both fail the
            # qualified flag — disclosed, not counted as a diff.
            if (k == "acc_vs_labels" and e.get("n_cmp") == 0
                    and ev == 0.0 and iv is None):
                continue
            diffs.append(f"{t}.{k}: engine {ev} vs indep {iv}")

    # the qualified panel + the >=2 guard (the engine's own rule)
    qualified = [t for t in TAGS if judges[t]["qualified"]]
    fams = sorted({FAM[t] for t in qualified})
    panel = (swap_robust_panel(engine_in, qualified, labels)
             if len(qualified) >= 2 else {
                 "guard": "TYPED REFUSAL (R136): fewer than 2 "
                          "qualified judges — panel agreement "
                          "undefined",
                 "panel_agreement": None})

    # the v1/v2 paired comparison RECOMPUTED FROM RAW (R137 #5):
    # per judge, the common comparable pids only + sample sizes
    delta = {}
    for t in TAGS:
        v1v, v2v = det_votes(v1_rows[t]), det_votes(v2_rows[t])
        common = sorted(set(v1v) & set(v2v) & set(labels))
        v1_only = sorted(set(v1v) - set(v2v))
        v2_only = sorted(set(v2v) - set(v1v))
        h1 = sum(1 for p in common if v1v[p] == labels[p])
        h2 = sum(1 for p in common if v2v[p] == labels[p])
        flips = [p for p in common if v1v[p] != v2v[p]]
        delta[t] = {
            "v1_n_total": len(v1v), "v2_n_total": len(v2v),
            "n_common": len(common),
            "v1_acc_common": round(h1 / len(common), 3)
            if common else None,
            "v2_acc_common": round(h2 / len(common), 3)
            if common else None,
            "paired_delta_common": round(
                (h2 - h1) / len(common), 3) if common else None,
            "v1_sample_note": (
                f"v1 comparable n={len(v1v)}"
                + (f" ({v1_only} absent from v2)" if v1_only
                   else "")),
            "v2_sample_note": (
                f"v2 comparable n={len(v2v)}"
                + (f" ({v2_only} absent from v1)" if v2_only
                   else "")),
            "flipped_pids": flips,
            "comparability": (
                "DIRECT (same comparable sample)" if
                len(v1v) == len(v2v) == len(common) else
                "NOT DIRECTLY COMPARABLE — different samples; "
                "the paired delta is on the COMMON observations "
                f"only (n={len(common)})"),
        }

    rec = {
        "record": "R136_PANEL_V2_CALIBRATION/1.1.0 (the R137 "
                  "instrument corrections applied)",
        "claim": "c-0216 (tallied) / c-0218 (corrected)",
        "at": "2026-11-23 (sandbox clock)",
        "arm": "PANEL-V2 (the constraint line; prereg 2d1170f06)",
        "authority": {
            "pids_labels": "git show 009ce91a8:eval/"
                           "auditor_judgments_r11_r5.json (the "
                           "frozen r5 dataset — authoritative)",
            "expected_legs": "PINNED 20 (10 frozen pairs x 2 "
                             "orders), passed explicitly",
            "judges": "all six preregistered judges represented; "
                      "an absent judge scores 0/20",
            "v1_source": "committed raw records: eval/r134_panel "
                         "(dsr1,qw32b,qwen235b,dsv32,llama4mav) + "
                         "eval/r135_panel (hy4f) — recomputed, no "
                         "hard-coded baselines"},
        "n_pairs": len(labels),
        "expected_legs_per_judge": EXPECTED_LEGS,
        "judges": judges,
        "engine_qualification": engine_q,
        "two_code_path_diff": diffs or "IDENTICAL",
        "qualified": qualified, "qualified_families": fams,
        "panel": panel,
        "v1_vs_v2_paired_common": delta,
        "gate": {
            "rcal": ">=3 judges acc>=0.8 AND answered>=0.9 from "
                    ">=2 non-agnes families (bars UNCHANGED)",
            "outcome": ("MET" if len(qualified) >= 3
                        and len(fams) >= 2 else "NOT_MET")},
        "no_score_claims": True,
    }
    OUT.write_text(json.dumps(rec, indent=1) + "\n")
    print("judges (v2, expected=20 pinned):")
    for t in TAGS:
        j = judges[t]
        print(f"  {t:10} legs {j['legs']:2} valid {j['valid']:2} "
              f"answered {j['answered_rate']:.2f} "
              f"acc {j['acc_vs_labels']} (n={j['n_cmp']}) "
              f"qual {j['qualified']}")
    print("two-code-path:", diffs or "IDENTICAL")
    print("qualified:", qualified, "families:", fams)
    print("gate:", rec["gate"]["outcome"])
    print("paired (common-only):")
    for t in TAGS:
        d = delta[t]
        print(f"  {t:10} v1 {d['v1_acc_common']} (n={d['n_common']})"
              f" -> v2 {d['v2_acc_common']} "
              f"delta {d['paired_delta_common']} "
              f"[{d['comparability'][:44]}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
