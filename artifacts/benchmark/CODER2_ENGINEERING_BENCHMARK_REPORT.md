# CODER 2 — ENGINEERING BENCHMARK REPORT

**Generated:** 2026-08-28T03:20:04.562450+00:00
**Owner:** Coder 2 (independent benchmark & quality system)
**Benchmark corpus:** technology-transfer-portfolio-15 @ 2e96b27 (FROZEN, read-only reference)
**Audited generator:** discovery-evidence-fabric discovery_fabric/engine (Coder 1) — A/E15-series engine at current HEAD, plus the pre-A-series baseline recorded below

---

## 1. The question

> **Does an automatically discovered invention produce an engineering
> technology-transfer dossier at the same substantive level as the
> 15 packages already produced?**

## 2. Answer

```
PARTIALLY — structure and integrity at gold-standard level;
depth much improved by the A/E15 engine, but not equivalent:
the engine's own quality gate rejects 12/15 independent benchmark
inputs, and the released dossiers still fail 2-3 depth dimensions
plus sparse reasoning closure on the real capstones.
```

## 3. Headline results (current engine)

| Measure | Result |
|---|---|
| Independent benchmark inputs | 15 (Coder-2 fixtures, all 11 domains, 5 evidence items each) |
| Released by the engine's own E15-H gate | **3/15** |
| Engine-rejected (fail-closed, honest) | **12/15** — "no viable survivor (quality-rejected)" |
| Depth verdict on released packages | {'BENCHMARK_PASS': 0, 'BENCHMARK_CONDITIONAL': 0, 'BENCHMARK_FAIL': 3} |
| Cross-package contamination | **PASS** — 0 input-content violations |
| V&V / numerical provenance / replay / consistency | all PASS on every released run |
| REAL capstone A12 (p01, live LLM) | **BENCHMARK_FAIL** — failing: ENGINEERING_REASONING_DEPTH, VERIFICATION_SPECIFICITY, UNKNOWN_DISCLOSURE |
| REAL capstone E15 (p06, live LLM) | **BENCHMARK_FAIL** — failing: MANUFACTURING_REASONING, UNKNOWN_DISCLOSURE |

### Baseline (pre-A-series engine, recorded for regression)

The same 15-input benchmark against the previous engine (HEAD 162ca5d) produced 15/15 releases but **15/15 BENCHMARK_FAIL** with 7 failing depth dimensions: ENGINEERING_REASONING_DEPTH, DESIGN_TRACEABILITY (3 DIs vs floor 9), FAILURE_ANALYSIS_DEPTH (0/14 FMs with design-control mitigations), VERIFICATION_SPECIFICITY (2 VFs, zero acceptance criteria), MANUFACTURING_REASONING (no regulatory DI), UNKNOWN_DISCLOSURE, EQUATION_APPLICABILITY (6/15 below floor). The A-series closed most of these — measured improvement, not narrative.

## 4. What PASSED (integrity layer — equal to the gold standard)

| Control | Result | Evidence |
|---|---|---|
| Cross-package contamination | **PASS** — 0 input-derived violations | L1 global ids / L2 id-universe / L3a harness-known input signatures |
| V&V separation | **PASS** — 0 violations | verification never collapses into validation; no fake results |
| Numerical provenance (hard gate) | **PASS** — 0 naked / unsupported numbers | provenance-record DIs hash-verified against the run's evidence records |
| Independent replay | **PASS** | chain hashes re-verified; linkage chains independently re-derived from the design graph |
| Artifact consistency | **PASS** | eng spec / maturity counts / traceability chains agree |
| Transfer honesty | **PASS** | transfer_ready honestly FALSE everywhere |
| Package completeness | **PASS** | every released run shipped all PDFs + JSONs + ZIP |

## 5. What FAILED or FALLS SHORT (depth layer)

### 5.1 Dominant finding: E15-H rejection rate on independent inputs

12/15 independently supplied survivor inputs were refused release by the engine's own E15-H quality gate ("no viable survivor — all candidates killed or quality-rejected"). Fail-closed is honest and correct behavior — but it means the engine's claimed "AUTONOMOUS DOSSIER EQUIVALENCE, all verdicts PASS" was demonstrated on Coder 1's OWN fixtures (A9-A11: 15/15 floors) and does not transfer to independent inputs: the release yield on Coder 2's inputs is 3/15. Either the gate is over-strict for legitimate survivors, or most independent inputs genuinely produce sub-bar dossiers — Coder 1 should characterize which, and the E15-B deficient-area detail should be surfaced in the release artifacts (currently only counts are recorded).

