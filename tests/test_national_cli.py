from jackpot.national import main, format_international, predict_international


def test_format_international_contains_key_lines():
    rep = format_international(predict_international("Brazil", "Ghana", 2030, 1640))
    assert "expected goals" in rep
    assert "Brazil win" in rep
    assert "Over 2.5" in rep


def test_main_with_sample_elo(capsys):
    code = main(["Brazil", "Croatia"])
    assert code == 0
    out = capsys.readouterr().out
    assert "Brazil" in out and "Croatia" in out


def test_main_with_explicit_elo(capsys):
    code = main(["TeamA", "TeamB", "2000", "1700"])
    assert code == 0
    assert "TeamA" in capsys.readouterr().out


def test_main_unknown_team_returns_error(capsys):
    code = main(["Atlantis", "Wakanda"])
    assert code == 1


def test_main_usage_on_too_few_args():
    assert main(["OnlyOne"]) == 2
