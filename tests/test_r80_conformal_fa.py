#!/usr/bin/env python3
"""R80 CI-wired acceptance tests for the conformal FA-control prototype
(scripts/r80_conformal_fa.py — MAPIE BSD-3-Clause). Deterministic, zero-LLM,
zero-network; every threshold was COMPUTED FIRST on the fixed-seed fixture
(this session's sanity probes) and only then baked in — never assumed.
Art. 22: fixtures prove MECHANICS; the Time-MoE/MOMENT FM evals + the real
dataset runs are the typed next steps (adoption-gated, no frozen bytes)."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "r80fa", REPO / "scripts" / "r80_conformal_fa.py")
r80fa = importlib.util.module_from_spec(spec)
sys.modules["r80fa"] = r80fa
spec.loader.exec_module(r80fa)


def _fixture():
    rng = np.random.default_rng(42)
    n = 1200
    y = np.zeros(n)
    for i in range(2, n):
        y[i] = 0.7 * y[i - 1] + 0.2 * y[i - 2] + 0.5 * rng.standard_normal()
    return y


def _model():
    return r80fa.fit_conformal(_fixture()[:800], lags=8, confidence=0.9)


# ---------------------------------------------------------- coverage
def test_indistribution_coverage_holds_the_guarantee():
    # COMPUTED FIRST: coverage 0.915 over 400 walk-forward steps (>= 0.90).
    cov = r80fa.rolling_coverage(_model(), _fixture(), 800)
    assert cov["n"] == 400
    assert cov["coverage"] >= 0.88, cov["coverage"]
    # a healthy FA controller is quiet in-distribution
    assert len(cov["alerts"]) <= 50, len(cov["alerts"])


def test_level_shift_is_detected_immediately():
    # COMPUTED FIRST: first alert at offset 0 of the +2.5 shift; 36/200
    # alert steps; shifted-window coverage drops to 0.820.
    y = _fixture()
    ys = y.copy()
    ys[1000:] += 2.5
    cov = r80fa.rolling_coverage(_model(), ys, 1000)
    assert cov["alerts"], "no FA on a shifted series"
    assert cov["alerts"][0] - 1000 <= 3, cov["alerts"][0] - 1000
    assert cov["coverage"] < 0.88, cov["coverage"]


def test_fa_signal_is_typed_with_side():
    y = _fixture()
    mod = _model()
    fa = r80fa.fa_signal(mod, y[992:1000], y[999] + 2.5)
    assert fa["fault_alert"] is True and fa["side"] == "high"
    assert fa["lo"] < fa["hi"] and fa["confidence"] == 0.9
    fa_ok = r80fa.fa_signal(mod, y[0:8], y[8])
    # an in-distribution point MAY alert (8.5% base rate) but stays typed
    assert isinstance(fa_ok["fault_alert"], bool)


# -------------------------------------------- the lag-order contract (the
# computed-evidence lesson: in-sample calibration was 0.902 while walk-
# forward collapsed to 0.525 under the reversed window — the wrapper must
# predict IDENTICALLY to a manually-built, contract-order row)
def test_wrapper_matches_manual_contract_order_row():
    y = _fixture()
    mod = _model()
    i = 805
    iv = r80fa.conformal_interval(mod, y[i - 8:i])
    manual = np.array([[y[i - 1 - k] for k in range(8)]])
    yp, y_pis = mod["mapie"].predict(
        manual, ensemble=False, confidence_level=0.9,
        allow_infinite_bounds=False)
    assert iv["pred"] == float(yp.ravel()[0])
    assert iv["lo"] == float(y_pis[0, 0, 0])
    assert iv["hi"] == float(y_pis[0, 1, 0])


def test_determinism():
    a = r80fa.conformal_interval(_model(), _fixture()[792:800])
    b = r80fa.conformal_interval(_model(), _fixture()[792:800])
    assert a == b


# ------------------------------------------------------------ guards
def test_frozen_baselines_untouched():
    rec = json.loads((REPO / "eval" / "r64_v9_preflight.json").read_text())
    fb = rec["checks"]["freeze_baselines_sha16"]
    for f, expected in fb.items():
        got = hashlib.sha256((REPO / f).read_bytes()).hexdigest()[:16]
        assert got == expected, f"the frozen file {f} MOVED (typed abort)"


def test_module_is_zero_network():
    src = (REPO / "scripts" / "r80_conformal_fa.py").read_text()
    for banned in ("import socket", "import requests", "import urllib",
                   "import http", "urlopen", "subprocess"):
        assert banned not in src, f"zero-network violation: {banned}"
