"""Weather for a named place from Open-Meteo (free, no key). Open-Meteo receives
the place name, the coordinates it resolves to (for the forecast), and the Mac's IP address.

The model's argument is hostile input: it is validated here, and the one sentence the
model hears is built from validated numbers and a fixed word table, never from raw
provider text. Failures return fixed strings, never exception text. The audit log holds
the tool name and ok or error only (REQ-14).
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

from . import posix_files

# Same file and format as the other tools' audit logs.
AUDIT_LOG = Path.home() / ".super-agent" / "tool-audit.log"

# Not the default opener: it would honour a system proxy and send the place name there.
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: object, **kwargs: object) -> None:
        return None  # a redirect becomes an error before any second request is made


_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SECONDS = 5.0
MAX_BYTES = 64 * 1024

NAMES = frozenset({"get_weather"})
TOOLS = [{"type": "function", "function": {
    "name": "get_weather",
    "description": "Get the current weather and today's forecast for a named place.",
    "parameters": {"type": "object", "required": ["place"], "properties": {
        "place": {"type": "string", "description": "A city or town, for example Lisbon or Paris, France."}}}}}]

BAD_ARGS = "error: give a place name of 1 to 60 letters, digits, spaces, commas, dots, apostrophes or hyphens."
NOT_FOUND = "error: I could not find that place."
FAILED = "error: the weather service did not answer. Say so."
NO_TOOL = "error: no such tool."

_PLACE = re.compile(r"(?:[^\W_]|[ ,.'-]){1,60}")
# WMO weather interpretation codes, grouped to a few spoken words.
_SKY = {0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast", 45: "foggy", 48: "foggy",
        51: "drizzly", 53: "drizzly", 55: "drizzly", 56: "icy drizzle", 57: "icy drizzle",
        61: "rainy", 63: "rainy", 65: "heavily rainy", 66: "icy rain", 67: "icy rain",
        71: "snowy", 73: "snowy", 75: "heavily snowy", 77: "snowy", 80: "showery", 81: "showery",
        82: "stormy showers", 85: "snowy", 86: "snowy", 95: "stormy", 96: "stormy", 99: "stormy"}


def enabled() -> bool:
    choice = os.environ.get("SUPER_AGENT_WEATHER", "off")
    if choice not in ("on", "off"):
        raise RuntimeError("SUPER_AGENT_WEATHER must be 'on' or 'off'")
    return choice == "on"


def _get(url: str) -> object:
    """One blocking HTTPS GET with a size cap. Module level so tests replace it; nothing real is fetched."""
    if not url.startswith("https://"):
        raise ValueError("https only")
    with _DIRECT.open(urllib.request.Request(url, headers={"Accept": "application/json"}),
                      timeout=TIMEOUT_SECONDS) as response:
        body = response.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise ValueError("response too large")
    return json.loads(body)


def _number(value: object, low: float, high: float) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError("bad number")
    return float(value)


def _first(values: object, low: float, high: float) -> float | None:
    """First entry of a daily list; None when the service had no value (rain chance can be null)."""
    if not isinstance(values, list) or not values:
        raise ValueError("bad list")
    return None if values[0] is None else _number(values[0], low, high)


def _lookup(place: str) -> str:
    found = _get(f"{GEOCODE_URL}?name={urllib.parse.quote(place)}&count=1&language=en&format=json")
    if not isinstance(found, dict):
        raise ValueError("bad geocode")
    results = found.get("results")
    if results is None:  # the service leaves the key out when nothing matches
        return NOT_FOUND
    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
        raise ValueError("bad geocode")
    top = results[0]
    latitude, longitude = _number(top.get("latitude"), -90, 90), _number(top.get("longitude"), -180, 180)
    name = place  # the user's own words, already checked; never text chosen by the service
    forecast = _get(
        f"{FORECAST_URL}?latitude={latitude:.4f}&longitude={longitude:.4f}"
        "&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        "&timezone=auto&forecast_days=2")
    current, daily = forecast["current"], forecast["daily"]  # a missing key is a KeyError: FAILED
    temp = _number(current["temperature_2m"], -90, 60)
    feels = _number(current["apparent_temperature"], -120, 80)
    wind = _number(current["wind_speed_10m"], 0, 500)
    sky = _SKY.get(current["weather_code"]) if type(current["weather_code"]) is int else None
    high, low = _first(daily["temperature_2m_max"], -90, 60), _first(daily["temperature_2m_min"], -90, 60)
    rain = _first(daily["precipitation_probability_max"], 0, 100)
    if high is None or low is None:
        raise ValueError("no daily range")
    text = (f"In {name} it is {temp:.0f} degrees Celsius and {sky or 'unsettled'}, feels like {feels:.0f}, "
            f"wind {wind:.0f} kilometres an hour. Today's high is {high:.0f} and the low is {low:.0f}")
    return text + (f", with a {rain:.0f} percent chance of rain." if rain is not None else ".")


async def run(name: object, arguments: object) -> str:
    """The only code a weather model call can reach. The lookup runs in a thread, off the event loop."""
    if not isinstance(name, str) or name not in NAMES:
        return NO_TOOL
    place = arguments.get("place") if isinstance(arguments, dict) and arguments.keys() == {"place"} else None
    place = " ".join(place.split()) if isinstance(place, str) else ""
    if not _PLACE.fullmatch(place) or not any(c.isalnum() for c in place):
        _audit("error")
        return BAD_ARGS  # refused before any request leaves the machine
    try:
        # to_thread alone cannot be cancelled mid-request, so the wait is bounded here too.
        # shortcut: wait_for abandons the worker thread, which runs on until its socket timeout (TIMEOUT_SECONDS per read), upgrade to an async HTTP client if abandoned threads ever pile up.
        result = await asyncio.wait_for(asyncio.to_thread(_lookup, place), TIMEOUT_SECONDS * 3)
    except Exception:  # network, timeout, bad JSON, bad numbers: one fixed answer
        result = FAILED
    _audit("error" if result.startswith("error") else "ok")
    return result


def _audit(outcome: str) -> None:
    """Appends time, tool name, and outcome. Never the place or the answer (REQ-14)."""
    posix_files.append_audit(AUDIT_LOG, posix_files.audit_line("get_weather", outcome))
