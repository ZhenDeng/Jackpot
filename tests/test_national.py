import math

import pytest

from jackpot.national import (
    elo_to_lambdas,
    SAMPLE_ELO,
    lookup_elo,
    INTL_TOTAL_GOALS,
)


def test_equal_elo_neutral_is_symmetric():
    lh, la = elo_to_lambdas(1800, 1800, neutral=True)
    assert math.isclose(lh, la, rel_tol=1e-12)
    assert math.isclose(lh, INTL_TOTAL_GOALS / 2, rel_tol=1e-9)


def test_stronger_team_gets_higher_lambda():
    lh, la = elo_to_lambdas(2000, 1700, neutral=True)
    assert lh > la
    # supremacy grows with the gap
    lh2, la2 = elo_to_lambdas(2100, 1700, neutral=True)
    assert (lh2 - la2) > (lh - la)


def test_lambda_sum_preserves_total_when_floor_inactive():
    lh, la = elo_to_lambdas(1900, 1750, neutral=True)
    assert math.isclose(lh + la, INTL_TOTAL_GOALS, rel_tol=1e-9)


def test_non_neutral_adds_home_edge():
    neutral = elo_to_lambdas(1800, 1800, neutral=True)
    at_home = elo_to_lambdas(1800, 1800, neutral=False)
    assert at_home[0] > neutral[0]
    assert at_home[1] < neutral[1]


def test_floor_keeps_lambda_positive_on_huge_gap():
    lh, la = elo_to_lambdas(2300, 1200, neutral=True)
    assert la > 0          # underdog never goes to/below zero
    assert lh > la


def test_lookup_elo_known_and_unknown():
    assert lookup_elo("Brazil") == SAMPLE_ELO["Brazil"]
    with pytest.raises(KeyError):
        lookup_elo("Atlantis")


def test_sample_elo_has_plausible_values():
    # a handful of real WC nations present, ratings in a sane range
    for team in ("Brazil", "France", "Argentina"):
        assert team in SAMPLE_ELO
        assert 1500 < SAMPLE_ELO[team] < 2200
