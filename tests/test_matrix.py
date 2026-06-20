import math

from jackpot.matrix import build_score_matrix
from jackpot.poisson import poisson_pmf


def _total(m):
    return sum(sum(row) for row in m)


def test_matrix_dimensions():
    m = build_score_matrix(1.5, 1.2, max_goals=8)
    assert len(m) == 9
    assert all(len(row) == 9 for row in m)


def test_matrix_sums_to_one():
    m = build_score_matrix(1.7, 1.3, rho=-0.05, max_goals=10)
    assert math.isclose(_total(m), 1.0, abs_tol=1e-9)


def test_matrix_zero_rho_matches_independent_poisson():
    lh, la = 1.4, 1.1
    m = build_score_matrix(lh, la, rho=0.0, max_goals=12)
    # with rho=0 and full normalisation, cell ~ independent poisson product
    expected_00 = poisson_pmf(0, lh) * poisson_pmf(0, la)
    # normalisation over a 13x13 grid is ~1, so close to raw product
    assert math.isclose(m[0][0], expected_00, rel_tol=1e-3)


def test_dixon_coles_raises_low_score_draws():
    lh, la = 1.5, 1.3
    plain = build_score_matrix(lh, la, rho=0.0, max_goals=12)
    dc = build_score_matrix(lh, la, rho=-0.08, max_goals=12)
    # negative rho pushes probability into 0-0 and 1-1
    assert dc[0][0] > plain[0][0]
    assert dc[1][1] > plain[1][1]


def test_higher_home_lambda_shifts_mass_to_home():
    even = build_score_matrix(1.3, 1.3, max_goals=10)
    home = build_score_matrix(2.1, 1.0, max_goals=10)

    def p_home_win(m):
        return sum(m[h][a] for h in range(len(m)) for a in range(len(m)) if h > a)

    assert p_home_win(home) > p_home_win(even)


def test_matrix_rejects_bad_lambda():
    try:
        build_score_matrix(-1.0, 1.0)
        assert False, "expected ValueError"
    except ValueError:
        pass
