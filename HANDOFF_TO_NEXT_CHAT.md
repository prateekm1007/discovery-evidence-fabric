# HANDOFF TO NEXT CHAT — Discovery-Evidence-Fabric / Toscanini Program

> **Read this file in full before writing any code or running any command.**
> This handoff supersedes all prior conversational context and REPLACES the
> 2026-08-17 CereVasc-era handoff (that content is preserved in git history at
> any pre-R385B commit). It was rewritten in response to the independent external
> coder audit of 2026-09-01 (audit directive "Move 1": the handoff must state the
> actual state, or the next session starts from a false premise — the old
> handoff was 15 days stale, which was a real defect of exactly that class).
>
> **Generated:** 2026-09-01, R385B correction cycle; **updated same day by R386** (canonical release chain — §0.5),
> **by R387** (CI genuinely green, STL defects closed, release `R387-3D-QUALITY-EDITION`,
> tag `v1.0.0-3D-edition`), and **by R388** (pipeline distillation + legacy archive — §0.7).
> **Constitution:** `EPISTEMIC_CONSTITUTION.md` v1.9.0 — re-read IN FULL before code.
> Read Articles II, III, XVIII, XXV, XXVII, XXVIII, XXXIV, XXXVIII, **XXXIX** with
> particular care (XXXIX governs the release chain and the buyer-distribution
> authority; it is mechanically enforced by `scripts/r386_release_chain.py`).

---

## 0. THE ONE THING THAT CAUSED THE LAST AUDIT CONFUSION — READ FIRST

**This program now lives in TWO repositories. Do not audit one and make claims
about the other.**

| | Engine repo | Portfolio repo (THE BUYER RELEASE) |
|---|---|---|
| URL | `github.com/prateekm1007/discovery-evidence-fabric` | `github.com/prateekm1007/technology-transfer-portfolio-15` |
| HEAD (verify via `git ls-remote`, Art. XXIII; R386 chain at HEAD) | R386 or later | `c83a2a6a` (release `d5f8930` + canonical manifest) |
| Role | The factory: engine code, CAD pipeline, tests, evidence records | The product: 15 buyer-facing technology packages |
| 3D CAD output files | **NOT stored here by convention** ("cryptographic anchors in, regenerable binaries out"): TTP_PACKAGES/ are legacy old-generation trees with 0 CAD files; the delivered 3D-EVIDENCE ZIP is anchored by SHA256SUMS.txt, not committed | **STORED HERE**: every package ships `MODEL/` (parametric source + STEP/STL/GLB/SVG + G-gate certificates + `3D_EVIDENCE/` layer) inside the per-package ZIPs and the master ZIP |

**Second trap — the local workspace is NOT the truth.** Between sessions the
local workspace was rolled back: the engine clone sat at R376 (`c9a9eca3`) and
the local portfolio source tree lost its `MODEL/` layers (0 of 15 locally) even
though BOTH REMOTES carried the full state. An auditor examining the local
trees correctly reported "no 3D output exists" — for the trees they looked at.
Per Art. XXIII: **verify state against the remotes (`git ls-remote`, GitHub API)
before believing any local checkout or any summary, including this one.** The
engine clone in this workspace was re-synced to `5dc153d8` during R385B; the
portfolio release lives in the fresh clone `ttp15-github/` (workspace) and at
its remote.

---

## 0.5 THE RELEASE CHAIN (R386) — the two-repo ambiguity is now AUTOMATED away

Per constitution **Article XXXIX** (v1.9.0), the program has a four-state
release chain with automatic failure:

```
ENGINE REPO  ->  CANONICAL RELEASE MANIFEST  ->  PORTFOLIO REPO  ->  BUYER ZIP  ->  VERIFICATION
```

