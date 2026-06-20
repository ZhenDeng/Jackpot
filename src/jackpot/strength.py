"""Estimate each team's attack/defense strength.

Strength is expressed relative to the league average (1.0 == average). It is
built from scoring/conceding **rates** (xG-based when available, since xG predicts
future goals better than past goals) and then **shrunk** toward 1.0 by sample size
so small samples — early season, promoted teams — don't produce wild estimates.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class TeamRates:
    """A team's per-game attacking/defending output over its recent matches.

    ``scored_per_game`` / ``conceded_per_game`` are xG-based when ``uses_xg`` is
    True, otherwise actual goals. ``matches`` is the sample size used for shrinkage.
    """

    scored_per_game: float
    conceded_per_game: float
    matches: int
    uses_xg: bool = False


def _shrink(raw: float, matches: int, shrink_k: float) -> float:
    """Pull ``raw`` toward 1.0, weighted by sample size.

    With ``k`` pseudo-matches at the league-average prior, the estimate is
    ``(n*raw + k*1.0) / (n + k)``.
    """
    n = max(0, matches)
    return (n * raw + shrink_k * 1.0) / (n + shrink_k)


def estimate_strength(
    rates: TeamRates,
    league_avg: float,
    shrink_k: float = 5.0,
) -> Tuple[float, float]:
    """Return ``(attack_strength, defense_strength)`` relative to league average.

    attack > 1 means the team scores more than average; defense < 1 means it
    concedes less than average (a good defense).
    """
    if league_avg <= 0:
        raise ValueError("league_avg must be positive")
    raw_attack = rates.scored_per_game / league_avg
    raw_defense = rates.conceded_per_game / league_avg
    attack = _shrink(raw_attack, rates.matches, shrink_k)
    defense = _shrink(raw_defense, rates.matches, shrink_k)
    return attack, defense


def decay_weight(age_days: float, half_life_days: float = 180.0) -> float:
    """Exponential time-decay weight: 1.0 today, halving every ``half_life_days``."""
    if half_life_days <= 0:
        raise ValueError("half_life_days must be positive")
    return 0.5 ** (age_days / half_life_days)


def weighted_mean(pairs: List[Tuple[float, float]]) -> float:
    """Weighted mean of ``(value, weight)`` pairs (used for time-decayed rates)."""
    total_w = sum(w for _v, w in pairs)
    if total_w <= 0:
        raise ValueError("weights must sum to a positive number")
    return sum(v * w for v, w in pairs) / total_w
