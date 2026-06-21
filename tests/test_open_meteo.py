import math

import pytest

from jackpot.data.weather import (
    parse_geocode,
    parse_open_meteo,
    fetch_weather_for_city,
)


# ---- parse_geocode ----

def test_parse_geocode_extracts_location():
    payload = {
        "results": [
            {"name": "London", "country": "United Kingdom",
             "latitude": 51.50853, "longitude": -0.12574}
        ]
    }
    loc = parse_geocode(payload)
    assert loc["name"] == "London"
    assert loc["country"] == "United Kingdom"
    assert math.isclose(loc["lat"], 51.50853, rel_tol=1e-9)
    assert math.isclose(loc["lon"], -0.12574, rel_tol=1e-9)


def test_parse_geocode_no_results_raises():
    with pytest.raises(ValueError):
        parse_geocode({"results": []})
    with pytest.raises(ValueError):
        parse_geocode({})


def test_parse_geocode_missing_coords_raises_valueerror():
    # a result with no centroid must raise ValueError, not a raw KeyError
    with pytest.raises(ValueError):
        parse_geocode({"results": [{"name": "Nowhere", "country": "X"}]})


# ---- parse_open_meteo ----

def test_parse_open_meteo_extracts_wind_and_rain():
    payload = {
        "current_units": {"wind_speed_10m": "km/h", "precipitation": "mm"},
        "current": {"wind_speed_10m": 12.4, "precipitation": 0.3},
    }
    wind_kph, rain_mm = parse_open_meteo(payload)
    assert math.isclose(wind_kph, 12.4, rel_tol=1e-9)
    assert math.isclose(rain_mm, 0.3, rel_tol=1e-9)


def test_parse_open_meteo_missing_fields_default_to_zero():
    wind_kph, rain_mm = parse_open_meteo({"current": {}})
    assert wind_kph == 0.0 and rain_mm == 0.0


def test_parse_open_meteo_null_values_treated_as_calm():
    # API may report null when a reading is unavailable -> conservative 0.0
    wind_kph, rain_mm = parse_open_meteo(
        {"current": {"wind_speed_10m": None, "precipitation": None}}
    )
    assert wind_kph == 0.0 and rain_mm == 0.0


def test_parse_open_meteo_missing_current_raises():
    with pytest.raises(ValueError):
        parse_open_meteo({})


# ---- fetch_weather_for_city (composition via injectable seams) ----

def test_fetch_weather_for_city_composes_geocode_and_weather():
    geo = {"results": [{"name": "Paris", "country": "France",
                        "latitude": 48.85, "longitude": 2.35}]}
    wx = {"current": {"wind_speed_10m": 20.0, "precipitation": 1.5}}
    geo_calls, wx_calls = [], []

    def fake_geo(name):
        geo_calls.append(name)
        return geo

    def fake_wx(lat, lon):
        wx_calls.append((lat, lon))
        return wx

    info = fetch_weather_for_city("Paris", _geocode_fetcher=fake_geo, _weather_fetcher=fake_wx)
    assert info["name"] == "Paris"
    assert info["country"] == "France"
    assert math.isclose(info["wind_kph"], 20.0, rel_tol=1e-9)
    assert math.isclose(info["rain_mm"], 1.5, rel_tol=1e-9)
    assert math.isclose(info["lat"], 48.85, rel_tol=1e-9)
    # the seam forwards the city to geocode, and the geocoded coords to weather
    assert geo_calls == ["Paris"]
    assert wx_calls == [(48.85, 2.35)]
