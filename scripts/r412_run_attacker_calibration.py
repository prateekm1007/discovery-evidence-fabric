#!/usr/bin/env python3
"""scripts/r412_run_attacker_calibration.py — P0-1 driver.

Thin CLI wrapper over R412/CALIBRATION/calibration_runner.py (the
runner module is the importable, testable implementation; this script
only dispatches arguments). See the runner docstring for the
measurement semantics and the constitutional grounding.

Examples:
  python scripts/r412_run_attacker_calibration.py --pass minimax-m3
  python scripts/r412_run_attacker_calibration.py --pass glm-5.3-free
  python scripts/r412_run_attacker_calibration.py --report
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "R412" / "CALIBRATION"))

from calibration_runner import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
