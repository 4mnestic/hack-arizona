# Development Plan

Spray-decision assistant for orchard pesticide application. Given weather, pesticide, and orchard data, it returns **GO**, **CAUTION**, or **STOP**, with plain-language reasons.

Advisory only. The pesticide label is the law.

## Architecture

```
Inputs (weather, pesticide, orchard)
        │  standardized SprayContext
   ┌────┼──────────────┬──────────────┐
Inversion   Wind/drift    Other checks
   └────┼──────────────┴──────────────┘
        ▼
Status model → GO / CAUTION / STOP + reasons
```

- **Standardized input:** one `SprayContext` combining weather, pesticide, and orchard data, with consistent units and timestamps.
- **Model output:** every model returns a status, a score, and its reasons.
- **Status model:** the most severe status wins, and all reasons are reported.
- **Rule-based:** models use physics and label rules, so every decision can be explained.
- **Fail safe:** missing or stale data gives CAUTION, never GO.

## Components

1. **Weather inputs:** current conditions and an hourly forecast from public sources.
2. **Inversion model:** whether an inversion is likely and at what height, compared with canopy height. Thresholds depend on the pesticide.
3. **Wind model:** speed, gusts, and how dangerous the wind is, including its direction relative to sensitive areas.
4. **Other checks:** rain forecast, temperature, humidity, volatility, and label limits.
5. **Status model:** combines all model results into one decision with reasons.

## App

- **Live** (`/`): the farmer chooses only the pesticide and nozzle. Weather comes automatically from the farm's own station, pushed to the API.
- **Demo** (`/demo`): adds simulated scenarios and public forecast data, for presentations.
- **Nozzle module:** converts nozzle to droplet size and pressure, merged with the pesticide's label values.
- FastAPI backend plus an installable PWA, deployed on Render.

## Inputs

- **Weather:** temperature and wind at multiple heights (plan for 5ft and 30ft, as specified in the challenge prompt, liable to change).
- **Pesticide:** vapor pressure, volatility, and label limits.
- **Nozzle:** droplet size class, VMD, and pressure.
- **Orchard:** location, canopy height, and nearby sensitive areas.

## Goals

**Core:** inputs, inversion, wind, and status models, with unit tests. Plan for how to implement a mobile interface all the while. When the models are MVP-ready, we'll build the mobile app (android and iOS compatible).

**Next (must-have, judged):** time-stamped log in the app. Record every decision (readings, status, what triggered each alert) with `spraywait/log.py`, and show it in a log view. The demo must show the log.

**Then (helps the tiebreaker):** next safe spray window timeline. Run the checks hour by hour over the coming day and show a GO/CAUTION/STOP strip with "next GO window: 9am–1pm". Use the dummy station's day cycle first, then NWS hourly forecasts.

**Stretch:**
- ML-based models

## Testing

TBD, testing is important.

## Presentation

- Storytelling: a orchard farmer starts his day and uses the app to help inform his decisions
- A live demo and a fake demo for multiple example scenarios

## Team breakdown

### Joy
* Understand pesticide data and help Leo integrate the pesticide data into the inversion and shear models. Involved a CSV that maps names to spray metrics, and the spray metrics are passed to the models.
* Design app UI. Don't start actually building until model MVP is ready

### Leo
* Research inversion and shear models, so that they are science-backed.
* Implement different variations of the models
* Implement MVP 

### Zach
* Maintain README