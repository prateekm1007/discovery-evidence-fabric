#!/bin/bash
# R415 acceptance stack: the zai gateway (8787) + the engine service
# (8788), detached exactly like the deployment shape. The server serves
# the webapp export same-origin and /api/* resolves to itself.
cd "$(dirname "$0")/.." || exit 1
mkdir -p ENGINE_RUNS
# gateway first (the sandbox-local transport; the ZAI key stays in
# .env.keys, server-side, never in any payload)
setsid node scripts/zai_gateway.mjs 8787 >> ENGINE_RUNS/zai_gateway.stdout.log 2>&1 < /dev/null &
sleep 3
for i in $(seq 1 20); do
  if curl -s -o /dev/null http://127.0.0.1:8787/healthz; then break; fi
  sleep 1
done
setsid python3 -m toscanini.server >> ENGINE_RUNS/toscanini_server.log 2>&1 < /dev/null &
sleep 4
for i in $(seq 1 20); do
  if curl -s -o /dev/null http://127.0.0.1:8788/api/health; then
    echo "stack up"; exit 0
  fi
  sleep 1
done
echo "stack FAILED to come up"; exit 1
