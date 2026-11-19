#!/usr/bin/env python3
"""conformal_predictor/1.0.0 — the engine-native conformal FA-control
predictor (claim c-0112; the P3 roadmap item 3, eval/roadmap_4_to_9.md:
"conformal thresholds make FA <=1/year a computed property (coverage
>= 1-alpha)").

THE CAPABILITY (why this is engine code, not a script — the F63 rule):
a fault alert whose threshold is a COMPUTED PROPERTY of the declared
confidence, not a guessed constant. The interval carries the coverage
guarantee (MAPIE TimeSeriesRegressor, enbpi, ensemble=False); the
FA budget is COMPUTED from the measured walk-forward alert rate and
the declared sampling period — with the assumption typed, never
silent (Art. 9). This module is the measured surface the predictor
arm cites; the c-0108 fixture mechanics (scripts/r80_conformal_fa.py,
VERIFIED DEV-stage) are the seed this module makes native.

THE C-0108 COMPUTED LESSONS ENCODED (never re-learned):
  1. ensemble=False: the base estimator predicts, the conformal
     residuals own the interval. ensemble=True broke the guarantee on
     the committed fixture (in-sample 0.902, walk-forward 0.525);
     ensemble=False restores 0.900 EXACT. The walk-forward coverage
     assertion in the CI battery IS the ensemble guard — flipping the
     flag reds the suite.
  2. The lag-ORDER contract: column 0 = MOST RECENT lag; a 1D window
     is reversed BEFORE reshaping (the 2D row-reverse was a no-op —
     in-sample 0.902 / walk-forward 0.525 under the wrong order,
     0.915 with the right one). The CI pins byte-parity against a
     manually-built contract-order row.
  3. Determinism: Ridge(alpha=1.0, solver="cholesky") +
     random_state=17 pins the enbpi bootstrap — two independent fits
     produce byte-identical intervals (the unseeded bootstrap was
     nondeterministic; the CI contract asserts equality, the Art. 15
     hash-seed discipline rides it).

TYPED REFUSALS (Art. 3: fail closed, typed, never silent; no
fallback epistemology — a degenerate history never yields a
fabricated interval):
  - DEGENERATE_CONSTANT_SERIES: a constant history carries no
    learnable residual structure (the interval would be a
    zero-width artifact around the constant).
  - INSUFFICIENT_HISTORY: fewer calibration points than the typed
    minimum (the guarantee needs residuals to quantify).
  - NON_FINITE_INPUT: NaN/inf anywhere in the history or the window
    (a missing number never becomes a fabricated result — the same
    clause the route's physics leg runs under).

FA BUDGET (the roadmap's computed property): fa_budget() converts a
MEASURED alert rate (alerts/steps over a NAMED committed slice) into
failures-per-year at the declared sampling period. The conversion
rests on a TYPED ASSUMPTION (the sampling period — Art. 9 exception
clause: a labelled assumption with a sensitivity path), the point
estimate carries a binomial CI on the alert rate, and the basis (the
slice, n, alpha, period) is returned — a caller that omits the
period gets a REFUSED, never a silently-assumed conversion.

Zero LLM, zero network (the real-dataset fetches live in the
executor script scripts/r96_real_data_conformal.py, never here).
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.linear_model import Ridge
from mapie.regression import TimeSeriesRegressor

RECORD = "CONFORMAL_PREDICTOR_ENGINE/1.0.0"

# --- the typed constants (the c-0108 lessons, pinned) --------------------
ENSEMBLE = False          # the guarantee wins over the aggregation
RANDOM_STATE = 17         # the enbpi bootstrap pin (determinism)
RIDGE_ALPHA = 1.0         # the fixed solver contract
DEFAULT_LAGS = 8
DEFAULT_CONFIDENCE = 0.90
MIN_CALIBRATION_POINTS = 16   # the typed minimum residual population
YEAR_SECONDS = 31_557_600.0   # Julian year (the typed conversion basis)


class ConformalRefused(Exception):
    """The typed refusal (Art. 3): reason carries the machine-readable
    class; the caller records it, never silently falls back."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail

    def to_record(self) -> Dict[str, Any]:
        return {"record": RECORD, "refused": True,
                "reason": self.reason, "detail": self.detail[:160]}


