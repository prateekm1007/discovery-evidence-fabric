# Round 250 Audit — MSVED Freeze + §103 + Killer Experiment FAIL

**Task ID:** R250-MSVED-FREEZE-103-KILLER
**Agent:** main (CTO, Super Z)
**Date:** 2026-08-24

---

## 1. P0 — MSVED FROZEN

**Artifact:** `CANONICAL_STATE/R250_MSVED_FROZEN_SPEC.md` (3,263 bytes, verified on disk)

Mechanism frozen: `ML change → clinical pathway → risk envelope → minimum sufficient evidence → sufficiency proof`. No new wording, features, or economic claims until §103 + killer experiment complete.

---

## 2. P1 — Brutal §103 Attack

### Methodology

Decomposed MSVED into 8 component domains. Built 4 explicit combinations. For each, assessed: motivation to combine, expectation of success, predictability, single-reference bridge, and whether the sufficiency proof is the inventive step.

### The 8 components

| Component | What it teaches | MSVED link |
|---|---|---|
| PCCP (FDA Dec 2024) | Requires modification methodology, validation, impact assessment | Creates the REQUIREMENT |
| ISO 14971 / FMEA | Risk-based V&V proportional to residual risk | Link 2 (risk envelope) |
| Influence functions | Maps ML change to training data subpopulations | Link 1 (partial — maps to data, not clinical pathways) |
| BOED | Selects experiments maximizing information gain | Link 3 (partial — different objective) |
| Active testing | Selects samples for performance estimation | Link 3 (partial — different objective) |
| NI testing | Tests "not worse" by pre-defined margin | Link 4 (partial — single test, not full proof) |
| Assurance cases (GSN) | Structured sufficiency argument | Link 4 (partial — manual, not ML-specific) |
| Conformal / PAC | Distribution-free coverage guarantees | Link 4 (partial — population-level, not modification-specific) |

### §103 Verdict: CONDITIONAL_SURVIVE

**The honest finding:** MSVED is MARGINAL TO WEAK under §103.

1. **Motivation is STRONG** — FDA PCCP guidance (Dec 2024) explicitly requires manufacturers to determine what validation evidence is needed. This creates direct, documented motivation to combine risk analysis + validation selection + sufficiency argument.

2. **Each component is individually known and practiced.** The 4-link chain maps directly to PCCP's own structure (modification → impact → validation → sufficiency).

3. **Under KSR v. Teleflex**, combining known components to solve a problem the market is explicitly asking for is likely obvious. "Obvious to try" is sufficient when there's a finite number of identified, predictable solutions.

### What might survive (MARGINAL)

- **Link 1 clinical bridge:** No existing tool maps ML changes to CLINICAL pathways (only to training data). But this is engineering, not invention — a PHOSITA would say "connect influence functions to a clinical ontology."
- **Link 4 modification-specific sufficiency proof:** Assurance cases + conformal/PAC cover the structure and guarantees, but no single reference ties them to a DERIVED minimum evidence set for a SPECIFIC modification. Whether this is "inventive" depends on whether the proof technique is a novel theorem or just an integration.

### What does NOT survive

- **The full chain as an integrated system** is likely obvious. PCCP provides motivation, each link is individually known, combination is predictable.
- **Link 2 (risk propagation):** ISO 14971 FMEA is standard. Automating it is engineering.
- **Link 3 (safety objective):** Reframing BOED from "info gain" to "safety sufficiency" is an objective-function change, not a new mechanism. FDA's "least burdensome" mandate already points this way.

### Survival condition

MSVED survives ONLY if the killer experiment demonstrates a TECHNICAL EFFECT that is NOT predictable from the components — i.e., MSVED produces a DIFFERENT and BETTER evidence set than BOED with the SAME assurance.

---

## 3. P2 — Killer Experiment: FAIL

**Artifact:** `CANONICAL_STATE/R250_MSVED_KILLER_EXPERIMENT_RESULTS.json` (2,493 bytes, verified on disk)

### Design

4 arms on 200 synthetic modifications (100 safe, 100 unsafe, 50 tests each):
- **A:** Conventional fixed plan (all 50 tests, accept if mean > 0.6)
- **B:** Expert risk-based (top 20 by risk weight, weighted mean > 0.6)
- **C:** BOED (top 15 by population info gain, mean > 0.6)
- **D:** MSVED (pathway-relevance-weighted selection, min score > 0.5)

### Results

| Arm | Tests | False Accept | False Reject | Assurance |
|---|---|---|---|---|
| A (conventional) | 50.0 | 0.00% | 0.00% | 100.00% |
| B (expert risk) | 20.0 | 0.00% | 0.00% | 100.00% |
| C (BOED) | 15.0 | 0.00% | 0.00% | 100.00% |
| **D (MSVED)** | **16.5** | **0.00%** | **26.00%** | **87.00%** |

### Decisive result

- D vs A: assurance diff = 13% (WORSE), burden reduction = 67% (fewer tests but worse assurance)
- D vs C (BOED): assurance diff = 13% (WORSE), burden reduction = -9.8% (MORE tests)

### Verdict: FAIL

MSVED fails 3 of 5 killer experiment conditions:
- ❌ d_same_or_better_assurance_than_a: FAIL (87% vs 100%)
- ✅ d_fewer_tests_than_a: PASS (16.5 vs 50)
- ❌ d_not_dominated_by_boed: FAIL (BOED uses fewer tests with better assurance)
- ❌ d_false_rejection_acceptable: FAIL (26% false rejection — rejecting safe modifications)
- ✅ d_false_acceptance_acceptable: PASS (0%)

