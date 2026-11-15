# Spray or Wait

Go, Caution, or Stop for orchard pesticide spraying, with the reasons why.

**Live app:** https://spraywait.onrender.com · works on any phone; install it from the browser menu ("Add to Home Screen").

## The problem

Pesticide spray can drift beyond the orchard onto neighboring crops, workers, homes, and water. The riskiest condition, a temperature inversion, is invisible from the ground: the air feels calm and a single ground-level weather station says conditions are fine, while cooler air trapped under warmer air keeps fine droplets in a shallow layer that carries them sideways. Applicators decide by what they see and feel, plus regional forecasts that don't match the air inside the orchard.

## What it does

- **Reads weather at two heights** (about 5 ft and 30 ft) from the orchard's station, plus the pesticide and nozzle being used.
- **Says GO, CAUTION, or STOP right now**, with the reasons in plain language (inversion, wind too low or too high, wind changing with height, heat and volatility limits).
- **Alerts** when conditions get worse (GO → CAUTION/STOP, CAUTION → STOP), on screen and as a phone notification.
- **Plans ahead:** a 24-hour forecast strip shows the next safe spray window, or warns when conditions are expected to turn bad.
- **Keeps a record:** a time-stamped log of every reading, decision, and what triggered it, exportable as CSV.

## Challenge goals

**Must-haves:** all met.

| Goal | How SprayWait meets it |
|---|---|
| Read temperature and wind at two or more heights | 5 ft and 30 ft from the orchard station: a real recorded Mesonet day on Live, simulated scenarios on Demo. |
| Detect an inversion (upper warmer than lower) | STOP whenever 30 ft is warmer than 5 ft, graded weak, moderate, or strong; CAUTION when one may be forming. |
| Flag wind below 3 mph or above 10 mph | STOP outside the pesticide's label limits (3–10 mph by default), CAUTION within 1 mph of either limit. |
| Flag large wind speed or direction differences between heights | CAUTION at 5 mph or 45°, STOP at 8 mph or 90°. |
| Clear status with plain-language reasons | GO, CAUTION, or STOP with every reason listed, using the measured numbers. |
| Time-stamped log of readings and what triggered each alert | Log page lists every reading, status, and trigger; downloadable as CSV. |

**Stretch goals**

| Goal | Status |
|---|---|
| Factor in pesticide properties and application details | Done. 47 pesticides with label temperature limits and volatility; the nozzle sets droplet size. |
| Use forecasts to predict the next safe window or warn before conditions turn bad | Done. The same checks run on each hour of a 24-hour Open-Meteo forecast, giving the next GO window and an early warning. Open-Meteo, not the National Weather Service, because the NWS hourly forecast has no temperature aloft and so cannot show an inversion. |
| Monitor during and after spraying | Partly. The app rechecks every minute against readings that arrive every 5 minutes, and alerts as soon as conditions get worse, so it works while spraying. Watching volatile products after spraying is not built yet. |
| Alerts by text or push notification | Partly. Phone notification and in-app banner while the app is open. Notifications to a closed app, and text alerts, are not built yet. |
| Physical sensor prototype | Not built. Stations post readings to an authenticated API; the Mesonet replay tool already does this over the network, so a real mast would only replace the data source. |

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

- **Inversion:** temperature at 30 ft minus 5 ft. Any warming aloft is STOP, graded weak (under 1°F), moderate, or strong (3°F or more, per NDSU Extension). Nearly equal temperatures with light ground wind (under 7 mph, per UC ANR) are CAUTION: an inversion may be forming. From 2 pm to 9 am, a weaker-than-normal drop also gives an early CAUTION. Time of day only ever adds caution.
- **Wind speed:** below 3 mph or above 10 mph is STOP (common guidance; the label's limits come first), and within 1 mph of a limit is CAUTION.
- **Wind shear:** speed differences of 5 mph or more between heights, or direction differences of 45° or more, are CAUTION; 8 mph or 90° is STOP.
- **Pesticide:** label temperature limits and volatility tighten the risk. The nozzle sets droplet size; with no nozzle chosen, droplets are assumed fine, the worst case for drift.
- **Status:** the most severe flag wins and every reason is shown. Missing or stale data is never GO.
- **Risk score (0–100):** ranks how bad it is within each status (GO 0, CAUTION 20–69, STOP 70–100), so the score never contradicts the status. It ranks risk; it is not a drift probability. It is in the API response and the log CSV, not yet on screen.

Every threshold, its source, and the reasoning behind the ones no source gives a number for are in [docs/LOGIC.md](docs/LOGIC.md).

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
