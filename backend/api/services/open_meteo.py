import hashlib
import math

import requests
from django.conf import settings
from django.core.cache import cache

from .nasa_power import WeatherServiceError


WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, 1) if math.isfinite(number) else None


def _weather_code(value):
    number = _number(value)
    return int(number) if number is not None and number.is_integer() else None


def _daily_number(daily, key, index):
    values = daily.get(key)
    if not isinstance(values, list) or index >= len(values):
        return None
    return _number(values[index])


def fetch_current_weather(latitude, longitude):
    try:
        lat, lon = round(float(latitude), 4), round(float(longitude), 4)
    except (TypeError, ValueError) as exc:
        raise ValueError("Valid farm coordinates are required.") from exc
    if not math.isfinite(lat) or not -90 <= lat <= 90 or not math.isfinite(lon) or not -180 <= lon <= 180:
        raise ValueError("Farm coordinates are outside valid latitude and longitude ranges.")

    cache_key = "open-meteo:" + hashlib.sha256(f"{lat}:{lon}".encode()).hexdigest()
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            settings.OPEN_METEO_BASE_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": (
                    "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,"
                    "weather_code,wind_speed_10m,wind_direction_10m,cloud_cover,is_day"
                ),
                "daily": (
                    "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
                    "precipitation_probability_max,et0_fao_evapotranspiration"
                ),
                "forecast_days": 7,
                "timezone": "auto",
                "temperature_unit": "celsius",
                "wind_speed_unit": "kmh",
                "precipitation_unit": "mm",
            },
            timeout=settings.OPEN_METEO_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise WeatherServiceError("Open-Meteo is temporarily unavailable. Please try again later.") from exc

    try:
        current = payload["current"]
        daily = payload["daily"]
        timezone_name = payload["timezone"]
        if not isinstance(current, dict) or not isinstance(daily, dict) or not isinstance(timezone_name, str):
            raise TypeError("Unexpected response types.")
        if not isinstance(current.get("time"), str) or not isinstance(daily.get("time"), list):
            raise TypeError("Missing current or daily weather data.")

        current_code = _weather_code(current.get("weather_code"))
        raw_is_day = _number(current.get("is_day"))
        current_weather = {
            "data_type": "modelled_current_conditions",
            "time": current["time"],
            "temperature_c": _number(current.get("temperature_2m")),
            "feels_like_c": _number(current.get("apparent_temperature")),
            "relative_humidity_pct": _number(current.get("relative_humidity_2m")),
            "precipitation_mm": _number(current.get("precipitation")),
            "weather_code": current_code,
            "condition": WEATHER_CODES.get(current_code, "Conditions unavailable"),
            "wind_speed_kmh": _number(current.get("wind_speed_10m")),
            "wind_direction_degrees": _number(current.get("wind_direction_10m")),
            "cloud_cover_pct": _number(current.get("cloud_cover")),
            "is_day": bool(raw_is_day) if raw_is_day in {0, 1} else None,
        }

        forecast = []
        for index, forecast_date in enumerate(daily["time"]):
            if not isinstance(forecast_date, str):
                raise TypeError("Invalid forecast date.")
            code = _weather_code(_daily_number(daily, "weather_code", index))
            forecast.append({
                "date": forecast_date,
                "weather_code": code,
                "condition": WEATHER_CODES.get(code, "Conditions unavailable"),
                "temperature_max_c": _daily_number(daily, "temperature_2m_max", index),
                "temperature_min_c": _daily_number(daily, "temperature_2m_min", index),
                "precipitation_sum_mm": _daily_number(daily, "precipitation_sum", index),
                "precipitation_probability_max_pct": _daily_number(daily, "precipitation_probability_max", index),
                "et0_mm": _daily_number(daily, "et0_fao_evapotranspiration", index),
            })
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherServiceError("Open-Meteo returned weather data in an unexpected format.") from exc

    result = {
        "source": "Open-Meteo",
        "attribution_url": "https://open-meteo.com/",
        "data_type": "modelled_current_conditions_and_forecast",
        "location": {"latitude": lat, "longitude": lon},
        "timezone": timezone_name,
        "current": current_weather,
        "daily_forecast": forecast,
    }
    cache.set(cache_key, result, 15 * 60)
    return result
