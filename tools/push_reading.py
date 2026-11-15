"""Stand-in farm weather station: push one simulated reading to the live app.

    FARM_API_KEY=... python -m tools.push_reading https://your-app.onrender.com clear_midday
"""

import json
import os
import sys
from urllib.request import Request, urlopen

from spraywait.weather import SimulatedSource


def push(base_url: str, scenario: str, key: str) -> dict:
    reading = SimulatedSource(scenario).get_reading().to_dict()
    reading["source"] = f"farm station (simulated {scenario})"
    req = Request(f"{base_url.rstrip('/')}/api/readings", data=json.dumps(reading).encode(),
                  headers={"Content-Type": "application/json", "X-Farm-Key": key}, method="POST")
    with urlopen(req, timeout=15) as res:
        return json.load(res)


def main(argv: list[str]) -> int:
    if len(argv) < 2 or not os.environ.get("FARM_API_KEY"):
        print(__doc__)
        return 2
    scenario = argv[2] if len(argv) > 2 else "clear_midday"
    print(json.dumps(push(argv[1], scenario, os.environ["FARM_API_KEY"]), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
