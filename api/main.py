"""FastAPI backend: wraps the spraywait engine in a JSON API and serves the PWA.

Live mode (/) uses the farm's station. FARM_WEATHER=dummy (default) reads the simulated
station; FARM_WEATHER=push uses the latest payload the real station POSTed to /api/readings.
Demo mode (/demo) can also use simulated scenarios or public forecast data.
"""

import csv
import io
import os
import secrets
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from spraywait import decide, single_station_decision
from spraywait.log import DecisionLog
from spraywait.pesticides import DEFAULT_PESTICIDE
from spraywait.spray_setup import SpraySetup
from spraywait.weather import (SCENARIOS, FarmSource, FarmStationStore, PublicSource, SimulatedSource,
                               StationSource, WeatherSource, parse_station_payload)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
DEFAULT_SCENARIO = "evening_inversion"

app = FastAPI(title="Spray or Wait", version="0.2.0")
setup = SpraySetup()
farm = FarmStationStore()
log = DecisionLog(Path(os.environ.get("SPRAY_LOG_PATH", "spray_log.jsonl")))
_last_logged: dict[tuple, tuple] = {}


class DecisionRequest(BaseModel):
    pesticide: str | None = None
    nozzle: str | None = None
    source: Literal["farm", "station", "simulated", "public"] = "farm"
    scenario: str | None = None
    lat: float | None = None
    lon: float | None = None


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/pesticides")
def pesticides() -> list[dict]:
    db = setup.pesticides
    return [asdict(DEFAULT_PESTICIDE)] + [asdict(db.get(n)) for n in db.list()]


@app.get("/api/nozzles")
def nozzles() -> list[dict]:
    db = setup.nozzles
    return [asdict(db.get(n)) | {"droplet_size": db.get(n).droplet_size} for n in db.list()]


@app.get("/api/scenarios")
def scenarios() -> list[dict]:
    return [{"id": k, "title": v["title"], "description": v["description"]} for k, v in SCENARIOS.items()]


@app.post("/api/readings", status_code=201)
def push_reading(payload: dict, x_farm_key: str | None = Header(default=None)) -> dict:
    """The farm's station pushes its payload here (format: spraywait/weather/station.py)."""
    expected = os.environ.get("FARM_API_KEY")
    if not expected:
        raise HTTPException(503, "farm ingest is not configured (set FARM_API_KEY)")
    if not x_farm_key or not secrets.compare_digest(x_farm_key, expected):
        raise HTTPException(401, "bad or missing X-Farm-Key")
    try:
        reading = parse_station_payload(payload)
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    if not reading.levels:
        raise HTTPException(422, "payload has no usable heights (need temp and wind)")
    farm.push(reading)
    return {"stored": reading.to_dict()}


def _source(req: DecisionRequest) -> WeatherSource:
    if req.source == "simulated":
        scenario = req.scenario or DEFAULT_SCENARIO
        if scenario not in SCENARIOS:
            raise HTTPException(404, f"unknown scenario {scenario!r}")
        return SimulatedSource(scenario)
    if req.source == "public":
        if req.lat is None or req.lon is None:
            raise HTTPException(422, "public weather needs lat and lon")
        return PublicSource(req.lat, req.lon)
    if req.source == "station" or os.environ.get("FARM_WEATHER", "dummy") == "dummy":
        return StationSource()
    return FarmSource(farm)


@app.post("/api/decision")
def decision(req: DecisionRequest) -> dict:
    """Decide GO/CAUTION/STOP; also returns what a ground-only station would say."""
    try:
        pesticide = setup.resolve(req.pesticide, req.nozzle)
    except KeyError as e:
        raise HTTPException(404, str(e.args[0])) from None
    source = _source(req)
    try:
        reading = source.get_reading()
    except OSError as e:
        raise HTTPException(502, f"weather source unavailable: {e}") from None
    ground = single_station_decision(reading, pesticide) if reading.levels else None
    result = decide(reading, pesticide)
    _log_if_new(req, reading, pesticide, result)
    return {
        "decision": result.to_dict(),
        "ground_only": ground.to_dict() if ground else None,
        # Engine times are naive server-local; send an explicit offset so phones show their own time.
        "reading": reading.to_dict() | {"timestamp": reading.timestamp.astimezone().isoformat()},
        "pesticide": asdict(pesticide),
    }


def _mode(req: DecisionRequest) -> str:
    return "live" if req.source == "farm" else "demo"


def _log_if_new(req, reading, pesticide, result) -> None:
    """Log once per new reading for each mode/pesticide/nozzle, so page refreshes don't duplicate."""
    stream = (_mode(req), pesticide.name, pesticide.nozzle)
    ident = (reading.source, reading.timestamp if reading.levels else None)  # "no data" logs once
    if _last_logged.get(stream) != ident:
        log.append(reading, pesticide, result, mode=_mode(req))
        _last_logged[stream] = ident


def _with_offset(ts: str) -> str:
    """Stored times are naive server-local; add the offset so browsers show local time."""
    return datetime.fromisoformat(ts).astimezone().isoformat()


@app.get("/api/log")
def get_log(mode: Literal["live", "demo"] = "live", limit: int = 200, changes_only: bool = False) -> list[dict]:
    """Newest-first log entries; `changed_from` marks status changes (alerts)."""
    entries = [e for e in log.history(mode) if e["changed_from"] or not changes_only]
    out = []
    for e in reversed(entries[-limit:] if limit > 0 else entries):
        e["logged_at"] = _with_offset(e["logged_at"])
        e["reading"]["timestamp"] = _with_offset(e["reading"]["timestamp"])
        out.append(e)
    return out


@app.get("/api/log.csv")
def get_log_csv(mode: Literal["live", "demo"] = "live") -> Response:
    rows = log.rows(mode)
    for r in rows:
        r["time"] = _with_offset(r["time"])
    fields = list(dict.fromkeys(k for r in rows for k in r)) or ["time", "status"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="spray-log-{mode}.csv"'})


@app.get("/log", include_in_schema=False)
def log_page() -> FileResponse:
    return FileResponse(WEB_DIR / "log.html")


@app.get("/demo", include_in_schema=False)
def demo_page() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
