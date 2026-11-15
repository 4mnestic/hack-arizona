from spraywait.checks import Severity, check_wind_shear, check_wind_speed
from spraywait.checks.wind import direction_difference
from spraywait.pesticides import DEFAULT_PESTICIDE, Pesticide
from tests.conftest import make_reading


def severities(flags):
    return [f.severity for f in flags]


def test_within_limits_is_clear():
    assert check_wind_speed(make_reading((70, 5, 180), (68, 6, 180)), DEFAULT_PESTICIDE) == []


def test_below_3mph_is_stop():
    flags = check_wind_speed(make_reading((70, 2, 180), (68, 6, 180)), DEFAULT_PESTICIDE)
    assert severities(flags) == [Severity.STOP]
    assert "calm" in flags[0].reason.lower()


def test_above_10mph_is_stop():
    flags = check_wind_speed(make_reading((70, 5, 180), (68, 12, 180)), DEFAULT_PESTICIDE)
    assert severities(flags) == [Severity.STOP]
    assert "30 ft" in flags[0].reason


def test_near_limit_is_caution():
    flags = check_wind_speed(make_reading((70, 3.5, 180), (68, 9.5, 180)), DEFAULT_PESTICIDE)
    assert severities(flags) == [Severity.CAUTION, Severity.CAUTION]


def test_pesticide_limits_override_defaults():
    strict = Pesticide(name="Strict", min_wind_mph=4, max_wind_mph=8)
    flags = check_wind_speed(make_reading((70, 3.5, 180), (68, 9, 180)), strict)
    assert severities(flags) == [Severity.STOP, Severity.STOP]


def test_speed_shear_caution_then_stop():
    assert severities(check_wind_shear(make_reading((66, 4, 180), (65, 9.5, 180)), DEFAULT_PESTICIDE)) == [Severity.CAUTION]
    assert severities(check_wind_shear(make_reading((66, 2, 180), (65, 10, 180)), DEFAULT_PESTICIDE)) == [Severity.STOP]


def test_direction_shear_caution_then_stop():
    assert severities(check_wind_shear(make_reading((66, 5, 180), (65, 6, 230)), DEFAULT_PESTICIDE)) == [Severity.CAUTION]
    assert severities(check_wind_shear(make_reading((66, 5, 180), (65, 6, 300)), DEFAULT_PESTICIDE)) == [Severity.STOP]


def test_direction_ignored_when_calm():
    assert check_wind_shear(make_reading((66, 0.5, 10), (65, 1.5, 200)), DEFAULT_PESTICIDE) == []


def test_direction_ignored_when_missing():
    assert check_wind_shear(make_reading((66, 5, None), (65, 6, 300)), DEFAULT_PESTICIDE) == []


def test_direction_difference_wraps_around():
    assert direction_difference(350, 10) == 20
    assert direction_difference(10, 350) == 20
    assert direction_difference(0, 180) == 180
    assert direction_difference(90, 90) == 0