**MSVED is WORSE than BOED on this synthetic test.** It uses MORE tests (16.5 vs 15) AND has WORSE assurance (87% vs 100%) AND has 26% false rejection (rejecting safe modifications that have one low-scoring test).

### Implementation vs. mechanism (Article XXIX)

Per Article XXIX (separate implementation failure from mechanism failure), this may be an implementation failure rather than a mechanism failure:

- The current MSVED implementation uses a **min-score threshold** (>0.5 for ALL selected tests) as the sufficiency check. This is extremely conservative — any single low-scoring test causes rejection.
- A real MSVED would use a **formal sufficiency proof** (e.g., non-inferiority test with pre-registered margin, or conformal risk control). The min-score threshold is a simplified proxy, not the full mechanism.
- The 26% false rejection is caused by the conservative threshold, not by the evidence-selection logic.

**However, per Article XXX (never optimize the evaluator) and Article XIX (never optimize for the gate), I must NOT tune the threshold to get a pass.** The honest result is: MSVED as currently implemented FAILS. Whether the mechanism can survive with a better sufficiency proof is an open question for the CEO to decide.

---

## 4. P3 — Commercial Loop (10 candidates ranked by EV)

**Artifact:** `CANONICAL_STATE/R250_MSVED_103_ATTACK_AND_KILLER_EXPERIMENT.json` (26,225 bytes, verified on disk)

### Ranking by expected value of next evidence acquisition

| Rank | ID | Name | EV | Note |
|---|---|---|---|---|
| 1 | CC-01 | MSVED | 0.15 | §103 conditional, killer FAIL |
| 2 | CC-04 | Automated Sufficiency Proof Generator | 0.12 | Link 4, most defensible |
| 3 | CC-02 | Clinical Pathway Change-Impact Mapper | 0.10 | Link 1, least contested |
| 4 | CC-05 | PCCP Modification Bound-Checker | 0.08 | Adjacent |
| 5 | CC-07 | Evidence Chain-of-Custody | 0.07 | Infrastructure |
| 6 | CC-06 | Subgroup Regression Detector | 0.06 | Component |
| 7 | CC-08 | Non-Inferiority Statistical Engine | 0.05 | Component, moderate collision |
| 8 | CC-09 | Clinical Risk Model Propagator | 0.04 | Link 2 |
| 9 | CC-10 | Modification Impact Assessor | 0.04 | PCCP framing |
| 10 | CC-03 | Safety-Sufficient Subset Selector | 0.03 | Highest collision risk |

---

## 5. Honest Scoreboard

| Metric | Value |
|---|---|
| Constitution | v1.5.0, 35 articles |
| Cemetery | 18 entries |
| Git HEAD | `26e83ac` (R249) → R250 pending commit |
| MSVED status | FROZEN |
| §103 verdict | CONDITIONAL_SURVIVE (marginal) |
| Killer experiment | **FAIL** (87% assurance, 26% false rejection, dominated by BOED) |
| Sellable candidates | 0 |
| Transactions | $0 |
| World-Class | 0/5 |

---

## 6. The CEO's Decision Point

MSVED has reached a critical juncture:

1. **§103 is marginal** — the full chain is likely obvious; survival depends on a non-obvious element in link 1 or link 4.
2. **Killer experiment FAILED** — the current implementation is WORSE than BOED.
3. **Article XXIX** says this may be implementation failure (conservative threshold), not mechanism failure.
4. **Article XXX** says I must NOT tune the threshold to get a pass.

### Options for the CEO:

**Option A: Kill MSVED.** The §103 is marginal and the killer experiment failed. Use the failure data to generate the next candidate. The transaction machine (buyer rejection → invention data) applies here: the synthetic experiment "rejected" MSVED, and the failure data (min-score threshold too conservative, pathway selection doesn't beat BOED) becomes input for the next candidate.

**Option B: Allow ONE redesign of the sufficiency check.** Replace the min-score threshold with a formal non-inferiority test or conformal risk control. Re-run the killer experiment. If the redesigned MSVED achieves same assurance as BOED with fewer tests → survives. If not → killed. Per Article XXIX, one implementation retry is permitted before declaring mechanism failure.

**Option C: Pivot to CC-04 (Automated Sufficiency Proof Generator).** This is link 4 alone — the rarest and most defensible element. Drop the full MSVED chain (which is likely obvious) and focus on the single element that might survive §103.

**My recommendation:** Option B (one redesign) is consistent with Article XXIX. If the redesigned sufficiency proof still fails, kill MSVED and pivot to CC-04.

---

## 7. Artifacts Produced (ALL VERIFIED ON DISK)

| Artifact | Path | Size |
|---|---|---|
| MSVED Frozen Spec | `CANONICAL_STATE/R250_MSVED_FROZEN_SPEC.md` | 3,263 bytes |
| §103 + Killer + Loop | `CANONICAL_STATE/R250_MSVED_103_ATTACK_AND_KILLER_EXPERIMENT.json` | 26,225 bytes |
| Killer Experiment Results | `CANONICAL_STATE/R250_MSVED_KILLER_EXPERIMENT_RESULTS.json` | 2,493 bytes |
| This Audit | `CANONICAL_STATE/ROUND_250_AUDIT.md` | (this file) |
| Script | `scripts/r250_msved_103_killer_loop.py` | (in /home/z/my-project/scripts/) |
