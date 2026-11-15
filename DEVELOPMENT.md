# Development notes

Setup, usage, and layout for the `spraywait` package. (Project overview and team plan live in README.md.)

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

Scenarios: `evening_inversion` (demo), `clear_midday`, `too_windy`, `dead_calm`, `shear_aloft`, `hot_afternoon`.

## Layout

- `spraywait/weather/` — inputs. `Reading` = timestamp + list of `Level`s (height, temp, wind speed, wind direction). `WeatherSource` is the interface; `SimulatedSource` is the only implementation so far. Add NWS/sensor sources by subclassing it.
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

- `/` is live mode. The farmer picks a **pesticide** and **nozzle** only; weather comes from the farm station. `FARM_WEATHER=dummy` (default) reads the simulated station; `FARM_WEATHER=push` uses the latest payload the real station posted (none yet gives STOP).
- `/demo` is demo mode. It adds a conditions picker: simulated scenarios, or public forecast data (Open-Meteo) at the phone's location.

| Route | Purpose |
|---|---|
| `GET /api/pesticides`, `/api/nozzles`, `/api/scenarios` | Picker options |
| `POST /api/decision` | `{pesticide, nozzle, source: farm\|station\|simulated\|public, scenario, lat, lon}` returns decision, ground-only comparison, reading, resolved spray profile |
| `POST /api/readings` | Farm station pushes its payload (format below) with header `X-Farm-Key: $FARM_API_KEY` |

- `spraywait/nozzles/`: nozzle catalog (`nozzles.json`); ASABE droplet class maps to the engine's fine/medium/coarse.
- `spraywait/spray_setup.py`: `SpraySetup().resolve(pesticide, nozzle)` returns the `Pesticide` the checks take, with droplet size, VMD, and pressure from the nozzle.
- `spraywait/weather/station.py`: the farm-station payload format (vendor-style: UTC time, metric units, one record per sensor with height), `parse_station_payload()` to turn it into a `Reading`, and `DummyStation`, a simulated 1.5 m / 9.1 m mast whose weather follows the local clock (inversion after dusk, mixing by day). Wiring a real station means replacing the payload supplier, not the checks.
- `spraywait/weather/farm.py`: in-memory store of the latest pushed reading (resets when the server restarts).
- `spraywait/weather/public.py`: Open-Meteo, 2 m temperature + 10 m wind near the ground, 80 m aloft. Demo only.
- `tools/push_reading.py`: stand-in farm station; pushes one dummy-station payload.

## Deploy (Render)

`render.yaml` is a Render Blueprint (free plan, deploys the `dev` branch, `FARM_WEATHER=dummy`, generates `FARM_API_KEY`). In Render: **New > Blueprint**, connect the GitHub repo, apply. The free plan sleeps after ~15 idle minutes, so the first request can take up to a minute.
