from datetime import datetime

from spraywait.checks.flag import Flag, Severity
from spraywait.pesticides.db import Pesticide
from spraywait.weather.types import Level, Reading

EDGE_MARGIN_MPH = 1.0
SHEAR_SPEED_CAUTION_MPH = 5.0
SHEAR_SPEED_STOP_MPH = 8.0
SHEAR_DIR_CAUTION_DEG = 45.0
SHEAR_DIR_STOP_DEG = 90.0
MIN_SPEED_FOR_DIRECTION_MPH = 1.0


def _speed_flags(lv: Level, lo: float, hi: float) -> list[Flag]:
    at = f"{lv.wind_mph:.1f} mph at {lv.height_ft:g} ft"
    if lv.wind_mph < lo:
        return [Flag(Severity.STOP, "wind_speed",
                     f"Wind too calm ({at}, label minimum {lo:g} mph). "
                     "Calm air often means an inversion; droplets hang and drift unpredictably.",
                     70 + 5 * (lo - lv.wind_mph))]
    if lv.wind_mph > hi:
        return [Flag(Severity.STOP, "wind_speed",
                     f"Wind too strong ({at}, label maximum {hi:g} mph). Droplets will be carried off target.",
                     70 + 5 * (lv.wind_mph - hi))]
    if lv.wind_mph < lo + EDGE_MARGIN_MPH:
        return [Flag(Severity.CAUTION, "wind_speed", f"Wind near the calm limit ({at}, minimum {lo:g} mph).")]
    if lv.wind_mph > hi - EDGE_MARGIN_MPH:
        return [Flag(Severity.CAUTION, "wind_speed", f"Wind near the upper limit ({at}, maximum {hi:g} mph).")]
    return []


def check_wind_speed(reading: Reading, pesticide: Pesticide, now: datetime | None = None) -> list[Flag]:
    flags: list[Flag] = []
    for lv in reading.sorted_levels():
        flags.extend(_speed_flags(lv, pesticide.min_wind_mph, pesticide.max_wind_mph))
    return flags


def direction_difference(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def check_wind_shear(reading: Reading, pesticide: Pesticide, now: datetime | None = None) -> list[Flag]:
    if len(reading.levels) < 2:
        return []
    lo, hi = reading.lowest, reading.highest
    flags: list[Flag] = []

    speed_diff = hi.wind_mph - lo.wind_mph
    desc = f"({lo.wind_mph:.1f} mph at {lo.height_ft:g} ft, {hi.wind_mph:.1f} mph at {hi.height_ft:g} ft)"
    if speed_diff >= SHEAR_SPEED_STOP_MPH:
        flags.append(Flag(Severity.STOP, "wind_shear",
                          f"Wind aloft is {speed_diff:.1f} mph stronger than at the ground {desc}. "
                          "Ground conditions do not reflect the air the spray will rise into.",
                          70 + 5 * (speed_diff - SHEAR_SPEED_STOP_MPH)))
    elif speed_diff >= SHEAR_SPEED_CAUTION_MPH:
        span = SHEAR_SPEED_STOP_MPH - SHEAR_SPEED_CAUTION_MPH
        flags.append(Flag(Severity.CAUTION, "wind_shear",
                          f"Wind aloft is {speed_diff:.1f} mph stronger than at the ground {desc}.",
                          30 + 30 * (speed_diff - SHEAR_SPEED_CAUTION_MPH) / span))

    both_dirs = lo.wind_dir_deg is not None and hi.wind_dir_deg is not None
    both_moving = min(lo.wind_mph, hi.wind_mph) >= MIN_SPEED_FOR_DIRECTION_MPH
    if both_dirs and both_moving:
        dir_diff = direction_difference(lo.wind_dir_deg, hi.wind_dir_deg)
        ddesc = f"({lo.wind_dir_deg:g} deg at {lo.height_ft:g} ft vs {hi.wind_dir_deg:g} deg at {hi.height_ft:g} ft)"
        if dir_diff >= SHEAR_DIR_STOP_DEG:
            flags.append(Flag(Severity.STOP, "wind_shear",
                              f"Wind direction differs by {dir_diff:.0f} deg between heights {ddesc}. "
                              "Spray can be carried in a direction the ground wind does not show.",
                              70 + 0.5 * (dir_diff - SHEAR_DIR_STOP_DEG)))
        elif dir_diff >= SHEAR_DIR_CAUTION_DEG:
            span = SHEAR_DIR_STOP_DEG - SHEAR_DIR_CAUTION_DEG
            flags.append(Flag(Severity.CAUTION, "wind_shear",
                              f"Wind direction differs by {dir_diff:.0f} deg between heights {ddesc}.",
                              30 + 30 * (dir_diff - SHEAR_DIR_CAUTION_DEG) / span))
    return flags
