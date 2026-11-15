#!/usr/bin/env bash
# git_cred_helper_vault.sh — F33 mitigation (AM23 D3, loop-owned per the
# Art. 28 addendum): the remote URL carries NO embedded token; this
# helper supplies GH_PAT at call time from the gitignored vault
# (.env.keys, vault-only storage). The token never reaches a log, an
# artifact, or git history: the helper writes to git's credential
# protocol pipe only.
set -euo pipefail
input=$(cat) # git feeds protocol=/host= lines on stdin
case "$input" in
  *host=github.com*) ;;
  *) exit 0 ;;
esac
vault="$(cd "$(dirname "$0")/.." && pwd)/.env.keys"
[ -f "$vault" ] || exit 1
pat=$(grep -E '^GH_PAT=' "$vault" | head -1 | cut -d= -f2-)
[ -n "$pat" ] || exit 1
printf 'username=x-access-token\npassword=%s\n' "$pat"