- Portfolio repo root now carries **`CANONICAL_RELEASE_MANIFEST.json`** (commit
  `c83a2a6a`): pins sha256 of all 924 buyer-surface files (8 root docs + every
  `DOWNLOAD/` file incl. `MODEL/` 3D layers + 15 package ZIPs + master ZIP
  `5044045a…`), the engine build commit `64c5ebca` (builder script sha-pinned),
  the 3D census recomputed from disk, and the final-authority declaration.
- Engine repo root now carries **`ENGINE_RELEASE_REGISTRY.json`**: the
  authoritative index pinning portfolio release commit, manifest sha256,
  master-ZIP sha256, engine build commit, and verification records.
- **The authority rule (verbatim, mechanical):** the buyer-distribution
  repository, not a local workspace and not the engine repository, is the final
  authority for what a buyer actually receives.
- **Anyone can verify the chain from anywhere, without trusting this handoff:**

```bash
python scripts/r386_release_chain.py verify-fresh \
  --engine-url https://github.com/prateekm1007/discovery-evidence-fabric.git \
  --portfolio-url https://github.com/prateekm1007/technology-transfer-portfolio-15.git
```

  (exit 0 + PASS certificate = all four states agree; nonzero = a state
  disagrees, name it in any report). 21 hermetic negative-control tests
  (`tests/test_r386_release_chain.py`) pin that every tampered state fails.
- Honest scope of the chain certificate: **delivery verification from clean
  clones** (the exact bytes a buyer receives). It does NOT claim
  rebuild-from-source reproduction — that remains the open item below (engine
  3D self-containment, CEO decision).
- Any future release MUST follow the Article XXXIX §5 protocol order (both
  repos clean and pushed BEFORE the build; portfolio committed first; manifest
  from the pushed state; registry recorded; clean-clone verification). The
  tool refuses to generate/record on dirty or unpushed trees.

---

## 0.7 R388 DISTILLATION (2026-09-01) — the active tree is now ONE canonical loop

CEO order "distill → verify → productize" executed with a call-graph audit
(imports + quoted path literals + read/write direction + G4 territory-map
constraints):

- **Archived (nothing destroyed):** 112 legacy roots (~6,346 files, 84.4 MB)
  removed from main and preserved byte-identical on branch
  `archive/rounds-R309-R383` (= pre-R388 tip) and in git history. Inventory:
  `ARCHIVE_MANIFEST.json`. Covers R310–R378 round trees, superseded CEREVASC
  research trees (the ones NOT required by G4/ledger), generation-era corpora,
  campaign byproducts, the stale `WORKLOG.md` fork, and a stale A2-era
  submodule gitlink.
- **Kept because load-bearing (evidence in ARCHIVE_MANIFEST.json):** all
  G4-required CEREVASC adjudication trees, R332/R334/R341/R346/R370-family
  frozen buyer-package state, constitution amendment sources
  (R309/R339/R370F), benchmark frozen corpus, tournament_v3 root-hash
  evidence, external corpora custody snapshots, engine runtime state
  (patent_sources meter, canonical_data), discovery_campaigns (service seed
  + test evidence), and the full evidence-custody set (ENGINE_RUNS,
  artifacts, experiments, inventions, elite_v3).
- **worklog.md rotated** to CODER-R371+ (157 KB); full history in git.
- **Docs distilled:** `README.md` + `ACTIVE_PATH.md` now define the ONE
  canonical production loop (stage → module map). No constitution edit was
  needed (R309/R339/R370F kept whole) → G14 acknowledgment untouched.
- NEXT (CEO strict order): buyer-dossier product output → Claude-like UI
  (Next.js/Vercel + FastAPI boundary) → investor demo (P-04, P-08, one
  non-medical).

## 0.8 R389 PRODUCTIZATION (2026-09-01) — the Claude-like product exists

CEO order R389 (8 phases) executed on top of the distilled tree. The engine
loop is UNCHANGED — everything below is product surface + the reality layer.

