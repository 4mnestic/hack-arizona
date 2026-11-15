# Development notes

Setup, usage, and layout for the `spraywait` package. (Project overview is in README.md, team plan in docs/PLAN.md, a file-level diagram in docs/FLOW.md.)

## Setup

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
# or: python -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## Usage

```python
from spraywait import decide, single_station_decision
from spraywait.weather import SimulatedSource
from spraywait.pesticides import LocalPesticideDB
from spraywait.log import DecisionLog

reading = SimulatedSource("evening_inversion").get_reading()   # 5 ft + 30 ft
pesticide = LocalPesticideDB().get("Captan")

d = decide(reading, pesticide)                 # Status.STOP + plain-language reasons
single_station_decision(reading)               # what a ground-only station would say (GO)
DecisionLog().append(reading, pesticide, d)    # appends to time-stamped spray_log.jsonl
```

Scenarios (each isolates one thing; `illustrates` holds the demo note and `expect` the ground-alone vs SprayWait outcome, checked by tests): `evening_inversion` (hidden inversion), `inversion_forming`, `shear_aloft`, `wind_direction_shift`, `clear_midday`, `hot_afternoon`, `too_windy`, `dead_calm`.

## How it works, step by step

**1. Weather input** (`spraywait/weather/`)
We get the weather at two or more heights, for example 5 ft and 30 ft. Each height has a temperature, a wind speed, and a wind direction. All of that together, with a timestamp, is one "reading". Right now readings come from built-in example scenarios. Later they can come from a web forecast or a real sensor without changing anything else.

**2. Pesticide input** (`spraywait/pesticides/`)
We look up the pesticide being sprayed and get its properties: how easily it evaporates, how fine its droplets are, and its label's wind and temperature limits. Right now this comes from a small built-in list. Later it can come from Joy's CSV or an online database.

**3. Checks** (`spraywait/checks/`)
The reading and the pesticide go through five separate checks. Each check looks at one thing and raises a warning if something is wrong. A warning is either CAUTION or STOP and comes with a sentence explaining why.
- Data quality: is there any data, is it recent, do we have more than one height?
- Inversion: is the air warmer up high than at the ground? If so, spray gets trapped near the ground.
- Wind speed: is the wind too calm or too strong at any height?
- Wind shear: is the wind much stronger, or blowing a different direction, above the trees than at the ground?
- Volatility: is it too hot for this pesticide, or is it windy enough to carry fine droplets?

**4. Decision** (`spraywait/decision.py`)
All the warnings are collected. If any says STOP, the answer is STOP. If any says CAUTION, the answer is CAUTION. If there are none, the answer is GO. Every warning's sentence is included so the applicator sees every reason.
There is also a "ground station only" version that uses just the lowest height. It shows what a normal weather station would say, so we can show the difference in the demo.

**5. Record** (`spraywait/log.py`)
Each reading, the pesticide, the warnings, and the final answer are written to a log file with a timestamp.

**6. Running it** (`demo.py`, `tests/`)
`demo.py` runs one scenario and prints both answers. The tests run every check with known inputs and confirm the answers are right.

## Layout

- `spraywait/weather/` — inputs. `Reading` = timestamp + list of `Level`s (height, temp, wind speed, wind direction). `WeatherSource` is the interface; implementations: `SimulatedSource` (scenarios), `StationSource` (farm station payloads, dummy for now), `FarmSource` (pushed readings), `PublicSource` (Open-Meteo). See Web app below.
- `spraywait/pesticides/` — `PesticideDB` interface; `LocalPesticideDB` reads `pesticides.json`. Swap in an online DB with the same interface.
- `spraywait/checks/` — one file per check (inversion, wind speed, wind shear, volatility, data quality). Each returns a list of `Flag(severity, check, reason)`. Thresholds are module constants at the top of each file.
- `spraywait/decision.py` — `decide()` runs every check; the most severe flag sets GO/CAUTION/STOP and all reasons are reported. `single_station_decision()` uses only the lowest level (for demo comparison).
- `spraywait/log.py` — `DecisionLog` appends JSONL entries and can flatten them into table rows.

## Testing

```bash
.venv/bin/pytest --cov=spraywait --cov=api --cov=tools
```

## Web app

`api/main.py` is a FastAPI app; `web/` is the PWA it serves (plain HTML/JS, no build step).

