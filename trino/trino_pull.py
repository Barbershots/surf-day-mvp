#!/usr/bin/env python3
"""
STEP 2 of 3. Chunked pull of Brockenhurst approach data from OpenSky Trino.

Design notes, because OpenSky's access rules matter here:
  * every query filters on the `hour` partition (mandatory);
  * windows are ONE WEEK by default, so this is many small queries rather than
    one big range;
  * queries run strictly sequentially, one at a time, with a pause between;
  * the heavy lifting is done SERVER-SIDE. Rather than dumping millions of raw
    state vectors, Trino reduces each flight to a single row: the moment it
    passed closest to the village. A decade comes back as roughly 200k rows,
    not hundreds of millions;
  * every week is cached to disk, so an interrupted run resumes and nothing is
    ever fetched twice.

    python trino_pull.py --start 2016-01-01 --end 2026-06-01

Altitudes from OpenSky are in METRES. They are converted to feet downstream.
`baroaltitude` is pressure altitude against the 1013.25 standard, exactly like
the OPDI data, so the same QNH correction applies. `geoaltitude` is GNSS height
above the WGS-84 ellipsoid, which is about 155 ft higher than height above sea
level in this part of the country.
"""
from __future__ import annotations

import argparse
import os
import time as _time
from datetime import datetime, timedelta, timezone

import pandas as pd
from pyopensky.trino import Trino

BLAT, BLON = 50.8217, -1.5739          # Brockenhurst village centre
LAT0, LAT1 = BLAT - 0.14, BLAT + 0.14
LON0, LON1 = BLON - 0.22, BLON + 0.22
GATE_KM = 5.0                          # keep the closest approach within 5 km
HDG_LO, HDG_HI = 215, 295              # inbound to runway 26 (track 255)
MAX_ALT_M = 3000                       # ~10,000 ft

import pathlib
HERE = pathlib.Path(__file__).resolve().parent
CACHE = str(HERE / 'cache')
os.makedirs(CACHE, exist_ok=True)

# One row per flight per day: the state vector at closest approach to the
# village, plus a simple count of how many points that flight contributed
# (a rough quality indicator).
SQL = """
WITH pts AS (
  SELECT
    icao24,
    TRIM(callsign) AS callsign,
    time, lat, lon, baroaltitude, geoaltitude, velocity, heading, vertrate,
    CAST(FLOOR(time/86400) AS BIGINT) AS day_idx,
    SQRT(
      POWER((lon - {blon}) * 111.320 * COS(RADIANS({blat})), 2) +
      POWER((lat - {blat}) * 110.574, 2)
    ) AS d_km
  FROM state_vectors_data4
  WHERE hour >= {h0} AND hour < {h1}
    AND lat BETWEEN {lat0} AND {lat1}
    AND lon BETWEEN {lon0} AND {lon1}
    AND baroaltitude IS NOT NULL
    AND baroaltitude < {maxalt}
    AND NOT onground
    AND heading BETWEEN {hlo} AND {hhi}
    AND callsign IS NOT NULL
),
near AS (
  SELECT * FROM pts WHERE d_km < {gate}
),
ranked AS (
  SELECT *,
         ROW_NUMBER() OVER (PARTITION BY icao24, callsign, day_idx ORDER BY d_km) AS rn,
         COUNT(*)    OVER (PARTITION BY icao24, callsign, day_idx)                AS n_points
  FROM near
)
SELECT icao24, callsign, time, lat, lon, baroaltitude, geoaltitude,
       velocity, heading, vertrate, d_km, n_points
FROM ranked
WHERE rn = 1
"""


def hour_of(dt: datetime) -> int:
    return int(dt.replace(minute=0, second=0, microsecond=0).timestamp())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--start', required=True)          # YYYY-MM-DD
    ap.add_argument('--end', required=True)
    ap.add_argument('--days', type=int, default=7, help='chunk size in days')
    ap.add_argument('--pause', type=float, default=5.0, help='seconds between queries')
    args = ap.parse_args()

    start = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)
    trino = Trino()

    cur, n_new, n_cached = start, 0, 0
    while cur < end:
        nxt = min(cur + timedelta(days=args.days), end)
        tag = cur.strftime('%Y%m%d')
        cache = f'{CACHE}/gate_{tag}.parquet'
        if os.path.exists(cache):
            n_cached += 1
            cur = nxt
            continue
        sql = SQL.format(h0=hour_of(cur), h1=hour_of(nxt),
                         lat0=LAT0, lat1=LAT1, lon0=LON0, lon1=LON1,
                         blat=BLAT, blon=BLON, gate=GATE_KM,
                         maxalt=MAX_ALT_M, hlo=HDG_LO, hhi=HDG_HI)
        t0 = _time.time()
        try:
            df = trino.query(sql)
        except Exception as e:                     # keep going; note the gap
            print(f'{tag}: FAILED ({e.__class__.__name__}: {str(e)[:80]})', flush=True)
            _time.sleep(30)
            cur = nxt
            continue
        df.to_parquet(cache, index=False)
        n_new += 1
        print(f'{tag}: {len(df):>5} flights  ({_time.time()-t0:.0f}s)', flush=True)
        _time.sleep(args.pause)                    # stay well inside fair use
        cur = nxt

    parts = [pd.read_parquet(f'{CACHE}/{f}') for f in sorted(os.listdir(CACHE))
             if f.startswith('gate_') and f.endswith('.parquet')]
    if not parts:
        print('no data pulled')
        return
    all_df = pd.concat(parts, ignore_index=True)
    all_df.to_parquet(str(HERE / 'brockenhurst_gate_10yr.parquet'), index=False)
    print(f'\n{n_new} new chunks, {n_cached} already cached')
    print(f'wrote {HERE / "brockenhurst_gate_10yr.parquet"}  ({len(all_df):,} flights)')


if __name__ == '__main__':
    main()
