# Round 252 Audit — CC-04 Theorem + Killer Test + IP Attack → KILLED

**Task ID:** R252-CC04-THEOREM-KILLER-IP
**Agent:** main (CTO, Super Z)
**Date:** 2026-08-24

---

## 1. P1 — The Theorem (Defined Before Implementation)

**Artifact:** `CANONICAL_STATE/R252_CC04_THEOREM_AND_KILLER_TEST.json` (17,734 bytes, verified on disk)

### MSES Theorem (Modification-Specific Evidence Sufficiency)

**Formal statement:** `E ⊢_A R(Δ)`

**Inputs:**
- Δ = model modification (M_old → M_new)
- R = clinical risk envelope (set of safety properties {P_1, ..., P_k})
- E = selected evidence set (test cases + results)
- A = frozen statistical assumptions (exchangeability, calibration)

**Output:** A machine-checkable proof obligation containing:
1. Per-property statistical bound (NI test on selected subset)
2. Coverage argument (no missing test that could change conclusion)
3. Multiple-testing correction (Bonferroni across properties)
4. Assumption-violation analysis (what happens if A is wrong)

### What makes it different from existing methods

| Method | What it does | How MSES differs |
|---|---|---|
| GSN | Structured narrative argument | MSES produces statistical bounds, not narrative |
| PAC/Conformal | Population-level bounds | MSES is modification-specific (takes Δ as input) |
| Non-inferiority | Single hypothesis test | MSES is composite (all properties in R simultaneously) |
| Formal verification | Proves for ALL inputs | MSES is evidential (uses test results) |
| Risk-based testing | Selects tests by risk | MSES PROVES the selection is sufficient |
| BOED | Optimizes information gain | MSES proves sufficiency (complementary) |

---

## 2. P2 — Killer Test: FAIL

### Design

Constructed E1 (insufficient: 5 tests, no subgroup coverage) vs E2 (sufficient: 15 tests, includes subgroup). The system must reject E1 and accept E2.

### Results

| Evidence Set | Verdict | P1 Sensitivity | P2 Specificity | P3 Subgroup Fairness |
|---|---|---|---|---|
| E1 (5 tests, no subgroup) | INSUFFICIENT | FAILS | FAILS | UNCOVERED |
| E2 (15 tests, with subgroup) | **INSUFFICIENT** | FAILS | FAILS | HOLDS |

### Conditions

| Condition | Required | Actual | Result |
|---|---|---|---|
| 1. Reject E1 | INSUFFICIENT | INSUFFICIENT | ✅ PASS |
| 2. Accept E2 | SUFFICIENT | **INSUFFICIENT** | ❌ **FAIL** |
| 3. Checkable proof | Machine-checkable | 6 formal elements | ✅ PASS |
| 4. ≤ baseline evidence | ≤ 15 tests | 15 tests | ✅ PASS |
| 5. Survive violated assumptions | Functions under perturbation | Produces valid verdict | ✅ PASS |

### Why E2 was incorrectly rejected

The synthetic M_new has a **deliberate subgroup regression** (tests 20-30 have 0.15 lower scores). This causes P1 (sensitivity) and P2 (specificity) to FAIL even on E2 — because M_new genuinely performs worse on those properties. The system correctly detects this, but it means E2 is NOT actually "sufficient evidence for a safe modification" — the modification IS unsafe on those properties.

**This reveals a design issue in the killer test:** I constructed E2 as "sufficient evidence" but the underlying modification is actually unsafe. The system correctly identifies this. The killer test design is flawed, not the system.

**However, per Article XXX (never optimize the evaluator):** I must NOT redesign the test to get a pass. The honest result is:
- The system correctly rejects insufficient evidence (E1)
- The system correctly rejects evidence that reveals unsafe modifications (E2, where M_new is genuinely worse)
- The system has NOT been shown to correctly ACCEPT sufficient evidence for a SAFE modification

**This is a real failure:** the killer test does not demonstrate that MSES can certify a safe modification. It only demonstrates that MSES can detect unsafe ones. Detection is necessary but not sufficient for a sufficiency proof.

---

## 3. P3 — IP Attack: KILL

### The decisive question

> Is the MSES mathematical sufficiency condition new, or merely an application of existing assurance/statistical theory to medical-device modifications?

### Component analysis

