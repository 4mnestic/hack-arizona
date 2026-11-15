# Decision logic

Every rule the tool uses to turn weather and spray choices into GO, CAUTION or STOP. Plain words first, exact numbers in the tables. For the file layout see FLOW.md; for setup and usage see DEVELOPMENT.md.

Advisory only. The pesticide label is the law.

## The big idea

1. Take the latest weather reading (two or more heights) and the spray setup (pesticide, plus nozzle if one is chosen).
2. Run five separate checks. Each check looks at one thing and may raise a warning. A warning is either CAUTION or STOP and has a plain-language reason.
3. Combine the warnings: any STOP means STOP, otherwise any CAUTION means CAUTION, otherwise GO.
4. Every reason is kept and shown, worst first, not just the worst one.
5. Write the reading, the warnings and the answer to the log.

## Combining warnings (`spraywait/decision.py`)

| Warnings raised | Answer |
|---|---|
| At least one STOP | STOP |
| No STOP, at least one CAUTION | CAUTION |
| None | GO ("air is mixing, wind is within label limits at every height, and no shear detected") |

One STOP outweighs any number of other results. The score below only says how bad it is; it never changes the status.

## Risk score (0 to 100)

Every decision also gets a score. Higher means more drift risk. Each status has its own band, so the score can never disagree with the status:

| Status | Score |
|---|---|
| GO | 0 |
| CAUTION | 20 to 69 |
| STOP | 70 to 100 |

How it is worked out:

1. Each warning gets its own score inside its band. By default CAUTION is 40 and STOP is 80, but most checks grade it by how bad the condition is.
2. The decision's score is the worst warning's score, plus 3 points for each additional warning. It is then kept inside the status band (CAUTION stops at 69, STOP stops at 100).
3. GO is always 0.

| Warning | Score |
|---|---|
| Inversion STOP | weak 75, moderate 85, strong 95 |
| Inversion CAUTION | nearly equal temperatures 45, may be forming 35 |
| Wind too calm or too strong (STOP) | 70 plus 5 for every mph past the label limit |
| Wind shear speed | CAUTION 30 to 60 as the difference grows from 5 to 8 mph; STOP 70 plus 5 for every mph past 8 |
| Wind shear direction | CAUTION 30 to 60 as the difference grows from 45 to 90 degrees; STOP 70 plus 1 for every 2 degrees past 90 |
| Over the label maximum temperature | 70 plus 2 for every degree past the limit |
| Highly volatile product in heat, fine droplets, wind near the limits, stale or single-height data | the defaults (CAUTION 40, STOP 80) |
| No weather data | 100 |

**This is a ranking, not a probability.** The points are chosen so worse conditions score higher and status stays consistent. They are not calibrated against measured drift. The extra 3 points per warning can double count related warnings (for example an inversion and wind shear often appear together).

The score appears in the decision output (`decision.score`), on each warning (`flags[].score`), in the log (a `score` column), and for the ground-station comparison (`ground_only.score`). The forecast hours from `windows.py` do not carry a score yet.

## Inputs the checks use

- **Weather reading:** a timestamp plus a list of heights. Each height has temperature (F), wind speed (mph) and wind direction (degrees, may be missing). The checks always compare the lowest height with the highest. Extra heights in between are not used.
- **Pesticide:** label wind limits (default 3 to 10 mph), an optional label maximum temperature, volatility (low, moderate or high) and droplet size.
- **Nozzle:** if one is chosen, its droplet size replaces the pesticide's. If none is chosen, droplets are assumed to be fine, the worst case for drift, and the pesticide's own droplet size is ignored.

## 1. Data quality (`checks/data_quality.py`)

Fail safe: missing or old data can never give GO.

| Situation | Result |
|---|---|
| No levels at all | STOP |
| Only one measurement height (cannot check inversion or shear) | CAUTION |
| Reading is more than 15 minutes old | CAUTION |

## 2. Inversion (`checks/inversion.py`)

An inversion means the air is warmer higher up than at the ground. It traps spray close to the ground, where it can travel sideways a long way. The difference used is the top temperature minus the bottom temperature.

| Situation | Result |
|---|---|
| Top is warmer than bottom | **STOP**, named weak (under 1F), moderate (1F to under 3F) or strong (3F or more) |
| Top is not warmer, but is less than 0.5F cooler (nearly equal), **and ground wind is under 7 mph** | CAUTION: an inversion may be forming |
| Same nearly-equal temperatures, **but ground wind is 7 mph or more** | No warning (moving air keeps the layer mixed) |
| Top is cooler by 0.5F to 1F, **and** it is 2 pm to 9 am, **and** ground wind is under 7 mph | CAUTION: the temperature drop is weaker than normal, so conditions favor an inversion forming |
| Anything else (normal cooling with height) | No warning |

