# Round 251 Audit — MSVED-R1 Pre-Registered + KILLED + CC-04 §103

**Task ID:** R251-MSVED-R1-KILLED-CC04-103
**Agent:** main (CTO, Super Z)
**Date:** 2026-08-24

---

## 1. Pre-Registration (Frozen BEFORE Execution)

**Artifact:** `CANONICAL_STATE/R251_MSVED_R1_PREREGISTERED_AND_EXECUTED.json` (9,288 bytes, verified on disk)

### Chosen mechanism: Conformal Risk Control (Angelopoulos et al. 2024)

**Why this is NOT a threshold adjustment:** R250's MSVED used min-score > 0.5 for ALL selected tests — a union-bound sufficiency RULE. MSVED-R1 replaces the entire RULE with conformal risk control: a calibrated mean-score threshold τ derived from a held-out calibration set, guaranteeing bounded expected false rejection rate at level α.

**Mathematical reason it should fix the failure:** R250's min-score rule rejects if ANY of k tests has score < 0.5. Under independence, P(all pass) = p^k, so false rejection grows as 1 - p^k. For k=16.5, p=0.95: P(all pass) ≈ 0.43 → ~57% false rejection (observed 26% due to correlation). Conformal risk control replaces this with: accept if mean score >= τ, where τ is calibrated to ensure P(reject | safe) <= α = 0.05. This controls the EXPECTED false rejection rate directly.

### Frozen parameters

| Parameter | Value |
|---|---|
| α (risk level) | 0.05 |
| Calibration fraction | 30% |
| Calibration seed | 251 |
| Data generation seed | 250 (SAME as R250) |
| All MSVED selection parameters | SAME as R250 |

### Pre-registered decision rule

1. Assurance >= 98%
2. Tests <= BOED (<= 15.0)
3. False reject <= BOED (<= 0%)
4. No post-hoc threshold adjustment
5. Robustness: assurance >= 95% under 0.3 misspecification

**Kill rule:** If ANY condition fails → MSVED KILLED. No R2.

---

## 2. Execution Results

### Calibration

- 60 calibration modifications (25 safe, 35 unsafe)
- τ (calibrated threshold) = 0.7420
- Expected false rejection on calibration set: <= 5%

### Evaluation (140 modifications)

| Arm | Tests | False Accept | False Reject | Assurance |
|---|---|---|---|---|
| BOED | 15.0 | 0.00% | 0.00% | 100.00% |
| **MSVED-R1** | **16.5** | **0.00%** | **4.00%** | **97.86%** |

### Robustness (0.3 misspecification)

- MSVED-R1 perturbed assurance: 95.00%

---

## 3. Pre-Registered Decision: 3 of 5 Conditions FAILED

| Condition | Required | Actual | Result |
|---|---|---|---|
| 1. Assurance | >= 98% | 97.86% | ❌ FAIL |
| 2. Tests | <= 15.0 | 16.5 | ❌ FAIL |
| 3. False reject | <= 0% | 4.00% | ❌ FAIL |
| 4. No post-hoc | frozen | frozen | ✅ PASS |
| 5. Robustness | >= 95% | 95.00% | ✅ PASS |

### Verdict: MSVED KILLED

**MSVED-R1 FAILS.** The conformal risk control mechanism improved things significantly (87% → 97.86% assurance, 26% → 4% false rejection) but still fails 3 conditions:
- Assurance is 97.86% vs required 98% (missed by 0.14%)
- Tests is 16.5 vs required ≤15.0 (10% over)
- False reject is 4% vs required ≤0%

Per the pre-registered kill rule: **MSVED is KILLED. No R2.**

### What the failure tells us

The conformal mechanism fixed the false rejection problem (26% → 4%) but could not reduce the test count below BOED. MSVED's pathway-relevance-based selection uses 16.5 tests on average vs BOED's 15 — the clinical-pathway bridge does not produce a SMALLER evidence set than information-maximizing selection. The mechanism's core claim ("minimum sufficient evidence") is not achieved: MSVED selects MORE evidence, not less, while delivering WORSE assurance.

This is a **mechanism failure**, not just an implementation failure. The conformal redesign was a legitimate mechanism change (not threshold tuning), pre-registered, and it still failed. Per Article XXIX, one implementation retry was permitted; per the CEO's directive, no R2 is allowed.

---

## 4. CC-04 §103 Attack (Parallel)

**Candidate:** CC-04: Automated Sufficiency Proof Generator