### 5.2 Remaining depth gaps on RELEASED packages

| Dimension | Runs failing | Corpus floor | Generated level | Severity |
|---|---|---|---|---|
| UNKNOWN_DISCLOSURE | 3/3 released | 6-9 specific remaining unknowns | remaining_unknowns register holds 1 aggregate entry; also fails on both real capstones | MEDIUM |
| MANUFACTURING_REASONING | 2/3 released | regulatory design input in 15/15 gold packages | no regulatory DI in 2/3 released runs and the E15 real capstone (the eng spec now has a regulatory block, but no regulatory design input reaches the DI list) | MEDIUM |
| EQUATION_APPLICABILITY | 1/3 released | >= 3 domain equations with assumptions | 1/3 released runs below the equation floor | MEDIUM |

### 5.3 Real-capstone-only gaps (live LLM path)

- **ENGINEERING_REASONING_DEPTH — hub-concentrated linkage.** The design graph links all 14 failure modes through ONE design output; 1/21 design-output chains close to a failure mode and verification on the E15 capstone (A12: 0/21). The gold corpus distributes DI→DO→FM→VF linkage across the design. Chain completeness is the single largest remaining reasoning gap.
- **VERIFICATION_SPECIFICITY (A12 capstone):** verification rows exist above the count floor but acceptance criteria remain NOT ESTABLISHED.
- **FAILURE_ANALYSIS_DEPTH (both capstones, CONDITIONAL):** failure modes are now invention-specific (A6) but mitigation coverage is partial.

### 5.4 Genericness (not contamination)

Template-chrome sentences: 2 recurring across >=3 packages; pair-shared engine sentences: 2 — including a factually mismatched disclosure ("no closed-loop control is proposed; operates passively open-loop") emitted into an active-control invention's dossier. The gold corpus carries invention-specific prose in these positions. Recorded as depth findings in CROSS_PACKAGE_CONTAMINATION_REPORT.json.

## 6. Deficiency register (for Coder 1)

| # | Dimension | Evidence (measured) | Severity | Recommended fix (Coder 1 scope) |
|---|---|---|---|---|
| 1 | RELEASE YIELD | 12/15 independent inputs quality-rejected by E15-H; rejection detail (which 4 areas) not surfaced in release artifacts | HIGH | characterize gate strictness on independent inputs; emit the E15-B deficient-area list into the rejected run's PACKAGE_FAILED.json |
| 2 | ENGINEERING_REASONING_DEPTH | 0-1/21 DO chains close to FM+VF on real capstones; linkage hub-concentrated on one DO | HIGH | spread FM/VF linkage across design outputs in the design graph (per-DO failure linkage, not one hub) |
| 3 | UNKNOWN_DISCLOSURE | remaining_unknowns register = 1 aggregate entry vs 6-9 specific unknowns in every gold package | MEDIUM | register one specific unknown per UNKNOWN-class critical parameter and per NOT_ESTABLISHED acceptance criterion |
| 4 | MANUFACTURING_REASONING | regulatory block exists in the eng spec but no regulatory DI reaches the design-input list (gold: 15/15) | MEDIUM | emit the regulatory pattern as a design input |
| 5 | VERIFICATION_SPECIFICITY | acceptance criteria NOT ESTABLISHED on the A12 capstone (count floor now met) | MEDIUM | domain-derived acceptance criteria (MODEL_DERIVED with provenance beats NOT ESTABLISHED) |
| 6 | EQUATION_APPLICABILITY | 1/3 released rehearsal runs below the 3-equation corpus floor | MEDIUM | complete the domain equation library |
| 7 | GENERICNESS | template sentences in identity positions; one factually mismatched passive-device disclosure on an active-control invention | MEDIUM | invention-conditional prose; suppress control-architecture boilerplate that contradicts the invention's actual nature |

## 7. Independent verification of Coder 1's equivalence claim

Coder 1's E15 commit message claims "AUTONOMOUS DOSSIER EQUIVALENCE — all ten verdicts PASS". Coder 2's independent measurement neither confirms nor repeats that claim; it bounds it:

- On Coder 1's own fixtures, the engine's internal verdicts may all pass — Coder 2 has not audited those fixtures' releases here.
- On Coder 2's independent inputs, release yield is 3/15 and released dossiers still fail 3 depth dimensions against the frozen corpus.
- The two REAL capstones (live LLM) fail 3 and 2 dimensions respectively — honest, complete, hash-verified, but not yet at the corpus's depth.

## 8. Limits of this benchmark (honest)

- The 15 benchmark inputs are Coder-2-authored SYNTHETIC fixtures (SYNTHETIC_REHEARSAL=TRUE labels preserved): they measure the deterministic post-RANK pipeline. The two REAL capstones cover the live retrieval+synthesis path on 2 inputs only.
- Live-mode 15-run benchmarking is credential-blocked in this sandbox (NVIDIA/Mistral keys lost in the reset; Coder 1's capstones were run elsewhere). Re-provision keys to repeat at scale.
- No benchmark threshold was tuned to any generator output: every threshold is the corpus min/median/max of the same measure.

## 9. Reproduction

```bash
# corpus profile + contract (needs read-only corpus clone)
git clone <portfolio-repo> /tmp/benchmark-corpus
python3 -m discovery_fabric.benchmark.benchmark_extractor \
    --corpus /tmp/benchmark-corpus --out artifacts/benchmark
python3 -m discovery_fabric.benchmark.depth_contract

# 15-survivor benchmark (offline, ~3 min)
python3 -m discovery_fabric.benchmark.corpus_runner

# adversarial + regression suite (CI-executable)
python3 -m pytest tests/benchmark/ -q
```

## 10. Verdict summary

```
STRUCTURE / INTEGRITY : at gold-standard level (both vintages)
  completeness, contamination, V&V honesty, numerical provenance,
  replay, artifact consistency, transfer honesty — all PASS

RELEASE YIELD         : 3/15 on independent inputs (12 honest
  quality rejections by the engine's own E15-H gate)

SUBSTANTIVE DEPTH     : improved from 7 failing dimensions to 2-3;
  real capstones fail reasoning closure (hub linkage), unknown
  disclosure, and (A12) verification specificity

BATCH VERDICT         : BENCHMARK_FAIL

BOTTOM LINE           : the machine now writes honest, complete,
  hash-verified dossiers at NEAR-corpus depth — the remaining
  distance is 7 specific gaps (section 6), concentrated in
  reasoning-closure breadth and the E15-H gate's behavior on
  inputs it did not tune itself against.
```

---

# PHASE 2 (CEO directive: "make your benchmark harder and more independent")

## 11. Phase 2 deliverables (B1-B6)

**B1 — BASELINE FROZEN.** `artifacts/benchmark/baseline/CURRENT_BASELINE.json`
(content hash `db161312c5c50…`, integrity guard + test-pinned). The baseline is
written once and never overwritten; `verify_baseline()` fails on any mutation;
re-audits write NEW files, never touch it.

```
CURRENT_BASELINE = 3/15 RELEASED, 12/15 QUALITY_REJECTED  (committed set)
BLIND SET        = 5/5 RELEASED, 5/5 BENCHMARK_FAIL       (aggregate only)
engine HEAD      = fbd113b
threshold hashes = depth contract + dossier profile, sha256-pinned
```

**B2 — BLIND HOLDOUT SPLIT.** `CODER2_BENCHMARK_SPLIT_MANIFEST.json` +
`BLIND_SET_MANIFEST.json` (hashes only):

| Set | Inputs | Disclosure contract |
|---|---|---|
| DEVELOPMENT_SET | BENCH_01..08 (2 released / 6 rejected) | committed; Coder 1 iterates openly |
| HOLDOUT_SET | BENCH_09..15 (1 released / 6 rejected) | committed before the split — reserved, NOT blind; results at checkpoints only |
| BLIND_SET | 5 Coder-2-authored inputs | content NEVER in the repo; custody outside git (CEO copy under download/coder2_blind/); repo carries sha256 hashes only; results published as aggregates only |

Blind runs execute through the real pipeline into a gitignored directory;
cross-set contamination (blind ↔ committed) = 0 violations. A test scans every
git-tracked file for blind-content 3-grams; the leak check is CLEAN.

**B3 — SEMANTIC CAUSAL REVIEW** (`semantic_causal.py`,
`ENGINEERING_SEMANTIC_CAUSAL_AUDIT.json`). Every chain link is graded
CORRECT / QUESTIONABLE / INCORRECT against the invention's own signature
(independently classified through the Coder 2 lexicon, never the engine's
detect_domain). Any INCORRECT link on a critical chain is a RELEASE BLOCKER.
Detectors: domain-family mismatch, engagement-claim re-verification,
assumption-violation re-verification (APPLICABLE despite laminar/turbulent
conflict = INCORRECT; correctly REJECTED = CORRECT), output-without-inputs,
control-architecture contradiction, FM causally unrelated to model,
verification measuring the wrong physical quantity.

**Measured on the current engine:** 21 INCORRECT critical chains across the 15
committed runs; 2 of the 3 RELEASED dossiers are release-blocked under B3
(BENCH_01: valve-seat-wear failure verified by an occlusion-challenge test —
measures a disjoint physical quantity; BENCH_04: same class). Blind set: 4/5
release-blocked. Examples are machine-cited (chain id + link + both sides'
tokens).

**B4 — SEMANTIC GENERICNESS AUDIT** (`semantic_genericness.py`,
`SEMANTIC_GENERICNESS_AUDIT.json`). Recurring template sentences are mined
across packages (eng spec + rendered dossier PDF, field-position tracked) and
tested PER PACKAGE against that package's own signature for five mismatch
classes: control-architecture, domain, mechanism-negation, operating-mode,
physical-assumption. Calibration against the frozen gold corpus (same
instrument): gold recurring = 36.

**Measured on the current engine:** committed set 176 recurring template
sentences (gold ceiling 36) with 6 semantic mismatches — including THE canonical
defect: "No closed-loop control is proposed: the invention operates
passively/open-loop" shipped into the adaptive-power ACTIVE-control dossier
(BENCH_04) and the on-device-learning dossier; plus CSF-shunt boilerplate
("CSF shunt systems for hydrocephalus management…") shipped into the telemetry,
sensor-array, infusion-pump, neurostimulator, and urinary-stent dossiers where
no CSF device exists. Blind set: 335 recurring, 11 mismatches — including a new class: the
engine's Poiseuille assumption boilerplate ("Newtonian fluid, laminar
regime, RIGID circular lumen, fully developed flow") shipped into a
superelastic-anchor dossier whose own physics is elastic (assumption
contradiction). Any SEMANTIC_MISMATCH is a release blocker (factual
mischaracterization shipped in a dossier).

**B5 — YIELD / DEPTH / CORRECTNESS SEPARATED**
(`tri_measurement.py`, `YIELD_DEPTH_CORRECTNESS_SEPARATION.json`). Three
independent measurements + full non-release attribution:

```
ENGINE_RELEASE_YIELD : 3/15 committed (dev 2/8, holdout 1/7); blind 5/5
DOSSIER_DEPTH        : all 3 released dossiers fail 1-3 depth dimensions;
                       would-be depth of the 12 rejected runs re-measured
                       directly from their persisted eng specs
DOSSIER_CORRECTNESS  : 3/3 released dossiers FAIL (semantic falsehoods;
                       integrity gates all PASS)
ATTRIBUTION          : 12/12 rejections = QUALITY_REJECTED_SHALLOW_OUTPUT —
                       the engine's own gate is honestly rejecting
                       below-corpus-floor output; ZERO over-strict-gate
                       candidates; the problem is GENERATION DEPTH, not gate
                       strictness
```

Blind-set corroboration: 5/5 released (yield is input-dependent — the gate is
not uniformly strict), yet all 5 fail depth AND 4/5 carry semantic
falsehoods, and blind run 02 additionally fails the NUMERICAL_PROVENANCE hard
gate (first hard provenance violation observed on any released run).

**B6 — RE-AUDIT MACHINERY READY** (`reaudit.py`,
`DEFICIENCY_REAUDIT.json`). Threshold integrity is hash-verified against the
frozen baseline BEFORE any before/after comparison (drift = comparison
refused, fail closed). The BEFORE row is frozen; the AFTER row is produced by
re-running the same split + the same thresholds once Coder 1 delivers repairs:

| Deficiency | BEFORE (frozen baseline) |
|---|---|
| RELEASE_YIELD | 3/15 RELEASED, 12 QUALITY_REJECTED (dev 2/8, holdout 1/7; blind 5/5) |
| REASONING_CLOSURE | do→FM closure median 0.048 (1/21 DOs carry FM linkage); hub concentration 1.0 (all FMs on one DO) |
| UNKNOWN_DISCLOSURE | dimension fails 3/3 released; median register 4 aggregate entries vs corpus 6-9 SPECIFIC |
| MANUFACTURING_REASONING | dimension fails 2/3 released; regulatory section present 3/3 but no regulatory DI |
| VERIFICATION_SPECIFICITY | 0/3 dimension fails on released runs (27/27 acceptance pre-registered); real capstones still fail |
| EQUATION_APPLICABILITY | dimension fails 1/3 released |
| GENERICNESS | 176 recurring template sentences (gold 36); 6 semantic mismatches incl. the passive/open-loop and CSF-boilerplate classes |

## 12. Phase 2 notes for Coder 1 (deficiency register EXTENDED)

The original 7-item register stands, now sharpened by B3/B4 measurements:
1. The genericness item is upgraded from "depth finding" to RELEASE BLOCKER:
   the passive/open-loop boilerplate is factually false for active-control
   inventions, and CSF-shunt boilerplate is false for non-CSF devices.
2. A new correctness class exists: verifications measuring a quantity
   disjoint from the failure's physics (seat-wear verified by occlusion
   testing; fatigue verified by a BER sweep).