- **Phase 1 — final pipeline audit** (`R389_PIPELINE_AUDIT.md` +
  `.json`, script `scripts/r389_pipeline_audit.py`): measured stage-envelope
  deltas (13 stages, all KEEP — the four smallest are exactly the epistemic
  safeguards), 37/41 engine modules reachable, the 4 unreachable are
  benchmark/audit tooling referenced by tests. **Zero dead code found** —
  the R388 distillation had already removed it. (Audit-defect lesson
  recorded: the first pass missed relative imports and produced a false
  33-unreachable result — fixed before any classification was drawn.)
- **Phase 2 — REALITY layer** (`discovery_fabric/engine/reality_provider.py`):
  provider-neutral REALITY_PROVIDER contract; World Labs/Marble adapter
  VERIFIED LIVE (operation `666549e8…`, world `695dcc40…`; GLB re-measured
  by trimesh: 177,712 tris; record at
  `TOSCANINI/R389_REALITY_PROVIDER_LIVE/VERIFICATION_RECORD.json`).
  REALITY_MODEL = 10 CEO fields, every datum origin-tagged.
  DESIGN_WORLD ↔ REALITY_COMPARISON ↔ REALITY_WORLD. Structural boundary:
  providers are locked to RECONSTRUCTED/COMPUTATIONAL; MEASURED has exactly
  one door (R370G-attested event, validated); `RealityModel.add()` rejects
  direct MEASURED data (adversarial hole found by self-attack, closed, test-
  pinned). 23 adversarial tests in
  `tests/test_r389_reality_provider.py`.
- **Phase 3 — directional physics:** verified ALREADY BUILT (per the STOP
  rule, no new infrastructure): R378 `evaluator_contract.py` (fidelity
  ladder, provider-neutral, evidence-rank declarations) + R379 direction
  propagation + R383 quantitative margins. The product surface consumes it.
- **Phases 4–7 — the product:** `TOSCANINI_UI/webapp/` (Next.js 15 +
  React Three Fiber; source committed, `node_modules`/`.next` ignored).
  Three experiences: CONVERSATION (one text box, no dashboard clutter) →
  live stage stream → DESIGN/3D (GLB viewer: rotate/zoom/pan/wireframe,
  RECONSTRUCTED badge support) → RESULT (8-step engineering argument:
  problem → observation → evidence → mechanism → design decision →
  technical result → uncertainty → next experiment — all artifact-derived,
  never chain-of-thought) → single DOWNLOAD TECHNOLOGY PACKAGE action.
  Job API per CEO spec: `POST /api/run`, `GET /api/run/{id}/stream`,
  `GET /api/run/{id}/result` — ALIASES of the same session/worker path
  (route-equality test-pinned). Frontend imports ZERO internal Python
  (grep-pinned by test). Engine service: `python3 -m toscanini.server`
  (8788); webapp: `cd TOSCANINI_UI/webapp && npm install && npm run dev`
  (3000, `/api/*` rewritten to the engine service; prod: `ENGINE_API` env).
- **Phase 5 — interactive 3D:** `toscanini/showcase.py::evaluate_parameter`
  → `cad_pipeline.rebuild_with_mutation`: parameter inside its DECLARED
  envelope → REAL sandbox rebuild (new model_id, mutation provenance,
  re-measured geometry, G1–G8 validation, preview GLB served at
  `/api/showcase/{slot}/preview/…`); out-of-envelope or unbound → explicit
  refusal (never clamped). Browser-verified live: 0.6 → 0.45 mm floor
  lumen rebuild, volume 595.92 mm³, preview swapped into the viewer.
- **Phase 8 — investor demos served from the same code path:** slots `04`
  (P-07 drainage floor — medical), `08` (NIR photovoltaic), `09` (UWB
  localization — NON-medical), all from the portfolio buyer-distribution
  repo (Art. XXXIX authority; showcase skips gracefully where that checkout
  is absent, e.g. CI). `tests/test_r389_product_surface.py` (14 tests).
- **World Labs key custody:** `.env.keys` (gitignored) — never committed;
  secret-hygiene test-pinned (payloads + ledger scanned for key material).

