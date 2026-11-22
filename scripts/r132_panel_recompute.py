#!/usr/bin/env python3
"""R132 INDEPENDENT panel tally recompute (auditor Art. 13 — never the
producing driver's own summary; reads ONLY the raw per-leg records in
eval/r132_panel/ + the audit-branch label bytes).

Protocol (amendment 1): every leg records its own `pass` (det|mir) and
`a_is` (which arm was shown as A) — the tally unswaps from the record
itself, not from a recomputed convention. Per judge x pair there are
TWO orders (the deterministic r9 sha-parity order + its mirror); the
judge's vote per pair = the majority of its two order-passes (a split
= tie).

Computes:
  1. per-judge R-CAL: accuracy vs the r5 prefer labels (exact incl.
     TIE), answered_rate (VALID outcome / legs).
  2. qualification: acc>=0.8 AND answered>=0.9.
  3. the qualified panel: per-pair majority prefer vs the auditor
     (agreement), pairwise Cohen's kappa on prefer (mean).
  4. AUC: the qualified panel's mean novelty separating the gold-set
     4 GOOD from the 6 BAD specimens (Mann-Whitney U, GOOD>BAD).

Writes eval/r132_panel_calibration.json (the gate record).

Usage: python3 -I scripts/r132_panel_recompute.py
"""
import json
import subprocess
import sys
from itertools import combinations
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "eval" / "r132_panel"
OUT = REPO / "eval" / "r132_panel_calibration.json"

JUDGE_FAMILIES = ["meta-llama", "qwen", "deepseek", "cohere"]
GEN_FAMILY = "agnes (z-ai gateway)"


def _vote(rec):
    """Unswap one VALID record into (prefer_in_arm_terms, novelty dict)."""
    p = rec["parsed"]
    a_is = rec["a_is"]  # "a1" | "baseline"
    pref = str(p.get("prefer") or "")
    out = {}
    if pref in ("A", "B"):
        pick_arm = a_is if pref == "A" else (
            "baseline" if a_is == "a1" else "a1")
        out["prefer"] = pick_arm
    else:
        out["prefer"] = "tie"
    for ax in ("N", "F", "T", "C"):
        a, b = p.get(f"{ax}_A"), p.get(f"{ax}_B")
        out[f"{ax}_a1"], out[f"{ax}_base"] = (
            (a, b) if a_is == "a1" else (b, a))
    return out


def _pair_votes(fam, pid, raw):
    """A judge's vote on a pair = majority of its VALID order-passes."""
    votes = []
    for f, p, r in raw:
        if f != fam or p != pid or r.get("outcome") != "VALID":
            continue
        votes.append(_vote(r))
    if not votes:
        return None
    counts = {}
    for v in votes:
        counts[v["prefer"]] = counts.get(v["prefer"], 0) + 1
    top = max(counts.values())
    winners = [k for k, v in counts.items() if v == top]
    prefer = winners[0] if len(winners) == 1 else "tie"
    # novelty per arm = mean over the order-passes
    nov = {}
    for arm in ("a1", "base"):
        vals = [v[f"N_{arm}"] for v in votes
                if v.get(f"N_{arm}") is not None]
        nov[arm] = round(sum(vals) / len(vals), 3) if vals else None
    return {"prefer": prefer, "n_passes": len(votes), "novelty": nov}


