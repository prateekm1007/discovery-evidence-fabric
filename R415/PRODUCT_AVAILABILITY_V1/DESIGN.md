# R415 — PRODUCT AVAILABILITY V1 (P0: make discovery always available + fix the frontend)

**Branch:** `r415/discovery-availability-v1` (from `r414/product-integration-v1` @ a2b1f6f8)
**Directive:** CODER P0 (21 sections + final checklist)
**reviewer_provenance:** AI_REVIEW on every artifact (Art. LXVII)

## The problem this round fixes

The deployed product surfaced `ERROR_TRANSPORT — LLM transport unavailable:
gateway=EXTERNAL probe=CALL_FAILED HTTPError: HTTP Error 410: Gone`. Root
cause (R415/PRODUCT_AVAILABILITY_V1/ROOT_CAUSE_410.json): the R414 registry
pinned ONE model per provider; the transport's pinned model was retired
upstream (the registry's own policy note records NVIDIA 410-ing retired
models), every call failed, and the machine treated one provider's one dead
model as total product death.

## What was built

1. **The 410 root cause (directive §1)** — `provider_health.py`: HTTP 410
   is the distinct `GONE` failure class + provider-health state (extends
   the R414 taxonomy; nothing reclassified). `model_routing.py`: a GONE
   model is demoted from ladders (known-dead from the provider's own
   response), the provider's other models stay eligible (Art. V); a 410
   gets NO same-model retry.
2. **Server-side keys (§2)** — validated at startup as
   `NVIDIA: CONFIGURED` / `OPENROUTER: CONFIGURED` (never the secret);
   the same sources the engine's call path reads (env + .env.keys
   bootstrap). Render injection is the operator action.
3. **The routing registry (§3)** — `discovery_fabric/engine/model_routing.py`:
   ProviderRegistry → ModelRegistry → health/availability → task
   suitability → routing decision. ModelRecords carry task_capabilities,
   cost/latency classes, context limits, structured_output + dynamic
   health fields computed on read.
4. **Availability score (§4)** — recent_success_rate × health_recency ×
   provider_health × task_compatibility × latency_suitability (× attack
   separation bonus, Art. XLV), from the ledger with EXPONENTIAL DECAY
   (4 h half-life: yesterday's outage does not permanently poison a
   provider). Separate provider / model / task trackings. Every weight is
   a recorded policy input (Art. XXVII); no telemetry → a disclosed
   neutral prior, never a fabricated 0/1 (Art. XXV).
5. **The ladders (§5)** — FAST / STRONG / CHEAP task classes (role-mapped);
   rung order is ROUND-ROBIN across providers (every provider's best
   model before any provider's second model — provider outages walk to
   the next provider; model retirements fall to the next provider's
   model); bands PRIMARY / SECONDARY_REASONING / PROVIDER_ALTERNATE /
   LAST_RESORT; bounded (≤ 8 rungs; ≤ 1+fallbacks+2 hops per call).
6. **Health probes (§6)** — short-TTL (300 s) probe cache, invalidated
   IMMEDIATELY on failure; provider states
   HEALTHY/DEGRADED/RATE_LIMITED/AUTH_FAILED/GONE/TIMEOUT/UNAVAILABLE/UNKNOWN.
7. **Automatic failover (§7)** — `llm_registry.generate()` walks the
   rungs; every hop typed + recorded (route + ledger + health book);
   success-after-failover carries the route (never silent).
8. **Transport ≠ discovery failure (§8)** — the worker's genuinely
   exhausted transport terminates `RUN_BLOCKED_TRANSPORT` (distinct from
   every verdict, Art. LXI): "Discovery temporarily blocked by
   infrastructure. Your problem is saved and ready to resume." + the §1
   typed failure record. Retryable (sessions.py).
9. **Always attempt (§9)** — every valid POST creates a run; the ladder
   probe + per-call cascade do the falling back; `POST /api/discovery`
   → 202 + run_id; `GET /api/discovery/{run_id}` → the canonical run
   state.