| Component | What it is | Prior art | Novelty |
|---|---|---|---|
| (a) Per-property statistical bound | NI test on selected subset | ICH E9, conformal, PAC | **NONE** — standard testing |
| (b) Coverage argument | Formal "no missing test" argument | Software coverage testing, mutation testing | **MARGINAL** — concept exists |
| (c) Multiple-testing correction | Bonferroni across properties | Bonferroni (1936), Holm (1979) | **NONE** — standard |
| (d) Assumption-violation analysis | Sensitivity to assumption breaks | Sensitivity analysis, robustness | **MARGINAL** — concept exists |

### The verdict

**The MSES theorem is an INTEGRATION of known methods, not a novel mathematical result.** Each component is standard statistical practice. The combination is engineering, not invention.

Under KSR v. Teleflex: combining known statistical methods (NI testing + coverage + Bonferroni + sensitivity analysis) to solve a problem FDA explicitly asks for (PCCP sufficiency) is **likely obvious**. A PHOSITA in regulatory statistics would be motivated to combine these and would expect success.

### What would make it novel

The theorem would be novel ONLY if it contains a NEW MATHEMATICAL RESULT — e.g.:
- A tight bound on minimum evidence set size that is BETTER than Bonferroni + NI individually
- A proof that coverage + NI produces a bound impossible with either alone
- A novel proof technique connecting clinical pathway coverage to statistical sufficiency

**The current MSES theorem has NONE of these.** It is an integration, not a theorem.

---

## 4. Final Verdict: CC-04 KILLED

### Two independent kill signals

1. **Killer test FAIL (P2):** The system cannot demonstrate it correctly accepts sufficient evidence for a safe modification. It only detects unsafe ones.
2. **IP attack KILL (P3):** The "theorem" is an integration of known methods, not a novel mathematical result. Under §103, likely obvious.

### Per CEO directive

> "If the proof is merely a structured explanation assembled from existing guarantees, KILL CC-04."

**CC-04 is exactly that.** It is killed.

### CC-04 added to cemetery as CE-020

---

## 5. What the Failure Teaches

### Lesson 1: "Sufficiency proof" without a novel theorem is just documentation

The MSES theorem looked like a formal proof but was actually a structured assembly of standard statistical methods. The CEO's test — "is this a new mathematical result or just integration?" — is the right test. Integration is engineering, not invention.

### Lesson 2: Killer tests must include a TRUE POSITIVE case

The killer test had E1 (insufficient) but E2 was not actually "sufficient for a safe modification" — it was "sufficient to detect an unsafe modification." A proper killer test needs:
- E1: insufficient evidence for a SAFE modification → system rejects (correct)
- E2: sufficient evidence for a SAFE modification → system accepts (correct)
- E3: sufficient evidence for an UNSAFE modification → system rejects (correct)

The current test only has E1 and a modified E2. This is a test design failure that must be corrected for the next candidate.

### Lesson 3: The frontier is a novel mathematical bound, not integration

Both MSVED (CE-019) and CC-04 (CE-020) failed because they were integrations of known methods, not novel mathematical results. The pattern is clear: the commercial AI loop will keep killing candidates until it finds one with a genuinely new mathematical theorem, not just a clever combination of existing techniques.

---

## 6. Updated Honest Scoreboard

| Metric | Value |
|---|---|
| Constitution | v1.5.0, 35 articles |
| Cemetery | 19 → **20** (CC-04 added as CE-020) |
| Killed this round | CC-04 (Automated Sufficiency Proof Generator) |
| Remaining candidates | CC-02, CC-03, CC-05, CC-06, CC-07, CC-08, CC-09, CC-10 (8 in discovery queue) |
| Sellable | 0 |
| Transactions | $0 |
| World-Class | 0/5 |

---

## 7. Artifacts Produced (ALL VERIFIED ON DISK)

| Artifact | Path | Size |
|---|---|---|
| CC-04 theorem + killer + IP | `CANONICAL_STATE/R252_CC04_THEOREM_AND_KILLER_TEST.json` | 17,734 bytes |
| This Audit | `CANONICAL_STATE/ROUND_252_AUDIT.md` | (this file) |
| Script | `scripts/r252_cc04_theorem_killer_ip.py` | (in /home/z/my-project/scripts/) |
