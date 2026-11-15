"""Public forecast-model weather (Open-Meteo, free, no key). Demo use only; real farms supply their own data."""

import json
from datetime import datetime
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
        # The model has no 10 m temperature, so the ground level pairs 2 m temp with 10 m wind.
        levels = [
            Level(round(2 * M_TO_FT, 1), cur["temperature_2m"], cur["wind_speed_10m"], cur["wind_direction_10m"]),
            Level(round(80 * M_TO_FT), cur["temperature_80m"], cur["wind_speed_80m"], cur["wind_direction_80m"]),
        ]
        # "current" is the model's now-cast, so stamp it with fetch time.
        return Reading(datetime.now(), levels, source=self.name)
