"""Poisson probability mass and the Dixon-Coles low-score correction.

Pure standard library (``math`` only) so the engine has zero dependencies and is
trivially testable.
"""
from __future__ import annotations

import math


def poisson_pmf(k: int, lam: float) -> float:
    """Probability of exactly ``k`` events for a Poisson rate ``lam``.

    P(k; lam) = lam^k * e^-lam / k!
    """
    if k < 0:
        raise ValueError("k must be a non-negative integer")
    if lam < 0:
        raise ValueError("lam (rate) must be non-negative")
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def dixon_coles_tau(
    home_goals: int,
    away_goals: int,
    lam_home: float,
    lam_away: float,
    rho: float,
) -> float:
    """Dixon-Coles dependency correction (tau) for low-scoring scorelines.

    Plain independent Poisson under-counts 0-0 and 1-1 draws and over-counts
    1-0 / 0-1. This multiplier corrects the four cells in {0,1} x {0,1}; every
    other scoreline is left unchanged (returns 1.0). ``rho`` is typically a small
    negative number (e.g. -0.05). ``rho == 0`` reduces to plain Poisson.
    """
    if home_goals == 0 and away_goals == 0:
        return 1.0 - lam_home * lam_away * rho
    if home_goals == 0 and away_goals == 1:
        return 1.0 + lam_home * rho
    if home_goals == 1 and away_goals == 0:
        return 1.0 + lam_away * rho
    if home_goals == 1 and away_goals == 1:
        return 1.0 - rho
    return 1.0
