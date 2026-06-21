"""Data-layer contracts: the dataclasses the engine consumes and the provider ABC.

The engine and UI depend only on these types and on ``MatchDataProvider`` — never
on a concrete data source. Adding or swapping a data source later means writing
one new provider, nothing else changes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class PlayerForm:
    """A single player's scoring inputs for the goalscorer model."""

    name: str
    xg_per90: float
    expected_minutes: float = 90.0
    penalty_taker: bool = False
    xa_per90: float = 0.0          # expected assists / 90 (drives "score or assist")


@dataclass
class TeamForm:
    """A team's recent attacking/defending output, as fed to the strength model."""

    name: str
    scored_per_game: float
    conceded_per_game: float
    matches: int
    uses_xg: bool = False
    squad: Optional[List["PlayerForm"]] = None


@dataclass
class MatchContext:
    """Everything about the fixture that isn't a single team's form."""

    league_avg_goals: float
    home_adjust: float = 1.0          # weather/rest multipliers on home lambda
    away_adjust: float = 1.0
    market_odds: Optional[Dict[str, float]] = None  # {"home","draw","away"} decimal


@dataclass
class MatchData:
    """A fully-resolved match ready for prediction."""

    home: TeamForm
    away: TeamForm
    context: MatchContext


class MatchDataProvider(ABC):
    """Source of match data. Concrete providers: Sample (offline), API-Football (live)."""

    @abstractmethod
    def list_teams(self, league: str) -> List[str]:
        """Team names available in a league."""

    @abstractmethod
    def get_match(self, home_team: str, away_team: str, league: str) -> MatchData:
        """Resolve a fixture into a ``MatchData`` for the engine."""
