"""Historical match results: a data type, a CSV loader, and a bundled sample season.

Feeds the walk-forward backtest. Real data can be loaded from football-data.co.uk
CSVs; the bundled sample season keeps the harness runnable offline and in tests.
"""
from __future__ import annotations

import csv
import datetime
import io
from dataclasses import dataclass
from typing import List, Optional


def normalize_date(s: str) -> str:
    """Return a sortable ISO date string, accepting dd/mm/yyyy or ISO input.

    Unrecognised formats are returned unchanged (so sorting degrades gracefully
    rather than raising).
    """
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return s


@dataclass
class HistoricalMatch:
    date: str          # ISO or dd/mm/yyyy; only used for chronological ordering
    league: str
    home: str
    away: str
    home_goals: int
    away_goals: int
    home_odds: Optional[float] = None   # decimal odds (margin not stripped)
    draw_odds: Optional[float] = None
    away_odds: Optional[float] = None


# bookmaker odds column triples to try, in preference order
_ODDS_COLUMNS = (
    ("B365H", "B365D", "B365A"),   # Bet365
    ("PSH", "PSD", "PSA"),         # Pinnacle
    ("AvgH", "AvgD", "AvgA"),      # market average
)


def _parse_odds(row: dict):
    """Return (home, draw, away) decimal odds from the first complete triple, or Nones."""
    for h, d, a in _ODDS_COLUMNS:
        try:
            oh, od, oa = float(row[h]), float(row[d]), float(row[a])
            if oh > 1 and od > 1 and oa > 1:
                return oh, od, oa
        except (KeyError, ValueError, TypeError):
            continue
    return None, None, None


def load_results_csv(text: str) -> List[HistoricalMatch]:
    """Parse the football-data.co.uk CSV format into HistoricalMatches.

    Expects columns ``HomeTeam, AwayTeam, FTHG, FTAG`` (+ optional ``Div, Date``).
    Rows with missing/non-integer goals or missing teams are skipped.
    """
    out: List[HistoricalMatch] = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            home, away = row["HomeTeam"].strip(), row["AwayTeam"].strip()
            if not home or not away:
                continue  # phantom-team guard
            oh, od, oa = _parse_odds(row)
            out.append(
                HistoricalMatch(
                    date=normalize_date(row.get("Date", "")),
                    league=row.get("Div", ""),
                    home=home,
                    away=away,
                    home_goals=int(row["FTHG"]),
                    away_goals=int(row["FTAG"]),
                    home_odds=oh, draw_odds=od, away_odds=oa,
                )
            )
        except (KeyError, ValueError, TypeError, AttributeError):
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
    start = datetime.date(2025, 8, 1)
    day = 0
    for _ in range(rounds):
        for i, home in enumerate(teams):
            for j, away in enumerate(teams):
                if i == j:
                    continue
                hg = _score(_SAMPLE_STRENGTH[home], _SAMPLE_STRENGTH[away], 0.4)
                ag = _score(_SAMPLE_STRENGTH[away], _SAMPLE_STRENGTH[home], 0.0)
                matches.append(
                    HistoricalMatch(
                        date=(start + datetime.timedelta(days=day)).isoformat(),
                        league="SAMPLE",
                        home=home,
                        away=away,
                        home_goals=hg,
                        away_goals=ag,
                    )
                )
                day += 1
    return matches
