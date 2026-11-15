from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import api.main as main
import spraywait.weather.public as public
from spraywait.decision import Status
from spraywait.pesticides import DEFAULT_PESTICIDE
from spraywait.weather import Level, Reading
from spraywait.windows import plan_windows

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


def om_hourly(kinds, start=None):
    """Open-Meteo-style hourly block (UTC times) for the given GO/CAUTION/STOP kinds."""
    start = start or datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    out = {"time": [], **{f: [] for f in public.FIELDS}}
    for i, ((t_lo, w_lo, d_lo), (t_hi, w_hi, d_hi)) in enumerate(kinds):
        out["time"].append((start + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M"))
        for f, v in [("temperature_2m", t_lo), ("wind_speed_10m", w_lo), ("wind_direction_10m", d_lo),
                     ("temperature_80m", t_hi), ("wind_speed_80m", w_hi), ("wind_direction_80m", d_hi)]:
            out[f].append(v)
    return out


def test_parse_hourly_converts_and_skips_gaps():
    """Each hour becomes a 2-level reading (UTC to naive local); hours with nulls are skipped."""
    h = om_hourly([GO, STOP], start=datetime(2026, 11, 16, tzinfo=timezone.utc))
    h["temperature_2m"][1] = None
    rs = public.parse_hourly(h)
    assert len(rs) == 1 and rs[0].timestamp.tzinfo is None and rs[0].source == "forecast:open-meteo"
    assert rs[0].timestamp == datetime(2026, 11, 16, tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
    lo, hi = rs[0].sorted_levels()
    assert (lo.temp_f, hi.temp_f, hi.wind_mph) == (70, 68, 6)


def test_parse_hourly_caps_hours():
    """No more than max_hours are read, whatever the client sends."""
    assert len(public.parse_hourly(om_hourly([GO] * 5), max_hours=3)) == 3


@pytest.mark.parametrize("bad", [{}, {"time": ["x"]}, {**om_hourly([GO]), "time": ["not a time"]},
                                 {**om_hourly([GO]), "wind_speed_80m": ["fast"]}, {**om_hourly([GO]), "temperature_2m": []}])
def test_parse_hourly_rejects_malformed(bad):
    """Missing fields, bad times, non-numbers, or short arrays are a ValueError."""
    with pytest.raises(ValueError):
        public.parse_hourly(bad)


def test_forecast_url_asks_for_hourly_fields():
    """The browser's forecast URL requests every field the parser needs, 24 hours, UTC."""
    url = public.forecast_url(37.6, -121.0)
    assert "latitude=37.6" in url and "forecast_hours=24" in url and "timezone=GMT" in url
    assert all(f in url for f in public.FIELDS)


@pytest.fixture
def client():
    return TestClient(main.app)


def test_orchard_endpoint(client):
    """The orchard endpoint gives its location and the forecast URL for the browser to fetch."""
    body = client.get("/api/orchard").json()
    assert (body["lat"], body["lon"]) == main.ORCHARD and body["forecast_url"].startswith(public.URL)


def test_forecast_endpoint_plans_windows(client):
    """Posted hourly data comes back as per-hour status, the GO window, and when it worsens."""
    body = client.post("/api/forecast", json={"hourly": om_hourly([GO, GO, STOP])}).json()
    assert [h["status"] for h in body["hours"]] == ["GO", "GO", "STOP"]
    assert body["worsens"]["status"] == "STOP" and body["next_go"]["start"] == body["hours"][0]["time"]
    assert datetime.fromisoformat(body["hours"][0]["time"]).tzinfo is not None


def test_forecast_endpoint_without_window(client):
    """With STOP now and no GO hour, next_go and worsens are null."""
    body = client.post("/api/forecast", json={"hourly": om_hourly([STOP])}).json()
    assert body["next_go"] is None and body["worsens"] is None


def test_forecast_endpoint_errors(client):
    """Unknown pesticide is 404; malformed forecast data is 422."""
    assert client.post("/api/forecast", json={"pesticide": "nope", "hourly": om_hourly([GO])}).status_code == 404
    assert client.post("/api/forecast", json={"hourly": {"time": ["x"]}}).status_code == 422
