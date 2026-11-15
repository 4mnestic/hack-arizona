# CLAUDE.md

Hackathon project (hack-arizona). Python.

## Conventions

- Tests: pytest, with coverage via `pytest --cov`.
- Keep `README.md` current with setup and run instructions.
- `README.md` is presentation-facing (for judges); development docs live in `docs/DEVELOPMENT.md` (setup, flow, layout) and `docs/LOGIC.md` (every rule and its source).

## Challenge prompt

### Spray or Wait? Using weather intelligence to prevent pesticide drift in orchards

**The problem.** When pesticides are sprayed in an orchard, some can drift beyond the target area. It can reach neighboring crops, workers, communities and the environment. Weather is one of the biggest factors, but applicators usually judge conditions by what they see and feel at ground level. They also use regional forecasts, which may not match what's happening inside the orchard.

One of the riskiest conditions is hard to spot: a temperature inversion. Normally, air gets cooler as you go up. In an inversion, cool air sits near the ground under warmer air. This stops the air from mixing upward, so fine spray droplets and vapor stay in a shallow layer and can travel sideways for long distances. Calm air at ground level doesn't mean it's safe either. Winds above the trees can be stronger or blowing a different way.

**Your task.** Build a decision-support tool that uses weather readings from more than one height to tell a pesticide applicator whether it's safe to spray right now, and why.

**Who it's for.** Pesticide applicators and Pest Control Advisers (PCAs) working in commercial tree orchards, such as those in California's Central Valley.

**Must-haves (minimum to submit)**

- Read multi-height weather data: temperature and wind from at least two heights, for example about 5 ft and 30 ft above the ground. Simulated data is fine.
- Detect an inversion: flag when the upper temperature is higher than the lower one.
- Check the wind:
  - Flag wind below 3 mph or above 10 mph. This is common guidance; actual limits depend on the pesticide label.
  - Flag large differences in wind speed or direction between heights.
- Give a clear status: for example Go, Caution or Stop, with the reason in plain language.
- Keep a record: a time-stamped log of the readings and what triggered each alert.

**Stretch goals**

- Factor in pesticide properties, such as volatility, or application details to adjust the risk.
- Use National Weather Service forecasts or historical data to predict the next safe spray window, or warn before conditions turn bad.
- Monitor conditions during and after spraying, not just before.
- Send alerts by text or push notification.
- Build a simple physical sensor prototype.

**Data you can use**

- Simulated data you generate (expected and completely fine)
- Public weather data, such as National Weather Service forecasts
- Starter dataset from the HUB, if provided

**Your demo (3 minutes).** Show us a scenario where a single ground-level weather station says conditions look fine, but your tool catches the risk. Show the alert, explain what triggered it, and show the log.

**Keep in mind.** Your tool supports the applicator's decision. It doesn't replace pesticide labels, on-site checks or regulations, and no system can guarantee zero drift. Judges care more about sound science and a clear, usable tool than a finished commercial product.

**Key terms**

- Pesticide drift: pesticide droplets or vapor moving outside the area being treated
- Temperature inversion: cooler air near the ground under warmer air above, which traps spray close to the ground
- Wind shear: wind speed or direction changing with height
- Volatility: how easily a pesticide turns into vapor; more volatile products can drift even after spraying
- PCA (Pest Control Adviser): a licensed professional who recommends pesticide use

**Learn more**

- [Surface Inversions Cause Spray Drift (UC ANR)](https://ucanr.edu/blog/topics-subtropics/article/surface-inversions-cause-spray-drift)
- [Using Weather Data to Demonstrate Spray Drift Risk Conditions (UC Cooperative Extension)](https://ucanr.edu/sites/default/files/2024-04/396035.pdf)
- [Portable Towers Provide Insight on Frost Characteristics](https://ives-openscience.eu/62153/)
- [Reducing Pesticide Drift (U.S. EPA)](https://www.epa.gov/reducing-pesticide-drift)
- [Airblast Spray Advisor (UC ANR)](https://ucanr.edu/site/airblast-spray-advisor)

### Judging (20 points)

| Criterion | Points | Outstanding |
|---|---|---|
| Drift-Risk Detection | 5 | Go/caution/stop, reasons, time-stamped log |
| Actionable Alerts & Records | 3 | Go/caution/stop, reasons, time-stamped log |
| Real-World Usefulness | 3 | Field-ready for applicators/PCAs |
| Execution & Functionality | 4 | Working and polished |
| Presentation Quality | 5 | Clear demo, on time |

Each judge scores every row from 1 to 5; a team's result is the plain average of its judges' totals. The organizers make the final decision.

**Tiebreaker (1–5, never added to the total):** "How much better than a single weather station?" Consider use of multi-height data, predicting good spray windows, creativity.
