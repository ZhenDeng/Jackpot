# Tasks — Auto Weather via Open-Meteo (Phase 11)

Source of truth for this phase. Check a box only when implemented AND tests pass.

## Build

- [x] W1  `weather.py` — parse_geocode + parse_open_meteo (pure, TDD) + network wrappers
         geocode_city/fetch_open_meteo/fetch_weather_for_city
- [x] W2  `app.py` — weather panel source selector (Off / Auto Open-Meteo / Manual);
         Auto fetches by city (cached) → weather_mult (AppTest)
- [x] W3  README weather/auto section; roadmap update; full suite green

## Done criteria
- All boxes checked
- `pytest` green (existing + new)
- No open CRITICAL/HIGH review findings
- App offers Auto (Open-Meteo) weather by city; Manual still works
