# eval score table (commit d99ee9d12ab3, dirty_tree=False, 2026-11-10T03:40:29+00:00Z)

metric: blind pairwise win-rate (pipeline vs strongest zero-paid single-shot baseline)
KPI: R506 yield funnel on DEV: mechanisms_found + candidates_generated_distinct
criteria: a=answers the asked question; b=uses user-stated variables; c=gives a specific testable prediction; d=grounded in the provided evidence; e=uses the user's clarification answer correctly

pipeline completion: 3/6
subset: dev6 (n=6)
yield funnel (DEV): {"n": 6, "completed": 3, "mechanisms_found": 3, "candidates_generated_distinct": 3, "mechanisms_rate": 0.5, "distinct_rate": 0.5, "starved": ["eval-new02-slipring-predictor", "eval-new06-bearing-vibration-predictor", "eval-new09-hvac-filter-predictor"], "starved_reasons": {"eval-new02-slipring-predictor": "GENERATION_NO_OPERATOR_CONTRACT", "eval-new06-bearing-vibration-predictor": "GENERATION_NO_OPERATOR_CONTRACT", "eval-new09-hvac-filter-predictor": "GENERATION_NO_OPERATOR_CONTRACT"}}
yield funnel (fresh): {"n": 3, "completed": 3, "mechanisms_found": 0, "candidates_generated_distinct": 0, "mechanisms_rate": 0.0, "distinct_rate": 0.0, "starved": ["eval-new02-slipring-predictor", "eval-new06-bearing-vibration-predictor", "eval-new09-hvac-filter-predictor"], "starved_reasons": {"eval-new02-slipring-predictor": "GENERATION_NO_OPERATOR_CONTRACT", "eval-new06-bearing-vibration-predictor": "GENERATION_NO_OPERATOR_CONTRACT", "eval-new09-hvac-filter-predictor": "GENERATION_NO_OPERATOR_CONTRACT"}}
wall time: {"sum_wall_s": 1610.2, "mean_wall_s": 268.4, "max_wall_s": 300.1, "mean_stage_s": {"ADJUDICATION": 0.02, "ATTACK": 32.12, "CLASSIFY": 0.05, "COLLISION": 14.84, "CONTRADICTION": 0.01, "FREEZE": 0.08, "IMPROVE": 0.02, "KILLER_EXPERIMENT": 0.03, "MECHANISM_SPACE": 70.39, "NEXT_BEST_ACTION": 0.01, "PHYSICS": 0.33, "PREMISE_GATE": 0.01, "RANK": 0.01, "RETRIEVE": 45.71, "SYNTHESIZE": 17.07, "VERIFY": 0.03}}
speed: {"n": 6, "p50_wall_s": 295.2, "p95_wall_s": 300.1, "timeout_count": 3, "budget_note": "owner budget: median ~120 s, worst ~300 s; timeouts are INCOMPLETE_INFRASTRUCTURE"}
baseline route: agnes / agnes-3.0-flash (OK)
judge route: xkiro / mistralai/ministral-14b (different provider+family from baseline; not 1.7B)
judge calibration: 1.0 (n=20, passed=True)

n usable pairs (completed pipeline only): 0/3
pipeline wins 0  baseline wins 0  ties 0

**BLIND PAIRWISE WIN-RATE: NOT_MEASURED** (None CI half-width)

fresh vs contaminated: {"DEV_CONTAMINATED": {"n": 3, "completed": 0, "usable": 0, "win_rate": "NOT_MEASURED"}, "FRESH": {"n": 3, "completed": 3, "usable": 0, "win_rate": "NOT_MEASURED"}}
criterion mean diffs (pipeline-baseline): {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null}

| problem | tag | type | final_status | completed | wall_s | mech | distinct | starved_reason | winner | crit diffs |
|---|---|---|---|---|---|---|---|---|---|---|
| bench-p02-leadacid-grid-corrosion | DEV_CONTAMINATED | intervention-proposal | INCOMPLETE_INFRASTRUCTURE | False | 300.1 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null} |
| bench-p05-bridge-bearing-aging | DEV_CONTAMINATED | intervention-proposal | INCOMPLETE_INFRASTRUCTURE | False | 300.0 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null} |
| bench-p09-packaging-barrier | DEV_CONTAMINATED | intervention-proposal | INCOMPLETE_INFRASTRUCTURE | False | 300.1 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null} |
| eval-new02-slipring-predictor | None | predictor-design | INVENTION_UNDER_DEVELOPMENT | True | 162.1 | False | False | GENERATION_NO_OPERATOR_CONTRACT | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null} |
| eval-new06-bearing-vibration-predictor | None | predictor-design | INVENTION_UNDER_DEVELOPMENT | True | 290.5 | False | False | GENERATION_NO_OPERATOR_CONTRACT | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null} |
| eval-new09-hvac-filter-predictor | None | predictor-design | INVENTION_UNDER_DEVELOPMENT | True | 257.4 | False | False | GENERATION_NO_OPERATOR_CONTRACT | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null} |
