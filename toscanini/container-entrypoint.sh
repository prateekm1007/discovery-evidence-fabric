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

exec python3 -m toscanini.server
