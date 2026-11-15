from datetime import datetime, timedelta

from spraywait.checks.flag import Flag, Severity
from spraywait.pesticides.db import Pesticide
from spraywait.weather.types import Reading

STALE_AFTER = timedelta(minutes=15)


def check_data_quality(reading: Reading, pesticide: Pesticide, now: datetime | None = None) -> list[Flag]:
    """Fail safe: missing or stale data can never produce GO."""
    if not reading.levels:
        return [Flag(Severity.STOP, "data", "No weather data available.", 100)]
    flags: list[Flag] = []
    if len({lv.height_ft for lv in reading.levels}) < 2:
        flags.append(Flag(Severity.CAUTION, "data",
                          "Only one measurement height. Cannot check for inversion or wind shear above the canopy."))
    age = (now or datetime.now()) - reading.timestamp
    if age > STALE_AFTER:
        flags.append(Flag(Severity.CAUTION, "data",
                          f"Weather data is {int(age.total_seconds() // 60)} minutes old. Conditions may have changed."))
    return flags
