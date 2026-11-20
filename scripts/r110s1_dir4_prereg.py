#!/usr/bin/env python3
"""r110s1_dir4_prereg.py — the R110 direction-4 claim (c-0139) + the
PRE-REGISTRATION of the within-domain gate recompute, committed BEFORE
any recompute byte (Art. 6 anti-gaming; claim-before-work Art. 29(b)).

The typed finding that shapes the design: the strict same-domain prior
subset for the v15 evaluated rows is EMPTY (0/192 textile/leather rows
in the v1-v14 prior corpus — the v15 holdout was auditor-authored
DOMAIN-DISJOINT by design, the r99 seal b0e7011309fa...). Direction 4
option (a) in its strict form is UNDEFINED on committed bytes; the
pre-registered adaptation keeps the anchor-relative two-leg structure
and re-references the p95/MAD legs to the row's NEAREST PRIOR PROCESS
NEIGHBORHOOD (cluster), which is computable for every row from
committed bytes with the same deterministic SPECTER2 stack.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

REG = Path("eval/work_claims.json")
PRE = Path("eval/r110_d4_gate_prereg.json")
NOW = datetime.now(timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)")

d = json.loads(REG.read_text(encoding="utf-8"))
ids = {c["claim_id"] for c in d["claims"]}
assert "c-0139" not in ids, "c-0139 exists — fail closed"
d["claims"].append({
    "claim_id": "c-0139",
    "claimed_at": NOW,
    "registered_at": NOW + " (push = the lock, Art. 29(b))",
    "work_id": "r110-lane-d4-gate-recompute",
    "session_id": "builder-r109s1",
    "role": "EXECUTOR",
    "status": "OPEN",
    "kind": "measurement",
    "base_sha": "ed1e02754",
    "lease_expiry": "2026-11-23T23:59:00Z",
    "title": ("the R110 direction 4 EXECUTION (the auditor pre-authorized "
              "the recompute with the staged options (a)+(b)): the "
              "score-8 anchor-relative gate recomputed with a "
              "domain-referenced p95/MAD leg after the typed finding "
              "that the strict same-domain prior subset is EMPTY "
              "(0/192 — the auditor's own disjointness design); the "
              "acceptance battery: the known-novel anchor PASSES, the "
              "obvious anchor + its paraphrase FAIL, self-match probes "
              "FAIL (0 false passes), the 30 v15 rows reported as a "
              "distribution (informational — no v15 gold labels)"),
    "notes": ("the prereg (eval/r110_d4_gate_prereg.json) commits the "
              "rule + thresholds BEFORE the verdict computation; the "
              "recompute is deterministic (SPECTER2 eval mode, zero "
              "quota)"),
    "artifact_paths": ["eval/r110_d4_gate_within_domain.json"],
})
REG.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")

prereg = {
    "record": "R110_D4_GATE_PREREG/1.0.0 (PRE-REGISTRATION)",
    "at": NOW,
    "executor": "builder-r109s1",
    "claim": "c-0139 (r110-lane-d4-gate-recompute)",
    "typed_finding_first": {
        "same_domain_prior_subset": 0,
        "prior_corpus_n": 192,
        "evidence": ("the deterministic slug scan over all 192 prior "
                     "row ids finds ZERO textile/leather rows (the "
                     "keyword list in scripts/r110_d4_gate_recompute."
                     "py, committed with this prereg); the v15 holdout "
                     "was auditor-authored DOMAIN-DISJOINT by design "
                     "(eval/r99_disjointness_v15_record.json, the F50 "
                     "seal b0e7011309fa...)"),
        "consequence": ("direction 4 option (a) in its strict "
                        "same-domain form is UNDEFINED on committed "
                        "bytes — the reference class is empty"),
    },
    "pre_registered_rule": {
        "representation": ("the SAME deterministic stack as the r106 "
                           "gate run: extract_core_mechanism (the "
                           "novelty-statement-marker rule) + "
                           "allenai/specter2_base proximity adapter, "
                           "eval mode, cosine distance"),
        "reference_class": ("the row's NEAREST PRIOR PROCESS "
                            "NEIGHBORHOOD: nearest prior row -> its "
                            "single-linkage cluster; clusters formed "
                            "at t_c = the PRIOR CORPUS' OWN MEDIAN "
                            "pairwise cosine distance (a derived, "
                            "deterministic constant — recorded at "
                            "cluster time, never hand-tuned)"),
        "small_cluster_fallback": ("a cluster with <8 rows unions the "
                                   "next-nearest cluster until >=8 "
                                   "(typed in the record per row)"),
        "legs": {
            "margin_leg (unchanged)": "d_min > known_obvious_anchor_dist "
                                      "+ 0.05 (the r100/r106 prereg "
                                      "margin, untouched)",
            "p95_domain_leg (option a, adapted)": "d_min(row, cluster) "
                                                  "> p95(pairwise within "
                                                  "the reference cluster)",
            "mad_z_leg (option b)": "z = (d_min - median(cluster "
                                    "pairwise)) / MAD(cluster pairwise) "
                                    "> 2.0 (the robust-outlier cut, "
                                    "pre-registered HERE at 2.0 before "
                                    "any verdict; the novel anchor's z "
                                    "is REPORTED, never used to set "
                                    "the cut)",
        },
        "verdict_rule": "novel iff margin_leg AND (p95_domain_leg OR "
                        "mad_z_leg)",
        "determinism": ("sorted keys, rounded floats, no wall-clock in "
                        "hashed inputs (Art. 15); the encoder cache is "
                        "the committed models_cache path"),
    },
    "acceptance_battery": {
        "known_novel_anchor": "must PASS (novel)",
        "known_obvious_anchor": "must FAIL",
        "known_obvious_paraphrase": "must FAIL",
        "self_match_probes": ("5 prior rows' own extracted mechanisms "
                              "fed back as evaluated rows — ALL must "
                              "FAIL (0 false passes)"),
        "v15_rows": ("the 30 burned rows reported as a distribution "
                     "(informational; no gold labels — the battery is "
                     "the acceptance, not the v15 verdicts)"),
    },
    "anti_tuning": ("this prereg lands on the queue BEFORE the "
                    "recompute runs; any post-hoc change to t_c, k_z, "
                    "the probe set, or the verdict rule is a typed "
                    "finding"),
}
PRE.write_text(json.dumps(prereg, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")
print("c-0139 registered; prereg written:", PRE)