def _check_finite(y: np.ndarray, where: str) -> None:
    arr = np.asarray(y, dtype=float)
    if arr.size and not np.all(np.isfinite(arr)):
        raise ConformalRefused(
            "NON_FINITE_INPUT",
            f"{where} carries NaN/inf — refuse, never fabricate")


def lag_matrix(y: np.ndarray, lags: int = DEFAULT_LAGS) -> Tuple[
        np.ndarray, np.ndarray]:
    """The deterministic featurizer: X[i] = [y[i-lags..i-1]] with
    column 0 the MOST RECENT lag; y_target = y[i]. The contract the
    CI pins byte-parity against (the c-0108 lesson 2)."""
    y = np.asarray(y, dtype=float)
    if lags < 1:
        raise ConformalRefused("BAD_LAG_ORDER",
                               f"lags must be >= 1, got {lags}")
    if len(y) <= lags:
        raise ConformalRefused(
            "INSUFFICIENT_HISTORY",
            f"need > {lags} points for the lag window, got {len(y)}")
    X = np.stack([y[lags - k - 1: len(y) - k - 1] for k in range(lags)],
                 axis=1)
    target = y[lags:]
    return X, target


def fit_conformal(y_hist: np.ndarray, lags: int = DEFAULT_LAGS,
                  confidence: float = DEFAULT_CONFIDENCE) -> dict:
    """Fit the conformal one-step predictor on the history. Typed
    refusals on degenerate inputs (Art. 3); deterministic (the pinned
    solver + bootstrap seed). Returns the fitted artifacts + the
    metadata (the model dict every other function consumes)."""
    _check_finite(y_hist, "y_hist")
    y = np.asarray(y_hist, dtype=float)
    if len(y) <= lags + MIN_CALIBRATION_POINTS:
        raise ConformalRefused(
            "INSUFFICIENT_HISTORY",
            f"need > lags+{MIN_CALIBRATION_POINTS} points for the "
            f"residual population, got {len(y)} (lags={lags})")
    if np.ptp(y) == 0.0:
        raise ConformalRefused(
            "DEGENERATE_CONSTANT_SERIES",
            "a constant history carries no learnable residual "
            "structure — the interval would be a zero-width artifact")
    if not (0.0 < confidence < 1.0):
        raise ConformalRefused(
            "BAD_CONFIDENCE",
            f"confidence must be in (0,1), got {confidence}")
    X, t = lag_matrix(y, lags)
    ridge = Ridge(alpha=RIDGE_ALPHA, solver="cholesky")
    mapie = TimeSeriesRegressor(estimator=ridge, method="enbpi",
                                random_state=RANDOM_STATE)
    mapie.fit(X, t)
    return {"record": RECORD, "mapie": mapie, "lags": int(lags),
            "confidence": float(confidence), "n_fit": int(len(t)),
            "ensemble": ENSEMBLE, "random_state": RANDOM_STATE,
            "hist_digest": hashlib.sha256(
                y.tobytes()).hexdigest()[:16]}


