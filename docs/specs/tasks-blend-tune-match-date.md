# Tasks — Blend-Weight Tuning + Match-Date Weather (Phase 12)

Source of truth for this phase. Check a box only when implemented AND tests pass.

## Build

- [ ] D1  `data/results.py` — HistoricalMatch odds fields + load_results_csv odds parse (TDD)
- [ ] D2  `backtest.py` — run_backtest applies per-match odds + blend_weight; tune/CLI surface best weight (TDD)
- [ ] D3  `data/weather.py` — parse_open_meteo_daily + dated fetch_open_meteo/fetch_weather_for_city (TDD)
- [ ] D4  `app.py` — "Match date" input; Auto weather uses the date's forecast (AppTest)
- [ ] D5  README (backtest odds + match-date weather); roadmap; full suite green

## Done criteria
- All boxes checked
- `pytest` green (existing + new)
- No open CRITICAL/HIGH review findings
- Backtest tunes blend_weight on an odds CSV; app fetches weather for a chosen date
