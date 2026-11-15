# Spray or Wait

Go, Caution, or Stop for orchard pesticide spraying, with the reasons why.

**Live app:** https://spraywait.onrender.com · works on any phone; install it from the browser menu ("Add to Home Screen").

## The problem

Pesticide spray can drift beyond the orchard onto neighboring crops, workers, homes, and water. The riskiest condition, a temperature inversion, is invisible from the ground: the air feels calm and a single ground-level weather station says conditions are fine, while cooler air trapped under warmer air keeps fine droplets in a shallow layer that carries them sideways. Applicators decide by what they see and feel, plus regional forecasts that don't match the air inside the orchard.

## What it does

- **Reads weather at two heights** (about 5 ft and 30 ft) from the orchard's station, plus the pesticide and nozzle being used.
- **Says GO, CAUTION, or STOP right now**, with the reasons in plain language: inversion, wind too low or too high, wind changing with height, heat and volatility limits.
- **Alerts** when conditions get worse (GO → CAUTION/STOP, CAUTION → STOP), on screen and as a phone notification.
- **Plans ahead:** a 24-hour forecast strip shows the next safe spray window, or warns when conditions are expected to turn bad.
- **Keeps a record:** a time-stamped log of every reading, decision, and what triggered it, exportable as CSV.

## Demo

**Live** (`/`): the farm station replays a real day of Oklahoma Mesonet readings (temperature at 1.5 m and 9 m, wind at 2 m and 10 m) in real time. From about 4:30 to 8 pm Arizona time it is in a recorded evening inversion: the ground sensor alone says GO, SprayWait says STOP. The **Station** page (`/station`) charts both heights over the day; the **Log** (`/log`) shows each decision and what triggered it.

**Demo** (`/demo`): pick a scenario to see each check.

| Scenario | Ground station alone | SprayWait | Why |
|---|---|---|---|
| Evening inversion | GO | **STOP** | Warmer air at 30 ft than at 5 ft, wind shifts with height |
| Calm below, strong wind aloft | GO | **STOP** | Wind above the canopy much stronger than at the ground |
| Too windy | STOP | **STOP** | Wind above 10 mph |
| Dead calm | STOP | **STOP** | Wind below 3 mph |
| Clear midday | GO | **GO** | Air mixing normally, moderate wind |

## How it works

```
Farm station (5 ft + 30 ft)  ─┐
Pesticide + nozzle           ─┼─► Checks ─► GO / CAUTION / STOP + reasons ─► Alert, Log
Hourly forecast (24 h)       ─┘            (same checks per hour) ─► Next spray window
```

