#!/usr/bin/env python3
"""
Full multi-year sweep of Bournemouth (EGHH) arrivals over Brockenhurst.

Streams the ~110 Europe-wide OPDI event files one at a time: download -> keep
only the EGHH-arrival rows (tiny) -> delete the big raw file. The small
per-window extract is cached in ./data so the sweep is resumable and cheap to
re-run. Disk never holds more than one raw file (~400 MB) at a time.

    python sweep.py --start 2023-01-01 --end 2026-01-01

Outputs (./outputs/sweep):
    arrivals.csv           every EGHH arrival, classified (category + day/eve/night)
    per_flight.csv         arrivals with trajectory data + measured Brockenhurst height
    night_large_jets.csv   the night-time low-flying table (plain-language)
    summary_by_year.csv    year-on-year headline numbers
    *.png                  plain-English charts
"""
from __future__ import annotations

import argparse
import os
from datetime import date, datetime

import pandas as pd

from brockenhurst import approach, opdi, report

ARR_COLS = ["id", "flt_id", "typecode", "icao_aircraft_class", "category",
            "is_large_jet", "time_window", "last_seen", "dof"]


def _d(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def months_between(start: date, end: date):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        m += 1
        if m > 12:
            y, m = y + 1, 1


def collect_arrivals(start, end) -> pd.DataFrame:
    """EGHH arrivals across the whole period, built one month at a time."""
    parts = []
    for y, m in months_between(start, end):
        fl = opdi.load_flight_list(y, m)
        a = opdi.arrivals(fl)
        parts.append(a[ARR_COLS])
        del fl, a
        print(f"  arrivals {y}-{m:02d}: {len(parts[-1])}", flush=True)
    arr = pd.concat(parts, ignore_index=True)
    arr["year"] = pd.to_datetime(arr["dof"]).dt.year
    return arr


def collect_events(start, end, arr_ids) -> pd.DataFrame:
    """Stream every event window, caching the small EGHH-only extract per window."""
    parts = []
    windows = list(opdi.event_windows(start, end))
    for i, (ws, we) in enumerate(windows, 1):
        s, e = ws.strftime("%Y%m%d"), we.strftime("%Y%m%d")
        cache = os.path.join(opdi.DATA_DIR, f"eghh_events_{s}_{e}.parquet")
        if os.path.exists(cache):
            ev = pd.read_parquet(cache)
        else:
            ev = opdi.load_flight_events(ws, we, only_ids=arr_ids, delete_after=True)
            ev.to_parquet(cache, index=False)
        parts.append(ev)
        print(f"  [{i}/{len(windows)}] {s}->{e}: {len(ev)} EGHH events", flush=True)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", required=True, type=_d)
    ap.add_argument("--end", required=True, type=_d)
    ap.add_argument("--outdir", default="outputs/sweep")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    print("Collecting EGHH arrivals ...", flush=True)
    arr = collect_arrivals(args.start, args.end)
    print(f"Total EGHH arrivals {args.start}..{args.end}: {len(arr)}", flush=True)
    arr.to_csv(os.path.join(args.outdir, "arrivals.csv"), index=False)

    print("Streaming trajectory events (download -> filter -> delete) ...", flush=True)
    events = collect_events(args.start, args.end, set(arr["id"]))

    # Attach arrival metadata to events, then analyse.
    meta = arr.rename(columns={"id": "flight_id"})[
        ["flight_id", "flt_id", "typecode", "icao_aircraft_class", "category",
         "is_large_jet", "time_window", "last_seen", "dof", "year"]]
    events = events.merge(meta, on="flight_id", how="left")

    pf = approach.per_flight(arr.rename(columns={}), events)
    pf = pf.merge(arr[["id", "year"]].rename(columns={"id": "flight_id"}),
                  on="flight_id", how="left")
    pf.to_csv(os.path.join(args.outdir, "per_flight.csv"), index=False)

    report.build(arr, events, pf, args.outdir)
    print(f"\nDone. See {args.outdir}/", flush=True)


if __name__ == "__main__":
    main()
