from spraywait import Status, decide, single_station_decision
from spraywait.pesticides import DEFAULT_PESTICIDE, LocalPesticideDB
from spraywait.weather import SCENARIOS, SimulatedSource
from tests.conftest import NOW, make_reading


def test_clear_conditions_go(now):
    d = decide(make_reading((72, 5.5, 300), (70.5, 6, 300)), now=now)
    assert d.status == Status.GO
    assert d.flags == []
    assert len(d.reasons) == 1


def test_stop_beats_caution(now):
    d = decide(make_reading((57, 3.5, 180), (61, 8, 250)), now=now)
    assert d.status == Status.STOP
    assert d.flags[0].severity.name == "STOP"
    assert "inversion" in d.reasons[0].lower()


def test_caution_only(now):
    d = decide(make_reading((70, 3.5, 300), (68.5, 6, 300)), now=now)
    assert d.status == Status.CAUTION


def test_demo_scenario_single_station_says_go_but_tool_says_stop(now):
    reading = SimulatedSource("evening_inversion", now=now).get_reading()
    assert single_station_decision(reading).status == Status.GO
    full = decide(reading, now=now)
    assert full.status == Status.STOP
    checks = {f.check for f in full.flags}
    assert "inversion" in checks and "wind_shear" in checks


def test_shear_aloft_scenario_caught(now):
    reading = SimulatedSource("shear_aloft", now=now).get_reading()
    assert single_station_decision(reading).status == Status.GO
    assert decide(reading, now=now).status == Status.STOP


def test_every_scenario_has_expected_status(now):
    expected = {
        "evening_inversion": Status.STOP,
        "clear_midday": Status.GO,
        "too_windy": Status.STOP,
        "dead_calm": Status.STOP,
        "shear_aloft": Status.STOP,
        "hot_afternoon": Status.GO,
    }
    assert set(expected) == set(SCENARIOS)
    for name, status in expected.items():
        reading = SimulatedSource(name, now=now).get_reading()
        assert decide(reading, now=now).status == status, name


def test_hot_afternoon_depends_on_pesticide(now):
    db = LocalPesticideDB()
    reading = SimulatedSource("hot_afternoon", now=now).get_reading()
    assert decide(reading, db.get("Captan"), now=now).status == Status.GO
    assert decide(reading, db.get("Malathion"), now=now).status == Status.STOP


def test_decision_serializes(now):
    d = decide(make_reading((57, 3.5, 180), (61, 8, 250)), DEFAULT_PESTICIDE, now=now)
    out = d.to_dict()
    assert out["status"] == "STOP"
    assert out["flags"][0]["severity"] == "STOP"
