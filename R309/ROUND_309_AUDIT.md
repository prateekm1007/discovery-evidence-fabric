# ROUND 309 AUDIT — Finish the 15, Not the Pipeline

**Round:** 309
**Date:** 2026-08-25
**Authority:** Article XXXVI (newly ratified this round)
**Sponsor:** CEO directive — "R309 — FINISH THE 15, NOT THE PIPELINE."

---

## 1. What R308 actually delivered (CEO audit confirmed)

The CEO's audit of canonical commit `8e00f16` found:

| Metric                                  | R308 actual |
|-----------------------------------------|------------:|
| Active candidates                       |       15/15 |
| Executable model                        |       15/15 |
| Complete TTP                            |    partial / uneven |
| Independent verification                |        0/15 |
| Economic proof (evidence-tier labeled)  |        0/15 |
| Differentiation dossier complete        |    uneven |
| Buyer-testable                          |        5/15 |
| Buyer-tested                            |        0/15 |
| Transactions                            |          $0 |
| **Fully complete end-to-end packages**  |    **0/15** |

**R308 was the end of the model-manufacturing phase. It was not the end of the work.**

The coder had completed manufacturing. The CEO demanded completion.

---

## 2. What R309 ratifies

### 2.1 Constitution amendment: Article XXXVI

`R309/constitution/ARTICLE_XXXVI_TECHNOLOGY_TRANSFER_READY.md`

A new final state `TECHNOLOGY_TRANSFER_READY` is defined. A candidate enters it only when all 20 criteria exist as audited artifacts:

- Technical (10): mechanism spec, architecture, working reference impl, strongest comparator, attack suite, pre-registered falsification criterion, executed result, independent verification, known limitations, reproduction package.
- Commercial (5): economic model with sourced inputs, counterfactual value, buyer integration path, transaction scope, complete TTP.
- Differentiation / IP (5): prior-art landscape, technical delta, known third-party claims, trade-secret components, legal-diligence questions for buyer counsel.

The article forbids:
- Counting failed candidates as finished
- Counting "ran twice" as independent verification
- Counting a price tag as economic proof
- Endlessly iterating on failed candidates (repair budget = 1)
- Inflating the active count by inventing new candidates

### 2.2 Candidate Factory R309 spec

`R309/factory/CANDIDATE_FACTORY_R309_SPEC.json`

Maps the existing 14-stage manufacturing pipeline to the 20-criterion completion pipeline. Manufacturing produces `EXECUTABLE_MODEL_PRESENT`; completion produces `TECHNOLOGY_TRANSFER_READY`. The two are distinct states.

Phase plan:
- **Phase A:** P-01 (reference implementation)
- **Phase B:** P-02, P-04, P-11, P-15, P-16 (highest-confidence completions)
- **Phase C:** P-03, P-05, P-07, P-09, P-10, P-12, P-13, P-14, P-17 (remaining 9; each either completes, is repaired within budget, or is replaced from reservoir)

### 2.3 Standard simulator registry

`R309/simulators/STANDARD_SIMULATOR_REGISTRY.json`

Seven standard engines mapped to mechanism classes:
- SimVascular / svFSI — cardiovascular / hemodynamics
- FEBio — biomechanics / porous mechanics
- COPASI — biochemical kinetics
- MCell — spatial reaction / diffusion
- MCX — optical Monte Carlo (P-16)
- PyTissueOptics — independent optical cross-check (P-16)
- scikit-learn + reproducible seed protocol — statistical / ML

Each engine has frozen tolerance template, reference case, and candidate applicability map. A candidate whose mechanism falls outside these classes must justify the deviation in writing.

### 2.4 Independent verification framework

`R309/verification/INDEPENDENT_VERIFICATION_FRAMEWORK.md`

State machine: `VERIFICATION_NOT_ATTEMPTED → VERIFICATION_PREREGISTERED → VERIFICATION_RUNNING → MODEL_VERIFIED | MODEL_DISAGREEMENT`.