3. The engine's E15-H gate is NOT over-strict: 12/12 rejections are
   below-corpus-floor output. Fix generation depth, not the gate.

## 13. Phase 2 adversarial hardening of the measurement layer itself

Self-found and fixed during build (Art. XVI/XXX): broken generator expression
silently crashing quantity-family matching; "sensitivity floor" RF/ML lexicon
collision; "ph" substring matching "phantom"; consequence-edge index error
(encrustation→obstruction closure never fired); hub-concentration formula
measured list length instead of DO in-degree; contract floor parser read a
wrong key (all attributions were NOT_MEASURABLE); link-evaluation loop skipped
PRINCIPLE→MODEL and MODEL→INPUT (node-type name mismatch) — caught by the
adversarial test suite, all audits re-run with the fixed evaluator;
negation-wrapped active phrases ("no closed-loop control") suppressed control
contradiction detection — fixed with negation stripping; single-word leak
guard false-positived on common vocabulary — replaced with 3-gram matching.

Suite: tests/benchmark/ = 47 passed (16 prior + 31 Phase 2: every new
detector attacked, clean-content false-positive guards, baseline immutability,
threshold drift, blind-content absence, attribution classes). Full repo suite:
905 passed, 2 skipped, only the 2 documented pre-existing environmental
failures (patsnap rate-limit, secret-scan historical baseline).

