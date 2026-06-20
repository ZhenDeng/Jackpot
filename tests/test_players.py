import math

from jackpot.players import (
    raw_output,
    p_score,
    p_two_plus,
    allocate_lambdas,
    PENALTY_FRACTION,
)


def test_raw_output_scales_with_minutes():
    assert math.isclose(raw_output(0.6, 90), 0.6, rel_tol=1e-9)
    assert math.isclose(raw_output(0.6, 45), 0.3, rel_tol=1e-9)
    assert raw_output(0.6, 0) == 0.0


def test_p_score_formula():
    assert math.isclose(p_score(0.0), 0.0, abs_tol=1e-12)
    assert math.isclose(p_score(0.5), 1 - math.exp(-0.5), rel_tol=1e-12)


def test_p_two_plus_formula():
    lam = 0.7
    assert math.isclose(p_two_plus(lam), 1 - math.exp(-lam) * (1 + lam), rel_tol=1e-12)
    # 2+ is always less likely than 1+
    assert p_two_plus(lam) < p_score(lam)


def test_allocate_conserves_team_lambda_without_penalty_taker():
    entries = [("A", 0.6, False), ("B", 0.4, False), ("C", 0.2, False)]
    lams = allocate_lambdas(entries, team_lambda=1.8)
    assert math.isclose(sum(lams.values()), 1.8, rel_tol=1e-9)


def test_allocate_conserves_team_lambda_with_penalty_taker():
    entries = [("A", 0.6, True), ("B", 0.4, False), ("C", 0.2, False)]
    lams = allocate_lambdas(entries, team_lambda=1.8)
    assert math.isclose(sum(lams.values()), 1.8, rel_tol=1e-9)


def test_penalty_taker_gets_boost_over_identical_non_taker():
    # two identical raws, one is the penalty taker -> taker has higher lambda
    entries = [("Taker", 0.5, True), ("Other", 0.5, False)]
    lams = allocate_lambdas(entries, team_lambda=2.0)
    assert lams["Taker"] > lams["Other"]
    # boost equals the penalty pool
    assert math.isclose(lams["Taker"] - lams["Other"], 2.0 * PENALTY_FRACTION, rel_tol=1e-9)


def test_higher_raw_gets_higher_lambda():
    entries = [("Star", 0.9, False), ("Sub", 0.1, False)]
    lams = allocate_lambdas(entries, team_lambda=1.5)
    assert lams["Star"] > lams["Sub"]


def test_allocate_zero_total_returns_empty():
    entries = [("A", 0.0, False), ("B", 0.0, False)]
    assert allocate_lambdas(entries, team_lambda=1.5) == {}


def test_allocate_aggregates_duplicate_names_preserving_conservation():
    # two entries share a name -> must not silently drop mass
    entries = [("Kane", 0.8, True), ("Kane", 0.7, False), ("Smith", 0.3, False)]
    lams = allocate_lambdas(entries, team_lambda=2.0)
    assert math.isclose(sum(lams.values()), 2.0, rel_tol=1e-9)
    # penalty flag is OR-ed across the merged entries, so the boost survives
    assert lams["Kane"] > lams["Smith"]


def test_allocate_rejects_bad_penalty_fraction():
    entries = [("A", 0.5, True), ("B", 0.5, False)]
    for bad in (-0.1, 1.5):
        try:
            allocate_lambdas(entries, team_lambda=2.0, penalty_fraction=bad)
            assert False, "expected ValueError"
        except ValueError:
            pass


def test_allocate_splits_penalty_pool_among_multiple_takers():
    entries = [("P1", 0.5, True), ("P2", 0.5, True)]
    lams = allocate_lambdas(entries, team_lambda=2.0)
    # conservation still holds; the two takers are symmetric
    assert math.isclose(sum(lams.values()), 2.0, rel_tol=1e-9)
    assert math.isclose(lams["P1"], lams["P2"], rel_tol=1e-9)
