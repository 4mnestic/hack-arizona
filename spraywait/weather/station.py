"""Farm weather station: the vendor-style payload format, its adapter, and a dummy station.

A real station (datalogger on a mast) reports something like:

    {
      "station_id": "orchard-tower-1",
      "observed_at": "2026-11-15T21:14:00Z",      # UTC
      "interval_s": 60,                             # averaging period
      "battery_v": 12.7,
      "sensors": [
        {"id": "AT_1", "type": "air_temp",   "height_m": 1.5, "value": 14.2, "unit": "C"},
        {"id": "WS_1", "type": "wind_speed", "height_m": 1.5, "value": 2.1,  "unit": "m/s"},
        {"id": "WG_1", "type": "wind_gust",  "height_m": 1.5, "value": 3.4,  "unit": "m/s"},
        {"id": "WD_1", "type": "wind_dir",   "height_m": 1.5, "value": 285,  "unit": "deg"},
        ... same at 9.1 m (30 ft) ...
      ]
    }

parse_station_payload() turns that into a Reading. Swapping DummyStation for a real
station's feed (pushed to the API or pulled from the vendor cloud) needs no other change.
"""

import math
import random
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from spraywait.weather.source import WeatherSource
from spraywait.weather.types import Level, Reading

M_TO_FT = 3.28084
TEMP_TO_F = {"F": lambda v: v, "C": lambda v: v * 9 / 5 + 32, "K": lambda v: (v - 273.15) * 9 / 5 + 32}
SPEED_TO_MPH = {"mph": 1.0, "m/s": 2.23694, "km/h": 0.621371, "kn": 1.15078}


def parse_station_payload(payload: dict) -> Reading:
    """Convert a station payload to a Reading. Heights missing temp or wind are dropped.

    Raises ValueError for malformed payloads or unknown units.
    """
    try:
        observed = datetime.fromisoformat(payload["observed_at"].replace("Z", "+00:00"))
        sensors = payload["sensors"]
    except (KeyError, AttributeError, TypeError, ValueError) as e:
        raise ValueError(f"bad station payload: {e}") from None
    if observed.tzinfo:  # engine works in naive local time
        observed = observed.astimezone().replace(tzinfo=None)

    by_height: dict[float, dict] = {}
    for s in sensors:
        value, unit = s.get("value"), s.get("unit", "")
        if value is None:  # sensor dropout
            continue
        h = round(s["height_m"] * M_TO_FT, 1)
        kind = s.get("type")
        if kind == "air_temp":
            if unit not in TEMP_TO_F:
                raise ValueError(f"unknown temperature unit {unit!r}")
            by_height.setdefault(h, {})["temp_f"] = round(TEMP_TO_F[unit](value), 1)
        elif kind == "wind_speed":
            if unit not in SPEED_TO_MPH:
                raise ValueError(f"unknown speed unit {unit!r}")
            by_height.setdefault(h, {})["wind_mph"] = round(value * SPEED_TO_MPH[unit], 1)
        elif kind == "wind_dir":
            by_height.setdefault(h, {})["wind_dir_deg"] = value
        # other types (gusts, humidity, ...) are not used by the checks yet

    _pair_heights(by_height)
    levels = [Level(h, **v) for h, v in sorted(by_height.items()) if {"temp_f", "wind_mph"} <= v.keys()]
    return Reading(observed, levels, source=f"farm station {payload.get('station_id', '?')}")


PAIR_FT = 4.0  # wind sensor this close to a thermometer counts as the same level


def _pair_heights(by_height: dict[float, dict]) -> None:
    """Masts often mount anemometers a little above the thermometer (Mesonet: 1.5/2 m, 9/10 m).

    Merge each wind-only height into the nearest temperature-only height within PAIR_FT;
    the level keeps the thermometer's height, since inversion depends on it.
    """
    temps = [h for h, v in by_height.items() if "temp_f" in v and "wind_mph" not in v]
    for h in [h for h, v in by_height.items() if "wind_mph" in v and "temp_f" not in v]:
        near = min(temps, key=lambda t: abs(t - h), default=None)
        if near is not None and abs(near - h) <= PAIR_FT:
            by_height[near].update(by_height.pop(h))
            temps.remove(near)