## 14. Phase 3 deliverables (B7-B12)

CEO Phase 3 directive, delivered in full. Auditor-only: no engine file
modified, no rejected output repaired, the benchmark was not weakened,
and the frozen baselines were not overwritten.

### B7 — Independent baseline freeze (permanent, double-hashed)

`artifacts/benchmark/baseline/INDEPENDENT_BASELINE_FREEZE.json`:

    BASELINE_RELEASE_YIELD = 3/15
    QUALITY_REJECTIONS     = 12/15

* frozen ONCE, refuses overwrite; canonical-content sha256 inside the
  file (self-verifiable) + byte-level sha256 pinned EXTERNALLY in
  `INDEPENDENT_BASELINE_FREEZE.bytehash` (a file cannot contain the hash
  of its own bytes; `sha256sum` on the committed freeze must reproduce
  the pin);
* HASH-CHAINED to the B1 freeze (B1 content sha256 embedded; freezing
  refuses to proceed if B1 is missing or mutated) — the two freezes
  provably describe the same measurement;
* mutation of the numbers (or of the file bytes with a recomputed
  content hash) is mechanically detected; both hashes are pinned by the
  test suite.

### B8 — Rejection decomposition (no more "shallow")

All 12 rejections decomposed into PRIMARY_BLOCKER + SECONDARY_BLOCKERS
over the CEO's 12-category taxonomy, every row carrying named evidence
(`ENGINE_GATE_RE_DERIVED` — the E15-B evaluator re-run read-only on the
persisted specs — or `INDEPENDENT_CODER2`). Headline finding:

