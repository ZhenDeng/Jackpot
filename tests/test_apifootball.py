import math

import pytest

from jackpot.data.base import MatchData
from jackpot.data.apifootball import (
    api_football_league_id,
    parse_standings,
    compute_league_avg,
    ApiFootballProvider,
)


def _standings_json():
    # shape of GET /standings: response[0].league.standings[0] == list of entries
    def entry(tid, name, played, gf, ga):
        return {
            "rank": tid,
            "team": {"id": tid, "name": name},
            "all": {"played": played, "goals": {"for": gf, "against": ga}},
        }
    return {
        "response": [
            {
                "league": {
                    "id": 39,
                    "name": "Premier League",
                    "season": 2024,
                    "standings": [[
                        entry(50, "Manchester City", 20, 50, 18),
                        entry(42, "Arsenal", 20, 40, 20),
                        entry(35, "Burnley", 10, 8, 24),
                    ]],
                }
            }
        ]
    }


# ---- league id map ----

def test_league_ids():
    assert api_football_league_id("EPL") == 39
    assert api_football_league_id("La Liga") == 140
    assert api_football_league_id("Serie A") == 135
    assert api_football_league_id("Bundesliga") == 78
    assert api_football_league_id("Ligue 1") == 61
    assert api_football_league_id("World Cup") == 1


def test_league_id_unknown_raises():
    with pytest.raises(KeyError):
        api_football_league_id("MLS")


# ---- parse_standings ----

def test_parse_standings_per_game_rates():
    parsed = parse_standings(_standings_json())
    city = parsed["Manchester City"]
    assert city["matches"] == 20
    assert math.isclose(city["scored_per_game"], 50 / 20, rel_tol=1e-12)
    assert math.isclose(city["conceded_per_game"], 18 / 20, rel_tol=1e-12)


def test_parse_standings_handles_zero_played():
    j = _standings_json()
    j["response"][0]["league"]["standings"][0].append(
        {"team": {"id": 99, "name": "NewTeam"}, "all": {"played": 0, "goals": {"for": 0, "against": 0}}}
    )
    parsed = parse_standings(j)
    assert "NewTeam" not in parsed  # 0 games -> skipped (no rate)


def test_parse_standings_empty_response_raises():
    with pytest.raises(ValueError):
        parse_standings({"response": [], "errors": ["No data"]})


def test_parse_standings_skips_null_goals_without_crashing():
    j = _standings_json()
    grp = j["response"][0]["league"]["standings"][0]
    grp.append({"team": {"id": 71, "name": "NullGoals"}, "all": {"played": 5, "goals": None}})
    grp.append({"team": {"id": 72, "name": "NullFor"}, "all": {"played": 5, "goals": {"for": None, "against": 4}}})
    parsed = parse_standings(j)  # must not raise
    assert "NullGoals" not in parsed
    assert "NullFor" not in parsed
    assert "Manchester City" in parsed  # valid teams still parsed


def test_parse_standings_skips_row_missing_team():
    j = _standings_json()
    j["response"][0]["league"]["standings"][0].append(
        {"all": {"played": 5, "goals": {"for": 5, "against": 5}}}  # no "team"
    )
    parsed = parse_standings(j)  # must not raise KeyError
    assert len(parsed) == 3  # the three valid teams


# ---- league average ----

def test_compute_league_avg_match_weighted():
    parsed = parse_standings(_standings_json())
    # match-weighted: total goals for / total played
    expected = (50 + 40 + 8) / (20 + 20 + 10)
    assert math.isclose(compute_league_avg(parsed), expected, rel_tol=1e-9)


# ---- provider (no network: pre-populated cache) ----

def test_provider_get_match_from_cache():
    p = ApiFootballProvider(api_key="KEY", season=2024)
    p._cache["EPL"] = parse_standings(_standings_json())
    md = p.get_match("Manchester City", "Burnley", "EPL")
    assert isinstance(md, MatchData)
    assert md.home.name == "Manchester City"
    assert md.home.matches == 20
    assert md.away.name == "Burnley"
    assert md.context.league_avg_goals > 0
    assert md.home.uses_xg is False


def test_provider_list_teams_sorted():
    p = ApiFootballProvider(api_key="KEY")
    p._cache["EPL"] = parse_standings(_standings_json())
    assert p.list_teams("EPL") == ["Arsenal", "Burnley", "Manchester City"]


def test_provider_unknown_team_raises():
    p = ApiFootballProvider(api_key="KEY")
    p._cache["EPL"] = parse_standings(_standings_json())
    with pytest.raises(KeyError):
        p.get_match("Nonexistent", "Burnley", "EPL")


def test_provider_headers_carry_key_and_repr_masks_it():
    p = ApiFootballProvider(api_key="secret-key-123")
    assert p._request_headers()["x-apisports-key"] == "secret-key-123"
    assert "secret-key-123" not in repr(p)


def test_provider_requires_api_key():
    with pytest.raises(ValueError):
        ApiFootballProvider(api_key="")
