"""Corners & cards — independent-Poisson count markets (fed by manual rates).

These are separate from the goals score-matrix: corners and cards are their own
counts. Each side is a Poisson rate; a total is the sum of two independent
Poissons. Card counts are dominated by the referee, so a referee factor scales them.
"""
from __future__ import annotations

import sys
from typing import Dict, Sequence

from .poisson import poisson_pmf
from .odds import fair_odds

CORNER_TOTAL_LINES = (8.5, 9.5, 10.5)
CORNER_TEAM_LINES = (3.5, 4.5)
CARD_TOTAL_LINES = (3.5, 4.5, 5.5)
CARD_TEAM_LINES = (1.5, 2.5)
DEFAULT_LEAGUE_REF_AVG = 4.0  # league-average yellow+red cards per game per referee


def poisson_over_under(lam: float, line: float) -> Dict[str, float]:
    """Over/Under for a Poisson count at a ``.5`` line (no push)."""
    if lam < 0:
        raise ValueError("lam must be non-negative")
    under = sum(poisson_pmf(k, lam) for k in range(int(line) + 1))
    return {"over": 1.0 - under, "under": under}


def _ou_table(lam: float, lines: Sequence[float]) -> Dict[str, Dict[str, float]]:
    return {str(l): poisson_over_under(lam, l) for l in lines}


def corners_markets(
    home_for: float,
    home_against: float,
    away_for: float,
    away_against: float,
    total_lines: Sequence[float] = CORNER_TOTAL_LINES,
    team_lines: Sequence[float] = CORNER_TEAM_LINES,
) -> Dict[str, object]:
    """Corner markets from each team's corners-for/against per game."""
    for name, v in (
        ("home_for", home_for), ("home_against", home_against),
        ("away_for", away_for), ("away_against", away_against),
    ):
        if v < 0:
            raise ValueError(f"{name} must be non-negative")
    lam_home = (home_for + away_against) / 2.0
    lam_away = (away_for + home_against) / 2.0
    lam_total = lam_home + lam_away
    return {
        "lambda_home": lam_home,
        "lambda_away": lam_away,
        "lambda_total": lam_total,
        "total": _ou_table(lam_total, total_lines),
        "home": _ou_table(lam_home, team_lines),
        "away": _ou_table(lam_away, team_lines),
    }


def cards_markets(
    home_rate: float,
    away_rate: float,
    referee_cpg: float = None,
    league_ref_avg: float = DEFAULT_LEAGUE_REF_AVG,
    total_lines: Sequence[float] = CARD_TOTAL_LINES,
    team_lines: Sequence[float] = CARD_TEAM_LINES,
) -> Dict[str, object]:
    """Card markets from each team's cards-per-game, scaled by a referee factor."""
    if home_rate < 0 or away_rate < 0:
        raise ValueError("card rates must be non-negative")
    if league_ref_avg <= 0:
        raise ValueError("league_ref_avg must be positive")
    ref_factor = (referee_cpg / league_ref_avg) if referee_cpg is not None else 1.0
    if ref_factor < 0:
        raise ValueError("referee_cpg must be non-negative")
    lam_home = home_rate * ref_factor
    lam_away = away_rate * ref_factor
    lam_total = lam_home + lam_away
    return {
        "lambda_home": lam_home,
        "lambda_away": lam_away,
        "lambda_total": lam_total,
        "ref_factor": ref_factor,
        "total": _ou_table(lam_total, total_lines),
        "home": _ou_table(lam_home, team_lines),
        "away": _ou_table(lam_away, team_lines),
    }


def _with_odds(market: Dict[str, object]) -> Dict[str, object]:
    """Wrap every {over, under} probability leaf with its fair odds."""
    out = {k: v for k, v in market.items() if k.startswith("lambda") or k == "ref_factor"}
    for side in ("total", "home", "away"):
        out[side] = {
            line: {sel: {"prob": p, "fair_odds": fair_odds(p)} for sel, p in legs.items()}
            for line, legs in market[side].items()
        }
    return out


def secondary_markets(
    home_corner_for: float,
    home_corner_against: float,
    away_corner_for: float,
    away_corner_against: float,
    home_card_rate: float,
    away_card_rate: float,
    referee_cpg: float = None,
    league_ref_avg: float = DEFAULT_LEAGUE_REF_AVG,
) -> Dict[str, object]:
    """Corners + cards markets as ``{prob, fair_odds}`` records, from manual rates."""
    corners = _with_odds(
        corners_markets(home_corner_for, home_corner_against, away_corner_for, away_corner_against)
    )
    cards = _with_odds(
        cards_markets(home_card_rate, away_card_rate, referee_cpg, league_ref_avg)
    )
    return {"corners": corners, "cards": cards}


# --- CLI ----------------------------------------------------------------------

# representative defaults so the CLI runs with no rate inputs
_DEFAULT_RATES = dict(
    home_corner_for=6.2, home_corner_against=4.1,
    away_corner_for=4.6, away_corner_against=5.3,
    home_card_rate=1.9, away_card_rate=2.2,
)


def _fmt_block(block: Dict[str, object], title: str, unit: str) -> str:
    lines = [f"{title}  (expected {block['lambda_total']:.1f} {unit}: "
             f"{block['lambda_home']:.1f} home / {block['lambda_away']:.1f} away)"]
    for line, legs in block["total"].items():
        o, u = legs["over"], legs["under"]
        lines.append(
            f"  total Over {line}: {o['prob']*100:4.1f}% (fair {o['fair_odds']:.2f})"
            f"   Under: {u['prob']*100:4.1f}%"
        )
    return "\n".join(lines)


def format_counts(out: Dict[str, object], home: str, away: str) -> str:
    return (
        f"{home} vs {away} — count props\n\n"
        + _fmt_block(out["corners"], "Corners", "corners") + "\n\n"
        + _fmt_block(out["cards"], "Cards", "cards")
    )


def main(argv: Sequence[str] = ()) -> int:
    """CLI: `python -m jackpot.counts [HOME AWAY] [--ref CARDS_PER_GAME]`."""
    args = list(argv)
    referee_cpg = None
    if "--ref" in args:
        i = args.index("--ref")
        try:
            referee_cpg = float(args[i + 1])
        except (IndexError, ValueError):
            print("error: --ref needs a number (referee cards per game)")
            return 1
        del args[i:i + 2]
    home = args[0] if len(args) >= 1 else "Home"
    away = args[1] if len(args) >= 2 else "Away"
    out = secondary_markets(referee_cpg=referee_cpg, **_DEFAULT_RATES)
    print(format_counts(out, home, away))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
