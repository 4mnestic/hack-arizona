from datetime import datetime

from spraywait.weather.source import WeatherSource
from spraywait.weather.types import Reading


class FarmStationStore:
    """Holds the latest reading pushed by the farm's own weather station."""

    def __init__(self):
        self.latest: Reading | None = None

    def push(self, reading: Reading) -> None:
        if self.latest is None or reading.timestamp >= self.latest.timestamp:
            self.latest = reading


class FarmSource(WeatherSource):
    """Live data from the farm. With no reading yet, returns an empty one (the checks then say STOP)."""

    name = "farm"

    def __init__(self, store: FarmStationStore):
        self.store = store

    def get_reading(self) -> Reading:
        return self.store.latest or Reading(datetime.now(), [], source="farm (no data yet)")
