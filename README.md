# Spray or Wait

Go, Caution, or Stop for orchard pesticide spraying, with the reasons why.

<!-- TODO: screenshot of the phone showing a STOP decision and its reason -->

> **Status:** in development. See the [development plan](docs/PLAN.md).

## The problem

<!-- TODO, about 3 sentences: on calm, clear mornings, inversions trap spray, which then drifts onto neighbors, water, and bees. Growers decide by feel. Add one sourced statistic. -->

## What it does

<!-- TODO, 3 bullets: inputs (weather, pesticide, orchard) → GO / CAUTION / STOP → a plain-language reason. -->

## Demo

<!-- TODO: GIF or video link. -->

| Scenario | Decision | Reason |
|---|---|---|
| Calm, clear dawn | STOP | <!-- TODO --> |
| Same morning, volatile pesticide | STOP | <!-- TODO --> |
| Mid-morning breeze, away from sensitive areas | GO | <!-- TODO --> |

## How it works

<!-- TODO: final architecture diagram. Explain the inversion, wind, and status models in one line each. -->

### Science

<!-- TODO: one cited source per threshold (inversion detection, wind limits, volatility). -->

## Run it

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
FARM_API_KEY=devkey .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
```

- Live app: http://localhost:8000. Pick a pesticide and nozzle; weather comes from the farm's station.
- Demo app: http://localhost:8000/demo. Adds simulated scenarios and public forecast data.
- Simulate a farm station push: `FARM_API_KEY=devkey .venv/bin/python -m tools.push_reading http://localhost:8000 clear_midday`
- Tests: `.venv/bin/pytest --cov=spraywait --cov=api --cov=tools`

## Tech stack

<!-- TODO: one line. -->

## Team

<!-- TODO: names and roles, one line each. -->

## What's next

<!-- TODO: forecast of the next safe spray window, ML models. -->

---

*Advisory only. The pesticide label is the law.*
