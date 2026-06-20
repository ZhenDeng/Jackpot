import math

from jackpot.poisson import poisson_pmf, dixon_coles_tau


def test_poisson_pmf_known_values():
    # P(k=0; lam=2) = e^-2 ~= 0.1353
    assert math.isclose(poisson_pmf(0, 2.0), math.exp(-2.0), rel_tol=1e-9)
    # P(k=1; lam=2) = 2 e^-2
    assert math.isclose(poisson_pmf(1, 2.0), 2.0 * math.exp(-2.0), rel_tol=1e-9)
    # P(k=3; lam=1.5)
    assert math.isclose(poisson_pmf(3, 1.5), (1.5 ** 3) * math.exp(-1.5) / 6, rel_tol=1e-9)


def test_poisson_pmf_sums_to_one():
    lam = 1.7
    total = sum(poisson_pmf(k, lam) for k in range(0, 50))
    assert math.isclose(total, 1.0, abs_tol=1e-9)


def test_poisson_pmf_rejects_negative():
    try:
        poisson_pmf(-1, 1.0)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_dixon_coles_tau_only_adjusts_low_scores():
    rho = -0.05
    lh, la = 1.4, 1.1
    # cells outside {0,1}x{0,1} are unchanged
    assert dixon_coles_tau(2, 0, lh, la, rho) == 1.0
    assert dixon_coles_tau(0, 3, lh, la, rho) == 1.0
    assert dixon_coles_tau(2, 2, lh, la, rho) == 1.0


def test_dixon_coles_tau_low_score_formulas():
    rho = -0.05
    lh, la = 1.4, 1.1
    assert math.isclose(dixon_coles_tau(0, 0, lh, la, rho), 1 - lh * la * rho, rel_tol=1e-12)
    assert math.isclose(dixon_coles_tau(0, 1, lh, la, rho), 1 + lh * rho, rel_tol=1e-12)
    assert math.isclose(dixon_coles_tau(1, 0, lh, la, rho), 1 + la * rho, rel_tol=1e-12)
    assert math.isclose(dixon_coles_tau(1, 1, lh, la, rho), 1 - rho, rel_tol=1e-12)


def test_dixon_coles_tau_zero_rho_is_neutral():
    # rho=0 -> no adjustment anywhere
    for h in range(2):
        for a in range(2):
            assert dixon_coles_tau(h, a, 1.3, 1.0, 0.0) == 1.0
