from datetime import datetime

from spraywait.checks.flag import Flag, Severity
from spraywait.pesticides.db import Pesticide
from spraywait.weather.types import Reading

HIGH_VOL_CAUTION_F = 75.0
HIGH_VOL_STOP_F = 85.0
MODERATE_VOL_CAUTION_F = 85.0
FINE_DROPLET_WIND_CAUTION_MPH = 7.0


def check_volatility(reading: Reading, pesticide: Pesticide, now: datetime | None = None) -> list[Flag]:
    if not reading.levels:
        return []
    flags: list[Flag] = []
    temp = reading.lowest.temp_f
    name = pesticide.name

    if pesticide.max_temp_f is not None and temp > pesticide.max_temp_f:
        flags.append(Flag(Severity.STOP, "label_temperature",
                          f"{temp:.0f}F is above the {pesticide.max_temp_f:g}F label limit for {name}."))

    if pesticide.volatility == "high":
        if temp >= HIGH_VOL_STOP_F:
            flags.append(Flag(Severity.STOP, "volatility",
                              f"{name} is highly volatile and it is {temp:.0f}F. "
                              "Vapor can keep drifting for hours after application."))
        elif temp >= HIGH_VOL_CAUTION_F:
            flags.append(Flag(Severity.CAUTION, "volatility",
                              f"{name} is highly volatile; at {temp:.0f}F expect some vapor drift after spraying."))
    elif pesticide.volatility == "moderate" and temp >= MODERATE_VOL_CAUTION_F:
        flags.append(Flag(Severity.CAUTION, "volatility",
                          f"{name} has moderate volatility; at {temp:.0f}F vapor loss increases."))

    if pesticide.droplet_size == "fine":
        windiest = max(lv.wind_mph for lv in reading.levels)
        if windiest >= FINE_DROPLET_WIND_CAUTION_MPH:
            flags.append(Flag(Severity.CAUTION, "droplet_size",
                              f"{name} is applied as fine droplets{' through ' + pesticide.nozzle if pesticide.nozzle else ''}; at {windiest:.0f} mph they drift more easily."))
    return flags
