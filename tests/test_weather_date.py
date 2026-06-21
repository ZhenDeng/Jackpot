import math

import pytest

from jackpot.data.weather import parse_open_meteo_daily, fetch_weather_for_city


def test_parse_daily_extracts_wind_and_rain():
    payload = {
        "daily_units": {"wind_speed_10m_max": "km/h", "precipitation_sum": "mm"},
        "daily": {
            "time": ["2026-06-25"],
            "wind_speed_10m_max": [18.7],
            "precipitation_sum": [2.1],
        },
    }
    wind_kph, rain_mm = parse_open_meteo_daily(payload)
    assert math.isclose(wind_kph, 18.7, rel_tol=1e-9)
    assert math.isclose(rain_mm, 2.1, rel_tol=1e-9)


def test_parse_daily_missing_raises():
    with pytest.raises(ValueError):
        parse_open_meteo_daily({"daily": {"time": [], "wind_speed_10m_max": []}})
    with pytest.raises(ValueError):
        parse_open_meteo_daily({})


def test_fetch_weather_for_city_with_date_uses_daily_forecast():
    geo = {"results": [{"name": "London", "country": "UK", "latitude": 51.5, "longitude": -0.1}]}
    daily = {"daily": {"time": ["2026-06-25"], "wind_speed_10m_max": [30.0], "precipitation_sum": [5.0]}}
    seen = {}

    def fake_geo(name):
        return geo

    def fake_wx(lat, lon, date=None):
        seen["date"] = date
        return daily

    info = fetch_weather_for_city(
        "London", date="2026-06-25", _geocode_fetcher=fake_geo, _weather_fetcher=fake_wx,
    )
    assert seen["date"] == "2026-06-25"       # date threaded to the weather fetch
    assert math.isclose(info["wind_kph"], 30.0, rel_tol=1e-9)
    assert math.isclose(info["rain_mm"], 5.0, rel_tol=1e-9)


def test_fetch_weather_for_city_without_date_uses_current():
    geo = {"results": [{"name": "London", "country": "UK", "latitude": 51.5, "longitude": -0.1}]}
    current = {"current": {"wind_speed_10m": 8.0, "precipitation": 0.0}}

    def fake_wx(lat, lon, date=None):
        assert date is None
        return current

    info = fetch_weather_for_city(
        "London", _geocode_fetcher=lambda n: geo, _weather_fetcher=fake_wx,
    )
    assert math.isclose(info["wind_kph"], 8.0, rel_tol=1e-9)
