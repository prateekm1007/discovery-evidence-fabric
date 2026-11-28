#!/usr/bin/env bash
# r6_run_dev12.sh — R6 B6: fresh composer-era DEV12 (owner directive
# 2026-11-12, Section B item 6), CHUNKED for the sandbox rule (processes
# are reaped at the tool-call boundary, measured R447 + re-measured
# 2026-11-12): each invocation runs its OWN problems chunk end-to-end
# (pipeline,baseline,judge arms together — the pair needs both answers
# on the SAME evidence snapshot, same invocation) and exits.
#
# Env contract (B-round rewrite, owner directives 1+4 — measured basis:
# this host's bash layer is WSL and its exports DO NOT cross into
# native .exe children, reproduced 2026-11-12; PowerShell does):
#   NO shell exports for engine env. Every engine env var rides
#   --engine-env KEY=VALUE on the python argv (eval/run.py applies it
#   to os.environ and merges it into every child env explicitly).
#   The launcher echoes the applied keys — the effective-env record
#   (Art. XXVII). LLM_ECONOMY.json remains the post-run check for the
#   EFFECTIVE cache_mode and healthy_call_cap.
#   .env.keys sourcing REMOVED: every key it held (AGNES/INCEPTION/
#   OPENROUTER) is measured-retired this window (agnes 429 quota,
#   openrouter 401); no engine env derives from it.
#   LLM route: ONE table, recorded once —
#   discovery_fabric/engine/model_routing.py ROUTE_TABLE (queried
#   here, never duplicated). zai for synthesis/attack/composer/bulk,
#   judge xkiro/ministral-14b, last-resort zai (committed constants
#   already match). On a host without the z-ai CLI the zai rung is
#   PROVIDER_UNAVAILABLE (typed skip; no ZAI_* env rides) and the
#   cascade resolves the role on the next serving rung — recorded
#   per call, never silent (Art. XXV).
#   R6_FABRIC_CACHE  rw (default) | off | ro — B6-as-restated and B10
#                    run with off ('off' omits the var from engine-env
#                    AND unsets it here so a Windows-side value cannot
#                    leak through the WSL->.exe hop)
#
# Usage: bash scripts/r6_run_dev12.sh <comma-separated problem ids>
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO" || exit 4

# --- python resolution (host-independent, the A3 discipline) -----------
# the codebase uses PEP 701 f-strings (eval/run.py: multi-line f-string
# expressions) — 3.12-class syntax. Measured this host: the PATH
# 'python3' AND 'python' are BOTH 3.10.12 (git-bundled; SyntaxError on
# import) while the system 3.12 parses. Deterministic selection: the
# first candidate that can COMPILE the source (no execution), in order:
#   1. R6_PYTHON — operator-named interpreter (the recorded-override
#      class, Art. XXVII; echoed below, never silent). No spaces in
#      the value: on Windows use the 8.3 short name when the install
#      dir has spaces (measured: /mnt/c/PROGRA~1/Python312/python.exe
#      works; C:/Users/... with spaces does not survive the bash layer).
#   2. PATH candidates: python3, python, then py -3 (Windows launcher)
# The file arg is the RELATIVE 'eval/run.py' (we are cd'd into the
# repo): a Windows python.exe CANNOT open POSIX /mnt/c paths (measured
# false-negative mode — it reported 3.12 'cannot parse' on the POSIX
# absolute form and parses the relative one), while unix-style
# interpreters handle the relative form fine.
_PY_PROBE='import sys; compile(open(sys.argv[1], encoding="utf-8").read(), "eval/run.py", "exec")'
PY=""
for _cand in ${R6_PYTHON:-} python3 python; do
  [ -n "$_cand" ] || continue
  if "$_cand" -B -c "$_PY_PROBE" eval/run.py >/dev/null 2>&1; then
    PY="$_cand"
    break
  fi
done
if [ -z "$PY" ] && command -v py >/dev/null 2>&1 && \
   py -3 -B -c "$_PY_PROBE" eval/run.py >/dev/null 2>&1; then
  PY="py -3"
fi
if [ -z "$PY" ]; then
  echo "[r6dev12] BLOCKED_NO_PYTHON: no candidate interpreter can parse
eval/run.py (PEP 701 f-strings: 3.12-class syntax required; measured
this host: PATH python3/python are 3.10). Set R6_PYTHON to a 3.12+
interpreter path (8.3 short name if it contains spaces)" >&2
  exit 9
fi
[ -n "${R6_PYTHON:-}" ] && \
  echo "[r6dev12] python source: R6_PYTHON (operator-named, Art. XXVII)"
echo "[r6dev12] python: $PY ($($PY -B --version 2>&1))"