* **12/12 PRIMARY = DOMAIN_REASONING.** The direct gate cause is the
  E15-B MECHANISM_DEPTH FAIL, and the independent corroboration is
  exact: on every rejected run the invention specification's mechanism
  body has the SAME word count as the input mechanism text
  (`mechanism_body_words == input_mechanism_words`, e.g. 21 == 21) —
  the generator passes the input mechanism through with ZERO
  engineering elaboration.
* Secondaries on all 12: CAUSAL_REASONING (independent B3 incorrect
  critical chains) and VERIFICATION_SPECIFICITY (wrong-quantity
  verifications), plus the UNKNOWN_DISCLOSURE depth floor (recorded as
  OTHER with an explicit taxonomy note — the CEO taxonomy has no
  unknown-disclosure category).

### B9 — Blind semantic adjudication layer

Two structurally independent adjudicators (separate code paths and
knowledge bases; no import of the B3/B4 detectors; Coder 1's labels
never inputs — Adjudicator A classifies the physics family with its own
vocabulary from the input signature):

* **Adjudicator A — FIRST_PRINCIPLES** (physics-first): family
  classification, control-architecture consistency, equation regimes,
  failure-mode physics, verification-quantity disjointness;
* **Adjudicator B — SYSTEMS_TRACE** (traceability-first): source-span
  traceability, chain closure, DI->DO->FM linkage, equation ties,
  acceptance quantification.

Seeded random sample of 6 of the 8 released dossiers (3 committed +
5 blind; seed 20260828, recorded). Verdicts per axis:
CORRECT / QUESTIONABLE / INCORRECT. **Disagreements are preserved with
both verdicts — never averaged, never resolved by a third rule** (26
disagreements across 30 axis-verdicts; e.g. Adjudicator A returns
INCORRECT on the adaptive-power dossier for the control-architecture
contradiction while Adjudicator B returns CORRECT on traceability
grounds — both recorded). Residual self-reference risk (both
adjudicators are authored by Coder 2) is disclosed in the artifact; the
external counterweight is B11.

### B10 — Unseen-problem test

4 problems outside the 15-technology corpus, outside the benchmark
fixtures, outside the blind set, never used to tune the evaluator
(hemodialysis graft / dental implant abutment / contact-lens window /
ablation tip class). Content custody outside git (repo carries hashes
only); distinctness mechanically verified (Jaccard < 0.4 vs every
committed AND blind input; zero mechanism 3-grams in any tracked file).

* **REAL mode**: live EuropePMC retrieval WORKS (5/5/5/4 real evidence
  items retrieved per problem); synthesis fail-closed on missing LLM
  credentials -> 0/4 released, **4/4 attributed to EVIDENCE_FAILURE —
  NOT a generation failure** (the engine's fail-closed behavior is
  correct under Art. IV/XXIX). CEO key re-provision unlocks this.
* **REHEARSAL mode (labeled)**: 3/4 released through the full four-stage
  pipeline; the released dossiers fail corpus depth (EQUATION_APPLICABILITY
  2/3, MANUFACTURING_REASONING 3/3, UNKNOWN_DISCLOSURE 3/3) and **3/3
  fail semantic correctness — the wrong-content defect class generalizes
  to problems the engine has never seen**.
* The evaluator is answer-blind: NO expected-answer key exists for
  unseen problems; the instruments are the same frozen property-based
  measurements used for the committed/blind sets, with NO
  unseen-specific thresholds.

### B11 — External human spot-check protocol

`HUMAN_SPOT_CHECK_QUEUE.json` (committed; 8 seeded-random items across
all 3 committed released dossiers) + `HUMAN_SPOT_CHECK_PROTOCOL.md` +
a blind-stratum queue in CEO custody (6 items, content never committed).
Each item is one reasoning chain presented as
claim -> source -> engineering interpretation -> design implication.
Status: **PENDING_HUMAN_REVIEW** — no verdicts fabricated. Verdict
vocabulary: HUMAN_CONFIRMED / HUMAN_DISPUTED / HUMAN_UNCERTAIN.
Ingestion is append-only, duplicate-refusing, queue-immutable, and
aggregates COUNTS ONLY — human review is external evidence and is never
converted into an automated score (pinned by tests).

