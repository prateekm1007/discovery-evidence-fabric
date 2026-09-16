# EXTERNAL AUDIT — TOSCANINI INTERNAL PLUMBING + DISCOVERY/INVENTION ENGINE

**Auditor:** independent external systems / AI-research / reliability audit
**Date:** 2026-09-16
**Target:** `github.com/prateekm1007/discovery-evidence-fabric`
**Audited tree:** `1750406162381500107f91b6601096185b4dfbf9` (= `origin/main`, verified by `git ls-remote`)
**Production:** `https://prateekm1-toscanini-prod-validation.hf.space` serving `6f1e87c4`
**Governing authority used:** `EPISTEMIC_CONSTITUTION.md` **v2.5.0**, Articles I–LXXIII (72 article headings; XXXVI's text is externalized to `R309/constitution/`)
**`reviewer_provenance`:** `AI_REVIEW` (Article LXVII — this audit is AI-on-AI. It is not independent human or institutional review and must not be scored as such.)

> **Correction to the commissioning brief:** the brief cites "Constitution v2.4.0."
> The ratified version in the tree is **v2.5.0**, amended 2026-09-16 to add
> Article LXXIII. All scoring below is against v2.5.0.

---

## 0. HOW THIS AUDIT WAS PERFORMED (evidence discipline)

Every claim below came from a command I ran or an endpoint I fetched in this
session. Nothing is carried over from a prior audit, a round record, or a
coder's claim. Three of my own intermediate conclusions were wrong and are
corrected inline (§0.1) — they are listed because the corrections change the
findings.

What I actually executed:

| Action | Result |
|---|---|
| `git ls-remote origin refs/heads/main` | `1750406…` — local HEAD == origin/main |
| Unshallow the clone | was **1 commit shallow**; now 1,277 commits of real history |
| Full test suite (`pytest tests/`) | **173 failed, 3421 passed, 58 skipped, 37 errors** in 409.62 s |
| Re-run of failures with tracebacks | 148 failed, 1 passed — classified in §3 |
| `HallucinationGauntlet` (executed, not read) | **18/18 blocked**, `overall_pass: true` |
| `HallucinationGauntletV2` (executed) | **14/14 blocked**, `overall_pass: true` |
| Real `EngineRun` end-to-end, out-of-domain problem | 0.4 s, 34 artifacts, all 16 stage envelopes |
| Production `/api/health` + `/api/showcase` | full readiness tuple, provider ledger, 14 packages |
| Evaluated the production readiness probe locally | `reality_loop_ready = False` |

### 0.1 Three claims of mine that were wrong, corrected

1. **"`reality_loop.py` never existed."** Wrong, and wrong because of my own
   tooling: the clone was **shallow (1 commit, `.git/shallow` present)**, so
   `git log --all` had no history to search. After `git fetch --unshallow`
   (1,277 commits) the truth is: `reality_loop.py` (1,006 lines) and
   `reality_provider.py` (818 lines) **did exist**, were added at R389/R390,
   and were **deleted at `cd6f0fc8` (R410)** as superseded Gen-1 machinery.
   The finding survives, but its shape changes completely (§4.1).
2. **"29 SyntaxErrors are a repo defect."** Wrong. `elite_documents.py:495`,
   `transport_capability.py:572`, `mechanism_space.py:1624`,
   `directional/hypothesis.py:388`, `run_qa.py:160` all use **PEP 701
   multi-line f-string replacement fields**, which require **Python ≥ 3.12**.
   The Dockerfile pins `python:3.12-slim`; CI pins `'3.12'`. My sandbox is
   3.11.2 and the 3.12 build assets are CDN-blocked here. **Not a repo
   defect** — a P2 portability-declaration gap only.
3. **"`epistemic_state: OBSERVED` on a zero-evidence run is a silent
   promotion (Art. XXVIII)."** Wrong. `OBSERVED` is `STATES[0]` — the floor of
   the ladder, the default initializer at `discovery_fabric/a2/classify.py:74`.
   It means "nothing established yet," not "something was observed." No
   violation.

---

## 1. TRUTH RECONSTRUCTION

### 1.1 Identity tuple (all measured)

```
origin/main              1750406162381500107f91b6601096185b4dfbf9
local HEAD               1750406162381500107f91b6601096185b4dfbf9   (identical)
production engine_commit 6f1e87c44f887b1f619b2f788a6d0336f6cca9eb
production drift         GREEN, identity_tamper=false
build_artifact_sha256    98071a71…81a903  ==  running_artifact_sha256   (match)
HF build_context_head    5dc86efb…          (the Space's own repo, not the engine's)
```

`git merge-base --is-ancestor 6f1e87c4 1750406` → **true**. The delta is
exactly one commit, and it is records-only ("Records delta only"). **This is
honest and correct, not drift.** Article LXXI's tuple holds.

### 1.2 Scale

```
tracked files at HEAD            8,690
live engine .py files              288   (138,708 LOC)
test files                         210   ( 76,379 LOC)
tests collected                  3,636   (README claims "2,037+")
top-level round directories         64   (R309 … R477)
```

**Capability ÷ complexity, as §40 demands:** 138,708 LOC of live engine
producing a portfolio of **14 packages in 1 domain family** (§6). By that
ratio the system is heavy. This is the central tension of the audit and it
recurs in almost every score.

### 1.3 Module classification (traced by import, not filename)

| Class | Evidence |
|---|---|
| **ACTIVE_RUNTIME** | 16 stage adapters (`adapters.py:1396-1413`), `run.py`, `toscanini/server.py` + `worker.py`, `package_compiler.py`, `cad_pipeline.py`, `visual_compiler/`, `model_routing.py`, `llm_registry.py`, `physics_stage.py` |
| **TEST_ONLY** | **`reality_ingestion.py`** — imported only by `scripts/archive/r407_reality_loop.py`, `tests/test_r407_first_reality_loop.py`, and a *string literal* in `server.py:346`. Nothing live calls it. |
| **SUPERSEDED but still documented as canonical** | `reality_loop.py`, `reality_provider.py` (deleted `cd6f0fc8`, still named in `ACTIVE_PATH.md` + `README.md`) |
| **QUARANTINED** | `KNOWLEDGE_GRAPH`, `SIMULATION`, `TEE_*`, `INVENTION_CORPUS_GENERATION` (`ACTIVE_DISCOVERY_GRAPH.json`) |
| **DEAD / never called** | `NextBestAction.execute_and_recalculate` — defined at `next_best_action.py:64`, **zero callers repo-wide** |

---

## 2. THE END-TO-END EXECUTION GRAPH (reconstructed, not quoted)

### 2.1 What the code actually does

`STAGE_ORDER` at `discovery_fabric/engine/adapters.py:1440` — **16 stages**:

```
RETRIEVE → FREEZE → PREMISE_GATE → SYNTHESIZE → VERIFY → MECHANISM_SPACE
→ MULTI_SOURCE_DISCOVERY → COLLISION → PHYSICS → ATTACK → CONTRADICTION
→ KILLER_EXPERIMENT → ADJUDICATION → CLASSIFY → NEXT_BEST_ACTION → RANK
```

Then, **outside the stage machine**, inside `run.py`:
R378 improvement pass → R379 technical improvement V2 pass → `_evolution_pipeline`
(fallback only) → package tail → `DISCOVERY_RELEASE`.

### 2.2 P1 — both canonical graph documents are wrong

`ACTIVE_PATH.md` opens by declaring itself *"the single authority for what the
production path IS."* At lines 86–89 it documents **13** stages.
`ACTIVE_DISCOVERY_GRAPH.json` documents the **same 13** and declares
`repo_head: "post-490099e"`.

I diffed them against the code:

```
IN CODE NOT IN DOC: ['PREMISE_GATE', 'MECHANISM_SPACE', 'PHYSICS']
IN DOC NOT IN CODE: []
```

**The single authority for the production path omits three of the sixteen
stages that run in production** — including `PHYSICS`, whose existence the
code comments describe as closing *"the consultant finding: 'the physics
solver is validated code but not part of the live run chain.'"* The document
that exists to prevent exactly this confusion is itself stale. This is the
textbook "stale projection" of §4.

### 2.3 The target loop vs. the real loop

Mapping the brief's 24-arrow target loop onto what exists:

| Target stage | Status |
|---|---|
| PROBLEM → Problem validation | **Thin.** `PREMISE_GATE` is a deterministic rule table: `n_rules_checked: 4`, with the disclosed limit *"a physically false but non-contradictory premise passes this gate."* |
| Retrieval → Evidence → Freeze | **Real.** Multi-source fabric, dedup, entity resolution, publication status, lineage. |
| Evidence binding → Knowledge graph | Binding real; **KNOWLEDGE_GRAPH is QUARANTINED.** |
| Mechanism → Candidates → Diversity | Real code (`mechanism_space.py` 123 KB, `candidate_diversity.py`). No live MMD measurement found on HEAD. |
| Prior-art / collision → Attack → Contradiction | **Real.** `prior_art_v2/`, `engineering_attack.py` (39 KB), `independent_attack.py` (29 KB), `attacker_calibration.py`. |
| Killer experiment | **Real EIG**, correctly wired (§7.1). |
| Adjudication → Classify → NBA → Rank | Run, but **NBA is not authoritative** (§7.2). |
| Candidate improvement | **Real**, wired, once each (R378 + R379). |
| Technical evaluation | **Not a stage.** `physics_ready: false` in production. |
| 3D / CAD | **Real.** `cad_pipeline.py` (80 KB) + visual compiler + visual gate. |
| Experiment / reality boundary | **Machinery deleted**; one static record survives (§4.1). |
| Outcome → Causal update → Re-evaluation | **Salvage path only** (§5). |
| Dossier → Package → Release QA | **Strongest part of the system.** |

**The engine's canonical stage machine terminates at RANK.** Everything the
brief calls the back half of invention — improve, technically evaluate,
experiment, ingest outcome, causally update, re-evaluate — is either
post-stage inline code in `run.py`, a fallback branch, or absent.

---

## 3. THE TEST SUITE — MEASURED, AND SPLIT INTO ENVIRONMENTAL VS GENUINE

Full run: **173 failed, 3421 passed, 58 skipped, 37 errors, 409.62 s.**

I re-ran the 148 reproducible failures with `--tb=line` and classified every
one by root cause. **This split matters — reporting "173 failures" without it
would be a false indictment.**

### Environmental (my sandbox — not repo defects): **~121**

| Count | Cause |
|---:|---|
| 58 | `ModuleNotFoundError: cadquery` — I did not install the ~700 MB OCP wheel |
| 61 | PEP 701 f-string files needing Python ≥ 3.12 (sandbox is 3.11.2) |
| 2 | No LLM credential / no network egress |

### Genuine — reproducible on HEAD: **~27**

| Count | Cause | Verdict |
|---:|---|---|
| **13** | `FileNotFoundError: inventions/INVENTION_GENERATION_V3_MANIFEST.json` | **P1.** Deleted at `6e0d04e1` (R410, *"delete the VERIFIED-dead top-level directories (89 paths)"*), but `tests/test_invention_v3_reconciliation.py:7` still hard-references it. **Dead-code elimination deleted a live test's fixture.** |
| **~15** | `TechStage.tsx`, `DiscoveryPipelineStrip.tsx`, `DeepDive.tsx` missing | **P1.** `components/` has 14 files, none of these three; `test_r433_one_canonical_model.py:598` and `test_r435_product_experience.py:40` require them. Webapp refactored without updating the Python contract tests over it. |
| 5 | `KeyError: 'cost_policy_eligible'` in `llm_registry.py` | **P1.** Field is produced at line 1048 but read on a path where it isn't set. |
| 1 | `test_secret_scanning` RED | **P2 — and read this carefully.** The "hard-coded secret" is `nvapi-poisoned-worker-level`, the repo's **own canary** (`test_r425_worker_env_boundary.py:44`). The secret gate is red on HEAD because it flags its own poison pill. **No credential leaked.** But a permanently-red control trains reviewers to ignore red. |
| 1 | `unclassified trust tiers: ['core','datacite','doaj','ndltd','openaire','unpaywall','zenodo']` | **P2.** Seven retrieval sources outside the trust-tier vocabulary. |
| 1 | `malformed JSON artifacts committed` | **P2.** The R417 defect class, still present. |
| 1 | `'deepseek/deepseek-v4-flash-0731' == 'z-ai/glm-5.3-flash'` | **P2.** Routing pin break — already self-disclosed in the R477 commit message. |
| ~4 | `'OPERATOR_PINNED'=='CATALOG'`, `'NO_TRANSPORT'=='EXTERNAL'`, `POLICY_BLOCKED ∉ (…)`, `NO_KEY ∉ (…)` | **P2.** Provider-state vocabulary drift. |

### Reliability finding

The suite writes **~19 GB to `/tmp`** (it filled the 21 GB sandbox disk
mid-run; I had to run a pruning loop to finish it). No single culprit — it is
per-test temp accumulation across ~2,400 tests. On a normal CI runner this is
a silent disk-exhaustion risk.

---

## 4. P0 FINDINGS

### 4.1 P0-1 — the system's only `REAL_LOOP_VERIFIED` record cannot be regenerated

The Constitution's Article XXXVIII makes `REAL_LOOP_VERIFIED` the strongest
state in the system, and Article LXII makes reproducibility *"part of
discovery."* There is exactly **one** such record:
`TOSCANINI/R390_REALITY_LOOP/`, event `EVT-R390-NIST-WATER-VISC-310K`
(measured η = 0.6913 mPa·s refuted the declared "water at 37 °C" basis;
`floor_lumen_diameter_mm` 0.6 → 0.5471; `loop_verification_state:
REAL_LOOP_VERIFIED`, `real_event: true`).

**What I verified:**

```
$ find . -name reality_loop.py            → (nothing)
$ python -c "from discovery_fabric.engine import reality_loop"
ImportError: cannot import name 'reality_loop' from 'discovery_fabric.engine'

$ git log --all --diff-filter=D -- 'discovery_fabric/engine/reality_loop.py'
cd6f0fc8  R410 audit step 2: delete Generation-1 reality-loop machinery —
          DELETED: reality_loop.py (1,006 lines), reality_provider.py (818) …
```

The only executable that produced the record,
`scripts/r390_close_reality_loop.py`, was **archived** (not deleted) and its
first engine import is the deleted module. It cannot run.

Meanwhile **`ACTIVE_PATH.md` and `README.md` at HEAD still name
`discovery_fabric/engine/reality_loop.py::acquire_nist_water_viscosity` and
`::close_reality_loop` as the canonical production modules for the reality
loop.** The file that declares itself the single authority for the production
path points at a module that was deleted 67 rounds ago.

**Why this is P0 and not a documentation nit:** the project's single most
important epistemic claim — *"reality changed a technical decision"* — is now
an unfalsifiable artifact. Nobody can re-derive it, re-run it, or attack it.
Under the project's own Article LXII (*"a discovery that cannot be
reconstructed is not a fully certified discovery"*), that record's status
should be **downgraded to UNREPRODUCIBLE**, not left at `REAL_LOOP_VERIFIED`.

**Corrective note (in fairness):** R410's deletion was itself
constitutionally disciplined — it recorded `DELETED`/`ARCHIVED_TO` per
Article LXIV.1 and relocated `_conductance_ml_per_min_mmhg` verbatim. The
failure is that the **documentation and the health probe were not updated in
the same change**, which is exactly what Article LXIV.1 exists to force.

### 4.2 P0-2 — `reality_loop_ready` is permanently false, from a stale file probe

`toscanini/server.py:344-346`:

```python
_reality_ok = all(
    (REPO_ROOT / "discovery_fabric" / "engine" / f).exists()
    for f in ("loop_chain.py", "reality_ingestion.py"))
```

I evaluated this exact expression against the tree:

```
reality_loop_ready = False
  loop_chain.py         exists=False      ← archived to archive/r455-lean/ at 82d67625 (R455-LEAN-1)
  reality_ingestion.py  exists=True
```

`git log -S 'loop_chain.py' -- toscanini/server.py` → last touched at
`a2b1f6f8` (**R414**). The probe has not been updated since the file it
checks was archived at **R455**.

Production confirms it: `"reality_loop_ready": false`.

Two defects in one line:
1. It is a **file-existence probe presented as a readiness signal** in the
   operational health contract. Two files on disk is not "the reality loop is
   ready."
2. It points at an **archived module**, so it can never go true — while
   `product_status` simultaneously reads `"Discovery ready"`.

### 4.3 P0-3 — the generational invention loop never runs on the happy path

`_evolution_pipeline` (`run.py:2328`) is the real closed loop: generations,
causal delta, re-evaluation through the *same* gauntlet instruments, and an
information-gain stop rule. Its own docstring states the entry contract:

> *"called from `run()` **ONLY** when the standard path produced no package"*

Verified at the call site (`run.py:620-622`):

```python
standard_path_packaged = bool(self.package_report and self.package_report.get("complete"))
if not standard_path_packaged and _ev.evolution_enabled():
```

**The strongest learning machinery in the system is a salvage path.** A
candidate that survives gets exactly one R378 improvement pass and one R379
technical improvement pass, then ships. It never enters a
mutate → re-evaluate → compare-against-previous-version loop.

This is *the* capability the brief names as the known gap
(*"candidate → evaluate → understand failure → mutate → re-evaluate"*), and
the code to do it **exists and is wired** — it is simply gated behind failure.

### 4.4 P0-4 — the Constitution's one immutable gate has no live implementation

The Constitution closes with `WORLD_CLASS_DISCOVERY_GATE`: *"One immutable
constitutional gate. It cannot become GREEN merely because code coverage is
high,"* listing 20 required measured checks.

```
$ grep -rln "WORLD_CLASS_DISCOVERY_GATE" --include=*.py . | grep -v archive
./scripts/r444_round_record.py:178    (a string inside a round-record generator)
./scripts/r445_round_record.py:137    (a string inside a round-record generator)

$ find . -iname "*world_class*"
./archive/r455-lean/premium_package_factory/archive/gates/r370k_world_class_dossier.py
```

**The only implementation is archived.** The gate the Constitution calls
immutable is not evaluated anywhere in CI or runtime.

### 4.5 P0-5 — canonical state has no current authority

`CANONICAL_STATE/CANONICAL_STATE_MANIFEST.json` is the only manifest (`find`
confirms no successor). It declares:

> *"No round may claim an artifact exists unless this manifest (or a successor
> manifest) can locate it."*

