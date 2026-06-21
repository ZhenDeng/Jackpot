import math

from jackpot.data.weather import weather_adjustment


# ---- weather adjustment ----

def test_weather_neutral_in_good_conditions():
    assert math.isclose(weather_adjustment(wind_kph=5, rain_mm=0), 1.0, rel_tol=1e-9)


def test_weather_reduces_goals_in_strong_wind_and_rain():
    bad = weather_adjustment(wind_kph=45, rain_mm=10)
    assert bad < 1.0


def test_weather_adjustment_is_bounded():
    # even in extreme weather we never wipe out scoring entirely
    extreme = weather_adjustment(wind_kph=120, rain_mm=80)
    assert 0.8 <= extreme <= 1.0
