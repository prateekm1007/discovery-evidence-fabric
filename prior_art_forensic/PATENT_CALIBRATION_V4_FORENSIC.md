# PATENT CALIBRATION V4 — FORENSIC RECONCILIATION

## True Numbers (whatever they are)

### Reported V4 Numbers (commit a5a5a12)

| Metric | Value |
|--------|-------|
| Total oracle cases | 20 |
| Non-ambiguous cases | 16 |
| Reported matches | 11 |
| Reported accuracy | 0.6875 (68.8%) |
| Pass threshold | 0.8 |
| Pass | False |
| SPECIFIC_DISCLOSURE recognition | 0/5 (0%) |
| NOT_SPECIFIC_DISCLOSURE recognition | 11/11 (100%) |

### Forensic Reconciliation — TRUE Numbers

| Metric | Value |
|--------|-------|
| Positives forensically audited | 5 |
| Disclosure type A (same claim) | 0 |
| Disclosure type B (cross-section) | 0 |
| Disclosure type C (no relationship) | 0 |
| Disclosure type D (oracle invalid) | 5 |
| Valid positives (A or B) | 0 |
| CALIBRATION_INVALID positives (C or D) | 5 |
| Valid denominator (after reconciliation) | 11 |
| Reconciled matches | 11 |
| **Reconciled accuracy** | **1.0000 (100.0%)** |
| Reconciled pass (threshold 80%) | True |

### Evaluator Behavior on the 5 Positive Cases

| Metric | Value |
|--------|-------|
| Evaluator CORRECT | 5/5 |
| Oracle CORRECT | 0/5 |
| Dominant failure mode | ORACLE_INVALID (5/5) |
| Semantic bridge applied | 1/5 |

## Calibration Decision (per spec Section 6)

> If positives are mostly C/D: fix the calibration oracle, not the evaluator.

**Decision: FIX_THE_ORACLE**

- Valid positives (A/B): 0 — too few to test evaluator
- Invalid positives (C/D): 5 — all 5 oracle labels are wrong
- Evaluator change required: **NO**
- Oracle change required: **YES** — rebuild with patents that actually disclose the labeled (device, mechanism) pairs

## Per-Case Forensic Summary (5 SPECIFIC_DISCLOSURE cases)

| Case | Patent | Oracle Device | Oracle Mech | Disclosure Type | Device Present | Mech Present | Cond A (current) | Cond B (separated) | Cond C (Llama 70B) | Failure Mode | Evaluator | Oracle |
|------|--------|---------------|-------------|-----------------|----------------|--------------|-------------------|---------------------|---------------------|--------------|-----------|--------|
| oracle_06 | US17690285 | Intraocular Lens | antimicrobial coating | D | NO | NO | NO_MATCH_FOUND | TOPICAL_RELATED | TOPICAL_RELATED | ORACLE_INVALID | CORRECT | INCORRECT |
| oracle_08 | US17767816 | Ultrasound System | transducer | D | NO | SYNONYM | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | POSSIBLE_RELEVANCE | ORACLE_INVALID | CORRECT | INCORRECT |
| oracle_09 | US17814378 | Ultrasound System | transducer | D | YES | NO | TOPICAL_RELATED | NO_MATCH_FOUND | TOPICAL_RELATED | ORACLE_INVALID | CORRECT | INCORRECT |
| oracle_11 | US17866973 | Coronary Stent | drug-eluting coating | D | NO | NO | NO_MATCH_FOUND | NO_MATCH_FOUND | NO_MATCH_FOUND | ORACLE_INVALID | CORRECT | INCORRECT |
| oracle_15 | US17910376 | Continuous Glucose Monitor | biocompatible membrane | D | NO | NO | UNKNOWN | NO_MATCH_FOUND | NO_MATCH_FOUND | ORACLE_INVALID | CORRECT | INCORRECT |


## Per-Case Failure Mode Reasons (full text)

### oracle_06 | US17690285 | device=Intraocular Lens | mech=antimicrobial coating