| Manifest (Round 249) | Measured at HEAD |
|---|---|
| `head_commit: dafdeb1a…` | `1750406…` |
| `tracked_file_count: 6615` | **8690** |
| Constitution `version: 1.5.0` | **2.5.0** |
| `article_count: 35` | **72 article headings** |

The manifest is ~228 rounds stale, and by its own rule **every artifact claim
in the repository is currently unverifiable against canonical state.** This is
an Article X defect (canonical state has one authority) with no authority
present.

---

## 5. WHAT GENUINELY WORKS (measured, not credited from documentation)

An audit that only lists defects is as useless as one that only lists
achievements. These are real and I verified them myself.

### 5.1 The Bayesian EIG engine is real and correctly wired
`epistemic_integrity/invention_loop_engine/bayesian_eig.py` implements true
expected information gain — `EIG = H(prior) − E[H(posterior)]` — with priors,
likelihoods, posterior entropy per outcome, and an **epistemic class on every
input** (`MODEL_DERIVED` / `EXPERIMENTALLY_ESTIMATED`), carrying the honest
warning that *"a perfectly implemented Bayesian engine fed invented priors is
still an invented result."* It is wired into the live chain at
`adapters.py:1147` (KILLER_EXPERIMENT). This is genuine instrument work.

### 5.2 The anti-hallucination gauntlet actually blocks — I ran it
| Gauntlet | Result (my execution) |
|---|---|
| `HallucinationGauntlet` | **18/18 blocked**, 0 allowed, `overall_pass: true` |
| `HallucinationGauntletV2` | **14/14 blocked**, 0 allowed, `uses_real_evidence: 13` |