# --- engine env: the explicit argv dict (directive 1) ------------------
# every value rides --engine-env KEY=VALUE; NOTHING is exported here.
ENGINE_ENV_ARGS=()
add_env() { ENGINE_ENV_ARGS+=(--engine-env "$1"); }

# cache mode (owner B protocol): B5/B7 use rw; B6-as-restated and B10
# use off. 'off' omits the var from engine-env (the llm_economy code
# default is off) AND unsets it here so a Windows-side value cannot
# leak through the WSL->.exe hop.
R6_CACHE="${R6_FABRIC_CACHE:-rw}"
case "$R6_CACHE" in
  off) unset FABRIC_LLM_CACHE ;;
  rw|ro) add_env "FABRIC_LLM_CACHE=$R6_CACHE" ;;
  *) echo "[r6dev12] bad R6_FABRIC_CACHE '$R6_CACHE' (rw|off|ro)" >&2
     exit 8 ;;
esac
echo "[r6dev12] fabric_llm_cache: ${R6_CACHE} (via --engine-env; off = omitted)"

# --- route: ONE table, recorded once (directive 4) ----------------------
# The committed ROUTE_TABLE is QUERIED, not restated: the values below
# come from discovery_fabric/engine/model_routing.py at run time, so
# the launcher can never drift from the recorded table.
ROUTE_JSON="$("$PY" -B -c 'import json; from discovery_fabric.engine.model_routing import ROUTE_TABLE as T; print(json.dumps(T))')" || {
  echo "[r6dev12] BLOCKED_ROUTE_TABLE_UNREADABLE: model_routing.ROUTE_TABLE failed to import" >&2
  exit 6; }
SYNTH_PROV="$("$PY" -B -c 'import json,sys; print(json.loads(sys.argv[1])["synthesis"][0])' "$ROUTE_JSON")"
ATTACK_PROV="$("$PY" -B -c 'import json,sys; print(json.loads(sys.argv[1])["attack"][0])' "$ROUTE_JSON")"
COMPOSE_PROV="$("$PY" -B -c 'import json,sys; print(json.loads(sys.argv[1])["composer"][0])' "$ROUTE_JSON")"
SYNTH_MODEL="$("$PY" -B -c 'import json,sys; print(json.loads(sys.argv[1])["synthesis"][1])' "$ROUTE_JSON")"
JUDGE_PROV="$("$PY" -B -c 'import json,sys; print(json.loads(sys.argv[1])["judge"][0])' "$ROUTE_JSON")"
JUDGE_MODEL="$("$PY" -B -c 'import json,sys; print(json.loads(sys.argv[1])["judge"][1])' "$ROUTE_JSON")"
echo "[r6dev12] ROUTE_TABLE: synthesis=$SYNTH_PROV/$SYNTH_MODEL attack=$ATTACK_PROV composer=$COMPOSE_PROV judge=$JUDGE_PROV/$JUDGE_MODEL"

