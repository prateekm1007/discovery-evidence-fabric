# Model Calibration V1 — Report

**Status**: Both conditions CALIBRATION_BLOCKED

## Summary

| Condition | Model | Accuracy | 103 Acc | 103 Prec | False Reject |
|---|---|---|---|---|---|
| A (Gemma) | gemma-4-31b-it | 15.0% | 75.0% | 83.3% | 75.0% |
| B (Nemotron) | nemotron-3.5-lightning-30b | 75.0% | 15.0% | 0.0% | 0.0% |

## Conclusion

Neither model alone passes the acceptance gate. See MODEL_COMPARISON.md for details.

## Next Steps

- Condition C (ensemble) not yet run — requires Gemma+Nemotron pipeline
- The ensemble may combine Gemma's evidence-finding with Nemotron's conservatism

STOP FOR CEO AUDIT.