**Mechanism:** Automated, modification-specific, clinical-risk-aware sufficiency proof — proving why a chosen minimal evidence set is sufficient for a modification-specific clinical safety claim.

### Components searched (8 domains)

| Domain | What exists | Gap |
|---|---|---|
| Assurance cases / GSN | Manual, not ML-specific, not tied to derived minimum evidence | Automation is the gap |
| Formal verification (SACM, Resolute) | Proves network properties, not evidence-sufficiency | Different target |
| Conformal / PAC | Population-level guarantees, not modification-specific | Wrong scope |
| Regulatory evidence frameworks | "Least burdensome" is a principle, not an algorithm | No automation |
| Safety-case generation tools | Help AUTHOR but do not DERIVE sufficiency arguments | No derivation |
| Automated test selection | Selects tests but does not PROVE sufficiency | Missing proof |
| Formal methods for ML | Proves input-robustness, not evidence-sufficiency | Different target |
| Clinical evidence synthesis | Synthesizes evidence but does not derive minimum sets | Different purpose |

### CC-04 Verdict: CONDITIONAL_SURVIVE

- **Novelty:** MARGINAL — the concept of sufficiency proof exists (assurance cases). The automation + ML-specificity + tie to derived minimum evidence is the novelty.
- **Obviousness risk:** MODERATE — a PHOSITA in assurance cases + ML would be motivated to automate.
- **What might survive:** If the sufficiency proof requires a NOVEL THEOREM (formal bound connecting evidence set to clinical risk envelope), that theorem is the inventive step. If it's just "feed evidence into GSN template," it's obvious.
- **Survival condition:** CC-04 must demonstrate a formal mathematical bound, not just structured documentation.

---

## 5. What Happens Now

### MSVED is KILLED

MSVED (CC-01) enters the cemetery as CE-019. The failure data is:
- The clinical-pathway bridge does not produce fewer tests than BOED
- The conformal sufficiency mechanism improves false rejection but does not achieve parity with BOED
- The mechanism's core claim ("minimum sufficient evidence") is not achieved

### CC-04 becomes the lead candidate

CC-04 (Automated Sufficiency Proof Generator) is now the strongest candidate because:
1. It isolates link 4 (the rarest and most defensible element)
2. It does not depend on the clinical-pathway bridge (which failed in MSVED)
3. Its §103 is CONDITIONAL_SURVIVE — depends on whether the proof is a novel theorem

### Next steps for CC-04

1. Determine whether CC-04's sufficiency proof can be a NOVEL THEOREM (not just GSN template integration)
2. If yes → implement the theorem, run killer experiment
3. If no → kill CC-04, move to next candidate

---

## 6. Updated Honest Scoreboard

| Metric | Value |
|---|---|
| Constitution | v1.5.0, 35 articles |
| Cemetery | 18 entries → **19** (MSVED added as CE-019) |
| MSVED status | **KILLED** (failed R250 killer + R251 pre-registered R1) |
| CC-04 status | CONDITIONAL_SURVIVE (§103 marginal, depends on theorem) |
| Sellable candidates | 0 |
| Transactions | $0 |
| World-Class | 0/5 |

---

## 7. The Lesson

MSVED was a promising hypothesis that failed honestly:
1. R250: first killer experiment FAIL (87% assurance, 26% false rejection)
2. R251: pre-registered conformal redesign FAIL (97.86% assurance, 4% false rejection, but still worse than BOED on all metrics)

The mechanism's core claim — "derive the MINIMUM sufficient evidence" — was not achieved. MSVED selected MORE evidence than BOED while delivering WORSE assurance. The clinical-pathway bridge, while novel, did not produce a smaller or better evidence set.

This is the commercial AI loop working as intended: a candidate was generated, attacked, tested, and killed — honestly, with pre-registered rules, and without evaluator optimization. The failure data now informs the next candidate (CC-04).

---

## 8. Artifacts Produced (ALL VERIFIED ON DISK)

| Artifact | Path | Size |
|---|---|---|
| MSVED-R1 pre-registered + executed | `CANONICAL_STATE/R251_MSVED_R1_PREREGISTERED_AND_EXECUTED.json` | 9,288 bytes |
| This Audit | `CANONICAL_STATE/ROUND_251_AUDIT.md` | (this file) |
| Script | `scripts/r251_msved_r1_preregistered.py` | (in /home/z/my-project/scripts/) |
