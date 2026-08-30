#!/usr/bin/env bash
# zai_gw_run.sh — run an engine command with the zai gateway alive for the
# DURATION of the command (the sandbox reaps detached processes between
# tool invocations, so the gateway must share the lifetime of the run).
#
# Usage: bash scripts/zai_gw_run.sh <python command...>
# Env:   ZAI_GATEWAY_KEY read from /home/z/my-project/.zai_gateway_env
#        (mirror of the gitignored ZAI_API_KEY in .env.keys)
#
# The wrapper: starts the gateway on 127.0.0.1:8787 -> waits for /healthz
# -> runs the command with ENGINE_SYNTHESIS_PROVIDER / ENGINE_ATTACK_PROVIDER
# pinned to zai (EXPLICIT operator overrides, recorded in candidate
# provenance per a2/synthesize.py + a2/adversarial.py) -> stops the gateway.
# Exit code: the command's exit code. Gateway log: ENGINE_RUNS/zai_gateway_*
set -u
REPO=/home/z/my-project/discovery-evidence-fabric
KEY=$(sed -n 's/^ZAI_GATEWAY_KEY=//p' /home/z/my-project/.zai_gateway_env)
if [ -z "$KEY" ]; then echo "no gateway key" >&2; exit 2; fi

# start gateway (same process group; killed on exit via trap)
ZAI_GATEWAY_KEY="$KEY" node "$REPO/scripts/zai_gateway.mjs" 8787 \
  >> "$REPO/ENGINE_RUNS/zai_gateway.stdout.log" 2>&1 &
GW_PID=$!
trap 'kill "$GW_PID" 2>/dev/null' EXIT

# wait for healthz (max 15 s)
for _ in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8787/healthz >/dev/null 2>&1; then break; fi
  sleep 0.5
done
if ! curl -sf http://127.0.0.1:8787/healthz >/dev/null 2>&1; then
  echo "gateway failed to become healthy" >&2; exit 3
fi

cd "$REPO" || exit 4
export ENGINE_SYNTHESIS_PROVIDER=zai
export ENGINE_ATTACK_PROVIDER=zai
export ENGINE_ENSEMBLE_PROVIDERS=zai
export ENGINE_GRID_PROVIDERS=zai
"$@"
