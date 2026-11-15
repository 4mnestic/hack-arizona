from datetime import datetime

from spraywait.checks.flag import Flag, Severity
from spraywait.pesticides.db import Pesticide
from spraywait.weather.types import Reading

# Air normally cools ~0.3F per 100 ft going up; over 25 ft that is ~0.1F.
# So a difference near zero already means mixing has stopped.
NEAR_NEUTRAL_F = 0.5
STRONG_INVERSION_F = 2.0


def check_inversion(reading: Reading, pesticide: Pesticide, now: datetime | None = None) -> list[Flag]:
    if len(reading.levels) < 2:
        return []
    lo, hi = reading.lowest, reading.highest
    delta = hi.temp_f - lo.temp_f
    where = f"({hi.temp_f:.1f}F at {hi.height_ft:g} ft vs {lo.temp_f:.1f}F at {lo.height_ft:g} ft)"

    if delta >= STRONG_INVERSION_F:
        return [Flag(Severity.STOP, "inversion",
                     f"Strong temperature inversion: air aloft is {delta:.1f}F warmer than at the ground {where}. "
                     "Spray will be trapped in a shallow layer and can drift long distances.")]
    if delta > 0:
        return [Flag(Severity.STOP, "inversion",
                     f"Temperature inversion: air aloft is {delta:.1f}F warmer than at the ground {where}. "
                     "Air is not mixing upward, so fine droplets and vapor can travel sideways.")]
    if delta > -NEAR_NEUTRAL_F:
        return [Flag(Severity.CAUTION, "inversion",
                     f"Temperature nearly the same at both heights {where}. "
                     "Little vertical mixing; an inversion may be forming.")]
    return []
