from jackpot.backtest import run_backtest, format_report, main
from jackpot.data.results import sample_season


def test_format_report_contains_key_metrics():
    rep = format_report(run_backtest(sample_season(), min_history=3), "X")
    for token in ("avg RPS", "avg log-loss", "accuracy", "calibration"):
        assert token in rep


def test_main_runs_on_bundled_season(capsys):
    code = main([])
    assert code == 0
    out = capsys.readouterr().out
    assert "Default weights" in out
    assert "Best tuned weights" in out
    assert "best params" in out
