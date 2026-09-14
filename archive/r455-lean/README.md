# archive/r455-lean — Deadweight Elimination (Round R455-LEAN-1-DELETIONS)

**Round:** R455-LEAN-1-DELETIONS (operator directive: "delete the useless code",
executing the EXT-AUDIT-LEAN-R454 deadweight register)
**Method:** `git mv` (Art. LXIV.3 — move to archive → full battery; real deletion
is a later round if the archive proves quiet). History preserved in git (Art. XI).
**Base commit:** 7ae2027bac67d889abcb7bbf6c223b7948955c0a (== origin/main at round start)
**Audit authority:** EXT-AUDIT-LEAN-R454 §B/§C/§E register, §O.6 mandated set,
§O.7/§N do-not-touch list.

## What was archived (accounting)

| Group | Files | py LOC | Audit basis |
|---|---:|---:|---|
| `premium_package_factory/` (superseded buyer-package factory; live compiler is `engine/package_compiler.py` + `invention_bridge/package.py`) | 217 | 72,051 | §C.2, §E |
| `discovery_fabric/prior_art_v2/` superseded version siblings (calibration ×7, obviousness ×6, elite ×2, retrieval_v4, rescue/invention_rescue/claim_attack/patsnap_claim_attack) | 20 | 10,873 | §C.4, §O.6, §E |
| `orchestrator/` dead subsystems (providers/ ×9, provider_capability_registry, provider_health_probe, evidence_identity, triangulation_engine, test/ ×3) | 16 | 4,109 | §C.6, §E |
| `discovery_fabric/r411/` + `r412/` (campaign/gradient/temporal/recovery machinery) | 23 | 10,623 | §C.8, §E |
| `discovery_fabric/benchmark/` unreachable instruments (keep: `__init__`, `candidate_quality`, `invention_quality`, `numerical_provenance`, `equation_integrity`) | 32 | 12,992 | §C.8, §B.1 |
| `discovery_fabric/engine/` dead modules (smoke_e2e, benchmark_dossiers, benchmark_corpus, benchmark_split, blind_protocol, campaign_bridge, loop_chain, release_gate, substance_metrics, model_measurement) | 12 | 3,826 | §O.6, §E |
| `discovery_fabric/engine/invention_bridge/r441_retired/` (Blender render path — R441 disposition executed) | 2 | 754+ | §C.7, §O.6 |
| `discovery_fabric/discovery_modes/{device_failure,opportunity}.py` | 2 | 1,263 | §E |
| Stale authority documents (R389_PIPELINE_AUDIT.{md,json}, RUNTIME_MODULE_PARTICIPATION_AUDIT.json, RELEASE_CHAIN_VERIFICATION_{LOCAL,R387,UNKNOWN}.json, HANDOFF_TO_NEXT_CHAT.md, DEPLOYMENT_CONFIG.json) | 8 | 0 | §C.9, §B.3, §E |
| Dead-surface test files (each pins ONLY modules archived this round) | 48 | ~14,846 | §C.2 "16 test files pinning a dead surface" (count measured higher), Art. LXIV.2 |
| **TOTAL** | **370** | **130,583** | |

Curated Python tree: **267,695 → 151,958 LOC (−115,737 / −43%)**.
Production import closure from the three entrypoints: **unchanged**
(168 files / 90,817 LOC reachable before == after).

## KEPT_BECAUSE (measured deviations from the audit register)

The audit's register was re-measured from the three production entrypoints
before execution. Where the measurement falsified the audit's "unreachable"
claim, or where a retained consumer exists, the module is KEPT with the
explicit Art. LXIV.1 disposition:

1. `orchestrator/coverage_engine.py`, `orchestrator/alternative_ledger.py` —
   `orchestrator/__init__.py` imports them unconditionally, and the live engine
   lazily imports orchestrator submodules during runs ⇒ **runtime-loaded**.
   The audit's "all unreachable" is falsified for these two (Art. XV
   disclosure; the audit's static closure did not model lazy imports).
