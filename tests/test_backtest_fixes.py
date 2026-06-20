"""Regression tests for backtest review findings."""
from jackpot.backtest import run_backtest, format_report
from jackpot.data.results import (
    HistoricalMatch,
    load_results_csv,
    sample_season,
    normalize_date,
)


# HIGH 1 — chronological order must be enforced regardless of input order
def test_run_backtest_sorts_input_by_date():
    season = sample_season()
    forward = run_backtest(season, min_history=3)
    shuffled = run_backtest(list(reversed(season)), min_history=3)
    assert shuffled.n_scored == forward.n_scored
    assert abs(shuffled.avg_rps - forward.avg_rps) < 1e-12


def test_normalize_date_handles_ddmmyyyy_and_iso():
    assert normalize_date("09/08/2025") == "2025-08-09"
    assert normalize_date("2025-08-09") == "2025-08-09"


# HIGH 2 — a goalless opening must not silently suppress all later predictions
def test_goalless_start_still_scores_via_league_prior():
    # eight 0-0 matches among two teams -> league_avg from goals stays 0,
    # but the harness should fall back to a prior and still score once history exists
    season = [
        HistoricalMatch(f"2025-08-{i+1:02d}", "X", "A", "B", 0, 0) for i in range(8)
    ]
    res = run_backtest(season, min_history=2)
    assert res.n_scored > 0


# MEDIUM — empty team names must be skipped by the loader
def test_load_results_csv_skips_empty_team_names():
    csv_text = (
        "HomeTeam,AwayTeam,FTHG,FTAG\n"
        "Arsenal,Chelsea,2,1\n"
        ",Chelsea,1,0\n"           # empty home
        "Arsenal,,0,0\n"           # empty away
    )
    assert len(load_results_csv(csv_text)) == 1


# MEDIUM — sample_season must produce valid, parseable dates for more rounds
def test_sample_season_dates_valid_for_three_rounds():
    for m in sample_season(rounds=3):
        # normalize_date round-trips a valid ISO date unchanged
        assert normalize_date(m.date) == m.date


# MEDIUM — empty calibration buckets report None, not a misleading 0.00
def test_empty_calibration_bucket_is_none():
    res = run_backtest(sample_season(), min_history=3)
    empty = [b for b in res.calibration if b["n"] == 0]
    assert empty, "expected at least one empty bucket in the sample season"
    assert all(b["mean_pred"] is None and b["actual_freq"] is None for b in empty)
    # and the report renders them without crashing
    assert isinstance(format_report(res), str)
