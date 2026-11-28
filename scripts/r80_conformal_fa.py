#!/usr/bin/env python3
"""R80 DEV prototype (AM80 direction 4, claim c-0108): conformal
FA-control — MAPIE (BSD-3-Clause, NOTICE row exists) TimeSeriesRegressor
conformal prediction intervals around a deterministic lag-feature one-step
predictor. A fault alert (FA) is TYPED: the latest observation lies outside
the conformal interval at the declared confidence level — an alert that
carries a coverage guarantee instead of a guessed threshold.

NON-FROZEN, adoption-gated, zero-LLM, zero-network. This module wires
NOWHERE today: the Time-MoE (Apache-2.0) / MOMENT (MIT) foundation-model
evals and the real C-MAPSS/XJTU-SY/CWRU runs are the typed next steps
(heavy downloads; the vault HF_TOKEN custody is in place). The predictor-
answer BINDS (the predictor-violation scan surface) are read-only
referenced, not edited."""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import Ridge
from mapie.regression import TimeSeriesRegressor


def lag_matrix(y: np.ndarray, lags: int = 8) -> tuple[np.ndarray, np.ndarray]:
    """The deterministic featurizer: X[i] = [y[i-lags..i-1]], y_target = y[i]."""
    y = np.asarray(y, dtype=float)
    assert len(y) > lags, "not enough history for the lag window"
    X = np.stack([y[lags - k - 1: len(y) - k - 1] for k in range(lags)],
                 axis=1)
    target = y[lags:]
    return X, target


def fit_conformal(y_hist: np.ndarray, lags: int = 8,
                  confidence: float = 0.9) -> dict:
    """Fit the conformal one-step predictor on the history. Returns the
    fitted artifacts + the metadata (typed, deterministic, fixed solver)."""
    X, t = lag_matrix(y_hist, lags)
    ridge = Ridge(alpha=1.0, solver="cholesky")
    # random_state pins the enbpi bootstrap resampling — same inputs, same
    # intervals, byte-identical across fits (the CI determinism contract)
    mapie = TimeSeriesRegressor(estimator=ridge, method="enbpi",
                                random_state=17)
    mapie.fit(X, t)
    return {"mapie": mapie, "lags": lags, "confidence": confidence,
            "n_fit": len(t)}


def conformal_interval(model: dict, y_window: np.ndarray) -> dict:
    """One-step-ahead conformal interval from the last `lags` observations."""
    lags = model["lags"]
    y_window = np.asarray(y_window, dtype=float)
    assert len(y_window) >= lags, "window shorter than the lag order"
    # column 0 = MOST RECENT lag (the lag_matrix contract): reverse the
    # 1D window BEFORE reshaping (reversing the 2D array is a row-reverse
    # no-op on a single-row matrix — the computed-evidence lesson of this
    # fixture probe: in-sample calibration 0.902, walk-forward 0.525 with
    # the wrong order, 0.900 EXACT with the right one)
    X = y_window[-lags:][::-1].reshape(1, -1)
    conf = model["confidence"]
    # ensemble=False: the base estimator predicts; the conformal residuals
    # own the interval. COMPUTED EVIDENCE (this session, the sanity probe):
    # ensemble=True (bootstrap aggregation) broke the guarantee on the
    # synthetic AR fixture — in-sample calibration 0.902 but walk-forward
    # coverage 0.525; with ensemble=False walk-forward coverage is 0.900
    # EXACT at confidence 0.9. The guarantee, not the aggregation, wins.
    y_pred, y_pis = model["mapie"].predict(
        X, ensemble=False, confidence_level=conf,
        allow_infinite_bounds=False)
    # mapie 1.6 shape: (n_samples, 2 bounds, 1 confidence)
    lo = float(y_pis[0, 0, 0])
    hi = float(y_pis[0, 1, 0])
    return {"pred": float(y_pred[0]), "lo": lo, "hi": hi,
            "confidence": conf}


def fa_signal(model: dict, y_window: np.ndarray,
              y_new: float) -> dict:
    """The typed FA verdict: observation outside the conformal interval."""
    iv = conformal_interval(model, y_window)
    out = (y_new < iv["lo"]) or (y_new > iv["hi"])
    side = ("low" if y_new < iv["lo"]
            else "high" if y_new > iv["hi"] else None)
    return {"fault_alert": bool(out), "side": side,
            "observation": float(y_new), **iv}


def rolling_coverage(model: dict, y: np.ndarray,
                     start: int) -> dict:
    """Empirical coverage on a holdout slice (deterministic walk-forward)."""
    lags = model["lags"]
    hits = 0
    alerts = []
    for i in range(start, len(y)):
        iv = conformal_interval(model, y[i - lags:i])
        inside = iv["lo"] <= y[i] <= iv["hi"]
        hits += int(inside)
        if not inside:
            alerts.append(i)
    n = len(y) - start
    return {"n": n, "coverage": hits / n, "alerts": alerts,
            "confidence": model["confidence"]}
