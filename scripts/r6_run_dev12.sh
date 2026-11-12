#!/usr/bin/env bash
# r6_run_dev12.sh — R6 B6: fresh composer-era DEV12 (owner directive
# 2026-11-12, Section B item 6), CHUNKED for the sandbox rule (processes
# are reaped at the tool-call boundary, measured R447 + re-measured
# 2026-11-12): each invocation runs its OWN problems chunk end-to-end
# (pipeline,baseline,judge arms together — the pair needs both answers
# on the SAME evidence snapshot, same invocation) and exits.
#
# Env contract:
#   .env.keys (gitignored vault)  AGNES_API_KEY, INCEPTION_API_KEY,
#                                 OPENROUTER_API_KEY (exported here;
#                                 never echoed)
#   ZAI_API_KEY                   the loopback gateway credential,
#                                 operator-declared (fail-closed)
#   FABRIC_LLM_CACHE=rw           A1 record+reuse: this round measures
#                                 the call economy live; identical
#                                 repeats become structurally free
#
# Usage: bash scripts/r6_run_dev12.sh <comma-separated problem ids>
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO" || exit 4

# vault: export provider keys (never printed)
if [ -f .env.keys ]; then
  set -a; source .env.keys; set +a
fi
if [ -z "${ZAI_API_KEY:-}" ]; then
  echo "[r6dev12] BLOCKED_NO_ZAI_API_KEY: the loopback credential must
be operator-declared (ZAI_API_KEY); there is no hard-coded fallback" >&2
  exit 5
fi
KEY="$ZAI_API_KEY"

# gateway: reuse a live one, else start one sharing this command's
# lifetime (in-command lifetime per the runbook sandbox rule)
if ! curl -sf http://127.0.0.1:8787/healthz >/dev/null 2>&1; then
  ZAI_GATEWAY_KEY="$KEY" node "$REPO/scripts/zai_gateway.mjs" 8787 \
    >> "$REPO/ENGINE_RUNS/zai_gateway.stdout.log" 2>&1 &
  GW_PID=$!
  trap 'kill "$GW_PID" 2>/dev/null' EXIT
  for _ in $(seq 1 30); do
    curl -sf http://127.0.0.1:8787/healthz >/dev/null 2>&1 && break
    sleep 0.5
  done
  curl -sf http://127.0.0.1:8787/healthz >/dev/null 2>&1 || {
    echo "gateway failed to become healthy" >&2; exit 3; }
  echo "[r6dev12] gateway started (in-command lifetime)"
else
  echo "[r6dev12] reusing live session gateway on 8787"
fi

export ZAI_API_KEY="$KEY"
export ZAI_MODEL="glm-4-plus"
export ENGINE_MODEL_COST_POLICY=UNRESTRICTED   # owner operator action 2026-11-11
export EVAL_JUDGE_ALLOW_SHARED_FAMILY=1        # owner operator action 2026-11-11
export ENGINE_NO_PACKAGE=1
export ENGINE_SECOND_JUDGE=0
export MS_BATCH_INSTANTIATION=1
export FABRIC_LLM_CACHE=rw                     # A1 record+reuse (owner item A1)
export RETRIEVE_JOB_BUDGET_S=20                # R6 retrieval job budget (committed)
# MEASURED CAP CORRECTION (disclosed, Art. XXV): the first composer-era
# chunk hit the 12-healthy cap with the pipeline still pending (5 typed
# HEALTHY_CALL_CAP_EXCEEDED stops per problem) — the stopped calls were
# the ATTACK stage, one operator, and the candidate EVALUATOR; the
# evaluator cut left every candidate unadjudicated and the composer
# typed-refused (NO_ADMISSIBLE_CANDIDATES) on ALL 3 problems. Measured
# composer-era healthy demand: 15-17 calls/problem. Cap 18 = demand +
# headroom; the RETRY-STORM controls are unchanged (retry cap 6, breaker
# threshold 3, AIMD pacing) — the ≤12 directive bounded ATTEMPTS, and
# attempts stay bounded by the retry cap + breaker, not by starving the
# evaluator. Disclosed in the round report; the economy record carries
# the per-problem counters as evidence.
export FABRIC_PROBLEM_CALL_CAP=18

PROBLEMS="${1:?usage: r6_run_dev12.sh <comma-separated problem ids>}"
echo "[r6dev12] chunk: $PROBLEMS"
python3 -B eval/run.py \
  --arms pipeline,baseline,judge \
  --problems-file eval/problems_dev12.json \
  --problems "$PROBLEMS" \
  --workers 1 --timeout 300 \
  --pairs-out eval/pairs/dev12_fresh
