"""
Wilson score confidence interval for a binomial proportion (e.g. "this
config passed k of n trials/tasks"). Used everywhere this project reports
a success rate.

Why Wilson and not the textbook "p +/- z*sqrt(p(1-p)/n)" (Wald) interval:
Wald is a straight-line approximation that gets badly wrong near 0% or
100% at small n -- it can even produce a lower bound below 0 or an upper
bound above 1, which is nonsense for a probability. Wilson comes from
inverting the actual hypothesis-test statistic instead of linearizing it,
so it stays inside [0, 1] and stays sane exactly where this project's
numbers live (n around 20-40, rates from 0% to 100%).

No statsmodels dependency: this project has stayed intentionally
stdlib-only (plus PyYAML and pytest), and the plan explicitly allows
implementing Wilson from its closed form instead of pulling in a stats
library for one function.
"""

from __future__ import annotations

import math

# z-scores for the confidence levels this project actually reports (the
# 97.5th, 95th, and 99.5th percentiles of the standard normal, i.e. the
# two-sided z for 95%/90%/99% confidence). A tiny fixed table beats
# depending on scipy's inverse-normal-CDF for three numbers.
_Z_SCORES = {0.90: 1.6448536269514722, 0.95: 1.959963984540054, 0.99: 2.5758293035489004}


def wilson_ci(successes: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """
    Wilson score interval for `successes` out of `n` trials. Returns
    (lower, upper), both clamped to [0, 1]. n=0 returns (0.0, 1.0) -- "no
    data" is not the same claim as "definitely 0%".
    """
    if confidence not in _Z_SCORES:
        raise ValueError(f"unsupported confidence {confidence!r}, expected one of {sorted(_Z_SCORES)}")
    if n == 0:
        return (0.0, 1.0)
    if not 0 <= successes <= n:
        raise ValueError(f"successes={successes} must be between 0 and n={n}")

    z = _Z_SCORES[confidence]
    phat = successes / n
    z2 = z * z

    denom = 1 + z2 / n
    center = phat + z2 / (2 * n)
    margin = z * math.sqrt(phat * (1 - phat) / n + z2 / (4 * n * n))

    lower = (center - margin) / denom
    upper = (center + margin) / denom
    return (max(0.0, lower), min(1.0, upper))


def wilson_ci_pct(successes: int, n: int, confidence: float = 0.95) -> dict:
    """Same as wilson_ci, but returns a dict with the point estimate too --
    the shape a report table actually wants: {rate, lower, upper, n}."""
    lower, upper = wilson_ci(successes, n, confidence)
    return {
        "rate": successes / n if n else 0.0,
        "ci_lower": lower,
        "ci_upper": upper,
        "n": n,
        "confidence": confidence,
    }
