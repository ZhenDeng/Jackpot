"""Weather -> goal-expectancy adjustment + free Open-Meteo auto-fetch (no API key).

Heavy wind and rain modestly suppress scoring. The adjustment is deliberately
**bounded** (never below 0.8) so a single context factor can't dominate the model.

Open-Meteo (public-apis weather list) is free, key-less, and already reports wind in
km/h and precipitation in mm — exactly ``weather_adjustment``'s inputs.
"""
from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple

WIND_THRESHOLD_KPH = 20.0   # below this, wind is irrelevant
MIN_ADJUST = 0.8            # floor: weather alone never cuts goals by >20%

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def weather_adjustment(wind_kph: float = 0.0, rain_mm: float = 0.0) -> float:
    """Return a multiplier in [MIN_ADJUST, 1.0] applied to both teams' lambda."""
    penalty = 0.0
    if wind_kph > WIND_THRESHOLD_KPH:
        penalty += 0.0015 * (wind_kph - WIND_THRESHOLD_KPH)  # ~0.0015 per kph over
    if rain_mm > 0:
        penalty += 0.005 * rain_mm                            # ~0.5% per mm
    return max(MIN_ADJUST, 1.0 - penalty)


def fetch_weather_adjustment(
    lat: float,
    lon: float,
    api_key: str,
    when_unix: Optional[int] = None,
) -> float:
    """Fetch kickoff weather from OpenWeatherMap and convert to an adjustment.

    Network call — not exercised by the test suite. Falls back to neutral (1.0)
    on any error so a weather hiccup never breaks a prediction.
    """
    try:
        import requests  # imported lazily so the engine stays dependency-free

        resp = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        wind_kph = float(data.get("wind", {}).get("speed", 0.0)) * 3.6  # m/s -> kph
        rain_mm = float(data.get("rain", {}).get("1h", 0.0))
        return weather_adjustment(wind_kph=wind_kph, rain_mm=rain_mm)
    except Exception:
        return 1.0


# ---- Open-Meteo (free, no API key) -------------------------------------------

def parse_geocode(payload: Dict) -> Dict[str, object]:
    """Pull the first match from an Open-Meteo geocoding response."""
    results = payload.get("results") or []
    if not results:
        raise ValueError("no location found")
    top = results[0]
    lat, lon = top.get("latitude"), top.get("longitude")
    if lat is None or lon is None:
        raise ValueError("geocoding result missing coordinates")
    return {
        "name": top.get("name", ""),
        "country": top.get("country", ""),
        "lat": float(lat),
        "lon": float(lon),
    }


def parse_open_meteo(payload: Dict) -> Tuple[float, float]:
    """Pull (wind_kph, rain_mm) from an Open-Meteo current-weather response.

    Open-Meteo reports wind in km/h and precipitation in mm by default, so no unit
    conversion is needed. A null/missing reading is treated as 0.0 (calm/dry) — a
    conservative default that can only soften the weather penalty, never inflate it.
    """
    current = payload.get("current")
    if current is None:
        raise ValueError("no current weather in response")
    wind_kph = float(current.get("wind_speed_10m") or 0.0)
    rain_mm = float(current.get("precipitation") or 0.0)
    return wind_kph, rain_mm


def _http_json(url: str, params: Dict) -> Dict:
    import requests  # lazy import keeps the engine dependency-free

    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def parse_open_meteo_daily(payload: Dict) -> Tuple[float, float]:
    """Pull (wind_kph, rain_mm) from an Open-Meteo *daily forecast* response.

    Uses the day's max wind and total precipitation (already km/h and mm). Null/missing
    readings default to 0.0 (calm/dry) — conservative, can only soften the penalty.
    """
    daily = payload.get("daily") or {}
    winds = daily.get("wind_speed_10m_max")
    rains = daily.get("precipitation_sum")
    if not winds or not rains:
        raise ValueError("no daily forecast in response")
    return float(winds[0] or 0.0), float(rains[0] or 0.0)


def geocode_city(name: str) -> Dict:
    return _http_json(_GEOCODE_URL, {"name": name, "count": 1})


def fetch_open_meteo(lat: float, lon: float, date: Optional[str] = None) -> Dict:
    """Current weather (``date`` None) or the daily forecast for an ISO ``date``."""
    if date:
        return _http_json(_FORECAST_URL, {
            "latitude": lat, "longitude": lon,
            "daily": "wind_speed_10m_max,precipitation_sum",
            "start_date": date, "end_date": date, "timezone": "auto",
        })
    return _http_json(
        _FORECAST_URL,
        {"latitude": lat, "longitude": lon, "current": "wind_speed_10m,precipitation"},
    )


def fetch_weather_for_city(
    city: str,
    date: Optional[str] = None,
    _geocode_fetcher: Callable[[str], Dict] = geocode_city,
    _weather_fetcher: Callable[..., Dict] = fetch_open_meteo,
) -> Dict[str, object]:
    """Geocode ``city`` then fetch weather → a single info dict.

    With ``date`` (ISO), uses that day's forecast; otherwise current conditions. The
    fetchers are injectable so composition is unit-testable without network.
    """
    loc = parse_geocode(_geocode_fetcher(city))
    payload = _weather_fetcher(loc["lat"], loc["lon"], date)
    wind_kph, rain_mm = parse_open_meteo_daily(payload) if date else parse_open_meteo(payload)
    return {**loc, "wind_kph": wind_kph, "rain_mm": rain_mm}
