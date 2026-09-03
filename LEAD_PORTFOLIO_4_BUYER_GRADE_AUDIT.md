# LEAD PORTFOLIO 4 — BUYER-GRADE VERIFICATION AUDIT (R404)

**Round:** R404 — verification of the four lead packages as buyer-grade assets
**Date:** 2026-09-04
**Base commit audited:** `135fd74f` (R403, certified on origin/main)
**Directive:** CEO R404 — "The next task is to establish whether the four lead packages are actually buyer-grade, not simply well documented."
**Scope rule honored:** no new infrastructure was built this round; every artifact below is evidence, a canonical record, or a test pin. One exception class: the restoration script + custody record for recovered evidence (that is evidence custody, not machinery).

---

## 0. Constitution

`CONSTITUTION_READ_FULLY: YES` — EPISTEMIC_CONSTITUTION.md v2.0.0, all 1,947 lines, re-read before touching the repository (Preamble, Discovery Imperative, Articles I–XXXIX, Discovery & Invention Articles XL–LXIII, Four Constitutional Layers, WORLD_CLASS_DISCOVERY_GATE).

## 1. What R403 certified — and what it did not

R403 certified the **test suite** and the **record layer** (identity registry, novelty records, experiment contracts, consistency tests — 38 tests, CI-certified at `135fd74f`). It did **not** certify novelty, patentability, engineering feasibility, physical feasibility, commercial value, or clinical utility. This round treats every R403 claim as a claimant's statement (Art. III) and re-derives the load-bearing facts from primary artifacts.

**One R403 audit error was found and corrected this round (Art. XV/XXXI):** the R403 ENERGY_BUDGET stated the R310/R311/R312 tissue-optics execution artifacts "DO NOT EXIST in the repository or its git history." **That was wrong.** They exist in git history (commits `e3b6adfd`/`35514d0a`/`f01ae2d1`; deleted from the working tree at R388 `8cb6ff3b`) and are now restored byte-identically with sha256 + blob-sha1 custody under `LEAD_PORTFOLIO_4/P08/VERIFICATION_EVIDENCE/`. The lesson is recorded in the restoration provenance: *an audit that searches only the working tree may declare git-recoverable evidence missing.* The novelty restoration (R403) searched git history; the energy-budget audit did not apply the same discipline to its own domain.

## 2. Novelty-evidence resolution (directive item 2)

Search performed over: the working tree, all reachable branches (main, archive/rounds-R309-R383, r401/empirical-canonicalization, runtime-state), 999 commits, 189 patent/novelty-named files ever committed, restored artifacts, and content search for the four technologies' identity markers.

| Package | Patent-Bear | PatSnap | Classification vs management's statement |
|---|---|---|---|
| P04 | **FOUND** — R359 search artifacts (496/50 hits, CONDITIONAL, closest US20240207499A1) restored, sha256-bound | attempted, never executed (documented balance/auth failures) | management's report is **artifact-supported** for Patent-Bear; PatSnap REPORTED_BUT_UNLOCATED |
| P08 | **FOUND** — R359 (40/0 hits) + R365 passage-level 0-of-5-elements analysis restored, hash-bound | same | same |
| P11 | **FOUND** — R359 (34/6 hits) + R368 narrow-claims refinement restored, hash-bound | same | same |
| P13 | **NOT_FOUND** for this technology — no search artifact in the full reachable history; the R370 ledger's "P-27-R1" citation is the old SMP catheter's search (lineage mis-attribution, C3) | never configured (not on the R354 roster) | **REPORTED_BUT_UNLOCATED** — the evidence-retrieval problem is recorded as exactly that; never converted to "never performed," never to "performed" |

Management's statement was neither overridden nor silently ratified (directive item 3): what survives in the repository is recorded per package, and P13's state is the honest evidence gap with its exact remediation (a fresh search, PatSnap meter 2/20 remaining at last recorded state; free sources EPO/Lens available).

## 3. P08 — the numerical contradiction, RECONCILED (directive item 4)

**The reported ~1050 µW and ~121 µW are the same fluence under different (area, efficiency) assumptions:**

- **1050 µW** = `verified_power_output_uW_assuming_1cm2_PV_100pct_conversion` = 1.049054 mW/cm² × **1.0 cm²** × **100 %** — the R310 4-model disagreement map's reference-detector conversion (the preregistered phantom detector is literally "PV cell at z=5mm, 1 cm² active area"). The field name records its own assumptions.
- **121 µW** = 1.049054 mW/cm² × **0.384845 cm²** (shipped KEEP receiver, independently re-measured 38.4845 mm² at R404) × **0.30** (GaAs-class EXTERNAL_PRECEDENT assumption).

