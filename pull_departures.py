#!/usr/bin/env python3
"""
Pull the FULL 3-year Bournemouth departure track set, to match the cached
arrivals (eghh_events_*). For each event window that we hold arrivals for, this
downloads the Europe-wide flight_events file, keeps only EGHH departures, writes
data/eghh_dep_events_START_END.parquet, and deletes the ~390 MB raw file.

Resumable: windows whose output already exists are skipped, so it can be
re-run if interrupted.

    python pull_departures.py
"""
import glob, re, os
import numpy as np, pandas as pd, pyarrow.parquet as pq
import config
from brockenhurst import opdi

LOG = "/tmp/pull_dep_full.log"
def log(*a):
    with open(LOG, "a") as f:
        print(*a, file=f, flush=True)
    print(*a, flush=True)


def to_u64(s):
    return s.view("uint64") if s.dtype == np.int64 else s.astype("uint64")


def dep_id_set():
    ids = set()
    for f in sorted(glob.glob("data/flight_list_2022*.parquet") +
                    glob.glob("data/flight_list_2023*.parquet") +
                    glob.glob("data/flight_list_2024*.parquet") +
                    glob.glob("data/flight_list_2025*.parquet") +
                    glob.glob("data/flight_list_2026*.parquet")):
        d = pd.read_parquet(f, columns=["id", "adep"])
        ids |= set(int(x) for x in to_u64(d.loc[d["adep"] == "EGHH", "id"]))
    return ids


def windows():
    ws = []
    for f in sorted(glob.glob("data/eghh_events_*.parquet")):
        m = re.search(r"eghh_events_(\d{8})_(\d{8})", f)
        if m:
            ws.append((m.group(1), m.group(2)))
    return ws


def main():
    open(LOG, "w").close()
    dep = dep_id_set()
    log(f"EGHH departure ids: {len(dep):,}")
    ws = windows()
    log(f"windows to process: {len(ws)}")
    total = 0
    for i, (s, e) in enumerate(ws, 1):
        out = f"data/eghh_dep_events_{s}_{e}.parquet"
        if os.path.exists(out):
            log(f"[{i}/{len(ws)}] {s}-{e} exists, skip"); continue
        url = config.OPDI_FLIGHT_EVENTS.format(start=s, end=e)
        raw = f"data/flight_events_{s}_{e}.parquet"
        try:
            opdi._download(url, raw)
        except Exception as ex:
            log(f"[{i}/{len(ws)}] {s}-{e} DOWNLOAD FAILED: {ex}"); continue
        keep = []
        pf = pq.ParquetFile(raw)
        for rg in range(pf.num_row_groups):
            df = pf.read_row_group(rg, columns=["flight_id", "latitude", "longitude", "altitude"]).to_pandas()
            df["flight_id"] = to_u64(df["flight_id"])
            df = df[df["flight_id"].isin(dep)]
            if len(df):
                keep.append(df)
        os.remove(raw)
        sub = pd.concat(keep, ignore_index=True) if keep else pd.DataFrame(columns=["flight_id","latitude","longitude","altitude"])
        sub.to_parquet(out)
        total += sub["flight_id"].nunique() if len(sub) else 0
        log(f"[{i}/{len(ws)}] {s}-{e} -> {len(sub):,} rows, {sub['flight_id'].nunique() if len(sub) else 0} deps")
    log(f"DONE. cumulative distinct departures seen: {total}")


if __name__ == "__main__":
    main()
