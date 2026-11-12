# eval score table (commit a11ed5a4890b, dirty_tree=False, 2026-11-12T08:15:47+00:00Z)

metric: blind pairwise win-rate (pipeline vs strongest zero-paid single-shot baseline)
KPI: R506 yield funnel on DEV: mechanisms_found + candidates_generated_distinct
criteria: a=answers the asked question; b=uses user-stated variables; c=gives a specific testable prediction; d=grounded in the provided evidence; e=uses the user's clarification answer correctly; f=gives a specific, non-obvious design (not the generic default)

pipeline completion: 2/2
subset: custom:2 (n=2)
yield funnel (DEV): {"n": 2, "completed": 2, "mechanisms_found": 2, "candidates_generated_distinct": 2, "mechanisms_rate": 1.0, "distinct_rate": 1.0, "starved": [], "starved_reasons": {}}
yield funnel (fresh): {"n": 2, "completed": 2, "mechanisms_found": 2, "candidates_generated_distinct": 2, "mechanisms_rate": 1.0, "distinct_rate": 1.0, "starved": [], "starved_reasons": {}}
wall time: {"sum_wall_s": 317.5, "mean_wall_s": 158.8, "max_wall_s": 175.4, "mean_stage_s": {"ADJUDICATION": 0.01, "ATTACK": 5.55, "CLASSIFY": 0.01, "COLLISION": 10.01, "CONTRADICTION": 0.0, "FREEZE": 0.02, "KILLER_EXPERIMENT": 0.01, "MECHANISM_SPACE": 36.39, "NEXT_BEST_ACTION": 0.0, "PHYSICS": 0.19, "PREMISE_GATE": 0.0, "RANK": 0.01, "RETRIEVE": 46.25, "SYNTHESIZE": 54.55, "VERIFY": 0.01}}
speed: {"n": 2, "p50_wall_s": 158.8, "p95_wall_s": 173.7, "timeout_count": 0, "budget_note": "owner budget: median ~120 s, worst ~300 s; timeouts are INCOMPLETE_INFRASTRUCTURE"}
baseline route: zai / glm-4-plus (OK)
judge route: zai / glm-4-plus (SHARED_FAMILY_DISCLOSED)
judge calibration: 0.833 (n=30, passed=True)

n usable pairs (completed pipeline only): 0/2
full scoreable pairs: 0
pairs with unverified numbers: 0
pipeline wins 0  baseline wins 0  ties 0

**SYSTEM SCORE (unconditional, all 2 problems): 0.0**  (0 wins, 0 ties)

**CONDITIONAL QUALITY (fully scoreable pairs, calibration-gated): NOT_MEASURED**  (0W 0T 0L over 0 pairs)

system losses (infrastructure/refusal/contract-invalid, N=2): 2;  normal-approx CI on N: (0.0, 0.0) (method normal_approx_0_0.5_1)
judge outcomes: {"JUDGE_VALID": 0, "JUDGE_TRANSPORT_FAILED": 0, "JUDGE_EMPTY_OUTPUT": 0, "JUDGE_PARSE_FAILED": 0, "JUDGE_CALIBRATION_FAILED": 0}
second judge: {"agree": 0, "disagree": 0, "no_route_or_invalid": 2}

fresh vs contaminated: {"DEV_CONTAMINATED": null, "FRESH": {"n": 2, "completed": 2, "usable": 0, "win_rate": "NOT_MEASURED"}}
criterion mean diffs (pipeline-baseline): {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty": null}
answer-shape contract: [{"problem_id": "eval-sofc-thermal-cycling", "valid": false, "violations": ["intervention contract: concrete parameter not labeled EVIDENCE-BACKED or ASSUMPTION", "intervention contract: no concrete numeric parameter", "intervention contract: no concrete test/measure named"]}, {"problem_id": "dev-fu-004-fouling", "valid": false, "violations": ["predictor contract: no INDICATOR: declared", "predictor contract: no THRESHOLD: declared", "predictor contract: no VALIDATION PROTOCOL: declared", "predictor contract: no numeric threshold with units", "predictor contract: no n=\u2026 sample-count stated", "predictor contract: the VALIDATION PROTOCOL does not name the INDICATOR quantity (no shared content word beyond protocol scaffolding) \u2014 the protocol must validate the same measure the threshold is declared on"]}]

| problem | tag | type | final_status | completed | wall_s | mech | distinct | starved_reason | winner | crit diffs |
|---|---|---|---|---|---|---|---|---|---|---|
| eval-sofc-thermal-cycling | None | intervention-proposal | INVENTION_REQUIRES_EXPERIMENT | True | 142.1 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
| dev-fu-004-fouling | None | predictor-design | INVENTION_REQUIRES_EXPERIMENT | True | 175.4 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
