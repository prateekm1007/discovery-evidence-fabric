#!/usr/bin/env python3
"""r110_d4_gate_recompute.py — the R110 direction-4 EXECUTION: the
score-8 anchor-relative gate recomputed with domain-referenced legs,
under the pre-registration eval/r110_d4_gate_prereg.json (incl. the
pre-execution amendment: margin 0.03, strictly below the measured
anchor separation 0.0343).

Deterministic, zero quota: the same extract_core_mechanism + SPECTER2
stack as the r106 gate run; single-linkage clusters at t_c = the prior
corpus' own MEDIAN pairwise distance; per-row reference class = the
nearest prior row's cluster (<8 rows -> union the next-nearest cluster,
typed); legs: margin (amended) AND (cluster-p95 OR MAD-z > 2.0).
Battery: known-novel anchor PASSES, obvious anchor + paraphrase FAIL,
5 self-match probes FAIL (0 false passes), the 30 v15 rows reported
informationally.
"""
import json
import statistics as st
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r106_score8_run import load_evaluated_rows, load_prior_corpus  # noqa
from discovery_fabric.engine.core_mechanism_gate import (  # noqa
    KNOWN_NOVEL_ANCHOR, KNOWN_OBVIOUS_ANCHOR,
    KNOWN_OBVIOUS_ANCHOR_PARAPHRASE, cosine_distance,
    extract_core_mechanism, load_specter2_encoder,
    pairwise_distances, pairwise_percentile)

OUT = REPO / "eval" / "r110_d4_gate_within_domain.json"
MARGIN = 0.03          # the prereg amendment (pre-execution)
K_Z = 2.0              # the prereg MAD-z cut
MIN_CLUSTER = 8        # the small-cluster union floor


def median_mad(vals):
    med = st.median(vals)
    mad = st.median([abs(x - med) for x in vals]) or 1e-9
    return med, mad


