"""A simulated farm station that replays one day of Oklahoma Mesonet 5-minute data in real time.

Mesonet MTS files (one row per 5 minutes, TIME in UTC) carry the two heights the challenge asks for:
air temperature at 1.5 m (TAIR) and 9 m (TA9M), wind speed at 2 m (WS2M) and 10 m (WSPD),
wind direction at 10 m only (WDIR). Values <= -990 are Mesonet's missing-data codes.

At wall-clock UTC time HH:MM the station reports the row for HH:MM + `shift` (rounded down to
5 min), stamped with the real current time, in the same vendor payload format as a real station.
The shift lets a demo at a given time of day replay a chosen part of the recorded day.
"""

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

from spraywait.weather.farm import FarmStationStore
from spraywait.weather.station import parse_station_payload

DEFAULT_CSV = Path(__file__).resolve().parents[2] / "data" / "mesonet_data_files.csv"
STEP = timedelta(minutes=5)
MISSING = -990

# (column, sensor type, height in m, unit)
SENSORS = [
    ("TAIR", "air_temp", 1.5, "C"),
    ("WS2M", "wind_speed", 2.0, "m/s"),
    ("TA9M", "air_temp", 9.0, "C"),
    ("WSPD", "wind_speed", 10.0, "m/s"),
    ("WMAX", "wind_gust", 10.0, "m/s"),
    ("WDIR", "wind_dir", 10.0, "deg"),
    ("RELH", "rel_humidity", 1.5, "%"),
]


def _value(raw: str) -> float | None:
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    return None if v <= MISSING else v


class MesonetStation:
    """Replays a Mesonet day file as a live station, one row per 5 minutes of UTC clock time."""

    def __init__(self, path: Path | str = DEFAULT_CSV, shift: timedelta = timedelta(0)):
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            raise ValueError(f"{path}: no rows")
        self.station_id = f"mesonet-{rows[0]['STID'].strip().lower()}"
        self.rows = {r["TIME"].strip(): r for r in rows}
        self.shift = shift

    @staticmethod
    def slot(now: datetime) -> datetime:
        """The start of the 5-minute UTC slot containing `now`."""
        utc = now.astimezone(timezone.utc).replace(second=0, microsecond=0)
        return utc - timedelta(minutes=utc.minute % 5)

    def payload(self, now: datetime | None = None) -> dict:
        """The vendor-style payload for the slot containing `now` (missing sensors report null)."""
        observed = self.slot(now or datetime.now(timezone.utc))
        row = self.rows.get(f"{observed + self.shift:%H:%M}", {})
        sensors = [{"id": col, "type": kind, "height_m": h, "value": _value(row.get(col)), "unit": unit}
                   for col, kind, h, unit in SENSORS]
        return {
            "station_id": self.station_id,
            "observed_at": observed.isoformat().replace("+00:00", "Z"),
            "interval_s": int(STEP.total_seconds()),
            "sensors": sensors,
        }

    def payloads_since(self, start: datetime, now: datetime | None = None) -> list[dict]:
        """Every slot's payload from `start` up to and including now (a datalogger's buffered upload)."""
        end = self.slot(now or datetime.now(timezone.utc))
        t, out = self.slot(start), []
        while t <= end:
            out.append(self.payload(t))
            t += STEP
        return out


class MesonetFeed:
    """Runs a MesonetStation inside the app: each sync() stores every reading that has come due.

    No timer: whenever the app needs weather it catches up to the clock, so readings still land
    on real 5-minute slots, and a server that slept (free hosting) fills its gap on wake.
    Readings with no usable heights are skipped, as the ingest API would reject them.
    """

    def __init__(self, station: MesonetStation, store: FarmStationStore, backfill: timedelta = timedelta(hours=6)):
        self.station, self.store, self.backfill = station, store, backfill
        self.last: datetime | None = None

    def sync(self, now: datetime | None = None) -> None:
        now = now or datetime.now(timezone.utc)
        start = self.last + STEP if self.last else now - self.backfill
        for payload in self.station.payloads_since(start, now):
            reading = parse_station_payload(payload)
            if reading.levels:
                self.store.push(reading)
        self.last = self.station.slot(now)


__all__ = ["MesonetStation", "MesonetFeed", "DEFAULT_CSV"]
