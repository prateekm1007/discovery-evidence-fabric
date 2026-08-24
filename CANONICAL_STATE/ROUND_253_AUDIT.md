# Round 253 Audit — CC-04 Corrected Killer + Bug Fix + Gate A/B

**Task ID:** R253-CC04-CORRECTED-KILLER-BUGFIX-GATES
**Agent:** main (CTO, Super Z)
**Date:** 2026-08-24

---

## 1. CEO Correction Accepted

R252's kill of CC-04 was **invalid** because the positive control (E2) contained an unsafe modification (sensitivity=0.758, below the 0.80 threshold). The system correctly rejected an unsafe modification — that is not evidence that CC-04 cannot recognize sufficient evidence. CC-04 was NOT killed; it was `IP_THREATENED + EXPERIMENT_INVALID`.

---

## 2. P0+P1 — Corrected Test Cohort + Pre-Registration

### Three frozen test classes (independently verified BEFORE execution)

| Class | Label | M_new properties | Evidence | Ground truth verified |
|---|---|---|---|---|
| E- | UNSAFE | Sensitivity 0.769 (<0.80), subgroup regression 0.20 | 5 tests, no subgroup | ✅ verified_safe=False |
| E+ | SAFE | Sensitivity 0.828 (≥0.80), subgroup maintained | 15 tests, with subgroup | ✅ verified_safe=True |
| E± | BORDERLINE | Sensitivity 0.794 (at threshold), slight subgroup regression | 10 tests, partial subgroup | ✅ verified_safe=False |

### Pre-registration

Ground truth committed with SHA-256 hash `19af35b7...` BEFORE the proof system saw the data. E+ independently verified as SAFE before execution.

---

## 3. Bug Discovery and Fix

### The bug

When I ran the corrected test cohort, Gate A **FAILED** again — E+ (SAFE) was rejected as INSUFFICIENT. Investigation revealed the cause:

**The MSES proof checker used the WRONG statistical test.** It implemented:
```
z = diff / se
p = norm.cdf(z)  # tests H0: diff <= 0 (SUPERIORITY)
```

But non-inferiority testing (ICH E9) requires:
```
z = (diff + margin) / se  # tests H0: diff <= -margin
p = 1 - norm.cdf(z)       # upper tail
```

The superiority test asks "is the new model BETTER than the old?" (very hard to prove). The non-inferiority test asks "is the new model NOT WORSE by more than margin?" (much easier to prove, and the correct test for PCCP modifications).

### Classification: Implementation bug (Article XXIX)

This is an **implementation bug**, not a mechanism failure. The theorem (non-inferiority testing per ICH E9) was always correct. The code implementing it was wrong. Per Article XXIX, fixing an implementation bug is permitted — it is NOT the same as redesigning the mechanism or tuning the evaluator.

### The fix

Changed two lines in the proof checker:
- `z = diff / se` → `z = (diff + margin) / se`
- `p = norm.cdf(z)` → `p = 1 - norm.cdf(z)`

The theorem, test cohort, and decision rule are unchanged. Only the statistical test implementation was corrected.

---

## 4. Gate A (Scientific Mechanism) — PASS

### Results with corrected NI test

| Class | Ground Truth | System Verdict | Correct? |
|---|---|---|---|
| E- | UNSAFE | INSUFFICIENT | ✅ (P3 subgroup UNCOVERED) |
| E+ | SAFE | **SUFFICIENT** | ✅ (all properties HOLD) |
| E± | BORDERLINE | INSUFFICIENT | ✅ (P1/P2 FAIL, which is correct for borderline) |

### Gate A conditions

| Condition | Required | Actual | Result |
|---|---|---|---|
| E- correctly rejected | UNSAFE → INSUFFICIENT | UNSAFE → INSUFFICIENT | ✅ PASS |
| E+ correctly accepted | SAFE → SUFFICIENT | SAFE → **SUFFICIENT** | ✅ PASS |
| E± correctly handled | Produces a verdict | BORDERLINE → INSUFFICIENT | ✅ PASS |

**Gate A VERDICT: PASS.** The proof engine CAN correctly distinguish safe+sufficient from unsafe/insufficient evidence.

---

## 5. Gate B (IP Novelty) — FAIL

### The question

Does the MSES proof contain a NEW mathematical relationship, or does it merely chain NI + coverage + Bonferroni + sensitivity analysis?

### Component analysis (unchanged from R252)

