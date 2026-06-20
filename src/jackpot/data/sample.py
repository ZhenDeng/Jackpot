"""Offline, deterministic data provider.

Bundles a handful of teams across two leagues with realistic xG-style rates. Used
by the test suite and as a zero-setup demo for the Streamlit app, so the whole
thing runs with no network and no scraping.
"""
from __future__ import annotations

from typing import Dict, List

from .base import TeamForm, MatchContext, MatchData, MatchDataProvider

# scored/conceded are season xG-per-game style figures (illustrative, not live)
_LEAGUES: Dict[str, Dict[str, Dict[str, float]]] = {
    "EPL": {
        "Manchester City": {"scored": 2.4, "conceded": 0.9, "matches": 24},
        "Arsenal": {"scored": 2.0, "conceded": 0.9, "matches": 24},
        "Liverpool": {"scored": 2.1, "conceded": 1.1, "matches": 24},
        "Manchester United": {"scored": 1.5, "conceded": 1.4, "matches": 24},
        "Burnley": {"scored": 0.9, "conceded": 2.1, "matches": 24},
        "Sheffield United": {"scored": 0.8, "conceded": 2.3, "matches": 24},
    },
    "La Liga": {
        "Real Madrid": {"scored": 2.2, "conceded": 0.8, "matches": 24},
        "Barcelona": {"scored": 2.1, "conceded": 1.0, "matches": 24},
        "Girona": {"scored": 1.9, "conceded": 1.2, "matches": 24},
        "Almeria": {"scored": 1.0, "conceded": 2.2, "matches": 24},
    },
}

# rough league average goals per team per game
_LEAGUE_AVG: Dict[str, float] = {"EPL": 1.45, "La Liga": 1.35}


class SampleDataProvider(MatchDataProvider):
    def list_teams(self, league: str) -> List[str]:
        if league not in _LEAGUES:
            raise KeyError(f"unknown league: {league}")
        return sorted(_LEAGUES[league].keys())

    def list_leagues(self) -> List[str]:
        return sorted(_LEAGUES.keys())

    def _team_form(self, league: str, name: str) -> TeamForm:
        teams = _LEAGUES[league]
        if name not in teams:
            raise KeyError(f"unknown team in {league}: {name}")
        row = teams[name]
        return TeamForm(
            name=name,
            scored_per_game=row["scored"],
            conceded_per_game=row["conceded"],
            matches=int(row["matches"]),
            uses_xg=True,
        )

    def get_match(self, home_team: str, away_team: str, league: str) -> MatchData:
        if league not in _LEAGUES:
            raise KeyError(f"unknown league: {league}")
        home = self._team_form(league, home_team)
        away = self._team_form(league, away_team)
        ctx = MatchContext(league_avg_goals=_LEAGUE_AVG.get(league, 1.4))
        return MatchData(home=home, away=away, context=ctx)