V2's attacks (H19–H32) are genuinely subtle: right number assigned to the
wrong entity, correct data from the wrong version, a teaches-away source cited
as support, a valid source with a fabricated span. Both gauntlets **refuse to
run against production registries** (they raise unless given an isolated
`registry_dir`) — a real fail-closed control.

Two honest deductions: (a) the committed `gauntlet_v2_report.json` says
`uses_real_evidence: 14`; my run measured **13** — a small report drift;
(b) both modules' `__main__` blocks are broken (they construct the gauntlet
without `registry_dir` and raise `ValueError`), so `python -m …` cannot
reproduce the committed reports.

### 5.3 Infrastructure failure is NOT converted into scientific knowledge
My end-to-end run had RETRIEVE die on a TLS error. The system's response:

```json
// final_state.json
"final_status": "MECHANISM_GENERATION_FAILED",
"reason": "the mandatory baseline architecture could not be generated
           (transport-class failure — Art. LXI: infrastructure, never a
           scientific rejection); the problem stays saved and resumable"

// cemetery_update.json
{"appended": false,
 "reason": "not a research kill (infrastructure failure or non-reject
            outcome); cemetery preserved untouched"}
```

**This is exactly right** and it is the single most important negative
control in the whole system: a dead network did **not** create a cemetery
entry, did **not** become `REJECTED_SCIENTIFIC`, and left the problem
resumable. Articles XXI.3, XXV and LXI are mechanically honoured.