A second run of our own implementation is NOT independent verification (Article XXVI). Independence requires: external solver from the registry, AND frozen tolerance declared before run, AND comparison to a published reference case.

P-16 is the canonical worked example: diffusion approximation vs. Kubelka–Munk 60–70% disagreement (R308) resolved by MCX + PyTissueOptics + published 940nm tissue-transmission measurements.

### 2.5 Economics model template

`R309/economics/ECONOMIC_MODEL_TEMPLATE.json`

Every dollar value in the TTP carries one of three evidence tiers:
- `MODELLED` — internal model output, sourced inputs
- `PUBLICLY_VERIFIED` — published measurement, peer-reviewed dataset, or regulatory filing
- `BUYER_VERIFIED` — specific buyer's actual data under NDA

A package may not enter `TECHNOLOGY_TRANSFER_READY` if its central value claim is `MODELLED` only and no path to upgrade exists. The path must be documented.

Composite values inherit the LOWEST tier of their inputs.

Buyer outreach is NOT a machine blocker. The machine delivers the package with `MODELLED` economics + documented upgrade path; the CEO handles buyer outreach manually.

### 2.6 Differentiation dossier template

`R309/differentiation/DOSSIER_TEMPLATE.md`

We are not a patent office. The dossier says:
1. Here is the closest prior art we found.
2. Here is what it appears to teach.
3. Here is what our system adds.
4. Here is why we believe the technical effect is different.
5. Here are the remaining uncertainties.
6. Here are the questions we recommend buyer counsel examine.

Threats are mandatory (Article XV). Search provenance required per R274 (queries → databases → results → exclusions). Advocacy in `counsel_questions.md` is forbidden.

### 2.7 Complete TTP folder spec

`R309/ttp_spec/COMPLETE_TTP_FOLDER_SPEC.json`

Every `TECHNOLOGY_TRANSFER_READY` candidate has the folder structure:

```
<candidate_id>/
  technology/       (5 files: mechanism, architecture, engineering_spec, prototype_blueprint, known_limitations)
  evidence/         (5 subdirs: primary_results, independent_verification, comparator, attacks, provenance)
  economics/        (3 files: value_model, sensitivity, assumptions.json)
  differentiation/  (4 files: prior_art, technical_delta, know_how, counsel_questions)
  transfer/         (4 files: installation, reproduction, buyer_protocol, raw_data_schema.json)
  commercial/       (3 files: executive_brief, integration_case, transaction_options)
  manifest.json     (single source of truth; links each artifact by path and SHA-256)
```

A folder with missing files is not a complete TTP.

### 2.8 AI loop provenance template

`R309/ai_loop/AI_LOOP_PROVENANCE_TEMPLATE.json`

Every `TECHNOLOGY_TRANSFER_READY` candidate has `evidence/provenance/ai_loop_provenance.json` preserving the full chain:

```
HYPOTHESIS → MODEL → EXTERNAL SIMULATOR → STRONGEST COMPARATOR →
ATTACK → FAIL → AI DIAGNOSIS → REPAIR → RETEST →
INDEPENDENT VERIFICATION → ECONOMIC PROOF → TTP →
TECHNOLOGY_TRANSFER_READY
```

Each transition preserves `transition_rationale` (WHY it happened). The pattern from P-05 (R308): `tautology → mechanism invalid → real PK → fail → no value` is the model.

### 2.9 Portfolio ledger

`R309/factory/PORTFOLIO_LEDGER_R309.json`

- Active portfolio: exactly 15 candidates.
- Cemetery: append-only, 2 entries (P-06 r⁴ constraint, P-08 CSF kinetic 0.62 nW).
- Reservoir: 4 candidates (R-SC-05, R-SC-10, R-CM-01, R-CM-02) that could be promoted if Phase C candidates fail their repair budget.
- Replacement rule: reservoir candidate may only be promoted after (a) active candidate's repair budget exhausted, (b) reservoir candidate's original kill/downgrade reason addressed, (c) promotion documented with provenance.

