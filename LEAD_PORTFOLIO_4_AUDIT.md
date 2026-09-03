# LEAD PORTFOLIO 4 — FORENSIC AUDIT (pre-implementation)

```text
CONSTITUTION_READ_FULLY: YES
```

**Auditor:** Coder (R403 session), per the CEO Lead-Portfolio-4 hardening directive.
**Date:** 2026-09-04 (all times UTC; artifacts dated by their own records).
**Mode:** READ-ONLY forensic audit. No repository file was modified before this report was written.
**Scope:** engine repo (`discovery-evidence-fabric`, HEAD `5a4a2b8b`, R402 certified) + buyer-distribution repo (`technology-transfer-portfolio-15`, tag `v1.0.0-3D-edition`, portfolio release commit `b978e32c`, 924 pinned buyer files) + git history (including branch `origin/archive/rounds-R309-R383`, fetched and verified this session).

---

## 1. Constitution status

- `EPISTEMIC_CONSTITUTION.md` v2.0.0 was read in full (1,947 lines) before any work. Articles I–XXXIX (epistemic integrity) and XL–LXIII (discovery integrity) govern this pass.
- Articles directly engaged by this directive:
  - **Art. VI / §8 of the directive** — never manufacture provenance; if a novelty artifact cannot be located, the state is `NOVELTY_SEARCH_REPORTED` + `SOURCE_ARTIFACT_UNAVAILABLE`, never invented certainty.
  - **Art. XI** — history is evidence; historical IDs, hashes, and the R388 archive deletion are immutable facts to be cited, not rewritten.
  - **Art. XXV / XXVIII** — a patent search is not a novelty determination; `NOVELTY_ASSESSMENT = SUPPORTED` (documented assessment) ≠ patentability opinion ≠ FTO opinion.
  - **Art. XXIX** — implementation failure ≠ mechanism failure: governs P04's `KILLED_GEOMETRY_INVALID`.
  - **Art. XXXVII / XXXVIII / LIII** — CAD is computational; no physical-validation claims; `REAL_LOOP_VERIFIED` cannot be assigned manually.
  - **Art. XXXIX** — the buyer-distribution repository is the final authority for what a buyer receives; every identity/novelty record here must be reconcilable against it.
  - **Art. XLII/XLVI** — mechanism identity is the unit of novelty, not labels; P-27-R1's lineage mis-attribution is exactly a violation class to correct.
  - **Art. LII / LIV / LXIII** — decisive experiment = falsification contract; every package carries its own kill condition; the buyer gets uncertainty, not scores.
- State recorded before audit: engine HEAD `5a4a2b8b` == origin/main (verified by fetch this session); worktree clean after silencing sandbox file-mode noise (1,814 files, 0 insertions/0 deletions — content byte-identical).

---

## 2. Identity audit

The repository contains **at least seven co-existing identity layers** (the danger the directive names):

| # | Layer | Where it lives | Example (drainage floor) |
|---|---|---|---|
| 1 | External portfolio sequence (01–15) | buyer repo folders, PDF headers/footers | `04_drainage_floor` — "Portfolio 04 of 15" |
| 2 | **Company designation (P04/P08/P11/P13/P14)** | **NOWHERE — not recorded in either repository** | — |
| 3 | Historical package ID (immutable) | frozen corpus r370, manifests, mutation certificates | `P-07` |
| 4 | Folder name | both repos | `04_drainage_floor` |
| 5 | Model identity | portfolio `MODEL/` dirs | `pm:4d42cf7d74b35dac`, `portfolio_04_dual_lumen_catheter.step` |
| 6 | Document footer | every shipped PDF | "Portfolio 04 of 15 - Package P-07 - Version 2.0" |
| 7 | Manifest identity | `PACKAGE_MANIFEST.json` / portfolio `PORTFOLIO_IDENTITY_REGISTRY.json` v2.0 | package_id `P-07`, portfolio_number `04` |

Verified canonical mapping (frozen corpus `MATURITY_BASIS.json` + portfolio `PORTFOLIO_IDENTITY_REGISTRY.json` agree; all 15 enumerated):

```text
P04 → Portfolio 04 → P-07  → Passive Drainage Priority Safety Floor        (folder 04_drainage_floor, v2.0)
P08 → Portfolio 08 → P-16  → NIR Photovoltaic Power Delivery for Implantable Devices (folder 08_nir_photovoltaic, v1.0)
P11 → Portfolio 11 → P-24  → Gravity Compensation Hydraulic Damper for Postural Transients (folder 11_gravity_damper, v1.0)
P13 → Portfolio 13 → P-27-R1 → Self-Referencing Piezoresistive Pressure Sensor (folder 13_pressure_sensor, v2.0)
P14 → Portfolio 14 → P-28  → Acoustic Obstruction Detection for CSF Shunts (folder 14_acoustic_detection, v2.0)
```