- **Inversion:** temperature at 30 ft minus 5 ft. Warmer aloft is STOP; nearly equal is CAUTION (mixing has stopped, an inversion may be forming).
- **Wind speed:** below 3 mph or above 10 mph is flagged (common guidance; the label's limits come first).
- **Wind shear:** large differences in speed or direction between heights are flagged.
- **Pesticide:** droplet size from the nozzle, plus heat and volatility limits, tighten the risk.
- **Status:** the most severe flag wins and every reason is shown. Missing or stale data is never GO.

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
### **Forecasting the Next Spray Window**
Inversions follow a daily cycle. On clear, calm evenings the ground loses heat quickly and cools the air just above it, so an inversion forms around sunset, strengthens overnight, and breaks up after sunrise as the sun warms the ground and the air starts mixing again (UC ANR, n.d.). Because this cycle is driven by the sun and the sky, weather models can forecast *when* it is likely to happen.

SprayWait uses an hourly forecast for the next 24 hours from Open-Meteo, which serves output from national weather-service forecast models. For each hour it reads temperature at 2 m (about 7 ft) and 80 m (about 260 ft), and wind speed and direction at 10 m and 80 m (Open-Meteo, n.d.). Each forecast hour is run through **the same checks as the live decision**: inversion (temperature aloft compared with the ground), wind speed limits, wind shear between heights, and the pesticide's heat and volatility limits. The tool then reports:
- **The next GO window**: the first run of consecutive hours with no drift-risk flags, for example "Next GO window: Mon 9 AM – 1 PM."
- **An early warning**: if it is safe now, the first hour that is forecast to turn CAUTION or STOP and why, for example "Expected to turn STOP around 6 PM (inversion)."

**Limits.** A forecast model describes an area several kilometres wide, not the air inside one orchard. Models are also known to have difficulty with the very stable, calm night-time air in which inversions form, and often underestimate how strong a surface inversion gets (Holtslag et al., 2013). For that reason the forecast is used only to **plan**. The decision to spray **now** always comes from the orchard's own multi-height station, which measures the inversion directly at 5 ft and 30 ft.

The U.S. National Weather Service hourly forecast was considered, but it gives conditions at the surface only, with no temperature aloft, so it cannot show a forecast inversion.

## **How SprayWait Applies This Science**
SprayWait uses multi-height weather measurements to identify atmospheric conditions that traditional ground-level weather stations may miss.

Measures temperature and wind speed and direction at approximately 5 ft and 30 ft.
Detects potential temperature inversions by comparing temperatures at both heights.
Identifies concerning wind speeds and changes in wind direction or speed with altitude.
Generates Go, Caution, or Stop alerts based on detected drift-risk conditions.
Records weather readings and alerts with timestamps for applicator and PCA reference.
Forecasts the next 24 hours with the same checks to show the next safe spray window, and warns before conditions are expected to turn bad.
The goal of SprayWait is to help applicators recognize dangerous atmospheric conditions before and during pesticide application, reducing unintended drift and protecting surrounding crops, workers, communities, and the environment.

**SprayWait is a decision-support tool and does not replace pesticide label requirements, regulations, or professional judgment.**

References
Nowatzki, J. (n.d.). Understanding air temperature inversions relating to pesticide drift. North Dakota State University Extension. https://www.ndsu.edu/agriculture/extension/publications/understanding-air-temperature-inversions-relating-pesticide-drift
Nuyttens, D., Baetens, K., De Schampheleire, M., & Sonck, B. (2007). Effect of nozzle type, size and pressure on spray droplet characteristics. Biosystems Engineering, 97(3), 333–345. https://doi.org/10.1016/j.biosystemseng.2007.03.001
Al Heidary, M., Douzals, J. P., Sinfort, C., & Vallet, A. (2014). Influence of spray characteristics on potential spray drift of field crop sprayers: A literature review. Crop Protection, 63, 120–130. https://doi.org/10.1016/j.cropro.2014.05.006
Holtslag, A. A. M., Svensson, G., Baas, P., et al. (2013). Stable atmospheric boundary layers and diurnal cycles: Challenges for weather and climate models. Bulletin of the American Meteorological Society, 94(11), 1691–1706. https://doi.org/10.1175/BAMS-D-11-00187.1
Open-Meteo. (n.d.). Weather forecast API documentation. https://open-meteo.com/en/docs
UC ANR. (n.d.). Surface inversions cause spray drift. Topics in Subtropics, University of California Agriculture and Natural Resources. https://ucanr.edu/blog/topics-subtropics/article/surface-inversions-cause-spray-drift

## Run it

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
FARM_API_KEY=devkey .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
```

- Live app: http://localhost:8000. Pick a pesticide and nozzle; weather comes from the farm's station (simulated until a real one is connected). Below the decision, a 24-hour forecast strip shows the next GO window, or when conditions are expected to turn worse. The forecast uses Open-Meteo at the orchard location (`ORCHARD_LAT`/`ORCHARD_LON`; default: near Modesto, CA).
- Demo app: http://localhost:8000/demo. Adds simulated scenarios and public forecast data.
- Station page: http://localhost:8000/station. What the farm station is reporting: readings at each height, a 24-hour chart, and the spray status over time.
- Farm station from real data: start the server with `FARM_WEATHER=mesonet` (the deployed default) to replay one day of Oklahoma Mesonet readings (`data/mesonet_data_files.csv`) in real time, one reading every 5 minutes, starting with the last 6 hours (`MESONET_BACKFILL_HOURS`). The deployed app sets `MESONET_SHIFT_HOURS=0.5`, so it replays the recorded day 30 minutes ahead of the clock. This is demo data: from about 4:30 to 8 pm Arizona time it replays the recorded evening inversion, when a ground station alone says GO and the 30 ft sensor makes it STOP. The file has no readings for the 2 hours before that (about 2:20 to 4:30 pm with the shift).
- Or run that replay as a separate station posting over the network (server with `FARM_WEATHER=push`): `FARM_API_KEY=devkey .venv/bin/python -m tools.mesonet_station http://localhost:8000 --backfill-hours 6`
- Push one simulated reading instead: `FARM_API_KEY=devkey .venv/bin/python -m tools.push_reading http://localhost:8000`
- Tests: `.venv/bin/pytest --cov=spraywait --cov=api --cov=tools`

## Tech stack

Python (FastAPI) rule engine and API, a plain HTML/JS installable web app (PWA), Open-Meteo forecasts, hosted on Render. Tested with pytest (155 tests).

## Team

- **Joy:** pesticide data and science research, app UI design.
- **Leo:** inversion and wind-shear models, the core decision engine.
- **Zach:** app, station and forecast integration, deployment, docs.

## What's next

- Real station hardware: the station data format is vendor-style, so a real mast only replaces the data source.
- Push notifications to a closed app (Web Push), and text alerts.
- Inversion-strength calibration against measured drift; ML models trained on station history.
- Monitoring during and after spraying for volatile products.

---

*Advisory only. The pesticide label is the law.*
