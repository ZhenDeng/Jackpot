"""Derive every bet market from the score matrix.

Each market is just a sum over the relevant cells of ``m[h][a]``. Because they all
come from the same matrix, the Tab is internally consistent by construction.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

Matrix = List[List[float]]


def _size(m: Matrix) -> int:
    return len(m)


def match_result(m: Matrix) -> Dict[str, float]:
    """1X2 — home win / draw / away win."""
    n = _size(m)
    home = sum(m[h][a] for h in range(n) for a in range(n) if h > a)
    draw = sum(m[h][h] for h in range(n))
    away = sum(m[h][a] for h in range(n) for a in range(n) if h < a)
    return {"home": home, "draw": draw, "away": away}


def over_under(m: Matrix, line: float) -> Dict[str, float]:
    """Over/Under total goals for a (typically .5) ``line``.

    Over wins when total goals strictly exceed the line.
    """
    n = _size(m)
    over = sum(
        m[h][a] for h in range(n) for a in range(n) if (h + a) > line
    )
    under = sum(
        m[h][a] for h in range(n) for a in range(n) if (h + a) <= line
    )
    return {"over": over, "under": under}


def btts(m: Matrix) -> Dict[str, float]:
    """Both Teams To Score — yes when both score at least one."""
    n = _size(m)
    yes = sum(m[h][a] for h in range(1, n) for a in range(1, n))
    return {"yes": yes, "no": 1.0 - yes}


def correct_score(m: Matrix, top_n: int = 5) -> List[Tuple[int, int, float]]:
    """Most likely exact scorelines, highest probability first."""
    n = _size(m)
    scores = [
        (h, a, m[h][a]) for h in range(n) for a in range(n)
    ]
    scores.sort(key=lambda t: t[2], reverse=True)
    return scores[:top_n]


def double_chance(m: Matrix) -> Dict[str, float]:
    """Double chance — two of the three 1X2 outcomes."""
    r = match_result(m)
    return {
        "1X": r["home"] + r["draw"],
        "12": r["home"] + r["away"],
        "X2": r["draw"] + r["away"],
    }


def draw_no_bet(m: Matrix) -> Dict[str, float]:
    """Draw No Bet — stake refunded on a draw, so renormalise excluding it."""
    r = match_result(m)
    non_draw = r["home"] + r["away"]
    if non_draw <= 0:
        raise ValueError("degenerate matrix: draw probability is ~1, DNB undefined")
    return {"home": r["home"] / non_draw, "away": r["away"] / non_draw}
