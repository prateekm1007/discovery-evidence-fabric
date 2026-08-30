# Toscanini — UI + orchestration boundary

The MVP web application in front of the discovery engine (CEO directive
2026-08-30). Repositories stay separate: this package lives in the ENGINE
repo; the portfolio repo remains buyer-packages only.

```text
Toscanini UI (Next.js 16, :3000)
    |  relative fetch /api/toscanini/*  (server-side proxy; no secrets in bundle)
toscanini.server (:8788, stdlib Python)
    |  subprocess worker per discovery (flock-serialized)
discovery_fabric.engine.run.EngineRun        (UNCHANGED engine)
    |  canonical package factory (QA-gated) — same path as the portfolio
ENGINE_RUNS/toscanini_ui_* + BUYER ZIP
```

## Run locally

```bash
# 1. engine orchestration service (seeds six-domain history, owns SSE)
cd discovery-evidence-fabric
./toscanini/start.sh            # :8788

# 2. UI (Next.js dev server on :3000)
cd <ui workspace> && bun run dev
```

## Endpoints (:8788)

- `GET /healthz` — service + gateway + engine commit
- `POST /api/discoveries {text}` — start a discovery (evidence-bound problem
  build → 13-stage chain → automatic package on survivor)
- `GET /api/sessions` — history index
- `GET /api/sessions/<id>` — full detail (stages, result, specs, package)
- `GET /api/sessions/<id>/events` — SSE live stream (artifact-derived)
- `POST /api/sessions/<id>/share` — read-only share id
- `GET /api/share/<id>` — public payload (no internals)
- `GET /api/sessions/<id>/package` — buyer ZIP (survivors)
- `GET /api/cemetery` — append-only failed-candidate cemetery

## Deployment shape (CEO #10)

- Vercel: the Next.js app (UI only). Set `TOSCANINI_UPSTREAM` to the
  orchestration service URL.
- Python service + engine: any container host; it needs the repo, `.env.keys`
  (NEVER committed), and the zai gateway (`node scripts/zai_gateway.mjs`).
- The Python scientific stack never deploys to Vercel.

## Constitutional notes

- Art. X: the engine run directory is the authority; `TOSCANINI_UI/sessions.json`
  is a projection index.
- Art. IV/VI: SSE events are derived only from persisted artifacts.
- Art. XVIII/XXXVIII: epistemic classes surface end-to-end in the UI.
- Art. XX/XXI: problems built from free text are evidence-bound with inline
  limitation stamps; provider failures are failures, never absence.
- Art. XXV: transport errors are shown as errors, never as kills.

## Transport pins

Workers set `ENGINE_SYNTHESIS_PROVIDER/ENGINE_ATTACK_PROVIDER/ENGINE_ENSEMBLE_PROVIDERS/
ENGINE_GRID_PROVIDERS=zai` — the engine's own explicit operator-override
mechanism (logged + provenance-recorded). Measured basis: nvidia endpoint
oscillation (35 s..>240 s) and mistral payment block. Runs are flock-serialized
(`TOSCANINI_UI/run.lock`) because the zai gateway 429s under concurrency.
