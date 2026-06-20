import math

import pytest

from jackpot.counts import poisson_over_under, corners_markets, cards_markets


# ---- poisson_over_under ----

def test_over_under_complements_to_one():
    ou = poisson_over_under(9.0, 9.5)
    assert math.isclose(ou["over"] + ou["under"], 1.0, abs_tol=1e-9)


def test_over_rises_with_lambda():
    assert poisson_over_under(12.0, 9.5)["over"] > poisson_over_under(7.0, 9.5)["over"]


def test_over_under_known_value():
    # lam=2, line=1.5 -> under = P(0)+P(1) = e^-2 (1+2) = 3 e^-2
    ou = poisson_over_under(2.0, 1.5)
    assert math.isclose(ou["under"], 3 * math.exp(-2), rel_tol=1e-9)


def test_over_under_rejects_negative_lambda():
    with pytest.raises(ValueError):
        poisson_over_under(-1.0, 9.5)


# ---- corners ----

def test_corners_more_attacking_team_wins_more_corners():
    m = corners_markets(home_for=7.0, home_against=4.0, away_for=3.0, away_against=6.0)
    assert m["lambda_home"] > m["lambda_away"]
    assert math.isclose(m["lambda_total"], m["lambda_home"] + m["lambda_away"], rel_tol=1e-12)


def test_corners_lambda_formula():
    m = corners_markets(home_for=7.0, home_against=4.0, away_for=3.0, away_against=6.0)
    assert math.isclose(m["lambda_home"], (7.0 + 6.0) / 2, rel_tol=1e-12)
    assert math.isclose(m["lambda_away"], (3.0 + 4.0) / 2, rel_tol=1e-12)


def test_corners_total_market_present_and_complement():
    m = corners_markets(6.0, 5.0, 5.0, 5.0, total_lines=(8.5, 9.5, 10.5))
    assert set(m["total"]) == {"8.5", "9.5", "10.5"}
    line = m["total"]["9.5"]
    assert math.isclose(line["over"] + line["under"], 1.0, abs_tol=1e-9)


# ---- cards ----

def test_cards_referee_scales_expected_cards():
    lenient = cards_markets(2.0, 2.0, referee_cpg=3.0, league_ref_avg=4.0)
    strict = cards_markets(2.0, 2.0, referee_cpg=6.0, league_ref_avg=4.0)
    assert strict["lambda_total"] > lenient["lambda_total"]


def test_cards_no_referee_means_neutral_factor():
    m = cards_markets(2.0, 1.5, referee_cpg=None)
    assert math.isclose(m["lambda_home"], 2.0, rel_tol=1e-12)
    assert math.isclose(m["lambda_away"], 1.5, rel_tol=1e-12)


def test_cards_rejects_bad_inputs():
    with pytest.raises(ValueError):
        cards_markets(-1.0, 2.0)
    with pytest.raises(ValueError):
        cards_markets(2.0, 2.0, referee_cpg=4.0, league_ref_avg=0.0)
