#!/bin/bash
# M1 campaign resilient loop — runs candidates when the endpoint is healthy,
# skips + retries during unhealthy windows. Per-candidate bash timeout 25 min
# (the driver persists per-run records + resumable run dirs; a kill loses
# nothing — the next pass resumes).
cd /home/z/my-project/discovery-evidence-fabric || exit 1

LOG=discovery_campaigns/M1_DOSSIER_CAMPAIGN_2026-08-29/loop.log
BUDGET_MINUTES=${1:-100}
START=$(date +%s)
BUDGET=$((START + BUDGET_MINUTES*60))
PASS=0

while true; do
  NOW=$(date +%s)
  if [ $NOW -ge $BUDGET ]; then
    echo "$(date -u +%H:%M:%S) budget exhausted after $BUDGET_MINUTES min, $PASS passes" >> "$LOG"
    break
  fi
  PASS=$((PASS+1))
  echo "$(date -u +%H:%M:%S) === pass $PASS ===" >> "$LOG"

  # Determine which candidates still need runs (no RUN_*.json yet)
  python3 scripts/m1_dossier_campaign.py --list > /tmp/m1_plan.txt 2>/dev/null
  TODO=$(grep -c "\[todo" /tmp/m1_plan.txt || true)
  DONE_REC=$(grep -c "REC:" /tmp/m1_plan.txt || true)
  echo "plan: $TODO todo, $DONE_REC recorded" >> "$LOG"
  if [ "$TODO" -eq 0 ]; then
    echo "$(date -u +%H:%M:%S) all candidates have records — final aggregate" >> "$LOG"
    python3 scripts/m1_dossier_campaign.py --aggregate-only >> "$LOG" 2>&1
    break
  fi

  for i in $(seq 1 22); do
    NOW=$(date +%s)
    if [ $NOW -ge $BUDGET ]; then break; fi
    # skip if record exists
    if [ -f "discovery_campaigns/M1_DOSSIER_CAMPAIGN_2026-08-29/RUN_${i}.json" ]; then
      continue
    fi
    echo "$(date -u +%H:%M:%S) candidate $i (pass $PASS)" >> "$LOG"
    timeout 1500 python3 scripts/m1_dossier_campaign.py --only "$i" >> "$LOG" 2>&1
    RC=$?
    echo "$(date -u +%H:%M:%S) candidate $i exit=$RC" >> "$LOG"
  done
done
echo "$(date -u +%H:%M:%S) loop finished" >> "$LOG"
