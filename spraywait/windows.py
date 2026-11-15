"""Spray windows: run the same checks on each forecast hour, then find the next GO window and the next worsening."""

from datetime import timedelta

from spraywait.decision import Status, decide
from spraywait.pesticides.db import Pesticide
from spraywait.weather.types import Reading

HOUR = timedelta(hours=1)
RANK = {Status.GO: 0, Status.CAUTION: 1, Status.STOP: 2}


def plan_windows(forecast: list[Reading], pesticide: Pesticide) -> dict:
    """Status per forecast hour, plus:

    next_go:   first run of consecutive GO hours {start, end} (end = after the last GO hour), or None.
    worsens:   if the first hour is GO or CAUTION, the first later hour that is worse {time, status, checks}, or None.
    """
    hours = []
    for r in sorted(forecast, key=lambda r: r.timestamp):
        d = decide(r, pesticide, now=r.timestamp)  # forecast hours are never "stale"
        hours.append({"time": r.timestamp, "status": d.status, "checks": sorted({f.check for f in d.flags})})

    next_go = None
    for i, h in enumerate(hours):
        if h["status"] is Status.GO:
            j = i
            while j + 1 < len(hours) and hours[j + 1]["status"] is Status.GO and \
                    hours[j + 1]["time"] - hours[j]["time"] <= HOUR:
                j += 1
            next_go = {"start": h["time"], "end": hours[j]["time"] + HOUR}
            break

    worsens = None
    if hours:
        first = hours[0]["status"]
        worsens = next((h for h in hours[1:] if RANK[h["status"]] > RANK[first]), None)

    return {"hours": hours, "next_go": next_go, "worsens": worsens}


__all__ = ["plan_windows"]