### 5.4 The causal-mutation proof is honest about itself
`R458_C1_REALITY_MUTATION_PROOF.json` shows a genuine causal edge: parent
candidate → virtual decisive experiment → `COMPUTED_FAIL` (predicted 10.60 <
required 40.00 mL/min) → **Poiseuille closed-form inverse** `d_new = d_old ×
(Q_req/Q_cand)^¼ = 1.6724 mm` → child with measurably different parameters.
`flip_regression.flip_tested: true` (perturbing the mutation to 1.9888 mm
changes the deficit 40 → 80). It is labelled
`loop_verification_state: SYNTHETIC_LOOP_VERIFIED` with
`proof_fixture: True` **and** the disclosure that the fixture was authored
with the full Poiseuille variable set by design. That disclosure is the
correct move — and it is also why this cannot score high (§8).

### 5.5 The loop demonstrably closes on out-of-domain problems
`R444/BENCHMARK_EXTENSION/RUNS/r401/` — four genuinely unrelated problems
(RL reward hacking, recommender feedback loop, LLM KV-cache fragmentation,
demand-forecast drift). **3 of 4** reached `survivor_reached: True` at
generation 2 with `n_evolution_generations: 1`, `final_status:
EVOLVED_INVENTION_CANDIDATE`. The 4th honestly recorded
`survivor_reached: False` at gen 1 and `INVENTION_UNDER_DEVELOPMENT`. This is
the strongest capability evidence in the repository, and it is honest about
epistemic state (`CANDIDATE_CONNECTION`, `OBSERVED` — never "invention").

