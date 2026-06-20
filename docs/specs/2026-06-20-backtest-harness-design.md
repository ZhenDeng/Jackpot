# Backtesting & Calibration Harness (Phase 5)

**Date:** 2026-06-20
**Status:** Approved for build
**Builds on:** the engine + props phases.

---

## Why

So far the model produces plausible-looking numbers, but nothing has measured
whether they're *right*. This phase adds the harness that:

1. **Scores** predictions against real outcomes with proper scoring rules.
2. **Replays** history with a strict **walk-forward** (no future leakage).
3. **Calibrates** — checks that "30% events" actually happen ~30% of the time.
4. **Tunes** the weights currently hardcoded (home advantage, ρ, shrinkage, blend).

This is what turns "reasonable" into "calibrated".

## Components

### `metrics.py` — proper scoring rules (pure)
- `log_loss(probs, outcome_index)` — penalises confident wrong calls.
- `brier_score(probs, outcome_index)` — squared error vs the one-hot outcome.
- `ranked_probability_score(probs, outcome_index)` — **RPS**, the standard for
  ordered 1X2 outcomes (draw sits "between" home and away). Lower is better.

### `data/results.py` — historical match data
- `HistoricalMatch(date, league, home, away, home_goals, away_goals)`.
- `load_results_csv(text)` — parses the common football-data.co.uk format
  (`Date,HomeTeam,AwayTeam,FTHG,FTAG`) into `HistoricalMatch`es.
- A small bundled **sample season** so the harness runs offline / in tests.

### `backtest.py` — walk-forward runner
- Processes matches **chronologically**. For each match it computes each team's
  form from **only its prior matches** (rolling goals scored/conceded), builds a
  `MatchData`, predicts, and scores the 1X2 result. No match sees its own or any
  future result — leakage-free by construction.
- `run_backtest(matches, min_history=4, **params) -> BacktestResult`.
- `BacktestResult`: `n_scored`, `avg_rps`, `avg_log_loss`, `avg_brier`,
  `accuracy` (top pick correct), `calibration` (predicted vs actual frequency
  buckets).

### Tuning
- Expose `home_adv`, `rho`, `shrink_k` as optional overrides on `predict()`
  (already plumbed in the lower layers; just thread them through).
- `tune(matches, grid)` — grid-search params, return runs sorted by `avg_rps`.

### CLI
- `python -m jackpot.backtest` — runs the bundled sample season (or a CSV path
  argument), prints a metrics + calibration report and the best tuned params.

## Out of scope
- Per-market backtesting beyond 1X2 (BTTS/OU scoring is a later extension).
- Bayesian/optimiser tuning (grid search is enough to demonstrate the loop).
- Fetching real history over the network (CSV loader + manual download covers it).

## Acceptance anchors (tests)
- log_loss/brier/RPS match known hand-computed values; a perfect prediction
  scores 0 on Brier/RPS; RPS penalises an "away" miss more when mass was on "home"
  than on "draw" (ordering matters).
- Walk-forward: a match is scored only after both teams have `min_history`
  priors; no match's own result feeds its own prediction.
- A team that has been winning is favoured in its next prediction.
- `BacktestResult` metrics are in sane ranges; accuracy in [0,1].
- `load_results_csv` parses the football-data.co.uk columns; bad rows skipped.
- `tune` returns the grid sorted by avg_rps; the best is no worse than the default.
