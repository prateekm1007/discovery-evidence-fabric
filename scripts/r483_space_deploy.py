#!/usr/bin/env python3
"""R483 — the union deploy: the campaign-unblock tree (the R483 union
aeaab57f) to the canonical production Space.

The r481 flow REUSED BY IMPORT with ONE delta: the record path
(R483/SPACE_DEPLOY_RECORD.json). Everything else — the R480 repoint
preservation, the fingerprint-gated ring + PAT re-wiring, the
push-before-deploy gate, the identity bake, the deterministic
post-wire restart — is the r481 driver's, unchanged.

This is the behavior-bearing round the R482 deferral pointed at: the
stale spawn pin retired, the repointed slot classified, the reasoning
ceiling raised, the span telemetry + the routing observability live.
The campaign re-run (attempt 3) executes AFTER this deploy, on this
tree.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r481_space_deploy as r481  # noqa: E402

# the ONE delta: this round's record path
r481.OUT = REPO / "R483" / "SPACE_DEPLOY_RECORD.json"

if __name__ == "__main__":
    raise SystemExit(r481.main())
