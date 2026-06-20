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

from .base import PlayerForm, TeamForm, MatchContext, MatchData, MatchDataProvider

# our league label -> Understat's URL code
_LEAGUE_CODES: Dict[str, str] = {
    "EPL": "EPL",
    "La Liga": "La_liga",
    "Serie A": "Serie_A",
    "Bundesliga": "Bundesliga",
    "Ligue 1": "Ligue_1",
}

_TEAMS_DATA_RE = re.compile(r"teamsData\s*=\s*JSON\.parse\('(?P<json>.*?)'\)", re.DOTALL)
_PLAYERS_DATA_RE = re.compile(r"playersData\s*=\s*JSON\.parse\('(?P<json>.*?)'\)", re.DOTALL)
_SQUAD_SIZE = 8
_MIN_MINUTES = 90.0  # require ~one full match before trusting a per-90 rate


def understat_league_code(league: str) -> str:
    """Map a friendly league name to Understat's URL slug."""
    if league not in _LEAGUE_CODES:
        raise KeyError(f"league not supported by Understat provider: {league}")
    return _LEAGUE_CODES[league]


def _unescape_understat(payload: str) -> str:
    """Reverse Understat's hex-escaping of a UTF-8 JSON string.

    Understat embeds the JSON with ``\\xNN`` byte escapes. The correct round-trip
    is: interpret the escapes to recover the raw bytes, then decode them as UTF-8 —
    otherwise multi-byte names (Alavés, Saint-Étienne) become mojibake. Falls back
    to the naive decode if the strict round-trip fails.
    """
    try:
        return (
            payload.encode("utf-8")
            .decode("unicode_escape")
            .encode("latin-1")
            .decode("utf-8")
        )
    except (UnicodeDecodeError, UnicodeEncodeError):
        return payload.encode("utf-8").decode("unicode_escape")


def compute_league_avg(teams: Dict[str, Dict[str, float]]) -> float:
    """Match-weighted league average goals/xG per team per game.

    A flat mean of per-team rates over-weights teams that have played fewer games
    (common mid-season), biasing every lambda. Weighting by ``matches`` fixes it.
    """
    total_matches = sum(t["matches"] for t in teams.values())
    if total_matches <= 0:
        raise ValueError("no matches available to compute league average")
    return sum(t["scored_per_game"] * t["matches"] for t in teams.values()) / total_matches


def parse_teams_data(html: str) -> Dict[str, Dict[str, float]]:
    """Extract per-team xG/xGA-per-game and match count from an Understat page.

    Returns ``{team_name: {scored_per_game, conceded_per_game, matches}}`` where
    scored/conceded are xG/xGA averages.
    """
    match = _TEAMS_DATA_RE.search(html)
    if not match:
        raise ValueError("teamsData payload not found in Understat HTML")
    teams = json.loads(_unescape_understat(match.group("json")))

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


def parse_players_data(html: str) -> Dict[str, List[PlayerForm]]:
    """Extract per-team squads (xG/90, avg minutes) from Understat ``playersData``.

    Returns ``{team_title: [PlayerForm, ...]}`` sorted by xG/90 descending, keeping
    the top scorers. Penalty taker isn't in this feed, so it defaults to False.
    """
    match = _PLAYERS_DATA_RE.search(html)
    if not match:
        raise ValueError("playersData payload not found in Understat HTML")
    players = json.loads(_unescape_understat(match.group("json")))

    squads: Dict[str, List[PlayerForm]] = {}
    for p in players:
        try:
            minutes = float(p.get("time", 0) or 0)
            if minutes < _MIN_MINUTES:
                continue  # too few minutes for a trustworthy per-90 rate
            games = float(p.get("games", 0) or 0) or 1.0
            xg = float(p.get("xG", 0) or 0)
            squads.setdefault(p["team_title"], []).append(
                PlayerForm(
                    name=p["player_name"],
                    xg_per90=xg / (minutes / 90.0),
                    expected_minutes=min(90.0, minutes / games),
                    penalty_taker=False,
                )
            )
        except (KeyError, ValueError, TypeError):
            continue  # one malformed record must not discard the rest

    # Rank by expected per-game contribution (raw_output), which is what the
    # allocation engine actually uses — not the raw per-90 rate, which a
    # short-minutes player can inflate.
    for team in squads:
        squads[team].sort(
            key=lambda pf: pf.xg_per90 * pf.expected_minutes / 90.0, reverse=True
        )
        squads[team] = squads[team][:_SQUAD_SIZE]
    return squads


class UnderstatProvider(MatchDataProvider):
    """Fetches live league xG from Understat and caches it per (league, season)."""

    def __init__(self, season: int = 2024):
        self.season = season
        self._cache: Dict[str, Dict[str, Dict[str, float]]] = {}
        self._squads: Dict[str, Dict[str, List[PlayerForm]]] = {}

    def _load_league(self, league: str) -> Dict[str, Dict[str, float]]:
        if league in self._cache:
            return self._cache[league]
        import requests  # lazy import keeps the engine dependency-free

        code = understat_league_code(league)
        url = f"https://understat.com/league/{code}/{self.season}"
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        parsed = parse_teams_data(resp.text)
        try:
            self._squads[league] = parse_players_data(resp.text)
        except (ValueError, KeyError):
            self._squads[league] = {}  # squads are optional; props degrade gracefully
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

        league_avg = compute_league_avg(teams)
        squads = self._squads.get(league, {})

        def form(name: str) -> TeamForm:
            row = teams[name]
            return TeamForm(
                name=name,
                scored_per_game=row["scored_per_game"],
                conceded_per_game=row["conceded_per_game"],
                matches=int(row["matches"]),
                uses_xg=True,
                squad=squads.get(name),
            )

        return MatchData(
            home=form(home_team),
            away=form(away_team),
            context=MatchContext(league_avg_goals=league_avg),
        )
