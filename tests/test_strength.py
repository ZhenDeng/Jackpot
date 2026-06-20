import math

from jackpot.strength import (
    TeamRates,
    estimate_strength,
    decay_weight,
    weighted_mean,
)
from jackpot.lambdas import compute_lambdas


# ---- strength ----

def test_league_average_team_has_unit_strength():
    rates = TeamRates(scored_per_game=1.5, conceded_per_game=1.5, matches=20, uses_xg=True)
    att, dfn = estimate_strength(rates, league_avg=1.5)
    assert math.isclose(att, 1.0, abs_tol=1e-6)
    assert math.isclose(dfn, 1.0, abs_tol=1e-6)


def test_strong_attack_above_one():
    rates = TeamRates(scored_per_game=2.4, conceded_per_game=1.0, matches=20, uses_xg=True)
    att, dfn = estimate_strength(rates, league_avg=1.5)
    assert att > 1.0   # scores more than average
    assert dfn < 1.0   # concedes less than average


def test_shrinkage_pulls_small_samples_toward_one():
    strong = TeamRates(scored_per_game=3.0, conceded_per_game=1.5, matches=2, uses_xg=True)
    same_strong_big = TeamRates(scored_per_game=3.0, conceded_per_game=1.5, matches=30, uses_xg=True)
    att_small, _ = estimate_strength(strong, league_avg=1.5, shrink_k=5)
    att_big, _ = estimate_strength(same_strong_big, league_avg=1.5, shrink_k=5)
    # small-sample attack is closer to 1.0 than the large-sample one
    assert abs(att_small - 1.0) < abs(att_big - 1.0)


def test_decay_weight_half_life():
    assert math.isclose(decay_weight(0, half_life_days=180), 1.0, rel_tol=1e-9)
    assert math.isclose(decay_weight(180, half_life_days=180), 0.5, rel_tol=1e-9)
    assert decay_weight(360, half_life_days=180) < 0.3


def test_weighted_mean():
    # recent value 2.0 (weight 1), old value 0.0 (weight 0.5) -> biased toward 2.0
    wm = weighted_mean([(2.0, 1.0), (0.0, 0.5)])
    assert math.isclose(wm, 2.0 / 1.5, rel_tol=1e-9)


# ---- lambdas ----

def test_home_advantage_raises_home_lambda():
    lh, la = compute_lambdas(
        home_attack=1.0, home_defense=1.0,
        away_attack=1.0, away_defense=1.0,
        league_avg=1.4, home_adv=1.3,
    )
    assert lh > la
    assert math.isclose(lh, 1.4 * 1.3, rel_tol=1e-9)
    assert math.isclose(la, 1.4, rel_tol=1e-9)


def test_stronger_home_attack_raises_home_lambda():
    base = compute_lambdas(1.0, 1.0, 1.0, 1.0, league_avg=1.4)
    strong = compute_lambdas(1.5, 1.0, 1.0, 1.0, league_avg=1.4)
    assert strong[0] > base[0]


def test_adjustments_multiply_lambda():
    base = compute_lambdas(1.0, 1.0, 1.0, 1.0, league_avg=1.4, home_adv=1.0)
    rainy = compute_lambdas(
        1.0, 1.0, 1.0, 1.0, league_avg=1.4, home_adv=1.0,
        home_adjust=0.9, away_adjust=0.9,
    )
    assert rainy[0] < base[0]
    assert rainy[1] < base[1]
    assert math.isclose(rainy[0], base[0] * 0.9, rel_tol=1e-9)


def test_lambdas_reject_negative():
    try:
        compute_lambdas(-1.0, 1.0, 1.0, 1.0, league_avg=1.4)
        assert False, "expected ValueError"
    except ValueError:
        pass