```bash
FARM_API_KEY=devkey .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

- `/` is live mode. The farmer picks a **pesticide** and **nozzle** only; weather comes from the farm station. `FARM_WEATHER=dummy` (default) reads the simulated station; `FARM_WEATHER=push` uses the latest payload the real station posted (none yet gives STOP). `FARM_WEATHER=mesonet` replays the Mesonet CSV in real time inside the app.
- `/log` shows the time-stamped log (Live/Demo tabs, status-changes filter, CSV download). Every new reading checked is logged once per pesticide/nozzle (refreshes don't duplicate). Stored as JSONL at `SPRAY_LOG_PATH` (default `spray_log.jsonl`); on Render's free plan it resets when the server sleeps.
- `/demo` is demo mode. It adds a conditions picker: simulated scenarios, or public forecast data (Open-Meteo) at the phone's location.

| Route | Purpose |
|---|---|
| `GET /api/pesticides`, `/api/nozzles`, `/api/scenarios` | Picker options |
| `POST /api/decision` | `{pesticide, nozzle, source: farm\|station\|simulated\|public, scenario, lat, lon}` returns decision, ground-only comparison, reading, resolved spray profile |
| `GET /api/log?mode=live\|demo&changes_only=&limit=` | Log entries, newest first; `changed_from` marks status changes (alerts) |
| `GET /api/log.csv?mode=` | Log as CSV |
| `GET /api/station` | Latest farm reading, its age, and 24 h history; each point carries the generic-label status and the checks it triggered |
| `GET /api/orchard` | Orchard location (`ORCHARD_LAT`/`ORCHARD_LON`) and the Open-Meteo hourly `forecast_url` for the browser to fetch |
| `POST /api/forecast` | `{pesticide, nozzle, hourly}` (Open-Meteo `hourly` block) returns per-hour status, `next_go` window and `worsens` |
| `POST /api/readings` | Farm station pushes its payload (format below) with header `X-Farm-Key: $FARM_API_KEY` |

- `spraywait/nozzles/`: nozzle catalog (`nozzles.json`); ASABE droplet class maps to the engine's fine/medium/coarse.
- `spraywait/spray_setup.py`: `SpraySetup().resolve(pesticide, nozzle)` returns the `Pesticide` the checks take, with droplet size, VMD, and pressure from the nozzle.
- `spraywait/weather/station.py`: the farm-station payload format (vendor-style: UTC time, metric units, one record per sensor with height), `parse_station_payload()` to turn it into a `Reading`, and `DummyStation`, a simulated 1.5 m / 9.1 m mast whose weather follows the local clock (inversion after dusk, mixing by day). Wiring a real station means replacing the payload supplier, not the checks. The parser pairs a wind-only height with the nearest temperature-only height within 4 ft (masts often mount anemometers just above the thermometer).
- `spraywait/weather/mesonet.py`: `MesonetStation` replays a Mesonet 5-minute day file (TIME in UTC) as a live station. At UTC clock time HH:MM it reports that row in the payload format above. Temperature is at 1.5 m and 9 m, wind speed at 2 m and 10 m, wind direction at 10 m only. Missing-data codes (-99x) become null. `MesonetFeed` runs it inside the app (`FARM_WEATHER=mesonet`): with no timer, each time the app needs weather it stores every reading that has come due since the last sync (backfilling `MESONET_BACKFILL_HOURS`, default 6, on first use). That also fills the gap after Render's free plan wakes from sleep. `MESONET_SHIFT_HOURS` (or `--shift-hours` on the tool) replays the row that many hours ahead of the clock while stamping the real time. The shift is rounded to 5 minutes. Render uses 0.75, which puts the recorded evening inversion (00:00 to 03:05 UTC in the file) on about 4:15–7:30 pm Arizona, with no data gap from 4:10 pm on.
- `spraywait/weather/farm.py`: in-memory store of the latest pushed reading plus 24 h of history for `/station` (resets when the server restarts).
- `spraywait/weather/public.py`: Open-Meteo, 2 m temperature + 10 m wind near the ground, 80 m aloft. `PublicSource` (current conditions) is demo only; `forecast_url()` and `parse_hourly()` handle the hourly forecast for spray windows. The browser fetches it, because Render's shared outbound IPs get rate-limited (HTTP 429) by Open-Meteo.
- `spraywait/windows.py`: `plan_windows(forecast, pesticide)` runs the normal checks on each forecast hour and returns per-hour status, the next GO window (first run of consecutive GO hours), and the first hour that is worse than now.
- `tools/push_reading.py`: stand-in farm station; pushes one dummy-station payload.
- `tools/mesonet_station.py`: runs `MesonetStation` as a process that posts to `/api/readings` on every 5-minute UTC boundary. With `--backfill-hours`, it first uploads the earlier readings, like a datalogger sending its buffer.

## Deploy (Render)

`render.yaml` is a Render Blueprint (free plan, deploys the `dev` branch, `FARM_WEATHER=mesonet`, generates `FARM_API_KEY`). In Render: **New > Blueprint**, connect the GitHub repo, apply. The free plan sleeps after ~15 idle minutes, so the first request can take up to a minute.
