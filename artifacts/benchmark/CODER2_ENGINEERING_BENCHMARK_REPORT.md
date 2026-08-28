# CODER 2 — ENGINEERING BENCHMARK REPORT

**Generated:** 2026-08-28T02:49:58.767251+00:00
**Owner:** Coder 2 (independent benchmark & quality system)
**Benchmark corpus:** technology-transfer-portfolio-15 @ 2e96b27 (FROZEN, read-only reference)
**Audited generator:** discovery-evidence-fabric discovery_fabric/engine (Coder 1)

---

## 1. The question

> **Does an automatically discovered invention produce an engineering
> technology-transfer dossier at the same substantive level as the
> 15 packages already produced?**

## 2. Answer

```
NO — not yet. (Structure: YES. Substance: NO.)
```

The automatic pipeline reliably produces the COMPLETE package structure — 15/15 runs released all six PDFs, manifests, traceability, maturity basis and ZIPs, with zero cross-package contamination, zero V&V honesty violations, zero naked numbers and a working hash-bound replay. On structure and integrity the engine matches the gold standard.

On SUBSTANCE, every one of the 15 benchmark dossiers falls below the frozen corpus on multiple depth dimensions: 7 dimensions fail across all 15 runs. The single REAL end-to-end run (F_SMOKE_REAL_P01, live LLM synthesis) fails 7 of the same dimensions — the gaps are systemic to the engineering-depth layer, not artifacts of the rehearsal fixtures.

## 3. Benchmark setup

| Item | Value |
|---|---|
| Corpus packages | 15 (8 V2 / 7 V1) |
| Contract thresholds | corpus-derived (min/median/max), 8 section contracts, R1-R4 derivation rules recorded per threshold |
| Benchmark inputs | 15 Coder-2 survivor fixtures across all 11 engine domains, 5 evidence items each (corpus floor density) |
| Drive path | Coder 1's real automatic pipeline (EngineRun post-RANK, rehearsal-labeled per Art. XXXVII) |
| Runs audited | 15 (completeness OK) |
| Batch verdict | **BENCHMARK_FAIL** |

## 4. What PASSED (integrity layer — equal to the gold standard)

| Control | Result | Evidence |
|---|---|---|
| Cross-package contamination | **PASS** — 0 violations | L1 global-id / L2 id-universe / L3a input-signature layers; 3 engine template sentences correctly classified as genericness, not contamination |
| V&V separation | **PASS** — 0 violations across 15 runs | verification ≠ validation enforced; no fake results |
| Numerical provenance (hard gate) | **PASS** — 0 naked / unsupported numbers | every nontrivial number classed or UNKNOWN |
| Independent replay | **PASS** — 0 broken hash/evidence links | chain hashes re-verified against shipped engineering objects |
| Artifact consistency | **PASS** | eng spec / maturity counts / traceability chains agree in every run |
| Transfer honesty | **PASS** | transfer_ready=FALSE honestly held everywhere; no collapse |
| Package completeness | **PASS** | 15/15 ZIPs, 15/15 full file sets |

## 5. What FAILED (depth layer — below the gold standard)

| Dimension | Runs failing | Corpus floor | Generated level | Severity |
|---|---|---|---|---|
| ENGINEERING_REASONING_DEPTH | 15/15 | complete CLAIM→…→VERIFICATION chains per design output | 0/3 chains complete — DOs never link to failure modes or verifications | HIGH |
| DESIGN_TRACEABILITY | 15/15 | 9-12 design inputs (median 11) | 3 design inputs per package | HIGH |
| FAILURE_ANALYSIS_DEPTH | 15/15 | 3-9 failure modes with real mitigations | 14 FM rows but 0/14 carry design-control mitigations (all 'NOT ESTABLISHED') | HIGH |
| VERIFICATION_SPECIFICITY | 15/15 | 3-6 verification items with acceptance criteria | 2 items, zero acceptance criteria (all 'NOT ESTABLISHED') | HIGH |
| MANUFACTURING_REASONING | 15/15 | regulatory design input in 15/15 gold packages | no regulatory design input in any generated package | MEDIUM |
| UNKNOWN_DISCLOSURE | 15/15 | 6-9 specific remaining unknowns (46-70 markers) | 1 aggregate unknown entry; below marker floor | MEDIUM |
| EQUATION_APPLICABILITY | 6/15 | >= 3 domain equations with assumptions | 6/15 runs below the equation floor (energy_harvesting: 0); thermal equation lacks assumptions | MEDIUM |

Additional finding (genericness, not contamination): 3 engine template sentences recur across up to 15/15 packages (e.g. "differences are asserted by synthesis and not yet claim-audited..."). The gold corpus carries package-specific prose in these positions. Recorded in CROSS_PACKAGE_CONTAMINATION_REPORT.json as a depth finding.

