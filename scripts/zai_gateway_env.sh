#!/usr/bin/env bash
# zai_gateway_env.sh — start-or-reuse the loop-local zai gateway and run
# the ONE real 1-call transport probe; on success emit the export lines
# the caller can eval; on failure exit 1 TYPED (the caller never guesses,
# Art. XXV). Used by the r7 queue runner's a0plus arm (the launcher
# r6_run_dev12.sh keeps its own inline block — the retire-into-one
# consolidation is queued for the next round, disclosed here, LXIV).
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
GW_KEY="r6-loopback-local"
mkdir -p "$REPO/ENGINE_RUNS"
if curl -sf http://127.0.0.1:8787/healthz >/dev/null 2>&1; then
  echo "[zgw] reusing live session gateway on 8787" >&2
else
  nohup env ZAI_GATEWAY_KEY="$GW_KEY" \
    ZAI_GATEWAY_LOG="$REPO/ENGINE_RUNS/zai_gateway_calls.jsonl" \
    node "$REPO/scripts/zai_gateway.mjs" 8787 \
    >> "$REPO/ENGINE_RUNS/zai_gateway.stdout.log" 2>&1 &
  GW_PID=$!
  disown "$GW_PID" 2>/dev/null || true
  for _ in $(seq 1 30); do
    curl -sf http://127.0.0.1:8787/healthz >/dev/null 2>&1 && break
    sleep 0.5
  done
  curl -sf http://127.0.0.1:8787/healthz >/dev/null 2>&1 || {
    echo "[zgw] ZAI_GATEWAY_UNHEALTHY: never became healthy (typed)" >&2
    kill "$GW_PID" 2>/dev/null
    exit 1
  }
fi
PROBE_HTTP=$(curl -s -m 45 -o /tmp/zai_probe_body_a0.json -w '%{http_code}' \
  -X POST http://127.0.0.1:8787/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GW_KEY" \
  -d '{"model":"glm-4-plus","messages":[{"role":"user","content":"Reply with exactly: READY"}],"max_tokens":8}' \
  2>/dev/null || echo 000)
if [ "$PROBE_HTTP" = "200" ] && grep -q '"content"' /tmp/zai_probe_body_a0.json 2>/dev/null; then
  echo "[zgw] ZAI_TRANSPORT_PROBE: 200 OK -> ZAI_* envs admitted" >&2
  echo "export ZAI_API_KEY=$GW_KEY"
  echo "export ZAI_GATEWAY_KEY=$GW_KEY"
  echo "export ZAI_MODEL=glm-4-plus"
  exit 0
fi
echo "[zgw] ZAI_TRANSPORT_PROBE: http=$PROBE_HTTP (typed unavailable)" >&2
exit 1
