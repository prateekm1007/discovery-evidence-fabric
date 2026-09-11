---
title: Toscanini Production Validation
emoji: "\U0001F3B5"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# R446-HF-PRO — Toscanini production-validation Space

Private validation Space for the canonical Toscanini engine.

- Engine source: github.com/prateekm1007/discovery-evidence-fabric at
  commit `39e768da407ea18a82378427632c76d8505a5e17` (pinned in `HF_ENGINE_SHA.txt`).
- This Space carries the EXACT tracked tree of that commit plus a
  documented Space adaptation layer (see `Dockerfile` header: identity
  source, runtime stack, HF runtime contract — zero engine-code deltas).
- Purpose (directive PHASE 0): determine experimentally whether the
  current Toscanini machine can complete its real end-to-end production
  path when the 512 MB Render constraint is removed.
- Health: `/api/version` (identity), `/health` (readiness, honest
  typed states — infrastructure health is not product capability).