**Conflicting/colliding schemes found (the concrete hazards):**

1. **`PACKAGE_ID_REGISTRY.json` (engine)** is a *sequential allocation* registry: 158 rows where portfolio number NN = package `P-NN`, and rows 16–158 were consumed by sandbox fixture allocations (`P-24 → inv:fixture:thermal:11:4e73c8041f14 ALLOCATED`, `P-16 → inv:fixture:thermal:11:8ead0528b487`…). These **collide with the real historical IDs**: registry-P-24 is a fixture; portfolio-P-24 is the gravity damper. Any consumer joining these tables gets wrong identities.
2. **`PORTFOLIO_COMMERCIAL_STATE.json`** (CEO-managed, 2026-08-26) tracks a *different 15-candidate set* (P-01, P-02, P-04, P-07, P-10, P-11, P-12, P-13, P-15, P-16, P-20, P-21, P-22, P-24, P-25) and **has no P-26/P-27-R1/P-28 entries at all** — P13 and P14 of today's external portfolio are untracked there. In that file, "P-04" is a *catalytic clearance* note — a third meaning for the same token.
3. Buyer-facing PDFs expose the internal historical ID (`Package P-07`) without any company-designation layer — the §19/§20 identity-leakage condition.
4. The engine's `BENCHMARK_ENGINEERING_DOSSIERS/P-XX.json` metrics files and the R370M/O/P/Q consultant exports all key on historical IDs — fine as provenance, but nothing joins them to commercial names.

**Historical-ID immutability is already well enforced structurally** (frozen corpus hashes, mutation certificates with before/after manifest hashes, portfolio registry policy "Historical package IDs are immutable and are never renumbered"). No rename of any historical artifact is proposed or needed.

---

## 3. Novelty audit

Management states all four lead technologies underwent novelty testing through **PatSnap and Patent-Bear**. Repository ground truth, measured artifact by artifact:

### 3.1 Patent-Bear (real, executed 2026-08-26) — EXISTS for 3 of 4 lead packages

The R354→R368 "patent intelligence" chain ran **real PatentBear MCP searches** (`https://www.patentbear.com/mcp`, Bearer-authenticated) over the then-15-package roster. All package-level result artifacts were **deleted from `main` at R388** (`8cb6ff3b`, 2026-09-01, "distill the active tree") and are recoverable **only from branch `origin/archive/rounds-R309-R383`** (tip `c7f7d692`; fetched and verified this session; no history rewrite — Art. XI satisfied).

| Package | Broad query → hits | Specific query → hits | Verdict | Closest prior art (real patent numbers) |
|---|---|---|---|---|
| **P-07** (P04) | `shunt drainage obstruction maintenance` → 496 | `shunt drainage floor mechanism partial obstruction maintenance flow` → 50 | CONDITIONAL (MEDIUM) | US20240207499A1 (sensor monitoring for in-dwelling catheters); US20250303128A1; US20230211135A1; US8545431B2 |
| **P-16** (P08) | `near infrared transcranial photovoltaic implantable medical device power delivery` → 40 | `940nm GaAs photovoltaic transcranial power implantable shunt` → **0** | PASS (VERY HIGH — "completely novel combination") | R365 passage-level: closest US20190111255A1 (54 claims) — missing all 5 mapped elements (940nm, GaAs PV, transcranial, power delivery, implantable shunt) |
| **P-24** (P11) | `CSF shunt anti-siphon valve overdrainage` → 34 | `compressible element proportional damper CSF shunt gravity compensating` → 6 | PASS (MEDIUM-HIGH) | US20250242099A1; US6953444B2 (inherent anti-siphon); US20060089589A1; US20030139699A1 |
| **P-27-R1** (P13) | — | — | **NO SEARCH OF THIS TECHNOLOGY EVER RAN** | none |

Evidence-chain artifacts (per package): R359 broad search + `canonical_evidence_v2/P-XX/evidence_graph_v2.json` (§102/§103/FTO attack graphs, "NOT a legal opinion… Buyer counsel must perform formal diligence"), R361 specific-mechanism queries, R363 (100 searches, design-arounds), R365 passage-level claim analysis, R368 final gate. All on the archive branch; sha256s computed this session (§3.4).

