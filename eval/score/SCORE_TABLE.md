# eval score table (commit 765919db4be5, dirty_tree=False, 2026-11-11T11:39:36+00:00Z)

metric: blind pairwise win-rate (pipeline vs strongest zero-paid single-shot baseline)
KPI: R506 yield funnel on DEV: mechanisms_found + candidates_generated_distinct
criteria: a=answers the asked question; b=uses user-stated variables; c=gives a specific testable prediction; d=grounded in the provided evidence; e=uses the user's clarification answer correctly; f=gives a specific, non-obvious design (not the generic default)

pipeline completion: 0/1
subset: custom:1 (n=1)
yield funnel (DEV): {"n": 1, "completed": 0, "mechanisms_found": 0, "candidates_generated_distinct": 0, "mechanisms_rate": 0.0, "distinct_rate": 0.0, "starved": ["eval-sofc-thermal-cycling"], "starved_reasons": {"eval-sofc-thermal-cycling": null}}
yield funnel (fresh): {"n": 1, "completed": 0, "mechanisms_found": 0, "candidates_generated_distinct": 0, "mechanisms_rate": 0.0, "distinct_rate": 0.0, "starved": ["eval-sofc-thermal-cycling"], "starved_reasons": {"eval-sofc-thermal-cycling": null}}
wall time: {"sum_wall_s": 300.0, "mean_wall_s": 300.0, "max_wall_s": 300.0, "mean_stage_s": {}}
speed: {"n": 1, "p50_wall_s": 300.0, "p95_wall_s": 300.0, "timeout_count": 1, "budget_note": "owner budget: median ~120 s, worst ~300 s; timeouts are INCOMPLETE_INFRASTRUCTURE"}
baseline route: None / None (None)
judge route: None / None (NO_ROUTE)
judge calibration: None (n=None, passed=None)

n usable pairs (completed pipeline only): 0/0
full scoreable pairs: 0
pairs with unverified numbers: 0
pipeline wins 0  baseline wins None  ties 0

**SYSTEM SCORE (unconditional, all 1 problems): None**  (0 wins, 0 ties)

**CONDITIONAL QUALITY (fully scoreable pairs, calibration-gated): NOT_MEASURED**  (0W 0T NoneL over 0 pairs)

system losses (infrastructure/refusal/contract-invalid, N=1): None;  normal-approx CI on N: None (method normal_approx_0_0.5_1)
judge outcomes: {"JUDGE_VALID": 0, "JUDGE_TRANSPORT_FAILED": 0, "JUDGE_EMPTY_OUTPUT": 0, "JUDGE_PARSE_FAILED": 0, "JUDGE_CALIBRATION_FAILED": 0}
second judge: {"agree": 0, "disagree": 0, "no_route_or_invalid": 1}

fresh vs contaminated: {"DEV_CONTAMINATED": null, "FRESH": {"n": 1, "completed": 0, "usable": 0, "win_rate": "NOT_MEASURED"}}
criterion mean diffs (pipeline-baseline): {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty": null}
answer-shape contract: [{"problem_id": "eval-sofc-thermal-cycling", "valid": false, "violations": ["intervention contract: concrete parameter not labeled EVIDENCE-BACKED or ASSUMPTION", "intervention contract: no concrete numeric parameter", "intervention contract: no concrete test/measure named"]}]

| problem | tag | type | final_status | completed | wall_s | mech | distinct | starved_reason | winner | crit diffs |
|---|---|---|---|---|---|---|---|---|---|---|
| eval-sofc-thermal-cycling | None | intervention-proposal | INCOMPLETE_INFRASTRUCTURE | False | 300.0 | None | None | None | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null, "e_clarification": null, "f_novelty" |
