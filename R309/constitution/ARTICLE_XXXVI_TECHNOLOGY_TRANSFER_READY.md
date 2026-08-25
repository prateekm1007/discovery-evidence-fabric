# Article XXXVI — TECHNOLOGY_TRANSFER_READY as the Manufactured-Asset Completion Standard

**Ratified:** 2026-08-25 (Round 309)
**Amends:** Epistemic Constitution v1.5.0 → v1.6.0
**Authority:** Constitutional — supersedes all candidate-state, gate-result, and "manufactured" claims
**Sponsor:** CEO directive R309 — "Finish the 15, not the pipeline."

---

## 1. The correction this article makes

Round 308 closed with the repository reporting:

```
15/15 executable models
 0/15 independently verified
 5/15 technically evaluable
 5/15 buyer-testable
 0/15 buyer-tested
 7 PASS / 7 FAIL / 1 CONDITIONAL
 2 cemetery entries
```

That is the end of the **model-manufacturing phase**. It is **not** the end of the work.

> A candidate with a Python file is not a finished technology asset.
> A candidate that "passes" against its own comparator is not finished.
> A candidate whose model has never been independently reproduced is not finished.
> A candidate with no economic proof is not finished.
> A candidate with no prior-art dossier is not finished.
> A candidate with no technology-transfer package is not finished.

This article makes that distinction machine-enforced.

---

## 2. The final state

A candidate enters `TECHNOLOGY_TRANSFER_READY` **only when all twenty criteria below exist as artifacts**, each with provenance, and each independently auditable:

### Technical (10)

1. **Mechanism specification** — what the candidate is, in mechanism terms (not just an intervention description).
2. **Architecture / design** — how the mechanism is realized in components, geometry, and control law.
3. **Working reference implementation** — executable code that runs end-to-end and produces output.
4. **Strongest comparator** — the best publicly known alternative that achieves the same effect, explicitly named, not strawmanned.
5. **Attack suite** — at least three hostile attacks (functional-equivalence, prior-art, mechanism-failure) with adversarial intent.
6. **Pre-registered falsification criterion** — a quantitative pass/fail threshold declared **before** the executed result is observed.
7. **Executed result** — the actual measurement, with seeds, configs, and raw output preserved.
8. **Independent verification / cross-check** — a second implementation, by a different code path or external solver, that agrees within a frozen tolerance.
9. **Known limitations** — what the model does not capture, what was approximated, where the uncertainty lives.
10. **Reproduction package** — sufficient for a competent third party to reproduce the executed result without our assistance.

### Commercial (5)

11. **Economic model with sourced inputs** — current cost, intervention cost, deployment cost, development cost — each tied to a public or buyer-specific source.
12. **Counterfactual value calculation** — what changes for the buyer if they adopt this vs. the strongest comparator, in dollars per year, with the model that produced the number.
13. **Buyer integration path** — the concrete steps a buyer would take to integrate, validate, and deploy.
14. **Transaction scope / options** — what is being offered, at what rights level, with what exclusivity and field-of-use boundaries.
15. **Complete TTP** — the full technology-transfer package as defined in §5 below.

### Differentiation / IP (5)

16. **Prior-art landscape** — the closest published art, with citations and what each reference teaches.
17. **Argument for technical differentiation** — what our system adds, framed as a technical effect, not as a patent claim.
18. **Known third-party claims / patents that could matter** — including ones that threaten us. Disclosure is mandatory.
19. **Trade-secret / know-how components** — the parts of the package that are not in the public artifacts but are necessary to practice the invention.
20. **Explicit legal-diligence questions for buyer counsel** — open questions, not advocacy. The buyer's counsel decides; we surface.

---

## 3. What this article forbids

1. **Counting a failed candidate as finished.** `FAIL` is not a finish state. A failed candidate enters the repair pipeline (§4) or the cemetery. It does not linger in the active portfolio as "in progress" indefinitely.

2. **Counting a candidate as "verified" because it ran twice.** A second run of our own implementation is not independent verification. Independence requires a different code path, a different solver, or a published reference case.

