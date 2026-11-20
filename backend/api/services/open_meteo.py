
import hashlib
import logging
import math
import time

import requests
from django.conf import settings
from django.core.cache import cache

from .nasa_power import WeatherServiceError


logger = logging.getLogger(__name__)

# Fresh cache: 30 min — reduces how often we hit the free-tier API.
FRESH_CACHE_SECONDS = 30 * 60
# Stale cache: 48 h — kept as a fallback when the live request fails.
STALE_CACHE_SECONDS = 48 * 60 * 60

# Retry settings for transient failures (429, 5xx, network errors).
_MAX_RETRIES = 3
_RETRY_BACKOFF = [1, 3, 7]   # seconds to wait before each retry attempt


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


def _cached_weather(fresh_key, stale_key):
    fresh = cache.get(fresh_key)

    if fresh is not None:
        return fresh

    return cache.get(stale_key)


def fetch_current_weather(latitude, longitude):
    # Validate farm coordinates.
    try:
        lat = round(float(latitude), 4)
        lon = round(float(longitude), 4)
    except (TypeError, ValueError) as exc:
        raise ValueError("Valid farm coordinates are required.") from exc

    if (
        not math.isfinite(lat)
        or not -90 <= lat <= 90
        or not math.isfinite(lon)
        or not -180 <= lon <= 180
    ):
        raise ValueError(
            "Farm coordinates are outside valid latitude and longitude ranges."
        )

    # Create separate fresh and backup cache keys.
    coordinate_hash = hashlib.sha256(
        f"{lat}:{lon}".encode()
    ).hexdigest()

    fresh_key = f"open-meteo:fresh:{coordinate_hash}"
    stale_key = f"open-meteo:stale:{coordinate_hash}"

    # Return fresh cached weather without calling the external API.
    cached = cache.get(fresh_key)

    if cached is not None:
        return cached

    # Also serve a still-valid stale entry rather than hammering the API on
    # every request when the fresh key has simply expired.
    stale = cache.get(stale_key)

    # Request weather data from Open-Meteo, retrying on transient errors.
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,"
            "precipitation,weather_code,wind_speed_10m,"
            "wind_direction_10m,cloud_cover,is_day"
        ),
        "daily": (
            "weather_code,temperature_2m_max,temperature_2m_min,"
            "precipitation_sum,precipitation_probability_max,"
            "et0_fao_evapotranspiration"
        ),
        "forecast_days": 7,
        "timezone": "auto",
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
    }

    last_exc = None
    payload = None

    for attempt in range(_MAX_RETRIES):
        try:
            response = requests.get(
                settings.OPEN_METEO_BASE_URL,
                params=params,
                timeout=settings.OPEN_METEO_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
            break  # success — exit retry loop

        except requests.HTTPError as exc:
            last_exc = exc
            status_code = exc.response.status_code if exc.response is not None else None
            is_retryable = status_code in {429, 500, 502, 503, 504}

            logger.warning(
                "Open-Meteo HTTP %s on attempt %d/%d for %s, %s",
                status_code, attempt + 1, _MAX_RETRIES, lat, lon,
            )

            if is_retryable and attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_BACKOFF[attempt])
                continue

            # Non-retryable HTTP error or final attempt — fall through.
            break

        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                "Open-Meteo network error on attempt %d/%d for %s, %s: %s",
                attempt + 1, _MAX_RETRIES, lat, lon, exc,
            )
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_BACKOFF[attempt])
                continue
            break

    # All attempts exhausted without a valid payload.
    if payload is None:
        if stale is not None:
            logger.warning(
                "Returning stale cached weather for %s, %s after %d failed attempts",
                lat, lon, _MAX_RETRIES,
            )
            return stale

        exc = last_exc
        if isinstance(exc, requests.HTTPError):
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code == 429:
                raise WeatherServiceError(
                    "The weather provider is receiving too many requests. "
                    "Please try again later."
                ) from exc

        raise WeatherServiceError(
            "Open-Meteo is temporarily unavailable. Please try again later."
        ) from exc

    # Validate and process the response.
    try:
        if not isinstance(payload, dict):
            raise TypeError("Weather response is not a dictionary.")

        current = payload.get("current")
        daily = payload.get("daily")
        timezone_name = payload.get("timezone")

        if not isinstance(current, dict):
            raise TypeError("Current weather data is missing or invalid.")

        if not isinstance(daily, dict):
            raise TypeError("Daily weather data is missing or invalid.")

        if not isinstance(timezone_name, str):
            raise TypeError("Timezone information is missing.")

        if not isinstance(current.get("time"), str):
            raise TypeError("Current weather timestamp is missing.")

        forecast_dates = daily.get("time")

        if not isinstance(forecast_dates, list) or not forecast_dates:
            raise TypeError("Daily forecast dates are missing.")

        current_code = _weather_code(current.get("weather_code"))
        raw_is_day = _number(current.get("is_day"))

        current_weather = {
            "data_type": "modelled_current_conditions",
            "time": current["time"],
            "temperature_c": _number(current.get("temperature_2m")),
            "feels_like_c": _number(current.get("apparent_temperature")),
            "relative_humidity_pct": _number(
                current.get("relative_humidity_2m")
            ),
            "precipitation_mm": _number(current.get("precipitation")),
            "weather_code": current_code,
            "condition": WEATHER_CODES.get(
                current_code, "Conditions unavailable"
            ),
            "wind_speed_kmh": _number(current.get("wind_speed_10m")),
            "wind_direction_degrees": _number(
                current.get("wind_direction_10m")
            ),
            "cloud_cover_pct": _number(current.get("cloud_cover")),
            "is_day": (
                bool(raw_is_day)
                if raw_is_day in {0, 1}
                else None
            ),
        }

        forecast = []

        for index, forecast_date in enumerate(forecast_dates):
            if not isinstance(forecast_date, str):
                raise TypeError("Invalid forecast date.")

            code = _weather_code(
                _daily_number(daily, "weather_code", index)
            )

            forecast.append({
                "date": forecast_date,
                "weather_code": code,
                "condition": WEATHER_CODES.get(
                    code, "Conditions unavailable"
                ),
                "temperature_max_c": _daily_number(
                    daily, "temperature_2m_max", index
                ),
                "temperature_min_c": _daily_number(
                    daily, "temperature_2m_min", index
                ),
                "precipitation_sum_mm": _daily_number(
                    daily, "precipitation_sum", index
                ),
                "precipitation_probability_max_pct": _daily_number(
                    daily, "precipitation_probability_max", index
                ),
                "et0_mm": _daily_number(
                    daily, "et0_fao_evapotranspiration", index
                ),
            })

    except (KeyError, TypeError, ValueError) as exc:
        logger.exception(
            "Open-Meteo returned an unexpected data structure."
        )

        stale = cache.get(stale_key)
        if stale is not None:
            return stale

        raise WeatherServiceError(
            "Open-Meteo returned weather data in an unexpected format."
        ) from exc

    # Build the final weather response.
    result = {
        "source": "Open-Meteo",
        "attribution_url": "https://open-meteo.com/",
        "data_type": "modelled_current_conditions_and_forecast",
        "location": {
            "latitude": lat,
            "longitude": lon,
        },
        "timezone": timezone_name,
        "current": current_weather,
        "daily_forecast": forecast,
    }

    # Save fresh weather and a longer-lived backup.
    cache.set(fresh_key, result, FRESH_CACHE_SECONDS)
    cache.set(stale_key, result, STALE_CACHE_SECONDS)

    return result
