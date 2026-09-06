#!/bin/bash
# launch the acceptance driver fully detached (survives the caller)
cd "$(dirname "$0")/.." || exit 1
mkdir -p ENGINE_RUNS R415/PRODUCT_AVAILABILITY_V1
LOG=ENGINE_RUNS/r415_acceptance.log
if [ -n "$1" ]; then
  setsid python3 scripts/r415_acceptance_run.py "$1" >> "$LOG" 2>&1 < /dev/null &
else
  setsid python3 scripts/r415_acceptance_run.py >> "$LOG" 2>&1 < /dev/null &
fi
echo "driver launched (pid $!)"