## 0.9 R390 REALITY LOOP CLOSED (2026-09-02) — the first REAL external event

CEO directive #6 executed: the loop REAL OBSERVATION → REALITY MODEL →
COMPARISON → DISCREPANCY → CAUSAL HYPOTHESIS → TECHNICAL STATE UPDATE →
MUTATION → NEW DESIGN → RE-EVALUATION, closed LIVE on P-07 with the
proof the CEO demanded — an observation changed a technical decision.

- **The observation:** `EVT-R390-NIST-WATER-VISC-310K` — live NIST
  WebBook acquisition (SRD 69, water, 310.15 K, liquid) = 0.6913 mPa·s
  vs the design basis 1.0 mPa·s ("essentially water at 37 C" — REFUTED;
  1.0 is water near 293 K). +30.9% vs the declared ±20% band. An
  ACQUISITION of externally published measured data, custody-complete
  (raw bytes + sha256 + attestation + frozen-gate validation) — honestly
  labeled, NOT an operator benchtop measurement.
- **The decision change:** `floor_lumen_diameter_mm` 0.6 → 0.5471 mm
  (EQ-1 compensation d·(ηm/ηd)^(1/4), inside envelope [0.3, 0.8]);
  deterministic sandbox rebuild (G1–G8 valid, measured geometry); floor
  conductance restored to ratio 0.99998 (the as-built-at-old-geometry
  +44.7% over-drainage miscalibration is what the observation exposed).
  Canonical package bytes UNTOUCHED (Art. IX) — recorded V2-class
  decision with full provenance.
- **The state:** `REAL_LOOP_VERIFIED` derived mechanically by
  `compute_real_loop_verified()` from the 9-stage Art. XXXVIII causal
  chain in the append-only ledgers (`premium_package_factory/output/
  reality_loop/*.jsonl` — now COMMITTED per the R370U anchor precedent).
  First real event in program history (Art. XXXVII scorecard: REAL 0→1).
- **Code:** `discovery_fabric/engine/reality_loop.py` (acquisition +
  closure; zero LLM; MEASURED only through the R370G one door),
  `scripts/r390_close_reality_loop.py` (`--rehearsal` hermetic /
  `--live`), 17 adversarial tests
  (`tests/test_r390_reality_loop.py`), conftest autouse guard redirects
  both ledgers for every hermetic test (e11 class closed; ENGINE_LIVE=1
  opts out). Product surface: `GET /api/showcase/{slot}/reality-loop` +
  webapp `RealityLoopPanel` (browser-verified, screenshot in
  `TOSCANINI/R390_REALITY_LOOP/live/`).
- **Honest limits:** direct CSF viscosity remains unmeasured — named as
  the next decisive experiment (Art. XXV/XXXIV). Rehearsal closures
  never flip state (same code path, Art. XXXVII).

## 1. VERIFIED STATE OF THE PORTFOLIO REPO (buyer release) — `b978e32c` (release `R387-3D-QUALITY-EDITION`, tag `v1.0.0-3D-edition`)

Chain of commits: `57b9c273` (V2 flat layout, pre-3D) → `d1c802d` (V4 render
hardening) → `fa6131b` (R384: 3D design layer added to every package) →
`d5f8930` (R385: root buyer documents regenerated for the 3D edition + full
release verification rerun) → `c83a2a6a` (R386: canonical release manifest
committed; buyer surface unchanged). **Tag cut at R387:** `v1.0.0-3D-edition` with `RELEASE/LATEST_RELEASE.json`
pointer. R387 rebuilt 3 packages via the canonical path (P-07/P-13 G2b
buyer-visible evidence, P-09 856 KB watertight antenna); 12 packages
byte-identical; chain verified 26/26 from clean clones.

What a buyer receives at `d5f8930` (all independently re-measured by the
R385B auditor session with trimesh + cadquery, not taken from the manifests):

- 15 package directories, flat under `DOWNLOAD/`, each with 6 buyer PDFs +
  JSON dossier metadata + `MODEL/` 3D design layer.
