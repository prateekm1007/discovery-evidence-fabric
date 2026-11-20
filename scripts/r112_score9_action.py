#!/usr/bin/env python3
"""r112_score9_action.py — the R112 direction 4: the score-9 typed
RCA->action record. The miss is GENUINE recovery (0 parse failures —
the generator-side contract is clean), so the action is a LANE DESIGN
decision, not a fix. The two branches of the direction:
  (a) the generation-side lever (mechanism-space prompting +
      inspiration retrieval) — a NEW one-run batch, quota-consuming,
      and per the direction's own rule ("if amended, auditor-authored
      prereg with power basis — no self-tuning") it must NOT run
      before the auditor authors/amends the prereg;
  (b) the prereg amendment REQUEST (filed here) — the bar's
      calibration class (0.40 on the m2-curated lineage vs the
      abstract-authored post-cutoff GTs) and the two-judge fail-closed
      adjudication (24/30 PARTIAL) are protocol-class properties, the
      auditor's call.
This record files (b) with the drafted lever design attached as the
amendment input, and does NOT run (a) — the quota is untouched."""
import json
from pathlib import Path

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
OUT = REPO / "eval" / "r112_score9_action.json"

rec = {
    "record": "R112_SCORE9_ACTION/1.0.0",
    "at": "2026-11-20T16:30:00Z (sandbox clock, TRUE UTC)",
    "executor": "builder-r111s1",
    "claim_context": "the R112 direction 4 (the score-9 capability "
                     "lever); the R111 measurement "
                     "(eval/r111_score9_rerun.json): 5/30 RECOVERED = "
                     "0.1667, CI95 [0.0734, 0.3356], bar 0.40 NOT met, "
                     "ZERO parse exhaustions, 0 interventions",
    "rca_typed": [
        ("the two-judge adjudication degrades to PARTIAL unless BOTH "
         "judges rate RECOVERED (the protocol's fail-closed rule): "
         "24/30 rows landed PARTIAL — the RECOVERED rate is a "
         "both-agreement rate structurally below any single-judge "
         "rate"),
        ("the post-cutoff ground truths are authored from publisher "
         "abstracts while the 0.40 bar was calibrated on the "
         "MOOSE-Chem2 curated-GT lineage — the corpus provenance's "
         "own typed caveat (eval/r105s2_score9_postcutoff_status."
         "json); the comparison classes differ"),
        ("the generator-side contract is CLEAN: 0 parse exhaustions "
         "(5/30 in the r106 run), 0 interventions — the miss is a "
         "genuine recovery miss, not an infrastructure failure"),
    ],
    "action_chosen": ("branch (b): the prereg amendment REQUEST — "
                      "filed to the auditor; branch (a) is DESIGNED "
                      "below and PREREGISTERED-AS-DRAFT only, never "
                      "run in this window (no quota consumed; one "
                      "generation run awaits the auditor-authored "
                      "prereg)"),
    "amendment_request": {
        "to": "the auditor (the prereg owner per the direction)",
        "asks": [
            ("rule on the BAR calibration class for the post-cutoff "
             "corpus: the m2-curated 0.40 vs an abstract-authored-GT "
             "class (a power basis is the auditor's authoring duty; "
             "the candidate power inputs are committed: the r106 "
             "30-batch + the R111 30-batch, the Wilson CIs, the "
             "two-judge agreement structure)"),
            ("rule on the adjudication structure: the both-judge "
             "fail-closed RECOVERED rule caps the rate by the judge "
             "agreement itself — the amendment may define the "
             "single-judge primary with the both-judge as the "
             "confirmed class, or keep the fail-closed rule with a "
             "class-calibrated bar"),
            ("rule on the served-form calibration: the abstract-"
             "authored GTs' key-mechanism element granularity vs the "
             "m2 curated elements (the Dir-3 instrument's element-"
             "recall machinery is the committed measurement layer for "
             "that class)"),
        ],
    },
    "lever_design_draft": {
        "name": "mechanism-space prompting + inspiration retrieval "
                "(the direction's own lever)",
        "generation_side": [
            ("the served prompt gains a MECHANISM-SPACE scaffold: the "
             "answer must name the causal chain (observable -> "
             "intermediate physical quantity -> decision), the "
             "domain-physical constraint it exploits, and the "
             "failure mode that bounds it — the key-mechanism "
             "element shapes, not free prose"),
            ("INSPIRATION RETRIEVAL: the corpus item's abstract "
             "anchor + the Dir-3 instrument's element list seed a "
             "typed retrieval slot (the committed SPECTER2 anchor "
             "machinery, the D4 gate's own constants) — the "
             "inspiration set is PRE-REGISTERED per item before any "
             "generation byte, never tuned post hoc"),
        ],
        "measurement_side": [
            ("the same Inspect harness, the same checkpoint discipline "
             "(ONE logical run), the same independent recompute path "
             "(the engine's deterministic acceptance module on the "
             "committed eval-log bytes)"),
            ("the Wilson 95% CI + the conservative 30-denominator "
             "rule unchanged; the bar itself is the auditor's "
             "amendment output"),
        ],
    },
    "no_quota_consumed_this_window": True,
    "no_acceptance_claims": True,
}
OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
print("wrote", OUT)