The reason text adds context when it is true: it is late afternoon through early morning, or the ground wind is light (so the layer is unlikely to mix out).

Time of day can only add caution. It is never used to remove or soften a warning, because the server's clock may not match the farm's clock.

**What is sourced and what is not** (sources: UC ANR, "Surface Inversions Cause Spray Drift", and NDSU Extension AE1876, see Sources below):

| Rule | Status |
|---|---|
| Any inversion means STOP | Supported. The page says "If you suspect there's an inversion, then don't spray." |
| Measure at the ground and several meters above | Supported. 5 ft and 30 ft (1.5 m and 9 m) fits. The page also says field temperatures often differ a lot from regional forecasts, which is why one ground or forecast reading is not enough. |
| Light wind means an inversion can persist: 7 mph | Supported. The page says inversions are expected daily unless wind stays above 7 mph for the whole night between sunset and sunrise ("although even this isn't always true"). The page writes "7 m/h", read here as mph. A single reading cannot show a whole night, so this is a snapshot approximation. |
| Window of 2 pm to 9 am | Supported in shape, approximated in numbers. The page says inversions begin 3 to 4 hours before sunset, peak just before sunrise, and fade within about an hour after sunrise. We have no sunrise or sunset times yet, so we use a fixed window wide enough to cover that rule all year. It only adds caution. |
| Strong inversion: 3F or more | Supported. NDSU says a bigger temperature difference means a more intense inversion and calls inversions of 3F or more the strongest. Its data was 3 m over 1 m, not our heights. |
| Compare air near the ground with air about 10 ft up | Supported. NDSU's summary says measure at 1 ft above the soil or crop canopy and at 10 ft; any case where the ground is coolest is an inversion. |
| Light wind: inversions resist mixing below 5 mph | Supported by NDSU, and weaker winds weaken inversions. We keep UC ANR's 7 mph, which is the more cautious of the two. |
| Wind direction can flip up to 180 degrees inside an inversion | Supported by NDSU. Backs up the direction-shear check. |
| 0.5F and 1F cutoffs | Partly supported. They are the band edges in NDSU's Figure 2 (counts of inversions by strength), not official limits. |
| 1F weak/moderate split and the names weak/moderate/strong | **Assumption.** No source gives these labels. They only change the wording and score; every inversion is STOP either way. |

## 3. Wind speed (`checks/wind.py`)

Checked separately at every height. The limits come from the pesticide (default 3 to 10 mph).

| Situation | Result |
|---|---|
| Below the minimum | STOP: too calm, often means an inversion and droplets hang and drift unpredictably |
| Above the maximum | STOP: too strong, droplets carried off target |
| Within 1 mph above the minimum | CAUTION: near the calm limit |
| Within 1 mph below the maximum | CAUTION: near the upper limit |
| Otherwise | No warning |

## 4. Wind shear (`checks/wind.py`)

Shear means the wind changes with height, so the ground wind does not show where the spray will go once it rises. It compares the lowest and highest heights.

| Wind aloft minus wind at ground | Result |
|---|---|
| 8 mph or more | STOP |
| 5 to 8 mph | CAUTION |

| Difference in direction | Result |
|---|---|
| 90 degrees or more | STOP |
| 45 to 90 degrees | CAUTION |

Direction is only compared when both heights report a direction and both winds are at least 1 mph (direction is meaningless in near-still air). The difference wraps around, so 350 and 10 degrees differ by 20.

## 5. Volatility, label temperature and droplets (`checks/volatility.py`)

Uses the temperature at the lowest height.

| Situation | Result |
|---|---|
| Hotter than the pesticide's label maximum temperature | STOP |
| Highly volatile product at 85F or more | STOP: vapor keeps drifting for hours |
| Highly volatile product at 75F to 85F | CAUTION |
| Moderately volatile product at 85F or more | CAUTION |
| Fine droplets and wind of 7 mph or more at any height | CAUTION: fine droplets drift more easily (names the nozzle if one is set) |

Low volatility products are never flagged for heat alone, only for a label temperature limit.

## Spray windows from the forecast (`spraywait/windows.py`)

The same five checks are run on every hour of the forecast, using the chosen pesticide and nozzle. Each hour gets its own GO, CAUTION or STOP. Then two things are reported:

- **Next GO window:** the first stretch of back-to-back GO hours. It starts at the first GO hour and ends one hour after the last GO hour in that run. If there are no GO hours, there is no window.
- **Gets worse:** if the first forecast hour is GO or CAUTION, the first later hour with a worse status (GO to CAUTION or STOP, or CAUTION to STOP), with the names of the checks that caused it.

Forecast hours are never treated as stale, because they are future predictions.

The forecast comes from Open-Meteo (model data, not measurements): temperature at 2 m, wind at 10 m for the ground level, and temperature and wind at 80 m for the upper level.

**Limits of forecast windows**

- **Heights are far apart.** 2 m and 80 m are about 262 ft apart, not the 25 ft the cutoffs assume. The label wind limits (3 to 10 mph) are applied to the 80 m wind, which is usually stronger than the wind in the trees. Example: a normal afternoon with 6 mph at the ground and 11 mph at 80 m gives STOP ("wind too strong at 262 ft") and a shear CAUTION. Forecast windows will therefore be pessimistic and may show few or no GO hours. Fix options: apply the wind limits and shear cutoffs to the 10 m wind only, or use model values closer to canopy height.
- **Timestamps use the server's clock.** Forecast times arrive in UTC and are converted to the server's local time. On Render the server runs in UTC, so the hour-of-day rule in the inversion check (2 pm to 9 am) would use UTC hours, not the orchard's. Because time of day only adds caution, the effect is extra or missing early-warning CAUTIONs, never a missed inversion STOP. The fix is to convert to the orchard's own timezone.

## The "single station" comparison (`single_station_decision`)

For demos only. It shows what a basic ground-level station would say: it uses just the lowest height and runs only the wind speed and volatility checks. It has no inversion, shear or data-quality checks. The gap between this answer and the full answer is what the tool adds.

## Where to change a number

Every cutoff is a constant at the top of its check file. Change it there and the tests show what moves.

## Known limits

- Sourced so far: the inversion wind and time rules above, the 3F strong-inversion cutoff (NDSU), and the 3 to 10 mph window (common guidance named in the challenge brief). Still assumptions: the 1F moderate cutoff, all wind shear cutoffs (5 and 8 mph, 45 and 90 degrees), the volatility temperatures (75F, 85F), the 7 mph fine-droplet cutoff, the 1 mph edge margin and the 15-minute stale limit.
- The inversion window is fixed hours, not real sunrise and sunset. Once the orchard's location is an input, compute it (3 to 4 hours before sunset until about an hour after sunrise).
- Cloud and rain are not inputs. The source says inversions are expected every day unless there is continuous heavy overcast or continuous rain, and that clear skies (cloud cover 25% or less) favor them.
- Other signs the source lists are not used: evening and night wind much lighter than daytime wind, dew, frost, fog, sound carrying far, smoke hanging in the air.
- Terrain is not an input. The source says inversions flow like water, drain downhill and collect in low spots, and that shade from trees or hills can start one earlier and keep it later.
- The inversion temperature cutoffs assume sensors roughly 25 ft apart. Heights far apart, like the Open-Meteo source (about 7 ft and 262 ft), are not calibrated.
- Gusts, humidity, orchard details (canopy height, sensitive neighbors) and wind direction relative to neighbors are not checked yet.
- The pesticide values are illustrative, from memory and not looked up. The label governs. Of the 47 pesticides, 44 are rated low volatility, 2 moderate (Malathion, Pendimethalin) and 1 high (2,4-D esters), so the volatility check only fires for those three, plus the 6 products with a label maximum temperature. Volatility is set by hand per product. The vapor pressure column is not used by any check, and 13 products have it blank. Every product uses the default 3 to 10 mph wind limits, so wind limits never differ between products. The droplet size column is ignored when the app resolves a spray setup, because the nozzle (or the fine-droplet default) decides droplet size.
- The EPA drift page and the UC Extension weather-data PDF could not be used (one gave no usable numbers, one link is dead), so shear and volatility have no source yet.

## Sources

- UC ANR, "Surface Inversions Cause Spray Drift": https://ucanr.edu/blog/topics-subtropics/article/surface-inversions-cause-spray-drift
- NDSU Extension, J. Nowatzki, "Understanding Air Temperature Inversions Relating to Pesticide Drift", AE1876 (reviewed Aug 2022): https://www.ndsu.edu/agriculture/extension/publications/understanding-air-temperature-inversions-relating-pesticide-drift (droplets of 200 microns or less fall only a few inches per second, which supports the fine-droplet default)
- Challenge brief ("Spray or Wait?", Hack Arizona AgX): inversion defined as upper temperature higher than lower; 3 to 10 mph as common wind guidance; flag large wind differences between heights; actual limits depend on the pesticide label.