- **CAD census: 143 STEP / 132 STL / 14 GLB / 96 SVG / 63 PNG / 14 parametric
  sources** (~82 MB). 14/15 packages carry full CAD; `06_failure_predictor`
  (P-13, pure-software ML) honestly records `3D_NOT_APPLICABLE` and ships only
  its N/A status files.
- STL quality (auditor-measured): 130/132 watertight. The 2 exceptions are
  disclosed render-only half-shell files in `09_uwb_localization/MODEL/3D_EVIDENCE/`
  (`*_mesh_half.stl`, named as such, disclosed in `3D_EVIDENCE_README.json` with
  the decimation ladder); the shipped antenna STL itself is a 605,108-face
  watertight sweep solid.
- STEP files are real analytic BREP (281 cylindrical / 8 conical / 8 B-spline
  surfaces; zero triangulated shell masquerading as BREP). Kernel:
  cadquery-occt 2.6.1.
- **Every per-package ZIP contains its MODEL/ layer** (auditor re-verified via
  `unzip -l`: 35–68 MODEL entries per package; 06 = 2 honest N/A files). The
  master ZIP (48.0 MB) contains the 8 root docs + 15 package ZIPs.
- Validity classes are honest throughout: `CAD_VALIDATED / COMPUTATIONAL_RESULT`
  for 14/15, `3D_NOT_APPLICABLE` for 06, **PHYSICALLY_VALIDATED: NONE — never
  claimed anywhere**; "render is not validation" is a structural field on every
  shipped 3D artifact. All CAD dimensions are declared
  `ENGINE-DECLARED MODELLED design proposals inside declared envelopes`
  (value_class MODELLED, binding NOT_IN_RECORD_ENGINE_DECLARED) — they are
  design proposals, not evidence claims (Art. XXVII/XXVIII/XXXVIII discipline).
- Root buyer documents (PORTFOLIO_INDEX.pdf, PORTFOLIO master overview,
  PORTFOLIO_RELEASE_REPORT.pdf) were regenerated at R385 to describe the 3D
  edition; release verification G1–G9 ALL PASS with certificates shipped in
  `INTERNAL_QA/` (incl. render QA of every page and byte-reproducibility).
- R382 disposition history: the source tree's buyer-primary subset was
  04 drainage floor / 11 gravity damper / 13 pressure sensor / 08 NIR
  photovoltaic (CEO order); the GitHub release intentionally carries all 15
  in the flat layout per the CEO directive that created `fa6131b`.

---

## 2. VERIFIED STATE OF THE ENGINE REPO — R386 chain at HEAD (R377→R386)

Rounds at HEAD: R377 (invention-substance quality) → R378/R379 (technical
improvement engine, structured technical state) → **R380 (CAD pipeline:
`discovery_fabric/engine/cad_pipeline.py`, sandboxed build programs, G1–G8,
trimesh as independent verifier; live positive demo
`TOSCANINI/R380_LIVE_POSITIVE/three_d/DEMO-DUAL-LUMEN-A`)** → R381 (3D retrofit
of the 15 portfolio packages: `premium_package_factory/r381/` 3,800+ lines,
14 package-specific parametric templates, mutation/KEEP-KILL loop, G9
regeneration reproducibility) → R382 (portfolio disposition + boundary defect
correction) → R383 (analytical equation layer:
`technical_equations.py` — 9 closed-form relations, deterministic binding,
margins, bisection solve, K8 keep gate; live KEEP and KILL demos in
`TOSCANINI/R383_LIVE_QUANTITATIVE/`) → R384 (3D evidence edition + remediation
response to the external FAIL re-review; response record committed under
`EXTERNAL_CONSULTANT_EVIDENCE/R384_3D_EVIDENCE_RESPONSE/`).