### 5.6 Technology transfer is the strongest subsystem
`package_compiler.py` (60 KB) + `invention_bridge/` + `dossier.py` (97 KB) +
the Article XXXIX four-state release chain verifier with 21 hermetic negative
controls, verified from **clean clones only**. Production confirms
`portfolio_ready: true` with `portfolio_commit_pinned == portfolio_commit_running`.

---

## 6. THE CROSS-DOMAIN PROBLEM (measured from production)

Article XLIX requires ≥10 problems, ≥6 domains, ≥2 problems per domain
family. Article LXIX forbids a portfolio concentrated in the domain the
system already knows best.

Production `/api/showcase` returns 14 packages:

```
medical      13   (multisegment flow, adaptive valve, catalytic clearance,
                   drainage floor, phage antibiofilm, self-powered sensing,
                   NIR photovoltaic, catheter navigation, gravity damper,
                   osmotic valve, pressure sensor, acoustic detection)
non-medical   1   (UWB localization — and that one is still
                   "positioning of instruments", i.e. medical-adjacent)
```

**The entire buyer-facing portfolio is one domain family.** The benchmark
split inherits this: 15 packages, of which the **blind holdout is n=2**
(P-01, P-21-R1) — and it benchmarks **dossier artifacts**, not discovery on
new problems. A system could pass it without ever discovering anything.

The four R444 cases (§5.5) are the genuine cross-domain evidence — and they
are ML-systems problems, not the engineering domains the brief lists
(materials, thermal, fluids, energy, electronics, manufacturing, chemical).

---

## 7. ADAPTIVE INTELLIGENCE — THE WEAKEST LINK

### 7.1 The real EIG is wired to the wrong stage
`bayesian_eig.py` computes genuine expected information gain and feeds
**KILLER_EXPERIMENT**. It does **not** feed NEXT_BEST_ACTION.

### 7.2 NEXT_BEST_ACTION is a three-template sorter over hard-coded constants

`orchestrator/next_best_action.py` is 3.3 KB. Its scoring formula is
`gain × p_change × impact ÷ cost − redundancy_penalty`, but **all four inputs
are caller-supplied floats** — the module computes no information gain.

`NextBestActionAdapter.execute` (`adapters.py`) builds at most **3** actions:

| Action | information_gain | p_change | impact | cost |
|---|---|---|---|---|
| attack contradiction | `0.5 × impact + 0.2` (default 0.5) | contradiction's own self-declared value, default 0.5 | default 0.5 | **1.0 constant** |
| run killer experiment | real `eig` ✓ | **0.8 hard-coded** | **0.9 hard-coded** | `eig_per_cost × 2.0` |
| inspect patent claims | **0.6** | **0.6** | **0.7** | **0.5** — all four hard-coded |

Two of the three carry no computed information content at all. The action
space is **3 fixed templates**, not the nine competing actions the brief asks
about — there is no *change material*, no *change geometry*, no *kill
candidate*, no *continue candidate*.

The redundancy term — "have I already learned this?" — is never computed. The
code's own comment says so:

```python
# (In full implementation, this would query the evidence graph)
for action in remaining:
    if action.provider == best.provider:
        action.redundancy_penalty += 0.1
```

And that block lives in `execute_and_recalculate`, which I searched for
repo-wide: **defined at `next_best_action.py:64`, zero callers.** The module
docstring promises *"Executes one action, recalculates."* Production never
calls it.

