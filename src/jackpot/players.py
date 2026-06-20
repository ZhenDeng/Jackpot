"""Player goal model — distribute the team's expected goals across the squad.

Player props are tied to the same team lambda that drives every other market, so
the squad's expected goals sum back to the team total (conservation). Each player's
goals are then treated as Poisson(lambda_i).
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

# fraction of team goals modelled as penalties, assigned to the penalty taker(s)
PENALTY_FRACTION = 0.08

# entry = (player_name, raw_output, is_penalty_taker)
Entry = Tuple[str, float, bool]


def raw_output(xg_per90: float, expected_minutes: float) -> float:
    """A player's base attacking output: xG/90 scaled by expected minutes."""
    if xg_per90 < 0 or expected_minutes < 0:
        raise ValueError("xg_per90 and expected_minutes must be non-negative")
    return xg_per90 * (expected_minutes / 90.0)


def p_score(lam: float) -> float:
    """P(player scores at least once) for Poisson rate ``lam``."""
    return 1.0 - math.exp(-lam)


def p_two_plus(lam: float) -> float:
    """P(player scores two or more)."""
    return 1.0 - math.exp(-lam) * (1.0 + lam)


def allocate_lambdas(
    entries: List[Entry],
    team_lambda: float,
    penalty_fraction: float = PENALTY_FRACTION,
) -> Dict[str, float]:
    """Split ``team_lambda`` across players by attacking share (+ penalty pool).

    Returns ``{player_name: lambda_i}``. The player lambdas sum to ``team_lambda``
    (conservation). The penalty pool is shared equally among penalty takers; if
    there are none, it folds back into the open-play pool so nothing is lost.
    """
    if team_lambda < 0:
        raise ValueError("team_lambda must be non-negative")
    total_raw = sum(raw for _name, raw, _pen in entries)
    if total_raw <= 0:
        return {}

    takers = [name for name, _raw, pen in entries if pen]
    pen_frac = penalty_fraction if takers else 0.0
    open_pool = team_lambda * (1.0 - pen_frac)
    pen_each = (team_lambda * pen_frac / len(takers)) if takers else 0.0

    result: Dict[str, float] = {}
    for name, raw, pen in entries:
        lam = (raw / total_raw) * open_pool
        if pen:
            lam += pen_each
        result[name] = lam
    return result