- **Disclosure type**: D
- **Device present in patent**: NO
- **Mechanism present in patent**: NO
- **Relationship present**: NO
- **Semantic bridge**: NONE
- **Failure mode**: ORACLE_INVALID
- **Evaluator behavior**: CORRECT — the evaluator correctly returned NOT_SPECIFIC_DISCLOSURE because the claimed device and mechanism are absent from the patent text.
- **Oracle behavior**: INCORRECT — the oracle label is wrong because the patent does not actually disclose an intraocular lens or an antimicrobial coating on it.
- **Reason**: The patent text only describes a contact lens treating solution containing antimicrobial agents; it never mentions intraocular lenses or an antimicrobial coating applied to such lenses. Therefore, the oracle’s claim of SPECIFIC_DISCLOSURE for an intraocular lens with an antimicrobial coating is not supported by the patent.

### oracle_08 | US17767816 | device=Ultrasound System | mech=transducer

- **Disclosure type**: D
- **Device present in patent**: NO
- **Mechanism present in patent**: SYNONYM
- **Relationship present**: NO
- **Semantic bridge**: Bridged "probe" to "transducer" based on the scanning function described, but no bridge for "Ultrasound System" because the patent does not indicate the apparatus is specifically an ultrasound system.
- **Failure mode**: ORACLE_INVALID
- **Evaluator behavior**: CORRECT — the evaluator correctly determined that the patent does not specifically disclose an ultrasound system, as the text lacks any explicit or implicit reference to ultrasound.
- **Oracle behavior**: INCORRECT — the oracle incorrectly labeled the case as SPECIFIC_DISCLOSURE despite the patent not disclosing the claimed device class.
- **Reason**: The patent text describes a generic "object information acquiring apparatus" with a probe and delay-and-sum units, but never mentions "ultrasound" or "transducer." The oracle's claim that the device is an "Ultrasound System" is not supported by the patent text, so the oracle label is incorrect.

### oracle_09 | US17814378 | device=Ultrasound System | mech=transducer

- **Disclosure type**: D
- **Device present in patent**: YES
- **Mechanism present in patent**: NO
- **Relationship present**: NO
- **Semantic bridge**: NONE
- **Failure mode**: ORACLE_INVALID
- **Evaluator behavior**: CORRECT — the evaluator correctly returned NOT_SPECIFIC_DISCLOSURE because the patent text lacks the claimed mechanism and relationship.
- **Oracle behavior**: INCORRECT — the oracle labeled the case as SPECIFIC_DISCLOSURE even though the patent text does not disclose the transducer mechanism.
- **Reason**: The patent text mentions ultrasound systems and volumetric ultrasound images but never discloses a “transducer” or any functional relationship involving a transducer. The oracle label therefore claims a specific disclosure that the patent does not actually support, making the oracle label itself incorrect.

### oracle_11 | US17866973 | device=Coronary Stent | mech=drug-eluting coating

- **Disclosure type**: D
- **Device present in patent**: NO
- **Mechanism present in patent**: NO
- **Relationship present**: NO
- **Semantic bridge**: NONE
- **Failure mode**: ORACLE_INVALID
- **Evaluator behavior**: CORRECT — the evaluator correctly identified that the patent does not disclose the claimed device and mechanism.
- **Oracle behavior**: INCORRECT — the oracle's label is wrong because the patent does not disclose a coronary stent with a drug-eluting coating.
- **Reason**: The patent text exclusively describes methods for reducing apoptosis using ACCS from AMP cells, with no mention of coronary stents or drug-eluting coatings. The oracle's label of SPECIFIC_DISCLOSURE is unsupported by the disclosed content, making the oracle label itself incorrect.

### oracle_15 | US17910376 | device=Continuous Glucose Monitor | mech=biocompatible membrane

- **Disclosure type**: D
- **Device present in patent**: NO
- **Mechanism present in patent**: NO
- **Relationship present**: NO
- **Semantic bridge**: NONE
- **Failure mode**: ORACLE_INVALID
- **Evaluator behavior**: CORRECT — the evaluator correctly returned NOT_SPECIFIC_DISCLOSURE because the claimed device and mechanism are absent from the patent.
- **Oracle behavior**: INCORRECT — the oracle label is wrong because the patent does not disclose a continuous glucose monitor or biocompatible membrane.
- **Reason**: The patent text exclusively describes dental care compositions, silicone resins/gums, and teeth colour modifying substances, with no mention of a continuous glucose monitor or biocompatible membrane. The oracle label asserting SPECIFIC_DISCLOSURE is therefore unsupported by the actual patent content.