### B12 — Final audit output (five-way failure taxonomy)

`FINAL_AUDIT_REPORT.json` classifies every failure into exactly one of
GENERATION / AUDIT / BENCHMARK / EVIDENCE / ENGINEERING REASONING
failure so Coder 1 cannot chase the wrong problem:

| Category | Entries | Open |
|---|---|---|
| GENERATION_FAILURE | G1-G4 (12/12 shallow rejections = mechanism pass-through; released depth deficits; blind corroboration; unseen rehearsal depth) | 4 |
| ENGINEERING_REASONING_FAILURE | E1-E4 (21 incorrect critical chains; control-architecture contradiction; domain boilerplate + Poiseuille assumption mismatch; unseen semantic failures) | 4 |
| AUDIT_FAILURE | A1-A2 (9 self-found measurement defects + blind-set purification — FIXED, history retained) | 0 |
| BENCHMARK_FAILURE | BM1-BM2 (blind-input overlap — CLOSED; canonical-registry pollution by Coder 1's test suite — OPEN) | 1 |
| EVIDENCE_FAILURE | V1-V2 (missing LLM credentials block real-mode synthesis — CEO action required; 2 documented pre-existing environmental) | 2 |

Bottom line (unchanged, now with evidence at every layer): Coder 1's
engine runs end-to-end but cannot yet generate dossiers at the depth of
the 15 reference packages, AND its released content carries engineering
falsehoods that generalize to unseen problems. Repair priorities:
(1) elaborate mechanisms instead of passing input text through — this
alone unblocks the 12 rejections; (2) make verification quantities
match failure physics; (3) stop shipping cross-domain boilerplate. The
gate is NOT over-strict. Do not declare victory until the frozen
baseline moves materially upward WITHOUT weakening the benchmark.

## 15. Phase 3 measurement-layer hardening (self-audit)

Defects found by attacking my own Phase 3 implementation, fixed, and
pinned by tests (Art. XVI/XXX):

* **B7 self-reference bug**: the freeze originally tried to embed the
  byte hash of its own file inside itself (mathematically impossible);
  found by my own tamper test before commit, redesigned to the
  external-pin scheme (content hash inside + byte hash pinned beside);
* **B7 pin-path bug**: freezing to a custom path wrote the byte pin to
  the PRODUCTION pin location (caught by the test that freezes to a
  tmp path and then verifies production integrity — the production pin
  was re-derived from the untouched freeze bytes and the test now pins
  both paths);
* **B8 first-pass ranking defect**: independent severity-3 findings
  outranked the gate's own FAIL dimension, mislabeling all 12 primaries
  as CAUSAL_REASONING; corrected to rank the DIRECT gate cause
  (severity 4) first — the decomposition now reflects what the E15-H
  selection actually acted on, with independent evidence as
  corroborating rows and secondaries;
* **B8 genericness extractor contract**: recurrence is per-field list
  length, not a count (TypeError caught on first run);
* **B9 control-architecture scan too narrow**: the passive/open-loop
  template record ships in design-output rows, outside the
  architecture fields — Adjudicator A initially missed the canonical
  contradiction; the ACTIVE side is now the invention's own mechanism
  claim and the PASSIVE side is scanned dossier-wide (and the
  consistent-passive case is verified NOT to fire);
* **B9 test-independence check**: naive text scan of the module source
  false-positived on the docstring's own independence contract —
  replaced with an AST import check;
* **B10 content-leak catch**: the unseen problem set's first draft
  leaked one 3-gram ("interface temperature below") into a tracked
  corpus file — caught by the distinctness screen before any run, the
  mechanism text rephrased, screen re-run clean.

Phase 3 test suite: `tests/benchmark/test_phase3_suite.py` — 34 tests
(freeze immutability + double-hash tamper detection + external
sha256sum reproduction, decomposition taxonomy/ranking/coverage,
adjudicator independence + defect-class catches + false-positive
guards + disagreement preservation, unseen leak screen + distinctness
rejection + EVIDENCE_FAILURE attribution, queue schema + ingestion
validation + no-score-conversion, taxonomy + report completeness).
Benchmark suite total: 81 passed. Full repo suite: 939 passed / 2
skipped / only the 2 documented pre-existing environmental failures.
No new failures introduced.
