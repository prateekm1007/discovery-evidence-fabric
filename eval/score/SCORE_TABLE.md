# eval score table (commit 31e2a56a693e, 2026-11-09T17:04:31+00:00Z)

metric: blind pairwise win-rate (pipeline vs strongest zero-paid single-shot baseline)
criteria: a=answers the asked question; b=uses user-stated variables; c=gives a specific testable prediction; d=grounded in the provided evidence

baseline route: localqwen / qwen3-1.7b (OK)
judge route: localqwen / qwen3-1.7b

n usable pairs: 18/18  pipeline wins 0  baseline wins 18  ties 0

**BLIND PAIRWISE WIN-RATE: 0.0** (0.231 CI half-width)

criterion mean diffs (pipeline-baseline): {"a_answered": -3.028, "b_user_vars": -3.833, "c_prediction": -3.611, "d_evidence": -3.5}

| problem | type | final_status | fallback_gen1 | same ev | winner | crit diffs |
|---|---|---|---|---|---|---|
| bench-p01-pemfc-dehydration | intervention-proposal | MECHANISM_GENERATION_FAILED | None | True | baseline | {"a_answered": -2.0, "b_user_vars": -3.5, "c_prediction": -2.5, "d_evidence": -2.5} |
| bench-p02-leadacid-grid-corrosion | intervention-proposal | MECHANISM_GENERATION_FAILED | None | True | baseline | {"a_answered": -3.0, "b_user_vars": -4.0, "c_prediction": -3.5, "d_evidence": -3.0} |
| bench-p03-phe-biofouling | intervention-proposal | MECHANISM_GENERATION_FAILED | None | True | baseline | {"a_answered": -3.5, "b_user_vars": -4.0, "c_prediction": -4.0, "d_evidence": -3.5} |
| bench-p04-pump-cavitation | intervention-proposal | MECHANISM_GENERATION_FAILED | None | True | baseline | {"a_answered": -3.5, "b_user_vars": -4.0, "c_prediction": -4.0, "d_evidence": -4.0} |
| bench-p05-bridge-bearing-aging | intervention-proposal | MECHANISM_GENERATION_FAILED | None | True | baseline | {"a_answered": -3.0, "b_user_vars": -4.0, "c_prediction": -4.0, "d_evidence": -3.5} |
| bench-p06-water-biofilm | intervention-proposal | MECHANISM_GENERATION_FAILED | None | True | baseline | {"a_answered": -3.0, "b_user_vars": -4.0, "c_prediction": -4.0, "d_evidence": -4.0} |
| bench-p07-cgm-biofouling | intervention-proposal | MECHANISM_GENERATION_FAILED | None | True | baseline | {"a_answered": -2.5, "b_user_vars": -4.0, "c_prediction": -3.5, "d_evidence": -3.5} |
| bench-p08-mems-stiction | intervention-proposal | MECHANISM_GENERATION_FAILED | None | True | baseline | {"a_answered": -3.0, "b_user_vars": -4.0, "c_prediction": -3.5, "d_evidence": -3.5} |
| bench-p09-packaging-barrier | intervention-proposal | MECHANISM_GENERATION_FAILED | None | True | baseline | {"a_answered": -3.5, "b_user_vars": -4.0, "c_prediction": -4.0, "d_evidence": -4.0} |
| bench-p10-pv-pid | intervention-proposal | MECHANISM_GENERATION_FAILED | None | True | baseline | {"a_answered": -3.5, "b_user_vars": -4.0, "c_prediction": -4.0, "d_evidence": -3.5} |
| bench-p11-spindle-thermal-drift | intervention-proposal | MECHANISM_GENERATION_FAILED | None | True | baseline | {"a_answered": -3.5, "b_user_vars": -4.0, "c_prediction": -4.0, "d_evidence": -4.0} |
| bench-p12-mbr-fouling | intervention-proposal | MECHANISM_GENERATION_FAILED | None | True | baseline | {"a_answered": -3.0, "b_user_vars": -4.0, "c_prediction": -4.0, "d_evidence": -4.0} |
| eval-sofc-redox | intervention-proposal | MECHANISM_GENERATION_FAILED | None | True | baseline | {"a_answered": -2.0, "b_user_vars": -2.5, "c_prediction": -2.5, "d_evidence": -2.5} |
| eval-new01-supercap-dryout | intervention-proposal | MECHANISM_GENERATION_FAILED | None | True | baseline | {"a_answered": -3.5, "b_user_vars": -4.0, "c_prediction": -4.0, "d_evidence": -4.0} |
| eval-new02-slipring-predictor | predictor-design | MECHANISM_GENERATION_FAILED | None | True | baseline | {"a_answered": -3.0, "b_user_vars": -3.5, "c_prediction": -3.0, "d_evidence": -3.0} |
| eval-new03-insulin-pump-occlusion | intervention-proposal | MECHANISM_GENERATION_FAILED | None | True | baseline | {"a_answered": -3.0, "b_user_vars": -4.0, "c_prediction": -3.5, "d_evidence": -3.0} |
| eval-new04-chiller-fouling-predictor | predictor-design | MECHANISM_GENERATION_FAILED | None | True | baseline | {"a_answered": -3.0, "b_user_vars": -4.0, "c_prediction": -3.5, "d_evidence": -3.5} |
| eval-new05-liion-balance-drift | intervention-proposal | MECHANISM_GENERATION_FAILED | None | True | baseline | {"a_answered": -3.0, "b_user_vars": -3.5, "c_prediction": -3.5, "d_evidence": -4.0} |
