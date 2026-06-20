import math

from jackpot.data.results import sample_season, HistoricalMatch
from jackpot.backtest import run_backtest, tune, outcome_index


def test_outcome_index():
    assert outcome_index(2, 0) == 0   # home win
    assert outcome_index(1, 1) == 1   # draw
    assert outcome_index(0, 3) == 2   # away win


def test_run_backtest_walk_forward_skips_early_matches():
    season = sample_season()
    res = run_backtest(season, min_history=3)
    # some early matches lack enough history -> not every match is scored
    assert 0 < res.n_scored < len(season)


def test_run_backtest_metrics_in_range():
    res = run_backtest(sample_season(), min_history=3)
    assert res.avg_rps >= 0
    assert res.avg_log_loss >= 0
    assert res.avg_brier >= 0
    assert 0.0 <= res.accuracy <= 1.0
    assert all(math.isfinite(v) for v in (res.avg_rps, res.avg_log_loss, res.avg_brier))


def test_model_beats_coin_flip_on_a_structured_season():
    # the sample season has a clear strength order; the model should do better
    # than uniform 1/3-each guessing (RPS of ~0.222 for 3 ordered outcomes)
    res = run_backtest(sample_season(), min_history=3)
    assert res.avg_rps < 0.222


def test_calibration_buckets_account_for_all_scored():
    res = run_backtest(sample_season(), min_history=3)
    assert sum(b["n"] for b in res.calibration) == res.n_scored


def test_no_leakage_a_match_result_does_not_inform_its_own_prediction():
    # if a single match could see its own result, a 10-0 thrashing would be
    # perfectly predicted. With walk-forward it is simply unscored (no history).
    one = [HistoricalMatch("2025-08-01", "X", "A", "B", 10, 0)]
    res = run_backtest(one, min_history=1)
    assert res.n_scored == 0


def test_tune_returns_runs_sorted_by_rps_and_best_is_not_worse_than_default():
    season = sample_season()
    grid = {"home_adv": [1.1, 1.3, 1.5], "rho": [-0.1, -0.05]}
    runs = tune(season, grid, min_history=3)
    rps_values = [r["result"].avg_rps for r in runs]
    assert rps_values == sorted(rps_values)            # ascending (best first)
    default = run_backtest(season, min_history=3).avg_rps
    assert runs[0]["result"].avg_rps <= default + 1e-9  # best tuned <= default
