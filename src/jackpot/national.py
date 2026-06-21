"""World Cup / national-team variant: Elo ratings -> expected goals.

National teams have no league table, so the club model's xG-based strength doesn't
apply. Instead we drive expected goals from **Elo ratings** (free, and academically
more predictive than FIFA rankings), then reuse the exact same score matrix and
markets — so the Tab stays internally consistent with the club model.
"""
from __future__ import annotations

import sys
from typing import Dict, List, Optional, Sequence, Tuple

from .matrix import build_score_matrix
from . import markets as mk
from . import players as pl
from .odds import fair_odds, strip_overround, blend, is_value

INTL_TOTAL_GOALS = 2.6     # baseline expected total goals in an international match
GOALS_PER_ELO = 0.006      # expected goal supremacy per Elo point of difference
HOME_ADV_ELO = 65.0        # Elo-point home edge (only when not a neutral venue)
LAMBDA_FLOOR = 0.15        # keep both sides' expected goals positive
# Elo-gap thresholds for prediction confidence (international football is high
# variance, so the bars are deliberately conservative).
CONFIDENCE_HIGH_GAP = 250.0
CONFIDENCE_MEDIUM_GAP = 100.0


def elo_confidence(elo_home: float, elo_away: float) -> str:
    """Prediction confidence from the Elo gap: a decisive mismatch is a confident
    call, a near-even tie is genuinely a coin-flip."""
    gap = abs(elo_home - elo_away)
    if gap >= CONFIDENCE_HIGH_GAP:
        return "High"
    if gap >= CONFIDENCE_MEDIUM_GAP:
        return "Medium"
    return "Low"


# Illustrative national-team Elo ratings (eloratings.net style; not live).
SAMPLE_ELO = {
    "Brazil": 2030,
    "Argentina": 2090,
    "France": 2010,
    "England": 1960,
    "Spain": 1980,
    "Portugal": 1950,
    "Netherlands": 1930,
    "Belgium": 1900,
    "Germany": 1900,
    "Croatia": 1850,
    "Morocco": 1830,
    "USA": 1750,
    "Mexico": 1740,
    "Japan": 1760,
    "Australia": 1700,
    "Ghana": 1640,
}


def lookup_elo(team: str) -> int:
    """Elo rating for a national team from the bundled sample table."""
    if team not in SAMPLE_ELO:
        raise KeyError(f"no sample Elo for '{team}'; pass an explicit rating")
    return SAMPLE_ELO[team]


def elo_to_lambdas(
    elo_home: float,
    elo_away: float,
    neutral: bool = True,
    total_goals: float = INTL_TOTAL_GOALS,
    goals_per_elo: float = GOALS_PER_ELO,
    home_adv_elo: float = HOME_ADV_ELO,
) -> Tuple[float, float]:
    """Convert two Elo ratings into ``(lambda_home, lambda_away)`` expected goals.

    Splits a fixed ``total_goals`` baseline around an Elo-derived goal *supremacy*.
    World Cup venues are neutral by default (no home edge). Both sides are floored
    so a huge mismatch can't drive expected goals to/through zero.
    """
    dr = (elo_home - elo_away) + (0.0 if neutral else home_adv_elo)
    supremacy = goals_per_elo * dr
    raw_home = (total_goals + supremacy) / 2.0
    raw_away = (total_goals - supremacy) / 2.0
    lam_home = max(LAMBDA_FLOOR, raw_home)
    lam_away = max(LAMBDA_FLOOR, raw_away)

    # If the floor lifted the underdog, shed the surplus from the favourite so
    # total expected goals stays at ``total_goals`` (the clamped side can't go
    # lower, so all goal markets would otherwise be biased upward).
    excess = (lam_home + lam_away) - total_goals
    if excess > 0:
        if raw_home >= raw_away:
            lam_home = max(LAMBDA_FLOOR, lam_home - excess)
        else:
            lam_away = max(LAMBDA_FLOOR, lam_away - excess)
    return lam_home, lam_away


_OU_LINES = (1.5, 2.5, 3.5)
_TEAM_TOTAL_LINES = (0.5, 1.5, 2.5)   # match the club path's team-total lines
_VALUE_THRESHOLD = 0.05
_PLAYER_TOP_N = 8


_REQUIRED_MR_KEYS = {"home", "draw", "away"}


def _o(
    prob: float,
    market_p: Optional[float] = None,
    raw_model_p: Optional[float] = None,
) -> Dict[str, object]:
    """Per-outcome record. Value compares the *raw model* prob to the market, so a
    blended output probability never dilutes the value signal."""
    model_p = raw_model_p if raw_model_p is not None else prob
    return {
        "prob": prob,
        "fair_odds": fair_odds(prob),
        "value": market_p is not None and is_value(model_p, market_p, _VALUE_THRESHOLD),
    }


def _player_props(squad, team_lambda: float) -> List[dict]:
    if not squad:
        return []
    entries = [
        (p.name, pl.raw_output(p.xg_per90, p.expected_minutes), p.penalty_taker)
        for p in squad
    ]
    lambdas = pl.allocate_lambdas(entries, team_lambda)
    props = [
        {
            "player": name,
            "p_score": pl.p_score(lam),
            "p_2plus": pl.p_two_plus(lam),
            "fair_odds": fair_odds(pl.p_score(lam)),
        }
        for name, lam in lambdas.items()
    ]
    props.sort(key=lambda e: e["p_score"], reverse=True)
    return props[:_PLAYER_TOP_N]


