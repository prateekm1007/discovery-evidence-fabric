"""discovery_fabric/engine/panel_agreement.py — the AGREEMENT METRICS
for the blind cross-family panel and the panel-vs-gate cross-check
as ENGINE code (the F63 rule: capability logic lives in the engine,
not scripts/).

Lineage (forward-only, Art. 16 accounting):
  - the AM85 P4 gate clause ("agreement >=0.7 (alpha>=0.6)") and the
    AM87 score-8 widening — until this module the metrics existed
    only as chat contracts / would-be script math; THIS MODULE is
    the engine landing consumed by the r106 score-8 execution lane
    (claim c-0124) and by every future sealed-set panel run.
  - metrics implemented EXACTLY as named in the pre-registration
    (eval/r106_score8_prereg.json, committed BEFORE any rating byte):
    nominal Krippendorff alpha, interval Krippendorff alpha, pairwise
    proportion agreement, Cohen's kappa, Spearman rho (tie-corrected),
    and the composed panel-vs-gate cross-check with the preregistered
    consensus mapping.

DEFINITIONS (canonical "coincidence" formulation, Krippendorff 2011):
  alpha = 1 - D_o / D_e
  D_o   = sum_u sum_{i!=j in u} delta(v_ui, v_uj) / sum_u k_u (k_u - 1)
  D_e   = sum_c sum_c' n_c n_c' delta(c, c') / (n' (n' - 1))
  where u ranges over PAIRABLE units (k_u >= 2 non-missing values),
  k_u is the unit's value count, n_c the pooled value counts and
  n' = sum_c n_c. Nominal delta = 0|1; interval delta = (v1 - v2)^2
  (values must be numeric for the interval metric). Missing values
  (None) drop out of every statistic — a seat that errored on a row
  is missing, never zero (the typed-error disclosure lives in the
  panel record, not here).

All functions are pure, deterministic, zero-network, zero-LLM; the
records serialize sorted (canonical_json convention). CI uses
hand-computed fixtures (Art. 22: fixtures prove mechanics only).
"""
from __future__ import annotations

import itertools
import json
import math
from typing import Callable, Optional, Sequence

# The preregistered consensus mapping constants (byte-identical to
# eval/r106_score8_prereg.json — pinned by CI against those bytes).
CONSENSUS_NO_MIN = 4          # median non_obviousness >= 4
CONSENSUS_KNOWN_MAJORITY = False   # majority recognizes_known_practice == False


# ---------------------------------------------------------------------------
# Krippendorff alpha (nominal + interval), missing-value aware
# ---------------------------------------------------------------------------
def _delta(v1, v2, metric: str) -> float:
    if v1 == v2:
        return 0.0
    if metric == "nominal":
        return 1.0
    if metric == "interval":
        return float((v1 - v2) ** 2)
    raise ValueError(
        f"unknown metric {metric!r} (typed refusal — nominal|interval)")


