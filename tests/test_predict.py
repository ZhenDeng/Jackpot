import math

import pytest

from jackpot.data.base import TeamForm, MatchContext, MatchData
from jackpot.data.sample import SampleDataProvider
from jackpot.predict import predict


# ---- sample provider ----

def test_sample_provider_lists_teams():
    p = SampleDataProvider()
    teams = p.list_teams("EPL")
    assert "Manchester City" in teams
    assert len(teams) >= 2


def test_sample_provider_returns_match_data():
    p = SampleDataProvider()
    md = p.get_match("Manchester City", "Burnley", "EPL")
    assert isinstance(md, MatchData)
    assert md.home.name == "Manchester City"
    assert md.away.name == "Burnley"
    assert md.context.league_avg_goals > 0


def test_sample_provider_unknown_team_raises():
    p = SampleDataProvider()
    with pytest.raises(KeyError):
        p.get_match("Nonexistent FC", "Burnley", "EPL")


# ---- prediction orchestration ----

def _match():
    strong = TeamForm("Strong", scored_per_game=2.3, conceded_per_game=0.8, matches=20, uses_xg=True)
    weak = TeamForm("Weak", scored_per_game=0.9, conceded_per_game=2.0, matches=20, uses_xg=True)
    return MatchData(home=strong, away=weak, context=MatchContext(league_avg_goals=1.45))


def test_predict_returns_all_markets():
    out = predict(_match())
    assert out["lambda_home"] > 0 and out["lambda_away"] > 0
    markets = out["markets"]
    for key in ("match_result", "over_under", "btts", "correct_score", "double_chance", "draw_no_bet"):
        assert key in markets


def test_predict_match_result_probabilities_sum_to_one():
    out = predict(_match())
    mr = out["markets"]["match_result"]
    total = mr["home"]["prob"] + mr["draw"]["prob"] + mr["away"]["prob"]
    assert math.isclose(total, 1.0, abs_tol=1e-9)


def test_predict_strong_home_is_favourite():
    out = predict(_match())
    mr = out["markets"]["match_result"]
    assert mr["home"]["prob"] > mr["away"]["prob"]
    # fair odds is reciprocal of prob
    assert math.isclose(mr["home"]["fair_odds"], 1.0 / mr["home"]["prob"], rel_tol=1e-9)


def test_predict_over_under_has_requested_lines():
    out = predict(_match(), over_under_lines=(1.5, 2.5, 3.5))
    ou = out["markets"]["over_under"]
    assert set(ou.keys()) == {"1.5", "2.5", "3.5"}
    assert math.isclose(ou["2.5"]["over"]["prob"] + ou["2.5"]["under"]["prob"], 1.0, abs_tol=1e-9)


def test_predict_confidence_reflects_data():
    thin = MatchData(
        home=TeamForm("A", 1.5, 1.5, matches=2, uses_xg=False),
        away=TeamForm("B", 1.5, 1.5, matches=2, uses_xg=False),
        context=MatchContext(league_avg_goals=1.5),
    )
    assert predict(thin)["confidence"] == "Low"


def test_predict_flags_value_against_market_odds():
    # market makes home an underdog (high odds), but model loves the home side
    md = _match()
    md = MatchData(
        home=md.home, away=md.away,
        context=MatchContext(
            league_avg_goals=1.45,
            market_odds={"home": 3.0, "draw": 3.4, "away": 2.3},
        ),
    )
    out = predict(md)
    mr = out["markets"]["match_result"]
    # model home prob (~0.7) >> market-implied home prob (~0.33) -> value flag
    assert mr["home"]["value"] is True
    assert mr["away"]["value"] is False


def test_predict_blend_moves_toward_market():
    md = MatchData(
        home=TeamForm("A", 2.3, 0.8, 20, True),
        away=TeamForm("B", 0.9, 2.0, 20, True),
        context=MatchContext(
            league_avg_goals=1.45,
            market_odds={"home": 3.0, "draw": 3.4, "away": 2.3},
        ),
    )
    pure = predict(md, blend_weight=1.0)["markets"]["match_result"]["home"]["prob"]
    blended = predict(md, blend_weight=0.5)["markets"]["match_result"]["home"]["prob"]
    # market thinks home is weaker, so blending lowers the home prob
    assert blended < pure
