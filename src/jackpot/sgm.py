"""Same Game Multi (SGM): combine the highest-confidence legs from one match.

A Same Game Multi is a single bet built from several selections within the *same*
fixture. We take the single most probable selection from each distinct market
dimension (result, match goals, both-teams-to-score, each team's goals), rank
those by probability, and combine the top ``n`` into one multi.

Picking one leg per dimension is deliberate: it keeps the legs distinct and
avoids nesting the same event twice (e.g. "Over 1.5" *and* "Over 2.5").

Correlation caveat: legs in the same game are not independent, so multiplying
their probabilities gives an *optimistic* combined estimate, not an exact one.
The combined fair odds are therefore a lower bound on a true correlated price.
"""
from __future__ import annotations

from math import prod
from typing import Dict, List, Tuple

from .odds import fair_odds


def _best(options: List[Tuple[str, float]]) -> Tuple[str, float]:
    """The (label, prob) with the highest probability."""
    return max(options, key=lambda o: o[1])


def _candidates(markets: dict, home: str, away: str) -> List[dict]:
    """One best-of selection per distinct market dimension."""
    dims: List[Tuple[str, Tuple[str, float]]] = []

    dc = markets["double_chance"]
    dims.append(("Result", _best([
        (f"{home} or Draw", dc["1X"]["prob"]),
        (f"{home} or {away}", dc["12"]["prob"]),
        (f"Draw or {away}", dc["X2"]["prob"]),
    ])))

    ou = markets["over_under"]
    ou_opts = []
    for line, rec in ou.items():
        ou_opts.append((f"Over {line} goals", rec["over"]["prob"]))
        ou_opts.append((f"Under {line} goals", rec["under"]["prob"]))
    dims.append(("Match goals", _best(ou_opts)))

    b = markets["btts"]
    dims.append(("Both teams to score", _best([
        ("Yes", b["yes"]["prob"]),
        ("No", b["no"]["prob"]),
    ])))

    tt = markets["team_total_goals"]
    for side, team in (("home", home), ("away", away)):
        opts = []
        for line, sides in tt.items():
            opts.append((f"{team} Over {line} goals", sides[side]["over"]["prob"]))
            opts.append((f"{team} Under {line} goals", sides[side]["under"]["prob"]))
        dims.append((f"{team} goals", _best(opts)))

    return [
        {"market": market, "selection": sel, "prob": p, "fair_odds": fair_odds(p)}
        for market, (sel, p) in dims
    ]


def same_game_multi(markets: dict, home: str, away: str, n: int = 4) -> Dict[str, object]:
    """Build a Same Game Multi from the ``n`` highest-confidence legs.

    ``markets`` is the ``markets`` block of a ``predict`` / ``predict_international``
    result. Returns the chosen ``legs`` (sorted most to least probable) plus the
    combined probability and combined fair odds for landing every leg.

    Raises ``ValueError`` for ``n < 1``. When fewer than ``n`` distinct dimensions
    exist, all of them are returned.
    """
    if n < 1:
        raise ValueError("n must be a positive integer")

    candidates = _candidates(markets, home, away)
    candidates.sort(key=lambda c: c["prob"], reverse=True)
    legs = candidates[:n]

    combined_prob = prod(leg["prob"] for leg in legs)
    return {
        "legs": legs,
        "combined_prob": combined_prob,
        "combined_fair_odds": fair_odds(combined_prob),
    }
