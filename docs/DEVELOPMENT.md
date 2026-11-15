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

Scenarios: `evening_inversion` (demo), `clear_midday`, `too_windy`, `dead_calm`, `shear_aloft`, `hot_afternoon`.

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

- `spraywait/weather/` — inputs. `Reading` = timestamp + list of `Level`s (height, temp, wind speed, wind direction). `WeatherSource` is the interface; `SimulatedSource` is the only implementation so far. Add NWS/sensor sources by subclassing it.
- `spraywait/pesticides/` — `PesticideDB` interface; `LocalPesticideDB` reads `pesticides.json`. Swap in an online DB with the same interface.
- `spraywait/checks/` — one file per check (inversion, wind speed, wind shear, volatility, data quality). Each returns a list of `Flag(severity, check, reason)`. Thresholds are module constants at the top of each file.
- `spraywait/decision.py` — `decide()` runs every check; the most severe flag sets GO/CAUTION/STOP and all reasons are reported. `single_station_decision()` uses only the lowest level (for demo comparison).
- `spraywait/log.py` — `DecisionLog` appends JSONL entries and can flatten them into table rows.

## Testing

```bash
.venv/bin/pytest --cov=spraywait
```
