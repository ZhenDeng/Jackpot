import pytest

from jackpot.data.base import MatchData, PlayerForm
from jackpot.data.manual import build_manual_match, rows_to_squad, safe_float
from jackpot.predict import predict


def _valid(**over):
    args = dict(
        home_name="Home FC", home_scored=1.9, home_conceded=1.0, home_matches=20,
        away_name="Away FC", away_scored=1.0, away_conceded=1.8, away_matches=20,
        league_avg=1.45,
    )
    args.update(over)
    return build_manual_match(**args)


def test_builds_match_data():
    md = _valid()
    assert isinstance(md, MatchData)
    assert md.home.name == "Home FC"
    assert md.away.name == "Away FC"
    assert md.context.league_avg_goals == 1.45
    assert md.home.uses_xg is True


def test_prediction_runs_and_has_all_markets():
    out = predict(_valid())
    for key in ("match_result", "over_under", "btts", "team_total_goals", "player_props"):
        assert key in out["markets"]


def test_stronger_home_is_favourite():
    out = predict(_valid())
    mr = out["markets"]["match_result"]
    assert mr["home"]["prob"] > mr["away"]["prob"]


def test_squads_passed_through_populate_player_props():
    home_squad = [
        PlayerForm("Star", 0.8, 88, penalty_taker=True),
        PlayerForm("Mid", 0.3, 80),
    ]
    out = predict(_valid(home_squad=home_squad))
    pp = out["markets"]["player_props"]
    assert len(pp["home"]) == 2
    assert pp["away"] == []          # no away squad -> graceful empty
    assert pp["home"][0]["player"] == "Star"


def test_market_odds_passed_through_enable_value():
    md = _valid(market_odds={"home": 3.0, "draw": 3.4, "away": 2.3})
    out = predict(md)
    # model loves home; market makes it an underdog -> value flag
    assert out["markets"]["match_result"]["home"]["value"] is True


@pytest.mark.parametrize("bad", [
    {"home_name": ""},
    {"home_scored": -1.0},
    {"away_conceded": -0.5},
    {"home_matches": 0},
    {"league_avg": 0.0},
    {"league_avg": -1.0},
])
def test_validation_rejects_bad_inputs(bad):
    with pytest.raises(ValueError):
        _valid(**bad)


def test_rejects_identical_team_names():
    with pytest.raises(ValueError):
        _valid(home_name="Arsenal", away_name="Arsenal")
    # whitespace-only difference is still the same team
    with pytest.raises(ValueError):
        _valid(home_name="Arsenal", away_name="Arsenal ")


def test_rejects_both_teams_zero_attack():
    with pytest.raises(ValueError):
        _valid(home_scored=0.0, away_scored=0.0)
    # one team at zero is allowed (a real, if extreme, fixture)
    assert _valid(home_scored=0.0, away_scored=1.2) is not None


# ---- safe_float ----

def test_safe_float_keeps_zero_but_defaults_blanks():
    assert safe_float("", 90.0) == 90.0       # blank -> default
    assert safe_float(None, 90.0) == 90.0      # absent -> default
    assert safe_float(0.0, 90.0) == 0.0        # explicit zero is preserved
    assert safe_float("0.5", 90.0) == 0.5      # numeric string parses
    assert safe_float(" 0.7 ", 90.0) == 0.7    # trailing space tolerated
    assert safe_float("abc", 90.0) == 90.0     # garbage -> default (no crash)


# ---- rows_to_squad ----

def test_rows_to_squad_coerces_and_skips_blanks():
    rows = [
        {"Player": "Star", "xG/90": "0.8", "Minutes": "88", "Penalty": True},
        {"Player": "", "xG/90": "0.4", "Minutes": "80", "Penalty": False},   # blank name skipped
        {"Player": "Sub", "xG/90": "abc", "Minutes": "", "Penalty": False},  # bad values -> safe defaults
    ]
    squad = rows_to_squad(rows)
    names = [p.name for p in squad]
    assert names == ["Star", "Sub"]
    star = squad[0]
    assert isinstance(star, PlayerForm) and star.penalty_taker is True
    sub = squad[1]
    assert sub.xg_per90 == 0.0 and sub.expected_minutes == 90.0  # safe defaults, no crash


def test_rows_to_squad_empty_returns_none():
    assert rows_to_squad([]) is None
    assert rows_to_squad([{"Player": "", "xG/90": "0.5"}]) is None
