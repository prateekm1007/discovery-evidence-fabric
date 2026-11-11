# eval score table (commit 983cad20404f, dirty_tree=False, 2026-11-11T14:14:31+00:00Z)

metric: blind pairwise win-rate (pipeline vs strongest zero-paid single-shot baseline)
KPI: R506 yield funnel on DEV: mechanisms_found + candidates_generated_distinct
criteria: a=answers the asked question; b=uses user-stated variables; c=gives a specific testable prediction; d=grounded in the provided evidence; e=uses the user's clarification answer correctly; f=gives a specific, non-obvious design (not the generic default)

pipeline completion: 4/7
subset: dev7 (n=7)
yield funnel (DEV): {"n": 7, "completed": 4, "mechanisms_found": 5, "candidates_generated_distinct": 5, "mechanisms_rate": 0.714, "distinct_rate": 0.714, "starved": ["bench-p05-bridge-bearing-aging", "eval-new02-slipring-predictor"], "starved_reasons": {"bench-p05-bridge-bearing-aging": "GENERATION_NO_OPERATOR_CONTRACT", "eval-new02-slipring-predictor": "GENERATION_NO_OPERATOR_CONTRACT"}}
yield funnel (fresh): {"n": 4, "completed": 3, "mechanisms_found": 3, "candidates_generated_distinct": 3, "mechanisms_rate": 0.75, "distinct_rate": 0.75, "starved": ["eval-new02-slipring-predictor"], "starved_reasons": {"eval-new02-slipring-predictor": "GENERATION_NO_OPERATOR_CONTRACT"}}
wall time: {"sum_wall_s": 1791.2, "mean_wall_s": 255.9, "max_wall_s": 300.0, "mean_stage_s": {"ADJUDICATION": 0.03, "ATTACK": 36.08, "CLASSIFY": 0.02, "COLLISION": 16.35, "CONTRADICTION": 0.01, "FREEZE": 0.05, "KILLER_EXPERIMENT": 0.03, "MECHANISM_SPACE": 54.11, "NEXT_BEST_ACTION": 0.02, "PHYSICS": 0.78, "PREMISE_GATE": 0.01, "RANK": 0.02, "RETRIEVE": 41.17, "SYNTHESIZE": 52.46, "VERIFY": 0.02}}
speed: {"n": 7, "p50_wall_s": 298.3, "p95_wall_s": 300.0, "timeout_count": 3, "budget_note": "owner budget: median ~120 s, worst ~300 s; timeouts are INCOMPLETE_INFRASTRUCTURE"}
baseline route: agnes / agnes-3.0-flash (OK)
judge route: None / None (NO_ROUTE)
judge calibration: None (n=None, passed=None)

n usable pairs (completed pipeline only): 0/4
full scoreable pairs: 0
pairs with unverified numbers: 3
pipeline wins 0  baseline wins None  ties 0

**SYSTEM SCORE (unconditional, all 7 problems): None**  (0 wins, 0 ties)

**CONDITIONAL QUALITY (fully scoreable pairs, calibration-gated): NOT_MEASURED**  (0W 0T NoneL over 0 pairs)

system losses (infrastructure/refusal/contract-invalid, N=7): None;  normal-approx CI on N: None (method normal_approx_0_0.5_1)
judge outcomes: {"JUDGE_VALID": 0, "JUDGE_TRANSPORT_FAILED": 4, "JUDGE_EMPTY_OUTPUT": 0, "JUDGE_PARSE_FAILED": 0, "JUDGE_CALIBRATION_FAILED": 0}
second judge: {"agree": 0, "disagree": 0, "no_route_or_invalid": 7}

fresh vs contaminated: {"DEV_CONTAMINATED": {"n": 3, "completed": 1, "usable": 0, "win_rate": "NOT_MEASURED"}, "FRESH": {"n": 4, "completed": 3, "usable": 0, "win_rate": "NOT_MEASURED"}}
criterion mean diffs (pipeline-baseline): {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty": null}
answer-shape contract: [{"problem_id": "bench-p02-leadacid-grid-corrosion", "valid": false, "violations": ["intervention contract: concrete parameter not labeled EVIDENCE-BACKED or ASSUMPTION", "intervention contract: no concrete numeric parameter", "intervention contract: no concrete test/measure named"]}, {"problem_id": "bench-p05-bridge-bearing-aging", "valid": true, "violations": []}, {"problem_id": "bench-p09-packaging-barrier", "valid": false, "violations": ["intervention contract: concrete parameter not labeled EVIDENCE-BACKED or ASSUMPTION", "intervention contract: no concrete numeric parameter", "intervention contract: no concrete test/measure named"]}, {"problem_id": "eval-sofc-thermal-cycling", "valid": false, "violations": ["intervention contract: concrete parameter not labeled EVIDENCE-BACKED or ASSUMPTION", "intervention contract: no concrete numeric parameter", "intervention contract: no concrete test/measure named"]}, {"problem_id": "eval-new02-slipring-predictor", "valid": false, "violations": ["1 numeric token(s) absent from the evidence packet"]}, {"problem_id": "eval-new06-bearing-vibration-predictor", "valid": true, "violations": []}, {"problem_id": "eval-new09-hvac-filter-predictor", "valid": false, "violations": ["4 numeric token(s) absent from the evidence packet"]}]

| problem | tag | type | final_status | completed | wall_s | mech | distinct | starved_reason | winner | crit diffs |
|---|---|---|---|---|---|---|---|---|---|---|
| bench-p02-leadacid-grid-corrosion | DEV_CONTAMINATED | intervention-proposal | INCOMPLETE_INFRASTRUCTURE | False | 300.0 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
| bench-p05-bridge-bearing-aging | DEV_CONTAMINATED | intervention-proposal | INVENTION_REQUIRES_EXPERIMENT | True | 193.9 | False | False | GENERATION_NO_OPERATOR_CONTRACT | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
| bench-p09-packaging-barrier | DEV_CONTAMINATED | intervention-proposal | INCOMPLETE_INFRASTRUCTURE | False | 300.0 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
| eval-sofc-thermal-cycling | None | intervention-proposal | INCOMPLETE_INFRASTRUCTURE | False | 300.0 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
| eval-new02-slipring-predictor | None | predictor-design | INVENTION_UNDER_DEVELOPMENT | True | 209.8 | False | False | GENERATION_NO_OPERATOR_CONTRACT | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
| eval-new06-bearing-vibration-predictor | None | predictor-design | INVENTION_REQUIRES_EXPERIMENT | True | 298.3 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
| eval-new09-hvac-filter-predictor | None | predictor-design | INVENTION_REQUIRES_EXPERIMENT | True | 189.2 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
