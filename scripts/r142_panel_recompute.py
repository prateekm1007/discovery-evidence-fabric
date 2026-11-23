#!/usr/bin/env python3
"""r142_panel_recompute — the DIR-2 independent verifier (Art. 29c /
R137 F31F convention): FULLY INDEPENDENT arithmetic, zero import of
the runner's tally or the engine's agreement instruments.

Recomputes from the RAW leg bytes (eval/r142_panel/*.json):
  - per-judge vote decoding (the parity-drawn det leg votes; the mir
    leg only discloses swap stability),
  - per-judge acc vs the auditor's overall_preference labels,
  - the answered rate on the EXPECTED denominator (24 legs),
  - the qualified set (acc>=0.8 AND answered>=0.9),
  - the panel majority per pair + proportion agreement,
  - pairwise Cohen's kappa + Krippendorff alpha (nominal, the
    independent implementation),
  - the gold-set AUC (Mann-Whitney U over the panel mean novelty,
    GOOD > BAD),
and diffs every shared field against the committed qualification
record (eval/r142_panel_qualification.json) — diff=0 required.
"""
import hashlib
import itertools
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "r142_panel"
AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
CORPUS_PATH = "eval/auditor_rcal_corpus_r142.json"
TAGS = ["dsr1", "qw32b", "qwen235b", "dsv32", "hy4f"]


def blind_order(pid: str) -> str:
    h = hashlib.sha256(f"{pid}::pair".encode()).hexdigest()
    return "a1_first" if int(h, 16) % 2 == 0 else "base_first"


def krippendorff_alpha_nominal(units):
    """Independent Krippendorff's alpha (nominal): alpha = 1 -
    D_o / D_e over the scored units (judges x items with complete
    coverage on the voted legs)."""
    scored = [u for u in units if len(u) >= 2]
    if not scored:
        return None
    n_pairs, n_diff = 0, 0
    vals = set()
    for u in scored:
        for a, b in itertools.combinations(u, 2):
            n_pairs += 1
            if a != b:
                n_diff += 1
        vals.update(u)
    if n_pairs == 0:
        return None
    D_o = n_diff / n_pairs
    # D_e: the chance disagreement under the observed distribution
    counts = {}
    n = sum(len(u) for u in scored)
    for u in scored:
        for v in u:
            counts[v] = counts.get(v, 0) + 1
    D_e = 0.0
    tot = sum(c * (n - c) for c in counts.values())
    for u in scored:
        m = len(u)
        if m < 2:
            continue
        D_e += (m / (m - 1)) * (tot / (n * (n - 1)))
    D_e = D_e / len(scored) if scored else None
    if not D_e:
        return None
    return round(1.0 - D_o / D_e, 3)


def mannwhitney_auc(goods, bads):
    """Independent AUC = U / (n_good * n_bad) with ties 0.5."""
    if not goods or not bads:
        return None
    wins = ties = 0
    for g in goods:
        for b in bads:
            if g > b:
                wins += 1
            elif g == b:
                ties += 1
    return round((wins + 0.5 * ties) / (len(goods) * len(bads)), 3)


