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
from .data.results import HistoricalMatch, load_results_csv, sample_season
from .metrics import log_loss, brier_score, ranked_probability_score
from .predict import predict

_N_BUCKETS = 5  # calibration reliability buckets over [0, 1]


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
        chosen = [
            (probs[0], oi) for probs, oi in records
            if (lo <= probs[0] < hi) or (b == _N_BUCKETS - 1 and probs[0] == 1.0)
        ]
        n = len(chosen)
        mean_pred = sum(p for p, _ in chosen) / n if n else 0.0
        actual = sum(1 for _, oi in chosen if oi == 0) / n if n else 0.0
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

    for m in matches:
        h_hist = history.get(m.home, [])
        a_hist = history.get(m.away, [])
        league_avg = league_goals / (league_games * 2) if league_games else 0.0

        if len(h_hist) >= min_history and len(a_hist) >= min_history and league_avg > 0:
            home = TeamForm(m.home, _mean(h_hist, 0), _mean(h_hist, 1), len(h_hist), False)
            away = TeamForm(m.away, _mean(a_hist, 0), _mean(a_hist, 1), len(a_hist), False)
            md = MatchData(home, away, MatchContext(league_avg_goals=league_avg))
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

_TUNE_GRID = {"home_adv": [1.1, 1.2, 1.3, 1.4], "rho": [-0.1, -0.05, 0.0]}


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
        f"  {'bucket':<12}{'n':>5}{'pred':>9}{'actual':>9}",
    ]
    for b in result.calibration:
        lines.append(
            f"  {b['lo']:.1f}-{b['hi']:.1f}      {b['n']:>5}"
            f"{b['mean_pred']:>9.2f}{b['actual_freq']:>9.2f}"
        )
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
    print(f"Source: {source}  ({len(matches)} matches)\n")
    print(format_report(baseline, "Default weights"))

    runs = tune(matches, _TUNE_GRID)
    best = runs[0]
    print("\n" + format_report(best["result"], "Best tuned weights"))
    print(f"\nbest params: {best['params']}  "
          f"(RPS {best['result'].avg_rps:.4f} vs default {baseline.avg_rps:.4f})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
