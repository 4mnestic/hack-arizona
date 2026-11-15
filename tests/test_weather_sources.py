import io
import json
from datetime import datetime, timedelta

import pytest

import spraywait.weather.public as public
import tools.push_reading as push_reading
from spraywait.weather import FarmSource, FarmStationStore, Level, PublicSource, Reading


def reading(ts):
    return Reading(ts, [Level(5, 70, 5), Level(30, 69, 6)], source="farm")


def test_farm_source_empty_until_pushed():
    """Before any push, the farm source returns a reading with no levels."""
    r = FarmSource(FarmStationStore()).get_reading()
    assert r.levels == [] and "no data" in r.source


def test_farm_store_keeps_newest():
    """An older reading arriving late does not replace a newer one."""
    store, now = FarmStationStore(), datetime.now()
    store.push(reading(now))
    store.push(reading(now - timedelta(minutes=5)))
    assert FarmSource(store).get_reading().timestamp == now


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def test_public_source_parses_open_meteo(monkeypatch):
    """Open-Meteo 'current' data becomes a 2-level reading (ground and 80 m)."""
    cur = {"temperature_2m": 60.0, "temperature_80m": 62.0, "wind_speed_10m": 4.0, "wind_speed_80m": 9.0,
           "wind_direction_10m": 180, "wind_direction_80m": 250}
    seen = {}

    def fake_urlopen(url, timeout):
        seen["url"] = url
        return FakeResponse(json.dumps({"current": cur}).encode())

    monkeypatch.setattr(public, "urlopen", fake_urlopen)
    r = PublicSource(38.5, -121.7).get_reading()
    assert "latitude=38.5" in seen["url"] and "temperature_80m" in seen["url"]
    lo, hi = r.sorted_levels()
    assert (lo.height_ft, lo.temp_f, lo.wind_mph) == (6.6, 60.0, 4.0)
    assert (hi.height_ft, hi.temp_f, hi.wind_dir_deg) == (262, 62.0, 250)


def test_push_reading_posts_with_key(monkeypatch):
    """The station script posts a dummy-station payload with the farm key header."""
    sent = {}

    def fake_urlopen(req, timeout):
        sent["url"], sent["key"], sent["body"] = req.full_url, req.get_header("X-farm-key"), json.loads(req.data)
        return FakeResponse(b'{"stored": {}}')

    monkeypatch.setattr(push_reading, "urlopen", fake_urlopen)
    assert push_reading.push("http://x/", "k") == {"stored": {}}
    assert sent["url"] == "http://x/api/readings" and sent["key"] == "k"
    assert sent["body"]["station_id"] == "orchard-tower-1" and sent["body"]["sensors"]


@pytest.mark.parametrize("argv,env,code", [(["p"], "k", 2), (["p", "http://x"], None, 2), (["p", "http://x"], "k", 0)])
def test_push_reading_main(monkeypatch, capsys, argv, env, code):
    """The CLI needs a URL and FARM_API_KEY; with both it pushes and prints the response."""
    if env:
        monkeypatch.setenv("FARM_API_KEY", env)
    else:
        monkeypatch.delenv("FARM_API_KEY", raising=False)
    monkeypatch.setattr(push_reading, "push", lambda *a: {"ok": True})
    assert push_reading.main(argv) == code
