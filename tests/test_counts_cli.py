from jackpot.counts import main, format_counts, secondary_markets, _DEFAULT_RATES


def test_format_counts_contains_blocks():
    out = secondary_markets(**_DEFAULT_RATES)
    rep = format_counts(out, "A", "B")
    assert "Corners" in rep and "Cards" in rep
    assert "total Over" in rep


def test_main_default(capsys):
    assert main(["A", "B"]) == 0
    out = capsys.readouterr().out
    assert "A vs B" in out and "Corners" in out


def test_main_with_referee(capsys):
    assert main(["A", "B", "--ref", "6.0"]) == 0
    assert "Cards" in capsys.readouterr().out


def test_main_bad_referee_returns_error():
    assert main(["A", "B", "--ref", "notnum"]) == 1
