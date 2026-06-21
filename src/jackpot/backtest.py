"""Walk-forward backtesting: replay history, score predictions, calibrate, tune.

For each match (processed chronologically) a team's form is computed from **only
its prior matches**, so no prediction can see its own or any future result. This
makes the evaluation leakage-free — the single most important property of an
honest backtest.
"""
from __future__ import annotations

import itertools
import sys
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from .data.base import TeamForm, MatchContext, MatchData
from .data.results import HistoricalMatch, load_results_csv, sample_season, normalize_date
from .metrics import log_loss, brier_score, ranked_probability_score
from .predict import predict

_N_BUCKETS = 5  # calibration reliability buckets over [0, 1]
_DEFAULT_LEAGUE_AVG = 1.3  # prior used until the league has produced some goals


@dataclass
class BacktestResult:
    n_scored: int
    avg_rps: float
    avg_log_loss: float
    avg_brier: float
    accuracy: float
    calibration: List[dict]


def outcome_index(home_goals: int, away_goals: int) -> int:
    """1X2 outcome as an index: 0 home win, 1 draw, 2 away win."""
    if home_goals > away_goals:
        return 0
    if home_goals == away_goals:
        return 1
    return 2


def _mean(pairs: List[Tuple[int, int]], which: int) -> float:
    return sum(p[which] for p in pairs) / len(pairs)


def _calibration(records: List[Tuple[List[float], int]]) -> List[dict]:
    """Reliability of the home-win probability vs. the realised home-win rate."""
    buckets = []
    for b in range(_N_BUCKETS):
        lo, hi = b / _N_BUCKETS, (b + 1) / _N_BUCKETS
        last = b == _N_BUCKETS - 1
        chosen = []
        for probs, oi in records:
            p = min(1.0, max(0.0, probs[0]))  # clamp guards float overshoot
            if (lo <= p < hi) or (last and p == hi):
                chosen.append((p, oi))
        n = len(chosen)
        mean_pred = (sum(p for p, _ in chosen) / n) if n else None
        actual = (sum(1 for _, oi in chosen if oi == 0) / n) if n else None
        buckets.append(
            {"lo": lo, "hi": hi, "n": n, "mean_pred": mean_pred, "actual_freq": actual}
        )
    return buckets


def run_backtest(
    matches: Sequence[HistoricalMatch],
    min_history: int = 4,
    **params,
) -> BacktestResult:
    """Replay ``matches`` chronologically and score the 1X2 prediction of each.

    ``params`` (home_adv / rho / shrink_k / blend_weight) are passed to predict().
    A match is scored only once both teams have at least ``min_history`` priors.
    """
    history: Dict[str, List[Tuple[int, int]]] = {}  # team -> [(scored, conceded)]
    league_goals = 0
    league_games = 0
    records: List[Tuple[List[float], int]] = []

    # enforce chronological order regardless of input ordering (walk-forward)
    ordered = sorted(matches, key=lambda mt: normalize_date(mt.date))

    for m in ordered:
        h_hist = history.get(m.home, [])
        a_hist = history.get(m.away, [])
        # fall back to a prior until the league has actually produced goals,
        # so a goalless opening round doesn't silently suppress predictions
        league_avg = (league_goals / (league_games * 2)) if league_goals else _DEFAULT_LEAGUE_AVG

        if len(h_hist) >= min_history and len(a_hist) >= min_history:
            home = TeamForm(m.home, _mean(h_hist, 0), _mean(h_hist, 1), len(h_hist), False)
            away = TeamForm(m.away, _mean(a_hist, 0), _mean(a_hist, 1), len(a_hist), False)
            # attach the match's bookmaker odds so blend_weight can actually engage
            odds = None
            if m.home_odds is not None and m.draw_odds is not None and m.away_odds is not None:
                odds = {"home": m.home_odds, "draw": m.draw_odds, "away": m.away_odds}
            md = MatchData(home, away, MatchContext(league_avg_goals=league_avg, market_odds=odds))
            mr = predict(md, **params)["markets"]["match_result"]
            probs = [mr["home"]["prob"], mr["draw"]["prob"], mr["away"]["prob"]]
            records.append((probs, outcome_index(m.home_goals, m.away_goals)))

        # update history AFTER predicting — never let a match inform itself
        history.setdefault(m.home, []).append((m.home_goals, m.away_goals))
        history.setdefault(m.away, []).append((m.away_goals, m.home_goals))
        league_goals += m.home_goals + m.away_goals
        league_games += 1

    n = len(records)
    if n == 0:
        return BacktestResult(0, 0.0, 0.0, 0.0, 0.0, _calibration(records))

    avg_rps = sum(ranked_probability_score(p, o) for p, o in records) / n
    avg_ll = sum(log_loss(p, o) for p, o in records) / n
    avg_brier = sum(brier_score(p, o) for p, o in records) / n
    accuracy = sum(1 for p, o in records if max(range(3), key=lambda i: p[i]) == o) / n
    return BacktestResult(n, avg_rps, avg_ll, avg_brier, accuracy, _calibration(records))