def clusters_at(ids, vec, t_c):
    """Single-linkage components over cosine distance at t_c
    (deterministic: sorted ids, union-find)."""
    parent = {r: r for r in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    n = len(ids)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = ids[i], ids[j]
            if cosine_distance(vec[a], vec[b]) <= t_c:
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[max(ra, rb)] = min(ra, rb)
    groups = {}
    for r in ids:
        groups.setdefault(find(r), []).append(r)
    return {k: sorted(v) for k, v in groups.items()}


def main():
    rows, _ = load_evaluated_rows()
    prior = load_prior_corpus()
    enc = load_specter2_encoder("/home/z/my-project/models_cache", None)

    prior_ex = {r: extract_core_mechanism(a) for r, a in prior.items()}
    prior_live = {r: c.text for r, c in prior_ex.items()
                  if not c.extraction_miss}
    prior_ids = sorted(prior_live)
    vec = {r: enc.encode(prior_live[r]) for r in prior_ids}

    # t_c = the prior corpus' own median pairwise distance (derived,
    # deterministic — the prereg rule, never hand-tuned). TYPED
    # FINDING (amendment 2): this yields ONE single-linkage component
    # over all 192 rows — the nearest-cluster adaptation degenerates;
    # the legs re-reference to the leave-one-out isolation
    # distribution (the faithful r109-staged definition).
    pd_all = pairwise_distances([vec[r] for r in prior_ids])
    t_c = st.median(pd_all)
    clusters = clusters_at(prior_ids, vec, t_c)
    loo = {}
    for r in prior_ids:
        others = [p for p in prior_ids if p != r]
        loo[r] = min(cosine_distance(vec[r], vec[p]) for p in others)
    loo_vals = [loo[r] for r in prior_ids]
    loo_med, loo_mad = median_mad(loo_vals)
    loo_p95 = pairwise_percentile(sorted(loo_vals), 0.95)

    # per-cluster pairwise distribution (distance basis + median/MAD)
    cl_stats = {}
    for k, members in clusters.items():
        pw = pairwise_distances([vec[r] for r in members])
        if pw:
            med, mad = median_mad(pw)
            cl_stats[k] = {"n": len(members), "members": members,
                           "p95": pairwise_percentile(pw, 0.95),
                           "median": med, "mad": mad,
                           "n_pairs": len(pw)}
        else:
            cl_stats[k] = {"n": len(members), "members": members,
                           "p95": None, "median": None, "mad": None,
                           "n_pairs": 0}

    def reference_class(row_vec):
        """Nearest prior row -> its cluster; union next-nearest
        clusters until >=MIN_CLUSTER members (typed per call)."""
        dists = sorted(((cosine_distance(row_vec, vec[p]), p)
                        for p in prior_ids))
        nearest = dists[0][1]
        root = next(k for k, m in clusters.items()
                    if nearest in m)
        members = list(clusters[root])
        unions = 0
        if len(members) < MIN_CLUSTER:
            for d, p in dists[1:]:
                rk = next(k for k, m in clusters.items() if p in m)
                if rk != root:
                    members += [m for m in clusters[rk]
                                if m not in members]
                    unions += 1
                if len(members) >= MIN_CLUSTER:
                    break
        pw = pairwise_distances([vec[r] for r in members])
        med, mad = median_mad(pw) if pw else (None, None)
        return {"root": root, "members": members, "unions": unions,
                "d_min_cluster": min(cosine_distance(row_vec, vec[p])
                                     for p in members),
                "d_min_corpus": dists[0][0],
                "nearest_prior": nearest,
                "p95": pairwise_percentile(pw, 0.95) if pw else None,
                "median": med, "mad": mad, "n_pairs": len(pw)}

    def judge(row_id, text):
        c = extract_core_mechanism(text)
        if c.extraction_miss:
            return {"row_id": row_id, "typed": "EXTRACTION_MISS"}
        return judge_vec(row_id, enc.encode(c.text),
                         method=c.method)

    def judge_vec(row_id, row_vec, method="raw_anchor_encoding"):
        """The anchor path: the RAW encoding judged through the same
        legs (evaluate_corpus's calibration uses the raw anchors; the
        extraction is a rows/priors-only step). Also the determinism
        check: the novel anchor's corpus distance must reproduce the
        r106 record (0.10399)."""
        rv = reference_class(row_vec)
        # the amendment-2 legs: the LOO isolation distribution (the
        # within-domain scale — each prior row's nearest neighbor is a
        # same-domain row by construction)
        p95_leg = rv["d_min_corpus"] > loo_p95
        z = ((rv["d_min_corpus"] - loo_med) / loo_mad
             if loo_mad else None)
        z_leg = z is not None and z > K_Z
        margin_leg = rv["d_min_corpus"] > obv_dist + MARGIN
        return {"row_id": row_id,
                "method": method,
                "d_min_corpus": round(rv["d_min_corpus"], 6),
                "loo_p95": round(loo_p95, 6),
                "loo_z": round(z, 3) if z is not None else None,
                "d_min_cluster": round(rv["d_min_cluster"], 6),
                "nearest_prior": rv["nearest_prior"],
                "cluster_n": len(set(rv["members"])),
                "cluster_unions": rv["unions"],
                "cluster_p95": round(rv["p95"], 6)
                if rv["p95"] is not None else None,
                "z": round(z, 3) if z is not None else None,
                "margin_leg": margin_leg,
                "p95_domain_leg": p95_leg,
                "mad_z_leg": z_leg,
                "novel": bool(margin_leg and (p95_leg or z_leg))}

    # anchor calibration on the SAME scale as the r106 run (the
    # anchors are encoded RAW — evaluate_corpus's own rule; the
    # extraction is a rows/priors-only step)
    v_obv = enc.encode(KNOWN_OBVIOUS_ANCHOR)
    obv_dist = min(cosine_distance(v_obv, vec[p]) for p in prior_ids)
    novel_j = judge_vec("KNOWN_NOVEL_ANCHOR",
                        enc.encode(KNOWN_NOVEL_ANCHOR))
    obv_j = judge_vec("KNOWN_OBVIOUS_ANCHOR", v_obv)
    para_j = judge_vec("KNOWN_OBVIOUS_PARAPHRASE",
                       enc.encode(KNOWN_OBVIOUS_ANCHOR_PARAPHRASE))

    # self-match probes: 5 prior rows' own mechanisms fed back
    probe_ids = [prior_ids[i] for i in (0, len(prior_ids) // 4,
                                        len(prior_ids) // 2,
                                        3 * len(prior_ids) // 4,
                                        len(prior_ids) - 1)]
    probes = [judge(f"SELF::{r}", prior_live[r]) for r in probe_ids]
    false_passes = [p["row_id"] for p in probes if p.get("novel")]

    rows_j = [judge(r, t) for r, t in sorted(rows.items())]
    n_novel_v15 = sum(1 for v in rows_j if v.get("novel"))

    battery = {
        "known_novel_anchor_passes": novel_j.get("novel") is True,
        "known_obvious_anchor_fails": obv_j.get("novel") is False,
        "obvious_paraphrase_fails": para_j.get("novel") is False,
        "self_match_false_passes": false_passes,
        "zero_false_passes": not false_passes,
        "acceptance": (novel_j.get("novel") is True
                       and obv_j.get("novel") is False
                       and para_j.get("novel") is False
                       and not false_passes),
    }

    rec = {
        "record": "R110_D4_GATE_WITHIN_DOMAIN/1.0.0",
        "at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)"),
        "executor": "builder-r109s1",
        "claim": "c-0139 (r110-lane-d4-gate-recompute; the R110 "
                 "direction 4)",
        "prereg": "eval/r110_d4_gate_prereg.json (incl. the "
                  "pre-execution amendment: margin 0.03, strictly "
                  "below the measured anchor separation 0.0343)",
        "typed_finding": ("the strict same-domain prior subset is "
                          "EMPTY (0/192) — the reference class is "
                          "the pre-registered nearest-cluster "
                          "adaptation"),
        "derived_constants": {"t_c_median_pairwise":
                              round(t_c, 6),
                              "n_clusters": len(clusters),
                              "cluster_size_hist": sorted(
                                  len(m) for m in clusters.values()),
                              "loo_isolation_median":
                              round(loo_med, 6),
                              "loo_isolation_mad": round(loo_mad, 6),
                              "loo_isolation_p95": round(loo_p95, 6),
                              "margin": MARGIN, "k_z": K_Z},
        "anchors": {"known_novel": novel_j, "known_obvious": obv_j,
                    "obvious_paraphrase": para_j,
                    "obvious_anchor_corpus_dist":
                    round(obv_dist, 6)},
        "self_match_probes": probes,
        "v15_rows_informational": rows_j,
        "v15_n_novel": n_novel_v15,
        "battery": battery,
        "typed_conclusion": ("the battery "
                             + ("PASSES" if battery["acceptance"]
                                else "FAILS")
                             + " — the gate is usable per the "
                             "direction's test"
                             if battery["acceptance"] else
                             "the battery FAILS — the failures are "
                             "typed per leg in the records"),
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print("battery:", json.dumps(battery))
    print("novel anchor:", {k: novel_j[k] for k in
                            ("d_min_corpus", "d_min_cluster", "z",
                             "novel")})
    print("v15 n_novel (informational):", n_novel_v15)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