def krippendorff_alpha(units: Sequence[Sequence],
                       metric: str = "nominal") -> dict:
    """Krippendorff's alpha over `units` (one unit per row; each unit
    is the raters' values, None = missing). Returns the alpha, the
    observed/expected disagreement, the pairable-unit census and the
    pooled value counts — every component disclosed (Art. 9).

    alpha = 1 - D_o/D_e; a degenerate input (no pairable unit, or a
    single distinct pooled value with zero expected disagreement)
    returns alpha=None with the typed degenerate_class disclosed —
    never a silent 1.0 or 0.0.
    """
    if metric not in ("nominal", "interval"):
        raise ValueError(
            f"unknown metric {metric!r} (typed refusal — nominal|interval)")
    pairable = []
    for u in units:
        vals = [v for v in u if v is not None]
        if len(vals) >= 2:
            pairable.append(vals)
    if not pairable:
        return {"alpha": None, "degenerate_class": "no_pairable_units",
                "n_units_input": len(units), "n_pairable": 0}
    pooled = [v for vals in pairable for v in vals]
    n_total = len(pooled)
    if n_total < 2:
        return {"alpha": None, "degenerate_class": "pooled_below_two",
                "n_units_input": len(units), "n_pairable": len(pairable)}

    # observed disagreement (pairs within units)
    num_o = 0.0
    den_o = 0
    for vals in pairable:
        k = len(vals)
        den_o += k * (k - 1)
        for a, b in itertools.permutations(vals, 2):
            num_o += _delta(a, b, metric)
    d_o = num_o / den_o if den_o else 0.0

    # expected disagreement (pairs drawn from the pooled distribution)
    counts: dict = {}
    for v in pooled:
        counts[v] = counts.get(v, 0) + 1
    num_e = 0.0
    for c1, c2 in itertools.permutations(sorted(counts), 2):
        num_e += counts[c1] * counts[c2] * _delta(c1, c2, metric)
    d_e = num_e / (n_total * (n_total - 1)) if n_total > 1 else 0.0

    if d_e == 0.0:
        return {"alpha": None, "degenerate_class": "zero_expected_disagreement",
                "n_units_input": len(units), "n_pairable": len(pairable),
                "d_o": round(d_o, 6), "d_e": 0.0,
                "pooled_counts": {str(k): v for k, v in sorted(
                    counts.items(), key=lambda kv: str(kv[0]))}}
    alpha = 1.0 - d_o / d_e
    return {
        "alpha": round(alpha, 6),
        "metric": metric,
        "degenerate_class": None,
        "n_units_input": len(units),
        "n_pairable": len(pairable),
        "d_o": round(d_o, 6),
        "d_e": round(d_e, 6),
        "pooled_counts": {str(k): v for k, v in sorted(
            counts.items(), key=lambda kv: str(kv[0]))},
    }


# ---------------------------------------------------------------------------
# Pairwise proportion agreement (co-rated units only)
# ---------------------------------------------------------------------------
def proportion_agreement(units: Sequence[Sequence]) -> dict:
    """Mean pairwise agreement over co-rated units: for every pairable
    unit and every rater pair within it, the fraction of equal values.
    Returns the proportion, the census and the match/total pair counts."""
    matches = 0
    total = 0
    for u in units:
        vals = [v for v in u if v is not None]
        for a, b in itertools.combinations(vals, 2):
            total += 1
            if a == b:
                matches += 1
    if total == 0:
        return {"proportion": None, "degenerate_class": "no_co_rated_pairs",
                "matching_pairs": 0, "total_pairs": 0}
    return {"proportion": round(matches / total, 6),
            "matching_pairs": matches, "total_pairs": total}


# ---------------------------------------------------------------------------
# Cohen's kappa (binary/ordinal, complete pairs only)
# ---------------------------------------------------------------------------
def cohen_kappa(xs: Sequence, ys: Sequence) -> dict:
    """Cohen's kappa over COMPLETE pairs (a row missing one value is
    dropped, disclosed). Returns kappa + the 2x2/nclass confusion
    matrix components — every input to the number disclosed."""
    if len(xs) != len(ys):
        raise ValueError("length mismatch (typed refusal)")
    pairs = [(x, y) for x, y in zip(xs, ys)
             if x is not None and y is not None]
    n = len(pairs)
    if n == 0:
        return {"kappa": None, "degenerate_class": "no_complete_pairs",
                "n_complete": 0}
    labels = sorted({str(v) for p in pairs for v in p})
    obs = sum(1 for x, y in pairs if x == y) / n
    counts_x: dict = {}
    counts_y: dict = {}
    for x, y in pairs:
        counts_x[str(x)] = counts_x.get(str(x), 0) + 1
        counts_y[str(y)] = counts_y.get(str(y), 0) + 1
    exp = sum((counts_x.get(l, 0) / n) * (counts_y.get(l, 0) / n)
              for l in labels)
    kappa = None if exp == 1.0 else (obs - exp) / (1 - exp)
    return {"kappa": None if kappa is None else round(kappa, 6),
            "observed_agreement": round(obs, 6),
            "expected_agreement": round(exp, 6),
            "n_complete": n,
            "labels": labels,
            "degenerate_class": None if kappa is not None
                else "one_label_only"}


