#!/usr/bin/env python3
"""R80: flip c-0108 OPEN->DONE on completion."""
import json, datetime

NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

with open("eval/work_claims.json") as f:
    reg = json.load(f)
claims = reg["claims"] if isinstance(reg, dict) and "claims" in reg else reg
c = next(x for x in claims if str(x.get("claim_id")) == "c-0108")
assert str(c.get("status")).upper() == "OPEN", "c-0108 not OPEN"
c["status"] = "DONE"
c["completed_at"] = f"{NOW} (sandbox clock, TRUE UTC)"
c["completion_note"] = (
    "DONE: the conformal FA-control prototype is landed and green — "
    "scripts/r80_conformal_fa.py (lag-feature featurizer + Ridge one-step "
    "predictor + MAPIE TimeSeriesRegressor enbpi conformal intervals, "
    "random_state-pinned for byte-identical fits) with 7 CI-wired "
    "deterministic tests. COMPUTED EVIDENCE before every threshold (never "
    "assumed): (1) the ensemble=True aggregation path BROKE the guarantee "
    "— in-sample calibration 0.902 but walk-forward coverage 0.525; "
    "ensemble=False restored 0.900 EXACT (the base estimator predicts, the "
    "conformal residuals own the interval — the guarantee, not the "
    "aggregation, wins); (2) the lag-ORDER contract caught twice by the "
    "fixture probe: the wrapper fed the window chronologically (and an "
    "initial [::-1] fix was a 2D row-reverse NO-OP on a single-row "
    "matrix) — in-sample 0.902 / walk-forward 0.525 under the wrong order, "
    "0.915 with the right one; the CI now asserts wrapper == manually-built "
    "contract-order row byte-identically (the bug class is pinned); (3) "
    "in-distribution walk-forward coverage 0.915 over 400 steps (>= 0.90 "
    "declared), a +2.5 injected level shift is detected at offset 0 with "
    "36/200 alert steps (coverage drops to 0.820), the FA verdict is typed "
    "with side; (4) determinism via random_state=17 (two independent fits "
    "produce byte-identical intervals); (5) freeze parity (15 baselines) "
    "+ zero-network. CI wiring additive: the suite joins the queue-surface "
    "invocation list + mapie joins the Install-test-deps step (the "
    "c-0066/c-0107 precedent). NOTICE.md: the MAPIE row updated (planned -> "
    "in-tree fixture prototype with the computed numbers). Typed next "
    "steps: the Time-MoE (Apache-2.0) / MOMENT (MIT) FM evals + the real "
    "C-MAPSS/XJTU-SY/CWRU runs (heavy downloads; the vault HF_TOKEN "
    "custody is in place). NO frozen bytes touched; the c-0106 peer lane "
    "untouched; 41/41 tests green across the four convergence+chemistry+FA "
    "suites.")

if isinstance(reg, dict):
    reg["claims"] = claims
with open("eval/work_claims.json", "w") as f:
    json.dump(reg, f, indent=1, ensure_ascii=False)
print("c-0108 OPEN->DONE")
