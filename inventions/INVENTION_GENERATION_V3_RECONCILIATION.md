# Invention V3 Reconciliation

Status: **PARTIAL_COMPLETION_DATA_RECONCILED**


## Summary

| Metric | Value |
|--------|-------|
| Attempt count | 20 |
| Substantive outputs | 7 |
| Operational failures | 13 |
| PASS | 1 |
| INSUFFICIENT_EVIDENCE | 6 |
| KILL | 0 |

## Normalizations Applied

- commercial_classification normalized to enum A/B/C/D/UNASSESSED
- pipeline_status normalized to INVENTION_EVALUATED/INSUFFICIENT_EVIDENCE/KILLED/PIPELINE_CALL_FAILED
- commercial_rationale separated from commercial_classification
- failed_stage recorded separately from pipeline_status
- report regenerated deterministically from manifest

## Note
13 operational failures NOT YET recovered. Recovery requires LLM re-runs with improved JSON parser.