**P-27-R1 lineage defect (found live):** the R359–R365 records keyed "P-27"/"P-27-R1" targeted the **old P-27** (shape-memory-polymer kink-resistant catheter, 2,014 broad / 515 specific hits, REPAIR) and its metallic-tubing repair. The **self-referencing pressure sensor** entered at R336 as CAND-002/P-25 and only *acquired* the P-27-R1 label at the R370 corpus rebuild. `R370/claim_level/ALL_CLAIMS.json` (still at HEAD) cites "R359-R365 patent intelligence **for P-27-R1**" — a **mis-attribution: the cited searches were for a different invention**. This is exactly the identity-integrity defect class the directive predicts.

### 3.2 PatSnap — NO search of any lead package ever executed

Measured failure record (all committed):
- `R354/patsnap_pipeline/PATSNAP_API_STATUS.json` (archive): "API key recognized but account balance EXHAUSTED (error 67200203)… Recharge ~$3,000" (2026-08-26). The pre-configured 15-package PatSnap query table (`patsnap_search.py`) **never executed** — no results file was ever committed.
- New key rejected 67200202 on 2026-08-31 (`experiments/autonomous_calibration_v3/NEW_PATSNAP_KEY_TEST.json`).
- Engine retrieval log (`artifacts/source_health/retrieval_log.jsonl`): all 13 `patsnap_eureka` rows FAILED ("PATSNAP_EUREKA_API_KEY not configured"); `SOURCE_HEALTH_REPORT.json`: `patsnap_eureka: BLOCKED (AUTH)`.
- Real PatSnap data exists **only for the old eShunt-era positions/territories** (CEREVASC_POSITION_004 V6 complete, TERRITORY_5/6–10, 2026-08-16→19) — not the four lead technologies.

### 3.3 P-28 (P14)

Explicitly recorded three times as never searched: R367 "§103: NOT_PERFORMED", R368 "NOT_SEARCHED — next step: Patent search + bench test", R370 claim ledger "§102 screen: NOT_PERFORMED — needs PatentBear search".

### 3.4 Honest reconciliation of the management claim

Per directive §8 (never fabricate; unknown stays unknown) the per-platform record is:

| Package | Patent-Bear | PatSnap |
|---|---|---|
| P04 / P-07 | **SUPPORTED** — real searches (R359/R361/R365 chain), artifacts restorable from the archive branch with hashes | **SEARCH_ATTEMPTED, NEVER EXECUTED** (documented auth/balance failures) → `SOURCE_ARTIFACT_UNAVAILABLE` |
| P08 / P-16 | **SUPPORTED** — including passage-level claim non-match (R365) | same |
| P11 / P-24 | **SUPPORTED** | same |
| P13 / P-27-R1 | **NOT_FOUND for this technology** — the historical P-27 searches are a different invention; management-reported testing is unverifiable from repository evidence → `NOVELTY_SEARCH_REPORTED` + `SOURCE_ARTIFACT_UNAVAILABLE` | same |

No conclusion anywhere may be promoted to patentability or FTO (Art. XXVIII; the R359 evidence graphs themselves carry "NOT a legal opinion" stamps).

---

## 4. Evidence audit

- **Buyer-side evidence layers are honestly labeled**: all four packages' `ENGINEERING_TRACEABILITY.json` pass with zero unsupported numbers; the buyer repo's release-gate truth model records **EXPLICIT 0 / PARTIAL 0 / UNKNOWN 9–11** traceability chains per package (`TRACEABILITY_UNKNOWN`) — "the graph is NOT represented as healthy."
- **P-16's strongest claim is asserted, not archived**: the R370Q dossier states `verified_fluence: "1.0–1.4 mW/cm² (T2-CONFIRMED via PyTissueOptics v2.0.1)"` and cites `R311/p16_actual_verification/`, `R312/p16_convergence/`, `R310/p16_disagreement/` — **none of these directories exist in the repo or its history**; the claim's own class is MODELLED with limitation "model prediction — not experimentally verified", `independent_verification: "none"`. The MC pre-registration (R309) is committed; the execution artifacts are not.
- **The one external-consultant quantitative review** (`EXTERNAL_CONSULTANT_REPORT_2026-08-27.md`) reconstructed the P-16 chain independently (940 nm, µ_eff 1.0–2.5 cm⁻¹ per Jacques 2013 → 60.7 %/28.7 % at 5 mm soft tissue; 100 mW/cm² × 28 % × ~30 % GaAs ≈ plausibility) and **confirmed the ≥500 mW target was a unit error** (corrected to µW).
- **Novelty evidence provenance**: the only HEAD-level citation is `R370/claim_level/ALL_CLAIMS.json` (P-07-C002/P-16-C002/P-24-C002: "§102 screen: SELECTED_REFERENCES_DO_NOT_DISCLOSE_ALL_MAPPED_LIMITATIONS", uncertainty "Global novelty not established") — which inherits the P-27-R1 mis-attribution.
- **Retrieval-log custody**: PatentBear's one successful engine call (`hydrocephalus shunt valve`, 2026-08-29, 5 records) is hash-logged but its payload is not committed (the disclosed prior_art_v2 custody gap).

