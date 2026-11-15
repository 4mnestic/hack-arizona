from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from spraywait import Status, decide
from spraywait.weather import DummyStation, StationSource, parse_station_payload

LA = ZoneInfo("America/Los_Angeles")


def at(hour, minute=0):
    return datetime(2026, 11, 15, hour, minute, tzinfo=LA)


def sensor(kind, h, value, unit):
    return {"type": kind, "height_m": h, "value": value, "unit": unit}


def test_parse_converts_units_and_heights():
    """Metric sensors become F/mph levels at heights in feet, sorted low to high; gusts ignored."""
    r = parse_station_payload({"station_id": "t1", "observed_at": "2026-11-15T20:00:00Z", "sensors": [
        sensor("air_temp", 9.1, 20, "C"), sensor("wind_speed", 9.1, 10, "km/h"), sensor("wind_dir", 9.1, 90, "deg"),
        sensor("air_temp", 1.5, 293.15, "K"), sensor("wind_speed", 1.5, 2, "m/s"), sensor("wind_gust", 1.5, 9, "m/s"),
    ]})
    lo, hi = r.levels
    assert (lo.height_ft, lo.temp_f, lo.wind_mph, lo.wind_dir_deg) == (4.9, 68.0, 4.5, None)
    assert (hi.height_ft, hi.temp_f, hi.wind_mph, hi.wind_dir_deg) == (29.9, 68.0, 6.2, 90)
    assert r.source == "farm station t1" and r.timestamp.tzinfo is None


@pytest.mark.parametrize("unit,value,expected", [("F", 50, 50.0), ("C", 10, 50.0), ("K", 283.15, 50.0)])
def test_parse_temperature_units(unit, value, expected):
    """Each supported temperature unit converts to Fahrenheit."""
    r = parse_station_payload({"observed_at": "2026-11-15T20:00:00", "sensors": [
        sensor("air_temp", 1.5, value, unit), sensor("wind_speed", 1.5, 1, "kn")]})
    assert r.levels[0].temp_f == expected and r.levels[0].wind_mph == 1.2 and r.source == "farm station ?"


def test_parse_drops_heights_with_missing_values():
    """A height whose temp or wind dropped out (null) is left out, not guessed."""
    r = parse_station_payload({"observed_at": "2026-11-15T20:00:00Z", "sensors": [
        sensor("air_temp", 1.5, 10, "C"), sensor("wind_speed", 1.5, 2, "m/s"),
        sensor("air_temp", 9.1, None, "C"), sensor("wind_speed", 9.1, 3, "m/s")]})
    assert [lv.height_ft for lv in r.levels] == [4.9]


@pytest.mark.parametrize("bad", [
    {}, {"observed_at": "not a date", "sensors": []}, {"observed_at": None, "sensors": []},
    {"observed_at": "2026-11-15T20:00:00Z", "sensors": [sensor("air_temp", 1, 1, "R")]},
    {"observed_at": "2026-11-15T20:00:00Z", "sensors": [sensor("wind_speed", 1, 1, "furlongs")]},
])
def test_parse_rejects_malformed(bad):
    """Missing fields, bad timestamps, and unknown units raise ValueError."""
    with pytest.raises(ValueError):
        parse_station_payload(bad)


def test_payload_shape_is_vendor_like():
    """The dummy emits UTC time, metric units, and temp/speed/gust/direction per height."""
    p = DummyStation().payload(at(13, 7))
    assert p["observed_at"] == "2026-11-15T21:07:00Z" and p["interval_s"] == 60
    assert {s["type"] for s in p["sensors"]} == {"air_temp", "wind_speed", "wind_gust", "wind_dir"}
    assert {s["height_m"] for s in p["sensors"]} == set(DummyStation.HEIGHTS_M)


def test_payload_deterministic_per_minute():
    """Two calls in the same minute return the same payload."""
    assert DummyStation().payload(at(13, 7)) == DummyStation().payload(datetime(2026, 11, 15, 21, 7, 45, tzinfo=timezone.utc))


@pytest.mark.parametrize("hour,expected", [(2, 1.0), (10, 0.0), (19.5, 0.5), (8, 0.5)])
def test_inversion_strength_follows_clock(hour, expected):
    """Inversion builds after dusk, holds overnight, and breaks mid-morning."""
    assert DummyStation.inversion_strength(hour) == expected


@pytest.mark.parametrize("hour,status", [(3, Status.STOP), (22, Status.STOP), (10, Status.GO)])
def test_dummy_day_cycle_decisions(hour, status):
    """The dummy station gives STOP at night (inversion) and GO mid-morning."""
    r = StationSource(now=at(hour)).get_reading()
    assert decide(r, now=r.timestamp).status == status


def test_night_has_inversion_flag():
    """At night the engine sees the simulated inversion."""
    r = StationSource(now=at(3)).get_reading()
    assert "inversion" in [f.check for f in decide(r, now=r.timestamp).flags]


def test_dropouts_produce_nulls():
    """With dropout_rate=1 every sensor value is null, so no usable levels remain."""
    p = DummyStation(dropout_rate=1.0).payload(at(12))
    assert all(s["value"] is None for s in p["sensors"])
    assert parse_station_payload(p).levels == []


def test_station_source_defaults_to_now():
    """With no time given, the source reads the current minute."""
    r = StationSource().get_reading()
    assert abs((datetime.now() - r.timestamp).total_seconds()) < 120
