"""Weather -> goal-expectancy adjustment, plus an OpenWeatherMap fetch helper.

Heavy wind and rain modestly suppress scoring. The adjustment is deliberately
**bounded** (never below 0.8) so a single context factor can't dominate the model.
"""
from __future__ import annotations

from typing import Optional

WIND_THRESHOLD_KPH = 20.0   # below this, wind is irrelevant
MIN_ADJUST = 0.8            # floor: weather alone never cuts goals by >20%


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
