# R397 Operator Deploy Runbook — Phase 1 "Make Current Code Real"

**Engine state:** `eb354d3a` (origin/main; code tip `73b89df3` + evidence commit).
**Certification:** CI "Epistemic Certification" 14-Gate Detached Certification =
**SUCCESS** on `73b89df3` (run 33667364597; `c6527873` also SUCCESS).
**Local proof already done:** artifact-identity contract + session isolation verified
end-to-end on the real server process
(`R396/LOCAL_DEPLOYMENT_SIMULATION_73b89df3.json` — P1 all-green,
identity_tamper=false, BUILD==RUNNING==HEALTH sha equality, drift GREEN).

The one action this environment cannot perform: the Render deploy itself
(the Render API key was provided in earlier sessions' conversations and is not
persisted here — disclosed, not fabricated). This runbook makes that action
exact and verifiable.

---

## 1. Deploy

Render dashboard → service `toscanini-engine-docker` → **Manual Deploy →
Deploy specific commit** → `eb354d3a` (or latest main). autoDeploy stays OFF.

- The Docker build bakes `ARTIFACT_IDENTITY.json` + `ARTIFACT_IDENTITY.sha256`
  from `RENDER_GIT_COMMIT` (Render supplies it when deploying a GitHub commit)
  → the deployed identity is the BUILD ARTIFACT, not an env var.
- If the service has the `RENDER_GIT_COMMIT` build-arg configured, it is used
  automatically; otherwise the Dockerfile falls back to the build context's
  git HEAD (same commit).

## 2. Environment variables (service settings)

Keep the full R392/R396 contract — ⚠️ Render env-var updates via API `PUT`
REPLACE the whole set (the R393 incident; use the dashboard or a complete
PUT body):

```
GITHUB_TOKEN          (already set — private-repo + runtime-state pushes)
NVIDIA_API_KEY        (already set)
NVIDIA_MODEL          openai/gpt-oss-120b
ENGINE_SYNTHESIS_PROVIDER / ENGINE_ATTACK_PROVIDER /
ENGINE_ENSEMBLE_PROVIDERS / ENGINE_GRID_PROVIDERS   nvidia
DURABLE_STATE_ENABLED 1
PORTFOLIO_COMMIT      b978e32c6a484fa14d7b42e60f407333612a50d9
ENGINE_OPERATOR_KEY   <generate a strong random secret>   # NEW (R396 A.2)
ENGINE_COMMIT         73b89df364c00c3a9c120b48d05a62160617818d
                      # OPTIONAL now — an EXPECTATION cross-check only;
                      # identity itself comes from the build artifact
```

## 3. Verify (from any machine)

```bash
curl -sS https://toscanini-engine-docker.onrender.com/api/health | python3 -m json.tool
```

Must show:
- `engine_commit` = `73b89df3…`, `engine_commit_source` = `build_artifact`
- `deployment_identity.identity_tamper` = `false`
- `build_artifact_sha256` == `running_artifact_sha256`
- `deployment_identity.deployment_drift` = `GREEN`
- `operator_key_configured` = `true` (value never disclosed)
- `portfolio_ready`/`llm_transport_ready`/`discovery_ready` = `true`

## 4. Snapshot → restart → restore proof

1. Run a fresh discovery from the public UI (any problem) → COMPLETED.
2. Wait ≥ 2 min (the periodic snapshot commits runtime state), or trigger
   any second run — then verify `durable.last_snapshot.ok` = `true` in
   `/api/health` (it now carries `manifest_sha256` + `engine_commit`).
3. Restart the service (Render dashboard → Manual restart).
4. After restart: `/api/health` → same `engine_commit` (same artifact, new
   `boot_time_utc` — restart, not deployment), and
   `durable.last_restore.integrity_verified` = `true` with the session count
   restored ≥ the pre-restart count.

## 5. External acceptance probes (P1–P7)

```bash
cd discovery-evidence-fabric
python3 scripts/r396_external_probes.py \
  --base https://toscanini-engine-docker.onrender.com \
  --deployed-sha 73b89df364c00c3a9c120b48d05a62160617818d \
  --out R396/EXTERNAL_PROBES_73b89df3.json
```

P1–P7 then run against the live host (P3 false-premise canary, P4
SEARCH_FAILED≠NO_MATCH_FOUND, P5 wind-erosion relevance ×2, P6 determinism ×3,
P7 18-case benchmark on the deployed host). Preserve the raw output and commit
it — this is the Phase 1 acceptance record ("CI is not acceptance").

Baseline for comparison: `R396/EXTERNAL_PROBES_BASELINE_f9dfd45d.json` (the
pre-deployment honest failure record — P1 env-asserted identity, P2 metadata
leakage, which this deployment closes).
