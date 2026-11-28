#!/usr/bin/env python3
"""r11_stats — P1-6 (Amendment 2): 95% confidence intervals on gate
proportions. n=10 CIs are wide (the novelty PASS at 1.0.0 was
provisional on a ~31-pair-need instrument); every gate record carries
the interval next to the point estimate from now on.

Wilson score interval (no continuity correction), alpha=0.05.
"""
import math


def wilson_ci(k: int, n: int, alpha: float = 0.05):
    """Returns (point, lo, hi) for a binomial proportion, or
    (None, None, None) when n == 0 (typed empty, Art. XXV)."""
    if n <= 0:
        return None, None, None
    z = 1.959963984540054  # two-sided 95%
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = (z * math.sqrt(p * (1 - p) / n
                          + z * z / (4 * n * n))) / den
    return round(p, 4), round(max(0.0, centre - half), 4), \
        round(min(1.0, centre + half), 4)


def pairs_needed(width_target: float = 0.3, alpha: float = 0.05,
                 p0: float = 0.5) -> int:
    """The n needed for a Wilson interval of approx width
    width_target at p0 (the auditor's stated ~31 for 80% power
    corresponds to width ~0.35 at p0=0.5)."""
    z = 1.959963984540054
    # crude width ~ 2*z*sqrt(p(1-p)/n); solve n
    n = (z * z * p0 * (1 - p0)) / ((width_target / 2) ** 2)
    return max(10, int(math.ceil(n)))


if __name__ == "__main__":
    for k, n in ((5, 10), (6, 10), (4, 10)):
        print(f"{k}/{n}: point,lo,hi = {wilson_ci(k, n)}")
    print("n for width 0.35:", pairs_needed(0.35))
