#!/usr/bin/env bash
# post_reset_queue.sh — the locked post-reset execution queue (R11 Q5c,
# committed per AM5 F24: the resume path MUST be durable in the repo —
# Art. LXXIV observer-independent durable execution; a fresh clone runs
# this file verbatim after the 00:00Z quota reset).
#
# Stages (typed outcomes, every stage logged to /tmp/post_reset_queue.log):
#   0. TYPED QUOTA PREFLIGHT — one tiny judge call through the battery's
#      own judge_call path; a quota-dead window refuses here (exit 3,
#      pools unspent — Art. LXI: typed, never silently wasted).
#   1. D6 30-pair battery  (scripts/r11_d6_battery30.py) — gate-decisive;
#      carries its own preflight (exit 3 = pool unspent) and the
#      earned-concurrency runner (ledger -> spread -> AIMD -> parallel).
#   2. D4 independent re-judgment (scripts/r11_d4_independent_judge.py)
#      — judge differs from every served generator rung in provider AND
#      model; gold-calibration gate + position swap.
#   3. D5 cross-family panel (scripts/r11_crossfamily_panel.py) —
#      mistral rungs cross-family vs the zai/agnes generator, distinct
#      from the D4 judge route.
#   4. COMMIT + PUSH (Art. LXXXV) — artifacts only; token-pattern grep
#      must be 0 before push (Art. 12); the vault (.env.keys) is found
#      lookup-first by the loaders (Art. LXXXVII).
#
# The gate itself is AUDITOR-judged (Art. XXVI) — this queue produces
# the measurement records; it never declares the gate MET.
set -u
cd "$(dirname "$0")/.."   # repo root — fresh-clone runnable

LOG=${POST_RESET_LOG:-/tmp/post_reset_queue.log}
: > "$LOG"
export ENGINE_LLM_TIMEOUT_S="${ENGINE_LLM_TIMEOUT_S:-40}"
export ENGINE_LLM_RETRY_SLEEP_S="${ENGINE_LLM_RETRY_SLEEP_S:-0}"
export A0P_QUEUE_WAIT_S="${A0P_QUEUE_WAIT_S:-0}"

stage() { echo "[$(date -u +%FT%TZ)] STAGE $1 -> $2" | tee -a "$LOG"; }

stage PREFLIGHT "one tiny judge call (typed; refuses pools while window dead)"
python3 - <<'PY' >>"$LOG" 2>&1
import sys
sys.path.insert(0, "scripts")
from r11_d6_battery30 import judge_call  # noqa: E402
jp = judge_call("xkiro", "mistralai/ministral-14b",
                'Judge preflight: reply with ONLY the JSON object '
                '{"prefer":"tie"} and nothing else.')
print("PREFLIGHT_OUTCOME:", jp.get("outcome"))
sys.exit(0 if jp.get("outcome") == "JUDGE_VALID" else 3)
PY
RC=$?
if [ $RC -ne 0 ]; then
    stage PREFLIGHT "JUDGE_WINDOW_DEAD_OR_QUOTA_SPENT (exit 3; pools unspent, typed Art. LXI) — re-run after the window resets"
    exit 3
fi
stage PREFLIGHT "JUDGE_VALID"

stage D6_BATTERY "30-pair gate-decisive run"
python3 scripts/r11_d6_battery30.py >>"$LOG" 2>&1
RC=$?
stage D6_BATTERY "exit=$RC (0=COMPLETE, 3=preflight-blocked, other=typed failure in log)"
if [ $RC -ne 0 ]; then exit $RC; fi

stage D4_REJUDGE "20/20 independent re-judgment (judge != generator)"
python3 scripts/r11_d4_independent_judge.py >>"$LOG" 2>&1
RC=$?
stage D4_REJUDGE "exit=$RC"
if [ $RC -ne 0 ]; then exit $RC; fi

stage D5_PANEL "cross-family panel (mistral rungs)"
python3 scripts/r11_crossfamily_panel.py >>"$LOG" 2>&1
RC=$?
stage D5_PANEL "exit=$RC"
if [ $RC -ne 0 ]; then exit $RC; fi

# STAGE 4: commit + push the produced measurement records (builder
# namespace only; the audit branch is never touched — audit_branch_guard
# RULE 1 would refuse it anyway).
BRANCH=$(git rev-parse --abbrev-ref HEAD)
stage COMMIT "staging builder-namespace artifacts on $BRANCH"
ARTS=$(git status --porcelain eval | awk '{print $2}')
if [ -z "$ARTS" ]; then
    stage COMMIT "no artifact changes — nothing to commit"
else
    # Art. 12: token-pattern grep on staged bytes must be 0.
    if git diff --cached --name-only >/dev/null 2>&1; then :; fi
    git add $ARTS
    if git diff --cached | grep -E "(ghp_|gho_|ghs_|sk-[a-z0-9]{20,}|xoxb-|AKIA[0-9A-Z]{16})" >/dev/null; then
        stage COMMIT "SECRET-PATTERN-GREP NONZERO — push REFUSED (Art. 12)"
        exit 4
    fi
    git commit -m "R11 post-reset queue run: D6 30-pair battery + D4 re-judgment + D5 panel (typed outcomes in eval/)" \
        || { stage COMMIT "commit failed (see log)"; exit 5; }
    if git push origin "$BRANCH" >>"$LOG" 2>&1; then
        stage PUSH "pushed $BRANCH (Art. LXXXV)"
    else
        stage PUSH "PUSH FAILED — artifacts committed locally; push manually (PAT via vault lookup-first)"
        exit 6
    fi
fi

stage DONE "queue complete — gate re-decision belongs to the auditor (Art. XXVI)"
exit 0
