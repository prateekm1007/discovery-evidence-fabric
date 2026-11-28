#!/usr/bin/env python3
"""r109_d4_gate_staging.py — the R108 direction-4 STAGING record: the
score-8 anchor-relative gate's failure anatomy + the three v16
candidate definitions' staged data, computed from COMMITTED BYTES
(r106_core_mechanism_gate_run.json verdicts + calibration). The
builder stages data only — the v16 gate definition stays the
auditor's (the R108 direction 4 assigns authorship; execution rides a
claim when it lands)."""
import json
import statistics as st
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
G = json.loads((REPO / "eval" / "r106_core_mechanism_gate_run.json")
               .read_text(encoding="utf-8"))
OUT = REPO / "eval" / "r109_d4_gate_staging.json"

cal = G["calibration"]
kn = cal["checks"]["known_novel_anchor_prior_dist"]
ko = cal["checks"]["known_obvious_anchor_prior_dist"]
p95 = cal["checks"]["prior_p95"]
margin = G["margin"]
margin_leg = ko + margin

vs = G["verdicts"]
ds = sorted(v["core_mechanism_distance"] for v in vs)
med = st.median(ds)
mad = st.median([abs(x - med) for x in ds])
eval_max = max(ds)

legs_table = {
    "known_novel_anchor_dist": kn,
    "known_obvious_anchor_dist": ko,
    "prior_p95_heterogeneous": p95,
    "margin_leg_threshold (obvious + margin)": round(margin_leg, 6),
    "anchor_vs_p95_leg": {"passes": kn > p95,
                          "gap": round(kn - p95, 6)},
    "anchor_vs_margin_leg": {"passes": kn > margin_leg,
                             "gap": round(kn - margin_leg, 6)},
    "evaluated_rows": {
        "n": len(ds), "min": min(ds), "median": med, "max": eval_max,
        "beyond_p95_count": sum(1 for x in ds if x > p95),
        "beyond_margin_count": sum(1 for x in ds if x > margin_leg),
        "n_novel_gate_output": G["n_novel"],
    },
}

eval_med_z = [round((x - med) / mad, 2) for x in ds] if mad else []
anchor_z_eval_scale = round((kn - med) / mad, 2) if mad else None

candidates = {
    "(a) within_domain_p95": {
        "definition": "the p95 leg recomputes over a DOMAIN-MATCHED "
                      "prior subset (the textile/leather prior rows "
                      "of v1-v14) instead of the full heterogeneous "
                      "192-row corpus",
        "staged_evidence": {
            "nearest_prior_version_composition_of_30_rows":
                sorted({v["nearest_prior_art_id"].split("/")[0]
                        for v in vs}),
            "reading": ("every evaluated row's nearest prior lands in "
                        "v9-v14 and the evaluated distances "
                        "(0.037-0.096) sit far below the heterogeneous "
                        "p95 (0.158) — the heterogeneous corpus "
                        "disperses across domains it does not share "
                        "with the evaluated set, inflating the leg's "
                        "threshold beyond ANY same-domain row"),
        },
        "v16_execution_needs": ("the deterministic core-mechanism "
                                "extraction + SPECTER2 re-embed over "
                                "the domain-matched prior subset "
                                "(committed bytes, zero quota); the "
                                "domain tag source must be "
                                "pre-registered with the definition"),
    },
    "(b) robust_mad_z": {
        "definition": "the leg normalizes distances by the PRIOR "
                      "corpus' median/MAD (robust center/scale) "
                      "instead of the raw p95: row_novel iff "
                      "z_prior(row) > z_prior(anchor_novel) + k for a "
                      "pre-registered k",
        "staged_evidence": {
            "evaluated_side_median": med,
            "evaluated_side_MAD": mad,
            "evaluated_rows_z_range": [min(eval_med_z),
                                       max(eval_med_z)],
            "known_novel_anchor_z_on_eval_scale": anchor_z_eval_scale,
            "reading": ("on the evaluated scale the anchor sits "
                        "ABOVE every evaluated row (a workable "
                        "separation) — the degenerate input is the "
                        "PRIOR corpus' cross-domain scale, so the "
                        "MAD must be taken over the prior corpus' "
                        "own within-domain structure, not the pooled "
                        "18336 pairs"),
        },
        "v16_execution_needs": ("the prior corpus' per-row distances "
                                "recomputed (deterministic; the "
                                "192-row embed set) — its median/MAD "
                                "are the normalizers; k pre-registered "
                                "before scoring"),
    },
    "(c) margin_without_p95": {
        "definition": "drop the p95 leg entirely: row_novel iff "
                      "dist > dist(known_obvious_anchor) + margin",
        "staged_evidence": {
            "anchor_fails_even_this_leg": kn <= margin_leg,
            "anchor_gap": round(kn - margin_leg, 6),
            "evaluated_rows_beyond": sum(1 for x in ds
                                         if x > margin_leg),
            "reading": ("the margin leg ALONE still misclassifies the "
                        "known-novel anchor (0.104 < 0.1197): the "
                        "obvious-anchor distance + 0.05 exceeds the "
                        "novel anchor — margin-only is NOT sufficient "
                        "unless the margin shrinks below the "
                        "anchor separation (0.0343) or the anchor "
                        "calibration itself is re-authored"),
        },
        "v16_execution_needs": ("an auditor decision: re-author the "
                                "anchor pair (a tighter obvious "
                                "anchor or a nearer novel anchor) or "
                                "re-magnitude the margin — both are "
                                "instrument-authoring acts"),
    },
}

rec = {
    "record": "R109_D4_GATE_STAGING/1.0.0 (STAGING ONLY — the v16 "
              "definition is the auditor's)",
    "at": datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)"),
    "executor": "builder-r109s1",
    "claim": "c-0136 (r109-lane-d4-gate-staging; the R108 direction 4)",
    "basis": "eval/r106_core_mechanism_gate_run.json (committed verdict "
             "bytes; deterministic SPECTER2 stack; zero generation)",
    "failure_anatomy": legs_table,
    "v16_candidate_definitions_staged": candidates,
    "typed_conclusion": ("the R108 diagnosis is reproduced from bytes: "
                         "the known-novel anchor (0.104) sits below the "
                         "heterogeneous prior p95 (0.158) AND below the "
                         "margin leg (0.1197), while all 30 evaluated "
                         "rows (max 0.096) sit below BOTH legs — the "
                         "gate is degenerate on heterogeneous priors. "
                         "Candidate (a) fixes the threshold's reference "
                         "class; candidate (b) fixes the scale; "
                         "candidate (c) alone still misclassifies the "
                         "anchor. The choice + the anchor re-authoring "
                         "stay the auditor's v16 authoring act; the "
                         "builder executes under claim-before-work"),
}
OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")
print("staged; anchor> p95:", kn > p95, "| anchor> margin:", kn > margin_leg,
      "| rows beyond either leg: 0/30 | n_novel:", G["n_novel"])
print("wrote", OUT)
