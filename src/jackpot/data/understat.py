"""Live data provider backed by Understat (free xG for the top-5 leagues).

Understat embeds each league's team data in the page as
``teamsData = JSON.parse('<escaped json>')``. We extract and parse that. The pure
parsing function is unit-tested; the network fetch is best-effort at runtime.

Note: scraping Understat is fine for personal use but is **not** licensed for
commercial products — see the design spec.
"""
from __future__ import annotations

import json
import re
from typing import Dict, List

from .base import TeamForm, MatchContext, MatchData, MatchDataProvider

# our league label -> Understat's URL code
_LEAGUE_CODES: Dict[str, str] = {
    "EPL": "EPL",
    "La Liga": "La_liga",
    "Serie A": "Serie_A",
    "Bundesliga": "Bundesliga",
    "Ligue 1": "Ligue_1",
}

_TEAMS_DATA_RE = re.compile(r"teamsData\s*=\s*JSON\.parse\('(?P<json>.*?)'\)", re.DOTALL)


def understat_league_code(league: str) -> str:
    """Map a friendly league name to Understat's URL slug."""
    if league not in _LEAGUE_CODES:
        raise KeyError(f"league not supported by Understat provider: {league}")
    return _LEAGUE_CODES[league]


def parse_teams_data(html: str) -> Dict[str, Dict[str, float]]:
    """Extract per-team xG/xGA-per-game and match count from an Understat page.

    Returns ``{team_name: {scored_per_game, conceded_per_game, matches}}`` where
    scored/conceded are xG/xGA averages.
    """
    match = _TEAMS_DATA_RE.search(html)
    if not match:
        raise ValueError("teamsData payload not found in Understat HTML")
    # Understat hex-escapes the JSON string; unicode_escape reverses that.
    raw = match.group("json").encode("utf8").decode("unicode_escape")
    teams = json.loads(raw)

    out: Dict[str, Dict[str, float]] = {}
    for team in teams.values():
        history = team.get("history", [])
        n = len(history)
        if n == 0:
            continue
        xg = sum(float(h["xG"]) for h in history) / n
        xga = sum(float(h["xGA"]) for h in history) / n
        out[team["title"]] = {
            "scored_per_game": xg,
            "conceded_per_game": xga,
            "matches": n,
        }
    return out


class UnderstatProvider(MatchDataProvider):
    """Fetches live league xG from Understat and caches it per (league, season)."""

    def __init__(self, season: int = 2024):
        self.season = season
        self._cache: Dict[str, Dict[str, Dict[str, float]]] = {}

    def _load_league(self, league: str) -> Dict[str, Dict[str, float]]:
        if league in self._cache:
            return self._cache[league]
        import requests  # lazy import keeps the engine dependency-free

        code = understat_league_code(league)
        url = f"https://understat.com/league/{code}/{self.season}"
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        parsed = parse_teams_data(resp.text)
        self._cache[league] = parsed
        return parsed

    def list_teams(self, league: str) -> List[str]:
        return sorted(self._load_league(league).keys())

    def get_match(self, home_team: str, away_team: str, league: str) -> MatchData:
        teams = self._load_league(league)
        if home_team not in teams:
            raise KeyError(f"team not found in {league}: {home_team}")
        if away_team not in teams:
            raise KeyError(f"team not found in {league}: {away_team}")

        league_avg = sum(t["scored_per_game"] for t in teams.values()) / len(teams)

        def form(name: str) -> TeamForm:
            row = teams[name]
            return TeamForm(
                name=name,
                scored_per_game=row["scored_per_game"],
                conceded_per_game=row["conceded_per_game"],
                matches=int(row["matches"]),
                uses_xg=True,
            )

        return MatchData(
            home=form(home_team),
            away=form(away_team),
            context=MatchContext(league_avg_goals=league_avg),
        )
