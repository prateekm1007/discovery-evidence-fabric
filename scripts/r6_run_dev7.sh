#!/usr/bin/env bash
# r6_run_dev7.sh — the R6 fresh DEV7 measurement (owner directive 2026-11-11,
# item 1: RE-RUN FRESH under the fixed harness).
#
# Env contract (all recorded per run in _run_meta.json argv + SCORE_TABLE):
#   ZAI_API_KEY                  the sandbox rung's loopback credential
#   ENGINE_MODEL_COST_POLICY=UNRESTRICTED   operator action (owner chat,
#                                2026-11-11): the ENVIRONMENT_GRANT rung is
#                                INELIGIBLE under ZERO_PAID_COST by design;
#                                this measurement round runs on the sandbox
#                                grant, recorded honestly per call.
#   EVAL_JUDGE_ALLOW_SHARED_FAMILY=1        operator action (owner chat,
#                                2026-11-11): my-judged win/tie/loss accepted
#                                for the dev round; disclosure rides every
#                                judge record + SCORE_TABLE.judge_independence.
#
# Usage: bash scripts/r6_run_dev7.sh <arms> <workers> <extra args...>
#   e.g. bash scripts/r6_run_dev7.sh pipeline,baseline,judge 3
set -u
REPO=/home/z/my-project/discovery-evidence-fabric
KEY="${ZAI_API_KEY:-r6session-key-2026}"

# --- gateway: reuse the session gateway if alive, else start one that
# shares this command's lifetime (processes are reaped at the tool-call
# boundary, measured R447)
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
  echo "[r6] gateway started (in-command lifetime)"
else
  echo "[r6] reusing live session gateway on 8787"
fi

cd "$REPO" || exit 4
export ZAI_API_KEY="$KEY"
export ZAI_MODEL="glm-4-plus"
export ENGINE_MODEL_COST_POLICY=UNRESTRICTED
export EVAL_JUDGE_ALLOW_SHARED_FAMILY=1
export ENGINE_NO_PACKAGE=1          # lean: no package tail in measured runs
export ENGINE_SECOND_JUDGE=0        # one judge; the second judge has no route
export MS_BATCH_INSTANTIATION=1     # R6 item 1: ONE batched operator-
                                    # instantiation call per problem (the
                                    # owner's "batch multi-operator
                                    # generation into fewer calls"); the
                                    # batch record rides the space and the
                                    # typed legacy fallback is unchanged
ARMS="${1:-pipeline,baseline,judge}"
WORKERS="${2:-3}"
shift 2 2>/dev/null || shift $#
python3 -B eval/run.py --arms "$ARMS" --subset dev7 --workers "$WORKERS" \
  --timeout 300 "$@"
