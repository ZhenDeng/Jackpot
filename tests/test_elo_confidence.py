from jackpot.national import elo_confidence, predict_international


def test_big_gap_is_high():
    assert elo_confidence(2100, 1800) == "High"   # 300 gap


def test_moderate_gap_is_medium():
    assert elo_confidence(1900, 1780) == "Medium"  # 120 gap


def test_even_match_is_low():
    assert elo_confidence(1850, 1840) == "Low"     # 10 gap


def test_symmetric():
    assert elo_confidence(1800, 2100) == elo_confidence(2100, 1800)


def test_predict_international_returns_real_confidence():
    out = predict_international("A", "B", 2100, 1800)
    assert out["confidence"] == "High"
    even = predict_international("A", "B", 1850, 1840)
    assert even["confidence"] == "Low"
    # bigger gap is at least as confident
    levels = {"Low": 0, "Medium": 1, "High": 2}
    assert levels[out["confidence"]] >= levels[even["confidence"]]
