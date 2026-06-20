"""Proper scoring rules for evaluating probabilistic predictions.

All take ``probs`` (a probability vector summing to ~1) and ``outcome_index``
(the index of the outcome that actually happened). Lower is better for all three.
Pure standard library.
"""
from __future__ import annotations

import math
from typing import Sequence

_EPS = 1e-15


def _check(probs: Sequence[float], outcome_index: int) -> None:
    if not 0 <= outcome_index < len(probs):
        raise ValueError("outcome_index out of range for probs")


def log_loss(probs: Sequence[float], outcome_index: int) -> float:
    """Negative log-likelihood of the realised outcome (clipped to stay finite)."""
    _check(probs, outcome_index)
    p = min(1.0, max(_EPS, probs[outcome_index]))
    return -math.log(p)


def brier_score(probs: Sequence[float], outcome_index: int) -> float:
    """Mean squared error against the one-hot realised outcome."""
    _check(probs, outcome_index)
    return sum((p - (1.0 if i == outcome_index else 0.0)) ** 2 for i, p in enumerate(probs))


def ranked_probability_score(probs: Sequence[float], outcome_index: int) -> float:
    """RPS for ordered categories (e.g. 1X2 = home < draw < away).

    Squared error between the cumulative predicted and cumulative observed
    distributions, averaged over the r-1 thresholds. Rewards putting mass *near*
    the true outcome, not just on it — the right metric for ordered results.
    """
    _check(probs, outcome_index)
    r = len(probs)
    cum_pred = 0.0
    cum_obs = 0.0
    total = 0.0
    for i in range(r - 1):
        cum_pred += probs[i]
        cum_obs += 1.0 if i == outcome_index else 0.0
        total += (cum_pred - cum_obs) ** 2
    return total / (r - 1)