---

## 5. Engineering / CAD audit

All five packages ship a full `MODEL/` layer in the buyer repo (STEP/STL/GLB + SVGs + `PARAMETRIC_MODEL_SOURCE.py` + `PARAMETERS.json` + `CONSTRAINTS.json` + `GEOMETRY_VALIDATION_REPORT.json` + `MODEL_MANIFEST.json` with sha256 per derivative + `3D_EVIDENCE/` with independent watertight checks + regeneration checks — all `REGENERATION_REPRODUCIBLE`).

| Package | Shipped model | Improvement-loop outcome | Geometry validity |
|---|---|---|---|
| P04 / P-07 | base `pm:4d42cf7d74b35dac` | **KILLED_GEOMETRY_INVALID** (the mutation, not the shipped base) | shipped base **VALID** — all gates, min wall 0.2 mm ≥ 0.15 |
| P08 / P-16 | KEEP child `pm:b5ffd7a6d0d1e37f` | KEEP (cell Ø 5→7 mm, area 19.635→38.485 mm²) | valid; G7 SATISFIED |
| P11 / P-24 | KEEP child `pm:c27f470fc50c2e36` | KEEP (gap 0.3→0.18 mm, c_h_rel ×4.63 MODELLED) | valid |
| P13 / P-27-R1 | KEEP child `pm:e478a473e1da01a5` | KEEP (diaphragm 0.12→0.07 mm, sensitivity ×2.939 MODELLED) | valid |
| P14 / P-28 | KEEP child `pm:2bf422771f4f2341` | KEEP (PZT Ø 1.4→1.7 mm) | valid |

The CAD pipeline is genuine and deterministic (CadQuery/OCCT, measured-on-built-solid G-gates, one declared mutation per package). Each package got exactly **one** mutation; alternatives (P-07: outer diameter, intermediate floor-lumen values) were never explored.

---

## 6. Validation audit

- **Zero `REAL_LOOP_VERIFIED` portfolio events** — confirmed. Exactly **one** reality event exists engine-wide: `EVT-R390-NIST-WATER-VISC-310K` (P-07): a NIST WebBook constants acquisition (water viscosity 691.3036 µPa·s @ 310.15 K, fetched live 2026-09-02, raw TSV preserved) that refuted P-07's 1.0 mPa·s design constant, drove a deterministic rebuild (floor lumen 0.6→0.5471 mm, valid, conductance restored to ratio 0.999984), and closed the loop **in the engine sandbox only** (`applied_to_canonical_package: false`). Its own attestation honestly says: "an ACQUISITION of externally published measured data, not a benchtop measurement performed by the operator."
- `loop_verification_state` in the buyer repo: P-07 NONE, P-16 NONE, P-24 **SYNTHETIC_LOOP_VERIFIED** (the only non-NONE; the R339 synthetic-observations loop), P-27-R1 NONE, P-28 NONE.
- All five `MATURITY_BASIS.json` declare `ENGINEERING_DEFINITION`; all buyer `LOOP_STATE.json` record `PHYSICAL_OBSERVATION = 0` on every queue.
- **No package may claim physical validation.** The directive's §14 ladder position for all four: `ENGINEERING_DEFINED` (arguably `COMPUTATIONALLY_VALIDATED` in the CAD dimension only — recorded as the sub-state, never the headline).

---

## 7. Commercial-transfer audit

