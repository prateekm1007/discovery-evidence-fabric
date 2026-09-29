# Discovery Evidence Fabric — Toscanini Program

**Epistemic discovery engine + technology-transfer portfolio factory.**
One governed production loop takes a real problem from live evidence to a
buyer-ready technology package, under the Epistemic Constitution v2.10.1
(`EPISTEMIC_CONSTITUTION.md` — read it in full before writing any code).

The program lives in TWO repositories (Article XXXIX: the buyer-distribution
repository is the final authority):

| | Engine repo (this one) | Portfolio repo (the buyer release) |
|---|---|---|
| URL | `github.com/prateekm1007/discovery-evidence-fabric` | `github.com/prateekm1007/technology-transfer-portfolio-15` |
| Role | The factory: engine code, CAD pipeline, gates, tests, evidence records | The product: 15 buyer-facing technology packages |
| Release | `R387-3D-QUALITY-EDITION` (tag `v1.0.0-3D-edition`) | portfolio commit pinned in `ENGINE_RELEASE_REGISTRY.json` |

Verify the release chain from clean clones (Article XXXIX §4):

```bash
python scripts/r386_release_chain.py verify-fresh \
  --engine-url https://github.com/prateekm1007/discovery-evidence-fabric.git \
  --portfolio-url https://github.com/prateekm1007/technology-transfer-portfolio-15.git
```

## The One Canonical Production Loop

```
PROBLEM → EVIDENCE → MECHANISM → CANDIDATES → ATTACK → INVENTION DIAGNOSTIC
→ IMPROVE → TECHNICAL EVALUATION → 3D DESIGN → DECISIVE EXPERIMENT
→ ENGINEERING DOSSIER → BUYER PACKAGE
```

Module map and gate anchors: `ACTIVE_PATH.md`. There is ONE production path —
no duplicate corpus builders, no alternate release routes. Legacy
round-byproduct trees (R310–R378 era) were archived at R388 to
`archive/rounds-R309-R383` (see `ARCHIVE_MANIFEST.json`; history preserved,
nothing destroyed).

## Active Surface (post-R388 distillation)

```
discovery_fabric/            engine: connectors, discovery modes, engine stages,
                             cad_pipeline (3D), equations (R383 evaluator),
                             prior_art_v2, source_registry, benchmark
orchestrator/                four-search attack, triangulation, provider health
toscanini/                   HTTP+SSE service (server, gateway, sessions,
                             problem_builder, showcase — the UI backend)
premium_package_factory/     canonical package builder: gates, templates,
                             r381 CAD templates, r382 disposition, r371 builder
                             + the R370G reality-event/mutation ledgers
scripts/                     release chain (r386), release build (r384/r385),
                             campaign + measurement tools, r390 reality loop
tests/                       full suite (2,037+ tests, incl. adversarial
                             R386/R387 release-chain controls)
epistemic_integrity/         CI 14-gate certification, registries, ledger,
                             gauntlet, constitution enforcement
CANONICAL_STATE/             G5 canonical portfolio state
TTP_PACKAGES/                legacy old-generation package trees (0 CAD files,
                             kept as provenance record)
TOSCANINI/ TOSCANINI_UI/     live demos (R380 3D, R383 quantitative, R389
                             product + R390 reality-loop closure records) +
                             sessions; webapp = Next.js product surface
ENGINE_RUNS/ artifacts/      run evidence custody
experiments/ discovery_campaigns/ inventions/ tournament_v3/
external_corpora/ elite_v3/  measurement / benchmark / custody inputs
CEREVASC_* (kept subset)     G4 per-territory adjudication trees + ledger evidence
R309 R332 R334 R339 R341 R346 R370-family/  frozen buyer-package state +
                             constitution amendment full-texts (R309/R339/R370F)
MECHANISM_CEMETERY/          negative knowledge (the moat — never delete)
RELEASE_CHAIN/ ENGINE_RELEASE_REGISTRY.json  Article XXXIX chain authority
```

## Epistemic States (never silently promoted)

```
OBSERVED → INFERRED → ANALOGY → CANDIDATE_CONNECTION →
MECHANISTIC_HYPOTHESIS → EXPERIMENTAL_PROPOSAL → INVENTION_CANDIDATE
```

Loop verification states (Article XXXVII): `NONE | SYNTHETIC_LOOP_VERIFIED |
REAL_LOOP_VERIFIED`. R390 closed the first REAL loop on the engine side:
`EVT-R390-NIST-WATER-VISC-310K` (live NIST SRD 69 acquisition) refuted P-07's
declared viscosity basis and changed `floor_lumen_diameter_mm` 0.6 → 0.5471
mm (conductance restored 0.99998); `REAL_LOOP_VERIFIED` was DERIVED by
`compute_real_loop_verified()` from the committed append-only ledgers —
never assigned. The canonical portfolio bytes are untouched (Art. IX): the
package-side state bump is a CEO-owned V3 regeneration, not silently applied.
Physical validation is still claimed NOWHERE (Article XXXVIII: the event is
an acquisition of externally published measured data, custody-complete and
honestly labeled — not an operator benchtop measurement; 3D output remains
`COMPUTATIONAL_RESULT`, never `PHYSICAL_OBSERVATION`).

## Anti-Hallucination Rule

Never output "Nobody has done this." Always output "No matching evidence was
found within the searched universe" together with the exact search universe,
queries, databases, time range, timestamp, result counts, and limitations.

## Certification

GitHub Actions runs the detached 14-gate certification on every push to main
(`Epistemic Certification (14 gates)` status). The workflow is deterministic:
same commit → same capsule hash. Reproduce locally:

```bash
python -m epistemic_integrity.post_scrub_certification_capsule
```

Constitution, worklog discipline, and the pre-session reading order live in
`HANDOFF_TO_NEXT_CHAT.md` (read it before any session).
