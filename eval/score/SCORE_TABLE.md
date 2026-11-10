# eval score table (commit 77e1e3847271, dirty_tree=False, 2026-11-10T06:57:07+00:00Z)

metric: blind pairwise win-rate (pipeline vs strongest zero-paid single-shot baseline)
KPI: R506 yield funnel on DEV: mechanisms_found + candidates_generated_distinct
criteria: a=answers the asked question; b=uses user-stated variables; c=gives a specific testable prediction; d=grounded in the provided evidence; e=uses the user's clarification answer correctly

pipeline completion: 6/6
subset: dev6 (n=6)
yield funnel (DEV): {"n": 6, "completed": 6, "mechanisms_found": 6, "candidates_generated_distinct": 6, "mechanisms_rate": 1.0, "distinct_rate": 1.0, "starved": [], "starved_reasons": {}}
yield funnel (fresh): {"n": 3, "completed": 3, "mechanisms_found": 3, "candidates_generated_distinct": 3, "mechanisms_rate": 1.0, "distinct_rate": 1.0, "starved": [], "starved_reasons": {}}
wall time: {"sum_wall_s": 1226.4, "mean_wall_s": 204.4, "max_wall_s": 269.9, "mean_stage_s": {"ADJUDICATION": 0.03, "ATTACK": 45.67, "CLASSIFY": 0.05, "COLLISION": 12.18, "CONTRADICTION": 0.01, "FREEZE": 0.05, "KILLER_EXPERIMENT": 0.03, "MECHANISM_SPACE": 43.01, "NEXT_BEST_ACTION": 0.02, "PHYSICS": 0.39, "PREMISE_GATE": 0.01, "RANK": 0.02, "RETRIEVE": 44.96, "SYNTHESIZE": 28.73, "VERIFY": 0.03}}
speed: {"n": 6, "p50_wall_s": 224.4, "p95_wall_s": 264.8, "timeout_count": 0, "budget_note": "owner budget: median ~120 s, worst ~300 s; timeouts are INCOMPLETE_INFRASTRUCTURE"}
baseline route: agnes / agnes-3.0-flash (OK)
judge route: xkiro / mistralai/ministral-14b (different provider+family from baseline; not 1.7B)
judge calibration: 0.967 (n=30, passed=True)

n usable pairs (completed pipeline only): 3/6
pipeline wins 0  baseline wins 2  ties 1

**BLIND PAIRWISE WIN-RATE: 0.167** (0.566 CI half-width)

fresh vs contaminated: {"DEV_CONTAMINATED": {"n": 3, "completed": 3, "usable": 2, "win_rate": 0.25}, "FRESH": {"n": 3, "completed": 3, "usable": 1, "win_rate": 0.0}}
criterion mean diffs (pipeline-baseline): {"a_answered": -0.833, "b_user_vars": -0.167, "c_prediction": -0.667, "d_evidence": -1.167, "e_clarification": null}

| problem | tag | type | final_status | completed | wall_s | mech | distinct | starved_reason | winner | crit diffs |
|---|---|---|---|---|---|---|---|---|---|---|
| bench-p02-leadacid-grid-corrosion | DEV_CONTAMINATED | intervention-proposal | INVENTION_REQUIRES_EXPERIMENT | True | 269.9 | True | True | None | baseline | {"a_answered": -1.5, "b_user_vars": -0.5, "c_prediction": -1.0, "d_evidence": -1.5, "e_clarification": null} |
| bench-p05-bridge-bearing-aging | DEV_CONTAMINATED | intervention-proposal | INVENTION_REQUIRES_EXPERIMENT | True | 249.7 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null} |
| bench-p09-packaging-barrier | DEV_CONTAMINATED | intervention-proposal | INVENTION_REQUIRES_EXPERIMENT | True | 228.2 | True | True | None | tie | {"a_answered": -0.5, "b_user_vars": 0.0, "c_prediction": -0.5, "d_evidence": -1.0, "e_clarification": null} |
| eval-new02-slipring-predictor | None | predictor-design | INVENTION_REQUIRES_EXPERIMENT | True | 220.7 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null} |
| eval-new06-bearing-vibration-predictor | None | predictor-design | INVENTION_REQUIRES_EXPERIMENT | True | 115.3 | True | True | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null} |
| eval-new09-hvac-filter-predictor | None | predictor-design | INVENTION_REQUIRES_EXPERIMENT | True | 142.6 | True | True | None | baseline | {"a_answered": -0.5, "b_user_vars": 0.0, "c_prediction": -0.5, "d_evidence": -1.0, "e_clarification": null} |
