# eval score table (commit 2505e43b9003, dirty_tree=True, 2026-11-11T03:25:43+00:00Z)

metric: blind pairwise win-rate (pipeline vs strongest zero-paid single-shot baseline)
KPI: R506 yield funnel on DEV: mechanisms_found + candidates_generated_distinct
criteria: a=answers the asked question; b=uses user-stated variables; c=gives a specific testable prediction; d=grounded in the provided evidence; e=uses the user's clarification answer correctly; f=gives a specific, non-obvious design (not the generic default)

pipeline completion: 7/7
subset: dev6 (n=7)
yield funnel (DEV): {"n": 7, "completed": 7, "mechanisms_found": 7, "candidates_generated_distinct": 7, "mechanisms_rate": 1.0, "distinct_rate": 1.0, "starved": [], "starved_reasons": {}}
yield funnel (fresh): {"n": 4, "completed": 4, "mechanisms_found": 4, "candidates_generated_distinct": 4, "mechanisms_rate": 1.0, "distinct_rate": 1.0, "starved": [], "starved_reasons": {}}
wall time: {"sum_wall_s": 1510.1, "mean_wall_s": 215.7, "max_wall_s": 236.9, "mean_stage_s": {"ADJUDICATION": 0.03, "ATTACK": 25.05, "CLASSIFY": 0.03, "COLLISION": 11.27, "CONTRADICTION": 0.02, "FREEZE": 0.04, "KILLER_EXPERIMENT": 0.02, "MECHANISM_SPACE": 42.37, "NEXT_BEST_ACTION": 0.02, "PHYSICS": 0.37, "PREMISE_GATE": 0.01, "RANK": 0.02, "RETRIEVE": 80.26, "SYNTHESIZE": 28.33, "VERIFY": 0.04}}
speed: {"n": 7, "p50_wall_s": 236.1, "p95_wall_s": 236.8, "timeout_count": 0, "budget_note": "owner budget: median ~120 s, worst ~300 s; timeouts are INCOMPLETE_INFRASTRUCTURE"}
baseline route: None / None (None)
judge route: None / None (different provider+family from baseline; not 1.7B)
judge calibration: None (n=None, passed=None)

n usable pairs (completed pipeline only): 0/7
full scoreable pairs: 0
pairs with unverified numbers: 5
pipeline wins 0  baseline wins 0  ties 0

**SYSTEM SCORE (unconditional, all 7 problems): None**  (0 wins, 0 ties)

**CONDITIONAL QUALITY (fully scoreable pairs, calibration-gated): NOT_MEASURED**  (0W 0T NoneL over 0 pairs)

system losses (infrastructure/refusal/contract-invalid, N=7): None;  Wilson95 CI on N: (-0.0, 0.354) (method wilson_score_95)
judge outcomes: {"JUDGE_VALID": 0, "JUDGE_TRANSPORT_FAILED": 7, "JUDGE_EMPTY_OUTPUT": 0, "JUDGE_PARSE_FAILED": 0, "JUDGE_CALIBRATION_FAILED": 0}
second judge: {"agree": 0, "disagree": 0, "no_route_or_invalid": 7}

fresh vs contaminated: {"DEV_CONTAMINATED": {"n": 3, "completed": 3, "usable": 0, "win_rate": "NOT_MEASURED"}, "FRESH": {"n": 4, "completed": 4, "usable": 0, "win_rate": "NOT_MEASURED"}}
criterion mean diffs (pipeline-baseline): {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty": null}
answer-shape contract: [{"problem_id": "bench-p02-leadacid-grid-corrosion", "valid": false, "violations": ["1 numeric token(s) absent from the evidence packet"]}, {"problem_id": "bench-p05-bridge-bearing-aging", "valid": false, "violations": ["intervention contract: concrete parameter not labeled EVIDENCE-BACKED or ASSUMPTION", "intervention contract: no concrete numeric parameter"]}, {"problem_id": "bench-p09-packaging-barrier", "valid": false, "violations": ["intervention contract: concrete parameter not labeled EVIDENCE-BACKED or ASSUMPTION"]}, {"problem_id": "eval-sofc-thermal-cycling", "valid": false, "violations": ["4 numeric token(s) absent from the evidence packet"]}, {"problem_id": "eval-new02-slipring-predictor", "valid": false, "violations": ["predictor contract: no 'indicator' declared", "predictor contract: no n=\u2026 sample-count stated"]}, {"problem_id": "eval-new06-bearing-vibration-predictor", "valid": false, "violations": ["1 numeric token(s) absent from the evidence packet"]}, {"problem_id": "eval-new09-hvac-filter-predictor", "valid": false, "violations": ["1 numeric token(s) absent from the evidence packet"]}]

| problem | tag | type | final_status | completed | wall_s | mech | distinct | starved_reason | winner | crit diffs |
|---|---|---|---|---|---|---|---|---|---|---|
| bench-p02-leadacid-grid-corrosion | DEV_CONTAMINATED | intervention-proposal | INVENTION_REQUIRES_EXPERIMENT | True | 236.9 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
| bench-p05-bridge-bearing-aging | DEV_CONTAMINATED | intervention-proposal | INVENTION_REQUIRES_EXPERIMENT | True | 236.4 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
| bench-p09-packaging-barrier | DEV_CONTAMINATED | intervention-proposal | INVENTION_REQUIRES_EXPERIMENT | True | 205.7 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
| eval-sofc-thermal-cycling | None | intervention-proposal | INVENTION_REQUIRES_EXPERIMENT | True | 236.1 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
| eval-new02-slipring-predictor | None | predictor-design | INVENTION_REQUIRES_EXPERIMENT | True | 207.7 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
| eval-new06-bearing-vibration-predictor | None | predictor-design | INVENTION_REQUIRES_EXPERIMENT | True | 236.3 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
| eval-new09-hvac-filter-predictor | None | predictor-design | INVENTION_REQUIRES_EXPERIMENT | True | 151.0 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
