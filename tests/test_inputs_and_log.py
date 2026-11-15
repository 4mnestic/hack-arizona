from datetime import timedelta

import pytest

from spraywait import decide
from spraywait.log import DecisionLog
from spraywait.pesticides import LocalPesticideDB
from spraywait.weather import SCENARIOS, Reading, SimulatedSource
from tests.conftest import NOW, make_reading


def test_simulated_source_timestamps_end_at_now(now):
    src = SimulatedSource("evening_inversion", now=now)
    readings = src.readings()
    assert readings[-1].timestamp == now
    assert readings[0].timestamp == now - timedelta(minutes=20 * (len(readings) - 1))
    assert src.get_reading() is readings[-1]


def test_unknown_scenario_rejected():
    with pytest.raises(KeyError):
        SimulatedSource("nope")


def test_all_scenarios_have_two_heights(now):
    for name in SCENARIOS:
        for r in SimulatedSource(name, now=now).readings():
            assert [lv.height_ft for lv in r.sorted_levels()] == [5, 30]


def test_reading_round_trips_through_dict():
    r = make_reading((57, 3.5, 180), (61, 8, 250))
    assert Reading.from_dict(r.to_dict()) == r


def test_pesticide_db_lookup():
    db = LocalPesticideDB()
    assert "Captan" in db.list()
    p = db.get("captan")
    assert p.max_wind_mph == 10 and p.volatility == "low"
    with pytest.raises(KeyError):
        db.get("unobtainium")


def test_log_appends_and_reads_back(tmp_path, now):
    log = DecisionLog(tmp_path / "log.jsonl")
    db = LocalPesticideDB()
    p = db.get("Captan")
    assert log.entries() == []

    for r in SimulatedSource("evening_inversion", now=now).readings():
        log.append(r, p, decide(r, p, now=r.timestamp), logged_at=r.timestamp)

    entries = log.entries()
    assert len(entries) == 4
    assert entries[-1]["decision"]["status"] == "STOP"
    assert entries[-1]["pesticide"] == "Captan"
    assert entries[-1]["reading"]["timestamp"] == now.isoformat()

    rows = log.rows()
    assert rows[0]["status"] == "GO"
    assert "inversion" in rows[-1]["triggered"]
    assert rows[-1]["temp 30ft"] == 61.0

    log.clear()
    assert log.entries() == []


def test_log_history_marks_changes_per_stream(tmp_path, now):
    """changed_from tracks each pesticide/nozzle stream separately and filters by mode."""
    from spraywait.pesticides.db import Pesticide
    log = DecisionLog(tmp_path / "log.jsonl")
    calm = make_reading((60, 1, 0), (62, 1, 0))
    clear = make_reading((70, 5, 300), (68.6, 6, 305))
    a, b = Pesticide(name="A"), Pesticide(name="B", nozzle="N")
    for r, p, mode in [(calm, a, "live"), (calm, b, "live"), (clear, a, "live"), (clear, a, "demo")]:
        log.append(r, p, decide(r, p, now=r.timestamp), mode=mode)
    live = log.history("live")
    assert [e["changed_from"] for e in live] == [None, None, "STOP"]
    assert len(log.history()) == 4 and log.history("demo")[0]["changed_from"] is None


def test_log_rows_handle_no_data(tmp_path, now):
    """A no-data entry flattens without temperature columns instead of crashing."""
    from spraywait.pesticides.db import DEFAULT_PESTICIDE
    from spraywait.weather.types import Reading
    log = DecisionLog(tmp_path / "log.jsonl")
    empty = Reading(now, [], source="farm")
    log.append(empty, DEFAULT_PESTICIDE, decide(empty, now=now))
    (row,) = log.rows()
    assert row["status"] == "STOP" and not any(k.startswith("temp") for k in row)


def test_log_reads_entries_without_mode(tmp_path):
    """Entries written before the mode field existed are treated as live."""
    import json
    path = tmp_path / "log.jsonl"
    old = {"logged_at": "2026-11-15T10:00:00", "pesticide": "A",
           "reading": {"timestamp": "2026-11-15T10:00:00", "source": "s", "levels": []},
           "decision": {"status": "GO", "reasons": [], "flags": []}}
    path.write_text(json.dumps(old) + "\n")
    assert DecisionLog(path).history("live")[0]["mode"] == "live"