def predict_international(
    home: str,
    away: str,
    elo_home: float,
    elo_away: float,
    neutral: bool = True,
    home_squad=None,
    away_squad=None,
    market_odds: Optional[Dict[str, float]] = None,
    blend_weight: float = 1.0,
    home_adjust: float = 1.0,
    away_adjust: float = 1.0,
) -> Dict[str, object]:
    """Full prediction Tab for an international fixture, driven by Elo ratings.

    Elo -> expected goals -> the same score matrix and markets as the club model,
    so the output shape and consistency guarantees match ``predict()``.

    ``home_adjust``/``away_adjust`` are bounded context multipliers (weather, rest,
    key absences) applied to the Elo-derived expected goals — parity with the club
    path so context factors work for national matches too.
    """
    if market_odds is not None and set(market_odds) != _REQUIRED_MR_KEYS:
        raise ValueError(
            f"market_odds must have exactly keys {_REQUIRED_MR_KEYS}, got {set(market_odds)}"
        )

    lam_home, lam_away = elo_to_lambdas(elo_home, elo_away, neutral=neutral)
    lam_home *= home_adjust
    lam_away *= away_adjust
    matrix = build_score_matrix(lam_home, lam_away)

    raw_mr = mk.match_result(matrix)
    market_mr = strip_overround(market_odds) if market_odds else None
    if market_mr:
        final_mr = {k: blend(raw_mr[k], market_mr[k], blend_weight) for k in raw_mr}
    else:
        final_mr = raw_mr

    match_result = {
        k: _o(final_mr[k], market_mr[k] if market_mr else None, raw_model_p=raw_mr[k])
        for k in ("home", "draw", "away")
    }
    over_under = {}
    for line in _OU_LINES:
        ou = mk.over_under(matrix, line)
        over_under[str(line)] = {"over": _o(ou["over"]), "under": _o(ou["under"])}
    btts = {k: _o(v) for k, v in mk.btts(matrix).items()}
    double_chance = {k: _o(v) for k, v in mk.double_chance(matrix).items()}
    draw_no_bet = {k: _o(v) for k, v in mk.draw_no_bet(matrix).items()}
    correct_score = mk.correct_score(matrix, 6)

    team_total_goals = {}
    for line in _TEAM_TOTAL_LINES:
        tt = mk.team_total_goals(matrix, line)
        team_total_goals[str(line)] = {
            side: {"over": _o(tt[side]["over"]), "under": _o(tt[side]["under"])}
            for side in ("home", "away")
        }
    clean_sheet = {k: _o(v) for k, v in mk.clean_sheet(matrix).items()}
    win_to_nil = {k: _o(v) for k, v in mk.win_to_nil(matrix).items()}
    winning_margin = {k: _o(v) for k, v in mk.winning_margin(matrix).items()}

    return {
        "home": home,
        "away": away,
        # shared contract with predict() so a common renderer can read either result
        "home_team": home,
        "away_team": away,
        "confidence": elo_confidence(elo_home, elo_away),
        "elo_home": elo_home,
        "elo_away": elo_away,
        "neutral": neutral,
        "lambda_home": lam_home,
        "lambda_away": lam_away,
        "markets": {
            "match_result": match_result,
            "over_under": over_under,
            "btts": btts,
            "correct_score": correct_score,
            "double_chance": double_chance,
            "draw_no_bet": draw_no_bet,
            "team_total_goals": team_total_goals,
            "clean_sheet": clean_sheet,
            "win_to_nil": win_to_nil,
            "winning_margin": winning_margin,
            "player_props": {
                "home": _player_props(home_squad, lam_home),
                "away": _player_props(away_squad, lam_away),
            },
        },
    }


# --- CLI ----------------------------------------------------------------------

def _pct(p: float) -> str:
    return f"{p * 100:.1f}%"


def format_international(out: Dict[str, object]) -> str:
    """Render an international prediction as a compact text report."""
    m = out["markets"]
    mr = m["match_result"]
    ou = m["over_under"]["2.5"]
    btts = m["btts"]
    lines = [
        f"{out['home']} (Elo {out['elo_home']}) vs {out['away']} (Elo {out['elo_away']})"
        f"  [{'neutral' if out['neutral'] else 'home'} venue]",
        f"expected goals: {out['lambda_home']:.2f} - {out['lambda_away']:.2f}",
        "",
        f"  {out['home']} win : {_pct(mr['home']['prob'])}  (fair {mr['home']['fair_odds']:.2f})",
        f"  Draw       : {_pct(mr['draw']['prob'])}",
        f"  {out['away']} win : {_pct(mr['away']['prob'])}",
        f"  Over 2.5   : {_pct(ou['over']['prob'])}    BTTS yes: {_pct(btts['yes']['prob'])}",
        "  likely scores: "
        + ", ".join(f"{h}-{a} ({_pct(p)})" for h, a, p in m["correct_score"][:3]),
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] = ()) -> int:
    """CLI: `python -m jackpot.national HOME AWAY [elo_home elo_away] [--home]`."""
    args = list(argv)
    neutral = True
    if "--home" in args:
        neutral = False
        args.remove("--home")
    if len(args) < 2:
        print('usage: python -m jackpot.national "Brazil" "Croatia" [eloH eloA] [--home]')
        return 2
    home, away = args[0], args[1]
    try:
        if len(args) >= 4:
            elo_home, elo_away = float(args[2]), float(args[3])
        else:
            elo_home, elo_away = lookup_elo(home), lookup_elo(away)
    except (KeyError, ValueError) as e:
        print(f"error: {e}")
        return 1
    print(format_international(
        predict_international(home, away, elo_home, elo_away, neutral=neutral)
    ))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
