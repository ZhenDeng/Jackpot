import math

from jackpot.data.base import PlayerForm
from jackpot.national import predict_international


def _out(**kw):
    args = dict(home="Brazil", away="Ghana", elo_home=2030, elo_away=1640)
    args.update(kw)
    return predict_international(**args)


def test_returns_all_core_markets():
    m = _out()["markets"]
    for key in (
        "match_result", "over_under", "btts", "correct_score",
        "double_chance", "draw_no_bet",
        "team_total_goals", "clean_sheet", "win_to_nil", "winning_margin",
        "player_props",
    ):
        assert key in m


def test_match_result_sums_to_one_and_favours_stronger():
    out = _out()
    mr = out["markets"]["match_result"]
    assert math.isclose(mr["home"]["prob"] + mr["draw"]["prob"] + mr["away"]["prob"], 1.0, abs_tol=1e-9)
    assert mr["home"]["prob"] > mr["away"]["prob"]  # Brazil >> Ghana
    assert out["lambda_home"] > out["lambda_away"]


def test_fair_odds_is_reciprocal():
    rec = _out()["markets"]["match_result"]["home"]
    assert math.isclose(rec["fair_odds"], 1.0 / rec["prob"], rel_tol=1e-9)


def test_player_props_from_squads():
    home_squad = [
        PlayerForm("Striker", 0.8, 85, penalty_taker=True),
        PlayerForm("Winger", 0.4, 80),
    ]
    out = _out(home_squad=home_squad)
    pp = out["markets"]["player_props"]
    assert len(pp["home"]) == 2
    assert pp["away"] == []                       # no away squad -> graceful
    assert pp["home"][0]["player"] == "Striker"


def test_market_odds_enable_value_flag():
    # market makes Brazil a heavy favourite but underprices vs the model? use odds
    # where model prob (high) beats market-implied -> value
    out = _out(market_odds={"home": 2.5, "draw": 3.4, "away": 2.8})
    assert out["markets"]["match_result"]["home"]["value"] is True


def test_team_props_consistent():
    wm = _out()["markets"]["winning_margin"]
    assert math.isclose(sum(v["prob"] for v in wm.values()), 1.0, abs_tol=1e-9)
