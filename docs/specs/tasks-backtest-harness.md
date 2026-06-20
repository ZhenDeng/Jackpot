# Tasks — Backtesting & Calibration Harness (Phase 5)

Source of truth for this phase. Check a box only when implemented AND tests pass.

## Build

- [ ] B1  `metrics.py` — log_loss, brier_score, ranked_probability_score (TDD)
- [ ] B2  `data/results.py` — HistoricalMatch, load_results_csv, bundled sample season (TDD)
- [ ] B3  `predict.py` — expose home_adv / rho / shrink_k overrides (TDD)
- [ ] B4  `backtest.py` — walk-forward run_backtest + calibration + tune (TDD)
- [ ] B5  `__main__`/CLI report + README backtest section; full suite green

## Done criteria
- All boxes checked
- `pytest` green (existing + new)
- No open CRITICAL/HIGH review findings
- `python -m jackpot.backtest` prints a metrics + calibration report