### 7.3 "Wired but not authoritative" — precisely
NBA output *is* consumed: `run.py:2316` → `final_state`,
`experiment_selector.py:68`, `invention_bridge/package.py` → the dossier. It
is **reporting**, not **control**. The stage chain proceeds to RANK regardless
of what NBA selected. It answers *"what should we do next?"* for the reader,
and changes nothing.

### 7.4 Duplicate scoring authority (Article X)
`toscanini/conversational/nba_controller.py` **re-implements the same formula
from scratch** (its own `score_action`, lines 79–81) and does **not import**
the canonical module — despite its docstring asserting *"one scoring
authority, two sites … it does not invent a second one."* It is a second
implementation, with no test pinning the two copies equal.

Ironically the *conversational* copy has the richer, closed 8-action
vocabulary (`RETRIEVE_MORE_EVIDENCE`, `ATTACK_CANDIDATE`,
`GENERATE_COMPETING_MECHANISM`, `ENGINEERING_ESCALATION`,
`PROPOSE_DECISIVE_EXPERIMENT`, `ASK_CLARIFICATION`, `STOP_HONEST`,
`PACKAGE_READY`). The better action space lives in the product layer; the
engine stage has three templates.

---

## 8. WHAT MIGHT STILL BE FALSE? (§34)

| Claim | Evidence | Counter-evidence | Unproven | Smallest decisive test |
|---|---|---|---|---|
| "The reality loop is closed" (`README`, `ACTIVE_PATH`) | One `REAL_LOOP_VERIFIED` record exists with full R370G custody | Producing module deleted at `cd6f0fc8`; operator script archived and `ImportError`s; `reality_loop_ready: false` in production | That the record is reproducible at all | Restore `reality_loop.py` from `cd6f0fc8^`, re-run `--live`, compare bytes |
| "Discovery ready" (production `product_status`) | `discovery_ready: true`, `llm_transport_ready: true` | `physics_ready: false`, `reality_loop_ready: false`, 9/18 providers `NOT_CONFIGURED`, only `atria` ever called (n=2) | That a *second* provider can carry a real run | Run one problem forcing a non-`atria` route; compare dossier |
| "Causal learning works" | R458: real causal edge, flip regression, honest labels | `SYNTHETIC_LOOP_VERIFIED`; `proof_fixture: True`; fixture authored with the full Poiseuille variable set by design | That it works on a problem **not** designed to have a closed-form inverse | Re-run the R458 chain on a blind problem with no analytic inverse |
| "The engine adapts" | NBA stage runs, emits ranked actions, feeds the dossier | 3 templates, 2 with hard-coded constants, `execute_and_recalculate` never called, output is reporting not control | That any NBA output ever changed a downstream decision | Instrument `selected_best` → assert a stage was skipped/added because of it |
| "Tests pass" | 3,421 passed | 173 failed + 37 errors; ~27 genuine, incl. a deleted-fixture suite and missing webapp components | That CI is green on HEAD | Run CI on `1750406` and publish the result |
| "15-package benchmark proves capability" | Deterministic split, sealed sha256 vectors | Benchmarks dossiers not problems; blind holdout n=2; 13/14 one domain | Discovery capability on an unseen problem in an unseen domain | 10 fresh problems × 6 engineering domains, engine untouched |

---

## 9. SCORECARD (0–10, per §32 definitions)

| # | Benchmark | Score | Basis |
|---:|---|---:|---|
| 1 | End-to-end completion | **4** | Runs and records honestly; my run produced no package; back half is post-stage inline code |
| 2 | Discovery quality | **5** | Real multi-source fabric; no fresh HEAD measurement I could reproduce |
| 3 | Evidence quality | **6** | Dedup, entity resolution, publication status, lineage, per-source health |
| 4 | Evidence binding | **7** | Claim registry + span verifier; gauntlet 32/32 blocked, reproduced by me |
| 5 | Mechanistic reasoning | **5** | 123 KB mechanism space; premise gate is a 4-rule table |
| 6 | Candidate diversity | **4** | Art. XLVIII MMD defined; no live MMD measurement on HEAD |
| 7 | Novelty / differentiation | **5** | `prior_art_v2`, collision engine, Art. XLII/XLVI machinery |
| 8 | Adversarial attack quality | **6** | 39 KB engineering attack + 29 KB independent attack + calibration corpus |
| 9 | Contradiction handling | **4** | `contradiction_queue.py` is 2.3 KB (add / to_dict); feeds an NBA template only |
| 10 | Experiment selection | **4** | Real EIG engine, but wired to KILLER_EXPERIMENT, not to action choice |
| 11 | Failure diagnosis | **6** | R458 shows real diagnosis → causal delta, flip-tested |
| 12 | Candidate mutation | **6** | R378 + R379 wired and real; one pass each, never generational |
| 13 | Causal learning | **5** | Real chain, honestly `SYNTHETIC_LOOP_VERIFIED`; 1 REAL record, unregenerable |
| 14 | Adaptive orchestration | **3** | 3 templates, hard-coded constants, dead controller, reporting not control |
| 15 | Model utilization | **3** | 18 providers configured; 1 ever called; 9 no credentials; free-tier only |
| 16 | Model / provenance integrity | **7** | Routing ledger, `code_commit` in every artifact, provider health taxonomy |
| 17 | Engineering representability | **6** | 107 KB engineering spec, 88 KB equations, SOURCE_FACT/COMPUTED/MODELLED/UNKNOWN |
| 18 | Simulation / technical evaluation | **3** | `physics_ready: false`, `wired_solver_importable: false`; simulation "not authorized" |
| 19 | Reality-boundary correctness | **6** | Art. XXXVIII structurally enforced, labels honest — but the one REAL record is unregenerable |
| 20 | Benchmark integrity | **5** | Deterministic split + sealed vectors; n=2 blind, dossiers not problems, v2 report drift |
| 21 | Cross-domain generality | **3** | 13/14 portfolio medical; 4 ML-domain cases are the only breadth |
| 22 | Reliability | **4** | 173 failed / 37 errors; ~19 GB /tmp; stale probes; dead fixture suite |
| 23 | Reproducibility | **5** | Hashes + commits everywhere; flagship loop unregenerable; gate archived |
| 24 | Technology-transfer package | **7** | Strongest subsystem; Art. XXXIX four-state chain, clean-clone verification |
| 25 | Overall autonomous invention | **4** | Cannot yet take a new problem to a defensible invention unaided |

