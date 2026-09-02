# R397 Operator Deploy Runbook — Phase 1 "Make Current Code Real"

**Engine state:** `930eca8b` (origin/main; the R399 lean build — image context 225→64 MB).
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
Deploy specific commit** → `930eca8b` (or latest main). autoDeploy stays OFF.

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
ENGINE_COMMIT         930eca8b7db8b0885abccb4e8159a77b8e802723
                      # OPTIONAL now — an EXPECTATION cross-check only;
                      # identity itself comes from the build artifact
```

## 3. Verify (from any machine)

```bash
curl -sS https://toscanini-engine-docker.onrender.com/api/health | python3 -m json.tool
```

Must show:
- `engine_commit` = `930eca8b…`, `engine_commit_source` = `build_artifact`
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

**R400: ONE COMMAND now runs the entire live acceptance** (P1 identity
with the pinned SHA target, P2 isolation, P3 premise gate, P4
incomplete-search gate, P5 relevance ×2, P6 determinism ×3, P7
18-case benchmark in resumable batches of 3, AND the R400-C
production physics chain run with the full 12-field capture contract
— every completed unit flushed to disk, a timeout never loses
records, non-affirmative states never converted):

```bash
cd discovery-evidence-fabric
python3 scripts/r400_post_deploy_acceptance.py
```

Or run them individually (same public-host contract, no local
substitution):

```bash
python3 scripts/r396_external_probes.py \
  --base https://toscanini-engine-docker.onrender.com \
  --deployed-sha 930eca8b7db8b0885abccb4e8159a77b8e802723 \
  --out R400/LIVE_PROBES_<name>_postdeploy.json        # --p 1..7
python3 scripts/r400_production_chain_run.py \
  --base https://toscanini-engine-docker.onrender.com \
  --out R400/PRODUCTION_PHYSICS_RUN_live_postdeploy.json
```

P1–P7 then run against the live host (P3 false-premise canary, P4
SEARCH_FAILED≠NO_MATCH_FOUND, P5 wind-erosion relevance ×2, P6 determinism ×3,
P7 18-case benchmark on the deployed host). Preserve the raw output and commit
it — this is the Phase 1 acceptance record ("CI is not acceptance").

Baseline for comparison: `R396/EXTERNAL_PROBES_BASELINE_f9dfd45d.json` (the
pre-deployment honest failure record — P1 env-asserted identity, P2 metadata
leakage, which this deployment closes). R400's same-day pre-deploy
re-measurement of the live f9dfd45d host is preserved in
`R400/LIVE_PROBES_*_f9dfd45d_predeploy.json` (P1/P2/P3/P4/P6 FAIL,
P5 PASS, P7 all-18-terminal — every failure classified, none
converted).
