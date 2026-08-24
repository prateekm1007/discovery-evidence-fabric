# MSVED Frozen Candidate Specification — Round 250

**Frozen:** 2026-08-24 (Round 250, per CEO directive)
**Authority:** Article XLV-equivalent (No Package-First) + Article I (evidence precedes assertion)
**Rule:** No new wording, features, or economic claims until §103 attack is complete.

---

## 1. Mechanism (FROZEN)

**Name:** Minimum Sufficient Validation Evidence Derivation (MSVED)

**Formulation (FROZEN):**
Given a proposed ML model modification, automatically determine the minimum
sufficient validation evidence needed to establish that the modification
remains within the previously authorized safety/effectiveness envelope,
and prove why that evidence is sufficient.

**4-Link Chain (FROZEN):**
```
ML change → clinical pathway impact → risk-envelope propagation →
minimum sufficient evidence → sufficiency proof
```

**Link 1:** ML change → clinical pathways (which patient journeys, decision points, outcomes are touched)
**Link 2:** Risk-envelope propagation (how the change propagates through the clinical risk model)
**Link 3:** Minimum sufficient evidence derivation (smallest test set that proves safety within affected envelope)
**Link 4:** Sufficiency proof (formal argument why the evidence set is sufficient)

---

## 2. What is NOT Claimed (FROZEN — killed by R249 collision search)

- Pre-deployment ML validation (covered by US10810512B1, US11610152B2)
- Performance threshold checking (covered by US10810512B1)
- Regulatory evidence generation (covered by US11610152B2)
- Automated audit process (covered by WO2024200698A1)
- PCCP authoring/documentation (FDA guidance + commercial vendors exist)
- ML drift monitoring (Fiddler, Arize, WhyLabs)
- eQMS design controls (Greenlight Guru, MasterControl)

---

## 3. Economic Hypotheses (FROZEN — as hypotheses, not claims)

### Hypothesis 1: Validation burden reduction
MSVED reduces the number of validation tests required per model modification
while maintaining the same safety assurance coverage.

**Status:** UNVERIFIED. Requires killer experiment (P2).

### Hypothesis 2: Cost reduction
If Hypothesis 1 holds, the cost savings = (tests eliminated) × (cost per test).

**Status:** UNVERIFIED. Depends on buyer-specific test cost (INDUSTRY ESTIMATE, not FDA-verified).

### Hypothesis 3: Buyer willingness-to-pay
A PMA/AI-device company would pay $50k-$200k per modification cycle for MSVED
if it reduces validation burden by ≥30% while maintaining assurance.

**Status:** UNVERIFIED. 0 buyer conversations.

---

## 4. What This Freeze Means

### Permitted:
- Run the §103 attack (P1)
- Design and execute the killer experiment (P2)
- Kill MSVED if §103 fails or killer experiment fails
- Approach buyers with HONEST hypotheses (labeled as hypotheses)

### Forbidden:
- Adding new links to the chain
- Modifying the mechanism formulation
- Claiming the mechanism is novel before §103 passes
- Claiming the mechanism works before killer experiment passes
- Claiming economic value before buyer disclosure
- Adding new features to make the mechanism "sound better"

### Changes require CEO approval:
- Adding/removing links
- Modifying the sufficiency proof approach
- Updating hypotheses based on experimental/buyer data
- Claiming novelty after §103 passes
