import math

from jackpot.matrix import build_score_matrix
from jackpot.markets import (
    match_result,
    over_under,
    btts,
    correct_score,
    double_chance,
    draw_no_bet,
)


def _m():
    return build_score_matrix(1.6, 1.2, max_goals=10)


def test_match_result_sums_to_one():
    r = match_result(_m())
    assert math.isclose(r["home"] + r["draw"] + r["away"], 1.0, abs_tol=1e-9)
    assert set(r) == {"home", "draw", "away"}


def test_match_result_favours_higher_lambda_side():
    r = match_result(build_score_matrix(2.2, 0.9, max_goals=10))
    assert r["home"] > r["away"]


def test_over_under_complements_to_one():
    ou = over_under(_m(), 2.5)
    assert math.isclose(ou["over"] + ou["under"], 1.0, abs_tol=1e-9)


def test_over_under_monotonic_in_line():
    m = _m()
    # higher line -> harder to go over -> lower over prob
    assert over_under(m, 3.5)["over"] < over_under(m, 1.5)["over"]


def test_over_line_is_strict_threshold():
    # a .5 line can't push; for an integer-ish check, Over 2.5 means total >= 3
    m = build_score_matrix(1.0, 1.0, max_goals=6)
    ou = over_under(m, 2.5)
    # manually: over = sum cells where h+a >= 3
    manual_over = sum(
        m[h][a] for h in range(len(m)) for a in range(len(m)) if h + a >= 3
    )
    assert math.isclose(ou["over"], manual_over, abs_tol=1e-12)


def test_btts_complements_to_one():
    b = btts(_m())
    assert math.isclose(b["yes"] + b["no"], 1.0, abs_tol=1e-9)


def test_btts_yes_is_both_scoring():
    m = _m()
    manual_yes = sum(
        m[h][a] for h in range(1, len(m)) for a in range(1, len(m))
    )
    assert math.isclose(btts(m)["yes"], manual_yes, abs_tol=1e-12)


def test_correct_score_top_n_sorted_desc():
    cs = correct_score(_m(), top_n=5)
    assert len(cs) == 5
    probs = [p for (_h, _a, p) in cs]
    assert probs == sorted(probs, reverse=True)


def test_double_chance_consistent_with_1x2():
    m = _m()
    r = match_result(m)
    dc = double_chance(m)
    assert math.isclose(dc["1X"], r["home"] + r["draw"], abs_tol=1e-9)
    assert math.isclose(dc["12"], r["home"] + r["away"], abs_tol=1e-9)
    assert math.isclose(dc["X2"], r["draw"] + r["away"], abs_tol=1e-9)


def test_draw_no_bet_renormalises_excluding_draw():
    m = _m()
    dnb = draw_no_bet(m)
    assert math.isclose(dnb["home"] + dnb["away"], 1.0, abs_tol=1e-9)
    r = match_result(m)
    # ratio home:away preserved after removing the draw
    assert math.isclose(dnb["home"] / dnb["away"], r["home"] / r["away"], rel_tol=1e-9)
