import io
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError

import pytest
from fastapi.testclient import TestClient

import api.main as main
import tools.mesonet_station as tool
from spraywait.log import DecisionLog
from spraywait.weather import FarmStationStore, Level, MesonetFeed, MesonetStation, Reading, parse_station_payload

HEADER = "STID,STNM,TIME,RELH,TAIR,WSPD,WVEC,WDIR,WDSD,WSSD,WMAX,RAIN,PRES,SRAD,TA9M,WS2M\n"
ROWS = [
    "ACME,110,00:00,74,8.6,3.3,3.2,105,9.8,0.5,4.5,0.25,971.91,0,8.8,2.6",  # inversion: 9 m warmer
    "ACME,110,00:05,75,10.0,4.0,3.4,99,11.3,0.6,5.6,0.00,971.78,0,9.0,3.0",
    "ACME,110,00:10,-996,-996,-996,-996,-996,-996,-996,-996,-996,-996,-996,-996,-996",  # all missing
]
UTC = timezone.utc


@pytest.fixture
def csv_path(tmp_path):
    p = tmp_path / "day.csv"
    p.write_text(HEADER + "\n".join(ROWS) + "\n")
    return p


@pytest.fixture
def station(csv_path):
    return MesonetStation(csv_path)


def at(h, m, s=0):
    return datetime(2026, 11, 15, h, m, s, tzinfo=UTC)


def test_payload_uses_row_for_current_utc_slot(station):
    """At 00:07 UTC the station reports the 00:05 row, stamped with today's date, as vendor-style metric sensors."""
    p = station.payload(at(0, 7, 42))
    assert p["station_id"] == "mesonet-acme"
    assert p["observed_at"] == "2026-11-15T00:05:00Z"
    vals = {s["id"]: s["value"] for s in p["sensors"]}
    assert vals["TAIR"] == 10.0 and vals["TA9M"] == 9.0 and vals["WS2M"] == 3.0 and vals["WDIR"] == 99


def test_shift_replays_a_later_row_at_the_real_time(csv_path):
    """With a shift, the station sends the row `shift` ahead of the clock but stamps the real time."""
    p = MesonetStation(csv_path, shift=timedelta(minutes=5)).payload(at(0, 0))
    assert p["observed_at"] == "2026-11-15T00:00:00Z"
    assert {s["id"]: s["value"] for s in p["sensors"]}["TAIR"] == 10.0  # the 00:05 row


def test_shift_rounds_to_five_minutes(csv_path):
    """A shift that isn't a multiple of 5 min (e.g. 0.6 h = 36 min) rounds to the row grid instead of matching nothing."""
    st = MesonetStation(csv_path, shift=timedelta(minutes=6))
    assert st.shift == timedelta(minutes=5)
    assert {s["id"]: s["value"] for s in st.payload(at(0, 0))["sensors"]}["TAIR"] == 10.0


def test_missing_codes_and_absent_rows_report_null(station):
    """Mesonet -99x codes, and times past the end of the file, become null sensor values."""
    for t in (at(0, 10), at(23, 55)):
        assert all(s["value"] is None for s in station.payload(t)["sensors"])


def test_payload_parses_to_two_paired_levels(station):
    """Wind at 2 m and 10 m pairs with temps at 1.5 m and 9 m; direction lands on the upper level."""
    r = parse_station_payload(station.payload(at(0, 0)))
    lo, hi = r.levels
    assert (lo.height_ft, lo.temp_f, lo.wind_mph, lo.wind_dir_deg) == (4.9, 47.5, 5.8, None)
    assert (hi.height_ft, hi.temp_f, hi.wind_mph, hi.wind_dir_deg) == (29.5, 47.8, 7.4, 105)


def test_all_missing_row_parses_to_no_levels(station):
    """A row of missing values gives a reading with no usable heights."""
    assert parse_station_payload(station.payload(at(0, 10))).levels == []