# ---------------------------------------------------------------------------
# Spearman rho (tie-corrected rank correlation)
# ---------------------------------------------------------------------------
def _ranks(vals: Sequence[float]) -> list:
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman_rho(xs: Sequence[float], ys: Sequence[float]) -> dict:
    """Tie-corrected Spearman rho over COMPLETE pairs (Pearson on the
    rank vectors — the tie-handling convention disclosed; a
    zero-variance side returns rho=None typed, never a silent 0)."""
    if len(xs) != len(ys):
        raise ValueError("length mismatch (typed refusal)")
    pairs = [(x, y) for x, y in zip(xs, ys)
             if x is not None and y is not None]
    if len(pairs) < 2:
        return {"rho": None, "degenerate_class": "below_two_complete_pairs",
                "n_complete": len(pairs)}
    rx = _ranks([p[0] for p in pairs])
    ry = _ranks([p[1] for p in pairs])
    mx = sum(rx) / len(rx)
    my = sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx)
    vy = sum((b - my) ** 2 for b in ry)
    if vx == 0 or vy == 0:
        return {"rho": None, "degenerate_class": "zero_variance_side",
                "n_complete": len(pairs)}
    rho = cov / math.sqrt(vx * vy)
    return {"rho": round(rho, 6), "n_complete": len(pairs)}