## 6. Deficiency register (for Coder 1)

| # | Dimension | Evidence (measured) | Severity | Recommended fix (Coder 1 scope) |
|---|---|---|---|---|
| 1 | ENGINEERING_REASONING_DEPTH | 0/3 DO chains complete; design_graph nodes/edges lists empty; gold links DI→DO→FM→VF | HIGH | emit explicit DO→FM and DO→VF edges into the design graph and traceability matrix |
| 2 | DESIGN_TRACEABILITY | 3 DIs vs corpus floor 9 / median 11 | HIGH | derive design inputs from user need + problem + mechanism + constraints + domain patterns (gold carries ~11) |
| 3 | FAILURE_ANALYSIS_DEPTH | 0/14 FMs carry design-control mitigations; mitigations are template 'NOT ESTABLISHED' | HIGH | derive mitigations from the domain registry failure-mode→control patterns per FM |
| 4 | VERIFICATION_SPECIFICITY | 2 VFs, 0 acceptance criteria; corpus floor 3 VFs with criteria | HIGH | verification rows need domain-derived acceptance criteria (MODEL_DERIVED with provenance beats NOT ESTABLISHED) |
| 5 | MANUFACTURING_REASONING | regulatory DI absent in 15/15 generated; gold has one in 15/15 | MEDIUM | emit a regulatory design input from the domain registry regulatory patterns |
| 6 | UNKNOWN_DISCLOSURE | remaining_unknowns register has 1 aggregate entry vs 6-9 specific unknowns in gold | MEDIUM | register one specific unknown per UNKNOWN-class critical parameter + per unsourced threshold |
| 7 | EQUATION_APPLICABILITY | energy_harvesting domain emits 0 equations; thermal equation has no assumptions | MEDIUM | complete the domain equation library (esp. energy_harvesting) and require assumptions per equation |
| 8 | GENERICNESS | 3 template sentences recur across up to 15/15 packages | MEDIUM | inject package-specific prose where the corpus has invention-specific text (novelty, distinguishing features) |

## 7. The one REAL run (live LLM synthesis)

ENGINE_RUNS/F_SMOKE_REAL_P01 (pacemaker, real EuropePMC retrieval + real Mistral synthesis): verdict **BENCHMARK_FAIL**, failing dimensions: ENGINEERING_REASONING_DEPTH, DESIGN_TRACEABILITY, EQUATION_APPLICABILITY, FAILURE_ANALYSIS_DEPTH, VERIFICATION_SPECIFICITY, MANUFACTURING_REASONING, UNKNOWN_DISCLOSURE. The failure profile matches the rehearsal benchmark — the depth gaps are in the deterministic engineering layer (Coder 1's templates), not in LLM synthesis quality. Note: live-mode benchmarking at 15-run scale is credential-blocked (sandbox reset lost the CEO-provided NVIDIA/Mistral keys); re-provision to repeat at scale.

## 8. Limits of this benchmark (honest)

- The 15 benchmark inputs are Coder-2-authored SYNTHETIC fixtures (labeled SYNTHETIC_REHEARSAL=TRUE in every artifact): they measure the deterministic post-RANK pipeline, not retrieval or LLM synthesis depth. The single real run partially covers the live path.
- Gold-side measurements rely on the frozen packages' JSONs and PDF text; three corpus packages render sections whose PDF text extraction is lossy — counts fall back to the JSON structures (recorded per measure, never guessed).
- No benchmark threshold was tuned to any generator output: every threshold is the corpus min/median/max of the same measure (contract records derivation per threshold).

## 9. Reproduction

```bash
# corpus profile + contract (needs read-only corpus clone)
git clone <portfolio-repo> /tmp/benchmark-corpus
python3 -m discovery_fabric.benchmark.benchmark_extractor \
    --corpus /tmp/benchmark-corpus --out artifacts/benchmark
python3 -m discovery_fabric.benchmark.depth_contract

# 15-survivor benchmark (offline, ~2 min)
python3 -m discovery_fabric.benchmark.corpus_runner

# adversarial + regression suite (CI-executable)
python3 -m pytest tests/benchmark/ -q
```

## 10. Verdict summary

```
STRUCTURE / INTEGRITY : at gold-standard level
  completeness, contamination, V&V honesty, numerical provenance,
  replay, artifact consistency, transfer honesty — all PASS

SUBSTANTIVE DEPTH     : below gold standard
  7 depth dimensions fail 15/15 runs
  1 real live-synthesis run fails the same dimensions

BATCH VERDICT         : BENCHMARK_FAIL

BOTTOM LINE           : the machine writes honest, complete,
  traceable but SHALLOW dossiers. The distance to the gold
  standard is concentrated in 8 specific, fixable depth gaps
  (section 6) — all inside Coder 1's engineering-spec layer.
```
