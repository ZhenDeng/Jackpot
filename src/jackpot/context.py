"""Context factors → bounded goal-expectancy multipliers.

Real match context (weather, rest, key absences) nudges the prediction through the
engine's existing ``home_adjust``/``away_adjust`` hooks. Every factor is user-supplied
(never guessed), bounded, and the combined result is clamped so no single factor can
dominate the goal model.
"""
from __future__ import annotations

from typing import Optional, Tuple

ADJUST_FLOOR = 0.70
ADJUST_CEIL = 1.30

_REST_FULL_DAYS = 4.0       # at/above this, rest is a non-factor
_REST_MIN_FACTOR = 0.90     # floor for an utterly exhausted side
_ATTACKER_OUT = 0.88        # a team scores ~12% less without a key attacker
_DEFENDER_OUT_OPP = 1.10    # the opponent scores ~10% more vs a missing key defender


def rest_factor(rest_days: Optional[float]) -> float:
    """Fatigue multiplier from days of rest: 1.0 when well-rested, lower when not."""
    if rest_days is None or rest_days >= _REST_FULL_DAYS:
        return 1.0
    # linear from 1.0 at _REST_FULL_DAYS down toward _REST_MIN_FACTOR at 0 days
    frac = max(0.0, rest_days) / _REST_FULL_DAYS
    return _REST_MIN_FACTOR + (1.0 - _REST_MIN_FACTOR) * frac


def _clamp(x: float) -> float:
    return max(ADJUST_FLOOR, min(ADJUST_CEIL, x))


def compute_adjustments(
    weather_mult: float = 1.0,
    home_rest: Optional[float] = None,
    away_rest: Optional[float] = None,
    home_attacker_out: bool = False,
    away_attacker_out: bool = False,
    home_defender_out: bool = False,
    away_defender_out: bool = False,
) -> Tuple[float, float]:
    """Combine context factors into ``(home_adjust, away_adjust)`` λ multipliers.

    Weather scales both sides; rest and a missing attacker scale the affected side's
    own scoring; a missing defender raises the *opponent's* scoring. The result is
    clamped to ``[ADJUST_FLOOR, ADJUST_CEIL]``.
    """
    home = weather_mult * rest_factor(home_rest)
    away = weather_mult * rest_factor(away_rest)
    if home_attacker_out:
        home *= _ATTACKER_OUT
    if away_attacker_out:
        away *= _ATTACKER_OUT
    if away_defender_out:          # away missing a defender -> home scores more
        home *= _DEFENDER_OUT_OPP
    if home_defender_out:          # home missing a defender -> away scores more
        away *= _DEFENDER_OUT_OPP
    return _clamp(home), _clamp(away)
