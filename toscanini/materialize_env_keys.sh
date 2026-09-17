#!/bin/sh
# toscanini/materialize_env_keys.sh — R491: materialize the engine's
# .env.keys FILE from the Article-LXXIII-registered credential names
# present in the environment (the HF Space secret surface arrives as
# env vars at boot).
#
# WHY THIS EXISTS (the measured defect it closes):
#   The engine has two credential layers. The LLM routing layer
#   (discovery_fabric/engine/llm_registry.py) reads ENV VARS directly —
#   that layer always worked on the canonical Space. The source-registry
#   layer (discovery_fabric/source_registry/keys.py,
#   discovery_fabric/prior_art_v2/sources.py, toscanini/gateway.py) reads
#   the .env.keys FILE at the repo root — and that file was
#   .dockerignore-excluded from the image by construction (S-01, correct)
#   and never materialized at boot. Result, measured live in R490:
#   5/10 collision-leg searches failed "LENS_API_TOKEN not configured"
#   while the env-layer atria leg served the same run — a two-layer
#   asymmetry, not a missing token.
#
# CONTRACT (Article LXXIII + BS-021):
#   - Values are written once, mode 600, and NEVER logged, echoed, or
#     traced (only credential NAMES appear in output).
#   - An allowlisted name absent from the environment stays absent from
#     the file — an absent key is never fabricated (unknown stays
#     unknown; callers fail into typed AUTH_FAILED / not-configured).
#   - Names NOT on the allowlist are never materialized, whatever their
#     environment value.
#   - Multi-line values are rejected (typed skip) — a credential file
#     line format cannot carry them, and a silent partial write would
#     manufacture a malformed key.
#   - The build-time exclusion (.dockerignore) is unchanged: no key file
#     enters the image; this script writes RUNTIME state only.
#
# Usage: sh materialize_env_keys.sh [DEST]   (default /app/.env.keys)
# Exit:  0 = file materialized; 3 = no allowlisted credential present
#        (honest absence, not an error — callers log the typed line).

DEST="${1:-/app/.env.keys}"

# The file-layer consumers' credential names (discovery_fabric/
# source_registry/keys.py + prior_art_v2/sources.py + toscanini/gateway.py
# call sites, enumerated R491). The LLM routing layer (ATRIA_API_KEY*,
# GITHUB_TOKEN, HF_TOKEN, ...) reads env vars directly and is deliberately
# NOT duplicated here — the file stays minimal.
ALLOWLIST="LENS_API_TOKEN ELSEVIER_API_KEY PATSNAP_EUREKA_API_KEY PATENT_BEAR_API_KEY PATENTSVIEW_API_KEY S2_API_KEY SEMANTIC_SCHOLAR_API_KEY CORE_API_KEY MATERIALS_PROJECT_API_KEY UNPAYWALL_EMAIL OPENALEX_EMAIL ZAI_API_KEY"

NL='
'
TMP="$DEST.tmp.$$"
NAMES=""
: > "$TMP"

for NAME in $ALLOWLIST; do
  eval "VAL=\${$NAME:-}"
  if [ -z "$VAL" ]; then
    continue
  fi
  case "$VAL" in
    *"$NL"*)
      echo "[materialize] skipped $NAME: multi-line value rejected (typed; never materialized)" >&2
      continue
      ;;
  esac
  printf '%s=%s\n' "$NAME" "$VAL" >> "$TMP"
  NAMES="$NAMES $NAME"
done

if [ -s "$TMP" ]; then
  umask 077
  mkdir -p "$(dirname "$DEST")" 2>/dev/null || true
  mv "$TMP" "$DEST"
  chmod 600 "$DEST"
  echo "[materialize] materialized $DEST from the environment (names:$NAMES; values never logged)"
  exit 0
else
  rm -f "$TMP"
  echo "[materialize] no allowlisted credential present in the environment — $DEST not written (file-layer sources stay typed not-configured; ABSENT is not FAILED)"
  exit 3
fi