3. **Counting a candidate as finished because it has a price tag.** "$500K" without an economic model is decorative. The economic model is the proof.

4. **Counting a candidate as finished because the coder believes it is novel.** The differentiation dossier must cite the closest prior art and the technical delta. Belief is not evidence (Article I).

5. **Endlessly iterating on a failed candidate.** Every FAIL gets a finite repair budget. After the budget is exhausted, the candidate is replaced from the existing reservoir or moved to the cemetery.

6. **Inflating the active count by inventing new candidates.** The active portfolio is fixed at 15. Replacement is permitted only when a candidate is moved to the cemetery.

---

## 4. The repair pipeline

For any candidate in `FAIL` or `CONDITIONAL`:

```
FAIL
  ↓
diagnose: mechanism failure vs. implementation failure (Article XXIX)
  ↓
repair if credible (one V iteration max, mirroring R263 successor rule)
  ↓
re-test under the same pre-registered criterion
  ↓
SUCCESS  →  TECHNOLOGY_TRANSFER_READY candidate (resume normal completion path)
FAIL     →  replacement from existing-candidate reservoir OR cemetery entry
```

**Repair budget per candidate:** one repair iteration. A second failure is terminal.

This is the operational form of the existing `SUCCESSOR_REQUIRED_WHEN_MARGINAL_NOVELTY_REMAINS_LOW` rule, extended from mechanism-novelty to model-completion.

---

## 5. The complete TTP folder structure

Every `TECHNOLOGY_TRANSFER_READY` candidate must have a folder laid out exactly as:

```
<candidate_id>/
  technology/
    mechanism.md
    architecture.md
    engineering_spec.md
    prototype_blueprint.md

  evidence/
    primary_results/
    independent_verification/
    comparator/
    attacks/
    provenance/

  economics/
    value_model.md
    sensitivity.md
    assumptions.json

  differentiation/
    prior_art.md
    technical_delta.md
    know_how.md
    counsel_questions.md

  transfer/
    installation.md
    reproduction.md
    buyer_protocol.md
    raw_data_schema.json

  commercial/
    executive_brief.md
    integration_case.md
    transaction_options.md

  manifest.json
```

The `manifest.json` is the single source of truth for that candidate's state and links each artifact by path and SHA-256.

A folder with missing files is not a complete TTP. The candidate is not `TECHNOLOGY_TRANSFER_READY`.

---

## 6. The standard simulator registry

To prevent fragile bespoke approximations (see R308 P-16: diffusion approximation vs. Kubelka–Munk, 60–70% disagreement), each candidate's reference implementation must be cross-checked against the **standard established engine** appropriate to its mechanism:

| Mechanism class                    | Standard engine                                       | Use for                                                          |
|------------------------------------|-------------------------------------------------------|------------------------------------------------------------------|
| Cardiovascular / hemodynamics      | SimVascular / svFSI                                   | Blood flow, FSI, cardiac electrophysiology, patient-specific models |
| Biomechanics / porous mechanics    | FEBio / FEBio Studio                                  | Soft-tissue FEA, porous media, contact mechanics                 |
| Biochemical kinetics               | COPASI                                                | Reaction networks, ODE/stochastic biochemical systems            |
| Spatial reaction / diffusion       | MCell                                                 | 3D molecular transport, surface reactions                        |
| Optical (NIR, tissue optics)       | MCX + PyTissueOptics + published reference data       | Monte Carlo photon transport, tissue optics validation           |
| Statistical / ML                   | scikit-learn + reproducible seed protocol             | Classifier/regression models, ablation studies                   |

