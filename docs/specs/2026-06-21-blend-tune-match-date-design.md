# Backtest Blend-Weight Tuning + Match-Date Weather (Phase 12)

**Date:** 2026-06-21
**Status:** Approved for build

---

## Two features

1. **Tune the model-vs-market blend weight** on real history, so "best weight" is
   data-backed instead of a heuristic.
2. **Match date** → fetch the **forecast** for the kickoff day, not just current weather.

---

## Feature 1 — blend-weight tuning

The blend (`final = w·model + (1-w)·market`) only matters when matches carry odds.
So the backtest must read odds from the CSV and replay them.

- `HistoricalMatch` gains optional `home_odds, draw_odds, away_odds`.
- `load_results_csv` parses bookmaker odds columns, trying common triples in order:
  `B365H/B365D/B365A` (Bet365), then `PSH/PSD/PSA` (Pinnacle), then `AvgH/AvgD/AvgA`.
  Missing/invalid odds → that match simply has no odds (blend has no effect for it).
- `run_backtest`: when a match has odds, set `MatchContext.market_odds` and pass the
  `blend_weight` param through to `predict()`.
- `tune` grid may include `blend_weight`; the CLI report prints the best weight.
- Odds-free data (e.g. the bundled sample season) still works — blend is just inert.

Result: `python -m jackpot.backtest results_with_odds.csv` reports the
RPS-minimising `blend_weight` for *your* leagues.

## Feature 2 — match-date weather

Open-Meteo's daily forecast gives a date's `wind_speed_10m_max` (km/h) and
`precipitation_sum` (mm) — already the model's units.

- `weather.py`: `parse_open_meteo_daily(payload)` → `(wind_kph, rain_mm)`.
  `fetch_open_meteo(lat, lon, date=None)` → current when `date` is None/today, else the
  daily forecast for `date` (start_date=end_date=date, `timezone=auto`).
  `fetch_weather_for_city(city, date=None)` threads the date through.
- `app.py`: a **"Match date"** date input (default today). The Auto weather fetch uses
  it, so a future kickoff gets that day's forecast. Out-of-range/past dates fall back
  to current with a caption note. Forecast horizon ~16 days.

## Out of scope
- Hourly kickoff-time precision (daily aggregate is enough).
- Historical-archive weather for past dates (predictions look forward).
- Persisting the chosen weight back into the app's default.

## Acceptance anchors (tests)
- `load_results_csv` parses B365/PS/Avg odds triples; skips a row with no/À-invalid
  odds (still loads the result); a fixture with odds yields populated odds.
- `run_backtest` with odds + `blend_weight=0` vs `1` produces **different** RPS
  (blend actually engages); odds-free data is unaffected by `blend_weight`.
- `tune` including `blend_weight` returns runs sorted by RPS; CLI report names the
  best weight.
- `parse_open_meteo_daily` extracts wind/rain from a daily fixture; raises on empty.
- `fetch_weather_for_city(date=...)` routes to the daily fetcher (injected seam).
- App: a "Match date" input renders; Auto weather still renders without network until
  a city is typed.
