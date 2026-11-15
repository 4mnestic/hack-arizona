from datetime import datetime

import pytest

from spraywait import Status, decide, single_station_decision
from spraywait.checks import Flag, Severity
from spraywait.log import DecisionLog
from spraywait.pesticides import DEFAULT_PESTICIDE, Pesticide
from spraywait.weather import SCENARIOS, Reading, SimulatedSource
from tests.conftest import NOW, make_reading


def score(lo, hi, pesticide=DEFAULT_PESTICIDE):
    return decide(make_reading(lo, hi), pesticide, now=NOW).score


def test_go_scores_zero(now):
    d = decide(make_reading((72, 8, 300), (70.5, 9, 300)), now=now)
    assert (d.status, d.score) == (Status.GO, 0)


def test_flag_score_is_clamped_into_its_severity_band():
    assert Flag(Severity.CAUTION, "x", "r", 95).score == 69
    assert Flag(Severity.STOP, "x", "r", 5).score == 70
    assert Flag(Severity.STOP, "x", "r", 1000).score == 100
    assert Flag(Severity.CAUTION, "x", "r").score == 40 and Flag(Severity.STOP, "x", "r").score == 80


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_scenario_score_matches_status_band(name, now):
    d = decide(SimulatedSource(name, now=now).get_reading(), now=now)
    bands = {Status.GO: (0, 0), Status.CAUTION: (20, 69), Status.STOP: (70, 100)}
    lo, hi = bands[d.status]
    assert lo <= d.score <= hi, (name, d.status, d.score)


def test_stronger_inversion_scores_higher():
    weak = score((60, 8, 180), (60.3, 8, 180))
    moderate = score((60, 8, 180), (61.2, 8, 180))
    strong = score((60, 8, 180), (63.5, 8, 180))
    assert weak < moderate < strong and weak >= 70


def test_wind_speed_score_grows_with_excess():
    over_a_little = score((70, 8, 180), (68, 11, 180))
    over_a_lot = score((70, 8, 180), (68, 14, 180))
    assert over_a_little < over_a_lot


def test_more_flags_raise_the_score_but_not_the_band():
    one = score((57, 8, 180), (61, 8, 180))
    several = score((57, 4, 180), (61, 13, 300))
    assert one < several <= 100


def test_caution_never_reaches_stop_band():
    many = Pesticide(name="Fine", droplet_size="fine", volatility="moderate")
    d = decide(make_reading((90, 9.5, 180), (86, 9.8, 230)), many, now=NOW)
    assert d.status == Status.CAUTION and d.score <= 69


def test_no_data_scores_100(now):
    d = decide(Reading(NOW, []), now=now)
    assert (d.status, d.score) == (Status.STOP, 100)


def test_flags_are_sorted_worst_first(now):
    d = decide(make_reading((57, 4, 180), (61, 13, 300)), now=now)
    assert [f.score for f in d.flags] == sorted((f.score for f in d.flags), reverse=True)
    assert d.flags[0].severity == Severity.STOP


def test_ground_station_scores_lower_than_full_tool_in_demo(now):
    reading = SimulatedSource("evening_inversion", now=now).get_reading()
    ground = single_station_decision(reading)
    full = decide(reading, now=now)
    assert ground.score == 0 and full.score >= 90


def test_score_is_in_serialized_decision_and_log_rows(tmp_path, now):
    reading = SimulatedSource("evening_inversion", now=now).get_reading()
    d = decide(reading, now=now)
    assert d.to_dict()["score"] == d.score and d.to_dict()["flags"][0]["score"] == d.flags[0].score
    log = DecisionLog(tmp_path / "log.jsonl")
    log.append(reading, DEFAULT_PESTICIDE, d, logged_at=now)
    assert log.rows()[0]["score"] == d.score
