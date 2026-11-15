import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

import api.main as main
import spraywait.weather.public as public
from spraywait.decision import Status
from spraywait.pesticides import DEFAULT_PESTICIDE
from spraywait.weather import Level, Reading
from spraywait.windows import plan_windows
from tests.test_weather_sources import FakeResponse

T0 = datetime(2026, 11, 16, 0, 0)
GO = ((70, 5, 300), (68, 6, 300))        # mixed air, moderate wind
CAUTION = ((70, 5, 300), (69.8, 6, 300))  # temps nearly equal: possible inversion
STOP = ((60, 2, 300), (64, 6, 300))       # inversion, calm below


def hour(i, kind):
    lo, hi = kind
    return Reading(T0 + timedelta(hours=i), [Level(6.6, *lo), Level(262, *hi)], source="forecast:test")


def statuses(plan):
    return [h["status"] for h in plan["hours"]]


def test_hours_get_same_checks_and_sorted():
    """Each forecast hour runs the normal checks (never flagged stale) and hours come back in time order."""
    plan = plan_windows([hour(1, STOP), hour(0, GO)], DEFAULT_PESTICIDE)
    assert statuses(plan) == [Status.GO, Status.STOP]
    assert "inversion" in plan["hours"][1]["checks"] and "data" not in plan["hours"][0]["checks"]


def test_next_go_window_spans_consecutive_go_hours():
    """From STOP now, the window is the first run of GO hours; it ends an hour after the last GO hour."""
    plan = plan_windows([hour(0, STOP), hour(1, GO), hour(2, GO), hour(3, STOP), hour(4, GO)], DEFAULT_PESTICIDE)
    assert plan["next_go"] == {"start": T0 + timedelta(hours=1), "end": T0 + timedelta(hours=3)}
    assert plan["worsens"] is None  # can't get worse than STOP


def test_go_window_breaks_on_missing_hour():
    """A gap in the forecast (skipped hour) ends the window rather than bridging it."""
    plan = plan_windows([hour(0, GO), hour(2, GO)], DEFAULT_PESTICIDE)
    assert plan["next_go"]["end"] == T0 + timedelta(hours=1)


def test_worsens_finds_first_worse_hour():
    """From GO now, `worsens` is the first later hour that is CAUTION or STOP."""
    plan = plan_windows([hour(0, GO), hour(1, GO), hour(2, CAUTION), hour(3, STOP)], DEFAULT_PESTICIDE)
    assert plan["worsens"]["time"] == T0 + timedelta(hours=2) and plan["worsens"]["status"] is Status.CAUTION
    plan = plan_windows([hour(0, CAUTION), hour(1, CAUTION), hour(2, STOP)], DEFAULT_PESTICIDE)
    assert plan["worsens"]["status"] is Status.STOP


def test_no_go_and_empty_forecast():
    """All-STOP has no window; an empty forecast has no hours, window, or worsening."""
    assert plan_windows([hour(0, STOP)], DEFAULT_PESTICIDE)["next_go"] is None
    assert plan_windows([], DEFAULT_PESTICIDE) == {"hours": [], "next_go": None, "worsens": None}


def test_hourly_forecast_parses_and_skips_gaps(monkeypatch):
    """Open-Meteo hourly data becomes one 2-level reading per hour (UTC to local); hours with nulls are skipped."""
    hourly = {"time": ["2026-11-16T00:00", "2026-11-16T01:00"], "temperature_2m": [60, None],
              "temperature_80m": [63, 61], "wind_speed_10m": [3, 4], "wind_speed_80m": [8, 9],
              "wind_direction_10m": [200, 210], "wind_direction_80m": [260, 270]}
    seen = {}

    def fake_urlopen(url, timeout):
        seen["url"] = url
        return FakeResponse(json.dumps({"hourly": hourly}).encode())

    monkeypatch.setattr(public, "urlopen", fake_urlopen)
    rs = public.hourly_forecast(37.6, -121.0)
    assert "forecast_hours=24" in seen["url"] and "hourly=" in seen["url"]
    assert len(rs) == 1 and rs[0].timestamp.tzinfo is None and rs[0].source == "forecast:open-meteo"
    lo, hi = rs[0].sorted_levels()
    assert (lo.temp_f, hi.temp_f, hi.wind_mph) == (60, 63, 8)


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "_forecasts", {})
    return TestClient(main.app)


def fake_forecast(calls):
    def f(lat, lon):
        calls.append((lat, lon))
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        return [Reading(now + timedelta(hours=i), hour(i, k).levels, "forecast:test")
                for i, k in enumerate([GO, GO, STOP])]
    return f


def test_forecast_endpoint_and_cache(client, monkeypatch):
    """The endpoint returns hours, window and worsening at the orchard by default, and caches per location."""
    calls = []
    monkeypatch.setattr(main, "hourly_forecast", fake_forecast(calls))
    body = client.get("/api/forecast").json()
    assert [h["status"] for h in body["hours"]] == ["GO", "GO", "STOP"]
    assert body["worsens"]["status"] == "STOP" and body["next_go"]["start"] == body["hours"][0]["time"]
    assert datetime.fromisoformat(body["hours"][0]["time"]).tzinfo is not None
    assert body["location"] == {"lat": main.ORCHARD[0], "lon": main.ORCHARD[1]}
    client.get("/api/forecast")
    client.get("/api/forecast?lat=1&lon=2")
    assert calls == [main.ORCHARD, (1.0, 2.0)]


def test_forecast_endpoint_without_window(client, monkeypatch):
    """With no GO hour and STOP now, next_go and worsens are null."""
    monkeypatch.setattr(main, "hourly_forecast", lambda lat, lon: [hour(0, STOP)])
    body = client.get("/api/forecast").json()
    assert body["next_go"] is None and body["worsens"] is None


def test_forecast_endpoint_errors(client, monkeypatch):
    """Unknown pesticide is 404; a failed forecast fetch is 502."""
    assert client.get("/api/forecast?pesticide=nope").status_code == 404

    def boom(lat, lon):
        raise OSError("down")
    monkeypatch.setattr(main, "hourly_forecast", boom)
    assert client.get("/api/forecast").status_code == 502
