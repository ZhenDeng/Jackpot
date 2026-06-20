import json
import math

import pytest

from jackpot.data.base import PlayerForm
from jackpot.data.understat import parse_players_data


def _html(players):
    payload = json.dumps(players)
    return f"<script>var playersData = JSON.parse('{payload}');</script>"


def test_parse_players_data_groups_by_team_and_computes_per90():
    players = [
        {"player_name": "Striker", "team_title": "Team A", "games": "10", "time": "900", "xG": "9.0"},
        {"player_name": "Mid", "team_title": "Team A", "games": "10", "time": "450", "xG": "1.5"},
        {"player_name": "Other", "team_title": "Team B", "games": "8", "time": "720", "xG": "2.0"},
    ]
    squads = parse_players_data(_html(players))
    assert set(squads.keys()) == {"Team A", "Team B"}
    a = {p.name: p for p in squads["Team A"]}
    # Striker: 9.0 xG over 900 min = 10 nineties -> 0.9 xG/90
    assert math.isclose(a["Striker"].xg_per90, 0.9, rel_tol=1e-9)
    # expected minutes = time/games = 900/10 = 90
    assert math.isclose(a["Striker"].expected_minutes, 90.0, rel_tol=1e-9)
    assert isinstance(a["Striker"], PlayerForm)


def test_parse_players_data_sorts_by_xg_and_skips_zero_minutes():
    players = [
        {"player_name": "Benchwarmer", "team_title": "T", "games": "0", "time": "0", "xG": "0"},
        {"player_name": "Low", "team_title": "T", "games": "10", "time": "900", "xG": "1.0"},
        {"player_name": "High", "team_title": "T", "games": "10", "time": "900", "xG": "8.0"},
    ]
    squads = parse_players_data(_html(players))
    names = [p.name for p in squads["T"]]
    assert "Benchwarmer" not in names          # zero minutes skipped
    assert names[0] == "High"                   # sorted by xG/90 desc


def test_parse_players_data_missing_payload_raises():
    with pytest.raises(ValueError):
        parse_players_data("<html>nothing</html>")
