from datetime import datetime

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


DAYTIME = datetime(2026, 11, 15, 13, 0)


def test_near_neutral_light_wind_is_caution():
    flags = check_inversion(make_reading((60, 2, 180), (59.8, 6, 180)), DEFAULT_PESTICIDE)
    assert [f.severity for f in flags] == [Severity.CAUTION]
    assert "ground wind is light" in flags[0].reason


def test_near_neutral_with_moving_air_is_clear():
    """Equal temperatures with a breeze is a mixed layer, not a forming inversion."""
    assert check_inversion(make_reading((60, 7.5, 180), (59.8, 9, 180)), DEFAULT_PESTICIDE) == []


def test_inversion_strength_is_named():
    weak = check_inversion(make_reading((60, 5, 180), (60.3, 6, 180)), DEFAULT_PESTICIDE)[0]
    moderate = check_inversion(make_reading((60, 5, 180), (61.2, 6, 180)), DEFAULT_PESTICIDE)[0]
    strong = check_inversion(make_reading((60, 5, 180), (62.5, 6, 180)), DEFAULT_PESTICIDE)[0]
    assert weak.reason.startswith("Weak") and moderate.reason.startswith("Moderate") and strong.reason.startswith("Strong")
    assert {weak.severity, moderate.severity, strong.severity} == {Severity.STOP}


def test_inversion_reason_mentions_evening_and_light_wind():
    reason = check_inversion(make_reading((57, 2, 180), (61, 6, 180)), DEFAULT_PESTICIDE)[0].reason
    assert "late afternoon through early morning" in reason and "ground wind is light" in reason


def test_inversion_stop_regardless_of_time_or_wind():
    """Time of day and wind explain an inversion but never downgrade it."""
    windy_day = make_reading((60, 9, 180), (61, 10, 180), ts=DAYTIME)
    flags = check_inversion(windy_day, DEFAULT_PESTICIDE)
    assert flags[0].severity == Severity.STOP
    assert "evening" not in flags[0].reason


def test_forming_inversion_flagged_at_night_with_light_wind():
    """A weaker-than-normal drop at dusk with calm air favors an inversion forming."""
    flags = check_inversion(make_reading((60, 3, 180), (59.2, 5, 180)), DEFAULT_PESTICIDE)
    assert [f.severity for f in flags] == [Severity.CAUTION]
    assert "favor an inversion forming" in flags[0].reason


def test_forming_inversion_not_flagged_by_day_or_in_wind():
    assert check_inversion(make_reading((60, 3, 180), (59.2, 5, 180), ts=DAYTIME), DEFAULT_PESTICIDE) == []
    assert check_inversion(make_reading((60, 7.5, 180), (59.2, 9, 180)), DEFAULT_PESTICIDE) == []


def test_near_neutral_light_wind_still_caution_by_day():
    """Time of day only adds caution; a daytime clock never relaxes the light-wind result."""
    flags = check_inversion(make_reading((60, 2, 180), (59.8, 6, 180), ts=DAYTIME), DEFAULT_PESTICIDE)
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
