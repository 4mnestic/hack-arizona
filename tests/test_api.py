from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import api.main as main
from spraywait.weather import FarmStationStore, Level, Reading

KEY = "test-key"
CLEAR = [{"height_ft": 5, "temp_f": 70, "wind_mph": 5, "wind_dir_deg": 300},
         {"height_ft": 30, "temp_f": 68.6, "wind_mph": 6, "wind_dir_deg": 305}]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("FARM_API_KEY", KEY)
    monkeypatch.setattr(main, "farm", FarmStationStore())
    return TestClient(main.app)


def push(client, levels=CLEAR, key=KEY, **extra):
    return client.post("/api/readings", json={"levels": levels, **extra}, headers={"X-Farm-Key": key})


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


def test_live_without_farm_data_is_stop(client):
    """Live mode with no farm reading yet fails safe to STOP and skips the ground comparison."""
    body = client.post("/api/decision", json={}).json()
    assert body["decision"]["status"] == "STOP"
    assert body["ground_only"] is None
    assert body["reading"]["levels"] == []


def test_live_uses_pushed_farm_reading(client):
    """After the farm pushes a clear reading, live mode says GO using it."""
    assert push(client, source="north block tower").status_code == 201
    body = client.post("/api/decision", json={"pesticide": "Captan", "nozzle": "Flat fan (standard)"}).json()
    assert body["decision"]["status"] == "GO"
    assert body["reading"]["source"] == "north block tower"
    assert body["pesticide"]["nozzle"] == "Flat fan (standard)"


def test_push_accepts_timezone_aware_timestamp(client):
    """A UTC timestamp from the station is converted, so the reading is not seen as stale."""
    push(client, timestamp=datetime.now(timezone.utc).isoformat())
    flags = client.post("/api/decision", json={}).json()["decision"]["flags"]
    assert "data" not in [f["check"] for f in flags]


@pytest.mark.parametrize("key,status", [("wrong", 401), (None, 401)])
def test_push_rejects_bad_key(client, key, status):
    """Pushing without the right farm key is rejected."""
    headers = {"X-Farm-Key": key} if key else {}
    assert client.post("/api/readings", json={"levels": CLEAR}, headers=headers).status_code == status


def test_push_disabled_without_configured_key(client, monkeypatch):
    """Ingest returns 503 when the server has no FARM_API_KEY."""
    monkeypatch.delenv("FARM_API_KEY")
    assert push(client).status_code == 503


def test_push_rejects_empty_levels(client):
    """A reading with no levels is a 422."""
    assert push(client, levels=[]).status_code == 422


def test_demo_inversion_scenario(client):
    """Simulated evening inversion: STOP, while ground-only says otherwise."""
    body = client.post("/api/decision", json={"source": "simulated"}).json()
    assert body["decision"]["status"] == "STOP"
    assert body["ground_only"]["status"] != "STOP"


def test_nozzle_changes_decision(client):
    """A fine-droplet nozzle in a breeze adds a droplet-size caution that a coarse nozzle does not."""
    push(client, levels=[{**CLEAR[0], "wind_mph": 7.5}, {**CLEAR[1], "wind_mph": 8}])
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
