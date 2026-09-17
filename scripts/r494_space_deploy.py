#!/usr/bin/env python3
"""scripts/r494_space_deploy.py — R494: deploy the union build
(a2_adversarial_gauntlet/2.0.0 — the v4 burden-of-proof gauntlet) to
the production Space, reusing the R491 deploy machinery verbatim (the
same upload/stage/variables/restart flow); only the record path and
the round attribution differ (the R491 record remains the sibling
line's deploy history; this round's record ships under R494/).

Usage: python3 scripts/r494_space_deploy.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r491_space_deploy as r491  # noqa: E402

OUT = REPO / "R494" / "SPACE_DEPLOY_RECORD.json"


def main() -> int:
    rc = r491.main()
    # the R491 machinery wrote its own record; copy the bytes into the
    # R494 record with this round's attribution (both ship; the git
    # history keeps each)
    r491_record = REPO / "R491" / "SPACE_DEPLOY_RECORD.json"
    try:
        rec = json.loads(r491_record.read_text())
    except (OSError, json.JSONDecodeError):
        rec = {}
    rec = dict(rec)
    rec["round"] = "R494"
    rec["deployed_by"] = ("scripts/r494_space_deploy.py (the R491 "
                          "machinery reused verbatim)")
    rec["purpose"] = ("the union build a2_adversarial_gauntlet/2.0.0 "
                      "(the v4 burden-of-proof gauntlet — the "
                      "race-instance-12/13 reconciliation of the "
                      "sibling's 1.1.0/v4.1 floors and this line's "
                      "burden classes) — the DEV-corpus measurement "
                      "that follows runs on the DEPLOYED instrument's "
                      "bytes")
    rec["recorded_at"] = datetime.now(timezone.utc).isoformat()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, default=str))
    print(f"[r494-deploy] record -> {OUT.relative_to(REPO)}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