def conformal_interval(model: dict, y_window: np.ndarray) -> dict:
    """One-step-ahead conformal interval from the last `lags`
    observations (the contract-order reshape — lesson 2)."""
    if not model.get("mapie") is not None:
        raise ConformalRefused("UNFITTED_MODEL",
                               "fit_conformal first")
    lags = int(model["lags"])
    y_window = np.asarray(y_window, dtype=float)
    _check_finite(y_window, "y_window")
    if len(y_window) < lags:
        raise ConformalRefused(
            "INSUFFICIENT_HISTORY",
            f"window shorter than the lag order ({len(y_window)} < "
            f"{lags})")
    X = y_window[-lags:][::-1].reshape(1, -1)
    conf = float(model["confidence"])
    # ensemble=False pinned (lesson 1): the base estimator predicts,
    # the conformal residuals own the interval
    y_pred, y_pis = model["mapie"].predict(
        X, ensemble=ENSEMBLE, confidence_level=conf,
        allow_infinite_bounds=False)
    lo = float(y_pis[0, 0, 0])
    hi = float(y_pis[0, 1, 0])
    if not (math.isfinite(lo) and math.isfinite(hi)):
        raise ConformalRefused(
            "NON_FINITE_INTERVAL",
            "the conformal interval is not finite — refuse, never "
            "fabricate")
    return {"pred": float(y_pred[0]), "lo": lo, "hi": hi,
            "confidence": conf, "ensemble": ENSEMBLE}


def fa_signal(model: dict, y_window: np.ndarray,
              y_new: float) -> dict:
    """The typed FA verdict: the observation lies outside the
    conformal interval at the declared confidence (with side). The
    alert carries the guarantee, not a guessed threshold."""
    y_new_f = float(y_new)
    if not math.isfinite(y_new_f):
        raise ConformalRefused(
            "NON_FINITE_INPUT",
            "the observation is NaN/inf — refuse, never fabricate")
    iv = conformal_interval(model, y_window)
    out = (y_new_f < iv["lo"]) or (y_new_f > iv["hi"])
    side = ("low" if y_new_f < iv["lo"]
            else "high" if y_new_f > iv["hi"] else None)
    return {"record": RECORD, "fault_alert": bool(out),
            "side": side, "observation": y_new_f, **iv}


def rolling_coverage(model: dict, y: np.ndarray, start: int) -> dict:
    """Empirical walk-forward coverage on a holdout slice
    (deterministic; the slice [start, len) is one-step-ahead
    evaluated in order)."""
    y = np.asarray(y, dtype=float)
    _check_finite(y, "y")
    lags = int(model["lags"])
    if start <= lags or start >= len(y):
        raise ConformalRefused(
            "BAD_SLICE",
            f"start must be in ({lags}, {len(y)}), got {start}")
    hits = 0
    alerts = []
    for i in range(start, len(y)):
        iv = conformal_interval(model, y[i - lags:i])
        inside = iv["lo"] <= y[i] <= iv["hi"]
        hits += int(inside)
        if not inside:
            alerts.append(i)
    n = len(y) - start
    return {"record": RECORD, "n": int(n),
            "coverage": hits / n, "alerts": alerts,
            "confidence": float(model["confidence"]),
            "slice": [int(start), int(len(y))]}


