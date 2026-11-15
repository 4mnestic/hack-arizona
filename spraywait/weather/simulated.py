from datetime import datetime, timedelta

from spraywait.weather.source import WeatherSource
from spraywait.weather.types import Level, Reading

# Each scenario is a short time series ending in the condition it is named for, and
# isolates one thing the tool does. Heights are 5 ft (ground station) and 30 ft (above the canopy).
# "illustrates" is a presenter's note for the demo page; "expect" is the outcome with the generic
# label, as (ground station alone, SprayWait). Tests hold the notes to the engine's actual output.
SCENARIOS: dict[str, dict] = {
    "evening_inversion": {
        "title": "Hidden inversion",
        "illustrates": (
            "A temperature inversion that a ground sensor alone can't detect. Wind is a steady "
            "5-6 mph from the same direction at both heights, so the 5 ft station sees nothing wrong. "
            "Only the 30 ft sensor shows the air above is 4\u00b0F warmer: the air has stopped mixing "
            "and spray will be trapped near the ground."
        ),
        "expect": ("GO", "STOP"),
        "steps": [
            [(5, 64.0, 5.5, 300), (30, 63.2, 6.0, 300)],
            [(5, 61.5, 5.0, 300), (30, 61.4, 6.0, 305)],
            [(5, 59.0, 5.0, 300), (30, 60.5, 6.0, 305)],
            [(5, 57.0, 5.0, 300), (30, 61.0, 6.0, 305)],
        ],
    },
    "inversion_forming": {
        "title": "Inversion forming",
        "illustrates": (
            "Early warning. Both heights read almost the same temperature, so the air has stopped "
            "mixing upward; on a clear evening an inversion usually follows. The ground station says GO; "
            "SprayWait says CAUTION before it becomes a STOP."
        ),
        "expect": ("GO", "CAUTION"),
        "steps": [
            [(5, 66.0, 5.5, 300), (30, 65.0, 6.0, 300)],
            [(5, 62.0, 5.0, 300), (30, 61.8, 5.5, 300)],
        ],
    },
    "shear_aloft": {
        "title": "Strong wind above the canopy",
        "illustrates": (
            "Wind speed changing with height. A gentle 4.5 mph breeze at the ground, but 12 mph above "
            "the trees, over the 10 mph limit, where the airblast plume reaches it. The direction is the "
            "same at both heights, so this is speed alone."
        ),
        "expect": ("GO", "STOP"),
        "steps": [
            [(5, 66.0, 4.5, 270), (30, 64.8, 12.0, 275)],
        ],
    },
    "wind_direction_shift": {
        "title": "Wind turning with height",
        "illustrates": (
            "Wind direction changing with height. Speeds are moderate at both heights, but above the "
            "canopy the wind blows from 120\u00b0 away from the ground wind. Spray can be carried toward "
            "a neighbor that the ground wind suggests is safe."
        ),
        "expect": ("GO", "STOP"),
        "steps": [
            [(5, 66.0, 5.0, 180), (30, 64.8, 6.0, 300)],
        ],
    },
    "clear_midday": {
        "title": "Good spraying conditions",
        "illustrates": (
            "The control case: air cooling with height (mixing normally) and a moderate wind from one "
            "direction. Both agree on GO; the extra sensor doesn't add false alarms."
        ),
        "expect": ("GO", "GO"),
        "steps": [
            [(5, 70.0, 5.0, 300), (30, 68.6, 6.0, 305)],
            [(5, 72.0, 5.5, 300), (30, 70.5, 6.0, 300)],
        ],
    },
    "hot_afternoon": {
        "title": "Hot afternoon",
        "illustrates": (
            "Pesticide-specific limits. At 96\u00b0F the weather is fine for the generic label, so both "
            "say GO. Switch the pesticide to Malathion (90\u00b0F label limit, moderately volatile) and "
            "SprayWait says STOP. A weather station knows nothing about the product."
        ),
        "expect": ("GO", "GO"),
        "steps": [
            [(5, 96.0, 6.0, 310), (30, 94.0, 7.0, 310)],
        ],
    },
    "too_windy": {
        "title": "Too windy",
        "illustrates": (
            "A case a single station already catches: wind over the common 10 mph limit at both "
            "heights. Both say STOP; SprayWait keeps the standard checks."
        ),
        "expect": ("STOP", "STOP"),
        "steps": [
            [(5, 68.0, 9.0, 280), (30, 66.5, 12.0, 285)],
            [(5, 68.0, 12.0, 280), (30, 66.0, 15.0, 285)],
        ],
    },
    "dead_calm": {
        "title": "Dead calm",
        "illustrates": (
            "Wind below the common 3 mph minimum at both heights. Both say STOP: droplets hang in "
            "still air and drift unpredictably, and calm air often comes with an inversion."
        ),
        "expect": ("STOP", "STOP"),
        "steps": [
            [(5, 60.0, 1.0, 90), (30, 59.5, 1.5, 100)],
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
