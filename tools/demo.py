"""Print what a ground station alone says vs. SprayWait for one simulated scenario.

Usage: python -m tools.demo [scenario]   (default: evening_inversion)
"""

import sys

from spraywait import decide, single_station_decision
from spraywait.pesticides import LocalPesticideDB
from spraywait.weather import SimulatedSource


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    scenario = args[0] if args else "evening_inversion"
    reading = SimulatedSource(scenario).get_reading()
    pesticide = LocalPesticideDB().get("Captan")

    print("Reading at", reading.timestamp.strftime("%H:%M"))
    for lv in reading.sorted_levels():
        print(f"  {lv.height_ft:>3g} ft: {lv.temp_f}F, {lv.wind_mph} mph from {lv.wind_dir_deg} deg")

    for label, d in (("Ground station only", single_station_decision(reading, pesticide)),
                     ("SprayWait", decide(reading, pesticide))):
        print(f"\n{label}: {d.status.value}")
        for r in d.reasons:
            print("  -", r)


if __name__ == "__main__":  # pragma: no cover
    main()
