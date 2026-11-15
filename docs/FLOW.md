# Logical flow

How a reading becomes a GO / CAUTION / STOP decision, by file.

```
INPUTS
======

  spraywait/weather/source.py            spraywait/pesticides/db.py
  ┌──────────────────────────┐           ┌──────────────────────────────┐
  │ WeatherSource (interface)│           │ PesticideDB (interface)      │
  │   .get_reading()         │           │   .get(name)  .list()        │
  └──────────┬───────────────┘           └──────────────┬───────────────┘
             │ implemented by                           │ implemented by
  spraywait/weather/simulated.py         spraywait/pesticides/db.py
  ┌──────────────────────────┐           ┌──────────────────────────────┐
  │ SimulatedSource          │           │ LocalPesticideDB             │
  │   SCENARIOS (6 scripts)  │           │   reads pesticides.json      │
  └──────────┬───────────────┘           └──────────────┬───────────────┘
             │ produces                                 │ produces
  spraywait/weather/types.py             spraywait/pesticides/db.py
  ┌──────────────────────────┐           ┌──────────────────────────────┐
  │ Reading                  │           │ Pesticide                    │
  │   timestamp              │           │   volatility, droplet_size   │
  │   levels: [Level, ...]   │           │   min/max_wind_mph           │
  │     height_ft, temp_f,   │           │   max_temp_f                 │
  │     wind_mph, wind_dir   │           │                              │
  └──────────┬───────────────┘           └──────────────┬───────────────┘
             │                                          │
             └────────────────┬─────────────────────────┘
                              ▼
CHECKS
======
  spraywait/checks/__init__.py  ->  run_all_checks(reading, pesticide)
             │
             ├─ checks/data_quality.py   no data -> STOP; one height or stale -> CAUTION
             ├─ checks/inversion.py      upper temp > lower temp -> STOP; near-equal -> CAUTION
             ├─ checks/wind.py           check_wind_speed: < min or > max -> STOP; near edge -> CAUTION
             │                           check_wind_shear: speed/direction differs by height -> CAUTION/STOP
             └─ checks/volatility.py     label max temp -> STOP; volatile + hot -> CAUTION/STOP;
                                         fine droplets + breeze -> CAUTION
             │
             ▼
  spraywait/checks/flag.py
  ┌──────────────────────────────────────────┐
  │ list[Flag]                               │
  │   severity: CAUTION | STOP               │
  │   check:    which file raised it         │
  │   reason:   plain-language sentence      │
  └──────────────────┬───────────────────────┘
                     ▼
DECISION
========
  spraywait/decision.py
  ┌──────────────────────────────────────────┐
  │ decide(reading, pesticide)               │
  │   any STOP flag    -> Status.STOP        │
  │   any CAUTION flag -> Status.CAUTION     │
  │   no flags         -> Status.GO          │
  │   reasons = every flag, worst first      │
  │                                          │
  │ single_station_decision(reading)         │
  │   lowest level only, wind + volatility   │
  │   (what a ground station would say)      │
  └──────────────────┬───────────────────────┘
                     ▼
RECORD
======
  spraywait/log.py
  ┌──────────────────────────────────────────┐
  │ DecisionLog.append(reading, pesticide,   │
  │                    decision)             │
  │   -> spray_log.jsonl (time-stamped)      │
  │ DecisionLog.rows() -> flat table rows    │
  └──────────────────────────────────────────┘

ENTRY POINTS
============
  demo.py        runs the evening_inversion scenario, prints ground-only vs full decision
  tests/         pytest; one test file per layer (inversion, wind, volatility+quality,
                 decision, inputs+log)
```

## Extending

- New weather source (NWS, sensor tower): subclass `WeatherSource` in `spraywait/weather/`, return a `Reading`.
- New pesticide source (CSV, online): subclass `PesticideDB` in `spraywait/pesticides/`, return `Pesticide` objects.
- New check: add a file in `spraywait/checks/` with `check_x(reading, pesticide, now) -> list[Flag]`, then append it to `ALL_CHECKS` in `checks/__init__.py`.
- Tune thresholds: constants at the top of each `checks/*.py` file.