The contradiction was born at **R332**, which re-labeled the reference conversion "~1050 μW power output (derived from fluence × area × efficiency, MODELLED)" without the 1 cm²/100 % qualifiers, and propagated through the R370Q dossier exports. The 1050 figure is not reproducible as a claim about the shipped receiver and must never be quoted as system output.

**The canonical calculation** (ENERGY_BUDGET.json v2.0): `P_electrical = Phi_det × A_receiver × eta_cell`, every input carrying value/unit/source/evidence_class/calculation; fluence inputs are the three archived anchors (1.049054 R310 MC / 1.415645 R311 actual PyTissueOptics v2.0.1 / 1.146949 R312 50k ladder — preregistration-hash-bound, CI-overlap verdict, all within the published Jacques 2013 range 0.5–2.0); receiver area is a re-measured computational result; **eta_cell is UNKNOWN**.

**The canonical buyer figure: UNKNOWN.** The conditional modelled band is **121–163 µW** under explicitly stated assumptions (archived fluence × measured area × GaAs-class 0.30). Presentation rule: one canonical statement, never "verified power."

**Discrepancies after this round:** D1 RESOLVED (above). D2 OPEN — the 500 µW device target (BUYER_DEFINED pass rule) vs the conditional band on the shipped 0.3848 cm² receiver: a ~4.3× area-equivalent engineering decision (area / fluence / efficiency / target revision), owner-gated; the decisive-experiment falsifier explicitly routes an in-band measurement to that decision, not to falsification. D3 partially resolved — the chain now exists in one artifact with the simulation evidence archived; stages 1 (real source), 4 (encapsulation), 5 (targeted-cell efficiency), 8 (power electronics) remain UNKNOWN.

## 4. P04 — independent geometry audit (directive item 5)

Not trusting the recorded VALID (Art. III): the shipped base model was **rebuilt deterministically from the committed template and the full G1–G9 gate battery re-executed** (`GEOMETRY_REVERIFICATION_EVIDENCE.json`):

- **FAILED_MUTATION** — floor_lumen 0.6→0.8: `KILLED_GEOMETRY_INVALID` **REPRODUCED** (G4 min wall 0.1 < 0.15 measured on the rebuilt solid). The kill stays in history, preserved verbatim in the shipped buyer package MODEL/ artifacts.
- **CURRENT_GEOMETRY** — shipped base (3.0 OD / 1.1 primary / 0.6 floor / 1.0 offset / 100 mm): ALL gates SATISFIED on the fresh rebuild; measured min wall 0.2 mm; volume 583.55 mm³.
- **GEOMETRY_EVIDENCE** — fresh-rebuild gate statuses + measurements, every value measured on the built solid.
- **ENGINEERING_CONCLUSION** — INDEPENDENTLY CONFIRMED: the shipped geometry is genuinely valid and the recorded kill is genuinely a kill. The mutation's failure is an implementation failure (Art. XXIX) — it does not kill the architecture, the concept, or the shipped model. CAD validity is COMPUTATIONAL_RESULT only, NOT physical validation; extrusion process capability remains unmeasured.

The same re-run verified the other three packages' key quantities: P08 receiver 38.4845 mm², P11 damping gap 0.3→0.18 mm (KEEP), P13 diaphragm 0.12→0.07 mm (KEEP) — all four base models valid on fresh rebuilds.

## 5. P11 — the real baseline (directive item 6)

The comparator is explicitly specified and recorded: **the ASD (anti-siphon device) as the incumbent real baseline + the standard valve catheter as the null arm, on the identical bench instrument** (Art. XLVII). The R339-recorded protocol (mock CSF loop, 3 arms, 4 postural pressures, 10 runs, blinded, $15K/8 weeks) is lifted into the 12-element falsification contract, with the directive's "real ASD device, not a model" requirement stated in the uncertainty field.

Mechanism plausibility vs demonstrated performance is separated explicitly: the five-step causal chain is MODELLED (plausibility); **0 established advantages** over ASD (differentiation audit verdict counts: ESTABLISHED 0 / UNESTABLISHED 2 / FALSE 2 / DISADVANTAGE 2); the two unestablished differentiators are promoted to the experiment's primary endpoints; the honest modeled finding (ASD closer to target flow in 3/4 postures) is quoted verbatim, not hidden. No benefit is claimed anywhere ahead of the comparative measurement.

## 6. P13 — the lineage, restored (directive item 7)

