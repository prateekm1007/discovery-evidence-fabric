#!/usr/bin/env python3
"""tests/test_conformal_predictor_engine.py — the engine-native
conformal FA-control battery (claim c-0112; deterministic, ZERO LLM,
ZERO network — Art. 22: fixtures prove mechanics; the real-telemetry
evals are the executor script's committed record).

Covers:
  - the lag-ORDER contract (byte-parity vs a manually-built
    contract-order row — the c-0108 lesson 2 bug class pinned);
  - the ensemble=False guard (the walk-forward coverage assertion
    BREAKS if the flag flips — the c-0108 lesson 1);
  - determinism (two fits byte-identical; PYTHONHASHSEED 1/2
    subprocess equality — the Art. 15 discipline);
  - the typed refusals (constant series / short history / NaN /
    bad confidence / missing sampling period — Art. 3: fail closed,
    typed, never a fabricated interval);
  - the computed FA budget (hand-math parity; CI bounds sane);
  - the typed shift leg (the alert fires at the offset, the coverage
    drop is computed and disclosed).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402

from discovery_fabric.engine import conformal_predictor as cp  # noqa: E402


def _ar_series(n: int = 480, seed: int = 7, shift: float = 0.0,
               shift_from: int = 10 ** 9) -> np.ndarray:
    """The deterministic AR(1) fixture (the c-0108 convention)."""
    rng = np.random.default_rng(seed)
    y = np.empty(n)
    y[0] = 10.0
    noise = rng.normal(0.0, 0.35, size=n)
    for i in range(1, n):
        y[i] = 0.7 * y[i - 1] + 3.0 + noise[i]
    if shift:
        y[shift_from:] = y[shift_from:] + shift
    return y


class TestLagContract(unittest.TestCase):
    def test_lag_matrix_column0_is_most_recent(self):
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        X, t = cp.lag_matrix(y, lags=3)
        # row 0 targets y[3]: [y2, y1, y0] — column 0 MOST RECENT
        self.assertEqual(X[0].tolist(), [3.0, 2.0, 1.0])
        self.assertEqual(t.tolist(), [4.0, 5.0, 6.0])

    def test_wrapper_row_is_byte_identical_to_manual_contract_row(self):
        """The c-0108 lesson 2 pinned: the predict-window reshape must
        equal the manually-built contract-order row."""
        y = _ar_series(240)
        model = cp.fit_conformal(y[:200], lags=8)
        window = y[200 - 8:200]
        manual = window[::-1].reshape(1, -1)
        pred, pis = model["mapie"].predict(
            manual, ensemble=cp.ENSEMBLE, confidence_level=0.9,
            allow_infinite_bounds=False)
        iv = cp.conformal_interval(model, window)
        self.assertEqual(float(pred[0]), iv["pred"])
        self.assertEqual(float(pis[0, 0, 0]), iv["lo"])
        self.assertEqual(float(pis[0, 1, 0]), iv["hi"])


class TestCoverageGuarantee(unittest.TestCase):
    def test_walk_forward_coverage_meets_declaration(self):
        """In-distribution walk-forward coverage >= the declared
        1-alpha on the committed fixture — THE ensemble=False guard
        (flipping the flag drops this to ~0.5, reds the suite: the
        c-0108 lesson 1 is enforced by this assertion, not prose)."""
        y = _ar_series(480)
        model = cp.fit_conformal(y[:280], lags=8, confidence=0.90)
        cov = cp.rolling_coverage(model, y, start=280)
        self.assertEqual(cov["n"], 200)
        self.assertGreaterEqual(cov["coverage"], 0.90)

    def test_interval_is_finite_and_ordered(self):
        y = _ar_series(240)
        model = cp.fit_conformal(y[:200])
        iv = cp.conformal_interval(model, y[192:200])
        self.assertLess(iv["lo"], iv["hi"])
        self.assertTrue(iv["lo"] <= iv["pred"] <= iv["hi"])
        self.assertFalse(iv["ensemble"])  # the pin, in the record


class TestDeterminism(unittest.TestCase):
    def test_two_fits_byte_identical(self):
        y = _ar_series(240)
        m1 = cp.fit_conformal(y[:200])
        m2 = cp.fit_conformal(y[:200])
        iv1 = cp.conformal_interval(m1, y[192:200])
        iv2 = cp.conformal_interval(m2, y[192:200])
        self.assertEqual(iv1, iv2)

    def test_eval_summary_digest_stable_across_hash_seeds(self):
        """The Art. 15 discipline: the record digest is identical
        across PYTHONHASHSEED 1/2 in fresh subprocesses."""
        here = Path(__file__).resolve().parent
        code = (
            "import sys\n"
            "sys.path.insert(0, {repo!r})\n"
            "import numpy as np\n"
            "from discovery_fabric.engine import conformal_predictor as cp\n"
            "rng = np.random.default_rng(7)\n"
            "y = np.empty(240)\n"
            "y[0] = 10.0\n"
            "noise = rng.normal(0.0, 0.35, size=240)\n"
            "for i in range(1, 240):\n"
            "    y[i] = 0.7 * y[i-1] + 3.0 + noise[i]\n"
            "m = cp.fit_conformal(y[:200])\n"
            "s = cp.eval_summary(m, y, start=200)\n"
            "s['coverage'].pop('alerts')\n"
            "print(cp.canonical_digest(s))\n"
        ).format(repo=str(REPO))
        digests = []
        for seed in ("1", "2"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            r = subprocess.run(
                [sys.executable, "-c", code], capture_output=True,
                text=True, env=env, cwd=str(here), timeout=180)
            self.assertEqual(r.returncode, 0, r.stderr[-400:])
            digests.append(r.stdout.strip())
        self.assertEqual(digests[0], digests[1])


class TestTypedRefusals(unittest.TestCase):
    """Art. 3: fail closed, typed, never silent — no fallback
    epistemology, no fabricated interval."""

    def test_constant_series_refused(self):
        y = np.full(240, 5.0)
        try:
            cp.fit_conformal(y)
            raise AssertionError("constant series must refuse")
        except cp.ConformalRefused as e:
            self.assertEqual(e.reason, "DEGENERATE_CONSTANT_SERIES")

    def test_short_history_refused(self):
        y = _ar_series(12)
        try:
            cp.fit_conformal(y)
            raise AssertionError("short history must refuse")
        except cp.ConformalRefused as e:
            self.assertEqual(e.reason, "INSUFFICIENT_HISTORY")

    def test_nan_input_refused(self):
        y = _ar_series(240)
        y[10] = np.nan
        try:
            cp.fit_conformal(y)
            raise AssertionError("NaN history must refuse")
        except cp.ConformalRefused as e:
            self.assertEqual(e.reason, "NON_FINITE_INPUT")

    def test_bad_confidence_refused(self):
        y = _ar_series(240)
        for conf in (0.0, 1.0, -0.5):
            try:
                cp.fit_conformal(y, confidence=conf)
                raise AssertionError(f"confidence {conf} must refuse")
            except cp.ConformalRefused as e:
                self.assertEqual(e.reason, "BAD_CONFIDENCE")

    def test_missing_period_refused_not_silently_assumed(self):
        """The per-year conversion NEVER assumes a sampling period —
        omission is a typed refusal (Art. 9)."""
        try:
            cp.fa_budget(3, 200, period_seconds=None)
            raise AssertionError("missing period must refuse")
        except cp.ConformalRefused as e:
            self.assertEqual(e.reason, "MISSING_SAMPLING_PERIOD")
        # the evaluator surfaces the refusal typed, with the raw
        # assumption-free rate alongside
        y = _ar_series(480)
        model = cp.fit_conformal(y[:280])
        s = cp.eval_summary(model, y, start=280, period_seconds=None)
        self.assertEqual(s["fa_budget"]["refused"],
                         "MISSING_SAMPLING_PERIOD")
        self.assertIn("raw_alert_rate", s["fa_budget"])

    def test_fa_signal_nan_observation_refused(self):
        y = _ar_series(240)
        model = cp.fit_conformal(y[:200])
        try:
            cp.fa_signal(model, y[192:200], float("nan"))
            raise AssertionError("NaN observation must refuse")
        except cp.ConformalRefused as e:
            self.assertEqual(e.reason, "NON_FINITE_INPUT")


class TestComputedFABudget(unittest.TestCase):
    def test_hand_math_parity(self):
        b = cp.fa_budget(2, 200, period_seconds=3600.0)
        self.assertAlmostEqual(b["alert_rate"], 0.01, places=12)
        steps = cp.YEAR_SECONDS / 3600.0
        self.assertAlmostEqual(b["fa_per_year"], 0.01 * steps,
                               places=9)
        self.assertEqual(b["period_assumption"].split(":")[0],
                         "TYPED ASSUMPTION (Art. 9)")

    def test_ci_bounds_sane(self):
        b = cp.fa_budget(5, 200, period_seconds=60.0)
        lo, hi = b["alert_rate_ci95"]
        self.assertTrue(0.0 <= lo <= b["alert_rate"] <= hi <= 1.0)
        # zero alerts: the CI lower bound is 0 and the point is 0
        b0 = cp.fa_budget(0, 200, period_seconds=60.0)
        self.assertEqual(b0["fa_per_year"], 0.0)
        self.assertEqual(b0["alert_rate_ci95"][0], 0.0)  # exact-binomial lower bound with zero events
        self.assertGreater(b0["alert_rate_ci95"][1], 0.0)

    def test_bad_slice_refused(self):
        for kwargs in ({"alerts": -1, "n_steps": 10},
                       {"alerts": 11, "n_steps": 10},
                       {"alerts": 1, "n_steps": 0},
                       {"alerts": 1, "n_steps": 10,
                        "period_seconds": 0.0}):
            period = kwargs.pop("period_seconds", 60.0)
            expected = ("BAD_SAMPLING_PERIOD" if period <= 0
                        else "BAD_SLICE")
            try:
                cp.fa_budget(period_seconds=period, **kwargs)
                raise AssertionError(f"{kwargs} must refuse")
            except cp.ConformalRefused as e:
                self.assertEqual(e.reason, expected)


class TestTypedShiftLeg(unittest.TestCase):
    def test_shift_detected_and_disclosed(self):
        """The c-0108 measured behavior, engine-native: the alert
        fires at the offset and the coverage drop is COMPUTED."""
        clean = _ar_series(480)
        shifted = _ar_series(480, shift=2.5, shift_from=280)
        model = cp.fit_conformal(clean[:280])
        det = cp.shift_detection(model, clean, shifted,
                                 shift_offset=280)
        self.assertEqual(det["shift_offset"], 280)
        self.assertGreater(det["coverage_drop"], 0.0)
        self.assertEqual(det["first_alert_at_offset_delta"], 0)
        self.assertGreater(det["alert_steps_under_shift"], 0)

    def test_adaptive_scheme_holds_coverage_under_drift(self):
        """The engine's adaptive trailing-window scheme restores the
        guarantee on a NON-STATIONARY fixture where the static
        one-shot interval collapses — the capability the P3 roadmap
        item asks for (FA control that survives real drift)."""
        drift = _ar_series(480, shift=2.5, shift_from=280)
        # static: the fixed calibration window is shredded by the
        # step+drift (the collapse is the typed expected behavior)
        static_model = cp.fit_conformal(drift[:280])
        static = cp.rolling_coverage(static_model, drift, start=280)
        self.assertLess(static["coverage"], 0.75)
        # adaptive: the trailing window quantifies the CURRENT
        # residual population — the coverage recovers
        ada = cp.adaptive_conformal_eval(drift, window=64,
                                         refit_every=8)
        self.assertEqual(ada["scheme"], "adaptive_trailing_window")
        self.assertGreater(ada["coverage"], 0.85)
        self.assertGreater(ada["refits"], 0)

    def test_adaptive_bad_window_refused(self):
        y = _ar_series(240)
        try:
            cp.adaptive_conformal_eval(y, window=8)
            raise AssertionError("too-small window must refuse")
        except cp.ConformalRefused as e:
            self.assertEqual(e.reason, "BAD_WINDOW")


if __name__ == "__main__":
    unittest.main()