# ---------------------------------------------------------------------------
# The preregistered consensus mapping (panel side)
# ---------------------------------------------------------------------------
def consensus_novel(ratings: Sequence[dict],
                    no_min: int = CONSENSUS_NO_MIN,
                    known_majority: bool = CONSENSUS_KNOWN_MAJORITY,
                    ) -> dict:
    """The preregistered panel->novel mapping applied to ONE row's
    served ratings (each a blind_panel Rating.as_dict() shape):
      panel_novel := (median non_obviousness >= no_min) AND
                     (majority recognizes_known_practice ==
                      known_majority)
    Missing ratings (the typed per-seat errors) drop out; a row with
    zero served ratings is consensus=None (never guessed). The
    components and the sensitivity rows (each conjunct alone) are
    returned so the auditor can read the mapping's pieces, not just
    the conjunction."""
    served = [r for r in ratings if isinstance(r, dict)
              and "error" not in r
              and isinstance(r.get("non_obviousness"), int)]
    if not served:
        return {"consensus_novel": None,
                "degenerate_class": "no_served_ratings",
                "n_served": 0}
    nos = sorted(r["non_obviousness"] for r in served)
    m = len(nos)
    med = (nos[m // 2] if m % 2 else (nos[m // 2 - 1] + nos[m // 2]) / 2)
    known = [bool(r.get("recognizes_known_practice")) for r in served]
    known_maj = sum(known) * 2 > len(known)
    no_ok = med >= no_min
    known_ok = (known_maj == known_majority)
    return {
        "consensus_novel": bool(no_ok and known_ok),
        "median_non_obviousness": med,
        "n_served": m,
        "known_majority": known_maj,
        "component_no_alone": no_ok,
        "component_known_alone": known_ok,
        "no_min": no_min,
        "known_majority_target": known_majority,
    }


# ---------------------------------------------------------------------------
# The composed panel-vs-gate cross-check
# ---------------------------------------------------------------------------
def panel_gate_agreement(panel_row_ratings: dict,
                         gate_verdicts: dict,
                         no_min: int = CONSENSUS_NO_MIN,
                         known_majority: bool = CONSENSUS_KNOWN_MAJORITY,
                         ) -> dict:
    """The two-instrument cross-check over the SHARED rows.
    panel_row_ratings: {row_id: [rating_dict, ...]}; gate_verdicts:
    {row_id: bool} (the anchor-relative gate's novel verdict). Rows
    absent from either side are typed EXCLUDED (shared-census
    disclosure). Returns the consensus mapping per row, the confusion
    matrix, proportion agreement, Cohen's kappa, and the continuous
    corroboration (Spearman rho between the panel's median
    non_obviousness and the gate's core-mechanism distance — the
    direction typed: BOTH increase with novelty).
    """
    shared = sorted(set(panel_row_ratings) & set(gate_verdicts))
    excluded_panel_only = sorted(set(panel_row_ratings)
                                 - set(gate_verdicts))
    excluded_gate_only = sorted(set(gate_verdicts)
                                - set(panel_row_ratings))
    consensus = {}
    p_flags, g_flags = [], []
    medians, distances = [], []
    tp = fp = tn = fn = 0
    for rid in shared:
        c = consensus_novel(panel_row_ratings[rid], no_min,
                            known_majority)
        consensus[rid] = c
        g = bool(gate_verdicts[rid])
        if c["consensus_novel"] is None:
            continue
        p = c["consensus_novel"]
        p_flags.append(p)
        g_flags.append(g)
        medians.append(c["median_non_obviousness"])
        distances.append(gate_verdicts[rid + "__dist"]
                         if rid + "__dist" in gate_verdicts else None)
        if p and g:
            tp += 1
        elif p and not g:
            fp += 1
        elif not p and g:
            fn += 1
        else:
            tn += 1
    total = tp + fp + tn + fn
    prop = (round((tp + tn) / total, 6) if total else None)
    kap = cohen_kappa(p_flags, g_flags)
    rho = spearman_rho(medians, distances)
    return {
        "n_shared": len(shared),
        "shared_row_ids": shared,
        "excluded_panel_only": excluded_panel_only,
        "excluded_gate_only": excluded_gate_only,
        "n_scored_pairs": total,
        "confusion": {"true_positive": tp, "false_positive": fp,
                      "false_negative": fn, "true_negative": tn},
        "proportion_agreement": prop,
        "cohens_kappa": {k: v for k, v in kap.items()},
        "spearman_rho": {k: v for k, v in rho.items()},
        "consensus_mapping": consensus,
        "no_min": no_min,
        "known_majority_target": known_majority,
        "rho_direction_typed": "both axes increase with novelty "
                               "(median non_obviousness and the "
                               "core-mechanism distance)",
    }


def canonical_json(record: dict) -> str:
    """Sorted-key, no-wall-clock serialization (the shared Art. 15 /
    F64 determinism convention)."""
    return json.dumps(record, indent=1, ensure_ascii=False,
                      sort_keys=True)


# ---------------------------------------------------------------------------
# The R-CAL + swap-robust panel qualification tally (R133 DIR-2 —
# engine code; the R132-F1 fix). All functions pure/deterministic.
# ---------------------------------------------------------------------------
def rcal_qualification(judge_rows: dict,
                       labels: dict,
                       acc_bar: float = 0.8,
                       answered_bar: float = 0.9,
                       expected_legs: int = None) -> dict:
    """Per-judge R-CAL qualification from raw per-leg records.

    judge_rows: {family: [{pid, order, pass, a_is, outcome, parsed},
    ...]} — the raw legs, BOTH orders (det + mir). The VOTING leg is
    the r9 parity-drawn order ('det'); the mirror leg ('mir') is a
    consistency check, never a vote-splitter (the R133 lever (a)).

    labels: {pid: 'a1'|'baseline'} — the auditor's forced-choice
    ground truth (ties impossible; a tie-labeled corpus raises).

    expected_legs: the R136 fix — the answered-rate denominator is
    the EXPECTED leg count (n_pairs x 2), never the legs-present
    count. A judge whose legs are MISSING on disk can now FAIL the
    answered bar (the verifier's finding: the legs-present
    denominator made the bar unfailable by omission). None = infer
    per judge as 2 x (the distinct pids seen across the WHOLE
    judge_rows — a partial run is penalized because every other
    judge's pids count toward the expectation); an explicit int
    pins it.

    Returns per-judge: legs, valid, expected, answered_rate, acc
    (exact match on the parity-drawn vote), swap_instability (the
    mirror-order disagreement rate — disclosed, NOT a vote),
    qualified flag.
    """
    out = {}
    all_pids = set()
    for legs in judge_rows.values():
        for l in legs:
            all_pids.add(l.get("pid"))
    inferred_expected = 2 * len(all_pids) if all_pids else 0
    for fam, legs in judge_rows.items():
        n = len(legs)
        expected = (expected_legs if expected_legs is not None
                    else inferred_expected)
        valid = [l for l in legs if l.get("outcome") == "VALID"]
        # the R136 denominator fix: EXPECTED legs, not legs-present
        answered = len(valid) / expected if expected else 0.0
        votes, mirrors, hits, n_cmp = {}, {}, 0, 0
        for l in valid:
            p = l.get("parsed") or {}
            pref = str(p.get("prefer") or "")
            pick = None
            if pref in ("A", "B"):
                pick = (l["a_is"] if pref == "A"
                        else ("baseline" if l["a_is"] == "a1" else "a1"))
            if pick is None:
                continue  # a VALID leg whose prefer was coerced out
            if l.get("pass") == "det":
                votes[l["pid"]] = pick
            else:
                mirrors[l["pid"]] = pick
        instability_n = 0
        for pid, v in votes.items():
            if pid in labels:
                n_cmp += 1
                if v == labels[pid]:
                    hits += 1
            if pid in mirrors and mirrors[pid] != v:
                instability_n += 1
        acc = hits / n_cmp if n_cmp else 0.0
        out[fam] = {
            "legs": n, "valid": len(valid),
            "expected_legs": expected,
            "answered_rate": round(answered, 3),
            "answered_rate_basis": "EXPECTED legs (the R136 fix; "
                                   "never legs-present)",
            "acc_vs_labels": round(acc, 3), "hits": hits,
            "n_cmp": n_cmp,
            "swap_instability": round(
                instability_n / len(votes), 3) if votes else None,
            "vote_rule": "parity-drawn order votes; mirror = "
                         "consistency check (swap_instability "
                         "disclosed, never a vote-splitter)",
            "qualified": bool(acc >= acc_bar and answered >= answered_bar),
        }
    return out


def swap_robust_panel(judge_rows: dict, qualified: Sequence,
                       labels: dict, gold_novelty: dict = None,
                       agreement_bar: float = 0.7,
                       kappa_bar: float = 0.6,
                       auc_bar: float = 0.8) -> dict:
    """The qualified-panel tally: per-pair majority vote (the
    parity-drawn per-judge votes; a split panel = the plurality
    winner, a true tie = 'split' — disclosed), panel-vs-labels
    agreement, pairwise Cohen's kappa (mean), and the gold-set AUC
    (panel mean novelty, GOOD > BAD, Mann-Whitney U).

    The R136 guard: fewer than 2 distinct qualified judges => the
    panel-agreement number is NOT COMPUTED (a single judge's
    agreement with the labels is just that judge's accuracy —
    reporting it as 'panel agreement' overstates the instrument;
    typed refusal, never a silent pass)."""
    if len(set(qualified)) < 2:
        return {
            "qualified": list(qualified),
            "panel_agreement": None,
            "n_scored": 0,
            "guard": "TYPED REFUSAL (R136): panel agreement is "
                     "undefined below 2 distinct qualified judges — "
                     "a single judge's label agreement is its own "
                     "accuracy, not a panel property",
            "agreement_ge_bar": False, "kappa_ge_bar": False,
            "auc_ge_bar": False,
        }
    fam_votes = {}
    for fam in qualified:
        fam_votes[fam] = {}
        for l in judge_rows.get(fam, []):
            if (l.get("outcome") != "VALID"
                    or l.get("pass") != "det"):
                continue
            p = l.get("parsed") or {}
            pref = str(p.get("prefer") or "")
            if pref not in ("A", "B"):
                continue
            pick = (l["a_is"] if pref == "A"
                    else ("baseline" if l["a_is"] == "a1" else "a1"))
            fam_votes[fam][l["pid"]] = pick
    pids = sorted(set().union(*[set(v) for v in fam_votes.values()])
                  if fam_votes else set())
    per_pair, agreement_hits = {}, 0
    for pid in pids:
        prefs = [fam_votes[f][pid] for f in qualified
                 if pid in fam_votes.get(f, {})]
        if not prefs:
            continue
        counts = {}
        for x in prefs:
            counts[x] = counts.get(x, 0) + 1
        top = max(counts.values())
        winners = sorted([k for k, v in counts.items() if v == top])
        maj = winners[0] if len(winners) == 1 else "split"
        lab = labels.get(pid)
        match = (maj == lab)
        if lab is not None:
            agreement_hits += 1 if match else 0
        per_pair[pid] = {"panel_majority": maj, "label": lab,
                         "match": match, "votes": prefs}
    n_scored = sum(1 for v in per_pair.values()
                   if v["label"] is not None)
    agreement = (agreement_hits / n_scored) if n_scored else 0.0
    kappas = []
    for fa, fb in itertools.combinations(sorted(qualified), 2):
        shared = sorted(set(fam_votes.get(fa, {}))
                        & set(fam_votes.get(fb, {})))
        if not shared:
            continue
        xs = [fam_votes[fa][p] for p in shared]
        ys = [fam_votes[fb][p] for p in shared]
        k = cohen_kappa(xs, ys)
        kappas.append((f"{fa}:{fb}", k.get("kappa")))
    kappa_vals = [k for _, k in kappas if k is not None]
    kappa_mean = (round(sum(kappa_vals) / len(kappa_vals), 3)
                  if kappa_vals else None)
    auc = None
    gold_detail = {}
    if gold_novelty:
        # gold_novelty: {specimen_id: {pid, arm, label}}; novelty per
        # specimen = mean over qualified judges of the parity-drawn
        # leg's N_<arm> axis
        goods, bads = [], []
        for sid, g in sorted(gold_novelty.items()):
            vals = []
            for fam in qualified:
                for l in judge_rows.get(fam, []):
                    if (l.get("outcome") == "VALID"
                            and l.get("pass") == "det"
                            and l["pid"] == g["pid"]):
                        v = (l.get("parsed") or {}).get(
                            "axes", {}).get(f"N_{g['arm']}")
                        if v is not None:
                            vals.append(v)
            if not vals:
                continue
            mean = round(sum(vals) / len(vals), 3)
            gold_detail[sid] = {"label": g["label"], "mean": mean,
                                "vals": vals}
            (goods if g["label"] == "GOOD" else bads).append(mean)
        if goods and bads:
            u = (sum(1 for g in goods for b in bads if g > b)
                 + 0.5 * sum(1 for g in goods for b in bads
                             if g == b))
            auc = round(u / (len(goods) * len(bads)), 3)
    return {
        "qualified": list(qualified),
        "panel_agreement": round(agreement, 3), "n_scored": n_scored,
        "pairwise_kappa": kappas, "kappa_mean": kappa_mean,
        "gold_auc": {"per_specimen": gold_detail,
                     "auc_good_gt_bad": auc,
                     "n_good": len(gold_detail) and sum(
                         1 for v in gold_detail.values()
                         if v["label"] == "GOOD"),
                     "n_bad": len(gold_detail) and sum(
                         1 for v in gold_detail.values()
                         if v["label"] == "BAD")},
        "gate": {
            "agreement_ge_bar": (agreement >= agreement_bar
                                 if n_scored else None),
            "kappa_ge_bar": (kappa_mean is not None
                             and kappa_mean >= kappa_bar),
            "auc_ge_bar": (auc is not None and auc >= auc_bar),
        },
        "per_pair": per_pair,
    }
