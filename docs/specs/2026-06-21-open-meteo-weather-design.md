# Auto Weather via Open-Meteo (Phase 11)

**Date:** 2026-06-21
**Status:** Approved for build
**Builds on:** the existing `weather.py` (`weather_adjustment`) and the app's weather panel.

---

## Why

The weather factor is currently typed by hand. Open-Meteo (from the public-apis
weather list) is **free, no API key, HTTPS/CORS** — so we can auto-fetch real kickoff
weather from a **city name**. Its units already match the model: **wind in km/h,
precipitation in mm** — exactly `weather_adjustment(wind_kph, rain_mm)`, no conversion.

## Endpoints (no key)

- Geocoding: `https://geocoding-api.open-meteo.com/v1/search?name=<city>&count=1`
  → `results[0].{name,country,latitude,longitude}`
- Current weather:
  `https://api.open-meteo.com/v1/forecast?latitude=<lat>&longitude=<lon>&current=wind_speed_10m,precipitation`
  → `current.{wind_speed_10m,precipitation}` (km/h, mm)

## Design — extend `weather.py`

Pure parsers (unit-tested with fixture JSON) + thin network wrappers (best-effort):

```
parse_geocode(payload) -> {"name","country","lat","lon"}       # raises on no results
parse_open_meteo(payload) -> (wind_kph, rain_mm)               # raises on missing 'current'
geocode_city(name) -> {...}            # GET geocoding (network)
fetch_open_meteo(lat, lon) -> (wind_kph, rain_mm)              # GET forecast (network)
fetch_weather_for_city(city) -> {name, country, lat, lon, wind_kph, rain_mm}
```

Network failures don't break a prediction — the caller falls back to neutral weather.

## UI (`app.py`) — weather panel

Replace the "Apply kickoff weather" checkbox with a small **source selector**:

- **Off** (default) — no weather effect.
- **Auto (Open-Meteo, free)** — text input for the **match city**; the app geocodes +
  fetches current wind/rain (cached per city via `st.cache_data`) and shows
  "London, UK: wind 12 km/h, rain 0.3 mm → ×0.99". On any fetch error, warns and uses
  neutral.
- **Manual** — the existing wind/rain number inputs.

Whichever source, the result feeds the existing `weather_mult` → `compute_adjustments`,
so the rest of the pipeline is unchanged. Works in every prediction mode.

## Out of scope
- Forecast for a future kickoff time/date (current conditions only for v1).
- Caching beyond the per-session `st.cache_data` TTL.

## Acceptance anchors (tests)
- `parse_geocode`: extracts name/country/lat/lon from a sample; raises on empty results.
- `parse_open_meteo`: extracts wind_kph/rain_mm from a sample; raises on missing `current`.
- `fetch_weather_for_city` composes geocode→weather (tested with the parsers via a
  small seam; live network not unit-tested).
- App: Manual weather still works (existing); Auto mode renders a city input without
  forcing a network call at import (AppTest).