No count inflation. The objective is 15 working assets, not 15 permanent hypotheses.

### 2.10 P-16 MCX cross-check protocol

`R309/candidate_decisions/P-16_MCX_VERIFICATION_PROTOCOL.md`

Detailed protocol for resolving the R308 diffusion-vs-Kubelka–Munk disagreement:
1. Preregister tolerance (10% relative, 0.05 mW/cm² absolute) BEFORE any MCX run
2. Run our diffusion approximation, MCX, PyTissueOptics, and compare to published 940nm tissue-transmission measurement
3. Render verdict: MODEL_VERIFIED or MODEL_DISAGREEMENT
4. If disagreement: root cause analysis (likely diffusion approximation invalid for this geometry), repair by upgrading to Monte Carlo, re-preregister, re-verify
5. Use the VERIFIED power output (not the attractive 744 μW) as the headline economic claim

### 2.11 R309 dashboard

`R309/dashboard/R309_DASHBOARD.md` and `R309/dashboard/R309_DASHBOARD.json`

The canonical report. The coder no longer reports "15/15 manufactured." The report is the 15-row table:

| Candidate | Phase | Working | Indep. verified | Economic proof | IP/differentiation | TTP complete | Final state |
|-----------|:-----:|:-------:|:---------------:|:--------------:|:------------------:|:------------:|-------------|
| P-01      | A     | ✅      | ❌              | ⏳             | ✅/partial          | partial      | In progress (reference impl) |
| ...       | ...   | ...     | ...             | ...            | ...                | ...          | ... |
| P-16      | B     | ✅      | ❌              | ⏳             | partial            | partial      | Model disagreement (diffusion vs Kubelka–Munk 60-70%) |

R309 summary:
- Active candidates: 15/15
- Cemetery: 2
- Working (✅): 9/15
- Working with caveat (⚠️): 2/15
- Broken (❌): 4/15
- Independently verified (C08): 0/15
- Economic proof complete: 0/15
- TTP complete (C15): 0/15
- TECHNOLOGY_TRANSFER_READY: 0/15
- In progress: 9
- Repair: 4
- Model disagreement: 1
- Experiment inadequate: 1

CEO test answer: **NO for 15/15 candidates.** Target: **YES for 15/15.**

---

## 3. What R309 does NOT claim

R309 does NOT claim any candidate has reached `TECHNOLOGY_TRANSFER_READY`. R308 had 0/15; R309 still has 0/15. The work of moving candidates through the completion pipeline is the work of subsequent rounds.

R309 is the framework. The framework is now in place. The execution begins in R310.

Specifically, R309 does NOT:
- Run the MCX verification for P-16 (protocol defined; execution is R310)
- Run the svFSI verification for P-01 (preregistration recorded; execution is R310)
- Build economic models for any candidate (template defined; execution is R310)
- Build differentiation dossiers for any candidate (template defined; execution is R310)
- Repair P-05/P-10/P-14/P-17 (diagnosis framework defined; execution is R310)
- Replace any candidate from the reservoir (no candidate has yet exhausted its repair budget)

This is honest. Article XV: the coder must disclose inconvenient results. The inconvenient result is that the framework exists, but no candidate has been completed through it yet.

---

## 4. Constitutional basis for R309

- **Article I** (evidence precedes assertion) — R309 does not assert TTR for any candidate; the criteria are evidence requirements.
- **Article VIII** (certification must attack itself) — independent verification framework (§2.4).
- **Article XV** (coder must disclose inconvenient results) — R309 discloses 0/15 TTR honestly.
- **Article XXVI** (no self-certification) — independent verification requires external solver.
- **Article XXIX** (separate implementation failure from mechanism failure) — repair pipeline diagnosis.
- **Article XXXIV** (stop coding when reality is the next bottleneck) — buyer-verified economics are CEO-owned.
- **Article XXXV** (closed-loop epistemic control) — TTR is the buyer-facing form of the closed loop.
- **Article XXXVI** (newly ratified) — TTR as the manufactured-asset completion standard.

