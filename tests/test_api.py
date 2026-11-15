from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import api.main as main
from spraywait.weather import FarmStationStore, Level, Reading

KEY = "test-key"


def sensors(lo_ms=2.4, hi_ms=2.7):
    """Clear midday: ~70F/5mph at 1.5 m, ~68.6F/6mph at 9.1 m, metric like a real logger."""
    out = []
    for h, c, ms, d in [(1.5, 21.1, lo_ms, 300), (9.1, 20.3, hi_ms, 305)]:
        out += [{"type": "air_temp", "height_m": h, "value": c, "unit": "C"},
                {"type": "wind_speed", "height_m": h, "value": ms, "unit": "m/s"},
                {"type": "wind_dir", "height_m": h, "value": d, "unit": "deg"}]
    return out


def payload(sensor_list=None, **extra):
    return {"station_id": "north-block", "observed_at": datetime.now(timezone.utc).isoformat(),
            "sensors": sensors() if sensor_list is None else sensor_list, **extra}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("FARM_API_KEY", KEY)
    monkeypatch.setenv("FARM_WEATHER", "push")
    monkeypatch.setattr(main, "farm", FarmStationStore())
    return TestClient(main.app)


def push(client, body=None, key=KEY):
    return client.post("/api/readings", json=body or payload(), headers={"X-Farm-Key": key})


def test_health(client):
    """Health endpoint responds ok."""
    assert client.get("/api/health").json() == {"status": "ok"}


def test_pesticides_lists_default_first(client):
    """Pesticide list starts with the generic label-defaults entry and includes the JSON products."""
    names = [p["name"] for p in client.get("/api/pesticides").json()]
    assert names[0] == "Generic (label defaults)"
    assert "Captan" in names


def test_nozzles_include_droplet_size(client):
    """Nozzle list carries both the ASABE class and the mapped droplet size."""
    items = client.get("/api/nozzles").json()
    assert items and all({"name", "asabe_class", "droplet_size"} <= n.keys() for n in items)


def test_scenarios_have_ids_and_titles(client):
    """Every simulated scenario is listed with an id, title, and description."""
    items = client.get("/api/scenarios").json()
    assert any(s["id"] == "evening_inversion" for s in items)
    assert all({"id", "title", "description"} <= s.keys() for s in items)


def test_live_push_mode_without_farm_data_is_stop(client):
    """Push-mode live with no farm reading yet fails safe to STOP and skips the ground comparison."""
    body = client.post("/api/decision", json={}).json()
    assert body["decision"]["status"] == "STOP"
    assert body["ground_only"] is None
    assert body["reading"]["levels"] == []


def test_live_uses_pushed_farm_payload(client):
    """After the station pushes a clear payload, live mode says GO using it (UTC time not seen as stale)."""
    assert push(client).status_code == 201
    body = client.post("/api/decision", json={"pesticide": "Captan", "nozzle": "Flat fan (standard)"}).json()
    assert body["decision"]["status"] == "GO"
    assert body["reading"]["source"] == "farm station north-block"
    assert body["pesticide"]["nozzle"] == "Flat fan (standard)"


def test_live_dummy_mode_uses_simulated_station(client, monkeypatch):
    """With FARM_WEATHER=dummy, live mode reads the dummy station without any push."""
    monkeypatch.setenv("FARM_WEATHER", "dummy")
    body = client.post("/api/decision", json={}).json()
    assert body["reading"]["source"].startswith("farm station orchard-tower-1")
    assert len(body["reading"]["levels"]) == 2


def test_demo_station_source(client):
    """source=station uses the dummy station even in push mode."""
    body = client.post("/api/decision", json={"source": "station"}).json()
    assert len(body["reading"]["levels"]) == 2


def test_reading_timestamp_has_offset(client):
    """Response timestamps carry a UTC offset so the phone shows correct local time."""
    ts = client.post("/api/decision", json={"source": "station"}).json()["reading"]["timestamp"]
    assert datetime.fromisoformat(ts).tzinfo is not None


@pytest.mark.parametrize("key,status", [("wrong", 401), (None, 401)])
def test_push_rejects_bad_key(client, key, status):
    """Pushing without the right farm key is rejected."""
    headers = {"X-Farm-Key": key} if key else {}
    assert client.post("/api/readings", json=payload(), headers=headers).status_code == status


def test_push_disabled_without_configured_key(client, monkeypatch):
    """Ingest returns 503 when the server has no FARM_API_KEY."""
    monkeypatch.delenv("FARM_API_KEY")
    assert push(client).status_code == 503


@pytest.mark.parametrize("body", [payload([]), {"sensors": []}, payload([{"type": "air_temp", "height_m": 1, "value": 1, "unit": "X"}])])
def test_push_rejects_unusable_payload(client, body):
    """Payloads with no usable heights, no timestamp, or unknown units are 422."""
    assert push(client, body).status_code == 422


def test_demo_inversion_scenario(client):
    """Simulated evening inversion: STOP, while ground-only says otherwise."""
    body = client.post("/api/decision", json={"source": "simulated"}).json()
    assert body["decision"]["status"] == "STOP"
    assert body["ground_only"]["status"] != "STOP"


def test_nozzle_changes_decision(client):
    """A fine-droplet nozzle in a breeze adds a droplet-size caution that a coarse nozzle does not."""
    push(client, payload(sensors(lo_ms=3.4, hi_ms=3.6)))
    fine = client.post("/api/decision", json={"nozzle": "Disc-core hollow cone"}).json()["decision"]
    coarse = client.post("/api/decision", json={"nozzle": "Air-induction hollow cone"}).json()["decision"]
    assert "droplet_size" in [f["check"] for f in fine["flags"]]
    assert "droplet_size" not in [f["check"] for f in coarse["flags"]]


def test_public_source(client, monkeypatch):
    """Public mode builds a PublicSource from lat/lon and returns its reading."""
    reading = Reading(datetime.now(), [Level(6.6, 70, 5, 300), Level(262, 68, 6, 300)], source="public:test")
    monkeypatch.setattr(main.PublicSource, "get_reading", lambda self: reading)
    body = client.post("/api/decision", json={"source": "public", "lat": 38.5, "lon": -121.7}).json()
    assert body["reading"]["source"] == "public:test"


def test_public_source_failure_is_502(client, monkeypatch):
    """A network failure fetching public weather returns 502."""
    def boom(self):
        raise OSError("offline")
    monkeypatch.setattr(main.PublicSource, "get_reading", boom)
    assert client.post("/api/decision", json={"source": "public", "lat": 1, "lon": 2}).status_code == 502


def test_public_source_needs_coordinates(client):
    """Public mode without lat/lon is a 422."""
    assert client.post("/api/decision", json={"source": "public"}).status_code == 422


@pytest.mark.parametrize("payload", [
    {"pesticide": "Nope"}, {"nozzle": "Nope"}, {"source": "simulated", "scenario": "nope"},
])
def test_unknown_inputs_404(client, payload):
    """Unknown pesticide, nozzle, or scenario names return 404."""
    assert client.post("/api/decision", json=payload).status_code == 404


@pytest.mark.parametrize("path", ["/", "/demo"])
def test_serves_pwa_pages(client, path):
    """Both the live and demo URLs serve the PWA page."""
    assert "Spray or Wait" in client.get(path).text


def test_manifest(client):
    """The web app manifest is served and installable as standalone."""
    assert client.get("/manifest.json").json()["display"] == "standalone"
