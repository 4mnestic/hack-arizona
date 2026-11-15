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

**Live** (`/`): the farm station replays a real day of Oklahoma Mesonet readings (temperature at 1.5 m and 9 m, wind at 2 m and 10 m) in real time. From about 4:15 to 7:30 pm Arizona time it is in a recorded evening inversion: the ground sensor alone says GO, SprayWait says STOP. The **Station** page (`/station`) charts both heights over the day; the **Log** (`/log`) shows each decision and what triggered it.

**Demo** (`/demo`): each scenario isolates one thing the tool checks. A dashed "Demo note" box says what it illustrates and the expected result; it is a presenter's aid, not part of the field app.

| Scenario | Illustrates | Ground station alone | SprayWait |
|---|---|---|---|
| Hidden inversion | Inversion a ground sensor can't see: 4°F warmer at 30 ft, wind fine | GO | **STOP** |
| Inversion forming | Early warning: same temperature at both heights, mixing has stopped | GO | **CAUTION** |
| Strong wind above the canopy | Wind speed changing with height: 4.5 mph below, 12 mph above | GO | **STOP** |
| Wind turning with height | Wind direction changing with height: 120° apart | GO | **STOP** |
| Good spraying conditions | Control case: no false alarms | GO | **GO** |
| Hot afternoon | Pesticide limits: GO for the generic label, STOP for Malathion (90°F) | GO | **GO / STOP** |
| Too windy | Over 10 mph: a single station catches this too | STOP | **STOP** |
| Dead calm | Under 3 mph: a single station catches this too | STOP | **STOP** |

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

## Decision rules

Five checks run on every reading. The worst warning wins: any STOP means **STOP**, any CAUTION means **CAUTION**, otherwise **GO**. Every reason is shown. A risk score (0 = GO, 20–69 = CAUTION, 70–100 = STOP) ranks how bad it is without changing the status.

| Check | STOP | CAUTION | Basis |
|---|---|---|---|
| **Data quality** | No data | Reading over 15 min old, or only one height | Fail safe: missing data is never GO |
| **Inversion** (30 ft minus 5 ft) | Warmer aloft. Named weak (<1°F), moderate, strong (≥3°F) | Nearly equal (within 0.5°F) with ground wind under 7 mph: mixing has stopped. Also, 2 pm–9 am with light wind, air aloft only 0.5–1°F cooler | "If you suspect an inversion, don't spray" (UC ANR). ≥3°F = strongest class (NDSU). 7 mph light-wind rule (UC ANR) |
| **Wind speed** (every height) | Below 3 or above 10 mph | Within 1 mph of either limit | Common guidance; the label's limits come first |
| **Wind shear** (speed) | Aloft ≥8 mph stronger than ground | 5–8 mph stronger | Ground wind doesn't show the air the spray rises into |
| **Wind shear** (direction) | ≥90° apart | 45–90° apart | Direction can flip up to 180° inside an inversion (NDSU) |
| **Pesticide** | Above the label's max temperature. Highly volatile at ≥85°F | Highly volatile at 75–85°F. Moderately volatile at ≥85°F. Fine droplets with wind ≥7 mph | Vapor drift rises with heat; droplets ≤200 µm fall only inches per second (NDSU) |

- If no nozzle is chosen, droplets are assumed fine, the worst case for drift.
- Time of day can only add caution, never remove it.
- Cutoffs without a published number are stated design choices that lean toward caution; none can turn a STOP into a GO. Every rule and its source is in [docs/LOGIC.md](docs/LOGIC.md).

## Science

### **Temperature Inversions (Primary Drift Risk)**
- Normally, air temperature decreases with altitude. An inversion occurs when warmer air sits above cooler surface air, suppressing vertical mixing.
- This traps fine pesticide droplets and vapor near the ground, allowing them to drift horizontally over long distances, potentially harming workers and communities.
- Inversions are difficult to detect from ground-level conditions alone (Nowatzki, n.d.).
### **Other Factors Affecting Spray Drift**
- Wind Speed: Very low wind speeds can allow droplets to remain suspended, while stronger winds can carry droplets beyond the target area.
- Wind Shear: Wind speed and direction can change with altitude. Winds above the orchard canopy may be stronger or travel in a different direction than winds near the ground.
- Droplet Size: Smaller droplets remain airborne longer and are more easily transported by wind. Nozzle type and spray pressure influence droplet size (Nuyttens et al., 2007).
- Temperature and Humidity: High temperatures and low humidity accelerate droplet evaporation, causing droplets to shrink and become more susceptible to drift.
- Pesticide Volatility: Some pesticides can vaporize after application, creating additional drift risks even after spraying has stopped (Al Heidary et al., 2014).

### **Forecasting the Next Spray Window**

- Inversions commonly develop around sunset, strengthen overnight, and break up after sunrise as the ground warms (UC ANR, n.d.).
- SprayWait uses Open-Meteo's hourly 24-hour forecast to compare temperatures and wind at multiple heights.
- The forecast applies the same drift-risk checks as the live system to identify:
    - Next GO window: Consecutive hours without detected risk conditions.
    - Early warning: When conditions are expected to become CAUTION or STOP.

Forecasts provide planning guidance, not confirmation of orchard conditions. Weather models may underestimate nighttime inversions, so live decisions rely on the orchard's 5 ft and 30 ft sensors (Holtslag et al., 2013).


**SprayWait is a decision-support tool and does not replace pesticide label requirements, regulations, or professional judgment.**

### **References**
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
- Farm station from real data: start the server with `FARM_WEATHER=mesonet` (the deployed default) to replay one day of Oklahoma Mesonet readings (`data/mesonet_data_files.csv`) in real time, one reading every 5 minutes, starting with the last 6 hours (`MESONET_BACKFILL_HOURS`). The deployed app sets `MESONET_SHIFT_HOURS=0.75`, so it replays the recorded day 45 minutes ahead of the clock. This is demo data: from about 4:15 to 7:30 pm Arizona time it replays the recorded evening inversion, when a ground station alone says GO and the 30 ft sensor makes it STOP. The file has no readings for the 2 hours before that (about 2:05 to 4:10 pm with the shift).
- Or run that replay as a separate station posting over the network (server with `FARM_WEATHER=push`): `FARM_API_KEY=devkey .venv/bin/python -m tools.mesonet_station http://localhost:8000 --backfill-hours 6`
- Push one simulated reading instead: `FARM_API_KEY=devkey .venv/bin/python -m tools.push_reading http://localhost:8000`
- Tests: `.venv/bin/pytest --cov=spraywait --cov=api --cov=tools`

## Tech stack

Python (FastAPI) rule engine and API, a plain HTML/JS installable web app (PWA), Open-Meteo forecasts, hosted on Render. Tested with pytest (183 tests).

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
