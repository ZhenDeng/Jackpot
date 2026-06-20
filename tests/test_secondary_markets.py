import math

from jackpot.counts import secondary_markets


def _out(**kw):
    args = dict(
        home_corner_for=6.2, home_corner_against=4.1,
        away_corner_for=4.6, away_corner_against=5.3,
        home_card_rate=1.9, away_card_rate=2.2,
    )
    args.update(kw)
    return secondary_markets(**args)


def test_returns_corners_and_cards():
    out = _out()
    assert set(out) == {"corners", "cards"}
    for block in out.values():
        assert "total" in block and "home" in block and "away" in block
        assert "lambda_total" in block


def test_leaves_have_prob_and_fair_odds():
    out = _out()
    rec = out["corners"]["total"]["9.5"]["over"]
    assert set(rec) == {"prob", "fair_odds"}
    assert math.isclose(rec["fair_odds"], 1.0 / rec["prob"], rel_tol=1e-9)


def test_over_under_still_complements():
    leg = _out()["cards"]["total"]["4.5"]
    assert math.isclose(leg["over"]["prob"] + leg["under"]["prob"], 1.0, abs_tol=1e-9)


def test_referee_passthrough_scales_cards():
    lenient = _out(referee_cpg=3.0)["cards"]["lambda_total"]
    strict = _out(referee_cpg=6.0)["cards"]["lambda_total"]
    assert strict > lenient