A candidate whose mechanism falls into one of these classes **must** have its independent verification (criterion #8) performed using the corresponding standard engine, not a second internal implementation.

A candidate whose mechanism does not fit any of these classes must declare the closest external reference and justify the deviation in writing.

---

## 7. Verification vs. "another run"

```
OUR IMPLEMENTATION
        ↓
EXTERNAL / INDEPENDENT SOLVER  (from §6 registry)
        ↓
KNOWN REFERENCE CASE             (published benchmark or analytical solution)
        ↓
COMPARISON against FROZEN TOLERANCE
        ↓
MODEL_VERIFIED          if within tolerance
MODEL_DISAGREEMENT      if outside tolerance → AI investigates root cause
```

A model becomes `MODEL_VERIFIED` **only** when:

- The independent solver is from the §6 registry (or a justified alternative is documented).
- The tolerance was declared **before** the comparison was run (Article VIII — certification must attack itself).
- The reference case is a published benchmark, analytical solution, or experimental measurement — not our own prior result.
- The comparison passed within tolerance, with raw outputs preserved.

A model that disagrees with the independent solver becomes `MODEL_DISAGREEMENT`. The AI investigates root cause: implementation bug, model assumption, parameter mismatch, or genuine physics gap. The candidate does not progress until the disagreement is resolved and the model is re-verified.

---

## 8. Economics must be labeled by evidence tier

Every economic claim in a `TECHNOLOGY_TRANSFER_READY` package must carry one of three labels:

- `MODELLED` — derived from our internal model. Sourced inputs, but the output is a prediction, not a measurement.
- `PUBLICLY_VERIFIED` — derived from a published measurement, peer-reviewed dataset, or regulatory filing.
- `BUYER_VERIFIED` — derived from a specific buyer's actual data, under NDA, with the data source cited.

A package may not enter `TECHNOLOGY_TRANSFER_READY` if its central value claim is `MODELLED` only and no path to `PUBLICLY_VERIFIED` or `BUYER_VERIFIED` exists. The path must be documented even if the verification hasn't happened yet.

The buyer-specific value range (criterion #12) must use `BUYER_VERIFIED` inputs where available, falling back to `PUBLICLY_VERIFIED`, falling back to `MODELLED` — and each fallback is disclosed.

---

## 9. The differentiation dossier is not a patent judgment

We are not a patent office (CEO directive, R275). The dossier must say:

1. Here is the closest prior art we found.
2. Here is what it appears to teach.
3. Here is what our system adds.
4. Here is why we believe the technical effect is different.
5. Here are the remaining uncertainties.
6. Here are the questions we recommend buyer counsel examine.

That is the full extent of the dossier's job. The buyer's counsel handles legal diligence. Our job is to surface the strongest technical argument and the strongest prior-art position, not to render a patentability verdict.

---

## 10. The AI loop must be demonstrated, not asserted

For every `TECHNOLOGY_TRANSFER_READY` candidate, the provenance chain must exist as an artifact:

```
HYPOTHESIS
   ↓
MODEL
   ↓
EXTERNAL SIMULATOR             (from §6 registry)
   ↓
STRONGEST COMPARATOR
   ↓
ATTACK
   ↓
FAIL (expected on first iteration)
   ↓
AI DIAGNOSIS                   (mechanism failure vs. implementation failure)
   ↓
REPAIR
   ↓
RETEST
   ↓
INDEPENDENT VERIFICATION       (§7)
   ↓
ECONOMIC PROOF                 (§8, with evidence-tier labels)
   ↓
TTP                            (§5 folder structure)
   ↓
TECHNOLOGY_TRANSFER_READY
```

Each transition must preserve **why** it happened. The loop is not "model ran → done." The loop is "model ran → attacked → repaired → independently verified → economically proven → packaged."

The pattern demonstrated in P-05 (R308): `tautology → mechanism invalid → real PK → fail → no value` is the model. Every candidate must have an analogous provenance chain, including the candidates that succeed.

---

## 11. The portfolio discipline

- Active portfolio: **exactly 15 candidates.**
- Cemetery: append-only. A cemetery entry is a learning artifact, not a deletion.
- Replacement is permitted only when:
  - A candidate's repair budget (§4) is exhausted, AND
  - A credible replacement exists in the existing-candidate reservoir, AND
  - The replacement is not merely invented to inflate the count.
- A candidate moved to the cemetery cannot be revived without a constitutional waiver.

The objective is **15 working assets, not 15 permanent hypotheses.**

---

## 12. The dashboard

The coder must stop reporting "15/15 manufactured."

The canonical report is:

| Candidate | Working | Indep. verified | Economic proof | IP/differentiation | TTP complete | Final state |
|-----------|--------:|----------------:|---------------:|-------------------:|-------------:|-------------|
| P-01      |       ✅ |               ⏳ |              ⏳ |          ✅/partial |      partial | In progress |
| ...       |     ... |             ... |            ... |                ... |          ... | ...         |

Columns:
- **Working** — ✅ executable runs / ⚠️ runs but caveat / ❌ broken
- **Indep. verified** — ✅ §7 satisfied / ❌ not yet
- **Economic proof** — ✅ evidence-tier labeled / ⏳ in progress / —
- **IP/differentiation** — ✅/partial/—
- **TTP complete** — ✅ all §5 files / partial / —
- **Final state** — `TECHNOLOGY_TRANSFER_READY` / `In progress` / `Repair` / `MODEL_DISAGREEMENT` / `Cemetery`

The target is **15 rows at `TECHNOLOGY_TRANSFER_READY`**.

Until that is reached, "manufactured" is not a finish state.

---

## 13. The honest current state (R309 baseline)

Against the §2 criteria, the R308 portfolio is:

| Criterion                                  | R308 actual |
|--------------------------------------------|------------:|
| Active candidates                          |       15/15 |
| Executable model                           |       15/15 |
| Complete TTP                               |    partial / uneven |
| Independent verification                   |        0/15 |
| Economic proof (evidence-tier labeled)     |        0/15 |
| Differentiation dossier complete           |    uneven |
| Buyer-testable                             |        5/15 |
| Buyer-tested                               |        0/15 |
| Transactions                               |          $0 |
| **Fully complete end-to-end packages**     |    **0/15** |

This is the honest baseline. R309's job is to move as many rows as possible from "In progress" to `TECHNOLOGY_TRANSFER_READY`, starting with P-01 as the reference implementation.

---

## 14. Relationship to existing articles

- **Article I** (evidence precedes assertion) — the criteria in §2 are evidence requirements; belief that a candidate is finished is not evidence.
- **Article VIII** (certification must attack itself) — independent verification (§7) is the operational form.
- **Article XXVI** (no self-certification) — a second run of our own code is not independent verification.
- **Article XXVIII** (no silent semantic promotion) — moving a candidate from "FAIL" to "in progress" without a successful repair is forbidden.
- **Article XXIX** (separate implementation failure from mechanism failure) — the §4 diagnosis step.
- **Article XXXIV** (stop coding when reality is the next bottleneck) — buyer-verified economics (§8) require buyer contact, which is CEO-owned and not a machine blocker. The machine's job is to deliver the package the CEO can hand to a buyer.
- **Article XXXV** (closed-loop epistemic control) — `TECHNOLOGY_TRANSFER_READY` is the buyer-facing form of the closed loop. The loop must be operational before the package is finished.

---

## 15. Enforcement

This article is enforced through:

1. **Pre-commit hook** — blocks commits that claim `TECHNOLOGY_TRANSFER_READY` without the §5 folder structure and §2 criteria manifest.
2. **Dashboard generator** — the canonical report (§12) is produced from artifacts, not from claims.
3. **Constitutional review** — the existing `constitution_loader.py` surfaces this article before every coding session.
4. **Cemetery append-only log** — replacements (§11) are auditable.

A claim of `TECHNOLOGY_TRANSFER_READY` that fails audit is treated as a constitutional violation under Article XV (the coder must disclose inconvenient results) and Article XXXI (every correction creates a memory artifact).

---

## 16. The finish line

The CEO's test:

> **Could you take any one of the 15 folders tomorrow, hand it to a competent engineering team, and have them start evaluating the technology without needing us to explain away gaps?**

Until the answer is **yes for all 15**, the work is not finished.

This article makes that test machine-enforced.
