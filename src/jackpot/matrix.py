"""Build the score-probability matrix that every market is derived from.

The matrix ``m[h][a]`` is the probability that the home team scores ``h`` and the
away team scores ``a``. It is the single source of truth for the whole Tab: every
bet market is just a sum over the relevant cells, which is what keeps predictions
mutually consistent.
"""
from __future__ import annotations

from typing import List

from .poisson import poisson_pmf, dixon_coles_tau

DEFAULT_RHO = -0.05
DEFAULT_MAX_GOALS = 8


def build_score_matrix(
    lam_home: float,
    lam_away: float,
    rho: float = DEFAULT_RHO,
    max_goals: int = DEFAULT_MAX_GOALS,
) -> List[List[float]]:
    """Return a ``(max_goals+1) x (max_goals+1)`` normalised score matrix.

    Each cell is the independent-Poisson probability of that scoreline, scaled by
    the Dixon-Coles ``tau`` correction, then the whole grid is renormalised so it
    sums to 1 (the tail beyond ``max_goals`` is folded back in by normalisation).
    """
    if lam_home < 0 or lam_away < 0:
        raise ValueError("lambdas must be non-negative")

    n = max_goals + 1
    grid: List[List[float]] = [[0.0] * n for _ in range(n)]
    total = 0.0
    for h in range(n):
        ph = poisson_pmf(h, lam_home)
        for a in range(n):
            pa = poisson_pmf(a, lam_away)
            cell = ph * pa * dixon_coles_tau(h, a, lam_home, lam_away, rho)
            if cell < 0:
                raise ValueError(
                    f"negative scoreline probability at ({h},{a}); rho={rho} "
                    "is out of the safe range for these lambdas"
                )
            grid[h][a] = cell
            total += cell

    if total <= 0:
        raise ValueError("degenerate score matrix (total probability is zero)")

    for h in range(n):
        for a in range(n):
            grid[h][a] /= total
    return grid
