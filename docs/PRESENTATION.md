# SprayWait: presentation brief

Everything the team needs to present to the judges. Demo is 3 minutes. Keep to time: presentation is 5 of 20 points.

Live app: https://spraywait.onrender.com
Demo scenarios: https://spraywait.onrender.com/demo
Station chart: https://spraywait.onrender.com/station
Log: https://spraywait.onrender.com/log

## Before you start (5 minutes before)

- Open the live app and all three pages on the presenting device. Render's free plan sleeps; the first load can take up to a minute.
- Check the clock. The live app replays a real recorded evening inversion from about 4:15 to 7:30 pm Arizona time. Inside that window, use the live page. Outside it, use /demo "Hidden inversion" (it always works).
- Have the log open in a tab with a few entries already in it.

## One-line pitch

A single ground weather station says "looks fine". SprayWait reads the air at two heights, catches the invisible temperature inversion, and tells the applicator Go, Caution or Stop, and why.

## The problem (20 seconds)

- Pesticide spray drifts onto neighboring crops, workers, homes and water.
- The worst condition is a temperature inversion: cool air near the ground under warmer air. The air stops mixing upward, so fine droplets and vapor stay in a shallow layer and travel sideways for long distances. NDSU Extension says small droplets can move thousands of feet, and vapor can move miles.
- It is invisible at ground level. Calm air feels safe. A ground station and a regional forecast both miss it.

## 3-minute demo script

0:00 to 0:20. The problem (above). "Applicators judge by what they see and feel. An inversion feels like a perfect calm evening."

0:20 to 1:20. The catch.
- Show the hidden inversion (live page if inside the 4:15 to 7:30 pm window, otherwise /demo "Hidden inversion").
- Point at "Ground station alone: GO". Then point at SprayWait: STOP.
- Read the reason out loud: the air at 30 ft is warmer than at 5 ft, so spray will be trapped near the ground and can drift.
- Say: "Same moment, same orchard. One sensor says go. Two heights say stop."

1:20 to 2:00. More than inversions.
- Quickly show one or two other /demo scenarios:
  - "Strong wind above the canopy": 4.5 mph below, 12 mph above. Ground says GO, SprayWait says STOP.
  - "Inversion forming": same temperature at both heights. CAUTION, an early warning before it turns into STOP.
- Show the pesticide picker: the same weather can be GO for one product and STOP for a heat-limited one (Hot afternoon: STOP for Malathion at 90F).

2:00 to 2:30. Planning ahead.
- Show the 24-hour forecast strip: the next safe spray window, or a warning that conditions will turn bad.

2:30 to 2:50. The record.
- Open /log. Every reading, the decision, the risk score and what triggered it, with a timestamp. Exportable as CSV for records.

2:50 to 3:00. Close. "SprayWait supports the applicator's decision. It doesn't replace the label, on-site checks or regulations. The label is the law."

## What it checks (plain words)

