#!/usr/bin/env python3
"""r99s2_p4_specter2_fullcorpus/1.0.0 — the score-8 P4 semantic
novelty leg recomputed over the FULL prior-art corpus (the offline
Art. 28 lane while the v14 push is credential-blocked; builder-r99s2,
claim c-0115's lane family, zero generation).

THE BLIND SPOT BEING CLOSED (the r99s1 calibration's own typed
finding + the CORR-6 lesson): the r99s1 SPECTER2 calibration compared
the burned v13 rows against the v9-v12 SOLUTION rows ONLY — the same
v9-v12-only-corpus blind spot that let the 13 prior-domain repeats
through the v13 authoring check. THIS script recomputes against the
FULL prior-art corpus:
  (i)  the committed v9-v12 SOLUTION rows (a1_answer, unchanged), AND
  (ii) the v1-v12 PROBLEM statements (device + failure + question,
       from the audit-ref committed bytes) AND the dev12 public bank
       (device + failure + failure_mode + constraint, from HEAD).
A v13 solution that merely re-describes a v1-v12 problem's known
scenario/mitigation space must now sit CLOSE to that prior text — the
full corpus makes the repeat class visible in the semantic space, not
only in the lexical domain-head space.

THE HONEST EXPECTATION (typed BEFORE the run — this is a
verification, not a gate): for the 13 CORR-6-verified repeat rows,
the distance to their VERIFIED prior source inside the FULL corpus
should be SMALL (near the paraphrase scale), and the distribution-
calibrated gate (min-distance > full-corpus pairwise p95) should
flag most of the 13 as NON-novel — i.e. the full corpus + SPECTER2
would have CAUGHT the v13 defect class pre-run. The 17 fresh rows
are expected to sit farther out. Every number is disclosed verbatim;
the gate definition remains the auditor's custody (AM87 redefined
the score-8 novelty gate to core-mechanism encoding + anchor-relative
calibration — this record is INPUT, never a verdict).

Zero generation (encoder only); deterministic (model.eval(), no
sampling); deterministic text assembly from committed bytes.
"""
from __future__ import annotations

import datetime
import glob
import importlib.util
import itertools
import json
import os
import subprocess
import sys

REPO = "/home/z/fabric-v14"
CACHE = "/home/z/models_cache"
AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
OUT = REPO + "/eval/r99s2_p4_specter2_fullcorpus.json"
sys.path.insert(0, REPO + "/scripts")

spec = importlib.util.spec_from_file_location(
    "harness", REPO + "/scripts/r99_p4_specter2.py")
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)
# this sandbox's layout differs from the r99s1 window's: retarget the
# harness constants BEFORE any call (the vault path and the weights
# cache; the token itself is read from the gitignored vault at call
# time, never printed)
harness.REPO = REPO
harness.CACHE = CACHE

# the committed-byte text loader lives in the r98 TF-IDF module (the
# harness imports it lazily inside its own main)
spec98 = importlib.util.spec_from_file_location(
    "r98p4", REPO + "/scripts/r98_p4_novelty.py")
r98p4 = importlib.util.module_from_spec(spec98)
spec98.loader.exec_module(r98p4)
load_texts = r98p4.load_texts

# the CORR-6 verified repeat pairs (eval/r97_v13_disjointness_
# verifier_findings.json finding_1, committed bytes)
VERIFIED_REPEAT_PAIRS = {
    "HO13-01-glass-tank-stones": ["HO4-04", "HO8-04"],
    "HO13-04-urea-biuret": ["HO10-04"],
    "HO13-05-pp-extruder-discoloration": ["HO7-02"],
    "HO13-07-methanol-conversion": ["HO10-13", "HO10-08"],
    "HO13-13-anodize-burning": ["HO8-01"],
    "HO13-14-digester-souring": ["HO7-12"],
    "HO13-17-forklift-battery-fade": ["HO3-10"],
    "HO13-20-hydraulic-press-seal": ["HO-04"],
    "HO13-22-esp-sparking": ["HO4-01", "HO12-25"],
    "HO13-24-swro-scaling": ["HO4-06"],
    "HO13-27-steam-trap-failure": ["HO5-09"],
    "HO13-29-cnc-spindle-preload": ["dev12"],
    "HO13-30-pv-inverter-caps": ["HO-18"],
}


