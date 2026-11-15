from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from spraywait.checks import Flag, Severity, check_volatility, check_wind_speed, run_all_checks
from spraywait.pesticides.db import DEFAULT_PESTICIDE, Pesticide
from spraywait.weather.types import Reading


class Status(str, Enum):
    GO = "GO"
    CAUTION = "CAUTION"
    STOP = "STOP"


@dataclass
class Decision:
    status: Status
    reasons: list[str]
    flags: list[Flag] = field(default_factory=list)
    timestamp: datetime | None = None
    pesticide: str = ""

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "reasons": self.reasons,
            "flags": [f.to_dict() for f in self.flags],
            "pesticide": self.pesticide,
        }


def _combine(flags: list[Flag], reading: Reading, pesticide: Pesticide, ok_reason: str) -> Decision:
    flags = sorted(flags, key=lambda f: -f.severity)
    if any(f.severity == Severity.STOP for f in flags):
        status = Status.STOP
    elif flags:
        status = Status.CAUTION
    else:
        status = Status.GO
    reasons = [f.reason for f in flags] or [ok_reason]
    return Decision(status, reasons, flags, reading.timestamp, pesticide.name)


def decide(reading: Reading, pesticide: Pesticide = DEFAULT_PESTICIDE, now: datetime | None = None) -> Decision:
    """Full multi-height assessment. The most severe flag sets the status; every reason is reported."""
    return _combine(
        run_all_checks(reading, pesticide, now), reading, pesticide,
        "Air is mixing, wind is within label limits at every height, and no shear detected.",
    )


def single_station_decision(reading: Reading, pesticide: Pesticide = DEFAULT_PESTICIDE) -> Decision:
    """What a basic ground-level station would conclude from its one height alone (for comparison)."""
    ground = Reading(reading.timestamp, [reading.lowest], source=reading.source)
    flags = check_wind_speed(ground, pesticide) + check_volatility(ground, pesticide)
    return _combine(flags, ground, pesticide,
                    f"Ground wind {ground.lowest.wind_mph:.1f} mph is within limits; temperature acceptable.")
