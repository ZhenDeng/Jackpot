"""Regression tests for issues found in code review."""
import math

import pytest

from jackpot.matrix import build_score_matrix
from jackpot.markets import over_under
from jackpot.strength import TeamRates, estimate_strength
from jackpot.data.understat import parse_teams_data, compute_league_avg


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


# #4 league average must be match-weighted, not a flat mean of per-team rates
def test_compute_league_avg_is_match_weighted():
    teams = {
        "A": {"scored_per_game": 2.0, "conceded_per_game": 1.0, "matches": 30},
        "B": {"scored_per_game": 1.0, "conceded_per_game": 2.0, "matches": 5},
    }
    # flat mean would be 1.5; match-weighted = (2.0*30 + 1.0*5)/35 = 1.857...
    avg = compute_league_avg(teams)
    assert math.isclose(avg, (2.0 * 30 + 1.0 * 5) / 35, rel_tol=1e-9)
    assert avg > 1.5  # weighted toward the team with more matches


# #10 UTF-8 team names (hex-escaped by Understat) must decode correctly
def test_parse_teams_data_decodes_utf8_names():
    # Understat hex-escapes UTF-8 bytes; "Alaves" with accent -> Alav\xc3\xa9s
    payload = '{"1": {"title": "Alav\\xc3\\xa9s", "history": [{"xG": 1.0, "xGA": 1.0}]}}'
    html = "var teamsData = JSON.parse('" + payload + "');"
    parsed = parse_teams_data(html)
    assert "Alavés" in parsed  # 'Alavés'


# #12 negative match count is a data error and must be rejected
def test_estimate_strength_rejects_negative_matches():
    with pytest.raises(ValueError):
        estimate_strength(TeamRates(1.5, 1.5, matches=-3, uses_xg=True), league_avg=1.5)