# recorded operator overrides (the ENGINE_*_PROVIDER class, Art. XXVII):
# the roles resolve through the committed table; the envs make the
# selection explicit and ride the engine's per-call records.
add_env "ENGINE_SYNTHESIS_PROVIDER=$SYNTH_PROV"
add_env "ENGINE_ATTACK_PROVIDER=$ATTACK_PROV"
add_env "ZAI_MODEL=$SYNTH_MODEL"
# operator actions carried from 2026-11-11 (unchanged owner directives)
add_env "ENGINE_MODEL_COST_POLICY=UNRESTRICTED"
add_env "EVAL_JUDGE_ALLOW_SHARED_FAMILY=1"
add_env "ENGINE_NO_PACKAGE=1"
add_env "ENGINE_SECOND_JUDGE=0"
add_env "MS_BATCH_INSTANTIATION=1"
add_env "RETRIEVE_JOB_BUDGET_S=20"
# owner directive 2026-11-12: <= 8 healthy calls per problem. The
# economy record carries the per-problem counters as evidence; the
# retry-storm controls are unchanged (retry cap 6, breaker threshold 3).
# owner directive 2026-11-12: hard cap 14 UNTIL the demand
# cuts land. OWNER ROUND 2026-11-13 DIRECTIVE 4: the demand cuts
# have LANDED (synthesis one-call + fallback; the knowledge-first
# pair FUSED into the MS batch call — its healthy call IS the batch
# call) and the fused demand is measured per stage in STAGE_CALLS.json
# (batch 1 + synthesis 1 + attack 1 + evaluator 1 + compose 1 + <=2
# repairs + <=1 truncation retry = 5-8 healthy logical calls).
# CAP LOWERED 14 -> 10 per the owner's directive; STAGE_CALLS.json is
# the evidence the cap fits (a typed HEALTHY_CALL_CAP_EXCEEDED stop on
# any queued problem reopens this constant with the measured number).
add_env "FABRIC_PROBLEM_CALL_CAP=10"
# OWNER ROUND 2026-11-13 ITEM 2 (latency): hard 40 s per-call socket
# timeout with ONE immediate retry, then rotate to the next rung — the
# measured p02 wall was ~75 s/call with 240 s default attempts and
# 5-20 s fixed retry sleeps; the owner's budget is <=120 s median /
# <=300 s worst per problem. A gateway that accepts and stalls is
# measured as a hang (ttfb_s) and rotates — no hang is counted as work.
# Overridable per invocation (ENGINE_LLM_TIMEOUT_S env wins).
add_env "ENGINE_LLM_TIMEOUT_S=${ENGINE_LLM_TIMEOUT_S:-40}"
# --- zai transport probe (typed availability, never silent) ------------
# MEASURED this host: the z-ai CLI is absent (WSL PATH, Windows npm
# dir, npm registry 404) — the loop-local gateway CANNOT serve here and
# the cascade resolves zai roles on the next serving rung (xkiro
# keyless, measured live). On a host WITH the CLI: start the gateway
# loop-local (binds 127.0.0.1, bearer = the loop-local constant) and
# admit the ZAI_* envs ONLY after ONE real 1-call transport probe
# passes — a healthy healthz alone never certifies transport.
GW_KEY="r6-loopback-local"   # loop-LOCAL only; the gateway binds 127.0.0.1
GW_STARTED=0
ZAI_OK=0
if command -v z-ai >/dev/null 2>&1; then
  mkdir -p "$REPO/ENGINE_RUNS"
  if ! curl -sf http://127.0.0.1:8787/healthz >/dev/null 2>&1; then
    ZAI_GATEWAY_KEY="$GW_KEY" \
    ZAI_GATEWAY_LOG="$REPO/ENGINE_RUNS/zai_gateway_calls.jsonl" \
      node "$REPO/scripts/zai_gateway.mjs" 8787 \
      >> "$REPO/ENGINE_RUNS/zai_gateway.stdout.log" 2>&1 &
    GW_PID=$!
    trap 'kill "$GW_PID" 2>/dev/null' EXIT
    for _ in $(seq 1 30); do
      curl -sf http://127.0.0.1:8787/healthz >/dev/null 2>&1 && break
      sleep 0.5
    done
    curl -sf http://127.0.0.1:8787/healthz >/dev/null 2>&1 || {
      echo "[r6dev12] ZAI_GATEWAY_UNHEALTHY: gateway never became healthy
(typed unavailable; no ZAI_* env rides, cascade resolves)" >&2
      kill "$GW_PID" 2>/dev/null
      GW_STARTED=0
    }
    if [ "$GW_STARTED" = "1" ]; then
      echo "[r6dev12] gateway started (in-command lifetime, loop-local)"
    fi
  else
    GW_STARTED=1
    echo "[r6dev12] reusing live session gateway on 8787"
  fi
  # ONE 1-call transport probe decides ZAI_* admission
  if [ "$GW_STARTED" = "1" ]; then
    PROBE_HTTP=$(curl -s -m 45 -o /tmp/zai_probe_body.json -w '%{http_code}' \
      -X POST http://127.0.0.1:8787/v1/chat/completions \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $GW_KEY" \
      -d '{"model":"glm-4-plus","messages":[{"role":"user","content":"Reply with exactly: READY"}],"max_tokens":8}' \
      2>/dev/null || echo 000)
    if [ "$PROBE_HTTP" = "200" ] && grep -q '"content"' /tmp/zai_probe_body.json 2>/dev/null; then
      add_env "ZAI_API_KEY=$GW_KEY"
      add_env "ZAI_GATEWAY_KEY=$GW_KEY"
      ZAI_OK=1
      echo "[r6dev12] ZAI_TRANSPORT_PROBE: 200 OK, non-empty content -> ZAI_* envs ride engine-env"
    else
      echo "[r6dev12] ZAI_TRANSPORT_PROBE: http=$PROBE_HTTP (typed unavailable; ZAI_* envs omitted, cascade resolves)" >&2
      [ -n "${GW_PID:-}" ] && kill "$GW_PID" 2>/dev/null
    fi
    rm -f /tmp/zai_probe_body.json
  fi
else
  echo "[r6dev12] ZAI_TRANSPORT_ABSENT: no z-ai CLI on this host (measured
2026-11-12: WSL PATH, Windows npm, npm registry 404) — the zai rung is
PROVIDER_UNAVAILABLE and the cascade resolves the role on the next
serving rung (xkiro, keyless, measured live); no ZAI_* env rides" >&2
fi