1. Data quality. No data means STOP. Old data (over 15 minutes) or only one height means CAUTION. Missing data can never give GO.
2. Inversion. Warmer at 30 ft than at 5 ft means STOP, named weak (under 1F), moderate, or strong (3F or more). Nearly equal temperatures with light wind means CAUTION: mixing has stopped and an inversion may be forming.
3. Wind speed. Below 3 mph or above 10 mph at any height means STOP (common guidance; the label's own limits come first). Within 1 mph of a limit means CAUTION.
4. Wind shear. Wind much stronger aloft (5 mph difference CAUTION, 8 mph STOP) or turning with height (45 degrees CAUTION, 90 degrees STOP) is flagged. The ground wind does not show where the spray will go once it rises.
5. Pesticide and nozzle. Over the label's temperature limit means STOP. Highly volatile products get CAUTION from 75F and STOP from 85F. Fine droplets plus wind of 7 mph or more get CAUTION. If no nozzle is picked, we assume the finest droplets, the worst case.

Decision: the worst warning wins. Any STOP means STOP, any CAUTION means CAUTION, otherwise GO. Every reason is shown. There is also a risk score from 0 to 100 (GO 0, CAUTION 20 to 69, STOP 70 to 100) that shows how bad it is without changing the status.

Alerts: on screen and as a phone notification when conditions get worse (GO to CAUTION or STOP, CAUTION to STOP).

## How it maps to the judging

- Drift-risk detection (5 points): inversion from two heights, wind too low or high, speed and direction shear, pesticide heat and volatility, plain-language reasons.
- Actionable alerts and records (3 points): Go/Caution/Stop with reasons, phone notification on worsening conditions, time-stamped log with CSV export.
- Real-world usefulness (3 points): works on any phone and installs like an app (Add to Home Screen). Pick your pesticide and nozzle. The station data format matches real vendor stations, so a real mast only swaps the data source.
- Execution (4 points): live and deployed, 183 automated tests, real recorded weather data (Oklahoma Mesonet) replayed in real time.
- Tiebreaker ("how much better than a single station?"): every demo scenario shows the ground-station answer next to ours. Multi-height data, a 24-hour forecast for the next safe window, and early warnings.

All must-haves are covered: two heights, inversion detection, wind below 3 or above 10 mph, shear, Go/Caution/Stop with reasons, time-stamped log.
Stretch goals covered: pesticide properties (volatility, label temperature, nozzle droplet size), forecast of the next spray window and warnings before conditions turn bad, push notifications.

## The science (if asked)

- Inversion: normally air cools with height. In an inversion the ground cools first in the evening, so air near the ground is colder and denser than air above. Air can only move sideways. Strongest in the evening to around midnight; they form 3 to 4 hours before sunset and fade about an hour after sunrise (UC ANR).
- Measuring it: NDSU Extension recommends measuring near the ground and about 10 ft up; if it is coolest at the surface, there is an inversion. The bigger the difference, the stronger it is. NDSU calls 3F or more the strongest, which is our "strong" cutoff.
- Wind and inversions: inversions resist mixing below 5 mph (NDSU) and are expected nightly unless wind stays above 7 mph all night (UC ANR). We use 7 mph, the more cautious one.
- Direction can flip up to 180 degrees inside an inversion (NDSU), which is why we check direction at both heights.
- Droplets: droplets of 200 microns or less fall only a few inches per second (NDSU). At 7 mph, a droplet released at 10 ft can travel roughly 400 ft before landing. That is why fine droplets are the default worst case.
- Forecast caveat: weather models tend to underestimate night-time inversions, so the forecast is for planning and the live decision always comes from the orchard's own sensors.

## Honest limits (good answers if asked)

- Every cutoff is documented in docs/LOGIC.md as either sourced (UC ANR, NDSU, the challenge brief) or a stated design choice. Design choices only ever add caution; none can turn a STOP into a GO.
- The score is a ranking, not a probability. It is not calibrated against measured drift.
- The inversion time window uses fixed hours, not real sunrise and sunset yet.
- Cloud cover, humidity, gusts and terrain (low spots collect cold air) are not inputs yet.
- Pesticide values are illustrative. The label governs.
- Live data is a replay of real Mesonet data, not a live mast in an orchard. The data format is ready for real hardware.

## Likely judge questions

Q: Why two heights and not one?
A: An inversion is defined by temperature changing with height. One sensor cannot see it. Same for wind shear: calm at the ground can mean strong wind above the trees.

Q: Why 5 ft and 30 ft?
A: Below and above a typical orchard canopy, which is the challenge's suggestion. NDSU recommends near-ground and about 10 ft. Any two heights work.

Q: What if the data is missing or old?
A: Fail safe. No data is STOP; stale or single-height data is CAUTION. It can never say GO without good data.

Q: Isn't any inversion too strict as STOP?
A: UC ANR says "If you suspect there's an inversion, then don't spray." We follow that. The strength label (weak, moderate, strong) tells you how bad it is.

Q: How is this better than a regional forecast?
A: Forecasts are regional and models underestimate night inversions. We read the air inside the orchard, and use the forecast only for planning the next window.

Q: Can it run on real hardware?
A: Yes. The station input uses a vendor-style format (one record per sensor with its height). A real mast replaces the replayed data without changing the checks.

Q: What's next?
A: Real station hardware, push notifications to a closed app and text alerts, sunrise and sunset from the orchard's location, monitoring during and after spraying for volatile products, and calibration against measured drift.

## Team

- Joy: pesticide data and science research, app UI design.
- Leo: inversion and wind-shear models, the core decision engine.
- Zach: app, station and forecast integration, deployment, docs.

## Tech

Python (FastAPI) rule engine and API, plain HTML/JS installable web app, Open-Meteo forecasts, hosted on Render, 183 pytest tests.

## Sources

- NDSU Extension, J. Nowatzki, "Understanding Air Temperature Inversions Relating to Pesticide Drift", AE1876 (reviewed 2022).
- UC ANR, "Surface Inversions Cause Spray Drift", Topics in Subtropics.
- Challenge brief, "Spray or Wait?" (3 to 10 mph common wind guidance; inversion = upper temperature higher than lower).
- Holtslag et al. (2013), Bulletin of the American Meteorological Society: models struggle with stable night-time layers.
- Nuyttens et al. (2007): nozzle type and pressure control droplet size.
