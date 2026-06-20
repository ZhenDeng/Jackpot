"""Historical match results: a data type, a CSV loader, and a bundled sample season.

Feeds the walk-forward backtest. Real data can be loaded from football-data.co.uk
CSVs; the bundled sample season keeps the harness runnable offline and in tests.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import List


@dataclass
class HistoricalMatch:
    date: str          # ISO or dd/mm/yyyy; only used for chronological ordering
    league: str
    home: str
    away: str
    home_goals: int
    away_goals: int


def load_results_csv(text: str) -> List[HistoricalMatch]:
    """Parse the football-data.co.uk CSV format into HistoricalMatches.

    Expects columns ``HomeTeam, AwayTeam, FTHG, FTAG`` (+ optional ``Div, Date``).
    Rows with missing/non-integer goals or missing teams are skipped.
    """
    out: List[HistoricalMatch] = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            out.append(
                HistoricalMatch(
                    date=row.get("Date", ""),
                    league=row.get("Div", ""),
                    home=row["HomeTeam"],
                    away=row["AwayTeam"],
                    home_goals=int(row["FTHG"]),
                    away_goals=int(row["FTAG"]),
                )
            )
        except (KeyError, ValueError, TypeError):
            continue
    return out


# team -> attacking strength (1.0 strong ... 0.0 weak); used to synthesise a
# deterministic, leakage-free sample season with a clear true ordering.
_SAMPLE_STRENGTH = {"Alpha": 1.0, "Bravo": 0.66, "Charlie": 0.33, "Delta": 0.0}


def _score(att: float, opp: float, home_bonus: float) -> int:
    """Deterministic goal count from a strength gap (no randomness)."""
    return max(0, round(1.2 + 1.6 * (att - opp) + home_bonus))


def sample_season(rounds: int = 2) -> List[HistoricalMatch]:
    """A deterministic double round-robin among four teams of clear, fixed strength.

    Strong teams beat weak teams (so a walk-forward model should learn the order),
    with home advantage baked in. Dates increment so the list is chronological.
    """
    teams = list(_SAMPLE_STRENGTH)
    matches: List[HistoricalMatch] = []
    day = 1
    for _ in range(rounds):
        for i, home in enumerate(teams):
            for j, away in enumerate(teams):
                if i == j:
                    continue
                hg = _score(_SAMPLE_STRENGTH[home], _SAMPLE_STRENGTH[away], 0.4)
                ag = _score(_SAMPLE_STRENGTH[away], _SAMPLE_STRENGTH[home], 0.0)
                matches.append(
                    HistoricalMatch(
                        date=f"2025-08-{day:02d}",
                        league="SAMPLE",
                        home=home,
                        away=away,
                        home_goals=hg,
                        away_goals=ag,
                    )
                )
                day += 1
    return matches
