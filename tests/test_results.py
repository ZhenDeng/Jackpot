from jackpot.data.results import HistoricalMatch, load_results_csv, sample_season


def test_load_results_csv_parses_football_data_format():
    csv_text = (
        "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG\n"
        "E0,09/08/2025,Arsenal,Chelsea,2,1\n"
        "E0,10/08/2025,Spurs,Everton,0,0\n"
    )
    matches = load_results_csv(csv_text)
    assert len(matches) == 2
    assert matches[0].home == "Arsenal" and matches[0].away == "Chelsea"
    assert matches[0].home_goals == 2 and matches[0].away_goals == 1
    assert isinstance(matches[0], HistoricalMatch)


def test_load_results_csv_skips_bad_rows():
    csv_text = (
        "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG\n"
        "E0,09/08/2025,Arsenal,Chelsea,2,1\n"
        "E0,10/08/2025,Spurs,Everton,,\n"          # missing goals -> skipped
        "E0,11/08/2025,OnlyHome\n"                  # malformed -> skipped
    )
    matches = load_results_csv(csv_text)
    assert len(matches) == 1


def test_sample_season_has_enough_matches_and_clear_strength():
    season = sample_season()
    assert len(season) >= 12
    # tally points; the designated strong team should top the table
    points = {}
    for mtch in season:
        for t in (mtch.home, mtch.away):
            points.setdefault(t, 0)
        if mtch.home_goals > mtch.away_goals:
            points[mtch.home] += 3
        elif mtch.home_goals < mtch.away_goals:
            points[mtch.away] += 3
        else:
            points[mtch.home] += 1
            points[mtch.away] += 1
    top = max(points, key=points.get)
    assert top == "Alpha"  # the strongest team in the sample


def test_sample_season_chronological():
    season = sample_season()
    dates = [m.date for m in season]
    assert dates == sorted(dates)
