from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from django.conf import settings
from django.core.cache import cache


WEATHER_CACHE_KEY = "analytics:weather:current"


def get_current_weather(location_override=None):
    provider = getattr(settings, "WEATHER_PROVIDER", "stub").lower()
    cache_key = _build_cache_key(location_override)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if provider == "open_meteo":
        weather = _fetch_open_meteo(location_override)
    else:
        weather = _stub_weather(location_override)

    if weather is None:
        return None

    ttl = int(getattr(settings, "WEATHER_CACHE_TTL", 900))
    cache.set(cache_key, weather, ttl)
    return weather


def _stub_weather(location_override=None):
    location_name = _resolve_location_name(location_override)
    return {
        "status": "stub",
        "temperature_c": float(getattr(settings, "WEATHER_STUB_TEMPERATURE_C", 21.0)),
        "precipitation_mm": float(getattr(settings, "WEATHER_STUB_PRECIP_MM", 0.0)),
        "condition": getattr(settings, "WEATHER_STUB_CONDITION", "sunny"),
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "location": {
            "name": location_name,
            "lat": _safe_float((location_override or {}).get("lat")),
            "lon": _safe_float((location_override or {}).get("lon")),
        },
        "source": "stub",
    }


def _fetch_open_meteo(location_override=None):
    lat = (location_override or {}).get("lat", getattr(settings, "WEATHER_LAT", None))
    lon = (location_override or {}).get("lon", getattr(settings, "WEATHER_LON", None))
    if lat in (None, "") or lon in (None, ""):
        return None

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,precipitation,weather_code",
        "timezone": "UTC",
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None

    current = payload.get("current") or {}
    weather_code = current.get("weather_code")
    condition = _map_weather_code(weather_code)

    return {
        "status": "ok",
        "temperature_c": _safe_float(current.get("temperature_2m")),
        "precipitation_mm": _safe_float(current.get("precipitation")),
        "condition": condition,
        "observed_at": current.get("time") or datetime.now(timezone.utc).isoformat(),
        "location": {
            "name": _resolve_location_name(location_override),
            "lat": _safe_float(lat),
            "lon": _safe_float(lon),
        },
        "source": "open-meteo",
    }


def _safe_float(value):
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _build_cache_key(location_override):
    if not location_override:
        return WEATHER_CACHE_KEY
    lat = _safe_float(location_override.get("lat"))
    lon = _safe_float(location_override.get("lon"))
    if lat is None or lon is None:
        return WEATHER_CACHE_KEY
    return f"{WEATHER_CACHE_KEY}:{round(lat, 2)}:{round(lon, 2)}"


def _resolve_location_name(location_override):
    if location_override and location_override.get("name"):
        return location_override["name"]
    return getattr(settings, "WEATHER_LOCATION_NAME", "Unknown")


def _map_weather_code(code):
    if code is None:
        return "unknown"
    try:
        code = int(code)
    except (TypeError, ValueError):
        return "unknown"

    if code == 0:
        return "sunny"
    if code in (1, 2, 3):
        return "cloudy"
    if code in (45, 48):
        return "fog"
    if code in (51, 53, 55, 56, 57):
        return "drizzle"
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (95, 96, 99):
        return "storm"
    return "unknown"