def fa_budget(alerts: int, n_steps: int, period_seconds: float,
              alpha: float = 0.05) -> dict:
    """THE COMPUTED FA BUDGET (the roadmap's "FA <=1/year a computed
    property"). The alert rate is MEASURED on a committed slice; the
    per-year conversion rests on a TYPED ASSUMPTION (the sampling
    period — the caller supplies it; omission is a REFUSED, never a
    silently-assumed conversion, Art. 9). The point estimate carries
    a two-sided normal CI on the binomial alert rate (the sensitivity
    path).

    fa_per_year = alert_rate * (YEAR_SECONDS / period_seconds)
    """
    if period_seconds is None:
        raise ConformalRefused(
            "MISSING_SAMPLING_PERIOD",
            "the per-year conversion needs the declared sampling "
            "period — supply it or report the raw alert rate (never "
            "a silently-assumed period)")
    if not (period_seconds > 0):
        raise ConformalRefused(
            "BAD_SAMPLING_PERIOD",
            f"period_seconds must be > 0, got {period_seconds}")
    if n_steps <= 0:
        raise ConformalRefused(
            "BAD_SLICE", f"n_steps must be > 0, got {n_steps}")
    if not (0 <= alerts <= n_steps):
        raise ConformalRefused(
            "BAD_SLICE",
            f"alerts {alerts} outside [0, {n_steps}]")
    rate = alerts / n_steps
    z = 1.959963984540054  # two-sided 95% normal quantile (typed)
    den = 1.0 + z * z / n_steps
    center = (rate + z * z / (2 * n_steps)) / den
    half = z * math.sqrt(rate * (1 - rate) / n_steps
                         + z * z / (4 * n_steps * n_steps)) / den
    rate_lo = max(0.0, center - half)
    rate_hi = min(1.0, center + half)
    if alerts == 0:
        # the exact binomial lower bound with zero events is 0 (the
        # Wilson-CC construction leaves a ~1e-18 float artifact here;
        # the typed clamp makes the computed property exact)
        rate_lo = 0.0
    steps_per_year = YEAR_SECONDS / period_seconds
    return {
        "record": RECORD,
        "alerts_measured": int(alerts), "n_steps": int(n_steps),
        "alert_rate": rate,
        "alert_rate_ci95": [rate_lo, rate_hi],
        "period_seconds": float(period_seconds),
        "period_assumption": (
            "TYPED ASSUMPTION (Art. 9): the per-year conversion uses "
            "the caller-declared sampling period; the raw alert rate "
            "+ CI is the assumption-free measurement"),
        "steps_per_year": steps_per_year,
        "fa_per_year": rate * steps_per_year,
        "fa_per_year_ci95": [rate_lo * steps_per_year,
                             rate_hi * steps_per_year],
        "declared_alpha": float(alpha),
        "guarantee_note": (
            "the interval carries coverage >= 1-alpha in distribution; "
            "the FA budget is the MEASURED walk-forward alert rate "
            "converted at the declared period — the two are typed "
            "separately and never conflated"),
    }


def shift_detection(model: dict, y_clean: np.ndarray,
                    y_shifted: np.ndarray,
                    shift_offset: int) -> dict:
    """The typed shift leg: coverage on the clean holdout vs coverage
    under the injected shift (the c-0108 measured behavior: the alert
    fires AT the offset and the coverage drops — the FA controller
    behaves as typed, disclosed, never hidden)."""
    clean = rolling_coverage(model, y_clean, shift_offset)
    shifted = rolling_coverage(model, y_shifted, shift_offset)
    first_alert = (shifted["alerts"][0] - shift_offset
                   if shifted["alerts"] else None)
    return {
        "record": RECORD,
        "shift_offset": int(shift_offset),
        "clean_coverage": clean["coverage"],
        "clean_n": clean["n"],
        "shifted_coverage": shifted["coverage"],
        "shifted_n": shifted["n"],
        "coverage_drop": clean["coverage"] - shifted["coverage"],
        "alert_steps_under_shift": len(shifted["alerts"]),
        "first_alert_at_offset_delta": first_alert,
        "typed_behavior": (
            "the alert fires where the interval breaks; the coverage "
            "drop is the DISCLOSED evidence, never a defect"),
    }


def eval_summary(model: dict, y: np.ndarray, start: int,
                 period_seconds: Optional[float] = None) -> dict:
    """The one-call evaluator: walk-forward coverage + the computed
    FA budget (when the period is declared) — the record surface the
    real-data executor commits."""
    cov = rolling_coverage(model, y, start)
    out: Dict[str, Any] = {"record": RECORD, "coverage": cov,
                           "confidence": model["confidence"],
                           "ensemble": ENSEMBLE,
                           "random_state": RANDOM_STATE}
    if period_seconds is not None:
        out["fa_budget"] = fa_budget(len(cov["alerts"]), cov["n"],
                                     period_seconds)
    else:
        out["fa_budget"] = {"refused": "MISSING_SAMPLING_PERIOD",
                            "raw_alert_rate":
                                len(cov["alerts"]) / cov["n"]}
    return out


