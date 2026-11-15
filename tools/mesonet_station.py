"""Run the Mesonet replay as a live farm station: post each 5-minute reading to the app, in real time.

    FARM_API_KEY=... python -m tools.mesonet_station http://localhost:8000 [--csv PATH] [--backfill-hours N]

The server must run with FARM_WEATHER=push (and the same FARM_API_KEY) for live mode to use it.
--backfill-hours first uploads the last N hours, like a datalogger sending its buffer after reconnecting.
"""

import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError

from spraywait.weather.mesonet import DEFAULT_CSV, STEP, MesonetStation
from tools.push_reading import push


def send(base_url: str, key: str, payload: dict) -> bool:
    """Post one payload; report and carry on if the app rejects it or is unreachable."""
    try:
        push(base_url, key, payload)
        print(f"{payload['observed_at']}  sent", flush=True)
        return True
    except HTTPError as e:
        print(f"{payload['observed_at']}  rejected ({e.code}): {e.read().decode(errors='replace')}", flush=True)
    except (URLError, OSError) as e:
        print(f"{payload['observed_at']}  app unreachable: {e}", flush=True)
    return False


def seconds_to_next_slot(now: datetime) -> float:
    """Seconds until the next 5-minute UTC boundary."""
    return (MesonetStation.slot(now) + STEP - now).total_seconds()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--csv", default=DEFAULT_CSV)
    ap.add_argument("--backfill-hours", type=float, default=0)
    args = ap.parse_args(argv[1:])
    key = os.environ.get("FARM_API_KEY")
    if not key:
        print("set FARM_API_KEY (must match the server's)")
        return 2

    station = MesonetStation(args.csv)
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=args.backfill_hours)
    for payload in station.payloads_since(start, now):
        send(args.url, key, payload)
    while True:
        time.sleep(seconds_to_next_slot(datetime.now(timezone.utc)))
        send(args.url, key, station.payload())


if __name__ == "__main__":  # pragma: no cover
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        sys.exit(0)
