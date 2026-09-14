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

exec python3 -m toscanini.server
