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
               logged_at: datetime | None = None, mode: str = "live") -> dict:
        entry = {
            "logged_at": (logged_at or datetime.now()).isoformat(timespec="seconds"),
            "mode": mode,
            "reading": reading.to_dict(),
            "pesticide": pesticide.name,
            "nozzle": pesticide.nozzle,
            "decision": decision.to_dict(),
        }
        with self.path.open("a") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]

    def history(self, mode: str | None = None) -> list[dict]:
        """Entries for one mode (or all), oldest first. Each gets `changed_from`: the previous
        status for the same pesticide and nozzle when it differs (an alert), else None."""
        last: dict[tuple, str] = {}
        out = []
        for e in self.entries():
            e.setdefault("mode", "live")
            if mode and e["mode"] != mode:
                continue
            key = (e["mode"], e["pesticide"], e.get("nozzle", ""))
            status = e["decision"]["status"]
            prev = last.get(key)
            e["changed_from"] = prev if prev and prev != status else None
            last[key] = status
            out.append(e)
        return out

    def rows(self, mode: str | None = None) -> list[dict]:
        """Flattened, one row per entry, for tables and CSV."""
        rows = []
        for e in self.history(mode):
            lv = e["reading"]["levels"]
            row = {
                "time": e["reading"]["timestamp"],
                "mode": e["mode"],
                "status": e["decision"]["status"],
                "score": e["decision"].get("score", ""),
                "changed_from": e["changed_from"] or "",
                "pesticide": e["pesticide"],
                "nozzle": e.get("nozzle", ""),
                "source": e["reading"]["source"],
            }
            if lv:
                lo, hi = lv[0], lv[-1]
                row |= {
                    f"temp {lo['height_ft']:g}ft": lo["temp_f"],
                    f"temp {hi['height_ft']:g}ft": hi["temp_f"],
                    f"wind {lo['height_ft']:g}ft": lo["wind_mph"],
                    f"wind {hi['height_ft']:g}ft": hi["wind_mph"],
                }
            row |= {
                "triggered": "; ".join(f"{f['severity']}: {f['check']}" for f in e["decision"]["flags"]) or "none",
                "reasons": " | ".join(e["decision"]["reasons"]),
            }
            rows.append(row)
        return rows

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()
