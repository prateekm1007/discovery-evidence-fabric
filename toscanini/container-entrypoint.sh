#!/bin/sh
# toscanini/container-entrypoint.sh — hosted container entrypoint (R392).
#
# Directive 3 (pinning): the container acquires EXACTLY the portfolio
# commit named by PORTFOLIO_COMMIT (deployment configuration). A moving
# branch never determines buyer-package contents; if the pin is absent or
# unacquirable, the showcase degrades honestly (portfolio_ready=false,
# fresh runs unaffected).
#
# Directive 4 (credential safety): GITHUB_TOKEN exists only at runtime,
# is supplied to git through a GIT_ASKPASS helper (mode 0700, generated
# here, reads the env var AT CALL TIME), and never appears in a
# command-line URL, in argv, in the image, or in logs. The helper is
# removed after acquisition.
set -e
cd /app

git config --global --add safe.directory /app 2>/dev/null || true
git config --global --add safe.directory /portfolio 2>/dev/null || true

PORTFOLIO_DIR=/portfolio
PORTFOLIO_REMOTE=https://github.com/prateekm1007/technology-transfer-portfolio-15.git

if [ ! -d "$PORTFOLIO_DIR/.git" ]; then
  if [ -n "$GITHUB_TOKEN" ] && [ -n "$PORTFOLIO_COMMIT" ]; then
    CRED_DIR=$(mktemp -d)
    cat > "$CRED_DIR/askpass.sh" <<'EOS'
#!/bin/sh
case "$1" in
  *sername*) echo "x-access-token" ;;
  *assword*) printf '%s\n' "$GITHUB_TOKEN" ;;
  *) echo "" ;;
esac
EOS
    chmod 700 "$CRED_DIR/askpass.sh"
    mkdir -p "$PORTFOLIO_DIR"
    git -C "$PORTFOLIO_DIR" init -q
    if GIT_ASKPASS="$CRED_DIR/askpass.sh" GIT_TERMINAL_PROMPT=0 \
        git -C "$PORTFOLIO_DIR" fetch --depth 1 "$PORTFOLIO_REMOTE" \
            "$PORTFOLIO_COMMIT" \
       && GIT_ASKPASS="$CRED_DIR/askpass.sh" \
          git -C "$PORTFOLIO_DIR" checkout --detach FETCH_HEAD; then
      echo "portfolio acquired at pinned commit $PORTFOLIO_COMMIT"
    else
      echo "WARN: portfolio pinned fetch failed — showcase unavailable (fresh runs unaffected)"
    fi
    rm -rf "$CRED_DIR"
  else
    echo "WARN: GITHUB_TOKEN or PORTFOLIO_COMMIT not set — portfolio unavailable (portfolio_ready=false)"
  fi
fi

# ---------------------------------------------------------------------------
# R451-C1.3: the self-hosted zero-paid local route (env-gated).
# LOCAL_QWEN_ENABLE=1 (the canonical Space's env contract) starts the
# pinned llama.cpp llama-server with the sha-pinned Qwen/Qwen3-1.7B
# Q4_K_M GGUF BEFORE the engine serves, and wires LOCAL_QWEN_BASE_URL.
# The engine's runtime-admission authority then measures this route
# like any other (probe-before-admit — no bespoke local exception).
# A failed start is HONEST: the typed route state stays PROBE_FAILED /
# NOT_PROBED and the engine keeps its other routes (Art. LXI); the
# entrypoint never fabricates a working local route.
# ---------------------------------------------------------------------------
if [ "$LOCAL_QWEN_ENABLE" = "1" ] \
    && [ -x /opt/llama/llama-server ] \
    && [ -f /opt/models/Qwen3-1.7B-Q4_K_M.gguf ]; then
  echo "[entrypoint] starting llama-server (the zero-paid local route)..."
  ( LD_LIBRARY_PATH=/opt/llama /opt/llama/llama-server \
      -m /opt/models/Qwen3-1.7B-Q4_K_M.gguf \
      --port 8790 --host 127.0.0.1 \
      -c "${LOCAL_QWEN_CTX:-8192}" -np "${LOCAL_QWEN_SLOTS:-1}" \
      -t "${LOCAL_QWEN_THREADS:-2}" \
      --alias qwen3-1.7b --no-webui \
      > /tmp/llama-server.log 2>&1 & )
  _lw_i=0
  while [ "$_lw_i" -lt 120 ]; do
    if curl -fsS http://127.0.0.1:8790/health >/dev/null 2>&1; then
      echo "[entrypoint] llama-server UP (zero-paid route available)"
      break
    fi
    _lw_i=$((_lw_i + 1))
    sleep 1
  done
  if ! curl -fsS http://127.0.0.1:8790/health >/dev/null 2>&1; then
    echo "WARN: llama-server did not become healthy in 120 s — the zero-paid route stays unprobed (typed, honest; other routes unaffected)"
  fi
  export LOCAL_QWEN_BASE_URL=http://127.0.0.1:8790/v1/chat/completions
