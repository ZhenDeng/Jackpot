import json
import math

from jackpot.data.understat import parse_teams_data, understat_league_code
from jackpot.data.weather import weather_adjustment


def _fake_understat_html():
    # Understat embeds team data as teamsData = JSON.parse('<json>')
    teams = {
        "1": {
            "id": "1",
            "title": "Team A",
            "history": [
                {"xG": 2.0, "xGA": 0.5},
                {"xG": 1.0, "xGA": 1.5},
            ],
        },
        "2": {
            "id": "2",
            "title": "Team B",
            "history": [
                {"xG": 0.5, "xGA": 2.0},
            ],
        },
    }
    payload = json.dumps(teams)
    return f"<script>var teamsData = JSON.parse('{payload}');</script>"


def test_parse_teams_data_aggregates_xg_per_game():
    parsed = parse_teams_data(_fake_understat_html())
    assert set(parsed.keys()) == {"Team A", "Team B"}
    a = parsed["Team A"]
    assert a["matches"] == 2
    assert math.isclose(a["scored_per_game"], 1.5, rel_tol=1e-9)   # (2.0+1.0)/2
    assert math.isclose(a["conceded_per_game"], 1.0, rel_tol=1e-9)  # (0.5+1.5)/2


def test_parse_teams_data_single_match_team():
    parsed = parse_teams_data(_fake_understat_html())
    b = parsed["Team B"]
    assert b["matches"] == 1
    assert math.isclose(b["scored_per_game"], 0.5, rel_tol=1e-9)


def test_parse_teams_data_missing_payload_raises():
    try:
        parse_teams_data("<html>no data here</html>")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_understat_league_code_maps_known_leagues():
    assert understat_league_code("EPL") == "EPL"
    assert understat_league_code("La Liga") == "La_liga"
    assert understat_league_code("Serie A") == "Serie_A"
    assert understat_league_code("Bundesliga") == "Bundesliga"
    assert understat_league_code("Ligue 1") == "Ligue_1"


def test_understat_league_code_unknown_raises():
    try:
        understat_league_code("MLS")
        assert False, "expected KeyError"
    except KeyError:
        pass


# ---- weather adjustment ----

def test_weather_neutral_in_good_conditions():
    assert math.isclose(weather_adjustment(wind_kph=5, rain_mm=0), 1.0, rel_tol=1e-9)


def test_weather_reduces_goals_in_strong_wind_and_rain():
    bad = weather_adjustment(wind_kph=45, rain_mm=10)
    assert bad < 1.0


def test_weather_adjustment_is_bounded():
    # even in extreme weather we never wipe out scoring entirely
    extreme = weather_adjustment(wind_kph=120, rain_mm=80)
    assert 0.8 <= extreme <= 1.0