`LEAD_PORTFOLIO_4/P13/LINEAGE_AUDIT.json` — the five directive fields:

- **Predecessor:** P-25, the self-referencing piezoresistive pressure sensor (born R336 as autonomous candidate CAND-002; survived 6 admission attacks; promoted to P-25).
- **Failure:** R337 computational falsification FAIL — 67.8 % common-mode cancellation measured in-model, but residual 3.45 mmHg error vs the 2.0 mmHg threshold; **biofouling (3 µV/day, exposed element only) and asymmetric creep are non-common-mode and pass through the bridge**; T1-FAIL at R337, cemetery at R347 (KA-P-25-CEMETERY-001, DC-P-25-001), dead re-confirmed at R370J (CF-004).
- **Causal implication:** self-referencing ALONE is insufficient for absolute-pressure accuracy in a fouling environment; the failure does not falsify the common-mode cancellation itself, does not kill the mechanism family (Art. XXIX), and conditions re-admission on addressing the non-common-mode channel.
- **New architecture:** the current P13 is the same dual-element family (0.07 mm diaphragm + shielded reference die, CAD independently re-verified), re-admitted at the R370 corpus build under the reassigned P-27-R1 label. Design deltas: diaphragm 0.12→0.07, recorded mitigations "periodic recalibration + spare capacity," hermeticity spec. **What did NOT change:** the non-common-mode channel is not repaired — "periodic recalibration" is the P-25 cemetery entry's own OPEN boundary question carried forward as a mitigation label. **Governance gap disclosed:** no cemetery-waiver/DC-P-25-001-satisfaction artifact exists for the re-admission.
- **Remaining uncertainty:** the recalibration/anti-fouling question (still open, zero physical measurement of any variant), reference-element stability, cycling endurance, the absent prior-art search, and the frozen dossier's lineage defects (below).

**The predecessor failure had partially DISAPPEARED from the buyer-facing record:** the frozen dossier's system_architecture carries a mis-attributed narrative ("R1 fix: original P-27 suffered from chronic drift; R1 redesign adds self-referencing bridge" — the original P-27 was the SMP catheter; the bridge was born in P-25), and the frozen dossier contains **zero** mentions of biofouling or non-common-mode drift — the predecessor's exact measured kill channel. Both defects are machine-pinned engine-side (`test_r404_buyer_grade.py` asserts the frozen text still contains the wrong narrative and zero biofouling mentions, so the defect cannot silently drift while the release chain schedules the fix); the correction of record is the LINEAGE_AUDIT + the R403 benchmark specification. The predecessor failure does not kill the descendant by inheritance — but the paired-die benchmark's fouling arm lets it kill the architecture **by measurement** if the channel dominates (the directive's both-hands rule, satisfied).

## 7. Buyer-surface identity audit (directive item 8)

Measured state (`BUYER_SURFACE_IDENTITY_AUDIT.json`): the buyer-distribution release (Art. XXXIX authority, v1.0.0-3D-edition) uses folder numbers + **historical IDs** (P-07/P-16/P-24/P-27-R1) as package identity via PORTFOLIO_IDENTITY_REGISTRY v2.0; **no commercial designation appears anywhere on the buyer surface.** The commercial layer (P04/P08/P11/P13) exists only in the engine-side canonical records, where historical IDs are confined to machine-readable provenance fields.

Ambiguity traps catalogued and pinned: commercial P13 (pressure sensor) vs **historical P-13 (adaptive valve, portfolio folder 02)** — different technologies; commercial P04 (drainage floor) vs historical P-04 (catalytic clearance, folder 03); the P-27-R1 label's two histories; model IDs (pm:…) as a third layer.

Remediation: the commercial-designation migration of the buyer surface is an **Art. XXXIX release-chain operation** (both repos clean/pushed before build → portfolio-repo-first commit of regenerated buyer docs with commercial identity lines and historical IDs demoted to provenance fields → manifest → engine registry → clean-clone verification). This round records the gap and the authoritative mapping the regeneration consumes; **zero buyer-repo bytes were touched.**

## 8. Claim-to-evidence matrices and decision chains (items 9/10)

Every lead package now carries `CLAIM_EVIDENCE_MATRIX.json` (P04: 6 rows, P08: 7, P11: 8, P13: 7) — each row: CLAIM → SOURCE → EVIDENCE_CLASS → VERIFICATION → UNKNOWN → EXPERIMENT — and `DECISION_CHAIN.json` (current maturity → next experiment → expected information gain → evidence required → commercial state after PASS → commercial state after FAIL). A buyer can inspect why every important sentence exists; every UNKNOWN stays UNKNOWN (machine-checked: matrix unknown-fields may not contain VERIFIED/ESTABLISHED).