- Transfer posture (both repos' manifests): `SPONSORED_VALIDATION` for all — a commercial-state label, not a technical one (PORTFOLIO_COMMERCIAL_STATE constitutional basis).
- The R382 CEO disposition (`PORTFOLIO_DISPOSITION.json`) already selected the buyer-primary subset: **"Show now: 04, 11, 13, 08 … Retire: 06, 07, 10, 14 …"** — i.e., the four lead packages of this directive are precisely the CEO's show-now set, and P14 is precisely the retired set. Consistent.
- `transfer_logic.transfer_ready: false` in all four; regulatory pathway UNKNOWN in all four (per R370C correction); manufacturing ENGINEERING_CANDIDATE in all four.
- REAL_BUYER: 0; every package UNCONTACTED in the CEO-managed commercial state (which, again, does not track P-27-R1/P-28).
- The r371 buyer-document generator already enforces the epistemic discipline the directive's §6 demands (`NOT_ESTABLISHED` for market/competitor/IP claims; "novelty determination NOT_ESTABLISHED (a patent search is not a novelty determination — Constitution Art. XXVIII)").

---

## 8. P04 findings — Passive Drainage Priority Safety Floor (P-07, portfolio 04)

1. **The `KILLED_GEOMETRY_INVALID` record is real but narrow — and the repo is honest about it.** The kill applies to the *improvement-loop mutation* (`floor_lumen_diameter_mm` 0.6 → 0.8 mm — deliberately pushed to the envelope edge, "the honest KILL demo: geometry gate decides"), which failed exactly one gate: **G4 / C_MIN_WALL** (measured min wall 0.1 mm < 0.15 mm, `MEASURED_ON_BUILT_SOLID`). The shipped base geometry `pm:4d42cf7d74b35dac` is **fully valid** (all gates; measured wall 0.2 mm; regeneration reproducible; manifest hashes match). `DESIGN_LINEAGE.json` states verbatim: `shipped_model_is: "the base design (the mutation was KILLED)"`. The failure is preserved in the shipped `IMPROVEMENT_LOOP_EVIDENCE.json` — not hidden.
2. **Art. XXIX separation is already factually available**: scientific concept (dual-lumen drainage-priority mechanism, 4 governing equations, 10 DIs) ≠ engineering architecture (parametric dual-lumen CAD) ≠ the one dead mutation attempt. A *separate* synthetic demo (`TOSCANINI/R383_LIVE_QUANTITATIVE/LEDGER_case4.json`) also records a KILLED_GEOMETRY_INVALID — that fixture's parent was deliberately invalid (wall −0.05 mm); it is NOT the portfolio package and must not be conflated with it.
3. **A physically coherent refined geometry already exists**: the R390 reality loop rebuilt the catheter at floor lumen 0.5471 mm (NIST-viscosity-driven), all gates valid, conductance restored — but only in the engine sandbox; the canonical package was deliberately untouched (Art. IX). Applying it to the buyer surface is a release-chain decision (Art. XXXIX protocol), not a hardening edit.
4. Open engineering unknowns (from MATURITY_BASIS): G_floor/G_primary manufacturable ratio UNKNOWN, common-cause obstruction immunity UNKNOWN (critical), Q_min UNKNOWN, multi-lumen extrusion capability UNKNOWN, regulatory pathway UNKNOWN, clinical benefit magnitude UNKNOWN.

**Answer to directive §9's question:** YES — the concept is already represented with physically coherent geometry (the shipped base). No rescue is needed and none may be fabricated; the required work is to *make the concept/architecture/implementation separation explicit and machine-checkable*, and to record the mutation-death + the valid R390 rebuild candidate as first-class package state.

---

## 9. P08 findings — NIR Photovoltaic Power Delivery (P-16, portfolio 08)

1. **The complete energy budget DOES NOT EXIST anywhere in the repository.** Closest components: EQ-1 (Beer–Lambert, µ_eff EXTERNAL_PRECEDENT 1–10 cm⁻¹), EQ-2 (P = η·P_opt), EQ-3; the R370Q one-line block (fluence 1.0–1.4 mW/cm² "T2-CONFIRMED via PyTissueOptics", power "~1050 μW (MODELLED: fluence × area × efficiency)" — with area and efficiency unstated); the consultant's reconstructed chain (100 mW/cm² × 28 % × ~30 % GaAs). No artifact enumerates every stage loss (source wall-plug, skin interface, tissue path incl. skull, encapsulation, PV at low irradiance, conversion/storage, device load) with evidence classes in one place.
2. **The "ACTUAL PyTissueOptics execution" is not reproducible from the repository**: cited execution dirs (R310/R311/R312) are absent from the tree and history; the claim self-labels as MODELLED with `independent_verification: "none"`. The pre-registration protocol (R309, MCX vs PyTissueOptics vs Jacques 2013, tolerance 0.05 mW/cm²) is committed; the execution artifacts are not. **The platform-technology claim must NOT be made** until the budget is assembled and the execution artifacts are restored or the runs repeated.
3. PV efficiency for the targeted cell: UNKNOWN. External source power: UNKNOWN (bounded by tissue heating limit). Cell area: UNKNOWN (constrained by geometry; the CAD KEEP grew receiver area 19.6→38.5 mm²).
4. The ≥500 µW target (post unit-error correction) is the one recorded device-side threshold with provenance (consultant calculation + R370Q dossier).

**Required work:** assemble `ENERGY_BUDGET.json` — every stage, every loss, every number labeled SOURCE_FACT / EXTERNAL_PRECEDENT / MODELLED / T2-CONFIRMED-ASSERTED-NOT-ARCHIVED / UNKNOWN; PV module efficiency never quoted as system efficiency.

---

## 10. P11 findings — Gravity Compensation Hydraulic Damper (P-24, portfolio 11)

1. **The causal chain exists and is explicit** (EQUATION_REGISTRY EQ-1…EQ-5 + R370Q `mechanism_architecture`): postural change → dP_gravity = ρ·g·dh (supine→upright ≈ 37 mmHg) → first-order hydraulic response dQ/dt = (dP_total − dP_gravity − c_h·Q)/I_h → damping dP_damper = c_h·Q → altered flow, settling τ = I_h/c_h.
2. **The baseline comparison exists and is honestly negative**: vs ASD, `postures_asd_closer_to_target: 3/4`; verbatim: "ASD is BETTER than P-24 at target-flow matching in 3/4 postures. P-24's advantage is proportional response and faster modeled dynamics — neither yet established as clinically material." Established advantages: **0**. The two unestablished differentiators (response speed 0.4 s vs 0.5 s; proportional vs binary control) are precisely the declared decisive endpoints.
3. **A decisive experiment specification already exists** (R339 buyer package): mock CSF loop, damper vs ASD vs standard, 4 postural pressures (10/20/30/40 mmHg), 10 runs each, blinded analysis, pass/fail rules quoted verbatim, $15K / 8 weeks. This is Art. LII-compatible in spirit and needs only to be lifted into the 12-element falsification-contract schema.
4. `SYNTHETIC_LOOP_VERIFIED` (the only one in the portfolio) — must remain labeled synthetic; VVUQ label "COMPUTATIONALLY_SUPPORTED_BUT_UNCERTAINTY_SENSITIVE — 78.8 % of the modeled parameter ensemble meets target".

---

## 11. P13 findings — Self-Referencing Piezoresistive Pressure Sensor (P-27-R1, portfolio 13)

1. **The central proposition is correctly narrow in the dossier** ("R1 fix … adds self-referencing bridge for drift correction"; `drift_compensation_target`: 1–10 mmHg/month → <0.5 mmHg/month, **MODEL_DERIVED target**, status "MODELLED — no hardware validation of drift performance"). No baseline-vs-self-referencing *measured* comparison exists anywhere for this package.
2. **The repository's only measured self-referencing result is a FAILURE** — retired package P-25: "67.8 % drift cancellation but 3.45 mmHg error > 2.0 threshold. Biofouling dominates non-common-mode drift. Lesson codified as KA-014." KA-014 (the codified lesson) blocks candidates relying on self-referencing **without a non-common-mode drift repair mechanism**. P-27-R1's recorded mitigations (periodic recalibration, spare capacity) do not obviously satisfy KA-014 — this is the package's largest scientific risk and is currently implicit, not surfaced.
3. Benchmark fields exist only as *planned* verifications: temperature cycle test, chronic aging study with periodic calibration, hermeticity (MIL-STD-883), WP-01 sensitivity/linearity/hysteresis, WP-02 "thermal drift reduced > 90 %" (target, unmeasured). No pressure/thermal cycling endurance field. Reference stability and packaging effects are partially present as failure modes (bridge mismatch, packaging).
4. **No "drift-free" or "self-calibrating" language found** in the package surfaces (grep-verified) — keep it that way and pin it.
5. Novelty: no search artifact for *this technology* exists (see §3.1/§3.4 — the historical-ID collision means the P-27-R1 citations are for a different invention). Any buyer-facing novelty claim must be `NOVELTY_SEARCH_REPORTED` + `SOURCE_ARTIFACT_UNAVAILABLE` until a fresh search runs (PatentBear meter shows 2/20 remaining).

---

## 12. P14 external-distribution risk — Acoustic Obstruction Detection (P-28, portfolio 14)

1. **Externally distributed — TRUE in the recorded sense**: P14 v2.0 is on the publicly pushed, tagged buyer-distribution release (`v1.0.0-3D-edition`; `DOWNLOAD/14_acoustic_detection.zip` sha-pinned in `CANONICAL_RELEASE_MANIFEST.json`, 62 files) that Art. XXXIX designates as "what a buyer actually receives", and its content went to two external consultant engagements (2026-08-27 report; the R384 3D re-review). **No record of a specific buyer/industry recipient exists** — every honest-status field says `REAL_BUYER: 0`; all candidates UNCONTACTED; `PORTFOLIO_COMMERCIAL_STATE.json` does not track P-28 at all.
2. **The technical problem is recorded and quantified**: dominant clinical obstruction types (tissue ingrowth Z-ratio 1.039; fibrous debris 1.072) sit **below the 1.1 kill-threshold ratio** (reflection coefficients 1.9–3.5 %) — "the kill condition appears to be triggered by the physical properties of the most common obstruction types"; air (ratio 3800) and calcification (5.13) are detectable but are minority obstruction types. The reconciliation **downgraded the consultant's kill verdict to PARTIALLY_CONFIRMED** ("kill-condition conclusion requires the dossier's actual detection model… reframe as feasibility risk requiring empirical test") and V2 discloses "HIGH FEASIBILITY RISK … Kill condition NOT confirmed — a frequency-dependent phantom experiment is required." So: **contested-but-unrefuted, empirically resolvable, never engine-killed** (no cemetery entry).
3. **Disposition conflict (must be surfaced, never silently resolved):** engine-side R382 disposition says P14 is **RETIRED** ("absent from DOWNLOAD/, the buyer manifest, README and the master ZIP") with CEO rationale preserved verbatim, while the R384 CEO directive explicitly kept **all 15 packages on the public release** — so the retired package is live on the public buyer surface today. This is exactly the internal/external ambiguity the directive's §18 exists to remove. Fix path = an explicit distribution record + disclosure, NOT deletion (history preserved; Art. XI).
4. The 1.1 kill threshold is a consultant/CEO-stated figure, not an engine-recorded number — it must carry `consultant_stated` provenance, not silent promotion to measured fact (Art. XXVII).

---

## 13. Conflicts between artifacts (complete list found)

| # | Conflict | Where |
|---|---|---|
| C1 | Sequential `PACKAGE_ID_REGISTRY.json` fixture allocations collide with real historical IDs (registry P-16/P-24 = fixtures vs portfolio P-16/P-24 = real packages) | engine `PACKAGE_ID_REGISTRY.json` |
| C2 | `PORTFOLIO_COMMERCIAL_STATE.json` candidate set ≠ external 15-package set (no P-26/P-27-R1/P-28 entries; "P-04" means a different technology there) | engine |
| C3 | P-27-R1 novelty-citation lineage mis-attribution (cited searches belong to the old SMP-catheter P-27) | `R370/claim_level/ALL_CLAIMS.json` |
| C4 | R382 RETIRED disposition vs R384/R387 public release shipping P14 | engine disposition vs portfolio repo |
| C5 | "T2-CONFIRMED via PyTissueOptics" (dossier) vs execution artifacts absent (not reproducible from repo) | R370Q dossier vs tree |
| C6 | "improvement-loop outcome KILLED_GEOMETRY_INVALID" (CEO reading) vs shipped base geometry VALID (kill applies to the mutation) — plus the separate synthetic R383 case-4 kill that can be misread as the package | portfolio MODEL records |
| C7 | `transfer_posture: SPONSORED_VALIDATION` (manifests) vs `REAL_BUYER: 0` / `transfer_ready: false` (release gates) — commercial label vs technical state, needs explicit non-conflation | both repos |
| C8 | Historical IDs exposed on buyer surface without company designations | PDF headers/footers |
| C9 | PatSnap "novelty testing completed" (management) vs measured never-executed searches (auth/balance failures) | conversation vs artifacts |
| C10 | P-24 `SYNTHETIC_LOOP_VERIFIED` unique non-NONE state vs "zero REAL_LOOP_VERIFIED portfolio events" headline — states must stay separated, never collapsed | buyer repo LOOP_STATE |

---

## 14. Required corrections (what implementation must do — and must NOT do)

1. **Create `LEAD_PORTFOLIO_IDENTITY_REGISTRY.json`** (engine repo) with the four company designations (+ P14 as separate historical/experimental entry referencing the same schema); historical IDs untouched; folders untouched; every other artifact references it. Fix C8 by *adding* the commercial layer, never renaming.
2. **Restore the Patent-Bear novelty artifacts from the archive branch** into a dedicated `NOVELTY_EVIDENCE/` provenance directory (byte-identical copies from `origin/archive/rounds-R309-R383`, sha256 recorded, source commit recorded — Art. XI/XII: restoration-from-history, not manufacture). Build `NOVELTY_ASSESSMENT.json` per package with the directive's schema; the P-27-R1 and PatSnap rows get the honest unavailable states (C3, C9). Never a global NOT_ESTABLISHED→ESTABLISHED replace; prior state preserved in the versioned record.
3. **P04**: create the concept/architecture/implementation separation record (P04_HARDENING or within the package's new canonical record); preserve the dead mutation verbatim; record the shipped-base VALID verdict + the R390 valid rebuild as the pending new-version candidate (CEO release decision, Art. XXXIX); no geometry is "fixed" to make anything green (C6).
4. **P08**: assemble the explicit stage-by-stage `ENERGY_BUDGET.json` (every loss, every evidence class, UNKNOWNs carried); forbid module-vs-system efficiency conflation; no platform claim (C5).
5. **P11**: consolidate the causal chain + ASD baseline + 0-established-advantage honesty + 2 unestablished differentiators into the canonical package record; decisive experiment as 12-element falsification contract.
6. **P13**: build the baseline-vs-self-referencing benchmark specification around the recorded failure evidence (P-25/KA-014), the drift-target MODEL_DERIVED status, and the §12 measurement field list; language guard (no drift-free/self-calibrating).
7. **P14**: `P14_EXTERNAL_DISTRIBUTION_RECORD.json` (external_distribution=true; recipient_class=industry_evaluator with the honest "public release + consultant engagements, REAL_BUYER: 0" basis; current_scientific_status=REVIEW_REQUIRED; commercial_lead=false); the R382/R384 conflict disclosed verbatim inside it (C4). No retrospective rewrite, no deletion.
8. **Per-package buyer-architecture record** (the 10-step sequence of §13), `TECHNOLOGY_MATURITY.json`, `DECISIVE_EXPERIMENT.json` (12 fields), `TRANSFER_STATE.json` (9-state ladder, TECHNICAL_REVIEW start state), `VALUE_OF_INFORMATION.json`.
9. **`LEAD_PORTFOLIO_4_MANIFEST.json`** enumerating the four packages reproducibly.
10. **Cross-artifact consistency tests** (hermetic, in `tests/`): registry ↔ package records ↔ PDF identity lines ↔ maturity/novelty/loop states ↔ P14 record; wrong number/ID/name/version/maturity/novelty/physical-validation/experiment-state/hash all fail loudly.
11. **C1/C2 are disclosed in the audit and bounded by tests** (the lead-registry is authoritative for the four+P14; the legacy registries are labeled non-authoritative for lead identity rather than edited — history preserved).
12. Nothing in the buyer-distribution repository is modified this round (Art. XXXIX release protocol is a separate, explicitly-triggered operation).

## 15. Files that must remain immutable (verified this session, hashes on record)

- All frozen-corpus r370 package files (both repos) — package PDFs, `PACKAGE_MANIFEST.json`, `MATURITY_BASIS.json`, `ENGINEERING_TRACEABILITY.json`, mutation certificates/addenda.
- All portfolio-repo `MODEL/` artifacts (STEP/STL/GLB/SVGs/manifests/validation reports/lineage evidence) and the 15 ZIPs + master ZIP (pinned by `CANONICAL_RELEASE_MANIFEST.json`, tag `v1.0.0-3D-edition`).
- Historical IDs P-01…P-29 and every hash they anchor: `PACKAGE_MUTATION_CERTIFICATE_*` before/after hashes, `V2_MUTATION_ADDENDUM` hashes, R384/R387 manifest pins.
- `origin/archive/rounds-R309-R383` branch (the novelty-artifact custody source) — restoration copies cite it; the branch itself is never rewritten.
- The R382 disposition record, the R390 reality-event ledger, the consultant reports/reconciliation, the mechanism cemetery, `PORTFOLIO_COMMERCIAL_STATE.json` (CEO-owned).
- Git history of both repositories (no rebase/rewrite/filter on pushed commits; all additions are new files/new commits).

## 16. Proposed implementation plan (post-audit, this session)

1. `LEAD_PORTFOLIO_IDENTITY_REGISTRY.json` + `LEAD_PORTFOLIO_4_MANIFEST.json` (engine repo root).
2. `NOVELTY_EVIDENCE/` — restored Patent-Bear artifacts (P-07/P-16/P-24: R359 search + evidence graphs, R361 assessment rows, R365 passage analysis, R368 final gate) with `RESTORATION_PROVENANCE.json` (source branch, commit, per-file sha256 before/after).
3. Per-package canonical records under `LEAD_PORTFOLIO_4/P04…P13/` (+ `P14/`): `NOVELTY_ASSESSMENT.json`, `TECHNOLOGY_MATURITY.json`, `DECISIVE_EXPERIMENT.json`, `TRANSFER_STATE.json`, `VALUE_OF_INFORMATION.json`, `BUYER_SEQUENCE.json`, plus package-specific hardening records (P04 geometry separation, P08 `ENERGY_BUDGET.json`, P11 causal-chain consolidation, P13 benchmark spec) and `P14_EXTERNAL_DISTRIBUTION_RECORD.json`.
4. `tests/test_r403_lead_portfolio_integrity.py` — cross-artifact consistency + immutability guards (audit-probe style, like R402's pinned audit attacks).
5. Full local suite re-run, commit with the R403 message, push via PAT, CI green, worklog update.

**Honest limits:** no new measurements are created; no novelty conclusions are invented; the four packages remain ENGINEERING_DEFINED with zero physical validation; the buyer repo is untouched; the P-27-R1 novelty gap and PatSnap unavailability are recorded as open owner actions, not resolved by this round.
