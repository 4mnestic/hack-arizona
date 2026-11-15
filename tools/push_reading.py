"""Stand-in for a real farm station: push one dummy-station payload to the app.

    FARM_API_KEY=... python -m tools.push_reading https://your-app.onrender.com

The server must run with FARM_WEATHER=push for live mode to use pushed data.
"""

import json
import os
import sys
from urllib.request import Request, urlopen

from spraywait.weather import DummyStation


def push(base_url: str, key: str, payload: dict | None = None) -> dict:
    """POST one station payload (default: the dummy station's current one) to the app."""
    body = payload or DummyStation().payload()
    req = Request(f"{base_url.rstrip('/')}/api/readings", data=json.dumps(body).encode(),
                  headers={"Content-Type": "application/json", "X-Farm-Key": key}, method="POST")
    with urlopen(req, timeout=15) as res:
        return json.load(res)


def main(argv: list[str]) -> int:
    if len(argv) < 2 or not os.environ.get("FARM_API_KEY"):
        print(__doc__)
        return 2
    print(json.dumps(push(argv[1], os.environ["FARM_API_KEY"]), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
