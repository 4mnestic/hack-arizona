from datetime import timedelta

from spraywait.checks import Severity, check_data_quality, check_volatility
from spraywait.pesticides import DEFAULT_PESTICIDE, Pesticide
from spraywait.weather.types import Level, Reading
from tests.conftest import NOW, make_reading

HOT = make_reading((96, 6, 310), (94, 7, 310))
MILD = make_reading((70, 5, 310), (68, 6, 310))


def test_low_volatility_ignores_heat():
    assert check_volatility(HOT, DEFAULT_PESTICIDE) == []


def test_label_max_temp_is_stop():
    oil = Pesticide(name="Oil", max_temp_f=90)
    flags = check_volatility(HOT, oil)
    assert flags[0].severity == Severity.STOP
    assert "90F" in flags[0].reason


def test_high_volatility_caution_then_stop():
    hot_product = Pesticide(name="Vol", volatility="high")
    assert check_volatility(make_reading((78, 5, 0), (76, 6, 0)), hot_product)[0].severity == Severity.CAUTION
    assert check_volatility(HOT, hot_product)[0].severity == Severity.STOP


def test_fine_droplets_caution_in_breeze():
    fine = Pesticide(name="Fine", droplet_size="fine")
    assert check_volatility(make_reading((70, 5, 0), (68, 8, 0)), fine)[0].severity == Severity.CAUTION
    assert check_volatility(MILD, fine) == []


def test_no_data_is_stop(now):
    assert check_data_quality(Reading(NOW, []), DEFAULT_PESTICIDE, now)[0].severity == Severity.STOP


def test_single_height_is_caution(now):
    flags = check_data_quality(Reading(NOW, [Level(5, 70, 5, 0)]), DEFAULT_PESTICIDE, now)
    assert [f.severity for f in flags] == [Severity.CAUTION]
    assert "one measurement height" in flags[0].reason.lower()


def test_stale_data_is_caution(now):
    old = make_reading((70, 5, 0), (68, 6, 0), ts=NOW - timedelta(minutes=40))
    flags = check_data_quality(old, DEFAULT_PESTICIDE, now)
    assert flags[0].severity == Severity.CAUTION
    assert "40 minutes" in flags[0].reason


def test_fresh_two_height_data_is_clean(now):
    assert check_data_quality(MILD, DEFAULT_PESTICIDE, now) == []
