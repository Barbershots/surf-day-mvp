"""
Ingest OPDI v0.0.2 open data (derived from OpenSky ADS-B).

Two tables are used:

* flight_list  (monthly)  - one row per flight: id, callsign, aircraft type,
                            ADEP/ADES, first_seen/last_seen. We filter to
                            arrivals at EGHH (Bournemouth).
* flight_events (10-day)  - milestone events along each trajectory, joined to a
                            flight via `flight_id`. Each event has lat/lon and
                            altitude (ft). The events we care about for noise
                            compliance are:
                              level-start / level-end  -> level-off segments
                              top-of-descent           -> where descent began
                              first/last-xing-flNN      -> descent profile points

Files are cached in ./data so re-runs are free. Each 10-day events file is
~150-400 MB; downloading is the slow part, the analysis is fast.
"""
from __future__ import annotations

import os
import re
from datetime import date, datetime

import pandas as pd
import pyarrow.parquet as pq

import config

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# The OPDI 10-day event windows are NOT a fixed grid (each year starts on a
# different day, e.g. 2025 starts 2025-01-05), so the real list of published
# files is scraped from the download page rather than computed.
_EVENT_INDEX_PAGE = "https://www.opdi.aero/flight-event-data"
_EVENT_FILE_RE = re.compile(r"flight_events_(\d{8})_(\d{8})\.parquet")


def _download(url: str, dest: str) -> str:
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    import urllib.request

    tmp = dest + ".part"
    print(f"  downloading {os.path.basename(dest)} ...", flush=True)
    urllib.request.urlretrieve(url, tmp)
    os.replace(tmp, dest)
    return dest


def _available_event_windows():
    """All published (start, end) event windows, scraped once and cached."""
    cache = os.path.join(DATA_DIR, "_event_windows.txt")
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(cache):
        import urllib.request

        html = urllib.request.urlopen(_EVENT_INDEX_PAGE, timeout=60).read().decode("utf-8", "ignore")
        pairs = sorted(set(_EVENT_FILE_RE.findall(html)))
        with open(cache, "w") as f:
            f.write("\n".join(f"{s}_{e}" for s, e in pairs))
    out = []
    for line in open(cache):
        line = line.strip()
        if not line:
            continue
        s, e = line.split("_")
        out.append((datetime.strptime(s, "%Y%m%d").date(),
                    datetime.strptime(e, "%Y%m%d").date()))
    return out


def event_windows(start: date, end: date):
    """Yield every published 10-day event window overlapping [start, end)."""
    for ws, we in _available_event_windows():
        if ws < end and we > start:
            yield ws, we


def load_flight_list(year: int, month: int) -> pd.DataFrame:
    ym = f"{year:04d}{month:02d}"
    url = config.OPDI_FLIGHT_LIST.format(ym=ym)
    path = _download(url, os.path.join(DATA_DIR, f"flight_list_{ym}.parquet"))
    return pq.read_table(path).to_pandas()


_EVENT_COLS = ["flight_id", "type", "event_time", "longitude", "latitude", "altitude"]


def load_flight_events(window_start: date, window_end: date,
                       only_ids: set | None = None,
                       delete_after: bool = False) -> pd.DataFrame:
    """
    Load one 10-day events file. For the multi-year sweep, pass `only_ids` (the
    EGHH arrival ids) to keep just those rows and `delete_after=True` to remove
    the ~200-400 MB raw file once filtered, so disk usage stays tiny.
    """
    s, e = window_start.strftime("%Y%m%d"), window_end.strftime("%Y%m%d")
    url = config.OPDI_FLIGHT_EVENTS.format(start=s, end=e)
    path = _download(url, os.path.join(DATA_DIR, f"flight_events_{s}_{e}.parquet"))
    df = pq.read_table(path, columns=_EVENT_COLS).to_pandas()
    if only_ids is not None:
        df = df[df["flight_id"].isin(only_ids)].copy()
    if delete_after:
        try:
            os.remove(path)
        except OSError:
            pass
    return df


def arrivals(flight_list: pd.DataFrame, airport: str = None) -> pd.DataFrame:
    """EGHH arrivals with aircraft-category and day/evening/night classification."""
    from . import classify

    airport = airport or config.DEST_AIRPORT
    arr = flight_list[flight_list["ades"] == airport].copy()
    return classify.add_classification(arr)


def load_period(start: date, end: date, large_jet_only: bool = False):
    """
    Load every EGHH arrival in [start, end) and the flight_events belonging to
    those arrivals. Returns (arrivals_df, events_df) where events_df is already
    filtered to arrival flights and carries the arrival metadata columns
    (callsign, typecode, is_large_jet, last_seen).

    Spans the necessary monthly flight_list files and 10-day event windows
    automatically.
    """
    # 1) Flight lists for every month the period touches.
    months = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        months.append((y, m))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    fl = pd.concat([load_flight_list(y, m) for y, m in months], ignore_index=True)
    arr = arrivals(fl)
    if large_jet_only:
        arr = arr[arr["is_large_jet"]]
    arr_ids = set(arr["id"])

    # 2) Events for every 10-day window the period touches, filtered to arrivals.
    parts = []
    for ws, we in event_windows(start, end):
        ev = load_flight_events(ws, we)
        parts.append(ev[ev["flight_id"].isin(arr_ids)])
    events = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

    # 3) Attach arrival metadata to each event.
    meta = arr[["id", "flt_id", "typecode", "icao_aircraft_class", "category",
                "is_large_jet", "time_window", "last_seen", "dof"]].rename(
        columns={"id": "flight_id"})
    events = events.merge(meta, on="flight_id", how="left")
    return arr, events
