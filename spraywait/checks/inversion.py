from datetime import datetime

from spraywait.checks.flag import Flag, Severity
from spraywait.pesticides.db import Pesticide
from spraywait.weather.types import Reading

# Air normally cools ~0.3F per 100 ft going up; over 25 ft that is ~0.1F.
# So a difference near zero already means mixing has stopped.
NEAR_NEUTRAL_F = 0.5
FORMING_F = 1.0
MODERATE_INVERSION_F = 1.0
STRONG_INVERSION_F = 2.0

# Source: UC ANR, "Surface Inversions Cause Spray Drift". Radiation inversions form 3-4 h before
# sunset and fade about an hour after sunrise, unless wind stays above 7 mph all night (the page
# writes "7 m/h", read here as mph). We have no sun times yet, so the window is a fixed
# year-round superset of that rule (sunset 17:00-20:00, sunrise 5:30-7:30); it only adds caution.
LIGHT_WIND_MPH = 7.0
PRONE_FROM_HOUR = 14
PRONE_UNTIL_HOUR = 9
# The temperature cutoffs above (0.5F, 1F, 2F) have no source yet; the page gives no numbers.


def _is_prone_hour(ts: datetime) -> bool:
    return ts.hour >= PRONE_FROM_HOUR or ts.hour < PRONE_UNTIL_HOUR


def _context(prone: bool, ground_wind: float) -> str:
    """Why the time of day and ground wind make an inversion more likely to persist."""
    parts = []
    if prone:
        parts.append("it is late afternoon through early morning, when surface inversions form and persist")
    if ground_wind < LIGHT_WIND_MPH:
        parts.append(f"ground wind is light ({ground_wind:.1f} mph), so the layer is unlikely to mix out")
    return f" Also, {' and '.join(parts)}." if parts else ""


def check_inversion(reading: Reading, pesticide: Pesticide, now: datetime | None = None) -> list[Flag]:
    """Time of day can only add caution; it never relaxes a result, because the clock may not match the farm's."""
    if len(reading.levels) < 2:
        return []
    lo, hi = reading.lowest, reading.highest
    delta = hi.temp_f - lo.temp_f
    where = f"({hi.temp_f:.1f}F at {hi.height_ft:g} ft vs {lo.temp_f:.1f}F at {lo.height_ft:g} ft)"
    prone = _is_prone_hour(reading.timestamp)
    light_wind = lo.wind_mph < LIGHT_WIND_MPH

    if delta > 0:
        if delta >= STRONG_INVERSION_F:
            strength, effect = "Strong", "Spray will be trapped in a shallow layer and can drift long distances."
        else:
            strength = "Moderate" if delta >= MODERATE_INVERSION_F else "Weak"
            effect = "Air is not mixing upward, so fine droplets and vapor can travel sideways."
        return [Flag(Severity.STOP, "inversion",
                     f"{strength} temperature inversion: air aloft is {delta:.1f}F warmer than at the ground "
                     f"{where}. {effect}{_context(prone, lo.wind_mph)}")]

    if delta > -NEAR_NEUTRAL_F:
        if not light_wind:
            return []  # near-equal temperatures with moving air is a mixed layer, not an inversion
        return [Flag(Severity.CAUTION, "inversion",
                     f"Temperature nearly the same at both heights {where}. "
                     f"Little vertical mixing; an inversion may be forming.{_context(prone, lo.wind_mph)}")]

    if delta > -FORMING_F and prone and light_wind:
        return [Flag(Severity.CAUTION, "inversion",
                     f"Air aloft is only {-delta:.1f}F cooler than at the ground {where}, a weaker drop than "
                     f"normal.{_context(prone, lo.wind_mph)} Conditions favor an inversion forming.")]
    return []
