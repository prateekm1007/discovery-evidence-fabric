# Round 255 Audit — CC-08 Killed + Optimizer Fixed + NEW-HUNT + Diversified Discovery

**Task ID:** R255-CC08-KILL-OPTIMIZER-NEWHUNT
**Agent:** main (CTO, Super Z)
**Date:** 2026-08-24

---

## 1. P0 — CC-08 §103 Attack: KILLED

**No simulation. No killer experiment. Killed immediately on §103 grounds.**

### Decomposition

| Component | What it is | Prior art | Novel? |
|---|---|---|---|
| NI testing | H0: diff ≤ -margin, H1: diff > -margin | ICH E9 (1998), standard biostatistics | NO |
| ML modification context | Apply NI to old vs new model | FDA PCCP guidance (Dec 2024) explicitly requires this | NO |
| Automated reporting | Format test statistic, p-value, margin | Standard in SAS, R, Python statsmodels | NO |
| Bonferroni correction | α/k across multiple metrics | Bonferroni (1936) | NO |
| Pre-registered margins | Define margin before testing | Standard clinical trial practice (ICH E9) | NO |

### Verdict: OBVIOUS

Every component is standard statistical practice applied to the ML modification context that FDA explicitly requires. There is no new mathematical relationship, no new algorithm, no new technical effect. The "innovation" is packaging standard statistics into a tool for a specific regulatory context.

Under KSR v. Teleflex: "obvious to try" — combining known methods to solve a problem the market explicitly asks for. **KILL CC-08.**

### CC-08 added to cemetery as CE-021

---

## 2. P1 — Portfolio Optimizer Fixed

### The problem

R254 chose the "least negative" candidate (CC-08, EV=-0.1356). That is WRONG. Negative EV means validation cost exceeds expected value. Choosing the least-bad option is still choosing a bad option.

### The fix: three states

| State | Condition | Action |
|---|---|---|
| **INVEST** | EV > 0 | Proceed with evidence acquisition |
| **WATCH** | EV ≈ 0 (within ±0.05) | Monitor, do not invest. Re-evaluate when new info arrives. |
| **RESET** | ALL candidates EV < -0.05 | Invoke NEW-HUNT MODE |

### NEW-HUNT MODE

When all candidates are in RESET, the machine automatically searches for NEW candidates across **diversified domains** — not variations of the same PCCP regulatory stack.

Search criteria: high buyer pain + high internal build cost + low external evidence cost + IP/know-how can accumulate + measurable technical effect.

### Current portfolio state after fix

| Candidate | EV Score | State |
|---|---|---|
| CC-02 | -0.2362 | RESET |
| CC-03 | -0.3259 | RESET |
| CC-05 | -0.1572 | RESET |
| CC-06 | -0.2045 | RESET |
| CC-07 | -0.1374 | RESET |
| CC-08 | -0.1356 | KILLED (§103) |
| CC-09 | -0.2856 | RESET |
| CC-10 | -0.2064 | RESET |
| CC-04 | N/A | COMMERCIAL_TOOL_CANDIDATE |

**All remaining CC candidates in RESET → NEW-HUNT MODE invoked.**

---

## 3. P2 — NEW-HUNT MODE: 5 Diversified Candidates

### The 5 new candidates across 5 different domains

| ID | Domain | Name | EV Score | State |
|---|---|---|---|---|
| **NC-05** | **hospital capital equipment** | **MRI Coil Failure Predictor** | **+0.0047** | **INVEST** |
| NC-03 | clinical trial infrastructure | Adaptive Trial Futility Calculator | -0.0373 | WATCH |
| NC-01 | manufacturing / QC | Sterilization Validation Dose Auditor | -0.0634 | WATCH |
| NC-04 | IVD assay development | Assay Cross-Reactivity Predictor | -0.0816 | WATCH |
| NC-02 | implant lifecycle management | Implant Fatigue Life Predictor | -0.0822 | WATCH |

