import math

from jackpot.odds import (
    fair_odds,
    implied_prob,
    strip_overround,
    blend,
    is_value,
    confidence_level,
)


def test_fair_odds_is_reciprocal():
    assert math.isclose(fair_odds(0.25), 4.0, rel_tol=1e-9)
    assert math.isclose(fair_odds(0.5), 2.0, rel_tol=1e-9)


def test_fair_odds_zero_prob_is_infinite():
    assert fair_odds(0.0) == float("inf")


def test_implied_prob_is_reciprocal():
    assert math.isclose(implied_prob(4.0), 0.25, rel_tol=1e-9)


def test_strip_overround_normalises_to_one():
    # bookmaker 1X2 odds with built-in margin
    probs = strip_overround({"home": 2.0, "draw": 3.5, "away": 4.0})
    assert math.isclose(sum(probs.values()), 1.0, abs_tol=1e-9)
    # favourite stays the most likely
    assert probs["home"] > probs["draw"]
    assert probs["home"] > probs["away"]


def test_strip_overround_removes_margin():
    # these raw implied probs sum to >1 (the overround); after stripping == 1
    raw_sum = implied_prob(2.0) + implied_prob(3.5) + implied_prob(4.0)
    assert raw_sum > 1.0
    probs = strip_overround({"home": 2.0, "draw": 3.5, "away": 4.0})
    assert math.isclose(sum(probs.values()), 1.0, abs_tol=1e-9)


def test_blend_weights():
    assert math.isclose(blend(0.6, 0.4, 0.5), 0.5, rel_tol=1e-9)
    assert math.isclose(blend(0.6, 0.4, 1.0), 0.6, rel_tol=1e-9)  # all model
    assert math.isclose(blend(0.6, 0.4, 0.0), 0.4, rel_tol=1e-9)  # all market


def test_blend_rejects_bad_weight():
    for w in (-0.1, 1.1):
        try:
            blend(0.5, 0.5, w)
            assert False, "expected ValueError"
        except ValueError:
            pass


def test_is_value_when_model_beats_market_by_threshold():
    # model 55% vs market-implied 45% -> value
    assert is_value(0.55, 0.45, threshold=0.05) is True
    # only 2 points better, below 5-point threshold -> no value
    assert is_value(0.47, 0.45, threshold=0.05) is False
    # model worse than market -> no value
    assert is_value(0.40, 0.45, threshold=0.05) is False


def test_confidence_levels():
    assert confidence_level(matches=12, has_xg=True) == "High"
    assert confidence_level(matches=6, has_xg=True) == "Medium"
    assert confidence_level(matches=6, has_xg=False) == "Low"
    assert confidence_level(matches=2, has_xg=True) == "Low"