| Component | Mathematical content | Novel? |
|---|---|---|
| (a) Per-property NI test | Standard z-test with margin (ICH E9) | NO |
| (b) Coverage argument | Set coverage check | NO |
| (c) Bonferroni correction | α/k (1936) | NO |
| (d) Assumption-violation analysis | Qualitative note | NO |

**Gate B VERDICT: FAIL.** No new mathematical relationship. The MSES theorem is an integration of known methods.

---

## 6. Combined Verdict: COMMERCIAL_TOOL_NOT_INVENTION

| Gate | Result |
|---|---|
| Gate A (scientific mechanism) | ✅ PASS |
| Gate B (IP novelty) | ❌ FAIL |
| **Combined** | **COMMERCIAL_TOOL_NOT_INVENTION** |

### What this means

Per CEO R253: "If Gate A passes but Gate B fails → COMMERCIAL TOOL, NOT INVENTION."

CC-04's proof engine **works** — it correctly distinguishes safe+sufficient from unsafe/insufficient evidence. But it contains **no novel mathematics** — it is an integration of standard statistical methods (NI testing + coverage + Bonferroni + sensitivity analysis).

### Implications

1. **Not a World-Class invention.** CC-04 cannot enter the 5-slot World-Class portfolio. The IP gate fails.

2. **Potential commercial tool.** CC-04 CAN potentially be sold as a $50K tool if buyer economics work. The buyer gets:
   - Complete technology-transfer package (14 elements)
   - Independent validation (Gate A passed on synthetic data; needs external validation)
   - Economic proof (requires buyer disclosure)
   - **IP position: trade-secret/know-how, NOT patent** (honestly disclosed)

3. **The distinction matters.** Per CEO R253: "scientifically novel ≠ patentable ≠ commercially valuable ≠ World-Class." CC-04 is:
   - NOT scientifically novel (Gate B fails)
   - NOT patentable (obvious integration)
   - POTENTIALLY commercially valuable (if buyer economics work)
   - NOT World-Class

### CC-04 is NOT killed

CC-04 is reclassified as `COMMERCIAL_TOOL_NOT_INVENTION`. It is NOT added to the cemetery. It remains in the commercial portfolio as a potential $50K tool, with the honest disclosure that its IP position is trade-secret, not patent.

---

## 7. Updated Honest Scoreboard

| Metric | Value |
|---|---|
| Constitution | v1.5.0, 35 articles |
| Cemetery | 20 entries (CE-019 MSVED, CE-020 CC-04 from R252 — but CC-04 is now RECLASSIFIED, not killed) |
| CC-04 status | **COMMERCIAL_TOOL_NOT_INVENTION** (Gate A pass, Gate B fail) |
| World-Class portfolio | 0/5 |
| Commercial candidates | 10 (CC-01 killed, CC-04 reclassified, 8 others in discovery) |
| Sellable | 0 (CC-04 needs buyer economics + independent validation) |
| Transactions | $0 |

### Correction to CE-020

CE-020 (added in R252) should be annotated: CC-04 was initially killed in R252 based on an invalid positive control. R253 corrected the test cohort and found an implementation bug. After the bug fix, Gate A passes. CC-04 is reclassified as COMMERCIAL_TOOL_NOT_INVENTION, not killed. CE-020 should be marked as "RECLASSIFIED, NOT KILLED" with a reference to R253.

---

## 8. Key Lessons from R253

1. **Test design matters.** R252's positive control was invalid (E2 was unsafe). The corrected cohort with independently verified ground truth is essential.

2. **Implementation bugs can masquerade as mechanism failures.** The NI test bug caused safe modifications to be rejected. Without the CEO's insistence on a valid positive control, I would have killed CC-04 based on a bug.

3. **The Gate A / Gate B distinction is crucial.** A mechanism can work (Gate A) without being novel (Gate B). CC-04 is a working tool that is not an invention. This is the "commercial tool, not invention" category the CEO identified.

4. **Article XXIX (implementation ≠ mechanism) was essential.** The bug fix was permitted because it was an implementation correction, not a mechanism redesign or evaluator tuning.

---

## 9. Artifacts Produced (ALL VERIFIED ON DISK)

| Artifact | Path | Size |
|---|---|---|
| Corrected killer + Gates | `CANONICAL_STATE/R253_CC04_CORRECTED_KILLER_AND_GATES.json` | 7,685 bytes |
| This Audit | `CANONICAL_STATE/ROUND_253_AUDIT.md` | (this file) |
| Script | `scripts/r253_cc04_bugfix_gates.py` | (in /home/z/my-project/scripts/) |
