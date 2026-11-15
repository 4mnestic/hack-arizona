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

## Science

#### **Temperature Inversions (Primary Drift Risk)**
Under normal atmospheric conditions, air temperature generally decreases as altitude increases.
A temperature inversion occurs when warmer air sits above cooler air near the ground, preventing normal vertical air mixing.
This creates a stable layer of air that can trap fine pesticide droplets and vapor close to the surface.
Instead of dispersing upward, airborne pesticides can travel horizontally over long distances, potentially reaching neighboring crops, workers, and nearby communities.
Inversions can be difficult to recognize because ground-level conditions may appear calm and suitable for spraying (Nowatzki, n.d.).
### **Other Factors Affecting Spray Drift**
Wind Speed: Very low wind speeds can allow droplets to remain suspended, while stronger winds can carry droplets beyond the target area.
Wind Shear: Wind speed and direction can change with altitude. Winds above the orchard canopy may be stronger or travel in a different direction than winds near the ground.
Droplet Size: Smaller droplets remain airborne longer and are more easily transported by wind. Nozzle type and spray pressure influence droplet size (Nuyttens et al., 2007).
Temperature and Humidity: High temperatures and low humidity accelerate droplet evaporation, causing droplets to shrink and become more susceptible to drift.
Pesticide Volatility: Some pesticides can vaporize after application, creating additional drift risks even after spraying has stopped (Al Heidary et al., 2014).
## **How SprayWait Applies This Science**
SprayWait uses multi-height weather measurements to identify atmospheric conditions that traditional ground-level weather stations may miss.

Measures temperature and wind speed and direction at approximately 5 ft and 30 ft.
Detects potential temperature inversions by comparing temperatures at both heights.
Identifies concerning wind speeds and changes in wind direction or speed with altitude.
Generates Go, Caution, or Stop alerts based on detected drift-risk conditions.
Records weather readings and alerts with timestamps for applicator and PCA reference.
The goal of SprayWait is to help applicators recognize dangerous atmospheric conditions before and during pesticide application, reducing unintended drift and protecting surrounding crops, workers, communities, and the environment.

**SprayWait is a decision-support tool and does not replace pesticide label requirements, regulations, or professional judgment.**

References
Nowatzki, J. (n.d.). Understanding air temperature inversions relating to pesticide drift. North Dakota State University Extension. https://www.ndsu.edu/agriculture/extension/publications/understanding-air-temperature-inversions-relating-pesticide-drift
Nuyttens, D., Baetens, K., De Schampheleire, M., & Sonck, B. (2007). Effect of nozzle type, size and pressure on spray droplet characteristics. Biosystems Engineering, 97(3), 333–345. https://doi.org/10.1016/j.biosystemseng.2007.03.001
Al Heidary, M., Douzals, J. P., Sinfort, C., & Vallet, A. (2014). Influence of spray characteristics on potential spray drift of field crop sprayers: A literature review. Crop Protection, 63, 120–130. https://doi.org/10.1016/j.cropro.2014.05.006
<!-- TODO: one cited source per threshold (inversion detection, wind limits, volatility). -->

## Run it

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
FARM_API_KEY=devkey .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
```

- Live app: http://localhost:8000. Pick a pesticide and nozzle; weather comes from the farm's station (simulated until a real one is connected).
- Demo app: http://localhost:8000/demo. Adds simulated scenarios and public forecast data.
- Station page: http://localhost:8000/station. What the farm station is reporting: readings at each height, a 24-hour chart, and the spray status over time.
- Farm station from real data: start the server with `FARM_WEATHER=mesonet` (the deployed default) to replay one day of Oklahoma Mesonet readings (`data/mesonet_data_files.csv`) in real time, one reading every 5 minutes, starting with the last 6 hours (`MESONET_BACKFILL_HOURS`). The deployed app sets `MESONET_SHIFT_HOURS=1`, so it replays the recorded day one hour ahead of the clock. This is demo data: from 4 to 7 pm Arizona time it replays the recorded evening inversion, when a ground station alone says GO and the 30 ft sensor makes it STOP. The file has no readings for the 2 hours before that (1:50 to 4 pm with the shift).
- Or run that replay as a separate station posting over the network (server with `FARM_WEATHER=push`): `FARM_API_KEY=devkey .venv/bin/python -m tools.mesonet_station http://localhost:8000 --backfill-hours 6`
- Push one simulated reading instead: `FARM_API_KEY=devkey .venv/bin/python -m tools.push_reading http://localhost:8000`
- Tests: `.venv/bin/pytest --cov=spraywait --cov=api --cov=tools`

## Tech stack

<!-- TODO: one line. -->

## Team

<!-- TODO: names and roles, one line each. -->

## What's next

<!-- TODO: forecast of the next safe spray window, ML models. -->

---

*Advisory only. The pesticide label is the law.*
