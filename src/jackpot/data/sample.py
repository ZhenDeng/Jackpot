"""Offline, deterministic data provider.

Bundles a handful of teams across two leagues with realistic xG-style rates. Used
by the test suite and as a zero-setup demo for the Streamlit app, so the whole
thing runs with no network and no scraping.
"""
from __future__ import annotations

from typing import Dict, List

from .base import PlayerForm, TeamForm, MatchContext, MatchData, MatchDataProvider

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

# illustrative squads (xg_per90, expected_minutes, penalty_taker, xa_per90) for the demo
_SQUADS: Dict[str, List[PlayerForm]] = {
    "Manchester City": [
        PlayerForm("E. Haaland", 0.95, 88, penalty_taker=True, xa_per90=0.15),
        PlayerForm("P. Foden", 0.45, 82, xa_per90=0.30),
        PlayerForm("B. Silva", 0.30, 80, xa_per90=0.30),
        PlayerForm("J. Alvarez", 0.40, 55, xa_per90=0.20),
        PlayerForm("K. De Bruyne", 0.35, 70, xa_per90=0.55),
    ],
    "Burnley": [
        PlayerForm("L. Foster", 0.35, 80, penalty_taker=True, xa_per90=0.12),
        PlayerForm("J. Rodriguez", 0.25, 72, xa_per90=0.15),
        PlayerForm("W. Odobert", 0.20, 75, xa_per90=0.18),
        PlayerForm("D. Brownhill", 0.12, 85, xa_per90=0.20),
    ],
    "Arsenal": [
        PlayerForm("B. Saka", 0.50, 85, penalty_taker=True, xa_per90=0.35),
        PlayerForm("K. Havertz", 0.45, 80, xa_per90=0.20),
        PlayerForm("G. Martinelli", 0.40, 78, xa_per90=0.25),
        PlayerForm("M. Odegaard", 0.35, 82, xa_per90=0.40),
    ],
    "Real Madrid": [
        PlayerForm("J. Bellingham", 0.55, 85, penalty_taker=True, xa_per90=0.30),
        PlayerForm("Vinicius Jr", 0.55, 84, xa_per90=0.35),
        PlayerForm("Rodrygo", 0.40, 78, xa_per90=0.25),
        PlayerForm("F. Valverde", 0.25, 86, xa_per90=0.30),
    ],
}


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
            # copy so callers can't mutate the shared module-level squad list
            squad=list(_SQUADS[name]) if name in _SQUADS else None,
        )

    def get_match(self, home_team: str, away_team: str, league: str) -> MatchData:
        if league not in _LEAGUES:
            raise KeyError(f"unknown league: {league}")
        home = self._team_form(league, home_team)
        away = self._team_form(league, away_team)
        ctx = MatchContext(league_avg_goals=_LEAGUE_AVG.get(league, 1.4))
        return MatchData(home=home, away=away, context=ctx)
