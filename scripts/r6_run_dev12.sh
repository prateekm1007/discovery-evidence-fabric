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
#                                 never echoed). Probe record for the
#                                 owner-supplied round: agnes ALIVE,
#                                 inception ALIVE, openrouter 401
#                                 "User not found" (re-probe of the
#                                 measured-dead key; scripts/
#                                 r6_probe_provider_keys.py).
#   LLM route (owner round 2026-11-12, the ZAI-free path):
#   R6_LLM_ROUTE  auto (default) | zai | owner-keys
#     auto        zai when ZAI_API_KEY is present, else owner-keys
#     zai         legacy loopback gateway (ZAI_API_KEY + gateway)
#     owner-keys  owner-supplied .env.keys rungs: synthesis pinned to
#                 AGNES (the R539 default pin), attack pinned to
#                 INCEPTION (independent account domain, Art. XLV),
#                 judge last-resort named AGNES via
#                 EVAL_JUDGE_LAST_RESORT (shared-family, disclosed;
#                 the calibration gate still applies in full)
#   R6_FABRIC_CACHE  rw (default, the committed B6 behavior) | off |
#                    ro — B6-as-restated and B10 run with off
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

# --- LLM route selection --------------------------------------------------
ROUTE="${R6_LLM_ROUTE:-auto}"
if [ "$ROUTE" = "auto" ]; then
  if [ -n "${ZAI_API_KEY:-}" ]; then ROUTE=zai; else ROUTE=owner-keys; fi
fi
echo "[r6dev12] route: $ROUTE"

if [ "$ROUTE" = "zai" ]; then
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
else
  # owner-keys (ZAI-free): fail-closed on the synthesis head
  if [ -z "${AGNES_API_KEY:-}" ]; then
    echo "[r6dev12] BLOCKED_NO_AGNES_API_KEY: the owner-keys route
requires AGNES_API_KEY (.env.keys vault); there is no hard-coded
fallback" >&2
    exit 7
  fi
  # recorded operator overrides (the ENGINE_*_PROVIDER class, Art. XXVII)
  export ENGINE_SYNTHESIS_PROVIDER=agnes
  # judge: the independent JUDGE_CANDIDATES (xkiro/unorouter) have no
  # credentials in this vault, and the committed zai last-resort rung has
  # no ZAI_API_KEY here — the operator (owner round 2026-11-12) names the
  # shared-family last-resort judge explicitly. The 30-pair calibration
  # gate still applies in full; the source of the name is recorded on the
  # route record + every judgment it produces (SHARED_FAMILY_DISCLOSED,
  # never the gate — Art. XXV/XXVII).
  export EVAL_JUDGE_LAST_RESORT=agnes,agnes-3.0-flash
  if [ -n "${INCEPTION_API_KEY:-}" ]; then
    export ENGINE_ATTACK_PROVIDER=inception
  else
    # disclosed shared-family fallback (never silent, Art. VI)
    export ENGINE_ATTACK_PROVIDER=agnes
    echo "[r6dev12] NOTE: INCEPTION_API_KEY absent; the attack evaluator
falls to agnes (shared-family route, disclosed in the round record)"
  fi
  echo "[r6dev12] owner-keys: synthesis=agnes attack=${ENGINE_ATTACK_PROVIDER}"
fi

export ENGINE_MODEL_COST_POLICY=UNRESTRICTED   # owner operator action 2026-11-11
export EVAL_JUDGE_ALLOW_SHARED_FAMILY=1        # owner operator action 2026-11-11
export ENGINE_NO_PACKAGE=1
export ENGINE_SECOND_JUDGE=0
export MS_BATCH_INSTANTIATION=1
# cache mode (owner B protocol): B5/B7 use rw; B6-as-restated and B10
# use off. 'off' is the code default (llm_economy), so off unsets the
# variable rather than exporting a sentinel.
R6_CACHE="${R6_FABRIC_CACHE:-rw}"
case "$R6_CACHE" in
  off) unset FABRIC_LLM_CACHE ;;
  rw|ro) export FABRIC_LLM_CACHE="$R6_CACHE" ;;
  *) echo "[r6dev12] bad R6_FABRIC_CACHE '$R6_CACHE' (rw|off|ro)" >&2
     exit 8 ;;
esac
echo "[r6dev12] fabric_llm_cache: ${FABRIC_LLM_CACHE:-off}"
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
