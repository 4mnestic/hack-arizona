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


def test_hidden_inversion_is_caught_by_inversion_alone(now):
    """The hidden-inversion demo: a ground station says GO, and the only thing SprayWait flags is the inversion."""
    reading = SimulatedSource("evening_inversion", now=now).get_reading()
    assert single_station_decision(reading).status == Status.GO
    full = decide(reading, now=now)
    assert full.status == Status.STOP
    assert {f.check for f in full.flags} == {"inversion"}


def test_inversion_forming_is_an_early_caution(now):
    """Near-equal temperatures give CAUTION from the inversion check only, while a ground station says GO."""
    reading = SimulatedSource("inversion_forming", now=now).get_reading()
    assert single_station_decision(reading).status == Status.GO
    full = decide(reading, now=now)
    assert full.status == Status.CAUTION
    assert {f.check for f in full.flags} == {"inversion"}


def test_strong_wind_aloft_is_speed_only(now):
    """Wind-aloft demo flags speed (limit and shear) but not direction or inversion."""
    reading = SimulatedSource("shear_aloft", now=now).get_reading()
    assert single_station_decision(reading).status == Status.GO
    full = decide(reading, now=now)
    assert full.status == Status.STOP
    assert {f.check for f in full.flags} <= {"wind_speed", "wind_shear"}
    assert not any("direction" in f.reason.lower() for f in full.flags)


def test_wind_turning_is_direction_only(now):
    """Direction demo: the only flag is the change in wind direction between heights."""
    reading = SimulatedSource("wind_direction_shift", now=now).get_reading()
    assert single_station_decision(reading).status == Status.GO
    full = decide(reading, now=now)
    assert full.status == Status.STOP
    assert len(full.flags) == 1 and "direction" in full.flags[0].reason.lower()


def test_every_scenario_note_matches_the_engine(now):
    """Each scenario's demo note states the outcome the engine actually produces (ground alone, SprayWait)."""
    for name, spec in SCENARIOS.items():
        reading = SimulatedSource(name, now=now).get_reading()
        got = (single_station_decision(reading).status.value, decide(reading, now=now).status.value)
        assert got == spec["expect"], name
        assert spec["illustrates"].strip(), name


def test_hot_afternoon_depends_on_pesticide(now):
    """The hot-afternoon demo is GO for a low-volatility product and STOP for Malathion's 90F limit."""
    db = LocalPesticideDB()
    reading = SimulatedSource("hot_afternoon", now=now).get_reading()
    assert decide(reading, db.get("Captan"), now=now).status == Status.GO
    assert decide(reading, db.get("Malathion"), now=now).status == Status.STOP


def test_decision_serializes(now):
    d = decide(make_reading((57, 3.5, 180), (61, 8, 250)), DEFAULT_PESTICIDE, now=now)
    out = d.to_dict()
    assert out["status"] == "STOP"
    assert out["flags"][0]["severity"] == "STOP"
