from datetime import date, timedelta
import hashlib
import math

import requests
from django.conf import settings
from django.core.cache import cache


class WeatherServiceError(Exception):
    pass


PARAMETERS = {
    "PRECTOTCORR": ("Precipitation", "mm/day"),
    "T2M": ("Temperature", "°C"),
    "RH2M": ("Relative humidity", "%"),
    "ALLSKY_SFC_SW_DWN": ("Solar radiation", "kWh/m²/day"),
}
NASA_PARAMETERS = ",".join(PARAMETERS)


def fetch_daily_weather(latitude, longitude, start=None, end=None):
    today = date.today()
    start_date = date.fromisoformat(start) if start else today - timedelta(days=30)
    end_date = date.fromisoformat(end) if end else today - timedelta(days=1)
    if start_date > end_date:
        raise ValueError("Start date must be on or before end date.")
    if start_date < date(1981, 1, 1):
        raise ValueError("NASA POWER daily data starts in 1981.")
    if end_date >= today:
        raise ValueError("Historical observations must end before today; NASA POWER is not a forecast.")
    if (end_date - start_date).days > 3650:
        raise ValueError("Date range cannot exceed 10 years.")

    lat, lon = round(float(latitude), 4), round(float(longitude), 4)
    raw_key = f"power:{lat}:{lon}:{start_date:%Y%m%d}:{end_date:%Y%m%d}"
    cache_key = "power:" + hashlib.sha256(raw_key.encode()).hexdigest()
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            settings.NASA_POWER_BASE_URL,
            params={
                "parameters": NASA_PARAMETERS,
                "community": "AG",
                "longitude": lon,
                "latitude": lat,
                "start": start_date.strftime("%Y%m%d"),
                "end": end_date.strftime("%Y%m%d"),
                "format": "JSON",
            },
            timeout=settings.NASA_POWER_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise WeatherServiceError("NASA POWER is temporarily unavailable. Please try again later.") from exc

    try:
        properties = payload["properties"]
        parameter_data = properties["parameter"]
        dates = sorted(set().union(*(parameter_data.get(name, {}).keys() for name in PARAMETERS)))
        observations = []
        for day in dates:
            values = {}
            for name, (label, unit) in PARAMETERS.items():
                raw = parameter_data.get(name, {}).get(day)
                if raw is not None:
                    value = float(raw)
                else:
                    continue
                if math.isfinite(value) and value > -900:
                    values[name] = {"value": round(value, 2), "unit": unit, "label": label}
            if values:
                observations.append({"date": f"{day[:4]}-{day[4:6]}-{day[6:]}", "values": values})
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherServiceError("NASA POWER returned data in an unexpected format.") from exc

    result = {
        "source": "NASA POWER",
        "data_type": "historical_observations",
        "is_forecast": False,
        "location": {"latitude": lat, "longitude": lon},
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "observations": observations,
        "units": {name: unit for name, (_, unit) in PARAMETERS.items()},
    }
    cache.set(cache_key, result, 6 * 60 * 60)
    return result
