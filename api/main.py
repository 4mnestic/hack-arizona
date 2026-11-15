"""FastAPI backend: wraps the spraywait engine in a JSON API and serves the PWA.

Live mode (/) uses the farm's station. FARM_WEATHER=dummy (default) reads the simulated
station; FARM_WEATHER=push uses the latest payload the real station POSTed to /api/readings;
FARM_WEATHER=mesonet replays the Mesonet CSV (MESONET_CSV) in real time inside the app,
MESONET_SHIFT_HOURS ahead of the clock.
Demo mode (/demo) can also use simulated scenarios or public forecast data.
"""

import csv
import io
import os
import secrets
from dataclasses import asdict
from datetime import datetime, timedelta
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
from spraywait.weather import (SCENARIOS, FarmSource, FarmStationStore, MesonetFeed, MesonetStation,
                               PublicSource, SimulatedSource, StationSource, WeatherSource,
                               parse_station_payload)
from spraywait.weather.mesonet import DEFAULT_CSV
from spraywait.weather.public import hourly_forecast
from spraywait.windows import plan_windows

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
DEFAULT_SCENARIO = "evening_inversion"

app = FastAPI(title="Spray or Wait", version="0.2.0")
setup = SpraySetup()
farm = FarmStationStore()
log = DecisionLog(Path(os.environ.get("SPRAY_LOG_PATH", "spray_log.jsonl")))
_last_logged: dict[tuple, tuple] = {}
_feed: MesonetFeed | None = None
# Orchard location for the forecast (default: an almond orchard near Modesto, CA, Central Valley).
ORCHARD = (float(os.environ.get("ORCHARD_LAT", 37.64)), float(os.environ.get("ORCHARD_LON", -120.99)))
FORECAST_TTL = timedelta(minutes=30)
_forecasts: dict[tuple, tuple] = {}


def _sync_station() -> None:
    """In mesonet mode, store every replayed reading that has come due (built on first use)."""
    global _feed
    if os.environ.get("FARM_WEATHER") != "mesonet":
        return
    if _feed is None or _feed.store is not farm:
        path = Path(os.environ.get("MESONET_CSV", DEFAULT_CSV))
        if not path.exists():
            return  # no data file: the farm store stays empty, so live mode fails safe to STOP
        backfill = timedelta(hours=float(os.environ.get("MESONET_BACKFILL_HOURS", 6)))
        shift = timedelta(hours=float(os.environ.get("MESONET_SHIFT_HOURS", 0)))
        _feed = MesonetFeed(MesonetStation(path, shift), farm, backfill)
    _feed.sync()


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


def _reading_out(reading) -> dict:
    """Reading as JSON with an explicit UTC offset (engine times are naive server-local)."""
    return reading.to_dict() | {"timestamp": reading.timestamp.astimezone().isoformat()}


@app.get("/api/station")
def station() -> dict:
    """What the farm station has reported: latest reading and the last 24 h, each with the
    generic-label status it implied at the time (pesticide-specific limits are on the main page)."""
    def point(r):
        d = decide(r, DEFAULT_PESTICIDE, now=r.timestamp)
        return _reading_out(r) | {"status": d.status.value, "checks": sorted({f.check for f in d.flags})}

    _sync_station()
    latest = farm.latest
    return {
        "weather": os.environ.get("FARM_WEATHER", "dummy"),
        "replay_shift_h": _feed.station.shift.total_seconds() / 3600 if _feed else None,
        "latest": point(latest) if latest else None,
        "age_s": int((datetime.now() - latest.timestamp).total_seconds()) if latest else None,
        "history": [point(r) for r in farm.history()],
    }


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
    _sync_station()
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
        "reading": _reading_out(reading),
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


def _forecast(lat: float, lon: float) -> list:
    """Hourly forecast for the next 24 h, cached per location for FORECAST_TTL."""
    key = (round(lat, 2), round(lon, 2))
    hit = _forecasts.get(key)
    if hit and datetime.now() - hit[0] < FORECAST_TTL:
        return hit[1]
    readings = hourly_forecast(lat, lon)
    _forecasts[key] = (datetime.now(), readings)
    return readings


@app.get("/api/forecast")
def forecast(pesticide: str | None = None, nozzle: str | None = None,
             lat: float | None = None, lon: float | None = None) -> dict:
    """Next 24 h of forecast spray status at the orchard, the next GO window, and when it next gets worse."""
    try:
        profile = setup.resolve(pesticide, nozzle)
    except KeyError as e:
        raise HTTPException(404, str(e.args[0])) from None
    lat, lon = (lat, lon) if lat is not None and lon is not None else ORCHARD
    try:
        plan = plan_windows(_forecast(lat, lon), profile)
    except (OSError, KeyError, ValueError) as e:
        raise HTTPException(502, f"forecast unavailable: {e}") from None
    t = lambda ts: ts.astimezone().isoformat()
    hour = lambda h: {"time": t(h["time"]), "status": h["status"].value, "checks": h["checks"]}
    nxt, worse = plan["next_go"], plan["worsens"]
    return {
        "location": {"lat": lat, "lon": lon},
        "hours": [hour(h) for h in plan["hours"]],
        "next_go": {"start": t(nxt["start"]), "end": t(nxt["end"])} if nxt else None,
        "worsens": hour(worse) if worse else None,
    }


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


@app.get("/station", include_in_schema=False)
def station_page() -> FileResponse:
    return FileResponse(WEB_DIR / "station.html")


@app.get("/demo", include_in_schema=False)
def demo_page() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
