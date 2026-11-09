# eval score table (commit 8b8ed70b85b1, 2026-11-09T14:04:23+00:00Z)

metric: blind pairwise win-rate (pipeline vs strongest zero-paid single-shot baseline)
criteria: a=answers the asked question; b=uses user-stated variables; c=gives a specific testable prediction; d=grounded in the provided evidence

baseline route: localqwen / qwen3-1.7b (OK)
judge route: localqwen / qwen3-1.7b

n usable pairs: 0/18  pipeline wins 0  baseline wins 0  ties 0

**BLIND PAIRWISE WIN-RATE: None** (None CI half-width)

criterion mean diffs (pipeline-baseline): {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null}

| problem | type | final_status | fallback_gen1 | same ev | winner | crit diffs |
|---|---|---|---|---|---|---|
| bench-p01-pemfc-dehydration | intervention-proposal | RUN_BLOCKED_CAPABILITY | None | False | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null} |
| bench-p02-leadacid-grid-corrosion | intervention-proposal | None | None | False | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null} |
| bench-p03-phe-biofouling | intervention-proposal | None | None | False | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null} |
| bench-p04-pump-cavitation | intervention-proposal | None | None | False | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null} |
| bench-p05-bridge-bearing-aging | intervention-proposal | None | None | False | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null} |
| bench-p06-water-biofilm | intervention-proposal | None | None | False | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null} |
| bench-p07-cgm-biofouling | intervention-proposal | None | None | False | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null} |
| bench-p08-mems-stiction | intervention-proposal | None | None | False | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null} |
| bench-p09-packaging-barrier | intervention-proposal | None | None | False | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null} |
| bench-p10-pv-pid | intervention-proposal | None | None | False | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null} |
| bench-p11-spindle-thermal-drift | intervention-proposal | None | None | False | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null} |
| bench-p12-mbr-fouling | intervention-proposal | None | None | False | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null} |
| eval-sofc-redox | intervention-proposal | None | None | False | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null} |
| eval-new01-supercap-dryout | intervention-proposal | None | None | False | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null} |
| eval-new02-slipring-predictor | predictor-design | None | None | False | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null} |
| eval-new03-insulin-pump-occlusion | intervention-proposal | None | None | False | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null} |
| eval-new04-chiller-fouling-predictor | predictor-design | None | None | False | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null} |
| eval-new05-liion-balance-drift | intervention-proposal | None | None | False | None | {"a_answered": null, "b_user_vars": null, "c_prediction": null, "d_evidence": null} |