### NC-05: MRI Coil Failure Predictor from Usage Telemetry

**Mechanism:** Given MRI coil usage telemetry (scan count, gradient amplitude, patient weight, cooling cycles), predict remaining useful life and recommend preventive maintenance before failure.

**Buyer pain:** MRI coil failure costs $50K-$200K per coil + $10K-$50K/day downtime. Current maintenance is schedule-based, not predictive. No tool uses telemetry to predict failure.

**Buyer:** Hospital radiology departments + MRI service companies (Philips, Siemens, GE Healthcare)

**Why it's the first INVEST candidate:**
- EV = +0.0047 (first positive EV in the portfolio)
- High evidence feasibility (0.70): telemetry data exists, failure events are recordable
- Low validation cost (0.20): can validate on historical failure data
- Good build-vs-buy (0.65): hospitals lack ML engineering teams
- Defensible know-how (0.60): accumulated failure telemetry becomes the moat

**Novelty question:** Is telemetry-based MRI coil failure prediction novel, or just predictive maintenance applied to MRI? (To be attacked in R256)

---

## 4. P3 — CC-04 Preserved

CC-04 remains as **COMMERCIAL_TOOL_CANDIDATE_NOT_SELLABLE**. Not killed (mechanism works), not promoted (not novel). It becomes sellable only when:
1. Independent validation on real PCCP data
2. Buyer-specific economic proof
3. Defensible know-how/IP position demonstrated
4. Complete 14-element TTP

CC-04 does NOT block new candidate discovery. It sits in the portfolio as a pending commercial option.

---

## 5. Updated Honest Scoreboard

| Metric | Value |
|---|---|
| Constitution | v1.5.0, 35 articles |
| Cemetery | 20 → **21** (CE-021 CC-08 added) |
| World-Class | 0/5 |
| Commercial tool candidates | 1 (CC-04, not sellable) |
| Killed | CC-01 (MSVED), CC-08 (NI engine) |
| RESET candidates | 7 (CC-02, CC-03, CC-05, CC-06, CC-07, CC-09, CC-10) |
| New hunt candidates | 5 (NC-01..NC-05) |
| INVEST candidates | **1 (NC-05, EV=+0.0047)** |
| Sellable | 0 |
| Transactions | $0 |

### The portfolio is now diversified

| Domain | Candidates |
|---|---|
| PCCP / regulatory software | CC-02..CC-10 (all RESET, exhausted) |
| Hospital capital equipment | NC-05 (INVEST) |
| Clinical trial infrastructure | NC-03 (WATCH) |
| Manufacturing / QC | NC-01 (WATCH) |
| IVD assay development | NC-04 (WATCH) |
| Implant lifecycle management | NC-02 (WATCH) |

---

## 6. Key Insight

The portfolio was stuck in a PCCP regulatory software loop. Every candidate was a variation of "automate FDA documentation." NEW-HUNT MODE breaks the loop by searching across diversified physical domains (manufacturing, implants, clinical trials, IVD, hospital equipment).

The new candidates have HIGHER EV scores because they address **physical mechanisms with measurable technical effects**, not just documentation automation. NC-05 (MRI coil failure prediction) is the first positive-EV candidate because:
- The buyer pain is concrete ($50K-$200K per failure + downtime)
- The evidence is available (telemetry data exists, failures are recorded)
- The build cost is high for hospitals (they lack ML teams)
- The know-how accumulates (failure telemetry becomes proprietary)

---

## 7. Artifacts Produced (ALL VERIFIED ON DISK)

| Artifact | Path | Size |
|---|---|---|
| CC-08 attack + optimizer + new hunt | `CANONICAL_STATE/R255_CC08_ATTACK_OPTIMIZER_NEWHUNT.json` | 16,071 bytes |
| This Audit | `CANONICAL_STATE/ROUND_255_AUDIT.md` | (this file) |
| Script | `scripts/r255_cc08_attack_optimizer_newhunt.py` | (in /home/z/my-project/scripts/) |
