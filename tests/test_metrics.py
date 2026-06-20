import math

from jackpot.metrics import log_loss, brier_score, ranked_probability_score


# ---- log loss ----

def test_log_loss_perfect_and_confident():
    # certain & correct -> ~0
    assert math.isclose(log_loss([1.0, 0.0, 0.0], 0), 0.0, abs_tol=1e-9)
    # -log(0.5) for a half-right call
    assert math.isclose(log_loss([0.5, 0.25, 0.25], 0), -math.log(0.5), rel_tol=1e-9)


def test_log_loss_clips_zero_probability():
    # confident & wrong must be finite (clipped), not inf
    val = log_loss([0.0, 0.0, 1.0], 0)
    assert math.isfinite(val) and val > 0


# ---- brier ----

def test_brier_perfect_is_zero():
    assert math.isclose(brier_score([1.0, 0.0, 0.0], 0), 0.0, abs_tol=1e-12)


def test_brier_known_value():
    # outcome=home(0); one-hot [1,0,0]; probs [0.6,0.3,0.1]
    # (0.6-1)^2 + (0.3)^2 + (0.1)^2 = 0.16+0.09+0.01 = 0.26
    assert math.isclose(brier_score([0.6, 0.3, 0.1], 0), 0.26, rel_tol=1e-9)


# ---- RPS ----

def test_rps_perfect_is_zero():
    assert math.isclose(ranked_probability_score([1.0, 0.0, 0.0], 0), 0.0, abs_tol=1e-12)


def test_rps_known_value():
    # probs [0.5,0.3,0.2], outcome away(2)
    # cum pred: 0.5, 0.8, 1.0 ; cum obs: 0,0,1
    # (0.5)^2 + (0.8)^2 over (r-1)=2 = (0.25+0.64)/2 = 0.445
    assert math.isclose(ranked_probability_score([0.5, 0.3, 0.2], 2), 0.445, rel_tol=1e-9)


def test_rps_respects_ordering():
    # outcome is away(2). Mass wrongly on home is "further" than mass on draw,
    # so it should be penalised more by RPS (unlike Brier/log-loss).
    on_home = ranked_probability_score([0.7, 0.0, 0.3], 2)
    on_draw = ranked_probability_score([0.0, 0.7, 0.3], 2)
    assert on_home > on_draw


def test_metrics_validate_outcome_index():
    for fn in (log_loss, brier_score, ranked_probability_score):
        try:
            fn([0.5, 0.5], 5)
            assert False, "expected ValueError"
        except ValueError:
            pass