10. **The headline (§10/§11/§12/§21)** — `DISCOVER. INVENT. ANYTHING.` +
    the directive subline; the problem input is the landing hierarchy's
    dominant element; the status chip is GENERATED from /api/health
    ("Discovery ready" / "Discovery ready · N providers degraded" /
    "Showcase ready · Discovery temporarily unavailable"); "engine
    starting…" is REMOVED (never a persistent state; a quiet chip while
    the first poll is in flight); the story strip
    DISCOVER → INVENT → INSPECT → CHALLENGE → REBUILD → EXPERIMENT.
11. **/api/health (§13)** — the directive's exact top-level block:
    showcase_ready / discovery_ready / providers{<id>:
    {status, available_models}} / retrieval_ready / physics_ready /
    reality_loop_ready + product_status; no keys, no endpoints (tested).
12. **Model choice invisible (§14)** + **role diversity (§15)** — the UI
    never shows model pickers; attack routing keeps provider separation;
    which provider/model executed each step is recorded (run state +
    ledger).
13. **MODEL_ROUTING_LEDGER (§16/§17)** — append-only jsonl (one line per
    attempt: request_id, run_id, stage, provider, model, attempt,
    latency, status, failure_class, tokens, estimated_cost,
    fallback_from, fallback_to) — THE evidence base; scores derive from
    its bytes (replayable, Art. XII/LXII).
14. **No hardcoded free list (§18)** — live catalog discovery (GET
    /v1/models, TTL-cached, disk-cached) ∩ the pinned FAMILY allowlist;
    UNDISCOVERED is disclosed and pinned defaults stand in. Live-verified
    against OpenRouter's public catalog: 430 models, 135 eligible.
15. **The fallback tests (§19)** — the directive's exact scenarios, both
    directions (A=410 → B=rate-limited → C=timeout → D=success: run
    succeeds, failures recorded, D selected; all fail: CALL_FAILED +
    RUN_BLOCKED_TRANSPORT + problem retained + no fake invention +
    resumable) + decay/GONE/TTL/secret-leak/ledger-schema/ladder-shape
    tests + the API contract (202 + run_id).
16. **The acceptance (§20)** — R415/PRODUCT_AVAILABILITY_V1/
    ACCEPTANCE_RECORD.json: a REAL query through the full chain (371 s,
    24 real LLM calls, 21 records from 8 live sources, attack PASS,
    honest physics refusal, CIO present, counsel ZIP, live web/3D/health
    surfaces) — no mocks, no staged data. RUN 1 of the acceptance caught
    TWO live pre-existing engine defects (Art. XV/XVI), both fixed with
    regression tests + targeted replays:
    - S2 `{"data": null}` throttle → `len(None)` TypeError crashed
      RETRIEVE (Art. XXI.3 violation) → now RATE_LIMITED + custody
      disclosure;
    - `select_survivors` ignored the entry's own `killed` flag → selected
      an independent-attack-killed candidate → `StopIteration` → package
      failure → the caller's kill record is now authoritative.

## Incident disclosed (Art. IX/XI)

The first post-edit test run (before the cascade tests were made
hermetic) recorded its fake-call TypeErrors through the PRODUCTION
routing-ledger singleton. Quarantined as
`ENGINE_RUNS/model_routing/ledger.test-pollution.quarantine.jsonl` with a
note; `tests/conftest.py` now redirects the ledger / state / catalog to a
tmp sandbox for EVERY test (structural isolation, the same pattern as the
R401-WC1 retrieval-log guard).

## Batteries

tests/test_r415_discovery_availability.py **35/35**; combined curated
battery **445+ passed** (R412 tvm/gradient/recovery, R413 physics, R414
product-integration, R395 workspace, R402 discovery-integrity,
toscanini-recovery; the R392 worker-matrix updated to the §8 vocabulary,
gateway-state independent). The R392 transport-snapshot/health failures
with a live local gateway are the previously-disclosed environmental
class (unchanged). webapp build + export GREEN (headline verified in the
bundle; "engine starting" verified absent).

## Standing notes NOT outranked by this round

- Attacker calibration (Art. L) — the 0.8 false-kill note stands.
- Upstream retrieval adequacy (Art. XIV) — still RED (the R412
  retrieval-resilience branch carries that work).
- R413 RUN_GATE stays PARTIALLY_OPEN (one solver wired).
- PUSH PENDING: this branch requires the operator's PAT (none in this
  session; r412/gradient-v3, r412/retrieval-resilience, r413/physics-
  stack-v1, r414/product-integration-v1 also remain unpushed).