---

## 10. FINAL EXECUTIVE SCORECARD

```
END-TO-END AI                    4/10
DISCOVERY ENGINE                 5/10
INVENTION ENGINE                 5/10
EVIDENCE ENGINE                  6/10
MECHANISTIC REASONING            5/10
ADVERSARIAL REASONING            6/10
EXPERIMENT ENGINE                4/10
CAUSAL LEARNING                  5/10
ADAPTIVE ORCHESTRATION           3/10
ENGINEERING ENGINE               6/10
REALITY BOUNDARY                 6/10
MODEL / AI INFRASTRUCTURE        3/10
RELIABILITY                      4/10
BENCHMARK INTEGRITY              5/10
CROSS-DOMAIN GENERALITY          3/10
TECHNOLOGY TRANSFER              7/10
─────────────────────────────────────
OVERALL                          4.8/10
```

### 9/10 BLOCKERS
1. **P0-1** — the only `REAL_LOOP_VERIFIED` record is unregenerable; its producing module is deleted while two canonical documents still name it.
2. **P0-2** — `reality_loop_ready` is permanently false from a stale file probe, beside a `"Discovery ready"` banner.
3. **P0-3** — the generational invention loop is gated behind failure; a surviving candidate never mutates and re-evaluates.
4. **P0-4** — `WORLD_CLASS_DISCOVERY_GATE` has no live implementation.
5. **P0-5** — canonical state manifest is 228 rounds stale; no authority exists.
6. **Cross-domain** — 13/14 of the shipped portfolio is one domain family; blind holdout is n=2 and measures dossiers, not discovery.
7. **Adaptive orchestration** — NBA is a three-template sorter; the real EIG engine is wired to a different stage; the controller loop is dead code.
8. **Reliability** — ~27 genuine test failures on HEAD, including a suite whose fixture was deleted by a cleanup round.

### TOP 10 HIGHEST-LEVERAGE CHANGES

| # | Change | Priority |
|---:|---|---|
| 1 | **Un-gate the evolution loop.** Run it on survivors too, with a budget and the existing information-gain stop rule. The code exists; only the `if not standard_path_packaged` condition blocks it. | P0 |
| 2 | **Regenerate or downgrade the R390 real loop.** Restore `reality_loop.py` from `cd6f0fc8^`, re-run `--live`, byte-compare. If it cannot be reproduced, set the record to `UNREPRODUCIBLE` — do not leave it at `REAL_LOOP_VERIFIED`. | P0 |
| 3 | **Wire `bayesian_eig` into NEXT_BEST_ACTION.** Replace the hard-coded `0.8 / 0.9 / 0.6 / 0.6 / 0.7 / 0.5` constants with computed EIG. This is a wiring change, not new architecture. | P0 |
| 4 | **Make NBA authoritative.** Let `selected_best` actually skip/add a stage via the `stage_gate` hook that already exists in `EngineRun.__init__`. | P0 |
| 5 | **Fix the stale probes and the two graph documents.** Regenerate `ACTIVE_DISCOVERY_GRAPH.json` from `STAGE_ORDER` by a test; correct `ACTIVE_PATH.md:86-89`; repair or delete the `loop_chain.py` probe. | P0 |
| 6 | **Delete the duplicate NBA.** Make `conversational/nba_controller.py` import `orchestrator.next_best_action`, or pin the two formulas equal by test. | P1 |
| 7 | **Fix the 27 genuine test failures.** Restore `inventions/INVENTION_GENERATION_V3_MANIFEST.json` (or retire its suite per Art. LXIV.2), update the three webapp component pins, fix the `cost_policy_eligible` KeyError, allowlist the canary in the secret scanner. | P1 |
| 8 | **Rebuild canonical state.** Regenerate `CANONICAL_STATE_MANIFEST.json` at HEAD and make CI fail when it drifts. | P1 |
| 9 | **Stand up a second real provider.** 9 of 18 are `NOT_CONFIGURED` and only `atria` (free tier, 25.8 s) has ever been called. A single free-tier model is not a world-class substrate. | P1 |
| 10 | **Run a genuine cross-domain campaign.** 10 fresh problems × 6 engineering domains, engine untouched, reported per domain (Art. XLIX/LXIX). | P1 |

