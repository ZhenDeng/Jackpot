import math

from jackpot.data.results import HistoricalMatch, sample_season
from jackpot.backtest import run_backtest, tune, has_odds, main


def _season_with_odds():
    """The sample season with a (deterministic) bookmaker odds triple on each match."""
    out = []
    for m in sample_season():
        # crude odds: favour the side that actually scored more (well-calibrated-ish)
        if m.home_goals > m.away_goals:
            oh, od, oa = 1.7, 3.6, 5.0
        elif m.home_goals < m.away_goals:
            oh, od, oa = 5.0, 3.6, 1.7
        else:
            oh, od, oa = 2.8, 3.1, 2.8
        out.append(HistoricalMatch(
            m.date, m.league, m.home, m.away, m.home_goals, m.away_goals,
            home_odds=oh, draw_odds=od, away_odds=oa,
        ))
    return out


def test_has_odds():
    assert has_odds(_season_with_odds())
    assert not has_odds(sample_season())


def test_blend_weight_changes_rps_only_with_odds():
    season = _season_with_odds()
    pure_model = run_backtest(season, min_history=3, blend_weight=1.0).avg_rps
    pure_market = run_backtest(season, min_history=3, blend_weight=0.0).avg_rps
    assert not math.isclose(pure_model, pure_market, abs_tol=1e-9)  # blend engages

    # without odds, blend_weight has no effect
    plain = sample_season()
    a = run_backtest(plain, min_history=3, blend_weight=1.0).avg_rps
    b = run_backtest(plain, min_history=3, blend_weight=0.0).avg_rps
    assert math.isclose(a, b, abs_tol=1e-12)


def test_tune_includes_blend_and_sorts_by_rps():
    runs = tune(_season_with_odds(), {"blend_weight": [0.0, 0.5, 1.0]}, min_history=3)
    rps = [r["result"].avg_rps for r in runs]
    assert rps == sorted(rps)
    assert "blend_weight" in runs[0]["params"]


def test_cli_reports_best_blend_when_odds_present(capsys, tmp_path):
    csv = "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,B365H,B365D,B365A\n"
    for i, m in enumerate(_season_with_odds()):
        csv += f"E0,2025-08-{i+1:02d},{m.home},{m.away},{m.home_goals},{m.away_goals},{m.home_odds},{m.draw_odds},{m.away_odds}\n"
    p = tmp_path / "odds.csv"
    p.write_text(csv)
    assert main([str(p)]) == 0
    out = capsys.readouterr().out
    assert "odds: yes" in out
    assert "best model-vs-market blend weight" in out
