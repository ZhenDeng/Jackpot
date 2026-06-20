"""Odds maths: fair odds, overround stripping, market blending, value, confidence."""
from __future__ import annotations

from typing import Dict


def fair_odds(prob: float) -> float:
    """Fair decimal odds for a probability (1 / p). Zero prob -> infinite odds."""
    if prob < 0:
        raise ValueError("probability must be non-negative")
    if prob == 0:
        return float("inf")
    return 1.0 / prob


def implied_prob(odds: float) -> float:
    """Raw implied probability from decimal odds (1 / odds), incl. the margin."""
    if odds <= 0:
        raise ValueError("odds must be positive")
    return 1.0 / odds


def strip_overround(odds: Dict[str, float]) -> Dict[str, float]:
    """Convert a set of bookmaker decimal odds to true probabilities.

    Bookmaker implied probabilities sum to more than 1 (the overround / vig). We
    remove it with the simple proportional method: normalise the raw implied
    probabilities so they sum to 1.
    """
    raw = {k: implied_prob(v) for k, v in odds.items()}
    total = sum(raw.values())
    if total <= 0:
        raise ValueError("degenerate odds")
    return {k: v / total for k, v in raw.items()}


def blend(model_p: float, market_p: float, weight: float) -> float:
    """Blend model and market probabilities. ``weight`` is the model's share."""
    if not 0.0 <= weight <= 1.0:
        raise ValueError("weight must be in [0, 1]")
    return weight * model_p + (1.0 - weight) * market_p


def is_value(model_p: float, market_p: float, threshold: float = 0.05) -> bool:
    """True when the model probability beats the market by at least ``threshold``.

    This is the positive-expected-value signal: we only flag a bet when our
    estimate is materially higher than the (margin-stripped) market price.
    """
    return (model_p - market_p) >= threshold


def confidence_level(matches: int, has_xg: bool) -> str:
    """Honest confidence from data completeness.

    Thin samples and missing xG make the estimate less trustworthy, so we say so.
    """
    if matches < 5:
        return "Low"
    if matches >= 10 and has_xg:
        return "High"
    if has_xg:
        return "Medium"
    return "Low"
