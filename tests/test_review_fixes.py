"""Regression tests for issues found in code review."""
import math

import pytest

from jackpot.matrix import build_score_matrix
from jackpot.markets import over_under
from jackpot.strength import TeamRates, estimate_strength


# #2 negative tau must not silently produce negative probabilities
def test_matrix_rejects_rho_that_makes_negative_cells():
    # rho=2.0 makes tau(1,1) = 1 - 2 = -1  -> negative cell
    with pytest.raises(ValueError):
        build_score_matrix(1.4, 1.1, rho=2.0, max_goals=8)


def test_matrix_accepts_normal_rho():
    m = build_score_matrix(1.4, 1.1, rho=-0.05, max_goals=8)
    assert all(cell >= 0 for row in m for cell in row)


# #5 under should be a direct sum, equal to the complement for a normalised matrix
def test_under_is_direct_sum():
    m = build_score_matrix(1.3, 1.1, max_goals=10)
    ou = over_under(m, 2.5)
    manual_under = sum(
        m[h][a] for h in range(len(m)) for a in range(len(m)) if h + a <= 2.5
    )
    assert math.isclose(ou["under"], manual_under, abs_tol=1e-12)
    assert math.isclose(ou["over"] + ou["under"], 1.0, abs_tol=1e-9)


# #12 negative match count is a data error and must be rejected
def test_estimate_strength_rejects_negative_matches():
    with pytest.raises(ValueError):
        estimate_strength(TeamRates(1.5, 1.5, matches=-3, uses_xg=True), league_avg=1.5)
