from dataclasses import dataclass
from enum import IntEnum


class Severity(IntEnum):
    CAUTION = 1
    STOP = 2


@dataclass
class Flag:
    severity: Severity
    check: str
    reason: str

    def to_dict(self) -> dict:
        return {"severity": self.severity.name, "check": self.check, "reason": self.reason}
