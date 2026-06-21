import math

from jackpot.data.base import TeamForm, MatchContext, MatchData
from jackpot.data.sample import SampleDataProvider
from jackpot.predict import predict


def test_player_props_present_for_sample_match():
    md = SampleDataProvider().get_match("Manchester City", "Burnley", "EPL")
    out = predict(md)
    pp = out["markets"]["player_props"]
    assert "home" in pp and "away" in pp
    assert len(pp["home"]) >= 3
    # entries have the expected shape (involvement primary, scorer secondary)
    top = pp["home"][0]
    assert set(top) == {
        "player", "p_involve", "fair_odds_involve", "p_score", "p_2plus", "fair_odds"
    }
    assert 0.0 <= top["p_score"] <= 1.0
    assert 0.0 <= top["p_involve"] <= 1.0
    assert top["p_involve"] >= top["p_score"]          # score-or-assist >= score
    assert math.isclose(top["fair_odds"], 1.0 / top["p_score"], rel_tol=1e-9)
    assert math.isclose(top["fair_odds_involve"], 1.0 / top["p_involve"], rel_tol=1e-9)


def test_player_props_sorted_by_involvement_descending():
    md = SampleDataProvider().get_match("Manchester City", "Burnley", "EPL")
    pp = predict(md)["markets"]["player_props"]["home"]
    probs = [e["p_involve"] for e in pp]
    assert probs == sorted(probs, reverse=True)


def test_top_involvement_is_the_star():
    md = SampleDataProvider().get_match("Manchester City", "Burnley", "EPL")
    pp = predict(md)["markets"]["player_props"]["home"]
    # Haaland: highest xG/90 and the penalty taker -> most likely involved
    assert pp[0]["player"] == "E. Haaland"


def test_two_plus_less_than_anytime():
    md = SampleDataProvider().get_match("Manchester City", "Burnley", "EPL")
    for entry in predict(md)["markets"]["player_props"]["home"]:
        assert entry["p_2plus"] <= entry["p_score"]


def test_player_props_graceful_when_squad_absent():
    md = MatchData(
        home=TeamForm("A", 1.8, 1.0, 20, True, squad=None),
        away=TeamForm("B", 1.0, 1.8, 20, True, squad=None),
        context=MatchContext(league_avg_goals=1.45),
    )
    out = predict(md)  # must not raise
    pp = out["markets"]["player_props"]
    assert pp["home"] == []
    assert pp["away"] == []


def test_player_props_respects_top_n():
    md = SampleDataProvider().get_match("Manchester City", "Burnley", "EPL")
    pp = predict(md, player_props_top_n=2)["markets"]["player_props"]
    assert len(pp["home"]) == 2
