from datetime import datetime

import pytest

from spraywait.weather.types import Level, Reading

NOW = datetime(2026, 11, 15, 18, 30)


def make_reading(lo, hi, ts=NOW):
    """lo/hi are (temp_f, wind_mph, wind_dir_deg) at 5 ft and 30 ft."""
    return Reading(ts, [Level(5, *lo), Level(30, *hi)], source="test")


@pytest.fixture
def now():
    return NOW