class DummyStation:
    """Simulates a 2-height orchard mast whose weather follows the farm's local clock.

    Night: surface inversion builds after dusk, light wind below, stronger veered wind aloft.
    Day: air mixes, slightly cooler aloft, moderate wind peaking mid-afternoon.
    Values are deterministic per minute, so repeated calls agree.
    """

    HEIGHTS_M = (1.5, 9.1)  # ~5 ft and ~30 ft

    def __init__(self, station_id: str = "orchard-tower-1", tz: str = "America/Los_Angeles",
                 dropout_rate: float = 0.0):
        self.station_id, self.tz, self.dropout_rate = station_id, ZoneInfo(tz), dropout_rate

    @staticmethod
    def inversion_strength(hour: float) -> float:
        """0 by day, ramps to 1 from 17h to 22h, holds overnight, breaks 7h to 9h."""
        if 9 <= hour < 17:
            return 0.0
        if 17 <= hour < 22:
            return (hour - 17) / 5
        if 7 <= hour < 9:
            return 1 - (hour - 7) / 2
        return 1.0

    def conditions(self, local: datetime) -> tuple[dict, random.Random]:
        """Physical conditions (C, m/s, deg) per height for a farm-local time, plus the minute's RNG."""
        hour = local.hour + local.minute / 60
        rng = random.Random(f"{self.station_id}{local:%Y%m%d%H%M}")
        inv = self.inversion_strength(hour)
        day = max(0.0, math.sin(math.pi * (hour - 7) / 11)) if 7 <= hour <= 18 else 0.0

        ground_c = 12 + 9 * math.sin(math.pi * (hour - 9) / 12) + rng.uniform(-0.2, 0.2)
        aloft_c = ground_c + 1.8 * inv - 0.6 * (1 - inv) + rng.uniform(-0.1, 0.1)
        ground_ms = 0.7 + 2.6 * day + rng.uniform(-0.2, 0.2)
        aloft_ms = ground_ms * (1.3 + 1.5 * inv) + rng.uniform(-0.2, 0.2)
        ground_dir = (290 + rng.uniform(-15, 15) - 80 * inv) % 360
        aloft_dir = (ground_dir + 70 * inv + rng.uniform(-8, 8)) % 360
        return {
            self.HEIGHTS_M[0]: (ground_c, max(0.1, ground_ms), ground_dir),
            self.HEIGHTS_M[1]: (aloft_c, max(0.1, aloft_ms), aloft_dir),
        }, rng

    def payload(self, now: datetime | None = None) -> dict:
        """The vendor-style JSON a real station would send for the minute containing `now`."""
        now_utc = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(second=0, microsecond=0)
        cond, rng = self.conditions(now_utc.astimezone(self.tz))
        sensors = []
        for i, (h, (temp_c, ws, wd)) in enumerate(cond.items(), start=1):
            for kind, sid, value, unit in [
                ("air_temp", f"AT_{i}", round(temp_c, 2), "C"),
                ("wind_speed", f"WS_{i}", round(ws, 2), "m/s"),
                ("wind_gust", f"WG_{i}", round(ws * rng.uniform(1.3, 1.8), 2), "m/s"),
                ("wind_dir", f"WD_{i}", round(wd), "deg"),
            ]:
                if rng.random() < self.dropout_rate:
                    value = None
                sensors.append({"id": sid, "type": kind, "height_m": h, "value": value, "unit": unit})
        return {
            "station_id": self.station_id,
            "observed_at": now_utc.isoformat().replace("+00:00", "Z"),
            "interval_s": 60,
            "battery_v": round(12.4 + rng.uniform(0, 0.5), 2),
            "sensors": sensors,
        }


class StationSource(WeatherSource):
    """Reads the farm station by pulling its payload (here, from the dummy) and parsing it."""

    name = "station"

    def __init__(self, station: DummyStation | None = None, now: datetime | None = None):
        self.station = station or DummyStation()
        self.now = now

    def get_reading(self) -> Reading:
        return parse_station_payload(self.station.payload(self.now))


__all__ = ["DummyStation", "StationSource", "parse_station_payload"]
