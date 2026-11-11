# eval score table (commit b7fdb2ccc944, dirty_tree=False, 2026-11-11T10:41:50+00:00Z)

metric: blind pairwise win-rate (pipeline vs strongest zero-paid single-shot baseline)
KPI: R506 yield funnel on DEV: mechanisms_found + candidates_generated_distinct
criteria: a=answers the asked question; b=uses user-stated variables; c=gives a specific testable prediction; d=grounded in the provided evidence; e=uses the user's clarification answer correctly; f=gives a specific, non-obvious design (not the generic default)

pipeline completion: 2/7
subset: dev7 (n=7)
yield funnel (DEV): {"n": 7, "completed": 2, "mechanisms_found": 4, "candidates_generated_distinct": 4, "mechanisms_rate": 0.571, "distinct_rate": 0.571, "starved": ["bench-p02-leadacid-grid-corrosion", "bench-p05-bridge-bearing-aging", "bench-p09-packaging-barrier"], "starved_reasons": {"bench-p02-leadacid-grid-corrosion": null, "bench-p05-bridge-bearing-aging": null, "bench-p09-packaging-barrier": null}}
yield funnel (fresh): {"n": 4, "completed": 2, "mechanisms_found": 4, "candidates_generated_distinct": 4, "mechanisms_rate": 1.0, "distinct_rate": 1.0, "starved": [], "starved_reasons": {}}
wall time: {"sum_wall_s": 1657.7, "mean_wall_s": 236.8, "max_wall_s": 300.0, "mean_stage_s": {"ADJUDICATION": 0.01, "ATTACK": 2.59, "CLASSIFY": 0.01, "COLLISION": 23.62, "CONTRADICTION": 0.0, "FREEZE": 0.02, "KILLER_EXPERIMENT": 0.01, "MECHANISM_SPACE": 42.66, "NEXT_BEST_ACTION": 0.01, "PHYSICS": 0.2, "PREMISE_GATE": 0.0, "RANK": 0.01, "RETRIEVE": 49.0, "SYNTHESIZE": 63.86, "VERIFY": 0.01}}
speed: {"n": 7, "p50_wall_s": 300.0, "p95_wall_s": 300.0, "timeout_count": 4, "budget_note": "owner budget: median ~120 s, worst ~300 s; timeouts are INCOMPLETE_INFRASTRUCTURE"}
baseline route: zai / glm-4-plus (OK)
judge route: zai / glm-4-plus (SHARED_FAMILY_DISCLOSED)
judge calibration: 0.733 (n=30, passed=False)

n usable pairs (completed pipeline only): 2/2
full scoreable pairs: 0
pairs with unverified numbers: 3
pipeline wins 0  baseline wins None  ties 0

**SYSTEM SCORE (unconditional, all 7 problems): None**  (0 wins, 0 ties)

**CONDITIONAL QUALITY (fully scoreable pairs, calibration-gated): NOT_MEASURED**  (0W 0T NoneL over 0 pairs)

system losses (infrastructure/refusal/contract-invalid, N=7): None;  normal-approx CI on N: None (method normal_approx_0_0.5_1)
judge outcomes: {"JUDGE_VALID": 2, "JUDGE_TRANSPORT_FAILED": 0, "JUDGE_EMPTY_OUTPUT": 0, "JUDGE_PARSE_FAILED": 0, "JUDGE_CALIBRATION_FAILED": 0}
second judge: {"agree": 0, "disagree": 0, "no_route_or_invalid": 7}

fresh vs contaminated: {"DEV_CONTAMINATED": {"n": 3, "completed": 0, "usable": 0, "win_rate": "NOT_MEASURED"}, "FRESH": {"n": 4, "completed": 2, "usable": 2, "win_rate": "NOT_MEASURED"}}
criterion mean diffs (pipeline-baseline): {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty": null}
answer-shape contract: [{"problem_id": "bench-p02-leadacid-grid-corrosion", "valid": false, "violations": ["intervention contract: concrete parameter not labeled EVIDENCE-BACKED or ASSUMPTION", "intervention contract: no concrete numeric parameter", "intervention contract: no concrete test/measure named"]}, {"problem_id": "bench-p05-bridge-bearing-aging", "valid": false, "violations": ["intervention contract: concrete parameter not labeled EVIDENCE-BACKED or ASSUMPTION", "intervention contract: no concrete numeric parameter", "intervention contract: no concrete test/measure named"]}, {"problem_id": "bench-p09-packaging-barrier", "valid": false, "violations": ["intervention contract: concrete parameter not labeled EVIDENCE-BACKED or ASSUMPTION", "intervention contract: no concrete numeric parameter", "intervention contract: no concrete test/measure named"]}, {"problem_id": "eval-sofc-thermal-cycling", "valid": false, "violations": ["9 numeric token(s) absent from the evidence packet"]}, {"problem_id": "eval-new02-slipring-predictor", "valid": false, "violations": ["predictor contract: no INDICATOR: declared", "predictor contract: no THRESHOLD: declared", "predictor contract: no VALIDATION PROTOCOL: declared", "predictor contract: no numeric threshold with units", "predictor contract: no n=\u2026 sample-count stated"]}, {"problem_id": "eval-new06-bearing-vibration-predictor", "valid": false, "violations": ["9 numeric token(s) absent from the evidence packet"]}, {"problem_id": "eval-new09-hvac-filter-predictor", "valid": false, "violations": ["8 numeric token(s) absent from the evidence packet"]}]

| problem | tag | type | final_status | completed | wall_s | mech | distinct | starved_reason | winner | crit diffs |
|---|---|---|---|---|---|---|---|---|---|---|
| bench-p02-leadacid-grid-corrosion | DEV_CONTAMINATED | intervention-proposal | INCOMPLETE_INFRASTRUCTURE | False | 300.0 | None | None | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
| bench-p05-bridge-bearing-aging | DEV_CONTAMINATED | intervention-proposal | INCOMPLETE_INFRASTRUCTURE | False | 300.0 | None | None | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
| bench-p09-packaging-barrier | DEV_CONTAMINATED | intervention-proposal | INCOMPLETE_INFRASTRUCTURE | False | 300.0 | None | None | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
| eval-sofc-thermal-cycling | None | intervention-proposal | INVENTION_REQUIRES_EXPERIMENT | True | 170.1 | True | True | None | baseline | {"a_answered": 0.0, "b_user_vars": 0.0, "c_prediction": 0.0, "d_evidence": -1.5, "e_clarification": 0.0, "f_novelty": -2 |
| eval-new02-slipring-predictor | None | predictor-design | INCOMPLETE_INFRASTRUCTURE | False | 300.0 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
| eval-new06-bearing-vibration-predictor | None | predictor-design | MECHANISM_STARVED | False | 125.5 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
| eval-new09-hvac-filter-predictor | None | predictor-design | INVENTION_REQUIRES_EXPERIMENT | True | 162.1 | True | True | None | tie | {"a_answered": 0.0, "b_user_vars": 0.0, "c_prediction": 0.0, "d_evidence": 0.0, "e_clarification": null, "f_novelty": 0. |
