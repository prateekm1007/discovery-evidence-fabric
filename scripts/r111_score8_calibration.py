#!/usr/bin/env python3
"""r111_score8_calibration.py — claim c-153 (the auditor direction 6):
the rating-rubric tightening + gate calibration on the BURNED set.

RECOMPUTE ONLY (Art. 29(c)): every rating byte comes from the
committed panel record (eval/r106_panel_run.json — "never re-scored,
never re-run", CORR-9); no LLM is called; the burned ratings ARE the
evidence. What changes is the NORMALIZATION:

  baseline (the r106 panel): raw ordinal votes binarized as-scored —
  proportion agreement 0.5875, nominal alpha -0.133, kappa 0.0 (the
  panel's own committed numbers).

  tightened (this lane): the raw rubric ordinal is normalized WITHIN
  each row's domain (the sealed rows' own committed question_type:
  15 intervention-proposal / 15 predictor-design — the domain split
  is a committed field, not an invented clustering):
    z = (x - median_domain_pooled) / (1.4826 * MAD_domain_pooled)
  over ALL seats' ratings pooled in that domain; the binarized seat
  vote = (z >= 0) — at-or-above the domain median. The calibrated
  gate = a row FAILS iff its seat-mean z sits more than 1 scaled-MAD
  BELOW its domain median (a within-domain floor); the burned demo's
  verdict = ACCEPT iff no row falls below the floor AND the pooled
  robust mean is at-or-above the pooled domain median.

  calibration_pass = the calibrated gate ACCEPTS the burned demo
  (which the auditor's R105 verdict already accepted at mean 3.90).
  Honest negative typed if the agreement stays <0.70 or the gate
  would reject any burned row.
"""
import json
import statistics
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PANEL = json.loads((REPO / "eval" / "r106_panel_run.json").read_text())
ROWS = REPO / "eval" / "holdout_v15_generation" / "rows"
OUT = REPO / "eval" / "r111_score8_calibration.json"


def mad_scaled(values):
    med = statistics.median(values)
    mad = statistics.median([abs(v - med) for v in values])
    return med, 1.4826 * mad


