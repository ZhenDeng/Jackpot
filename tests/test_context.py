import math

from jackpot.context import rest_factor, compute_adjustments, ADJUST_FLOOR, ADJUST_CEIL


# ---- rest_factor ----

def test_full_rest_is_neutral():
    assert rest_factor(None) == 1.0
    assert rest_factor(7) == 1.0
    assert rest_factor(4) == 1.0


def test_short_rest_penalises():
    assert rest_factor(1) < rest_factor(3) < 1.0
    assert math.isclose(rest_factor(1), 0.92, abs_tol=0.01)


def test_rest_factor_never_below_floor():
    assert rest_factor(0) >= 0.90


# ---- compute_adjustments ----

def test_all_defaults_are_neutral():
    assert compute_adjustments() == (1.0, 1.0)


def test_weather_scales_both_sides():
    h, a = compute_adjustments(weather_mult=0.9)
    assert math.isclose(h, 0.9, rel_tol=1e-9)
    assert math.isclose(a, 0.9, rel_tol=1e-9)


def test_attacker_out_lowers_own_side_only():
    h, a = compute_adjustments(home_attacker_out=True)
    assert h < 1.0
    assert a == 1.0


def test_defender_out_raises_the_opponent():
    # home's key defender out -> away scores more (away_adjust up), home unchanged
    h, a = compute_adjustments(home_defender_out=True)
    assert a > 1.0
    assert h == 1.0


def test_short_rest_penalises_that_side():
    h, a = compute_adjustments(home_rest=1)
    assert h < 1.0
    assert a == 1.0


def test_combined_factors_stack_then_clamp():
    # many negatives stacked must clamp at the floor, never below
    h, a = compute_adjustments(
        weather_mult=0.8, home_rest=0, home_attacker_out=True, away_defender_out=True
    )
    assert ADJUST_FLOOR <= h <= ADJUST_CEIL
    assert h <= 0.8  # at least as low as weather alone


def test_result_is_clamped_to_range():
    # an extreme weather boost (hypothetical >1) plus defender-out stays within ceiling
    h, a = compute_adjustments(weather_mult=1.5, away_defender_out=True)
    assert h <= ADJUST_CEIL