def tune(
    matches: Sequence[HistoricalMatch],
    grid: Dict[str, List[float]],
    min_history: int = 4,
) -> List[dict]:
    """Grid-search model weights; return ``[{params, result}]`` sorted by avg_rps."""
    keys = list(grid)
    runs = []
    for combo in itertools.product(*(grid[k] for k in keys)):
        params = dict(zip(keys, combo))
        runs.append({"params": params, "result": run_backtest(matches, min_history, **params)})
    runs.sort(key=lambda r: r["result"].avg_rps)
    return runs


# --- CLI report ---------------------------------------------------------------

_TUNE_GRID = {
    "home_adv": [1.1, 1.2, 1.3, 1.4],
    "rho": [-0.1, -0.05, 0.0],
    "shrink_k": [3.0, 5.0, 8.0],
}

# model-vs-market blend weights to add to the grid when the data carries odds
_BLEND_WEIGHTS = [0.0, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0]


def has_odds(matches) -> bool:
    """True if any match carries a complete bookmaker odds triple."""
    return any(
        m.home_odds is not None and m.draw_odds is not None and m.away_odds is not None
        for m in matches
    )


def format_report(result: BacktestResult, label: str = "Backtest") -> str:
    """Render a metrics + calibration report as plain text."""
    lines = [
        f"== {label} ==",
        f"matches scored : {result.n_scored}",
        f"avg RPS        : {result.avg_rps:.4f}   (lower better; ~0.222 = coin flip)",
        f"avg log-loss   : {result.avg_log_loss:.4f}",
        f"avg Brier      : {result.avg_brier:.4f}",
        f"accuracy (top) : {result.accuracy:.1%}",
        "",
        "calibration (home-win prob vs actual):",
        f"  {'bucket':<10}{'n':>5}{'pred':>9}{'actual':>9}",
    ]
    for b in result.calibration:
        bucket = f"{b['lo']:.1f}-{b['hi']:.1f}"
        pred = "    —" if b["mean_pred"] is None else f"{b['mean_pred']:>9.2f}"
        actual = "    —" if b["actual_freq"] is None else f"{b['actual_freq']:>9.2f}"
        lines.append(f"  {bucket:<10}{b['n']:>5}{pred}{actual}")
    return "\n".join(lines)


def main(argv: Sequence[str] = ()) -> int:
    """Run a backtest report. Optional first arg: path to a results CSV."""
    if argv:
        with open(argv[0], encoding="utf-8") as fh:
            matches = load_results_csv(fh.read())
        source = argv[0]
    else:
        matches = sample_season()
        source = "bundled sample season"

    baseline = run_backtest(matches)
    odds_present = has_odds(matches)
    print(f"Source: {source}  ({len(matches)} matches, "
          f"odds: {'yes' if odds_present else 'no'})\n")
    print(format_report(baseline, "Default weights"))

    grid = dict(_TUNE_GRID)
    if odds_present:
        grid["blend_weight"] = _BLEND_WEIGHTS   # tune model-vs-market only with odds
    runs = tune(matches, grid)
    best = runs[0]
    print("\n" + format_report(best["result"], "Best tuned weights"))
    print(f"\nbest params: {best['params']}  "
          f"(RPS {best['result'].avg_rps:.4f} vs default {baseline.avg_rps:.4f})")
    if odds_present:
        print(f"best model-vs-market blend weight: {best['params'].get('blend_weight')}")
    else:
        print("(add a CSV with bookmaker odds columns to tune the blend weight)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