def main() -> int:
    raw = []
    for f in sorted(RAW.glob("*.json")):
        stem = f.stem
        if stem.count("__") != 2:
            continue
        family, pid, tag = stem.split("__", 1)[0], None, None
        parts = f.stem.split("__")
        family, pid, tag = parts[0], parts[1], parts[2]
        r = json.loads(f.read_text())
        if family in JUDGE_FAMILIES:
            raw.append((family, pid, r))
    pids = sorted({p for _, p, _ in raw})
    labels = {}
    for _, p, r in raw:
        a = str(r.get("auditor_prefer") or "").lower()
        labels[p] = a if a in ("a1", "baseline", "tie") else "tie"

    # ---- 1. per-judge R-CAL ----
    judges = {}
    for fam in JUDGE_FAMILIES:
        legs = [(p, r) for f, p, r in raw if f == fam]
        valid = [r for _, r in legs if r.get("outcome") == "VALID"]
        answered = len(valid) / len(legs) if legs else 0.0
        hits = n_cmp = 0
        for p in pids:
            v = _pair_votes(fam, p, raw)
            if v is None:
                continue
            n_cmp += 1
            if v["prefer"] == labels[p]:
                hits += 1
        acc = hits / n_cmp if n_cmp else 0.0
        judges[fam] = {
            "legs": len(legs), "valid": len(valid),
            "answered_rate": round(answered, 3),
            "acc_vs_r5_prefer": round(acc, 3), "hits": hits,
            "n_cmp": n_cmp,
            "qualified": bool(acc >= 0.8 and answered >= 0.9),
        }
    qualified = [f for f, j in judges.items() if j["qualified"]]

    # ---- 2. panel agreement + pairwise kappa (qualified only) ----
    per_pair = {}
    panel_votes = {}
    for p in pids:
        prefs = [_pair_votes(f, p, raw)["prefer"] for f in qualified
                 if _pair_votes(f, p, raw) is not None]
        if not prefs:
            continue
        counts = {}
        for x in prefs:
            counts[x] = counts.get(x, 0) + 1
        top = max(counts.values())
        winners = [k for k, v in counts.items() if v == top]
        maj = winners[0] if len(winners) == 1 else "tie"
        panel_votes[p] = prefs
        per_pair[p] = {"panel_majority": maj, "auditor": labels[p],
                       "match": maj == labels[p], "votes": prefs}
    agreement = (sum(1 for v in per_pair.values() if v["match"])
                 / len(per_pair)) if per_pair else 0.0

    def kappa(pa, pb):
        cats = sorted(set(pa) | set(pb))
        n = len(pa)
        po = sum(1 for a, b in zip(pa, pb) if a == b) / n
        pe = sum((pa.count(c) / n) * (pb.count(c) / n) for c in cats)
        return (po - pe) / (1 - pe) if pe < 1 else 0.0

    kappas = []
    for fa, fb in combinations(qualified, 2):
        pa = [_pair_votes(fa, p, raw)["prefer"] for p in pids
              if _pair_votes(fa, p, raw) is not None
              and _pair_votes(fb, p, raw) is not None]
        pb = [_pair_votes(fb, p, raw)["prefer"] for p in pids
              if _pair_votes(fa, p, raw) is not None
              and _pair_votes(fb, p, raw) is not None]
        if pa:
            kappas.append((f"{fa}:{fb}", round(kappa(pa, pb), 3)))
    kappa_mean = (round(sum(k for _, k in kappas) / len(kappas), 3)
                  if kappas else 0.0)

    # ---- 3. AUC on the gold specimens (novelty, GOOD > BAD) ----
    gold = json.loads(subprocess.run(
        ["git", "show",
         "60657db7d:audit/gold_set/AUDITOR_GOLD_SET_v1.json"],
        capture_output=True, text=True, check=True).stdout)
    nov = {}
    for s in gold["specimens"]:
        pid = Path(s["path"]).stem
        arm = s.get("arm", "a1")
        vals = []
        for fam in qualified:
            v = _pair_votes(fam, pid, raw)
            if v and v["novelty"].get(arm) is not None:
                vals.append(v["novelty"][arm])
        if vals:
            nov[s["id"]] = {"label": s["label"], "pid": pid,
                            "arm": arm, "vals": vals,
                            "mean": round(sum(vals) / len(vals), 3)}
    goods = [v["mean"] for v in nov.values() if v["label"] == "GOOD"]
    bads = [v["mean"] for v in nov.values() if v["label"] == "BAD"]
    if goods and bads:
        u = (sum(1 for g in goods for b in bads if g > b)
             + 0.5 * sum(1 for g in goods for b in bads if g == b))
        auc = round(u / (len(goods) * len(bads)), 3)
    else:
        auc = None

    gate = {
        "record": "R132_PANEL_CALIBRATION/1.0.1 (amendment 1 protocol)",
        "claim": "c-0211", "at": "2026-11-23 (sandbox clock)",
        "method": ("independent recompute from raw per-leg records only "
                   "(auditor Art. 13); every leg carries its own order + "
                   "a_is, the tally unswaps from the record; per judge x "
                   "pair the vote = majority of the two order-passes "
                   "(det + mirror), a split = tie"),
        "judges": judges, "qualified_panel": qualified,
        "panel_agreement_vs_auditor": round(agreement, 3),
        "panel_agreement_n": len(per_pair),
        "pairwise_kappa_prefer": kappas, "kappa_mean": kappa_mean,
        "gold_auc": {"per_specimen": nov, "auc_good_gt_bad": auc,
                     "n_good": len(goods), "n_bad": len(bads)},
        "gate": {
            "n_qualified": len(qualified),
            "agreement_ge_0.7": bool(agreement >= 0.7) if per_pair else None,
            "kappa_ge_0.6": bool(kappa_mean >= 0.6) if kappas else None,
            "auc_ge_0.8": bool(auc is not None and auc >= 0.8),
        },
        "generator_family_excluded": GEN_FAMILY,
        "per_pair": per_pair,
        "disclosure": ("pass-1 (11 legs, fixed order) is archived at "
                       "eval/r132_panel_pass1_fixedorder/ and EXCLUDED "
                       "from every tally — it was run before the "
                       "protocol defect was caught; the prereg "
                       "amendment 1 discloses the correction"),
    }
    OUT.write_text(json.dumps(gate, indent=1) + "\n")
    print(json.dumps({k: gate[k] for k in
                      ("judges", "qualified_panel",
                       "panel_agreement_vs_auditor", "kappa_mean",
                       "gold_auc", "gate")}, indent=1)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
