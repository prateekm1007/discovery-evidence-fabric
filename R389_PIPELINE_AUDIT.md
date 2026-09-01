# R389 PHASE 1 — Final Production Pipeline Audit

> CEO directive R389: "Perform a final production call-graph audit… Classify
> KEEP / MERGE / REPLACE / ARCHIVE / REMOVE. Do not remove epistemic
> safeguards. Remove duplicate computation, ceremonial stages, legacy
> wrappers, redundant transformations and dead orchestration. The production
> system must have ONE canonical entry path."
>
> Evidence base: `R389_PIPELINE_AUDIT.json` (static AST import graph,
> relative-import aware, adapter registry included) + measured stage-envelope
> deltas on the real run `ENGINE_RUNS/w9_nephrology_hemodialysis_dose_flow_limit`
> + reverse-reference greps for every unreachable module.
>
> Method note (Art. II/XXIV): every claim below is machine-measured, not
> recalled. The first audit pass had a defect — relative imports
> (`from .candidate import ...`) were not resolved, producing a false
> "33 unreachable modules" result. The defect was found, fixed, and re-run
> before any classification was drawn from it (Art. XXXI: the correction and
> its lesson are recorded here).

## 1. One canonical entry path — VERIFIED

```
USER PROBLEM TEXT
  → toscanini/server.py  (HTTP+SSE job surface; no engine internals cross it)
  → toscanini/worker.py  (serialized detached subprocess; flock)
  → problem_builder.build_problem()   (evidence-bound structuring)
  → discovery_fabric/engine/run.py EngineRun   ← THE canonical loop
  → premium_package_factory (dossier + buyer package, gates)
  → Article XXXIX release chain (manifest → portfolio → ZIP → verify)
```

The CLI (`python -m discovery_fabric.engine.run`) is an operator transport of
the same `EngineRun` path — one loop, two transports, zero divergence.

## 2. Stage-level classification (13 runtime stages)

Unique-information delta per stage = number of NEW JSON paths the stage adds
to the candidate envelope (measured, w9 run):

| Stage | Δ paths | Decision it changes | Classification | Rationale |
|---|---|---|---|---|
| RETRIEVE | 59 (root) | everything downstream (evidence base) | **KEEP** | unique: evidence records |
| FREEZE | +21 | evidence custody (Art. II exact binding) | **KEEP** | unique: content hashes, spans |
| SYNTHESIZE | +38 | the invention itself (mechanism map) | **KEEP** | unique: mechanism/intervention/falsification |
| VERIFY | +8 | claim admission (span verification) | **KEEP** | safeguard: verifier never trusts claimant (Art. III) |
| MULTI_SOURCE_DISCOVERY | +88 | candidate diversity (4-search attack) | **KEEP** | unique: destruction/transfer/reality searches |
| COLLISION | +136 | novelty/prior-art decision | **KEEP** | safeguard: prior-art firewall |
| ATTACK | +28 | kill decision (5 attack families) | **KEEP** | safeguard: adversarial gate |
| CONTRADICTION | +14 | blocking-contradiction resolution | **KEEP** (no merge) | feeds ADJUDICATION as a *gate input*; merging would move a safeguard into the verdict stage — the two-actor separation (Art. III) is the point |
| KILLER_EXPERIMENT | +23 | decisive-experiment selection | **KEEP** | unique: hypotheses + priors |
| ADJUDICATION | +31 | final verdict (council checks) | **KEEP** | safeguard: independent verdict |
| CLASSIFY | +4 | epistemic-state assignment | **KEEP** (no merge) | the Art. XXVIII promotion gate; +4 paths is the *cheapest* stage in the loop and the *most* constitutionally load-bearing |
| NEXT_BEST_ACTION | +24 | buyer-facing next steps | **KEEP** | unique: ranked actions w/ cost & decision impact |
| RANK | +14 | portfolio ordering | **KEEP** (no merge with NEXT_BEST_ACTION) | portfolio ordering ≠ next action for a single candidate; different consumers |

**No stage is ceremonial.** The four smallest stages (VERIFY +8,
CLASSIFY +4, RANK +14, CONTRADICTION +14) are precisely the epistemic
safeguards the directive forbids removing. Their information is small in
volume and large in decision weight.

## 3. Module-level classification (41 engine modules)

Measured reachability from the product entry path (toscanini.* →
EngineRun → stage adapters → premium_package_factory):

- **37/41 REACHABLE — KEEP.** Includes both evaluator generations:
  `technical_improvement_engine.py` (improvement-time, R379, feeds run.py)
  and `equations.py` (dossier-time, R383, feeds the builder chain). These
  are NOT duplicates: different inputs (candidate vs final design),
  different stages, different consumers — the two-independent-verifiers
  discipline (Art. III), same pattern as trimesh re-measuring OCCT STLs.
- **4/41 not reachable from the production entry — all referenced by
  governance/tooling, classification KEEP (as tooling):**
  - `benchmark_corpus.py` — benchmark + acceptance scripts, 2 tests
  - `blind_protocol.py` — E16 blind-audit machinery (governance), 1 test
  - `campaign_bridge.py` — benchmark campaign runner, 1 test
  - `smoke_e2e.py` — smoke harness, referenced by test_dossier_bridge
- **REMOVE: none. ARCHIVE: none.** After the R388 distillation (111 legacy
  roots archived), no dead orchestration, legacy wrapper, or unreferenced
  transformation remains in the active tree — this is a measured result,
  not an assumption.
- **MERGE candidates considered and REJECTED (documented per directive):**
  - `technical_equations.py` ↔ `equations.py`: two stages, two consumers
    (see above). Merging couples the improvement loop to the dossier
    builder — a regression risk to a certified-green chain with no
    duplicate-computation payoff.
  - `CONTRADICTION` into `ADJUDICATION`, `CLASSIFY` into `ADJUDICATION`,
    `RANK` into `NEXT_BEST_ACTION`: each is a distinct decision with a
    distinct safeguard role (§2).

## 4. Duplicate-computation check

The one measured near-duplicate — dossier-time re-evaluation of a design
the improvement loop already evaluated — is intentional defense-in-depth
(two independent evaluators, Art. III), not waste. Its removal would
weaken the verifier, which the directive forbids.

## 5. Verdict

> The active path is already minimal for its epistemic guarantees:
> **13 stages, 37 production modules, one canonical entry path, zero
> measured dead code.** Further removal would remove safeguards, not
> ceremony. The correct next move is exactly the CEO's: stop pruning,
> build the product (Phases 2–8).