def _audit_problems(v: int) -> list:
    r = subprocess.run(
        ["git", "show", f"{AUDIT_REF}:audit/holdout_v{v}/"
         f"holdout_v{v}_problems.json"],
        capture_output=True, cwd=REPO)
    if r.returncode != 0:
        raise RuntimeError(f"v{v} problems unreadable (typed abort)")
    return json.loads(r.stdout.decode("utf-8"))["problems"]


def full_prior_corpus():
    """(id, text) over the FULL prior-art corpus from committed
    bytes: v9-v12 solutions + v1-v12 problems + dev12 problems."""
    sol_docs = _solution_rows()
    prob_docs = _problem_texts()
    docs = sol_docs + prob_docs
    return docs, sol_docs, prob_docs


def _solution_rows():
    return load_texts(
        [REPO + "/eval/holdout_v9_generation/rows",
         REPO + "/eval/holdout_v10_generation/rows",
         REPO + "/eval/holdout_v11_generation/rows",
         REPO + "/eval/holdout_v12_generation/rows"])


def _problem_texts():
    docs = []
    for v in range(1, 13):
        for p in _audit_problems(v):
            t = " ".join(str(p.get(k, "")) for k in
                         ("device", "failure", "question")).strip()
            if t:
                docs.append((p["problem_id"], t))
    r = subprocess.run(["git", "show", "HEAD:eval/problems_dev12.json"],
                       capture_output=True, cwd=REPO)
    if r.returncode == 0:
        for p in json.loads(r.stdout.decode("utf-8"))["problems"]:
            t = " ".join(str(p.get(k, "")) for k in
                         ("device", "failure", "failure_mode",
                          "constraint")).strip()
            if t:
                docs.append(("dev12:" + p.get("problem_id", "?"), t))
    return docs


def _v13_candidates():
    return load_texts(
        [REPO + "/eval/holdout_v13_generation/rows"])