def main() -> int:
    corpus = json.loads(__import__("subprocess").run(
        ["git", "show", f"{AUDIT_REF}:{CORPUS_PATH}"],
        capture_output=True, text=True, check=True).stdout)
    labels = {p["problem_id"]: p["overall_preference"]
              for p in corpus["pairs"]}
    pids = sorted(labels)
    expected_legs = 2 * len(pids)

    votes, mirrors, n_valid = {}, {}, {}
    for tag in TAGS:
        votes[tag], mirrors[tag] = {}, {}
        n_valid[tag] = 0
        for pid in pids:
            for order in ("det", "mir"):
                lf = OUT / f"{tag}__{pid}__{order}.json"
                if not lf.exists():
                    continue
                r = json.loads(lf.read_text())
                if r["outcome"] != "VALID":
                    continue
                n_valid[tag] += 1
                pref = (r.get("parsed") or {}).get("prefer")
                if pref not in ("A", "B"):
                    continue
                pick = (r["a_is"] if pref == "A"
                        else ("baseline" if r["a_is"] == "a1"
                              else "a1"))
                if order == "det":
                    votes[tag][pid] = pick
                else:
                    mirrors[tag][pid] = pick

    qual = {}
    for tag in TAGS:
        hits = sum(1 for pid, v in votes[tag].items()
                   if labels.get(pid) == v)
        n_cmp = len(votes[tag])
        inst = sum(1 for pid, v in votes[tag].items()
                   if mirrors[tag].get(pid, v) != v)
        qual[tag] = {
            "acc": round(hits / n_cmp, 3) if n_cmp else 0.0,
            "answered": round(n_valid[tag] / expected_legs, 3),
            "swap_instability": (round(inst / n_cmp, 3)
                                 if n_cmp else None),
            "qualified": (hits / n_cmp >= 0.8
                          and n_valid[tag] / expected_legs >= 0.9
                          and n_cmp > 0)}
    qualified = [t for t in TAGS if qual[t]["qualified"]]

    # the panel majority over the qualified judges' votes
    per_pair, hits, n_scored = {}, 0, 0
    panel_mean_novelty = {"GOOD": [], "BAD": []}
    for pid in pids:
        prefs = [votes[t][pid] for t in qualified
                 if pid in votes[t]]
        if not prefs:
            continue
        counts = {}
        for x in prefs:
            counts[x] = counts.get(x, 0) + 1
        top = max(counts.values())
        winners = sorted(k for k, v in counts.items() if v == top)
        maj = winners[0] if len(winners) == 1 else "split"
        lab = labels[pid]
        match = maj == lab
        n_scored += 1
        hits += 1 if match else 0
        per_pair[pid] = {"majority": maj, "label": lab,
                         "match": match, "votes": prefs}
    agreement = round(hits / n_scored, 3) if n_scored else None

    # pairwise kappa over the qualified judges' shared votes
    kappas = []
    for a, b in itertools.combinations(qualified, 2):
        shared = sorted(set(votes[a]) & set(votes[b]))
        if len(shared) < 2:
            continue
        xs = [votes[a][p] for p in shared]
        ys = [votes[b][p] for p in shared]
        n = len(xs)
        po = sum(1 for x, y in zip(xs, ys) if x == y) / n
        pe = sum(
            (sum(1 for x in xs if x == c) / n)
            * (sum(1 for y in ys if y == c) / n)
            for c in set(xs) | set(ys))
        k = round((po - pe) / (1 - pe), 3) if pe < 1 else None
        kappas.append({"pair": f"{a}:{b}", "kappa": k})
    kappa_vals = [k["kappa"] for k in kappas if k["kappa"] is not None]
    kappa_mean = (round(sum(kappa_vals) / len(kappa_vals), 3)
                  if kappa_vals else None)

    # Krippendorff alpha over the qualified judges' votes per item
    units = [[votes[t][pid] for t in qualified if pid in votes[t]]
             for pid in pids]
    alpha = krippendorff_alpha_nominal(units)

    # the AUC: panel mean novelty per specimen (the det leg's N_<arm>)
    gold_goods, gold_bads = [], []
    for p in corpus["pairs"]:
        pid = p["problem_id"]
        det_a_is = "a1" if blind_order(pid) == "a1_first" else "baseline"
        lab = labels[pid]
        for arm_name, corpus_arm in (
                ("A", det_a_is),
                ("B", "baseline" if det_a_is == "a1" else "a1")):
            vals = []
            for t in qualified:
                lf = OUT / f"{t}__{pid}__det.json"
                if not lf.exists():
                    continue
                r = json.loads(lf.read_text())
                v = (r.get("parsed") or {}).get("axes", {}).get(
                    f"N_{arm_name}")
                if v is not None:
                    vals.append(v)
            if not vals:
                continue
            mean = sum(vals) / len(vals)
            (gold_goods if corpus_arm == lab else gold_bads).append(mean)
    auc = mannwhitney_auc(gold_goods, gold_bads)

    rec = {
        "record": "R142_PANEL_RECOMPUTE_INDEPENDENT/1.0.0",
        "claim": "c-0227",
        "at": "2026-11-23 (sandbox clock)",
        "independence": ("zero import of the runner's tally or the "
                         "engine's agreement instruments — every "
                         "statistic recomputed from the RAW leg bytes "
                         "(own kappa, own alpha, own Mann-Whitney AUC)"),
        "per_judge": qual,
        "qualified_tags": qualified,
        "panel": {"n_scored": n_scored, "agreement": agreement,
                  "kappa_mean": kappa_mean, "kappas": kappas,
                  "alpha": alpha, "auc": auc,
                  "per_pair": per_pair},
        "gates": {
            "ge3_qualified": len(qualified) >= 3,
            "families": sorted({t for t in qualified}),
            "agreement_ge_0.7":
                agreement is not None and agreement >= 0.7,
            "alpha_ge_0.6": alpha is not None and alpha >= 0.6,
            "auc_ge_0.8": auc is not None and auc >= 0.8},
    }
    (REPO / "eval" / "r142_panel_recompute_independent.json").write_text(
        json.dumps(rec, indent=1, ensure_ascii=False) + "\n")

    # diff vs the committed qualification record
    diff = []
    qf = REPO / "eval" / "r142_panel_qualification.json"
    if qf.exists():
        committed = json.loads(qf.read_text())
        for tag, q in qual.items():
            cq = (committed.get("qualification") or {}).get(
                "qwen:" + tag) or (committed.get("qualification") or {}).get(
                "deepseek:" + tag) or (committed.get("qualification")
                                       or {}).get("cent-ai:" + tag)
            if not cq:
                continue
            if abs(cq.get("acc_vs_labels", -1) - q["acc"]) > 1e-9:
                diff.append(f"{tag}: acc {cq.get('acc_vs_labels')} != "
                            f"{q['acc']}")
            if abs(cq.get("answered_rate", -1) - q["answered"]) > 1e-9:
                diff.append(f"{tag}: answered "
                            f"{cq.get('answered_rate')} != {q['answered']}")
        cg = committed.get("gates") or {}
        cp = committed.get("panel") or {}
        for name, mine, theirs in (
                ("panel_agreement", agreement,
                 cp.get("panel_agreement")),
                ("kappa_mean", kappa_mean, cp.get("kappa_mean")),
                ("auc", auc, cp.get("auc"))):
            if theirs is not None and mine is not None:
                if abs(theirs - mine) > 1e-9:
                    diff.append(f"{name}: committed {theirs} != "
                                f"independent {mine}")
    rec["diff_vs_committed"] = diff
    (REPO / "eval" / "r142_panel_recompute_independent.json").write_text(
        json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(rec["gates"], indent=1))
    print("qualified:", qualified)
    print("panel:", json.dumps({k: rec["panel"][k] for k in
                                ("agreement", "kappa_mean", "alpha",
                                 "auc")}))
    print("diff_vs_committed:", diff or "NONE (diff=0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