**What the engine repo deliberately does NOT contain:** the 3D output binaries
themselves. `TTP_PACKAGES/` (19 directories, old-generation IDs —
P-03_DRAINAGE_FLOOR, P-07_DRAINAGE_PRIORITY, …) are legacy research trees with
**zero CAD files**; the buyer-facing 3D output was built into the portfolio
tree and released through the portfolio repo. Repo convention: regenerable
binaries stay out; cryptographic SHA256 anchors go in. If the CEO wants the
engine repo self-contained in 3D, that is an open work item (see §4), not an
accident.

`TOSCANINI_UI/` contains only `sessions.json`. The committed service code is
`toscanini/` (server.py, gateway.py, sessions.py, problem_builder.py — HTTP+SSE
orchestration from the pre-R377 MVP). **No frontend is committed anywhere.**

---

## 3. RECONCILIATION WITH THE EXTERNAL CODER AUDIT (2026-09-01)

The audit's verdict — "the claim 'the current build tree already contains
validated CAD for 14/15 packages' is not supported by the repository" — was
**correct about the trees it examined and wrong about the release**. Precisely:

| Audit claim | Verified reality (R385B, evidence-based) |
|---|---|
| 3D in TTP_PACKAGES: 0 of 18 | TRUE (19 dirs, 0 CAD files) — but these are legacy old-generation trees, never the release vehicle |
| 3D in the DOWNLOAD ZIPs buyers receive: 0 of 15 | **FALSE for the pushed release** — all 15 ZIPs at `d5f8930` contain MODEL/ (re-verified by direct ZIP listing). TRUE only for the rolled-back LOCAL source tree the audit effectively observed |
| "14/15 validated CAD" is unsupported | The claim (R384 commit message, referring to the release tree) is supported at the portfolio remote: full census above, G1–G9 certificates, independent trimesh re-measurement 130/132 watertight, 14 parametric sources re-read line-by-line |
| Handoff contains the false 14/15 claim | The handoff contained **no such claim** — it was 15 days stale (2026-08-17 CereVasc era), which is the same defect class and worse; fixed by this rewrite |
| Moves 2–4: run CAD on P-07 drainage / P-24 gravity damper / P-27-R1 pressure sensor | **Already shipped** at `fa6131b`/`d5f8930` (R381): P-07 4/4 watertight STLs, P-24 8/8, P-27-R1 7/7 (auditor-measured); these are 3 of the 4 R382 buyer-primary packages |
| Move 5: regenerate buyer ZIPs with THREE_D_DESIGN | **Already shipped** (R384 ZIP rebuild + R385 root-doc regeneration, G1–G9 PASS) |
| TOSCANINI UI 0% | Frontend: TRUE (none committed). Backend: a committed service exists (`toscanini/`); no FastAPI, no committed Next.js app |

Note on package naming (caused audit-internal inconsistencies): portfolio
DIRECTORY numbers and historical package IDs are different axes
(04_drainage_floor = P-07; 11_gravity_damper = P-24; 13_pressure_sensor =
P-27-R1; 06_failure_predictor = P-13). They are bound permanently in
`PORTFOLIO_IDENTITY_REGISTRY.json` and never renumbered.

The genuine lessons the audit taught, accepted and acted on:
1. **Claims must be repo-anchored.** "Build tree" was ambiguous; a claim
   without a repo + commit hash + verification path invites exactly this
   failure. This handoff now anchors every claim.
2. **A stale handoff is a live defect**, not a documentation nit.
3. The engine repo is not self-contained in 3D output — declare it or fix it
   (open item below).

---

## 4. OPEN ITEMS (honest, no ordering implied except where noted)

1. ~~CEO decision — tag the portfolio release.~~ DONE at R387
   (`v1.0.0-3D-edition`; pending CEO acceptance is now the tag itself, not
   the act of tagging).
