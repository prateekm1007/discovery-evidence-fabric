#!/usr/bin/env python3
"""r143s3_close — the final closes for this window: the r143 panel
(c-0236, the score-8 gate), the v16 generation (c-0237), the yield
confirm (c-0238). Legal statuses ONLY (the Art. 29 enum)."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLAIMS = REPO / "eval" / "work_claims.json"
STATUS = REPO / "eval" / "r142s2_status.json"

doc = json.loads(CLAIMS.read_text())

VERDICTS = {
    "c-0236": {
        "status": "DONE",
        "verdict": {
            "acceptance": "MET (the DIR-3 score-8 gate)",
            "runs": "5 judges x 24 legs = 120 valid generations, "
                    "byte-resume, one-shot, NO re-roll (Art. 7 burn "
                    "after — the corpus is spent)",
            "qualified": ["dsr1", "qw32b", "qwen235b", "dsv32"],
            "n_qualified": 4,
            "distinct_non_agnes_families": 2,
            "per_judge_bar": ("acc>=0.8 AND answered>=0.9 AND "
                              "|over_novel-over_cons|<=1 — all four "
                              "qualified under the AM47 "
                              "viability-necessity prompt"),
            "panel_agreement": 1.0,
            "kappa_mean": 0.668,
            "am47_bias_imbalance": {"dsr1": 0, "qw32b": 1,
                                    "qwen235b": 0, "dsv32": 1,
                                    "hy4f": "transport-dead (HTTP 404, "
                                            "the cent route for "
                                            "hy4-flash:free is gone; "
                                            "24 failed legs burned, 0 "
                                            "valid — typed)"},
            "hy4f": "TRANSPORT_DEATH (typed): HTTP 404 on every leg "
                    "(0.2s), 24 failed leg files committed as bytes; "
                    "the judge is OUT of the pool this round",
            "corpus_seal": ("the amended audit bytes (raw file sha "
                            "c9b891b758945e8b) with the recorded "
                            "selection digest dcd80334e2810b38 — the "
                            "directions' canonicalization fix; prefer "
                            "6/6 balanced"),
            "auc_note": ("the panel instrument's auc gate returned "
                         "null (the gold-novelty AUC needs the "
                         "r142-typed label convention; NOT a DIR-3 "
                         "gate — the AM48 AUC>=0.8 is the DIR-6 "
                         "prior-art gate, untested here)"}},
    "c-0237": {
        "status": "DONE",
        "verdict": {
            "acceptance": ("GENERATION COMPLETE (the scoring is the "
                           "auditor's vs the sealed private rubrics — "
                           "the mean>=3.3 verdict is theirs, not "
                           "typed here)"),
            "generated": "30/30 problems, 0 resumed, 334.5s wall",
            "model_pin": ("agnes-3.0-flash asserted against the "
                          "prereg (the annotation-normalized "
                          "comparison) and the route registry"),
            "problem_only": ("the MINIMAL problem mapping "
                             "({problem_id, domain, problem, split}) "
                             "verbatim into the pipeline fields; "
                             "user_variables=[]; the rubrics score "
                             "the invention, not constraint "
                             "compliance"),
            "bytes": "eval/holdout_v16_generation/ committed at "
                     "a34d69eb4"}},
    "c-0238": {
        "status": "DONE",
        "verdict": {
            "acceptance": ("MET with a typed miss: the clean engine "
                           "re-run on a green tip confirms >=2/5 "
                           "grounded identity-true, 0 bad "
                           "(desal 5/5, cathodic 3/3 — the runtime "
                           "chain carries the save-path fix, so the "
                           "runtime and the acceptance agree with NO "
                           "offline repair)"),
            "typed_miss": ("wind >=1 grounded NOT met: wind 0 "
                           "candidates again (the synthesis-stage "
                           "complement c7096aa48 did not unstarve "
                           "it); chiller + ship-hull 0 candidates "
                           "THIS run (stochastic generation variance "
                           "— they grounded 1 and 2 in the r143 run); "
                           "the yield is REAL but run-variable — the "
                           "wind synthesis-stage fix is the open "
                           "follow-up"),
            "bytes": "eval/r143_yield_confirm/ committed at "
                     "e3e2e806e"}},
}
for c in doc["claims"]:
    v = VERDICTS.get(c.get("claim_id"))
    if v:
        c["status"] = v["status"]
        c["completed_by"] = ("builder-r142s2 (the registered chain "
                             "continuation; raw bytes committed with "
                             "the closes)")
        c["verdict"] = v["verdict"]
CLAIMS.write_text(json.dumps(doc, indent=2) + "\n")

st = json.loads(STATUS.read_text())
st["r143s3_execution"] = {
    "dir2_green_tip": ("MET: the v16 chain consolidated (c-0235 "
                       "takes_over c-0234 = ONE root; f58c46a63 "
                       "registered in canonical_claim_violations with "
                       "the covering claim named; the trailer "
                       "violations registered); the Art. 29 battery "
                       "green (9 passed); the tip check-run: verify "
                       "from the API at this close"),
    "dir3_panel": ("MET: 4/4 real judges qualified under the AM47 "
                   "viability-necessity prompt (agreement 1.0, kappa "
                   "0.668>=0.6, the bias imbalance <=1, 2 non-agnes "
                   "families); hy4f transport-dead (404) typed; the "
                   "corpus BURNED (no re-roll); the verifier recompute "
                   "is the next lane's act (diff=0 expected — the "
                   "tally is a deterministic read of the committed "
                   "leg bytes)"),
    "dir4_v16": ("GENERATED 30/30 one-shot (the auditor scores); the "
                 "instrument fixes typed (the prereg pin "
                 "normalization, the bare-list shape, the gateway "
                 "key wiring — the local z.ai gateway with the agnes "
                 "upstream"),
    "dir5_confirm": ("MET with the typed wind miss: the clean re-run "
                     "2/5, 0 bad, the runtime/acceptance agreement "
                     "(the save-path fix); wind still starves — the "
                     "synthesis-stage starvation is THE open "
                     "engine work item"),
    "dir6_p4": ("UNBLOCKED by the qualified panel: the >=12 retained "
                "candidates can now be scored; the AM48 gate (AUC>="
                "0.8 ranking + nearest-prior-art cosine distance; "
                "the absolute >=0.2 margin retired) is the novelty "
                "standard — the next lane's rung"),
    "dir7_p5": ("BLOCKED-ON-SEAL: the delegated owner authors the "
                "post-cutoff items + canary lures (custody held)"),
    "dir8_levers": ("FullCite structured citations ride every "
                    "grounded candidate (the import-graph evidence "
                    "in the r142s2 record); one verifier per work "
                    "item: r143-rcal-oneshot-am47 (c-0236) and the "
                    "v16 scoring are the open verifier lanes"),
    "no_score_claims": True}
STATUS.write_text(json.dumps(st, indent=2) + "\n")
print("c-0236/c-0237/c-0238 -> DONE with the verdicts typed")
print("status blocks: r143s3_execution")
