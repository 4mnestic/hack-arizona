"""Public forecast-model weather (Open-Meteo, free, no key).

Current conditions are a demo-only stand-in for a farm station; the hourly forecast plans spray windows.
"""

import json
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import urlopen

from spraywait.weather.source import WeatherSource
from spraywait.weather.types import Level, Reading

URL = "https://api.open-meteo.com/v1/forecast"
FIELDS = ["temperature_2m", "temperature_80m", "wind_speed_10m", "wind_speed_80m",
          "wind_direction_10m", "wind_direction_80m"]
M_TO_FT = 3.28084


class PublicSource(WeatherSource):
    """Current modelled conditions near the ground (2 m temp, 10 m wind) and aloft (80 m)."""

    name = "public:open-meteo"

    def __init__(self, lat: float, lon: float, timeout: float = 8.0):
        self.lat, self.lon, self.timeout = lat, lon, timeout

    def get_reading(self) -> Reading:
        query = urlencode({
            "latitude": self.lat, "longitude": self.lon, "current": ",".join(FIELDS),
            "temperature_unit": "fahrenheit", "wind_speed_unit": "mph",
        })
        with urlopen(f"{URL}?{query}", timeout=self.timeout) as res:
            cur = json.load(res)["current"]
        # "current" is the model's now-cast, so stamp it with fetch time.
        return Reading(datetime.now(), _levels(lambda f: cur[f]), source=self.name)


def _levels(get) -> list[Level]:
    """Ground and 80 m levels. The model has no 10 m temperature, so the ground pairs 2 m temp with 10 m wind."""
    return [
        Level(round(2 * M_TO_FT, 1), get("temperature_2m"), get("wind_speed_10m"), get("wind_direction_10m")),
        Level(round(80 * M_TO_FT), get("temperature_80m"), get("wind_speed_80m"), get("wind_direction_80m")),
    ]


def forecast_url(lat: float, lon: float, hours: int = 24) -> str:
    """Open-Meteo hourly forecast URL (UTC times). Fetched by the browser, which isn't behind a shared host IP."""
    return f"{URL}?" + urlencode({
        "latitude": lat, "longitude": lon, "hourly": ",".join(FIELDS), "forecast_hours": hours,
        "temperature_unit": "fahrenheit", "wind_speed_unit": "mph", "timezone": "GMT",
    })


def parse_hourly(hourly: dict, max_hours: int = 48) -> list[Reading]:
    """Open-Meteo `hourly` block -> one Reading per hour. Hours with missing model values are skipped.

    Raises ValueError for malformed data.
    """
    try:
        times = hourly["time"][:max_hours]
        out = []
        for i, t in enumerate(times):
            if any(hourly[f][i] is None for f in FIELDS):
                continue
            # Engine times are naive server-local.
            ts = datetime.fromisoformat(t).replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
            levels = _levels(lambda f: float(hourly[f][i]))
            out.append(Reading(ts, levels, source="forecast:open-meteo"))
        return out
    except (KeyError, IndexError, TypeError, ValueError) as e:
        raise ValueError(f"bad forecast data: {e!r}") from None
