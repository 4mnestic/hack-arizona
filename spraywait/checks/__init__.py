from datetime import datetime

from spraywait.checks.flag import Flag, Severity
from spraywait.checks.data_quality import check_data_quality
from spraywait.checks.inversion import check_inversion
from spraywait.checks.volatility import check_volatility
from spraywait.checks.wind import check_wind_shear, check_wind_speed
from spraywait.pesticides.db import DEFAULT_PESTICIDE, Pesticide
from spraywait.weather.types import Reading

ALL_CHECKS = [
    check_data_quality,
    check_inversion,
    check_wind_speed,
    check_wind_shear,
    check_volatility,
]


def run_all_checks(
    reading: Reading,
    pesticide: Pesticide = DEFAULT_PESTICIDE,
    now: datetime | None = None,
) -> list[Flag]:
    flags: list[Flag] = []
    for check in ALL_CHECKS:
        flags.extend(check(reading, pesticide, now))
    return flags


__all__ = [
    "Flag",
    "Severity",
    "run_all_checks",
    "check_data_quality",
    "check_inversion",
    "check_wind_speed",
    "check_wind_shear",
    "check_volatility",
]
