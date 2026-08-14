# RECOVERY ARTIFACT CONSISTENCY REPORT

## Objective

Make every representation of AIC:V1:p0002 consistent with HISTORICAL_RECOVERY_V1_1.

## Required Final State

| Field | Value |
|-------|-------|
| recovery_status | RECOVERED_CANDIDATE_PENDING_ADVERSARIAL |
| aic_promotion | BLOCKED |
| adversarial.overall | KILLED |
| All 7 dimensions | KILLED |
| recovered_AIC | 0 |
| recovered_candidate | 1 |

## Fixes Applied

- HISTORICAL_RECOVERY_V1.json: p0002 recovery_status RECOVERED_AIC → RECOVERED_CANDIDATE_PENDING_ADVERSARIAL
- HISTORICAL_RECOVERY_V1.json: p0002 aic adversarial overall PASS → KILLED
- HISTORICAL_RECOVERY_V1.json: p0002 mechanism_validity UNKNOWN → KILLED
- HISTORICAL_RECOVERY_V1.json: p0002 transfer_validity UNKNOWN → KILLED
- HISTORICAL_RECOVERY_V1.json: p0002 boundary_failure UNKNOWN → KILLED
- HISTORICAL_RECOVERY_V1.json: p0002 obvious_combination UNKNOWN → KILLED
- HISTORICAL_RECOVERY_V1.json: p0002 engineering_feasibility UNKNOWN → KILLED
- HISTORICAL_RECOVERY_V1.json: p0002 regulatory_feasibility UNKNOWN → KILLED
- HISTORICAL_RECOVERY_V1.json: p0002 falsifiability UNKNOWN → KILLED
- HISTORICAL_RECOVERY_V1.json: p0002 aic_means updated to reflect BLOCKED promotion
- HISTORICAL_RECOVERY_V1.json: report_counts.recovered_AIC 1 → 0
- HISTORICAL_RECOVERY_V1.json.sha256: updated
- AIC_V1_p0002.json: adversarial overall PASS → KILLED
- AIC_V1_p0002.json: mechanism_validity UNKNOWN → KILLED
- AIC_V1_p0002.json: transfer_validity UNKNOWN → KILLED
- AIC_V1_p0002.json: boundary_failure UNKNOWN → KILLED
- AIC_V1_p0002.json: obvious_combination UNKNOWN → KILLED
- AIC_V1_p0002.json: engineering_feasibility UNKNOWN → KILLED
- AIC_V1_p0002.json: regulatory_feasibility UNKNOWN → KILLED
- AIC_V1_p0002.json: falsifiability UNKNOWN → KILLED
- AIC_V1_p0002.json: aic_means updated to reflect BLOCKED promotion
- AIC_V1_p0002.json: added recovery_status=RECOVERED_CANDIDATE_PENDING_ADVERSARIAL
- AIC_V1_p0002.json: added aic_promotion=BLOCKED
- AIC_V1_p0002.json: saved
- HISTORICAL_RECOVERY_V1_1.json: already correct (verified)
- RECOVERY_AIC_FORENSIC.json: already correct (verified)

## Files Checked

| File | Status |
|------|--------|
| HISTORICAL_RECOVERY_V1.json | FIXED (recovery_status, adversarial, report_counts) |
| HISTORICAL_RECOVERY_V1_1.json | Already correct |
| RECOVERY_AIC_FORENSIC.json | Already correct |
| recovered_aics/AIC_V1_p0002.json | FIXED (adversarial, aic_means, added status fields) |

## Verification

The candidate (p0002) is preserved as a confirmed FALSE_PRIOR_ART_KILL — the old
LIKELY_PRIOR_ART_EXISTS was a false kill (NO_MATCH_FOUND on re-evaluation).
However, the candidate does NOT survive adversarial review (all 7 dimensions KILLED)
and is therefore NOT an AUTOMATED_INVENTION_CANDIDATE.

No nested field in any artifact claims RECOVERED_AIC or adversarial PASS.
