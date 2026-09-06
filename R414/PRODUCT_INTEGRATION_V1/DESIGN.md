# R414 — Product Integration V1: Website + Discovery Engine as One Product

**Directive:** the operator's product-integration directive (23 sections).
**Branch:** `r414/product-integration-v1` (from `r413/physics-stack-v1` @ a7f96de6)
**Scope:** the product contract (every query starts discovery), provider
resilience, the canonical DiscoveryRun state, the CIO, the counsel export,
the honest health surface — WITHOUT weakening any constitutional gate.

## What was built

| Layer | Module | Contract |
|---|---|---|
| Provider resilience | `discovery_fabric/engine/provider_health.py` | The 8-value failure taxonomy (RATE_LIMITED / TIMEOUT / AUTH_FAILURE / NETWORK_FAILURE / INVALID_RESPONSE / MODEL_FAILURE / PARSER_FAILURE / UNKNOWN), the per-provider health book (persisted: `ENGINE_RUNS/provider_health/`), rate-limit cooldown (demotion, never removal — Art. V), the deterministic role router (synthesis / extraction / attack / transform), the independence vocabulary (Art. XLV) |
| Cascade | `llm_registry.generate()` upgrade | MODEL A -> failure -> MODEL B -> failure -> MODEL C (bounded: 1 + max_provider_fallbacks). Every hop typed and recorded (`provider_attempted`, `failure_type`, `timestamp`, `fallback_provider`, `fallback_model`, `retry_count`); a success after failover CARRIES the route (never silent); total failure stays CALL_FAILED with the typed chain (Art. XXI.3 / LXI) |
| Run state | `toscanini/run_state.py` | The canonical DiscoveryRun object (directive §4: model_route, retrieval_route, evidence/mechanism/invention/physics/novelty/attack/experiment/package states, provenance, failure_state) + the four terminal outcomes (§18) + the phase progression (§5) — backend-derived from the run's own artifacts; the frontend READS, never re-derives |
| CIO | `toscanini/cio.py` | The Canonical Invention Object (§12: identity / maturity / evidence / engineering / geometry / simulation / reality_loop / downloads / provenance). The maturity fields (§14: DESIGNED / SIMULATED / EVIDENCE-SUPPORTED / EXPERIMENTALLY VERIFIED) are derived from run artifacts — never frontend badges. `MECHANISM_NOT_SIMULATABLE` is NOT a simulation (honest refusal). No invention artifacts -> no CIO |
| Counsel export | `toscanini/counsel.py` | The "Prepare for IP counsel" package (§20): 8 sections derived from run artifacts only, sha-pinned provenance manifest, cover NEVER asserts patentability (§3), reviewer_provenance=AI_REVIEW |
| Language guard | `cio.language_guard` | Banned patentability words detected on every shipped CIO; violations quarantined and disclosed, never silently edited (Art. XV) |
| Health | `server._health_payload()` | providers[] (§10: status, last_success, latency, rate_limit_state, model_count — NEVER_CALLED is reported, never "healthy"), plus llm/retrieval/physics/reality_loop/showcase readiness fields, each a measured fact |
| Frontend | `webapp/*` | Phase progression checklist + four-outcome banners (RunNarrative), the CIO artifact panel with maturity badges + 3D-only-when-geometry + counsel button (RunArtifact), the calm health status ("Discovery ready" / "one provider degraded"), types+api for the new endpoints |

## The honest behaviors this round pins

1. **A provider outage never looks like product death, and never looks
   like success either.** The cascade tries three providers with every
   hop typed; the run continues through failover; a total outage lands
   in RUN_BLOCKED (infrastructure, Art. LXI) — never NO_DEFENSIBLE.
2. **RUN_BLOCKED is infrastructure-only.** A scientific rejection is
   NO_DEFENSIBLE_INVENTION even though both terminate the run (tested
   both directions — the metamorphic flip test).
3. **No invention is manufactured for the UI.** Two real runs on the
   same problem produced INVENTION_SURVIVED and NO_DEFENSIBLE_INVENTION
   respectively — the engine's own verdict reported both times.
4. **The CIO is the single source of truth for the browser.** No 3D
   unless the run's geometry exists (a material-based mechanism gets an
   honest "no 3D on this run"); the maturity ladder never claims more
   than the artifacts establish.
5. **Not a patent court.** Product copy, CIO, counsel export, and PDFs
   never assert patentability; the guard is tested against the shipped
   UI files.

## Incidents found and fixed during the round (all disclosed)

- **`NameError: _os` in run.py's CAD pass** (pre-existing, caught LIVE
  by acceptance run 1's degradation ledger): the CAD pass read env vars
  through an alias imported only in other methods. Fix: one import
  line. Verified by a targeted replay on run 1's survivor spec (the CAD
  pass now executes; its warrants gate honestly returns
  NOT_APPLICABLE_NO_GEOMETRY for this material mechanism).
- **Phase progression read the wrong file** (run_manifest.json is
  written only at finalize): fixed to read the per-stage envelopes'
  stage_log (live during runs).
- **physics_state "SIMULATED" mislabel**: MECHANISM_NOT_SIMULATABLE was
  counted as a simulation — fixed to NOT_SIMULATABLE (an honest refusal
  is not a result, Art. LIII).
- **List-row/detail outcome disagreement**: public_session_view
  stripped run_dir BEFORE deriving the outcome, so the session index's
  lagging package field produced a different outcome than the detail
  view. Fixed: derive first, strip after (Art. X: one authority).
- **Wrapped `{value: X}` fields**: the invention spec wraps narrative
  fields; the CIO/counsel readers initially crashed or reported empty
  evidence. Fixed with `_unwrap` (both modules) — the acceptance run
  surfaced it live (counsel endpoint 500 -> fixed -> 8 sections).

## Batteries

`tests/test_r414_product_integration.py` — 53 tests (taxonomy, health
book + persistence, role router, cascade honesty/boundedness/cooldown,
four-state mapping both directions, run-state schema + no fabrication,
CIO maturity + language guard + no-object honesty, counsel package,
health payload, no-secrets, metamorphic flips). With the toscani/
workspace/mechanism/R413/R412 batteries: **418 passed, 1 skipped**
(pre-existing). Pre-existing full-suite conditions disclosed at R413
are unchanged (test_e21a at base; order pollution) — not this round's
defects, not fixed here (Art. VII).

## The acceptance demonstration

`R414/PRODUCT_INTEGRATION_V1/ACCEPTANCE_RECORD.json` — two REAL runs
on a real query through the live z-ai transport: run 1 the complete
chain to a survivor + package + CIO + counsel export + WHY Q&A; run 2
an honest rejection to the cemetery. Not mocked, not staged, not
hardcoded.

## Operator-attention items

- The r412/retrieval-resilience branch (main worktree) carries its own
  uncommitted prior-session progress — untouched by this round.
- The push requires the operator's PAT (none in this session; the
  standing one-shot pattern).
- The attacker-calibration standing note (Art. L) is NOT outranked by
  this round.
- The webapp export build (`TOSCANINI_UI/webapp-export/`) is a build
  artifact, not source; CI (R401-WC2) builds it.