def test_wind_far_from_any_thermometer_is_not_paired():
    """A wind sensor more than PAIR_FT from the nearest thermometer stays unpaired and is dropped."""
    r = parse_station_payload({"observed_at": "2026-11-15T00:00:00Z", "sensors": [
        {"type": "air_temp", "height_m": 1.5, "value": 10, "unit": "C"},
        {"type": "wind_speed", "height_m": 5.0, "value": 2, "unit": "m/s"}]})
    assert r.levels == []


def test_payloads_since_covers_every_slot(station):
    """Backfill yields one payload per 5-minute slot from start through now, inclusive."""
    ps = station.payloads_since(at(0, 1), at(0, 12))
    assert [p["observed_at"][11:16] for p in ps] == ["00:00", "00:05", "00:10"]


def test_empty_csv_rejected(tmp_path):
    """A file with a header but no rows is an error, not a silent empty station."""
    p = tmp_path / "empty.csv"
    p.write_text(HEADER)
    with pytest.raises(ValueError):
        MesonetStation(p)


def test_store_history_is_sorted_deduped_and_pruned():
    """History is oldest-first, a resent timestamp replaces its reading, and readings older than `keep` drop."""
    store = FarmStationStore(keep=timedelta(hours=1))
    t = datetime(2026, 11, 15, 12)
    mk = lambda ts, src="a": Reading(ts, [Level(5, 60, 5)], source=src)
    store.push(mk(t))
    store.push(mk(t - timedelta(minutes=5)))
    store.push(mk(t, "b"))
    assert [(r.timestamp, r.source) for r in store.history()] == [(t - timedelta(minutes=5), "a"), (t, "b")]
    store.push(mk(t + timedelta(hours=2)))
    assert [r.timestamp for r in store.history()] == [t + timedelta(hours=2)]


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("FARM_API_KEY", "k")
    monkeypatch.setenv("FARM_WEATHER", "push")
    monkeypatch.setattr(main, "farm", FarmStationStore())
    monkeypatch.setattr(main, "log", DecisionLog(tmp_path / "log.jsonl"))
    monkeypatch.setattr(main, "_last_logged", {})
    return TestClient(main.app)


def test_station_endpoint_empty(client):
    """Before any report the station endpoint says so, with the weather mode."""
    assert client.get("/api/station").json() == {"weather": "push", "replay_shift_h": None, "latest": None,
                                                 "age_s": None, "history": []}


def test_station_endpoint_reports_history_with_status(client, station):
    """Pushed Mesonet readings come back oldest-first, each with the status and checks it implied."""
    now = datetime.now(UTC)
    for p in station.payloads_since(now - timedelta(minutes=5), now):
        p["sensors"] = station.payload(at(0, 0))["sensors"]  # the inversion row, at current times
        assert client.post("/api/readings", json=p, headers={"X-Farm-Key": "k"}).status_code == 201
    body = client.get("/api/station").json()
    assert len(body["history"]) == 2 and body["latest"] == body["history"][-1]
    assert body["latest"]["source"] == "farm station mesonet-acme"
    assert "inversion" in body["latest"]["checks"] and body["latest"]["status"] in ("CAUTION", "STOP")
    assert 0 <= body["age_s"] < 600


def test_station_page_served(client):
    """The /station page is served and the main page links to it."""
    assert "Farm station" in client.get("/station").text
    assert 'href="/station"' in client.get("/").text


def http_error(code):
    return HTTPError("u", code, "x", {}, io.BytesIO(b"bad payload"))


@pytest.mark.parametrize("effect,ok,printed", [
    (None, True, "sent"), (http_error(422), False, "rejected (422): bad payload"),
    (URLError("down"), False, "unreachable"),
])
def test_send_reports_outcome(monkeypatch, capsys, effect, ok, printed):
    """send() posts once and prints success, a rejection with its body, or an unreachable app, without raising."""
    def fake_push(*a):
        if effect:
            raise effect
    monkeypatch.setattr(tool, "push", fake_push)
    assert tool.send("http://x", "k", {"observed_at": "T"}) is ok
    assert printed in capsys.readouterr().out


