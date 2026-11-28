#!/bin/bash
# r176i_drive.sh — crash-isolation + seat-window wrapper for the AM53
# invention run (claim c-0283): the driver is byte-resumable per item
# (completed items persist and are never re-run); every RELAUNCH
# re-probes the judge seats (a recovered ctai quota window is picked
# up at the next boundary; the seat per item is recorded in the pair
# file — availability-window shaping, disclosed in the prereg
# amendment). Exit 3 (both seats down) waits 30 min and re-probes
# rather than dying — the overnight window is used, never spun.
cd /home/z/my-project/repo || exit 1
LOG=/tmp/r176i_run.log
for attempt in $(seq 1 40); do
  echo "[drive] relaunch $attempt $(date -u +%H:%M:%SZ)" >> "$LOG"
  python3 scripts/r176_invention_run.py >> "$LOG" 2>&1
  rc=$?
  echo "[drive] exit $rc $(date -u +%H:%M:%SZ)" >> "$LOG"
  if [ "$rc" -eq 0 ]; then
    echo "[drive] COMPLETE" >> "$LOG"
    break
  fi
  if [ "$rc" -eq 3 ]; then
    echo "[drive] both judge seats down — wait 30 min and re-probe" >> "$LOG"
    sleep 1800
  else
    sleep 60
  fi
done
