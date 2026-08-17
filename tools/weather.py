from __future__ import annotations
import requests

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
_TIMEOUT = 8


def _geocode(location: str) -> tuple[float, float] | None:
    try:
        resp = requests.get(_GEOCODE_URL, params={"name": location, "count": 1}, timeout=_TIMEOUT)
        resp.raise_for_status()
        results = resp.json().get("results")
        if not results:
            return None
        return results[0]["latitude"], results[0]["longitude"]
    except Exception:
        return None


def get_weather(location: str) -> dict:
    """Return current weather and 7-day forecast for a location.

    Falls back to an empty dict on any error.
    """
    coords = _geocode(location)
    if not coords:
        return {}

    lat, lon = coords
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m"],
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"],
        "forecast_days": 7,
        "timezone": "auto",
    }
    try:
        resp = requests.get(_WEATHER_URL, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return {
            "location": location,
            "current": data.get("current", {}),
            "daily": data.get("daily", {}),
        }
    except Exception:
        return {}
