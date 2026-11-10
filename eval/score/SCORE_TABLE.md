# eval score table (commit a7f62005f732, dirty_tree=False, 2026-11-10T06:42:22+00:00Z)

metric: blind pairwise win-rate (pipeline vs strongest zero-paid single-shot baseline)
KPI: R506 yield funnel on DEV: mechanisms_found + candidates_generated_distinct
criteria: a=answers the asked question; b=uses user-stated variables; c=gives a specific testable prediction; d=grounded in the provided evidence; e=uses the user's clarification answer correctly

pipeline completion: 6/6
subset: dev6 (n=6)
yield funnel (DEV): {"n": 6, "completed": 6, "mechanisms_found": 6, "candidates_generated_distinct": 6, "mechanisms_rate": 1.0, "distinct_rate": 1.0, "starved": [], "starved_reasons": {}}
yield funnel (fresh): {"n": 3, "completed": 3, "mechanisms_found": 3, "candidates_generated_distinct": 3, "mechanisms_rate": 1.0, "distinct_rate": 1.0, "starved": [], "starved_reasons": {}}
wall time: {"sum_wall_s": 1211.3, "mean_wall_s": 201.9, "max_wall_s": 275.7, "mean_stage_s": {"ADJUDICATION": 0.04, "ATTACK": 45.39, "CLASSIFY": 0.07, "COLLISION": 15.69, "CONTRADICTION": 0.01, "FREEZE": 0.06, "KILLER_EXPERIMENT": 0.04, "MECHANISM_SPACE": 66.1, "NEXT_BEST_ACTION": 0.03, "PHYSICS": 0.34, "PREMISE_GATE": 0.01, "RANK": 0.02, "RETRIEVE": 49.91, "SYNTHESIZE": 19.63, "VERIFY": 0.03}}
speed: {"n": 6, "p50_wall_s": 180.3, "p95_wall_s": 272.6, "timeout_count": 0, "budget_note": "owner budget: median ~120 s, worst ~300 s; timeouts are INCOMPLETE_INFRASTRUCTURE"}
baseline route: agnes / agnes-3.0-flash (OK)
judge route: xkiro / mistralai/ministral-14b (different provider+family from baseline; not 1.7B)
judge calibration: 0.967 (n=30, passed=True)

n usable pairs (completed pipeline only): 6/6
pipeline wins 0  baseline wins 5  ties 1

**BLIND PAIRWISE WIN-RATE: 0.083** (0.4 CI half-width)

fresh vs contaminated: {"DEV_CONTAMINATED": {"n": 3, "completed": 3, "usable": 3, "win_rate": 0.0}, "FRESH": {"n": 3, "completed": 3, "usable": 3, "win_rate": 0.167}}
criterion mean diffs (pipeline-baseline): {"a_answered": -1.917, "b_user_vars": -1.5, "c_prediction": -1.5, "d_evidence": -2.583, "e_clarification": null}

| problem | tag | type | final_status | completed | wall_s | mech | distinct | starved_reason | winner | crit diffs |
|---|---|---|---|---|---|---|---|---|---|---|
| bench-p02-leadacid-grid-corrosion | DEV_CONTAMINATED | intervention-proposal | INVENTION_REQUIRES_EXPERIMENT | True | 183.1 | True | True | None | baseline | {"a_answered": -2.0, "b_user_vars": -0.5, "c_prediction": -1.5, "d_evidence": -2.0, "e_clarification": null} |
| bench-p05-bridge-bearing-aging | DEV_CONTAMINATED | intervention-proposal | INVENTION_REQUIRES_EXPERIMENT | True | 177.5 | True | True | None | baseline | {"a_answered": -2.0, "b_user_vars": -1.0, "c_prediction": -2.0, "d_evidence": -3.5, "e_clarification": null} |
| bench-p09-packaging-barrier | DEV_CONTAMINATED | intervention-proposal | INVENTION_REQUIRES_EXPERIMENT | True | 263.5 | True | True | None | baseline | {"a_answered": -1.5, "b_user_vars": -1.0, "c_prediction": -0.5, "d_evidence": -2.0, "e_clarification": null} |
| eval-new02-slipring-predictor | None | predictor-design | INVENTION_REQUIRES_EXPERIMENT | True | 153.0 | True | True | None | baseline | {"a_answered": -2.0, "b_user_vars": -2.0, "c_prediction": -2.0, "d_evidence": -3.5, "e_clarification": null} |
| eval-new06-bearing-vibration-predictor | None | predictor-design | INVENTION_REQUIRES_EXPERIMENT | True | 275.7 | True | True | None | baseline | {"a_answered": -3.5, "b_user_vars": -4.0, "c_prediction": -2.5, "d_evidence": -4.0, "e_clarification": null} |
| eval-new09-hvac-filter-predictor | None | predictor-design | INVENTION_REQUIRES_EXPERIMENT | True | 158.5 | True | True | None | tie | {"a_answered": -0.5, "b_user_vars": -0.5, "c_prediction": -0.5, "d_evidence": -0.5, "e_clarification": null} |
