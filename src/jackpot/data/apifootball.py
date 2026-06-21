"""API-Football (api-sports.io) provider — official, ToS-clean live data.

One ``/standings`` call per league returns every team's games played and goals
for/against, which powers both the team list and per-team form — minimal requests,
friendly to the free 100/day tier. Team form is goals-based (``uses_xg=False``);
the strength model's shrinkage handles that. xG/players/odds are documented
follow-ups.
"""
from __future__ import annotations

from typing import Dict, List

from .base import TeamForm, MatchContext, MatchData, MatchDataProvider

API_BASE = "https://v3.football.api-sports.io"

# friendly league name -> API-Football league id (stable v3 ids)
_LEAGUE_IDS: Dict[str, int] = {
    "EPL": 39,
    "La Liga": 140,
    "Serie A": 135,
    "Bundesliga": 78,
    "Ligue 1": 61,
    "World Cup": 1,
}


def api_football_league_id(league: str) -> int:
    """Map a friendly league name to its API-Football id."""
    if league not in _LEAGUE_IDS:
        raise KeyError(f"league not supported by API-Football provider: {league}")
    return _LEAGUE_IDS[league]


def parse_standings(payload: Dict) -> Dict[str, Dict[str, float]]:
    """Extract per-team goals-based form from a ``/standings`` response.

    Returns ``{team_name: {scored_per_game, conceded_per_game, matches}}``. Teams
    with zero games played are skipped (no defined rate). Raises ValueError when the
    response is empty (API-Football reports quota/parameter problems that way).
    """
    response = payload.get("response") or []
    if not response:
        errors = payload.get("errors")
        raise ValueError(
            "empty API-Football standings response — the league/season may be "
            "off-season, a knockout tournament without a table, or outside your "
            f"plan's coverage (errors: {errors})"
        )

    league = response[0].get("league", {})
    groups = league.get("standings") or []

    out: Dict[str, Dict[str, float]] = {}
    for group in groups:                      # standings is a list of groups
        for row in group:
            allp = row.get("all") or {}
            played = float(allp.get("played", 0) or 0)
            if played <= 0:
                continue
            # API-Football returns null goals/team for pre-season or bracket rows
            name = (row.get("team") or {}).get("name")
            goals = allp.get("goals") or {}
            gf, ga = goals.get("for"), goals.get("against")
            if not name or gf is None or ga is None:
                continue  # incomplete row — skip rather than crash or invent data
            out[name] = {
                "scored_per_game": float(gf) / played,
                "conceded_per_game": float(ga) / played,
                "matches": int(played),
            }
    if not out:
        raise ValueError("no teams with games played in standings response")
    return out


def compute_league_avg(parsed: Dict[str, Dict[str, float]]) -> float:
    """Match-weighted league average goals per team per game."""
    total_matches = sum(t["matches"] for t in parsed.values())
    if total_matches <= 0:
        raise ValueError("no matches to compute league average")
    return sum(t["scored_per_game"] * t["matches"] for t in parsed.values()) / total_matches


class ApiFootballProvider(MatchDataProvider):
    """Live provider backed by API-Football's ``/standings`` endpoint."""

    def __init__(self, api_key: str, season: int = 2024):
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self.season = season
        self._cache: Dict[str, Dict[str, Dict[str, float]]] = {}

    def __repr__(self) -> str:
        # never echo the API key in logs / tracebacks
        return f"ApiFootballProvider(season={self.season}, api_key=***)"

    def _request_headers(self) -> Dict[str, str]:
        return {"x-apisports-key": self.api_key}

    def _load_league(self, league: str) -> Dict[str, Dict[str, float]]:
        if league in self._cache:
            return self._cache[league]
        import requests  # lazy import keeps the engine dependency-free

        league_id = api_football_league_id(league)
        resp = requests.get(
            f"{API_BASE}/standings",
            params={"league": league_id, "season": self.season},
            headers=self._request_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        try:
            parsed = parse_standings(resp.json())
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError(f"unexpected API-Football response for {league!r}: {exc}") from exc
        self._cache[league] = parsed
        return parsed

    def list_teams(self, league: str) -> List[str]:
        return sorted(self._load_league(league).keys())

    def get_match(self, home_team: str, away_team: str, league: str) -> MatchData:
        teams = self._load_league(league)
        for name in (home_team, away_team):
            if name not in teams:
                raise KeyError(f"team not found in {league}: {name}")
        league_avg = compute_league_avg(teams)

        def form(name: str) -> TeamForm:
            row = teams[name]
            return TeamForm(
                name=name,
                scored_per_game=row["scored_per_game"],
                conceded_per_game=row["conceded_per_game"],
                matches=int(row["matches"]),
                uses_xg=False,
            )

        return MatchData(
            home=form(home_team),
            away=form(away_team),
            context=MatchContext(league_avg_goals=league_avg),
        )
