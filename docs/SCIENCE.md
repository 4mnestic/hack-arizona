# SprayWait: the science

The research behind SprayWait's checks. Every threshold and its source is in [LOGIC.md](LOGIC.md).

## Temperature inversions (primary drift risk)

- Normally, air temperature decreases with altitude. An inversion occurs when warmer air sits above cooler surface air, suppressing vertical mixing.
- This traps fine pesticide droplets and vapor near the ground, allowing them to drift horizontally over long distances, potentially harming workers and communities.
- Inversions are difficult to detect from ground-level conditions alone (Nowatzki, n.d.).

## Other factors affecting spray drift

- **Wind speed:** very low wind speeds can allow droplets to remain suspended, while stronger winds can carry droplets beyond the target area.
- **Wind shear:** wind speed and direction can change with altitude. Winds above the orchard canopy may be stronger or travel in a different direction than winds near the ground.
- **Droplet size:** smaller droplets remain airborne longer and are more easily transported by wind. Nozzle type and spray pressure influence droplet size (Nuyttens et al., 2007).
- **Temperature and humidity:** high temperatures and low humidity accelerate droplet evaporation, causing droplets to shrink and become more susceptible to drift.
- **Pesticide volatility:** some pesticides can vaporize after application, creating additional drift risks even after spraying has stopped (Al Heidary et al., 2014).

## Forecasting the next spray window

- Inversions commonly develop around sunset, strengthen overnight, and break up after sunrise as the ground warms (UC ANR, n.d.).
- SprayWait uses Open-Meteo's hourly 24-hour forecast to compare temperatures and wind at multiple heights, and applies the same drift-risk checks as the live system to find:
  - **Next GO window:** consecutive hours without detected risk conditions.
  - **Early warning:** when conditions are expected to become CAUTION or STOP.

Forecasts provide planning guidance, not confirmation of orchard conditions. Weather models may underestimate nighttime inversions, so live decisions rely on the orchard's 5 ft and 30 ft sensors (Holtslag et al., 2013).

> **SprayWait is a decision-support tool and does not replace pesticide label requirements, regulations, or professional judgment.**

## References

Nowatzki, J. (n.d.). Understanding air temperature inversions relating to pesticide drift. North Dakota State University Extension. https://www.ndsu.edu/agriculture/extension/publications/understanding-air-temperature-inversions-relating-pesticide-drift

Nuyttens, D., Baetens, K., De Schampheleire, M., & Sonck, B. (2007). Effect of nozzle type, size and pressure on spray droplet characteristics. Biosystems Engineering, 97(3), 333–345. https://doi.org/10.1016/j.biosystemseng.2007.03.001

Al Heidary, M., Douzals, J. P., Sinfort, C., & Vallet, A. (2014). Influence of spray characteristics on potential spray drift of field crop sprayers: A literature review. Crop Protection, 63, 120–130. https://doi.org/10.1016/j.cropro.2014.05.006

Holtslag, A. A. M., Svensson, G., Baas, P., et al. (2013). Stable atmospheric boundary layers and diurnal cycles: Challenges for weather and climate models. Bulletin of the American Meteorological Society, 94(11), 1691–1706. https://doi.org/10.1175/BAMS-D-11-00187.1

Open-Meteo. (n.d.). Weather forecast API documentation. https://open-meteo.com/en/docs

UC ANR. (n.d.). Surface inversions cause spray drift. Topics in Subtropics, University of California Agriculture and Natural Resources. https://ucanr.edu/blog/topics-subtropics/article/surface-inversions-cause-spray-drift