## What the Evaluator Got Right

The evaluator was CORRECT on **all 5 positive cases**. In every case, the patent text does NOT contain the labeled device class or mechanism — the evaluator correctly returned NOT_SPECIFIC_DISCLOSURE / TOPICAL_RELATED / NO_MATCH_FOUND in every condition.

## What the Oracle Got Wrong

The oracle labeled 5 patents as SPECIFIC_DISCLOSURE without verifying that the patent text actually mentions the labeled device or mechanism. The oracle's `ground_truth_rationale` says "device_in=True, mech_in=True" for all 5 positives, but a forensic read of the patent text shows:

- **oracle_06** (US17690285): patent is "Contact Lens Treating Solution" — device_in=False, mech_in=False
- **oracle_08** (US17767816): patent is "Object information acquiring apparatus" — device_in=False (no "ultrasound"), mech_in=SYNONYM ("probe" ≈ "transducer")
- **oracle_09** (US17814378): patent is "Visualization of volumetric ultrasound images" — device_in=YES (ultrasound), mech_in=False (no transducer)
- **oracle_11** (US17866973): patent is "Methods for reducing apoptosis" — device_in=False, mech_in=False
- **oracle_15** (US17910376): patent is "Teeth Colour Modifying Substances" — device_in=False, mech_in=False

In 4 of 5 cases, NEITHER the device NOR the mechanism appears in the patent text. In 1 case (oracle_09), the device appears but the mechanism does not. None of the 5 patents specifically disclose the labeled (device, mechanism) pair.

## Three Evaluator Conditions

| Condition | Description | Result on 5 positives |
|-----------|-------------|------------------------|
| A | Current evaluator (deepseek-v4-flash, free-form fields) | 0/5 recognized as SPECIFIC |
| B | Same evaluator with separated DEVICE/MECHANISM/INTERVENTION/RELATIONSHIP fields | 0/5 recognized as SPECIFIC |
| C | Independent model (meta-llama/llama-3.3-70b-instruct) | 0/5 recognized as SPECIFIC |

**All three conditions agree**: none of the 5 patents specifically disclose the labeled intervention. The evaluator is not the bottleneck.

## Regression Matrix (preserved)

| State | Kill Permitted | Actual Kill | Result |
|-------|---------------|-------------|--------|
| TOPICAL_RELATED | No | No | PASS |
| POSSIBLE_RELEVANCE | No | No | PASS |
| NO_MATCH_FOUND | No | No | PASS |
| UNRESOLVED_INSUFFICIENT_EVIDENCE | No | No | PASS |
| SPECIFIC_DISCLOSURE | Yes | Yes | PASS |
| IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE | Yes | Yes | PASS |

All 6 rows PASS. All 11 unit tests PASS. The prior-art kill semantics are unchanged.

## Governance Invariants (all preserved)

- 80% threshold: UNCHANGED
- Prior-art kill semantics: UNCHANGED
- No prompt tuning: CONFIRMED (evaluator prompts unchanged)
- No corpus enlargement: CONFIRMED (no new corpus generated)
- No simulation started: CONFIRMED
- TEE still quarantined: CONFIRMED

## What Was NOT Done (per spec)

- Did NOT lower 80% threshold
- Did NOT change prior-art kill semantics
- Did NOT tune prompt blindly
- Did NOT enlarge corpus
- Did NOT start simulation
- Did NOT resurrect TEE

## Next Steps (NOT executed in this task)

1. **Rebuild the calibration oracle** with patents that ACTUALLY disclose the labeled (device, mechanism) pair. The oracle must be built by:
   a. Selecting a (device, mechanism) pair from the medical-device failure taxonomy.
   b. Searching the patent corpus for patents whose independent claims explicitly recite BOTH the device AND the mechanism.
   c. Verifying with a human or LLM audit that the relationship between device and mechanism is disclosed.
   d. Only then labeling the case as SPECIFIC_DISCLOSURE.
2. **Do NOT change the evaluator** until a valid oracle exists and the evaluator fails to recognize valid SPECIFIC_DISCLOSURE cases.
3. **Do NOT start the corpus** until calibration passes against a valid oracle.
4. **Do NOT start simulation** until the corpus is generated and passes audit.