### MINIMUM 9/10 PATH — the 5 changes that unlock most of it
1. **Un-gate the evolution loop** (#1) → moves Invention Engine, Causal Learning, Candidate Mutation.
2. **Wire EIG into NBA and make it authoritative** (#3 + #4) → moves Adaptive Orchestration, Experiment Selection.
3. **Regenerate the real loop** (#2) → moves Reality Boundary, Reproducibility, and removes the largest honesty exposure.
4. **Fix the stale graph + probes + canonical state** (#5 + #8) → removes the "two answers to the same question" class entirely.
5. **Prove cross-domain breadth** (#10) → the only thing that moves Cross-Domain Generality off 3.

Everything else is P2/P3. **No new registries, no new state machines, no new
frameworks** — items 1–5 are wiring, regeneration and subtraction, consistent
with the repository's own entropy rule.

---

## 11. ROADMAP PHASING

**Phase 0 — Truth reconstruction (week 1).** Exit: `ACTIVE_DISCOVERY_GRAPH.json` regenerated from `STAGE_ORDER` by a test; `ACTIVE_PATH.md` stage list corrected; `CANONICAL_STATE_MANIFEST.json` regenerated at HEAD with a CI drift gate; the R390 record's true reproducibility status established.

**Phase 1 — P0 blockers (weeks 2–3).** Exit: CI green on a fresh commit; 0 genuine test failures; no stale file-existence probe in the health contract; either a regenerated real loop or an honest `UNREPRODUCIBLE` downgrade.

**Phase 2 — Closed-loop invention (weeks 3–6).** Exit: one run where a **surviving** candidate is mutated, re-evaluated by the same gauntlet, and compared against its predecessor — recorded in `INVENTION_LINEAGE.json` with `n_evolution_generations ≥ 2` on a non-salvage path.

**Phase 3 — Adaptive intelligence (weeks 6–9).** Exit: NBA action set ≥ 6 types; every `expected_information_gain` computed rather than constant; `selected_best` demonstrably changes a stage decision; one NBA implementation.

**Phase 4 — Cross-domain proof (weeks 9–12).** Exit: 10 problems × 6 engineering domains, per-domain reporting, domain concentration explicitly checked against Article LXIX.

**Phase 5 — World-class hardening (weeks 12–16).** Exit: `WORLD_CLASS_DISCOVERY_GATE` re-implemented live with all 20 checks; blind holdout ≥ 10 problems across ≥ 6 domains; a second production provider carrying real runs; suite's /tmp footprint bounded.

---

## FINAL QUESTION

> **Does Toscanini currently qualify as a world-class end-to-end AI discovery
> and invention machine?**

# **NO**

**The evidence for that answer:**

I gave the engine a genuinely new technical problem outside its familiar
domain — LPBF thin-wall Inconel 718 residual-stress warpage. It completed all
16 stages in 0.4 seconds and produced **no package**: `final_status:
MECHANISM_GENERATION_FAILED`, `DISCOVERY_RELEASE.status: NOT_A_SURVIVOR`,
`loop_verification_state: NONE`. Retrieval died on a TLS error in my sandbox,
so that particular outcome is partly environmental — but the structural facts
are not environmental at all:

- The generational invention loop **cannot run on a surviving candidate**
  (`if not standard_path_packaged`). The capability the brief identifies as
  the core gap is present in code and gated behind failure.
- The **one** `REAL_LOOP_VERIFIED` record in the entire system cannot be
  regenerated — its producing module was deleted 67 rounds ago, and the two
  documents that declare the canonical production path still point at it.
- The Constitution's **one immutable gate has no implementation** outside
  `archive/`.
- **Canonical state** is 228 rounds stale, so by its own rule nothing in the
  repository is currently verifiable against it.
- **13 of 14** shipped packages are one domain family, and the blind holdout
  is **n=2 dossiers** — a benchmark a system could pass without discovering
  anything.
- Adaptive orchestration is a **three-template sorter** whose controller
  method has zero callers, while the genuinely Bayesian engine sits wired to a
  different stage.

**What the "NO" is not saying.** This system's *epistemic integrity machinery
is genuinely exceptional*, and I want that on the record because it is the
part most audits would miss. I watched a network failure occur mid-run and the
system **refused to manufacture knowledge from it**: no cemetery entry, no
`REJECTED_SCIENTIFIC`, problem left resumable, reason string explicitly
citing Article LXI. I executed both hallucination gauntlets myself and they
blocked **32/32** attacks built from real evidence with real hashes. Every
artifact carries `code_commit` and content hashes. Causal mutation is
flip-tested. Synthetic and real loop states are machine-separated and
`REAL_LOOP_VERIFIED` is derived, never assigned. Almost nothing in this
repository is a lie — including the parts that are bad news for the
repository.

That is why the honest verdict is **NO** rather than a polite *partially*:
the failure is not one of integrity, it is one of **capability**. Toscanini is
currently a **world-class honesty machine wrapped around a mid-tier discovery
engine**. It will not tell you a false thing about an invention. It cannot yet
reliably *produce* one from a new problem, mutate it when it fails, and prove
the result across domains. The Constitution already knows this —
Article XXXV's own honest gap section says *"NONE of the 5 slots have this
loop fully operational."* The distance to 9/10 is not a rewrite. Per §10, it
is **five wiring and regeneration changes**, most of which un-gate machinery
that already exists and already works.
