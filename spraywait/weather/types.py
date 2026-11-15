from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass
class Level:
    """Weather at one height above the ground."""

    height_ft: float
    temp_f: float
    wind_mph: float
    wind_dir_deg: float | None = None


@dataclass
class Reading:
    """All levels measured at one moment."""

    timestamp: datetime
    levels: list[Level]
    source: str = "unknown"

    def sorted_levels(self) -> list[Level]:
        return sorted(self.levels, key=lambda lv: lv.height_ft)

    @property
    def lowest(self) -> Level:
        return self.sorted_levels()[0]

    @property
    def highest(self) -> Level:
        return self.sorted_levels()[-1]

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "levels": [asdict(lv) for lv in self.sorted_levels()],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Reading":
        return cls(
            timestamp=datetime.fromisoformat(d["timestamp"]),
            levels=[Level(**lv) for lv in d["levels"]],
            source=d.get("source", "unknown"),
        )
