#!/bin/bash
# ensure the sandbox zai gateway is up, with the server-side key from
# .env.keys (the key NEVER appears in logs or output — env injection)
cd "$(dirname "$0")/.." || exit 1
if curl -s -o /dev/null http://127.0.0.1:8787/healthz; then
  echo "gateway up"; exit 0
fi
KEY=$(python3 -c "
keys={}
for line in open('.env.keys'):
    line=line.strip()
    if line and not line.startswith('#') and '=' in line:
        k,v=line.split('=',1); keys[k.strip()]=v.strip()
print(keys.get('ZAI_API_KEY',''))")
if [ -z "$KEY" ]; then echo "no ZAI key in .env.keys"; exit 1; fi
ZAI_GATEWAY_KEY="$KEY" ZAI_GATEWAY_LOG="ENGINE_RUNS/zai_gateway_calls.jsonl" setsid node scripts/zai_gateway.mjs 8787 >> ENGINE_RUNS/zai_gateway.stdout.log 2>&1 < /dev/null &
for i in $(seq 1 30); do
  if curl -s -o /dev/null http://127.0.0.1:8787/healthz; then
    echo "gateway restarted"; exit 0
  fi
  sleep 1
done
echo "gateway FAILED"; exit 1
