from jackpot.data.results import HistoricalMatch, load_results_csv


def test_historical_match_odds_default_none():
    m = HistoricalMatch("2025-08-09", "E0", "A", "B", 1, 0)
    assert m.home_odds is None and m.draw_odds is None and m.away_odds is None


def test_load_parses_b365_odds():
    csv_text = (
        "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,B365H,B365D,B365A\n"
        "E0,09/08/2025,Arsenal,Chelsea,2,1,1.80,3.60,4.50\n"
    )
    m = load_results_csv(csv_text)[0]
    assert m.home_odds == 1.80 and m.draw_odds == 3.60 and m.away_odds == 4.50


def test_load_falls_back_to_pinnacle_then_avg():
    ps = "Div,HomeTeam,AwayTeam,FTHG,FTAG,PSH,PSD,PSA\nE0,A,B,1,1,2.0,3.3,3.8\n"
    assert load_results_csv(ps)[0].home_odds == 2.0
    avg = "Div,HomeTeam,AwayTeam,FTHG,FTAG,AvgH,AvgD,AvgA\nE0,A,B,1,1,2.5,3.2,2.9\n"
    assert load_results_csv(avg)[0].draw_odds == 3.2


def test_load_without_odds_still_loads_result():
    csv_text = "Div,HomeTeam,AwayTeam,FTHG,FTAG\nE0,A,B,2,0\n"
    m = load_results_csv(csv_text)[0]
    assert m.home_goals == 2
    assert m.home_odds is None


def test_load_skips_invalid_odds_but_keeps_match():
    csv_text = (
        "Div,HomeTeam,AwayTeam,FTHG,FTAG,B365H,B365D,B365A\n"
        "E0,A,B,2,0,,,\n"          # blank odds -> no odds, but result kept
    )
    m = load_results_csv(csv_text)[0]
    assert m.home_goals == 2
    assert m.home_odds is None
