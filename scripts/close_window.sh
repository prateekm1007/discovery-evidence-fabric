#!/usr/bin/env bash
# close_window.sh — the DIR-3 (R141-F2 / R139S3-F2) scoped-close
# procedure. REPLACES the add -A close that resurrected pruned paths
# twice (8efc85b54 deleted the twin's citation-identity integration;
# the stale-tree class the auditor named R139S3-F2).
#
# Usage:  scripts/close_window.sh <work_id> <file-or-dir> [<more>...]
#         (all paths must be inside the repo; the claim registry and
#          the round status are added automatically if present)
#
# Steps (fixed order, fail-closed):
#   0. refuse to run dirty-unrelated (nothing staged/unstaged outside
#      the named paths + the UI churn, which is typed as excluded)
#   1. fetch the remote tip; REFUSE if the local branch has diverged
#      (the operator must rebase explicitly — never a blind push)
#   2. stage EXACTLY the work_id's paths (git add -- <paths>)
#   3. run the guard battery: pruned-module reappearance + claim
#      trailers + secret scan
#   4. print the staged manifest for the record before committing
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

WORK_ID="${1:?usage: close_window.sh <work_id> <path> [more paths...]}"
shift
[ $# -ge 1 ] || { echo "REFUSED: no artifact paths named" >&2; exit 1; }

# 0. the named paths must exist
for p in "$@"; do
  [ -e "$p" ] || { echo "REFUSED: named path missing: $p" >&2; exit 1; }
done

# 1. fetch + divergence check (never push a blind non-FF)
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
git fetch origin queue/dev12_r7
LOCAL="$(git rev-parse HEAD)"
REMOTE="$(git rev-parse origin/queue/dev12_r7)"
if ! git merge-base --is-ancestor "$REMOTE" "$LOCAL"; then
  echo "REFUSED: local $BRANCH is behind/diverged from origin/queue/dev12_r7" >&2
  echo "  rebase first: git rebase origin/queue/dev12_r7 (stash the UI churn)" >&2
  exit 1
fi

# 2. stage EXACTLY the named paths (+ the registry/counter if changed)
git add -- "$@"
for auto in eval/work_claims.json eval/claim_next_id.txt; do
  if ! git diff --quiet -- "$auto" 2>/dev/null \
     || ! git diff --cached --quiet -- "$auto" 2>/dev/null; then
    git add -- "$auto"
  fi
done

# 3. the guard battery
echo "=== guard: pruned-module reappearance"
python3 -m pytest tests/test_pruned_module_reappearance.py -q -p no:warnings
echo "=== guard: secret scan of the staged tree"
if git grep -nE "ghp_[A-Za-z0-9]{30,}|hf_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{20,}" --cached; then
  echo "REFUSED: live credential pattern in staged content" >&2
  exit 1
fi

# 4. the staged manifest (the record)
echo "=== staged for work_id $WORK_ID:"
git diff --cached --stat
echo "=== unstaged leftovers (MUST be UI-churn only):"
git status --short | grep -v '^[MARD]' | head -10 || true
git status --short | grep '^ M\|^??' | grep -v "TOSCANINI_UI" | head -10 \
  && { echo "NOTE: non-UI unstaged files exist — they stay uncommitted (scoped close)." >&2; } || true

echo "close_window guards GREEN — commit with the Session/Work-Id trailers:"
echo "  git commit -m \"...\" -m \"Session: <session_id>\" -m \"Work-Id: $WORK_ID\""
