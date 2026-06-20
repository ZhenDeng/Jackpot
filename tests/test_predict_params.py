"""The tuning params exposed on predict() must actually change the output."""
from jackpot.data.base import TeamForm, MatchContext, MatchData
from jackpot.predict import predict


def _match():
    return MatchData(
        home=TeamForm("H", 1.6, 1.1, 20, True),
        away=TeamForm("A", 1.3, 1.2, 20, True),
        context=MatchContext(league_avg_goals=1.4),
    )


def test_home_adv_increases_home_win_prob():
    low = predict(_match(), home_adv=1.0)["markets"]["match_result"]["home"]["prob"]
    high = predict(_match(), home_adv=1.5)["markets"]["match_result"]["home"]["prob"]
    assert high > low


def test_rho_changes_low_score_draw_mass():
    base = predict(_match(), rho=0.0)["markets"]["match_result"]["draw"]["prob"]
    dc = predict(_match(), rho=-0.1)["markets"]["match_result"]["draw"]["prob"]
    assert dc != base


def test_shrink_k_pulls_predictions_toward_even():
    # a strong-vs-weak match; heavy shrinkage flattens the home edge
    strong = MatchData(
        home=TeamForm("H", 2.4, 0.7, 6, True),
        away=TeamForm("A", 0.8, 2.1, 6, True),
        context=MatchContext(league_avg_goals=1.4),
    )
    light = predict(strong, shrink_k=1.0)["markets"]["match_result"]["home"]["prob"]
    heavy = predict(strong, shrink_k=50.0)["markets"]["match_result"]["home"]["prob"]
    assert heavy < light  # more shrinkage -> less extreme favourite


def test_defaults_unchanged_when_params_omitted():
    a = predict(_match())["markets"]["match_result"]["home"]["prob"]
    b = predict(_match(), home_adv=1.3, rho=-0.05, shrink_k=5.0)["markets"]["match_result"]["home"]["prob"]
    assert abs(a - b) < 1e-12
