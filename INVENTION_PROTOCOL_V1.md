# INVENTION_PROTOCOL_V1

> **The Immutable Constitution for Inventions #1 through #150**
>
> This document is the standard against which every invention in this repository is adjudicated.
> No agent, coder, model, or human may bypass, soften, or interpret away the rules in this file.
> Changes to this file require the Protocol Evolution Workflow (Section 14).
>
> **Repository issue:** [#2 — ENFORCE INVENTION_PROTOCOL_V1](https://github.com/prateekm1007/discovery-evidence-fabric/issues/2)
>
> **Status:** FROZEN as of 2026-08-17
> **Version:** V1.0
> **Supersedes:** All per-invention ad-hoc procedures (V1–V8.3 of CereVasc work)
> **Applies to:** Inventions #1 through #150 (15 companies × 10 moat positions)

---

## 1. Purpose and Scope

### 1.1 Purpose

`INVENTION_PROTOCOL_V1` exists to prevent exactly the failure modes observed during the CereVasc #1 audit cycle:

- LLM-generated patent assertions treated as evidence when no primary-source passage supported it.
- 102 (novelty) attacks that actually described 103 (obviousness) combinations — silently mis-classified.
- A1's 102 status incorrectly marked "anticipated by EnClear" when in reality the analysis was a 103 motivation question — never a single-reference anticipation.
- Model-derived predictions presented without `model-derived` labels, conflated with primary-source evidence.
- Scores promoted to BUYER_READY without all hard gates passing — silent promotions.
- Patent search coverage confused with evidence coverage confused with family coverage.
- The protocol itself changed mid-run, so what passed yesterday should not have passed today.

This file ends all of that. It is the standard, not a suggestion.

### 1.2 Scope

This protocol governs every invention produced by the discovery-evidence-fabric program, including but not limited to:

- All 150 inventions across 15 companies (10 inventions per company).
- All prior-art discovery, claim analysis, 102/103 attacks, design-around analysis, engineering simulation, regulatory analysis, build-vs-buy analysis, and adjudication.
- All artifacts produced by any agent (model, subagent, or human coder) operating on an invention.
- All post-hoc audits, retractions, and re-adjudications.

### 1.3 Authority

Where any agent's behavior, prompt, or output conflicts with this file, **this file prevails**. There is no appeal path that bypasses this file except the Protocol Evolution Workflow (Section 14).

### 1.4 The Foundational Principle

> **The pipeline is standardized; the invention-specific science is not.**

Every invention traverses the same pipeline (Section 4) and produces the same mandatory artifacts (Section 6) and passes the same hard gates (Section 7). But the science inside each stage is domain-specific and chosen by the protocol at runtime, never predetermined.

For CereVasc A1, the engineering simulation happens to be membrane fouling → hydraulic resistance → ICP. For another company it might be thermal simulation, battery degradation, structural fatigue, fluid dynamics, optical propagation, pharmacokinetics, semiconductor yield, network latency, mechanical wear, energy efficiency, or manufacturing tolerance. The protocol chooses the correct simulation based on the engineering domain; it does not force Hagen-Poiseuille on a battery invention.

---

## 2. Glossary

Precise terms. Imprecise terms are forbidden in artifacts produced under this protocol.

| Term | Definition |
|---|---|
| **Limitation** | A single element of a patent claim, frozen per Section 8. Labeled L1, L2, ..., Ln. |
| **Limitation Freeze** | The immutable record of the claim's limitations and arrangement. Once frozen, cannot be edited; only superseded by a new version. |
| **Discovery Coverage** | The fraction of relevant prior-art search families that returned results. A search coverage ≥90% does NOT mean evidence coverage. |
| **Evidence Coverage** | The fraction of relevant discovered prior-art references for which primary-source claim text was retrieved and passage-mapped. Distinct from discovery coverage. |
| **Family Coverage** | The fraction of discovered references whose DOCDB/INPADOC family members were enumerated. Distinct from both discovery and evidence coverage. |
| **Primary Source** | The patent text itself (claims, specification, drawings) as published by a patent office. LLM-generated text about a patent is NOT a primary source. |
| **Passage** | A direct quotation from a primary source, with location (claim number, column, line) and content hash. |
| **Evidence ID** | A unique identifier (`E001`, `E002`, ...) assigned to every conclusion in the evidence ledger, with provenance back to a primary source or `model-derived` label. |
| **Model-Derived** | Any prediction, score, or assertion produced by an LLM or model, as distinct from primary-source evidence. Must be labeled. |
| **Hard Gate** | A scoring gate whose failure cannot be compensated by other gates. Patent Gate and Evidence Gate are non-compensable. |
| **Hard Gate Threshold** | The minimum score required to pass a hard gate. Patent ≥70, Evidence ≥70. |
| **Soft Gate** | A scoring gate whose failure may be compensated by excellence in other gates. Technical, Engineering, Commercial. |
| **Buyer-Ready** | Composite score ≥70 AND both non-compensable gates pass AND all soft gates pass their thresholds. |
| **Adjudication** | The final decision: WOULD_NOT_PAY / WOULD_CONSIDER_WITH_MILESTONES / LEVEL_4_BUYER_READY. |
| **Silent Promotion** | Marking an invention BUYER_READY without all gates passing. **Forbidden.** |
| **Provenance Chain** | The path from any conclusion back to its primary source or model-derived label. Every conclusion must have a complete provenance chain. |
| **Protocol Evolution** | The only permitted mechanism for changing this file (Section 14). |
| **Moat Position** | One of 10 deliberately selected invention slots per company. Each position is independently subjected to all gates. |
| **Portfolio** | The set of 150 Moat Positions (15 companies × 10 positions). |

---

## 3. Governance Principles

These are the immutable laws of the program. No agent may violate them.

### 3.1 The Hierarchy of Truth

1. **Primary-source patent text** is evidence.
2. **LLM-generated fact** is a hypothesis requiring validation.
3. **Keyword presence** in a patent is not claim evidence.
4. **Family member disclosure** in one country is not disclosure in another unless explicitly validated.
5. **Model-derived predictions** are labeled as such — always, without exception.

### 3.2 The Three Counts

For every prior-art reference checked against a claim, three independent counts must be recorded:

1. `keyword_match` — did the keyword appear anywhere in the patent text? (Weakest)
2. `claim_relevant` — does the keyword appear in the claim text or a claim-relevant passage? (Stronger)
3. `claim_limitations_disclosed` — does the claim actually disclose the specific limitation L1..Ln at issue? (Strongest)

A high `keyword_match` count is meaningless. A high `claim_limitations_disclosed` count is the only thing that matters for 102/103.

### 3.3 The Three Graphs

Three independent knowledge graphs are maintained per company. They are never merged:

1. **Technology Graph** — what does the prior art actually teach?
2. **Ownership Graph** — who owns what patent? (assignment, licensing, M&A)
3. **Buyer Graph** — what does the target buyer (e.g., CereVasc) own, license, or co-develop?

A single patent may appear in all three graphs, but each graph records different facts about it. Merging them creates transitive-reasoning errors.

### 3.4 Provenance Traceability

Every conclusion traces to an `evidence_id`. Every `evidence_id` traces to a primary source or a `model-derived` label. There is no conclusion without provenance. A conclusion without provenance is forbidden, not merely discouraged.

### 3.5 Distinct Coverages

Discovery coverage, evidence coverage, and family coverage are three separate measurements reported in three separate fields. They are never conflated. A 90% discovery coverage with 30% evidence coverage is a failure, not a pass.

### 3.6 Failure Permanence

Failure reasons are recorded permanently. A failed 102 attack does not disappear because the next run succeeded. The failure record stays in the evidence ledger and informs future runs.

### 3.7 No Silent Promotion

A `PROMISING` status cannot be silently promoted to `BUYER_READY`. Promotion requires all gates to pass with documented evidence pointers. The only permitted terminal statuses are:

- `WOULD_NOT_PAY` — at least one hard gate failed.
- `WOULD_CONSIDER_WITH_MILESTONES` — all gates pass, but milestone list is non-empty.
- `LEVEL_4_BUYER_READY` — all gates pass, milestone list is empty, buyer-ready threshold met.

### 3.8 Protocol Immutability Within a Run

This file cannot be edited during an invention run. If the protocol is wrong, the run completes under the current protocol, the issue is filed as a Protocol Change Proposal (Section 14), and V2 supersedes V1 only after audit.

---

## 4. The Standardized Pipeline

Every invention must traverse this pipeline. Stages may not be skipped. Stages may not be reordered.

```text
1. COMPANY CORPUS
      ↓
2. FAMILY-COMPLETE IP MAP
      ↓
3. TECHNOLOGY / OWNERSHIP / BUYER GRAPHS
      ↓
4. MOAT MAP
      ↓
5. PROBLEM SELECTION
      ↓
6. FROZEN LIMITATIONS  (LIMITATION_FREEZE.json — immutable from this point)
      ↓
7. PRIOR-ART DISCOVERY
      ↓
8. PRIMARY-SOURCE CLAIM RETRIEVAL
      ↓
9. 102 SINGLE-REFERENCE ATTACK  (one reference per attack; no combinations)
      ↓
10. 103 COMBINATION + MOTIVATION ATTACK  (explicit motivation + reasonable expectation of success)
      ↓
11. ARCHITECTURE GENERATION
      ↓
12. DESIGN-AROUND ATTACK  (≥5 alternatives, each with limitation-avoidance matrix)
      ↓
13. ENGINEERING BLUEPRINT
      ↓
14. DOMAIN-SPECIFIC SIMULATION  (chosen by the protocol; not predetermined)
      ↓
15. MANUFACTURING / REGULATORY SCREEN
      ↓
16. BUILD-vs-BUY ECONOMICS
      ↓
17. BUYER VALUE / MOAT
      ↓
18. ADJUDICATION
      ↓
WOULD_NOT_PAY  |  WOULD_CONSIDER_WITH_MILESTONES  |  LEVEL_4_BUYER_READY
```

Each stage produces a mandatory artifact (Section 6). Each artifact is hashed. Each artifact references the previous artifact's hash. The pipeline is a chain, not a checklist.

---

## 5. Stage Definitions

### 5.1 COMPANY CORPUS
Build the complete corpus of the target buyer (e.g., CereVasc): patents, applications, regulatory filings, clinical trial registrations, press releases, investor materials, conference presentations, scientific publications by employees.

### 5.2 FAMILY-COMPLETE IP MAP
Expand the corpus to include all DOCDB / INPADOC family members of every patent in the corpus. A family member in another country is prior art against the buyer's own claims if filed earlier.

### 5.3 TECHNOLOGY / OWNERSHIP / BUYER GRAPHS
Build three independent graphs (Section 3.3). Each node is a patent. Each edge is a relationship (cites, cited-by, assigned-to, licensed-to, co-owned). The graphs are never merged.

### 5.4 MOAT MAP
Identify the white space — the combinations of (buyer's existing IP) × (competitor IP) × (technology domain) that the buyer could occupy. 10 distinct positions are selected as Moat Positions for the company.

### 5.5 PROBLEM SELECTION
Pick one Moat Position as Invention #N. Document why this position was selected, what buyer pain it addresses, and what gate threshold it must clear.

### 5.6 FROZEN LIMITATIONS
Define L1..Ln — the limitations of the proposed claim — and their arrangement. This artifact (`05_LIMITATION_FREEZE.json`) is immutable from this point forward. Changes require a new version (V2, V3, ...).

### 5.7 PRIOR-ART DISCOVERY
Multi-source discovery: PatSnap (if available), EPO OPS, Google BigQuery patents, USPTO ODP, Lens.org. Each source failure is recorded with substate (PERMISSION_ERROR, HTTP_ERROR, RATE_LIMIT, NO_RESULTS). The three coverage measurements (discovery / evidence / family) are reported independently.

### 5.8 PRIMARY-SOURCE CLAIM RETRIEVAL
For every discovered reference, retrieve the actual claim text. Keyword matches in the abstract or specification are insufficient. LLM-generated paraphrases of claims are forbidden — only direct claim text counts.

### 5.9 102 SINGLE-REFERENCE ATTACK
For each limitation L1..Ln, test whether a **single** reference discloses that limitation. 102 anticipation requires **all** limitations to be present in **one** reference (or inherent to it). 102 is **never** a combination. If a 102 attack uses multiple references, it is mis-classified and must be re-run as 103.

### 5.10 103 COMBINATION + MOTIVATION ATTACK
For each reference pair (or n-tuple), document (a) the explicit motivation to combine and (b) the reasonable expectation of success. "Both known in the art" is **not** motivation. A documented reason a person of ordinary skill would combine them is required. Anti-hindsight: the motivation must exist in the prior art or in the problem statement, not in the applicant's own disclosure.

### 5.11 ARCHITECTURE GENERATION
Generate ≥5 architectural alternatives that achieve the same technical effect. Each is checked against the frozen limitations for infringement.

### 5.12 DESIGN-AROUND ATTACK
For each architectural alternative, generate ≥5 design-around variants that avoid at least one limitation. Each variant has a limitation-avoidance matrix (which L1..Ln does this avoid?) and a 102/103 motivation analysis. The strongest design-around for blocking competitors is identified.

### 5.13 ENGINEERING BLUEPRINT
Specify the engineering implementation: materials, dimensions, manufacturing process, integration with the buyer's existing device, failure modes, and worst-case boundary conditions.

### 5.14 DOMAIN-SPECIFIC SIMULATION
The protocol selects the appropriate simulation type based on the engineering domain:

```text
ENGINEERING_SIMULATION
    ├── physics model appropriate to invention
    ├── failure modes
    ├── worst-case boundary conditions
    ├── sensitivity analysis
    ├── safety constraints
    └── design modification loop
```

Examples of valid simulation domains:

- membrane fouling → hydraulic resistance → ICP (CereVasc A1)
- thermal simulation (catheter ablation)
- battery degradation (implanted electronics)
- structural fatigue (orthopedic implants)
- fluid dynamics (cardiac valves)
- optical propagation (ophthalmic devices)
- pharmacokinetics (drug-eluting devices)
- semiconductor yield (neuromodulation ASICs)
- network latency (implanted telemetry)
- mechanical wear (joint replacements)
- energy efficiency (implanted pumps)
- manufacturing tolerance (precision mechanics)

The simulation is not predetermined. The protocol inspects the engineering blueprint and selects the simulation type from the registry (Section 12). An invalid simulation choice (e.g., Hagen-Poiseuille on a battery invention) is a hard CI failure.

### 5.15 MANUFACTURING / REGULATORY SCREEN
Identify the FDA device classification, predicate analysis, combination product designation (if applicable), CNS-contact material requirements (ISO 10993 series), and required preclinical/clinical testing.

### 5.16 BUILD-vs-BUY ECONOMICS
Estimate internal development cost and timeline against acquisition cost. Identify named competitors blocked by the patent position. Classify strategic moat strength (NONE / WEAK / MEANINGFUL / STRONG / UNASSAILABLE).

### 5.17 BUYER VALUE / MOAT
Synthesize: does this invention actually serve the buyer's strategic position? Would the buyer pay to license or acquire it? The answer must be defensible to a CTO/CSO/BD executive.

### 5.18 ADJUDICATION
Score all 5 gates (Section 7). Compute composite. Issue terminal status. List milestones if any.

---

## 6. Mandatory Artifact Folder Structure

Every invention folder MUST contain these artifacts. Missing artifacts cause CI failure (Section 9).

```text
INVENTION_XXX/
├── 00_MANIFEST.json                 ← lists every artifact + hash
├── 01_COMPANY_CORPUS/              ← Stage 1
├── 02_FAMILY_GRAPH/                 ← Stage 2
├── 03_TECHNOLOGY_MAP/               ← Stage 3 (Technology Graph)
├── 04_OWNERSHIP_MAP/                ← Stage 3 (Ownership Graph)
├── 05_BUYER_MAP/                    ← Stage 3 (Buyer Graph)
├── 06_MOAT_MAP/                     ← Stage 4
├── 07_PROBLEM_SELECTION/            ← Stage 5
├── 08_LIMITATION_FREEZE.json        ← Stage 6 (IMMUTABLE)
├── 09_PRIOR_ART/                    ← Stage 7
├── 10_CLAIM_RETRIEVAL/              ← Stage 8
├── 11_102_ATTACK/                   ← Stage 9
├── 12_103_ATTACK/                   ← Stage 10
├── 13_ARCHITECTURES/                ← Stage 11
├── 14_DESIGN_AROUND/                ← Stage 12
├── 15_ENGINEERING_BLUEPRINT/        ← Stage 13
├── 16_SIMULATION/                   ← Stage 14 (domain-specific)
├── 17_MANUFACTURING/                ← Stage 15a
├── 18_REGULATORY/                   ← Stage 15b
├── 19_BUILD_BUY/                    ← Stage 16
├── 20_BUYER_MEMO/                   ← Stage 17
├── 21_EVIDENCE_LEDGER.json          ← provenance for every conclusion
├── 22_FINAL_ADJUDICATION.json       ← Stage 18
├── 23_LESSONS_LEARNED.json          ← immutable learning record
└── SHA256SUMS                       ← hashes for all artifacts above
```

The directory names use a zero-padded index. The index is the order of execution. Skipping an index is a CI failure (an artifact was produced out of order or skipped).

---

## 7. The Five Gates

### 7.1 Gate Definitions

| Gate | Weight | Threshold | Compensable | Source of Truth |
|---|---|---|---|---|
| Patent Gate | 35% | ≥70 | **NO** (non-compensable) | 11_102_ATTACK + 12_103_ATTACK + 08_LIMITATION_FREEZE + 14_DESIGN_AROUND |
| Evidence Gate | 25% | ≥70 | **NO** (non-compensable) | 21_EVIDENCE_LEDGER + provenance chain completeness |
| Technical Gate | 15% | ≥65 | YES | 15_ENGINEERING_BLUEPRINT + 16_SIMULATION |
| Engineering Gate | 15% | ≥60 | YES | 16_SIMULATION + 17_MANUFACTURING (failure modes + worst-case + safety) |
| Commercial Gate | 10% | ≥65 | YES | 19_BUILD_BUY + 20_BUYER_MEMO |

Composite score = Σ(gate_score × gate_weight).

Composite threshold for BUYER_READY = **≥70**.

### 7.2 Non-Compensability Rule

If Patent Gate < 70 OR Evidence Gate < 70, the invention is `WOULD_NOT_PAY` regardless of composite score. No amount of excellence in Technical / Engineering / Commercial gates can compensate.

### 7.3 Hard Gate Evidence Pointer

Every gate score must reference the `evidence_id`s that support it. A gate score without evidence pointers is a silent promotion and is a CI failure.

### 7.4 Soft Gate Thresholds

Technical ≥65, Engineering ≥60, Commercial ≥65. Composite must be ≥70 even if all soft gates clear. Soft gate failures are recorded but do not force `WOULD_NOT_PAY`; they reduce composite and may push status to `WOULD_CONSIDER_WITH_MILESTONES`.

### 7.5 Milestone Lists

A `WOULD_CONSIDER_WITH_MILESTONES` verdict must enumerate every milestone required to reach `LEVEL_4_BUYER_READY`. Milestones must be specific (not "do more work"). Each milestone references the evidence_id gap it would close.

---

## 8. Limitation Freeze Rules

### 8.1 What is Frozen

Once `08_LIMITATION_FREEZE.json` is written:

- The limitations L1..Ln cannot be edited.
- Their arrangement (order, dependency) cannot be edited.
- The claim language cannot be reworded.

### 8.2 Supersession

If the limitations must change, a new version (`V2`) is created. V1 is preserved. V2 references V1 with a `supersedes` pointer and a `supersession_rationale`. No overwrite is permitted.

### 8.3 Hash Anchoring

`08_LIMITATION_FREEZE.json` is hashed in `SHA256SUMS`. The 102/103 attack artifacts reference the limitation-freeze content hash. Any mismatch (e.g., 102 attack references V1 freeze but SHA256SUMS shows V2 freeze) is a CI failure.

### 8.4 Frozen Arrangement Test

102 anticipation requires not just that all limitations are present in a single reference, but that the **arrangement** is also disclosed (or inherent). A reference disclosing L1, L2, L3 in different embodiments, with no teaching to combine them, is **not** 102 anticipation. It may be 103 obviousness — but only with documented motivation.

---

## 9. Hard CI / Preflight Checks

The repository contains a `preflight_check.py` script (Section 11) that runs against every invention folder. The CI fails (exit non-zero, blocks merge to main) if any of the following conditions are detected:

### 9.1 Missing Artifacts

- `00_MANIFEST.json` is missing.
- Any of `08_LIMITATION_FREEZE.json`, `21_EVIDENCE_LEDGER.json`, `22_FINAL_ADJUDICATION.json`, `23_LESSONS_LEARNED.json` is missing.
- `SHA256SUMS` is missing.
- Any directory in the Section 6 list is missing.

### 9.2 Limitation Freeze Violations

- `08_LIMITATION_FREEZE.json` is missing.
- The freeze file does not contain L1..Ln with explicit text.
- The freeze file has been edited without a version supersession record.

### 9.3 Patent Assertion Without Primary-Source Evidence

- A 102 or 103 assertion in `11_102_ATTACK` or `12_103_ATTACK` lacks an `evidence_id`.
- The `evidence_id` does not resolve to an entry in `21_EVIDENCE_LEDGER.json`.
- The ledger entry has no `passage` (or `passage_present: false` for primary-source entries).
- The ledger entry's `artifact_pointer` does not match a hashed file in `SHA256SUMS`.

### 9.4 102 Multiple-Reference Violations

- A 102 assertion uses more than one reference.
- A 102 assertion says `anticipated: true` while the limitation matrix contains `NOT_DISCLOSED` for any limitation.
- A 102 assertion's rationale text describes a combination (the word "combine" or "combination" appears) — this is a 103 attack mis-classified as 102.

### 9.5 103 Missing Motivation Violations

- A 103 assertion lacks a `motivation` field.
- The motivation field is empty or contains only "both known in the art" / "well-known" without a documented reason.
- A 103 assertion lacks a `reasonable_expectation_of_success` field.

### 9.6 Family Coverage Violations

- Discovery coverage is reported but family coverage is missing.
- Family coverage is `<100%` without an explicit `EVIDENCE_INSUFFICIENT` flag and a list of which families were not enumerated.

### 9.7 Engineering Worst-Case Violations

- `15_ENGINEERING_BLUEPRINT` has no `failure_modes` field, or the field is empty.
- `16_SIMULATION` has no `worst_case_boundary_conditions` field.
- A permanent-device invention has no `fail_safe_analysis` field where applicable (devices with safety-critical failure modes; this triggers for CNS, cardiac, vascular, respiratory, implantable-power-source domains).

### 9.8 Simulation Number Provenance Violations

- `16_SIMULATION` contains a numeric output without `model_inputs`.
- `model_inputs` is empty or does not include the variables the output depends on.

### 9.9 Score Provenance Violations

- `22_FINAL_ADJUDICATION.json` reports a gate score without an `evidence_pointer` for that gate.
- A `LEVEL_4_BUYER_READY` verdict is issued while any gate score is below threshold.
- A `WOULD_CONSIDER_WITH_MILESTONES` verdict has an empty milestone list.
- A `LEVEL_4_BUYER_READY` verdict is issued while the milestones list is non-empty.

### 9.10 Hash Integrity Violations

- An artifact listed in `00_MANIFEST.json` has a different SHA256 than the file on disk.
- `SHA256SUMS` does not list all artifacts in the invention folder.
- An artifact referenced by `21_EVIDENCE_LEDGER.json` is not in `SHA256SUMS`.

### 9.11 Version Preservation Violations

- A previous version directory (`CEREVASC_INVENTION_001_V1_FROZEN`) has been deleted or overwritten.
- A `LIMITATION_FREEZE` V2 has been written without preserving V1.

### 9.12 Silent Promotion Violations

- An invention is marked `BUYER_READY` while any hard gate score is below threshold.
- An invention is marked `BUYER_READY` while a soft gate score is below threshold AND composite < 70.

---

## 10. Provenance Rules

### 10.1 Evidence Ledger Schema

Every entry in `21_EVIDENCE_LEDGER.json`:

```json
{
  "evidence_id": "E001",
  "task_id": "TASK1",
  "claim": "<one-sentence claim this evidence supports>",
  "evidence_source": "<where the evidence comes from>",
  "source_type": "patent_primary_text | fda_database | iso_standards | industry_benchmarks | physics_simulation | patent_law_framework | model_derived",
  "passage_present": true,
  "passage": "<direct quote from primary source, with location>",
  "model_derived": false,
  "model_derived_note": "<required if model_derived=true>",
  "artifact_pointer": "<file this evidence is recorded in>",
  "content_hash": "<sha256 of that file>"
}
```

### 10.2 Bidirectional Traceability

- Every conclusion in `22_FINAL_ADJUDICATION.json` references one or more `evidence_id`s.
- Every `evidence_id` in the ledger resolves to an `artifact_pointer`.
- Every `artifact_pointer` resolves to a file in `SHA256SUMS`.
- The chain is bidirectional: from any conclusion, walk back to the file; from any file, walk forward to the conclusions it supports.

### 10.3 Model-Derived Labeling

Any assertion produced by an LLM, model, or simulation (as opposed to direct quotation from a primary source) MUST have `model_derived: true` and a non-empty `model_derived_note` explaining what was derived and from what inputs. A model-derived assertion presented as primary-source evidence is a CI failure (silent fabrication).

---

## 11. Mechanical Enforcement — `preflight_check.py`

A Python script at `protocol/preflight_check.py` enforces every rule in Section 9 mechanically. The script:

1. Walks every `INVENTION_*` directory in the repository.
2. For each directory, runs every check in Section 9.
3. Returns exit 0 if all checks pass; exit 1 if any check fails.
4. Produces a `preflight_report.json` with per-check pass/fail and the specific failure reason.

CI runs this script on every commit to `main`. A failure blocks the commit.

The script is **not** a substitute for human review — it is the floor. Human review is still required for substance (is the motivation analysis actually meaningful? is the simulation actually correct?). But no invention can be promoted to `BUYER_READY` without passing this script.

---

## 12. Domain-Specific Simulation Registry

The protocol maintains a registry of simulation domains. Each domain entry:

```text
SIMULATION_DOMAIN
    ├── name: "membrane_fouling"
    ├── engineering_context: "selective-permeability devices with chronic fluid exposure"
    ├── required_physics_model: "Hagen-Poiseuille hydraulic resistance"
    ├── required_failure_modes: ["fouling", "occlusion", "membrane rupture", "leak"]
    ├── required_worst_case: "complete occlusion"
    ├── required_sensitivity_variables: ["fouling_fraction", "flow_rate", "lumen_diameter"]
    ├── required_safety_constraints: ["max_ICP < 20 mmHg", "fail-safe bypass"]
    ├── required_design_modification_loop: true
    └── applicable inventions: ["CEREVASC_001", ...]
```

When the Engineering Blueprint (Stage 13) is complete, the protocol inspects the blueprint and selects the simulation domain. An invalid selection (e.g., "membrane_fouling" for a battery invention) is a CI failure.

The registry is extensible only via the Protocol Evolution Workflow (Section 14). New domains cannot be added mid-run.

---

## 13. Lessons Learned Process

### 13.1 `23_LESSONS_LEARNED.json` Schema

Every invention produces a `23_LESSONS_LEARNED.json` with the following fields:

```json
{
  "invention_id": "CEREVASC_INVENTION_001_V2",
  "protocol_version": "INVENTION_PROTOCOL_V1",
  "what_worked": ["..."],
  "what_failed": ["..."],
  "hallucinations_caught": ["..."],
  "false_positives": ["..."],
  "false_negatives": ["..."],
  "prior_art_search_failures": ["..."],
  "patsnap_endpoint_failures": ["..."],
  "model_specific_errors": ["..."],
  "engineering_assumptions_invalidated": ["..."],
  "buyer_objections": ["..."],
  "protocol_changes_proposed": ["..."]
}
```

### 13.2 Immutability

Lessons are **recorded**, not **enforced**. A lesson cannot silently modify this protocol. A lesson that suggests a protocol change is added to `protocol_changes_proposed` and queued for the Protocol Evolution Workflow (Section 14).

### 13.3 Why This Matters

This separation prevents entropy. Lessons accumulate, but the constitution remains stable until audit. The 150 inventions all play by the same rules; their lessons inform V2 of the constitution, not the run in progress.

---

## 14. Protocol Evolution Workflow

This is the only way `INVENTION_PROTOCOL_V1` becomes `INVENTION_PROTOCOL_V2`.

```text
INVENTION_PROTOCOL_V1  (this file — FROZEN)
        ↓
INVENTION_001 ... INVENTION_150  (each runs under V1)
        ↓
23_LESSONS_LEARNED.json per invention  (lessons accumulate)
        ↓
PROTOCOL_CHANGE_PROPOSAL  (a lesson suggests a change)
        ↓
AUDIT  (independent reviewer audits the proposal)
        ↓
INVENTION_PROTOCOL_V2  (supersedes V1; V1 preserved)
```

### 14.1 Proposal

A `PROTOCOL_CHANGE_PROPOSAL.md` is filed with:

- The proposed change (diff against V1).
- The lessons that motivate it (citing specific `evidence_id`s from specific `LESSONS_LEARNED.json` files).
- The expected impact on existing inventions (would they re-pass under V2?).

### 14.2 Audit

An independent reviewer (not the agent that filed the proposal) audits:

- Is the change justified by the evidence?
- Does the change weaken any non-compensable gate? (Forbidden — V2 cannot weaken V1's gates.)
- Does the change introduce a loophole that allows silent promotion? (Forbidden.)
- Does the change apply retroactively? (Forbidden — V1 inventions are not re-adjudicated under V2.)

### 14.3 Supersession

If audit passes, `INVENTION_PROTOCOL_V2.md` is created. V1 remains in the repository. New inventions from #N+1 onward run under V2. The repository root README indicates which protocol version is current.

### 14.4 What Cannot Be Changed By V2

- The non-compensable status of Patent and Evidence gates.
- The 102 single-reference rule.
- The 103 motivation/expectation requirement.
- The provenance chain requirement.
- The limitation freeze immutability.
- The mandatory artifact list.
- The "no silent promotion" rule.
- The Protocol Evolution Workflow itself.

These are the **constitutional invariants**. V3, V4, V∞ cannot weaken them.

---

## 15. Portfolio Discipline

### 15.1 10 Moat Positions Per Company

For each company, 10 Moat Positions are selected deliberately before any invention work begins. The selection is informed by the Moat Map (Stage 4) and addresses distinct strategic white space.

### 15.2 Independent Adjudication

Each Moat Position is independently subjected to all gates. One Moat Position failing does not disqualify the company. One Moat Position passing does not redeem the company. Each stands on its own.

### 15.3 No "Try 10 and Hope One Survives"

The portfolio approach is **deliberate**, not opportunistic. Each position is selected because it represents a defensible white-space claim. The 10 positions are not "shotgun" attempts; they are 10 distinct strategic bets.

### 15.4 15 Companies × 10 Positions = 150 Inventions

The program scale. Each invention produces a complete package (Section 6). Each invention's `23_LESSONS_LEARNED.json` feeds the next invention's selection. Lessons accumulate, but the constitution does not.

---

## 16. Adjudication Tiers

### 16.1 Three Terminal Statuses

```text
WOULD_NOT_PAY
    → At least one hard gate (Patent or Evidence) failed.
    → Composite score is irrelevant.
    → Reason recorded permanently.

WOULD_CONSIDER_WITH_MILESTONES
    → All gates pass.
    → Composite ≥ 70.
    → Milestones list is non-empty (required to reach BUYER_READY).
    → Each milestone references an evidence_id gap.

LEVEL_4_BUYER_READY
    → All gates pass.
    → Composite ≥ 70.
    → Milestones list is empty.
    → Independent buyer (CTO/CSO/BD) would reasonably pay for this invention.
```

### 16.2 The Final Test

> "If you were CereVasc's CTO / CSO / BD lead, would you pay to acquire or license this invention today?"

The answer is the verdict. The protocol exists to make the answer defensible — not to optimize the answer to "yes." A `WOULD_NOT_PAY` verdict under a correctly-applied protocol is a successful run. A `WOULD_PAY` verdict under a sloppy protocol is a failure.

### 16.3 Anti-Optimization Stance

The protocol is not tuned to produce `LEVEL_4_BUYER_READY`. The protocol is tuned to produce **defensible** verdicts. If 149 of 150 inventions return `WOULD_NOT_PAY`, that is a successful portfolio run — it means the protocol honestly rejected 149 weak positions. If 150 of 150 return `LEVEL_4_BUYER_READY`, that is suspicious — it means the protocol is too permissive and a V2 audit is required.

---

## 17. Closing

This file is the constitution. It is FROZEN as of 2026-08-17. It will only change via the Protocol Evolution Workflow. It cannot be edited during a run. It cannot be bypassed. It cannot be interpreted away. It is the standard.

Inventions #1 through #150 run under this file.

> **If any mandatory artifact, gate, provenance link, checksum, or protocol version is missing, the invention run must stop rather than exercise judgment.**

— END OF INVENTION_PROTOCOL_V1 —