2. **CEO decision — engine-repo 3D self-containment.** Either sync the 3D
   output into the engine repo (or a portfolio mirror inside it), or record
   the portfolio repo as the canonical 3D home (one paragraph in the engine
   README would suffice). NOTE (R386): the *ambiguity* part of this item is
   now closed mechanically — `CANONICAL_RELEASE_MANIFEST.json` + `ENGINE_RELEASE_REGISTRY.json`
   declare the portfolio repo as the distribution authority and the chain
   verifier fails on any disagreement; what remains open is only the CEO's
   choice on physically mirroring the 3D binaries into the engine repo.
3. **TOSCANINI frontend.** Zero committed UI. The 3D buyer layer is complete
   in the portfolio repo, the backend service exists (`toscanini/`), and the
   R388 distillation cleared the working tree — UI work is UNBLOCKED and is
   the next CEO-ordered deliverable (Claude-like single-screen UX;
   Next.js/Vercel frontend + FastAPI boundary over the long-running engine).
4. **Physical validation: NONE.** 0 physical observations, 0 external
   validation events — recorded honestly everywhere (Art. XXXVIII). The
   07_self_powered_sensing revival still awaits its $3K shaker test; that is
   reality-side work, not portfolio polish.
5. **PAT rotation** (CEO action, pending since R270): live credentials remain
   in tracked files of this private repo. See `CREDENTIALS_AND_MODELS.md`
   (read AFTER this handoff; do not reproduce its contents anywhere).
6. **Known engine-side technical debts disclosed in R383:** only the
   dual_lumen_tube template family participates in the geometry feedback loop;
   equation chaining not implemented; multi-radius models fall back to state
   values (recorded).

---

## 5. NON-NEGOTIABLE RULES FOR THE NEXT SESSION (unchanged)

1. Re-read `EPISTEMIC_CONSTITUTION.md` v1.9.0 IN FULL before writing code.
2. Verify repo state from the REMOTES (`git ls-remote` / GitHub API), never
   from local checkouts or summaries (Art. XXIII/XXXIX). For the buyer
   release specifically, run the chain verifier from clean clones:
   `python scripts/r386_release_chain.py verify-fresh ...` (Art. XXXIX §3).
3. The verifier never trusts the claimant (Art. III): any green gate must be
   re-derivable by an independent instrument (trimesh for STL, fresh rebuild
   for CAD, `unzip -l` for ZIP contents).
4. PAT and API keys never enter new commits; run the secret scan before every
   push (`tests/test_secret_scanning.py` + pattern scan).
5. No claim of physical validation, ever, without reality-produced evidence
   (Art. XXXVIII).
6. Append every work session to `worklog.md` (this repo) and the workspace
   worklog (`/home/z/my-project/worklog.md`).

---

## 6. WORKSPACE PATHS (this machine, subject to rollback — see §0)

- `/home/z/my-project/discovery-evidence-fabric/` — engine clone (resynced to
  `5dc153d8` during R385B).
- `/home/z/my-project/ttp15-github/` — fresh clone of the portfolio release
  (`d5f8930`), used for the R385B independent audit.
- `/home/z/my-project/technology-transfer-portfolio-15/` — legacy portfolio
  SOURCE tree; **currently rolled back to a pre-3D state (0 MODEL dirs)** — do
  not use as evidence of anything; the release truth is the portfolio remote.
- `/home/z/my-project/portfolio/` — a SECOND stale portfolio checkout
  (R384-era `a30ee9c`, dirty) — same rule: not evidence of anything. Run
  `python scripts/r386_release_chain.py drift --repos <paths...>` to name all
  standing trees that disagree with the remotes; both stale trees DRIFT by
  design of the tool's report (local workspaces are non-authority, Art. XXXIX).
- `/home/z/my-project/scripts/` — generation/verification scripts
  (r381…r386); `r385_root_docs_regeneration.py` is now committed to this
  repo's `scripts/` as well.

*Historical note: the CereVasc-era program description (150 inventions, 15
companies × 10 moat positions) and the 2026-08-17 state tables previously in
this file are superseded by the above; they remain retrievable from git
history. The constitution and protocol documents they referenced continue to
govern.*