@pytest.mark.parametrize("now,secs", [(at(0, 7, 30), 150), (at(0, 5), 300), (at(23, 59, 59), 1)])
def test_seconds_to_next_slot(now, secs):
    """The station wakes on 5-minute UTC boundaries."""
    assert tool.seconds_to_next_slot(now) == secs


def test_main_requires_key(monkeypatch, capsys):
    """Without FARM_API_KEY the station refuses to start."""
    monkeypatch.delenv("FARM_API_KEY", raising=False)
    assert tool.main(["x", "http://x"]) == 2


def test_main_backfills_then_sends_each_slot(monkeypatch, csv_path):
    """main() uploads the backfill window, then sends one reading per wait until stopped."""
    monkeypatch.setenv("FARM_API_KEY", "k")
    sent, waits = [], []

    class Stop(Exception):
        pass

    def fake_sleep(s):
        waits.append(s)
        if len(waits) > 1:
            raise Stop

    monkeypatch.setattr(tool, "send", lambda url, key, p: sent.append(p["observed_at"]))
    monkeypatch.setattr(tool.time, "sleep", fake_sleep)
    with pytest.raises(Stop):
        tool.main(["x", "http://x", "--csv", str(csv_path), "--backfill-hours", "0.25", "--shift-hours", "1"])
    assert len(sent) in (4, 5)  # 15 min backfill (3-4 slots) + 1 live send
    assert all(0 < w <= 300 for w in waits)


def test_feed_backfills_then_catches_up(station):
    """First sync stores the backfill window; later syncs add only newly due slots; empty rows are skipped."""
    store = FarmStationStore()
    feed = MesonetFeed(station, store, backfill=timedelta(minutes=5))
    feed.sync(at(0, 6))
    assert [r.timestamp.astimezone(UTC).strftime("%H:%M") for r in store.history()] == ["00:00", "00:05"]
    feed.sync(at(0, 9))  # same slot: nothing new
    feed.sync(at(0, 11))  # 00:10 is all missing: skipped
    assert len(store.history()) == 2 and feed.last == at(0, 10)


@pytest.fixture
def mesonet_client(client, monkeypatch, csv_path):
    monkeypatch.setenv("FARM_WEATHER", "mesonet")
    monkeypatch.setenv("MESONET_CSV", str(csv_path))
    monkeypatch.setattr(main, "_feed", None)
    return client


def test_mesonet_mode_feeds_live_decision_and_station(mesonet_client, monkeypatch, tmp_path):
    """In mesonet mode the app replays the CSV itself: live decisions and /api/station both see it."""
    day = tmp_path / "full.csv"  # the inversion row at every 5-minute slot, so any clock time has data
    day.write_text(HEADER + "".join(ROWS[0].replace("00:00", f"{m // 60:02d}:{m % 60:02d}") + "\n"
                                    for m in range(0, 1440, 5)))
    monkeypatch.setenv("MESONET_CSV", str(day))
    monkeypatch.setenv("MESONET_SHIFT_HOURS", "1")
    body = mesonet_client.post("/api/decision", json={}).json()
    assert body["reading"]["source"] == "farm station mesonet-acme"
    assert body["decision"]["status"] == "STOP"
    assert any(f["check"] == "inversion" for f in body["decision"]["flags"])
    station = mesonet_client.get("/api/station").json()
    assert len(station["history"]) > 1 and station["replay_shift_h"] == 1


def test_mesonet_mode_without_csv_fails_safe(mesonet_client, monkeypatch, tmp_path):
    """With the data file missing, mesonet mode has no readings: live says STOP, station reports none."""
    monkeypatch.setenv("MESONET_CSV", str(tmp_path / "nope.csv"))
    assert mesonet_client.post("/api/decision", json={}).json()["decision"]["status"] == "STOP"
    assert mesonet_client.get("/api/station").json()["latest"] is None
