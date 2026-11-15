import json
from datetime import datetime
from pathlib import Path

from spraywait.decision import Decision
from spraywait.pesticides.db import Pesticide
from spraywait.weather.types import Reading

DEFAULT_LOG = Path("spray_log.jsonl")


class DecisionLog:
    """Append-only, time-stamped record of every reading, its flags, and the decision."""

    def __init__(self, path: Path = DEFAULT_LOG):
        self.path = Path(path)

    def append(self, reading: Reading, pesticide: Pesticide, decision: Decision,
               logged_at: datetime | None = None) -> dict:
        entry = {
            "logged_at": (logged_at or datetime.now()).isoformat(timespec="seconds"),
            "reading": reading.to_dict(),
            "pesticide": pesticide.name,
            "decision": decision.to_dict(),
        }
        with self.path.open("a") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]

    def rows(self) -> list[dict]:
        """Flattened, one row per entry, for tables."""
        rows = []
        for e in self.entries():
            lv = e["reading"]["levels"]
            lo, hi = lv[0], lv[-1]
            rows.append({
                "time": e["reading"]["timestamp"],
                "status": e["decision"]["status"],
                "pesticide": e["pesticide"],
                f"temp {lo['height_ft']:g}ft": lo["temp_f"],
                f"temp {hi['height_ft']:g}ft": hi["temp_f"],
                f"wind {lo['height_ft']:g}ft": lo["wind_mph"],
                f"wind {hi['height_ft']:g}ft": hi["wind_mph"],
                "triggered": "; ".join(f"{f['severity']}: {f['check']}" for f in e["decision"]["flags"]) or "none",
                "reasons": " | ".join(e["decision"]["reasons"]),
            })
        return rows

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()
