import math

from jackpot.national import predict_international


def _home_prob(**kw):
    out = predict_international("A", "B", 1850, 1780, **kw)
    return out["markets"]["match_result"]["home"]["prob"], out["lambda_home"], out["lambda_away"]


def test_home_adjust_raises_home_prob_and_lambda():
    base_p, base_lh, _ = _home_prob()
    up_p, up_lh, _ = _home_prob(home_adjust=1.2)
    assert up_lh > base_lh
    assert up_p > base_p


def test_away_adjust_raises_away_lambda():
    _, _, base_la = _home_prob()
    _, _, up_la = _home_prob(away_adjust=1.2)
    assert up_la > base_la


def test_defaults_unchanged_when_omitted():
    a = _home_prob()
    b = _home_prob(home_adjust=1.0, away_adjust=1.0)
    assert math.isclose(a[0], b[0], abs_tol=1e-12)
    assert math.isclose(a[1], b[1], abs_tol=1e-12)
