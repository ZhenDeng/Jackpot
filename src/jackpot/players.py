"""Player goal model — distribute the team's expected goals across the squad.

Player props are tied to the same team lambda that drives every other market, so
the squad's expected goals sum back to the team total (conservation). Each player's
goals are then treated as Poisson(lambda_i).
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

from .odds import fair_odds

# fraction of team goals modelled as penalties, assigned to the penalty taker(s)
PENALTY_FRACTION = 0.08

# Fraction of ALL a team's goals that are assisted (penalties in the denominator),
# used to size the assist pool shared across creators. ~0.75 already folds in that
# penalties and solo efforts have no assister (open-play share ~0.92 × ~0.80
# assisted ≈ 0.74), so the pool is sized off the full team lambda — do NOT also
# apply a (1 - PENALTY_FRACTION) correction or assists get double-discounted.
ASSIST_FRACTION = 0.75

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


def p_involvement(goal_lambda: float, assist_lambda: float) -> float:
    """P(player scores OR assists at least once).

    Goals and assists are treated as independent Poisson processes, so
    P(neither) = e^-goal * e^-assist and involvement = 1 - that. With
    ``assist_lambda == 0`` this is exactly the anytime-scorer probability.
    """
    if goal_lambda < 0 or assist_lambda < 0:
        raise ValueError("goal_lambda and assist_lambda must be non-negative")
    return 1.0 - math.exp(-(goal_lambda + assist_lambda))


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
    if not 0.0 <= penalty_fraction <= 1.0:
        raise ValueError("penalty_fraction must be in [0, 1]")

    # Aggregate entries that share a name so duplicates can't drop lambda mass
    # (dict keys collide) and break conservation.
    merged: Dict[str, List] = {}
    order: List[str] = []
    for name, raw, pen in entries:
        if name not in merged:
            merged[name] = [0.0, False]
            order.append(name)
        merged[name][0] += raw
        merged[name][1] = merged[name][1] or pen
    entries = [(name, merged[name][0], merged[name][1]) for name in order]

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


def build_player_props(
    squad: Optional[Sequence],
    team_lambda: float,
    top_n: int,
    assist_fraction: float = ASSIST_FRACTION,
) -> List[dict]:
    """Per-player props for a team, headlined by goal involvement (score or assist).

    Goals are allocated from ``team_lambda`` (with the penalty boost); assists are
    allocated from a separate ``team_lambda * assist_fraction`` pool by xA/90 share
    (no penalty boost — penalties aren't assisted). Each player's involvement is
    ``p_involvement(goal_lambda, assist_lambda)``. Returns the ``top_n`` most likely
    to be involved; ``[]`` when no squad / no attacking output is available.

    A pure-creator (xG/90 = 0, xA/90 > 0) has ``p_score == 0`` and therefore
    ``fair_odds == inf`` — the same zero-probability convention used everywhere
    else; callers render it via the ``_odds`` helper.
    """
    if not squad:
        return []

    goal_entries = [
        (p.name, raw_output(p.xg_per90, p.expected_minutes), p.penalty_taker)
        for p in squad
    ]
    assist_entries = [
        (p.name, raw_output(p.xa_per90, p.expected_minutes), False)
        for p in squad
    ]
    goal_lams = allocate_lambdas(goal_entries, team_lambda)
    assist_lams = allocate_lambdas(
        assist_entries, team_lambda * assist_fraction, penalty_fraction=0.0
    )
    if not goal_lams and not assist_lams:        # no attacking output at all
        return []

    names: List[str] = []
    seen = set()
    for p in squad:                              # stable, de-duplicated order
        if p.name not in seen:
            seen.add(p.name)
            names.append(p.name)

    props = []
    for name in names:
        g = goal_lams.get(name, 0.0)
        a = assist_lams.get(name, 0.0)
        involve = p_involvement(g, a)
        sc = p_score(g)
        props.append({
            "player": name,
            "p_involve": involve,
            "fair_odds_involve": fair_odds(involve),
            "p_score": sc,
            "p_2plus": p_two_plus(g),
            "fair_odds": fair_odds(sc),
        })
    props.sort(key=lambda e: e["p_involve"], reverse=True)
    return props[:top_n]