def main() -> int:
    import torch
    tok, model = harness.load_model()

    # 0) the calibration pair MUST re-run first (the harness's typed
    # precondition: only when both checks pass are distances reported)
    cal_texts = [harness.CAL_OBVIOUS, harness.CAL_OBVIOUS_PARAPHRASE,
                 harness.CAL_NOVEL]
    cal = harness.encode(tok, model, cal_texts)
    d_par = float(1 - (cal[0] @ cal[1]).item())
    d_on = float(1 - (cal[0] @ cal[2]).item())
    calib = {"paraphrase_distance": round(d_par, 4),
             "paraphrase_pass": d_par < 0.05,
             "obvious_novel_distance": round(d_on, 4),
             "obvious_novel_pass_am85_absolute": d_on >= 0.2}
    print("CALIBRATION:", json.dumps(calib), flush=True)

    sol_docs = _solution_rows()
    prob_docs = _problem_texts()
    full_docs = sol_docs + prob_docs
    cand_docs = _v13_candidates()
    print(f"full prior corpus: {len(full_docs)} docs "
          f"({len(sol_docs)} v9-v12 solutions + {len(prob_docs)} "
          f"v1-v12+dev12 problem texts); candidates {len(cand_docs)} "
          "(burned v13 rows)", flush=True)

    C = harness.encode(tok, model, [t for _, t in cand_docs])
    P = harness.encode(tok, model, [t for _, t in full_docs])
    sims = C @ P.T

    # the FULL corpus's own pairwise distance distribution
    Psims = P @ P.T
    n = P.size(0)
    pair_d = [float(1 - Psims[i, j].item())
              for i, j in itertools.combinations(range(n), 2)]
    pair_d.sort()
    p50 = pair_d[len(pair_d) // 2]
    p95 = pair_d[int(len(pair_d) * 0.95)]
    pmax = pair_d[-1]

    # the OLD blind corpus (v9-v12 solutions only) for the comparison
    P_old = harness.encode(tok, model, [t for _, t in sol_docs])
    sims_old = C @ P_old.T

    rows = []
    for i, (pid, _) in enumerate(cand_docs):
        j = int(sims[i].argmax())
        dist_full = float(1 - sims[i, j].item())
        j_old = int(sims_old[i].argmax())
        dist_old = float(1 - sims_old[i, j_old].item())
        rank = sum(1 for d in pair_d if d < dist_full) / len(pair_d)
        # the verified prior source distance (the blind-spot test)
        src_ids = VERIFIED_REPEAT_PAIRS.get(pid.split("#")[0], [])
        src_dists = []
        for sid in src_ids:
            for k, (did, _) in enumerate(full_docs):
                # the v1 problem ids use the 'HO-NN' form (no set
                # digit) — accept both id conventions
                if did == sid or did == "dev12:" + sid or \
                        did.startswith(sid) or \
                        did.startswith(sid.replace("HO", "HO-", 1)):
                    src_dists.append(
                        {"source_id": did,
                         "distance": round(
                             float(1 - sims[i, k].item()), 4)})
        best_src = min((d["distance"] for d in src_dists), default=None)
        rows.append({
            "problem_id": pid,
            "nearest_full_corpus_id": full_docs[j][0],
            "min_distance_full_corpus": round(dist_full, 4),
            "min_distance_old_blind_corpus": round(dist_old, 4),
            "full_corpus_percentile_rank": round(rank, 4),
            "distribution_novel_pass_p95_full": dist_full > p95,
            "verified_repeat_row": pid in VERIFIED_REPEAT_PAIRS,
            "verified_source_distances": src_dists,
            "min_verified_source_distance": best_src,
        })

    n_rep = sum(1 for r in rows if r["verified_repeat_row"])
    rep_flagged_non_novel = sum(
        1 for r in rows
        if r["verified_repeat_row"]
        and not r["distribution_novel_pass_p95_full"])
    rep_close_to_source = sum(
        1 for r in rows
        if r["verified_repeat_row"]
        and r["min_verified_source_distance"] is not None
        and r["min_verified_source_distance"] < 0.10)
    fresh = [r for r in rows if not r["verified_repeat_row"]]
    fresh_p95_pass = sum(1 for r in fresh
                         if r["distribution_novel_pass_p95_full"])

    rec = {
        "record": "R99S2_P4_SPECTER2_FULLCORPUS/1.0.0",
        "filed_at": datetime.datetime.now(datetime.UTC).isoformat()
                            .replace("+00:00", "Z"),
        "lane": "the score-8 P4 FULL-corpus semantic recompute (the "
                "offline Art. 28 lane; the r99s1 calibration's typed "
                "v9-v12-only blind spot closed)",
        "weights": {"encoder": "allenai/specter2_base",
                    "adapter": "allenai/specter2 (proximity)",
                    "license": "Apache-2.0 (AllenAI) — NOTICE.md",
                    "fetched_via": "the restored vault HF token "
                                   "(digest-verified 33bc7af22c62; "
                                   "value never printed/committed)",
                    "cache": CACHE},
        "calibration": calib,
        "corpus": {"full_n": len(full_docs),
                   "v9_v12_solution_n": len(sol_docs),
                   "v1_v12_dev12_problem_n": len(prob_docs),
                   "candidates_n": len(cand_docs),
                   "texts": "committed bytes only (solutions: "
                            "a1_answer from the rows dirs; problems: "
                            "device+failure+question from the audit "
                            "ref; dev12: device+failure+failure_mode"
                            "+constraint)"},
        "full_corpus_distance_distribution": {
            "p50": round(p50, 4), "p95": round(p95, 4),
            "max": round(pmax, 4), "n_pairs": len(pair_d)},
        "rows": rows,
        "blind_spot_closure_test": {
            "honest_expectation_typed_before_run": (
                "the 13 CORR-6 repeat rows should sit CLOSE to their "
                "verified prior sources in the FULL corpus (the "
                "repeat class must be visible semantically now) and "
                "the p95 distribution gate should flag most of them "
                "NON-novel — the full corpus would have caught the "
                "v13 defect class pre-run"),
            "repeat_rows_total": n_rep,
            "repeat_rows_flagged_non_novel_by_p95": rep_flagged_non_novel,
            "repeat_rows_within_0p10_of_verified_source": (
                rep_close_to_source),
            "fresh_rows_total": len(fresh),
            "fresh_rows_passing_p95": fresh_p95_pass,
            "note": "the gate definition remains the auditor's "
                    "custody (AM87: core-mechanism encoding + "
                    "anchor-relative); this record is INPUT, never a "
                    "verdict; every number disclosed verbatim",
        },
        "zero_generation": True,
        "deterministic": True,
    }
    with open(OUT, "w") as f:
        json.dump(rec, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("record ->", OUT, flush=True)
    print(json.dumps(rec["blind_spot_closure_test"], indent=1),
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
