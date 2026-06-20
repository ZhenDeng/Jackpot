import math

from jackpot.matrix import build_score_matrix
from jackpot.markets import (
    match_result,
    team_total_goals,
    clean_sheet,
    win_to_nil,
    winning_margin,
)


def _m():
    return build_score_matrix(1.7, 1.1, max_goals=10)


def test_team_total_goals_complements_to_one_per_team():
    tt = team_total_goals(_m(), 1.5)
    for side in ("home", "away"):
        assert math.isclose(tt[side]["over"] + tt[side]["under"], 1.0, abs_tol=1e-9)


def test_team_total_over_05_equals_one_minus_p_zero():
    m = _m()
    tt = team_total_goals(m, 0.5)
    # home scores 0 == row 0 sum
    p_home_zero = sum(m[0][a] for a in range(len(m)))
    assert math.isclose(tt["home"]["over"], 1.0 - p_home_zero, abs_tol=1e-12)


def test_team_total_monotonic_in_line():
    m = _m()
    assert team_total_goals(m, 2.5)["home"]["over"] < team_total_goals(m, 0.5)["home"]["over"]


def test_higher_lambda_team_scores_more():
    m = build_score_matrix(2.4, 0.7, max_goals=10)
    tt = team_total_goals(m, 1.5)
    assert tt["home"]["over"] > tt["away"]["over"]


def test_clean_sheet_matches_opponent_zero():
    m = _m()
    cs = clean_sheet(m)
    p_away_zero = sum(m[h][0] for h in range(len(m)))   # away scores 0
    p_home_zero = sum(m[0][a] for a in range(len(m)))   # home scores 0
    assert math.isclose(cs["home"], p_away_zero, abs_tol=1e-12)
    assert math.isclose(cs["away"], p_home_zero, abs_tol=1e-12)


def test_win_to_nil_bounded_by_clean_sheet_and_win():
    m = _m()
    wtn = win_to_nil(m)
    cs = clean_sheet(m)
    mr = match_result(m)
    assert wtn["home"] <= cs["home"] + 1e-12
    assert wtn["home"] <= mr["home"] + 1e-12
    assert 0.0 <= wtn["home"] <= 1.0


def test_win_to_nil_formula():
    m = _m()
    manual_home = sum(m[h][0] for h in range(1, len(m)))  # home>=1, away=0
    assert math.isclose(win_to_nil(m)["home"], manual_home, abs_tol=1e-12)


def test_winning_margin_buckets_sum_to_one_and_draw_matches_1x2():
    m = _m()
    wm = winning_margin(m)
    assert math.isclose(sum(wm.values()), 1.0, abs_tol=1e-9)
    assert set(wm) == {"home_2plus", "home_1", "draw", "away_1", "away_2plus"}
    assert math.isclose(wm["draw"], match_result(m)["draw"], abs_tol=1e-12)
