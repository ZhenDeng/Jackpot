# Tasks — Backtesting & Calibration Harness (Phase 5)

Source of truth for this phase. Check a box only when implemented AND tests pass.

## Build

- [x] B1  `metrics.py` — log_loss, brier_score, ranked_probability_score (TDD)
- [x] B2  `data/results.py` — HistoricalMatch, load_results_csv, bundled sample season (TDD)
- [x] B3  `predict.py` — expose home_adv / rho / shrink_k overrides (TDD)
- [x] B4  `backtest.py` — walk-forward run_backtest + calibration + tune (TDD)
- [x] B5  `__main__`/CLI report + README backtest section; full suite green

## Done criteria
- All boxes checked
- `pytest` green (existing + new)
- No open CRITICAL/HIGH review findings
- `python -m jackpot.backtest` prints a metrics + calibration report
