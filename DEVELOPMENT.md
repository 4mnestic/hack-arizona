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
.venv/bin/pytest --cov=spraywait
```
