import math

import pytest

from jackpot.national import elo_to_lambdas, predict_international, LAMBDA_FLOOR, INTL_TOTAL_GOALS


# HIGH 1 — total goals must be conserved even when the floor clamps the underdog
def test_floor_preserves_total_goals_on_big_gap():
    lh, la = elo_to_lambdas(2300, 1200, neutral=True)   # huge mismatch
    assert math.isclose(la, LAMBDA_FLOOR, rel_tol=1e-9)  # underdog at the floor
    assert math.isclose(lh + la, INTL_TOTAL_GOALS, rel_tol=1e-9)  # total conserved
    assert lh > la


def test_total_conserved_across_a_range_of_gaps():
    for eh, ea in [(1800, 1800), (1900, 1750), (2090, 1700), (2300, 1100)]:
        lh, la = elo_to_lambdas(eh, ea)
        assert lh + la <= INTL_TOTAL_GOALS + 1e-9   # never inflates above baseline


# HIGH 2 — bad market_odds keys must raise a clear error, not KeyError-crash
def test_market_odds_wrong_keys_raises_valueerror():
    with pytest.raises(ValueError):
        predict_international("A", "B", 2000, 1700, market_odds={"1": 2.1, "X": 3.3, "2": 3.5})


def test_market_odds_missing_key_raises_valueerror():
    with pytest.raises(ValueError):
        predict_international("A", "B", 2000, 1700, market_odds={"home": 2.0, "away": 3.0})


# MEDIUM — value flag must compare the RAW model prob to the market, not the blend
def test_value_uses_raw_model_even_when_blended_to_market():
    # strong favourite by Elo; market underprices home. Even at blend_weight=0
    # (output = pure market), the value flag should reflect the model's edge.
    out = predict_international(
        "Strong", "Weak", 2100, 1600,
        market_odds={"home": 2.2, "draw": 3.4, "away": 3.2},
        blend_weight=0.0,
    )
    assert out["markets"]["match_result"]["home"]["value"] is True
