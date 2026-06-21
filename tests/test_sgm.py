import math

import pytest

from jackpot.predict import predict
from jackpot.sgm import same_game_multi
from jackpot.data.sample import SampleDataProvider


def _markets():
    """A minimal markets dict shaped like predict()['markets'] with known probs.

    Probabilities are chosen so the per-dimension winners are unambiguous:
    Result 0.78 > away goals 0.74 > match goals 0.70 > BTTS 0.66 > home goals 0.55.
    """
    return {
        "double_chance": {
            "1X": {"prob": 0.78}, "12": {"prob": 0.60}, "X2": {"prob": 0.55},
        },
        "over_under": {
            "1.5": {"over": {"prob": 0.70}, "under": {"prob": 0.30}},
            "2.5": {"over": {"prob": 0.45}, "under": {"prob": 0.55}},
            "3.5": {"over": {"prob": 0.20}, "under": {"prob": 0.80}},  # nested w/ 1.5
        },
        "btts": {"yes": {"prob": 0.66}, "no": {"prob": 0.34}},
        "team_total_goals": {
            "0.5": {
                "home": {"over": {"prob": 0.55}, "under": {"prob": 0.45}},
                "away": {"over": {"prob": 0.74}, "under": {"prob": 0.26}},
            },
            "1.5": {
                "home": {"over": {"prob": 0.30}, "under": {"prob": 0.70}},
                "away": {"over": {"prob": 0.40}, "under": {"prob": 0.60}},
            },
        },
    }


def test_returns_legs_and_combined():
    sgm = same_game_multi(_markets(), "Home", "Away", n=4)
    assert set(sgm) == {"legs", "combined_prob", "combined_fair_odds"}
    assert len(sgm["legs"]) == 4
    for leg in sgm["legs"]:
        assert set(leg) == {"market", "selection", "prob", "fair_odds"}
        assert math.isclose(leg["fair_odds"], 1.0 / leg["prob"], rel_tol=1e-9)


def test_picks_highest_confidence_legs_in_order():
    sgm = same_game_multi(_markets(), "Home", "Away", n=4)
    probs = [leg["prob"] for leg in sgm["legs"]]
    assert probs == sorted(probs, reverse=True)
    # Per-dimension winners: match goals 0.80 (Under 3.5), result 0.78,
    # away goals 0.74, home goals 0.70, BTTS 0.66 -> top four:
    assert probs == [0.80, 0.78, 0.74, 0.70]


def test_one_leg_per_dimension_no_nested_duplicates():
    # The 3.5 Under (0.80) is the most probable single over/under selection, but
    # match goals contributes only ONE leg, so we must not see two O/U legs.
    sgm = same_game_multi(_markets(), "Home", "Away", n=4)
    markets_used = [leg["market"] for leg in sgm["legs"]]
    assert len(markets_used) == len(set(markets_used))


def test_combined_prob_is_product_of_legs():
    sgm = same_game_multi(_markets(), "Home", "Away", n=4)
    expected = math.prod(leg["prob"] for leg in sgm["legs"])
    assert math.isclose(sgm["combined_prob"], expected, rel_tol=1e-9)
    assert math.isclose(sgm["combined_fair_odds"], 1.0 / expected, rel_tol=1e-9)


def test_n_caps_at_available_dimensions():
    sgm = same_game_multi(_markets(), "Home", "Away", n=99)
    # five distinct dimensions are available
    assert len(sgm["legs"]) == 5


def test_rejects_non_positive_n():
    with pytest.raises(ValueError):
        same_game_multi(_markets(), "Home", "Away", n=0)


def test_works_on_real_prediction_output():
    provider = SampleDataProvider()
    league = provider.list_leagues()[0]
    teams = provider.list_teams(league)
    match = provider.get_match(teams[0], teams[1], league)
    out = predict(match)
    sgm = same_game_multi(out["markets"], out["home_team"], out["away_team"], n=4)
    assert len(sgm["legs"]) == 4
    assert 0.0 < sgm["combined_prob"] <= 1.0
    # combining four sub-1.0 probabilities must shorten the combined chance
    assert sgm["combined_prob"] < min(leg["prob"] for leg in sgm["legs"])
