from abc import ABC, abstractmethod

from spraywait.weather.types import Reading


class WeatherSource(ABC):
    """Anything that can produce a multi-height Reading: simulator, sensor tower, web API."""

    name: str = "unknown"

    @abstractmethod
    def get_reading(self) -> Reading:
        """Return the most recent reading."""
