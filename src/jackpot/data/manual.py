"""Build a MatchData from user-entered numbers (no scraping required).

Manual entry powers the "try a real match today" flow: the user types each team's
recent form and the app feeds the exact same engine as the providers do.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .base import PlayerForm, TeamForm, MatchContext, MatchData


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def build_manual_match(
    home_name: str,
    home_scored: float,
    home_conceded: float,
    home_matches: int,
    away_name: str,
    away_scored: float,
    away_conceded: float,
    away_matches: int,
    league_avg: float,
    home_squad: Optional[List[PlayerForm]] = None,
    away_squad: Optional[List[PlayerForm]] = None,
    market_odds: Optional[Dict[str, float]] = None,
) -> MatchData:
    """Validate manual inputs and assemble a standard ``MatchData``."""
    _require(bool(home_name and home_name.strip()), "home_name must not be empty")
    _require(bool(away_name and away_name.strip()), "away_name must not be empty")
    _require(league_avg > 0, "league_avg must be positive")
    for label, value in (
        ("home_scored", home_scored), ("home_conceded", home_conceded),
        ("away_scored", away_scored), ("away_conceded", away_conceded),
    ):
        _require(value >= 0, f"{label} must be non-negative")
    _require(home_matches >= 1, "home_matches must be at least 1")
    _require(away_matches >= 1, "away_matches must be at least 1")

    home = TeamForm(
        name=home_name.strip(),
        scored_per_game=home_scored,
        conceded_per_game=home_conceded,
        matches=int(home_matches),
        uses_xg=True,
        squad=list(home_squad) if home_squad else None,
    )
    away = TeamForm(
        name=away_name.strip(),
        scored_per_game=away_scored,
        conceded_per_game=away_conceded,
        matches=int(away_matches),
        uses_xg=True,
        squad=list(away_squad) if away_squad else None,
    )
    return MatchData(
        home=home,
        away=away,
        context=MatchContext(league_avg_goals=league_avg, market_odds=market_odds),
    )
