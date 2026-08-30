#!/usr/bin/env bash
# Toscanini quota sentinel — probes the z-ai transport every 2 minutes;
# when it recovers, fires ONE serialized acceptance discovery.
# All outcomes recorded honestly by the worker (no fabrication).
set -u
LOG=/home/z/my-project/discovery-evidence-fabric/ENGINE_RUNS/toscanini_quota_sentinel.log
PROBLEM="Why do robotic lawn mower boundary wires get cut by edging tools, and how can break detection be localized without digging the whole wire?"
echo "$(date -u +%FT%TZ) sentinel start" >> "$LOG"
while true; do
  OUT=$(timeout 60 z-ai chat --prompt "Reply with exactly: READY" 2>&1 | grep -c "READY" || true)
  if [ "$OUT" -ge 1 ]; then
    echo "$(date -u +%FT%TZ) transport RECOVERED — firing acceptance run" >> "$LOG"
    curl -s -m 20 -X POST http://127.0.0.1:8788/api/discoveries \
      -H "Content-Type: application/json" \
      -d "{\"text\":\"$PROBLEM\"}" >> "$LOG" 2>&1
    echo "" >> "$LOG"
    echo "$(date -u +%FT%TZ) acceptance run dispatched" >> "$LOG"
    exit 0
  fi
  sleep 120
done