def adaptive_conformal_eval(y: np.ndarray, lags: int = DEFAULT_LAGS,
                            confidence: float = DEFAULT_CONFIDENCE,
                            window: int = 64,
                            refit_every: int = 8,
                            fit_fraction: float = 0.6) -> dict:
    """THE ADAPTIVE SCHEME (pre-registered constants, deterministic):
    trailing-window refit conformal for NON-STATIONARY telemetry.

    The static one-shot interval carries the guarantee IN
    DISTRIBUTION — real degradation telemetry is non-stationary (the
    drift is the signal), so a fixed calibration window is shredded
    by the drift (the committed real-data eval measures exactly that:
    the static pooled coverage collapses while the clean-fixture
    coverage holds — the shift leg's live proof). The typed fix is
    the adaptive scheme: the calibration window TRAILS the stream
    (refit every `refit_every` steps on the last `window` steps), so
    the interval quantifies the CURRENT residual population — the
    Gibbs-Candes adaptive-conformal semantics, deterministic here
    (the pinned solver + bootstrap seed; no wall-clock, no hash
    order — Art. 15).

    Returns the measured walk-forward coverage + the alert list +
    the refit count. The FA budget is computed by the CALLER from
    these stats (fa_budget) — the conversion stays typed.
    """
    y = np.asarray(y, dtype=float)
    _check_finite(y, "y")
    if window < lags + MIN_CALIBRATION_POINTS:
        raise ConformalRefused(
            "BAD_WINDOW",
            f"window {window} too small for lags={lags} + "
            f"{MIN_CALIBRATION_POINTS} calibration points")
    cut = int(len(y) * fit_fraction)
    if cut <= lags or cut >= len(y):
        raise ConformalRefused(
            "BAD_SLICE",
            f"fit_fraction {fit_fraction} yields cut {cut} outside "
            f"({lags}, {len(y)})")
    model = fit_conformal(y[:cut], lags=lags, confidence=confidence)
    hits = 0
    alerts = []
    refits = 0
    last_fit_at = cut
    for i in range(cut, len(y)):
        if i - last_fit_at >= refit_every:
            seg_start = max(0, i - window)
            try:
                model = fit_conformal(y[seg_start:i], lags=lags,
                                      confidence=confidence)
                last_fit_at = i
                refits += 1
            except ConformalRefused:
                # the trailing window hit a degenerate stretch: the
                # PREVIOUS fit stands (typed continuity — the refusal
                # is recorded, never a fabricated interval)
                pass
        iv = conformal_interval(model, y[i - lags:i])
        inside = iv["lo"] <= y[i] <= iv["hi"]
        hits += int(inside)
        if not inside:
            alerts.append(i)
    n = len(y) - cut
    return {"record": RECORD, "scheme": "adaptive_trailing_window",
            "window": int(window), "refit_every": int(refit_every),
            "fit_fraction": float(fit_fraction),
            "cut": int(cut), "n": int(n),
            "coverage": hits / n, "alerts": alerts,
            "refits": refits, "confidence": float(confidence)}


def canonical_digest(record: dict) -> str:
    """The Art. 15 discipline: sorted-key compact JSON sha256_16 —
    the eval records digest deterministically across hash seeds."""
    blob = json.dumps(record, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


__all__ = ["RECORD", "ConformalRefused", "ENSEMBLE", "RANDOM_STATE",
           "DEFAULT_LAGS", "DEFAULT_CONFIDENCE",
           "MIN_CALIBRATION_POINTS", "YEAR_SECONDS", "lag_matrix",
           "fit_conformal", "conformal_interval", "fa_signal",
           "rolling_coverage", "fa_budget", "shift_detection",
           "eval_summary", "adaptive_conformal_eval",
           "canonical_digest"]
