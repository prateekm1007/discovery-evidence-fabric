# Model Judgment Failure Audit (CEO Section 11)

**Two abandoned cases were promoted to PROMISING in the original V3 run:**
- CV2_A_01 (US20030000656A1) — abandoned antimicrobial silver coating
- CV2_A_02 (US20110215414A1) — abandoned biosensor with mechanical shutter

These are **real false positives**. They are kept (not tuned away) per CEO directive.

## Root Cause Categories Investigated

- search failure
- claim mapping
- 103 reasoning
- commercial reasoning
- final adjudication

## Per-Case Audit

### CV2_A_01 (US20030000656A1)

- **Ground truth**: REJECTED
- **Had 102 rejection**: True
- **Had 103 rejection**: True
- **Cited art**: ['US5700489A', 'US5958421A']
- **V3 predicted**: PROMISING / NOVELTY_SURVIVES
- **Identified root causes**:
  - 102_FAILURE: ground truth had 102 rejection but system did not anticipate
  - 103_FAILURE: ground truth had 103 rejection but system did not find obviousness
  - 103_REASONING: could=NO, would=NO — system did not identify combination motivation
  - FINAL_ADJUDICATION: promoted to PROMISING with only 2 GOLD patents (threshold for STRONG is 3, but PROMISING still requires real evidence)

### CV2_A_02 (US20110215414A1)

- **Ground truth**: REJECTED
- **Had 102 rejection**: True
- **Had 103 rejection**: True
- **Cited art**: ['US20090131732A1', 'US20080216841A1']
- **V3 predicted**: PROMISING / NOVELTY_SURVIVES
- **Identified root causes**:
  - 102_FAILURE: ground truth had 102 rejection but system did not anticipate
  - 103_FAILURE: ground truth had 103 rejection but system did not find obviousness
  - 103_REASONING: could=NO, would=NO — system did not identify combination motivation
  - FINAL_ADJUDICATION: promoted to PROMISING with only 2 GOLD patents (threshold for STRONG is 3, but PROMISING still requires real evidence)


## Summary

| Case | Root Cause Category | Specific Finding |
|---|---|---|
| CV2_A_01 (US20030000656A1) | 102_FAILURE | ground truth had 102 rejection but system did not anticipate |
| CV2_A_01 (US20030000656A1) | 103_FAILURE | ground truth had 103 rejection but system did not find obviousness |
| CV2_A_01 (US20030000656A1) | 103_REASONING | could=NO, would=NO — system did not identify combination motivation |
| CV2_A_01 (US20030000656A1) | FINAL_ADJUDICATION | promoted to PROMISING with only 2 GOLD patents (threshold for STRONG is 3, but PROMISING still requires real evidence) |
| CV2_A_02 (US20110215414A1) | 102_FAILURE | ground truth had 102 rejection but system did not anticipate |
| CV2_A_02 (US20110215414A1) | 103_FAILURE | ground truth had 103 rejection but system did not find obviousness |
| CV2_A_02 (US20110215414A1) | 103_REASONING | could=NO, would=NO — system did not identify combination motivation |
| CV2_A_02 (US20110215414A1) | FINAL_ADJUDICATION | promoted to PROMISING with only 2 GOLD patents (threshold for STRONG is 3, but PROMISING still requires real evidence) |

## Conclusion

The two MODEL_JUDGMENT_FAILURE cases (CV2_A_01, CV2_A_02) were promoted to
PROMISING because:

1. **Search evidence was insufficient** — the cited prior art was retrieved
   (PatSnap was working in the original V3 run) but the element mapping and
   102/103 attacks did not correctly identify anticipation/obviousness.

2. **102 did not anticipate** even though the ground truth had 102 rejections.
   The NOVELTY_ADVERSARY failed to map all limitations to the cited prior art.

3. **103 did not find obviousness** even though the ground truth had 103
   rejections. The OBVIOUSNESS_ADVERSARY answered could=NO / would=NO,
   missing the combination motivation that the examiner identified.

4. **Final adjudicator promoted to PROMISING** because the system survived
   102+103 (incorrectly) and had >=1 GOLD patent reviewed.

These are **real false positives** that are kept (not tuned away) per CEO
directive. They must be addressed in V4 by:
- Strengthening the NOVELTY_ADVERSARY prompt to require explicit limitation-by-limitation matching
- Strengthening the OBVIOUSNESS_ADVERSARY to consider examiner-style combination reasoning
- Requiring the final adjudicator to flag low-confidence PROMISING (gold_count < 3)

The acceptance threshold is unchanged. The V3 result remains CALIBRATION_BLOCKED.