## 9. Final classification (item 12) — no forced PASS

| Package | State | Deciding facts |
|---|---|---|
| **P04** | **READY_FOR_TECHNICAL_EVALUATION** | geometry independently re-verified valid (kill reproduces); novelty artifacts FOUND + hash-bound; no unresolved contradictions; decisive experiment specified but uncosted (owner-gated) — a technical evaluator can assess it honestly today |
| **P08** | **REQUIRES_ENGINEERING_REPAIR** | D1 resolved and the simulation chain is now the strongest evidence layer of the four — but D2 is decisive: the shipped design cannot meet its own recorded 500 µW acceptance target under recorded assumptions (121–163 µW conditional band; ~4.3× area-equivalent gap), and the canonical deliverable power is UNKNOWN (η unknown) |
| **P11** | **READY_FOR_SPONSORED_VALIDATION** | the only package with a recorded, costed decisive experiment ($15K/8wk, 3-arm vs REAL ASD, blinded); comparator explicit; plausibility vs demonstrated advantage separated; the honest modeled disadvantage quoted |
| **P13** | **REQUIRES_EVIDENCE_REPAIR** | no search artifact for this technology (REPORTED_BUT_UNLOCATED); the frozen buyer dossier's lineage narrative is mis-attributed and omits the predecessor's measured kill channel (biofouling: 0 mentions); the cemetery re-admission lacks a recorded waiver — the CAD itself is valid (engineering is not the defect) |

**P14 is NOT in the four-lead portfolio** (item 11): its external-distribution record is preserved unchanged (sha256-pinned against the R403 committed blob by test); nothing was altered to improve the four-package metrics; its classification field records the separation explicitly.

No package is classified above its evidence. The two repair classifications are the honest costs of the contradiction and the erasure this round surfaced.

## 10. Verification battery this round

- Independent geometry re-verification: 4/4 base models valid on fresh deterministic rebuilds; P04 kill reproduced (`scripts/r404_geometry_verification.py` → `GEOMETRY_REVERIFICATION_EVIDENCE.json`).
- Evidence restoration: 5 P-16 simulation artifacts byte-identical from git history, preregistration-hash-bound (`scripts/r404_restore_p16_verification.py` → `VERIFICATION_EVIDENCE/`).
- Canonical energy budget v2.0 with arithmetic self-checks (121.0/163.4/132.4 µW recomputed).
- Tests: `test_r404_buyer_grade.py` **33/33 PASS**; `test_r403_lead_portfolio_integrity.py` **38/38 PASS** (no regression from the record updates); `test_r402_discovery_integrity.py` **36/36 PASS**.
- P14 unchanged: sha256 == R403 committed blob.

## 11. Open owner actions (unchanged or updated by this round)

1. **P08 D2 engineering decision** (area vs fluence vs efficiency vs target revision) — the single blocker between REQUIRES_ENGINEERING_REPAIR and readiness.
2. **P13 fresh prior-art search** (cheap, parallel to the benchmark).
3. **P13 buyer-surface lineage correction** (release-chain operation): fix the system_architecture narrative, add the biofouling failure channel to the failure-mode table.
4. **P13 re-admission waiver** (or re-run the admission per DC-P-25-001).
5. **Cost/time bases** for the P04/P08/P13 decisive experiments (owner inputs).
6. **Buyer-surface commercial-designation migration** (release-chain operation per the identity audit).
7. The R402-era frozen measurement harnesses (attacker calibration, model contest, benchmark) — still awaiting LLM transport recovery; not blocking this round's records.

## 12. Commit discipline (directive item 13)

Constitution re-read in full before any change; this round's change surface is 100% additive except the four P08 record updates (BUYER_SEQUENCE/TRANSFER_STATE/VALUE_OF_INFORMATION made consistent with the canonical budget v2.0 — old states preserved in the ENERGY_BUDGET version_history and the git history, Art. XI) and the P04 GEOMETRY_SEPARATION addition (additive block); zero historical artifacts deleted or renamed; zero buyer-distribution bytes touched; P14 untouched (hash-pinned); full battery green locally; secret scan of the change surface performed pre-push; PAT transport-only.

The machine's honest summary: **two of the four lead packages are buyer-grade for their next respective steps (P04 technical evaluation, P11 sponsored validation); two are not yet (P08 needs an engineering decision, P13 needs evidence repair) — and every one of those judgments now rests on re-executed evidence rather than documentation.**
