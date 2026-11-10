# eval score table (commit 7703c4392bba, dirty_tree=True, 2026-11-10T06:16:05+00:00Z)

metric: blind pairwise win-rate (pipeline vs strongest zero-paid single-shot baseline)
KPI: R506 yield funnel on DEV: mechanisms_found + candidates_generated_distinct
criteria: a=answers the asked question; b=uses user-stated variables; c=gives a specific testable prediction; d=grounded in the provided evidence; e=uses the user's clarification answer correctly

pipeline completion: 5/6
subset: dev6 (n=6)
yield funnel (DEV): {"n": 6, "completed": 5, "mechanisms_found": 6, "candidates_generated_distinct": 6, "mechanisms_rate": 1.0, "distinct_rate": 1.0, "starved": [], "starved_reasons": {}}
yield funnel (fresh): {"n": 3, "completed": 3, "mechanisms_found": 3, "candidates_generated_distinct": 3, "mechanisms_rate": 1.0, "distinct_rate": 1.0, "starved": [], "starved_reasons": {}}
wall time: {"sum_wall_s": 1117.0, "mean_wall_s": 186.2, "max_wall_s": 300.0, "mean_stage_s": {"ADJUDICATION": 0.03, "ATTACK": 54.43, "CLASSIFY": 0.05, "COLLISION": 14.46, "CONTRADICTION": 0.02, "FREEZE": 0.09, "KILLER_EXPERIMENT": 0.03, "MECHANISM_SPACE": 27.15, "NEXT_BEST_ACTION": 0.02, "PHYSICS": 0.34, "PREMISE_GATE": 0.01, "RANK": 0.02, "RETRIEVE": 54.37, "SYNTHESIZE": 8.77, "VERIFY": 0.03}}
speed: {"n": 6, "p50_wall_s": 160.4, "p95_wall_s": 273.3, "timeout_count": 1, "budget_note": "owner budget: median ~120 s, worst ~300 s; timeouts are INCOMPLETE_INFRASTRUCTURE"}
baseline route: agnes / agnes-3.0-flash (OK)
judge route: xkiro / mistralai/ministral-14b (different provider+family from baseline; not 1.7B)
judge calibration: 1.0 (n=20, passed=True)

n usable pairs (completed pipeline only): 5/5
pipeline wins 0  baseline wins 4  ties 1

**BLIND PAIRWISE WIN-RATE: 0.1** (0.438 CI half-width)

fresh vs contaminated: {"DEV_CONTAMINATED": {"n": 3, "completed": 2, "usable": 2, "win_rate": 0.25}, "FRESH": {"n": 3, "completed": 3, "usable": 3, "win_rate": 0.0}}
criterion mean diffs (pipeline-baseline): {"a_answered": -2.0, "b_user_vars": -1.7, "c_prediction": -2.1, "d_evidence": -2.7, "e_clarification": null}

| problem | tag | type | final_status | completed | wall_s | mech | distinct | starved_reason | winner | crit diffs |
|---|---|---|---|---|---|---|---|---|---|---|
| bench-p02-leadacid-grid-corrosion | DEV_CONTAMINATED | intervention-proposal | INVENTION_REQUIRES_EXPERIMENT | True | 145.2 | True | True | None | baseline | {"a_answered": -2.0, "b_user_vars": -2.0, "c_prediction": -2.0, "d_evidence": -3.0, "e_clarification": null} |
| bench-p05-bridge-bearing-aging | DEV_CONTAMINATED | intervention-proposal | INVENTION_REQUIRES_EXPERIMENT | True | 157.6 | True | True | None | tie | {"a_answered": 0.0, "b_user_vars": 0.0, "c_prediction": -0.5, "d_evidence": -0.5, "e_clarification": null} |
| bench-p09-packaging-barrier | DEV_CONTAMINATED | intervention-proposal | INCOMPLETE_INFRASTRUCTURE | False | 300.0 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null} |
| eval-new02-slipring-predictor | None | predictor-design | INVENTION_REQUIRES_EXPERIMENT | True | 163.3 | True | True | None | baseline | {"a_answered": -3.0, "b_user_vars": -2.5, "c_prediction": -2.5, "d_evidence": -3.5, "e_clarification": null} |
| eval-new06-bearing-vibration-predictor | None | predictor-design | INVENTION_REQUIRES_EXPERIMENT | True | 193.3 | True | True | None | baseline | {"a_answered": -3.0, "b_user_vars": -2.5, "c_prediction": -3.0, "d_evidence": -3.5, "e_clarification": null} |
| eval-new09-hvac-filter-predictor | None | predictor-design | INVENTION_REQUIRES_EXPERIMENT | True | 157.6 | True | True | None | baseline | {"a_answered": -2.0, "b_user_vars": -1.5, "c_prediction": -2.5, "d_evidence": -3.0, "e_clarification": null} |
