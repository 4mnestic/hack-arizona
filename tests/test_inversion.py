from spraywait.checks import Severity, check_inversion
from spraywait.pesticides import DEFAULT_PESTICIDE
from spraywait.weather.types import Level, Reading
from tests.conftest import NOW, make_reading


def test_warmer_aloft_is_stop():
    flags = check_inversion(make_reading((57, 5, 180), (61, 6, 180)), DEFAULT_PESTICIDE)
    assert [f.severity for f in flags] == [Severity.STOP]
    assert "inversion" in flags[0].reason.lower()
    assert "4.0F" in flags[0].reason


def test_slight_inversion_still_stop():
    flags = check_inversion(make_reading((60, 5, 180), (60.3, 6, 180)), DEFAULT_PESTICIDE)
    assert flags[0].severity == Severity.STOP


def test_near_neutral_is_caution():
    flags = check_inversion(make_reading((60, 5, 180), (59.8, 6, 180)), DEFAULT_PESTICIDE)
    assert [f.severity for f in flags] == [Severity.CAUTION]


def test_normal_lapse_is_clear():
    assert check_inversion(make_reading((70, 5, 180), (68.5, 6, 180)), DEFAULT_PESTICIDE) == []


def test_single_level_cannot_detect():
    r = Reading(NOW, [Level(5, 60, 5, 180)])
    assert check_inversion(r, DEFAULT_PESTICIDE) == []


def test_uses_lowest_and_highest_of_many_levels():
    r = Reading(NOW, [Level(30, 61, 6, 180), Level(5, 57, 5, 180), Level(15, 59, 5, 180)])
    flags = check_inversion(r, DEFAULT_PESTICIDE)
    assert flags[0].severity == Severity.STOP
    assert "30 ft" in flags[0].reason and "5 ft" in flags[0].reason