# Judge last-resort naming (the recorded-override class, Art. XXVII):
# the committed JUDGE_LAST_RESORT (route table judge_last_resort = zai)
# is correct ON A HOST WITH THE ZAI TRANSPORT. Measured on THIS host
# (zai absent): the judge probe then has no eligible candidate (the
# baseline resolves to xkiro -> same-provider rejection; unorouter
# calibrated 0/30 TRANSPORT_OTHER), so the operator names the SERVING
# rung as the shared-family last resort. The 30-pair calibration gate
# still applies IN FULL and the SHARED_FAMILY_DISCLOSED class rides
# the route record + every judgment (automated score only; the holdout
# gate stays auditor-judged).
if [ "$ZAI_OK" != "1" ]; then
  add_env "EVAL_JUDGE_LAST_RESORT=$JUDGE_PROV,$JUDGE_MODEL"
  echo "[r6dev12] EVAL_JUDGE_LAST_RESORT=$JUDGE_PROV,$JUDGE_MODEL (zai transport absent; operator names the serving rung, calibration gate in full, disclosed)"
fi

echo "[r6dev12] engine-env keys: $(printf '%s ' "${ENGINE_ENV_ARGS[@]}" | sed 's/--engine-env //' | cut -d= -f1 | sort -u | tr '\n' ' ')"
# --timeout: MEASURED (owner round 2026-11-12, fu-001 smokes x2): on the
# zai-CLI host the pipeline fits the owner's 300 s worst-case (2 s
# calls); on THIS host the cascade serves xkiro free-tier long-form
# MEASURED ~150 s/call (SYNTHESIZE 19:09:14 -> 19:11:47) + retrieval
# fanout ~150 s (several sources hit the 20 s job budget) — a 300 s
# wall cannot fit the pipeline shape and produced INCOMPLETE_
# INFRASTRUCTURE on both smokes. 900 s = retrieval + 3 synthesis-class
# calls + headroom. The B10 speed protocol measures the real walls
# separately; the owner budget note stays the zai-host measurement.
TIMEOUT_S="${R6_TIMEOUT:-900}"
PROBLEMS="${1:?usage: r6_run_dev12.sh <comma-separated problem ids>}"
# OWNER ROUND 2026-11-13 DIRECTIVE 5 (unattended queue runner): the
# pairs directory is an env override (default unchanged — the audited
# dev12_fresh files are NEVER redirected or overwritten by a runner;
# the runner writes to eval/pairs/dev12_r7). R6_EXTRA_ENV carries the
# ablation-arm engine env verbatim (space-separated KEY=VALUE list;
# applied through the SAME argv channel — never exported, Art. XXVII).
R6_PAIRS_OUT="${R6_PAIRS_OUT:-eval/pairs/dev12_fresh}"
# OWNER ROUND 2026-11-13 DIRECTIVE 5: the queue runner also drives the
# B8 two-turn round 2 and the arm selection through the SAME launcher
# (one env channel, never exported):
#   R6_PROBLEMS_FILE  the problems payload (default the committed DEV12)
#   R6_TWO_TURNS=1    round-2 ingestion flag (--two-turns, Art. LI)
#   R6_ARMS           the run arms (default pipeline,baseline,judge)
R6_PROBLEMS_FILE="${R6_PROBLEMS_FILE:-eval/problems_dev12.json}"
R6_ARMS="${R6_ARMS:-pipeline,baseline,judge}"
_TWO_TURNS_ARGS=()
if [ "${R6_TWO_TURNS:-0}" = "1" ]; then _TWO_TURNS_ARGS+=(--two-turns); fi
if [ -n "${R6_EXTRA_ENV:-}" ]; then
  for _kv in $R6_EXTRA_ENV; do
    case "$_kv" in
      *=*) add_env "$_kv" ;;
      *) echo "[r6dev12] skipping malformed extra-env entry '$_kv' (want KEY=VALUE)" >&2 ;;
    esac
  done
  echo "[r6dev12] extra engine-env: $R6_EXTRA_ENV"
fi
echo "[r6dev12] chunk: $PROBLEMS (timeout ${TIMEOUT_S}s, pairs-out $R6_PAIRS_OUT, file $R6_PROBLEMS_FILE, arms $R6_ARMS)"
"$PY" -B eval/run.py \
  --arms "$R6_ARMS" \
  --problems-file "$R6_PROBLEMS_FILE" \
  --problems "$PROBLEMS" \
  --workers 1 --timeout "$TIMEOUT_S" \
  "${_TWO_TURNS_ARGS[@]}" \
  "${ENGINE_ENV_ARGS[@]}" \
  --pairs-out "$R6_PAIRS_OUT"
