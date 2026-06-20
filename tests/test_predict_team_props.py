import math

from jackpot.data.sample import SampleDataProvider
from jackpot.predict import predict


def _out():
    md = SampleDataProvider().get_match("Manchester City", "Burnley", "EPL")
    return predict(md)


def test_predict_includes_team_prop_markets():
    m = _out()["markets"]
    for key in ("team_total_goals", "clean_sheet", "win_to_nil", "winning_margin"):
        assert key in m


def test_team_total_goals_records_shape():
    ttg = _out()["markets"]["team_total_goals"]
    assert set(ttg.keys()) == {"0.5", "1.5", "2.5"}
    rec = ttg["1.5"]["home"]["over"]
    assert set(rec) == {"prob", "fair_odds", "value"}
    assert math.isclose(rec["fair_odds"], 1.0 / rec["prob"], rel_tol=1e-9)


def test_clean_sheet_and_win_to_nil_have_both_sides():
    m = _out()["markets"]
    assert set(m["clean_sheet"]) == {"home", "away"}
    assert set(m["win_to_nil"]) == {"home", "away"}
    # City (strong) keeps a clean sheet vs Burnley more often than vice versa
    assert m["clean_sheet"]["home"]["prob"] > m["clean_sheet"]["away"]["prob"]


def test_winning_margin_buckets_sum_to_one():
    wm = _out()["markets"]["winning_margin"]
    total = sum(v["prob"] for v in wm.values())
    assert math.isclose(total, 1.0, abs_tol=1e-9)
