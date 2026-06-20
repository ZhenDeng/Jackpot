"""Combine team strengths into the expected goals (lambda) for a specific match."""
from __future__ import annotations

from typing import Tuple

DEFAULT_HOME_ADV = 1.3


def compute_lambdas(
    home_attack: float,
    home_defense: float,
    away_attack: float,
    away_defense: float,
    league_avg: float,
    home_adv: float = DEFAULT_HOME_ADV,
    home_adjust: float = 1.0,
    away_adjust: float = 1.0,
) -> Tuple[float, float]:
    """Return ``(lambda_home, lambda_away)`` — expected goals for each side.

    lambda_home = league_avg * home_attack * away_defense * home_adv * home_adjust
    lambda_away = league_avg * away_attack * home_defense * away_adjust

    ``*_adjust`` are bounded multiplicative context factors (weather, rest,
    fatigue) applied on top of pure strength.
    """
    values = {
        "home_attack": home_attack,
        "home_defense": home_defense,
        "away_attack": away_attack,
        "away_defense": away_defense,
        "league_avg": league_avg,
        "home_adv": home_adv,
        "home_adjust": home_adjust,
        "away_adjust": away_adjust,
    }
    for name, v in values.items():
        if v < 0:
            raise ValueError(f"{name} must be non-negative")

    lam_home = league_avg * home_attack * away_defense * home_adv * home_adjust
    lam_away = league_avg * away_attack * home_defense * away_adjust
    return lam_home, lam_away
