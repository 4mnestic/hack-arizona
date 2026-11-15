from datetime import datetime, timedelta

from spraywait.weather.source import WeatherSource
from spraywait.weather.types import Level, Reading

# Each scenario is a short time series ending in the condition it is named for.
# Heights are 5 ft (ground station height) and 30 ft (above the canopy).
SCENARIOS: dict[str, dict] = {
    "evening_inversion": {
        "title": "Evening inversion (demo)",
        "description": (
            "Sunset in a Central Valley almond orchard. The ground station reads a "
            "light breeze and mild temperature - looks fine. Above the canopy it is "
            "warmer and the wind is stronger and from a different direction: a "
            "surface inversion with shear. Spray would pool and drift sideways."
        ),
        "steps": [
            [(5, 64.0, 5.0, 300), (30, 63.2, 6.0, 305)],
            [(5, 61.0, 4.0, 290), (30, 61.0, 6.5, 290)],
            [(5, 58.5, 4.5, 200), (30, 60.5, 7.5, 250)],
            [(5, 57.0, 4.5, 180), (30, 61.0, 8.0, 250)],
        ],
    },
    "clear_midday": {
        "title": "Clear midday",
        "description": "Sunny, well-mixed air, steady moderate wind at both heights.",
        "steps": [
            [(5, 70.0, 5.0, 300), (30, 68.6, 6.0, 305)],
            [(5, 72.0, 5.5, 300), (30, 70.5, 6.0, 300)],
        ],
    },
    "too_windy": {
        "title": "Too windy",
        "description": "Afternoon wind above the common 10 mph limit at both heights.",
        "steps": [
            [(5, 68.0, 9.0, 280), (30, 66.5, 12.0, 285)],
            [(5, 68.0, 12.0, 280), (30, 66.0, 15.0, 285)],
        ],
    },
    "dead_calm": {
        "title": "Dead calm",
        "description": "Almost no wind at either height; droplets will hang and drift unpredictably.",
        "steps": [
            [(5, 60.0, 1.0, 90), (30, 59.5, 1.5, 100)],
        ],
    },
    "shear_aloft": {
        "title": "Calm below, strong wind aloft",
        "description": (
            "Ground station reads a gentle breeze. Above the trees the wind is over "
            "10 mph and blowing a different direction - a single station misses it."
        ),
        "steps": [
            [(5, 66.0, 4.0, 180), (30, 65.0, 11.0, 300)],
        ],
    },
    "hot_afternoon": {
        "title": "Hot afternoon",
        "description": "Well-mixed but very hot; volatile products can vaporize and drift later.",
        "steps": [
            [(5, 96.0, 6.0, 310), (30, 94.0, 7.0, 310)],
        ],
    },
}

STEP_MINUTES = 20


def _build(scenario: str, now: datetime | None = None) -> list[Reading]:
    spec = SCENARIOS[scenario]
    steps = spec["steps"]
    end = now or datetime.now()
    readings = []
    for i, step in enumerate(steps):
        ts = end - timedelta(minutes=STEP_MINUTES * (len(steps) - 1 - i))
        levels = [Level(h, t, w, d) for (h, t, w, d) in step]
        readings.append(Reading(ts, levels, source=f"simulated:{scenario}"))
    return readings


class SimulatedSource(WeatherSource):
    """Plays back a scripted scenario. get_reading() returns the latest step."""

    def __init__(self, scenario: str = "evening_inversion", now: datetime | None = None):
        if scenario not in SCENARIOS:
            raise KeyError(f"unknown scenario {scenario!r}; choose from {list(SCENARIOS)}")
        self.scenario = scenario
        self.name = f"simulated:{scenario}"
        self._readings = _build(scenario, now)

    def readings(self) -> list[Reading]:
        return list(self._readings)

    def get_reading(self) -> Reading:
        return self._readings[-1]