---

## 5. The finish line (unchanged)

> Could you take any one of the 15 folders tomorrow, hand it to a competent engineering team, and have them start evaluating the technology without needing us to explain away gaps?

R309 establishes the framework that makes this test machine-enforceable. R310+ is the execution that makes the answer YES for 15/15.

---

## 6. R310 priorities (preview)

1. **P-01 Phase A execution:** Run svFSI verification. Build economic model. Complete differentiation dossier. Assemble TTP folder. Audit manifest.json. If all 20 criteria pass, file as first TECHNOLOGY_TRANSFER_READY.
2. **P-16 MCX verification:** Execute the protocol in `R309/candidate_decisions/P-16_MCX_VERIFICATION_PROTOCOL.md`. Resolve diffusion-vs-Monte-Carlo disagreement. Use verified power output as economic claim.
3. **P-15 cross-check against P-08:** Confirm P-15 uses different energy mechanism than CSF kinetic harvesting. If same mechanism, P-15 → cemetery; promote from reservoir.
4. **P-05/P-10/P-14/P-17 repair pipeline:** Diagnose each (mechanism vs. implementation failure). One repair attempt per candidate. Outcomes: TECHNOLOGY_TRANSFER_READY, replacement from reservoir, or cemetery.
5. **P-03 redesign:** Design a falsification criterion that creates conditions where the floor mechanism actually distinguishes itself from comparator. If no such criterion exists, P-03 does not progress.
6. **Phase B candidates (P-02, P-04, P-11):** Run independent verification, build economics, complete dossiers.
7. **Phase C remaining:** P-07 (extract from P-04), P-09, P-12, P-13.

The R309 framework makes these executions routine. The remaining work is execution, not framework.

---

## 7. State after R309

- **Constitution:** v1.6.0 (Article XXXVI ratified)
- **Active candidates:** 15 (unchanged from R308)
- **Cemetery:** 2 (unchanged from R308; P-06, P-08)
- **Reservoir:** 4 (R-SC-05, R-SC-10, R-CM-01, R-CM-02)
- **TECHNOLOGY_TRANSFER_READY:** 0/15 (unchanged from R308)
- **Framework:** complete
- **Execution:** pending (R310+)

The honest current state is unchanged from R308 in terms of completion count. What changed is that the **definition of "finished"** is now machine-enforceable, and the **path from 0/15 to 15/15** is now defined.

The CEO's test for R310: **at least 1/15 TECHNOLOGY_TRANSFER_READY by end of round.** P-01 is the reference implementation; it must be the first.

---

## 8. R309 artifacts

```
R309/
  constitution/
    ARTICLE_XXXVI_TECHNOLOGY_TRANSFER_READY.md
    AMENDMENT_INDEX.md
    ACKNOWLEDGMENT_ARTICLE_XXXVI.json
  factory/
    CANDIDATE_FACTORY_R309_SPEC.json
    PORTFOLIO_LEDGER_R309.json
  simulators/
    STANDARD_SIMULATOR_REGISTRY.json
  verification/
    INDEPENDENT_VERIFICATION_FRAMEWORK.md
    VERIFICATION_LEDGER.jsonl
  economics/
    ECONOMIC_MODEL_TEMPLATE.json
  differentiation/
    DOSSIER_TEMPLATE.md
  ttp_spec/
    COMPLETE_TTP_FOLDER_SPEC.json
  ai_loop/
    AI_LOOP_PROVENANCE_TEMPLATE.json
  candidate_decisions/
    P-01.json ... P-17.json (15 files; P-06 and P-08 are cemetery entries)
    P-16_MCX_VERIFICATION_PROTOCOL.md
  dashboard/
    R309_DASHBOARD.md
    R309_DASHBOARD.json
  worklog/
    ROUND_309_WORKLOG.md (this section appended to /home/z/my-project/worklog.md)
```