2. `discovery_fabric/prior_art_v2/{calibration_v2,calibration_v3,novelty_v34,
   retrieval_v3}.py` — hard imports of the retained highest versions
   (`calibration_v3_9`, `elite_v3`); `retrieval_v4` archived in v3's place
   because v3 is the retained chain's dependency.
3. `discovery_fabric/engine/transport_capability.py` — active R451-C1.2 tooling
   (`scripts/r451_route_probe_matrix.py` + `tests/test_r451_transport_capability.py`).
4. `discovery_fabric/engine/improvement_authority.py` — audit §B.2 merge/wire
   decision pending; not a pure DELETE.
5. `discovery_fabric/engine/maturity.py` — live F-series D7 contract
   (`compute_maturity`, Art. LX ladder), CI-chained via
   `test_r399_gates` ← `test_f_series_integration`.
6. `discovery_fabric/engine/causal_correctness.py` — live e21 R8-gate test
   evaluator (`tests/test_e21_series.py`).
7. `discovery_fabric/knowledge_graph/entities.py` — imported by retained
   `graph.py`/`lifters.py`.
8. `discovery_fabric/physics_stack/solver_registry.py` — imported by
   `physics_stack/__init__.py` + retained physics_stack modules.
9. `discovery_fabric/benchmark/{numerical_provenance,equation_integrity}.py` —
   live test consumers (CI-invoked `test_r380_cad_pipeline.py`; e21 series).
10. `premium_package_factory/r374/pathway.py` (+ the two empty `__init__.py`) —
    the canonical cemetery-chain cross-verifier wired into
    `tests/test_cemetery_chain_preservation.py` (an epistemic control; audit
    §M: "This audit removes unnecessary machinery, not necessary epistemic
    protection").

## DO NOT TOUCH — verified untouched (audit §O.7 / §N)

- `epistemic_integrity/` — whole package, byte-identical (§N.1 determination
  still open).
- `engine/{causal_learning,decisive_experiment,reality_calibration,
  reality_ingestion}.py` — §N.2 causal/reality-loop carve-out.
- R453 adaptive-admission logic (`runtime_admission.py` et al.) — untouched.
- Sealed experiment records (R452-A3, R451, r416, R412/CALIBRATION evidence
  trees) — untouched.
- Typed infrastructure-failure vocabulary — untouched.

## Known effects (honest disclosure, Art. XV)

- 19 historical `scripts/r411_*/r412_*` round scripts import the archived
  packages and will not run without
  `git checkout archive/r455-lean -- discovery_fabric/r41x`. Their evidence
  trees (R411/, R412/) are sealed and untouched (Art. XI).
- `scripts/r385_root_docs_regeneration.py` (the R385 buyer-root-docs builder,
  sha-pinned by the release chain) imports the archived factory. Rebuilding
  the R371-era buyer root docs from source now requires git history. Delivery
  verification (the authoritative mode, Art. XXXIX.4) is unaffected — it runs
  from clean clones against the buyer repo, not the factory.
- The R374-era portfolio cannot be regenerated from the live tree; the sealed
  releases remain pinned by `ENGINE_RELEASE_REGISTRY.json` and the buyer
  repository (Art. XXXIX authority).

## Repairs applied alongside the moves

- `tests/test_r401_mechanism_space.py`: `TestReleaseGateCaps` retired with
  `engine/release_gate.py` (the only class importing it).
- `tests/test_f_series_integration.py`: two archived modules removed from
  `D6_SOURCE_FILES` (archived modules are not authoritative sources).
- `tests/test_r440_canonical_package_compiler.py`: the closed
  `compile_package` importer/call-site set narrowed to exactly the bridge
  gate (the archived `smoke_e2e.py` was the only other member — a stricter
  invariant, same contract).
- `.github/workflows/epistemic_certification.yml`: the FULL-tier path filter
  `premium_package_factory/**` → `archive/r455-lean/premium_package_factory/**`.

Retrieval: `git checkout archive/r455-lean -- <path>` or
`git log --all -- <path>`.