fi

# ---------------------------------------------------------------------------
# R456: the zero-paid semantic-relevance engine (env-gated, the same
# llama.cpp discipline as the chat route). LOCAL_EMBED_ENABLE=1 starts a
# second llama-server in EMBEDDING mode with the sha-pinned
# bge-small-en-v1.5 Q8_0 GGUF (CLS pooling — the model's trained
# pooling) and wires LOCAL_EMBED_URL for the Phase-P1 semantic
# relevance adjudicator (discovery_fabric/source_registry/
# semantic_relevance.py — the measured evidence-relevance bottleneck).
# A failed start is HONEST and TYPED: the adjudicator records
# SEMANTIC_UNAVAILABLE per record and the lexical gate stays the
# recorded authority (Art. IV) — the entrypoint never fabricates a
# working semantic engine.
# ---------------------------------------------------------------------------
if [ "$LOCAL_EMBED_ENABLE" = "1" ] \
    && [ -x /opt/llama/llama-server ] \
    && [ -f /opt/models/bge-small-en-v1.5-q8_0.gguf ]; then
  echo "[entrypoint] starting llama-server (embedding mode, the zero-paid semantic route)..."
  ( LD_LIBRARY_PATH=/opt/llama /opt/llama/llama-server \
      -m /opt/models/bge-small-en-v1.5-q8_0.gguf \
      --embedding --pooling cls \
      --port 8791 --host 127.0.0.1 \
      -c 1024 -t "${LOCAL_EMBED_THREADS:-1}" \
      --alias bge-small-en-v1.5 --no-webui \
      > /tmp/llama-embed-server.log 2>&1 & )
  _le_i=0
  while [ "$_le_i" -lt 60 ]; do
    if curl -fsS http://127.0.0.1:8791/health >/dev/null 2>&1; then
      echo "[entrypoint] embedding llama-server UP (semantic relevance route available)"
      break
    fi
    _le_i=$((_le_i + 1))
    sleep 1
  done
  if ! curl -fsS http://127.0.0.1:8791/health >/dev/null 2>&1; then
    echo "WARN: embedding llama-server did not become healthy in 60 s — the semantic layer stays SEMANTIC_UNAVAILABLE (typed, honest; the lexical gate is unaffected)"
  fi
  export LOCAL_EMBED_URL=http://127.0.0.1:8791
fi

# ---------------------------------------------------------------------------
# R491: the file-layer credential materialization. The source-registry
# layer (source_registry/keys.py, prior_art_v2/sources.py, gateway.py)
# reads the .env.keys FILE — excluded from the image by .dockerignore by
# construction, so file-layer credentials could never resolve in the
# container (the measured R490 collision-leg failure: 5 x lens_patent
# LENS_API_TOKEN not configured while the env-layer atria leg served).
# Materialize /app/.env.keys from the LXXIII-registered names present in
# the environment. Values never logged (BS-021); honest absence is not
# an error (exit 3) and never blocks the boot.
# ---------------------------------------------------------------------------
if [ -f /app/toscanini/materialize_env_keys.sh ]; then
  sh /app/toscanini/materialize_env_keys.sh /app/.env.keys || true
fi

exec python3 -m toscanini.server