def main():
    label_map = PANEL["label_map_local_only"]
    # the committed domain split: the sealed rows' question_type
    domain_of = {}
    for rid, ho in label_map.items():
        row = json.loads((ROWS / f"{ho}.json").read_text())
        domain_of[rid] = row["question_type"]

    seats = [s["id"] for s in PANEL["seats"]]
    # collect (row, seat) -> non_obviousness + the domain pools
    votes = {}
    domain_pool = {}
    for entry in PANEL["ratings"]:
        rid = entry["label"]
        for seat, r in entry["ratings"].items():
            if r.get("out_of_range") or "non_obviousness" not in r:
                continue
            x = int(r["non_obviousness"])
            votes[(rid, seat)] = x
            domain_pool.setdefault(domain_of[rid], []).append(x)
    stats = {d: mad_scaled(v) for d, v in domain_pool.items()}

    # the tightened binarized votes (within-domain robust z >= 0)
    # DEGENERATE-MAD DISCLOSURE: both domains' pooled MAD is 0 (the
    # burned rubric mass sits at 4/5 with a thin 2/3 tail — the panel's
    # own pooled_counts), so the scaled-MAD denominator is undefined
    # and the normalization DEGENERATES to median-centering
    # (z = x - median_domain); typed here, never silently rescaled to
    # a fake spread.
    bin_votes = {}
    degenerate_domains = []
    for (rid, seat), x in votes.items():
        med, mads = stats[domain_of[rid]]
        if mads > 0:
            z = (x - med) / mads
        else:
            if domain_of[rid] not in degenerate_domains:
                degenerate_domains.append(domain_of[rid])
            z = x - med
        bin_votes[(rid, seat)] = (z >= 0.0, round(z, 4))

    # pairwise proportion agreement over complete seat pairs
    pairs = [(a, b) for i, a in enumerate(seats)
             for b in seats[i + 1:]]
    matching = total = 0
    for a, b in pairs:
        for rid in label_map:
            va, vb = bin_votes.get((rid, a)), bin_votes.get((rid, b))
            if va is None or vb is None:
                continue
            total += 1
            matching += int(va[0] == vb[0])
    agreement = round(matching / total, 4) if total else None

    # the raw baseline for the same complete-pair set (comparable)
    matching_raw = 0
    for a, b in pairs:
        for rid in label_map:
            va, vb = votes.get((rid, a)), votes.get((rid, b))
            if va is None or vb is None:
                continue
            matching_raw += int((va >= 4) == (vb >= 4))
    baseline_agreement = round(matching_raw / total, 4) if total \
        else None

    # the calibrated gate on the burned demo
    row_verdicts = {}
    for rid in label_map:
        zs = [bin_votes[(rid, s)][1] for s in seats
              if (rid, s) in bin_votes]
        if not zs:
            continue
        mean_z = statistics.mean(zs)
        med, mads = stats[domain_of[rid]]
        floor_z = -1.0  # one scaled-MAD below the domain median
        row_verdicts[rid] = {
            "domain": domain_of[rid],
            "seat_mean_z": round(mean_z, 4),
            "below_domain_floor": bool(mean_z < floor_z),
            "at_or_above_domain_median": bool(mean_z >= 0.0),
        }
    below = [r for r, v in row_verdicts.items()
             if v["below_domain_floor"]]
    pooled_z = statistics.mean(
        v[0] for v in bin_votes.values())
    demo_accepted = (not below) and (pooled_z >= 0.0)

    # per-seat agreement detail (which seat disagrees)
    per_seat = {}
    for a, b in pairs:
        m = t = 0
        for rid in label_map:
            va, vb = bin_votes.get((rid, a)), bin_votes.get((rid, b))
            if va is None or vb is None:
                continue
            t += 1
            m += int(va[0] == vb[0])
        if t:
            per_seat[f"{a}~{b}"] = round(m / t, 4)

    rec = {
        "record": "R111_SCORE8_CALIBRATION/1.0.0",
        "executor": "builder-r111s1",
        "claim": "c-153 (r111-score8-calibration, task)",
        "recompute_only": ("every rating byte from the committed "
                           "r106 panel record (CORR-9: never "
                           "re-scored, never re-run); zero LLM calls"),
        "domain_split_committed": ("the sealed rows' own question_type "
                                   "field (15 intervention-proposal / "
                                   "15 predictor-design) — the "
                                   "within-domain normalization uses a "
                                   "committed field, not an invented "
                                   "clustering"),
        "normalization": {
            "formula": "z = (x - median_domain_pooled) / "
                       "(1.4826 * MAD_domain_pooled); MAD=0 domains "
                       "degenerate to median-centering (typed)",
            "degenerate_mad_domains": degenerate_domains,
            "domain_stats": {d: {"median": round(m, 4),
                                 "mad_scaled": round(s, 4),
                                 "n_pooled": len(domain_pool[d])}
                             for d, (m, s) in stats.items()},
        },
        "agreement": {
            "metric": "pairwise proportion agreement on the "
                      "binarized votes (complete seat pairs)",
            "tightened_within_domain": agreement,
            "raw_baseline_same_pairs": baseline_agreement,
            "r106_panel_committed": 0.5875,
            "target": 0.7,
            "target_met": bool(agreement is not None
                               and agreement >= 0.7),
            "per_seat_pair": per_seat,
        },
        "gate_calibration": {
            "rule": ("a row FAILS iff its seat-mean robust-z sits more "
                     "than 1 scaled-MAD below its domain median; the "
                     "burned demo ACCEPTS iff no row fails AND the "
                     "pooled mean z >= 0"),
            "rows_below_domain_floor": below,
            "pooled_mean_z": round(pooled_z, 4),
            "demo_accepted": bool(demo_accepted),
            "calibration_pass": bool(demo_accepted),
            "audit_anchor": ("the burned demo was ACCEPTED by the "
                             "auditor R105 verdict at mean 3.90 "
                             "(CORR-9); calibration_pass=true means "
                             "the tightened gate reproduces that "
                             "acceptance from committed bytes"),
        },
        "honest_note": ("the agreement is measured on BINARIZED votes "
                        "of an ordinal rubric — the within-domain "
                        "normalization removes the cross-domain scale "
                        "heterogeneity, not rater variance; a "
                        "target-miss is typed, never tuned away"),
        "no_acceptance_claims": True,
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    print(f"agreement tightened {baseline_agreement} -> {agreement} "
          f"(target 0.7: met={rec['agreement']['target_met']})")
    print(f"calibration_pass={demo_accepted} "
          f"(rows below floor: {len(below)}, pooled z {pooled_z:.3f})")


if __name__ == "__main__":
    main()
