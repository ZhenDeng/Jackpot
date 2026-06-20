"""Orchestrate a full Tab prediction from resolved match data.

Pipeline: strengths -> lambdas -> score matrix -> markets -> per-outcome
probability / fair odds / value flag, with optional market blending. Everything
flows from one matrix, so the Tab is internally consistent.
"""
from __future__ import annotations

from typing import Dict, Optional, Sequence

from .data.base import MatchData
from .strength import TeamRates, estimate_strength
from .lambdas import compute_lambdas
from .matrix import build_score_matrix
from . import markets as mk
from .odds import fair_odds, strip_overround, blend, is_value, confidence_level

DEFAULT_OU_LINES = (1.5, 2.5, 3.5)
VALUE_THRESHOLD = 0.05


def _rates(form) -> TeamRates:
    return TeamRates(
        scored_per_game=form.scored_per_game,
        conceded_per_game=form.conceded_per_game,
        matches=form.matches,
        uses_xg=form.uses_xg,
    )


def _outcome(prob: float, market_p: Optional[float]) -> Dict[str, object]:
    """Per-outcome record: probability, fair odds, and value flag vs the market."""
    return {
        "prob": prob,
        "fair_odds": fair_odds(prob),
        "value": (market_p is not None and is_value(prob, market_p, VALUE_THRESHOLD)),
    }


def predict(
    match: MatchData,
    over_under_lines: Sequence[float] = DEFAULT_OU_LINES,
    blend_weight: float = 1.0,
    correct_score_top_n: int = 6,
) -> Dict[str, object]:
    """Produce the full prediction Tab for a match.

    ``blend_weight`` is the model's share when market odds are present
    (1.0 = pure model, 0.0 = pure market). Value flags always compare the final
    (possibly blended) probability to the margin-stripped market price.
    """
    ctx = match.context

    # 1. strengths (xG-based, shrunk toward league average)
    h_att, h_def = estimate_strength(_rates(match.home), ctx.league_avg_goals)
    a_att, a_def = estimate_strength(_rates(match.away), ctx.league_avg_goals)

    # 2. expected goals for this fixture
    lam_home, lam_away = compute_lambdas(
        home_attack=h_att, home_defense=h_def,
        away_attack=a_att, away_defense=a_def,
        league_avg=ctx.league_avg_goals,
        home_adjust=ctx.home_adjust, away_adjust=ctx.away_adjust,
    )

    # 3. the one source of truth
    matrix = build_score_matrix(lam_home, lam_away)

    # 4. raw market probabilities derived from the matrix
    raw_mr = mk.match_result(matrix)
    raw_btts = mk.btts(matrix)
    raw_dc = mk.double_chance(matrix)
    raw_dnb = mk.draw_no_bet(matrix)

    # 5. optional market blend (only the 1X2 market has odds in scope)
    market_mr: Optional[Dict[str, float]] = None
    if ctx.market_odds:
        market_mr = strip_overround(ctx.market_odds)
        final_mr = {
            k: blend(raw_mr[k], market_mr[k], blend_weight) for k in raw_mr
        }
        # renormalise after blending so it still sums to 1
        s = sum(final_mr.values())
        final_mr = {k: v / s for k, v in final_mr.items()}
    else:
        final_mr = raw_mr

    # 6. assemble per-outcome records
    match_result = {
        k: _outcome(final_mr[k], market_mr[k] if market_mr else None)
        for k in ("home", "draw", "away")
    }

    over_under = {}
    for line in over_under_lines:
        ou = mk.over_under(matrix, line)
        over_under[str(line)] = {
            "over": _outcome(ou["over"], None),
            "under": _outcome(ou["under"], None),
        }

    btts = {
        "yes": _outcome(raw_btts["yes"], None),
        "no": _outcome(raw_btts["no"], None),
    }
    double_chance = {k: _outcome(v, None) for k, v in raw_dc.items()}
    draw_no_bet = {k: _outcome(v, None) for k, v in raw_dnb.items()}
    correct_score = mk.correct_score(matrix, correct_score_top_n)

    # 7. honest confidence from the thinner of the two samples
    min_matches = min(match.home.matches, match.away.matches)
    has_xg = match.home.uses_xg and match.away.uses_xg
    confidence = confidence_level(min_matches, has_xg)

    return {
        "home_team": match.home.name,
        "away_team": match.away.name,
        "lambda_home": lam_home,
        "lambda_away": lam_away,
        "confidence": confidence,
        "markets": {
            "match_result": match_result,
            "over_under": over_under,
            "btts": btts,
            "correct_score": correct_score,
            "double_chance": double_chance,
            "draw_no_bet": draw_no_bet,
        },
    }
