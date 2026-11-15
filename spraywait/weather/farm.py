from datetime import datetime, timedelta

from spraywait.weather.source import WeatherSource
from spraywait.weather.types import Reading


class FarmStationStore:
    """Holds readings pushed by the farm's own weather station: the latest, plus recent history."""

    def __init__(self, keep: timedelta = timedelta(hours=24)):
        self.latest: Reading | None = None
        self.keep = keep
        self._history: dict[datetime, Reading] = {}

    def push(self, reading: Reading) -> None:
        if self.latest is None or reading.timestamp >= self.latest.timestamp:
            self.latest = reading
        self._history[reading.timestamp] = reading  # a resent timestamp replaces the old one
        cutoff = self.latest.timestamp - self.keep
        self._history = {t: r for t, r in self._history.items() if t >= cutoff}

    def history(self) -> list[Reading]:
        """Stored readings, oldest first."""
        return [self._history[t] for t in sorted(self._history)]


class FarmSource(WeatherSource):
    """Live data from the farm. With no reading yet, returns an empty one (the checks then say STOP)."""

    name = "farm"

    def __init__(self, store: FarmStationStore):
        self.store = store

    def get_reading(self) -> Reading:
        return self.store.latest or Reading(datetime.now(), [], source="farm (no data yet)")
