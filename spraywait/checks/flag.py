from dataclasses import dataclass
from enum import IntEnum


class Severity(IntEnum):
    CAUTION = 1
    STOP = 2


# A flag's score is kept inside its severity's band so a score can never contradict a status.
SCORE_BANDS = {Severity.CAUTION: (20, 69), Severity.STOP: (70, 100)}
DEFAULT_SCORES = {Severity.CAUTION: 40, Severity.STOP: 80}


@dataclass
class Flag:
    severity: Severity
    check: str
    reason: str
    score: float | None = None

    def __post_init__(self):
        lo, hi = SCORE_BANDS[self.severity]
        raw = DEFAULT_SCORES[self.severity] if self.score is None else self.score
        self.score = round(min(max(raw, lo), hi))

    def to_dict(self) -> dict:
        return {"severity": self.severity.name, "check": self.check, "reason": self.reason, "score": self.score}
