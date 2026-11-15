"""FastAPI backend: wraps the spraywait engine in a JSON API and serves the PWA.

Live mode (/) uses the farm's own station data, pushed to POST /api/readings.
Demo mode (/demo) can also use simulated scenarios or public forecast data.
"""

import os
import secrets
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from spraywait import decide, single_station_decision
from spraywait.pesticides import DEFAULT_PESTICIDE
from spraywait.spray_setup import SpraySetup
from spraywait.weather import (SCENARIOS, FarmSource, FarmStationStore, Level, PublicSource, Reading,
                               SimulatedSource, WeatherSource)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
DEFAULT_SCENARIO = "evening_inversion"

app = FastAPI(title="Spray or Wait", version="0.2.0")
setup = SpraySetup()
farm = FarmStationStore()


class LevelIn(BaseModel):
    height_ft: float
    temp_f: float
    wind_mph: float
    wind_dir_deg: float | None = None


class ReadingIn(BaseModel):
    timestamp: datetime | None = None
    levels: list[LevelIn]
    source: str = "farm"


class DecisionRequest(BaseModel):
    pesticide: str | None = None
    nozzle: str | None = None
    source: Literal["farm", "simulated", "public"] = "farm"
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


def _naive_local(ts: datetime) -> datetime:
    """Engine timestamps are naive local time; convert timezone-aware input."""
    return ts.astimezone().replace(tzinfo=None) if ts.tzinfo else ts


@app.post("/api/readings", status_code=201)
def push_reading(reading: ReadingIn, x_farm_key: str | None = Header(default=None)) -> dict:
    """Farm weather station pushes its latest multi-height reading here."""
    expected = os.environ.get("FARM_API_KEY")
    if not expected:
        raise HTTPException(503, "farm ingest is not configured (set FARM_API_KEY)")
    if not x_farm_key or not secrets.compare_digest(x_farm_key, expected):
        raise HTTPException(401, "bad or missing X-Farm-Key")
    if not reading.levels:
        raise HTTPException(422, "reading needs at least one level")
    farm.push(Reading(
        timestamp=_naive_local(reading.timestamp) if reading.timestamp else datetime.now(),
        levels=[Level(**lv.model_dump()) for lv in reading.levels],
        source=reading.source,
    ))
    return {"stored": farm.latest.to_dict()}


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
    return {
        "decision": decide(reading, pesticide).to_dict(),
        "ground_only": ground.to_dict() if ground else None,
        "reading": reading.to_dict(),
        "pesticide": asdict(pesticide),
    }


@app.get("/demo", include_in_schema=False)
def demo_page() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
