#!/usr/bin/env python3
"""
STEP 1 of 3. Run this FIRST, before any bulk pull.

Checks how far back OpenSky's coverage of the Brockenhurst approach is actually
usable. Coverage grew enormously over the last decade, so a raw "flights per
year" trend from OpenSky mostly measures the growth of the receiver network,
not the growth of air traffic. This probe samples ONE WEEK per year so we can
see where real coverage begins before committing to a long pull.

Respects the OpenSky fair-use rules: every query filters on the `hour`
partition, windows are one week, queries run strictly one at a time, and
results are cached so nothing is ever fetched twice.

    python trino_probe.py
"""
from __future__ import annotations

import os
import time as _time
from datetime import datetime, timezone

import pandas as pd
from pyopensky.trino import Trino

# Brockenhurst village centre.
BLAT, BLON = 50.8217, -1.5739
# Small box around the village: roughly +/- 15 km.
LAT0, LAT1 = BLAT - 0.14, BLAT + 0.14
LON0, LON1 = BLON - 0.22, BLON + 0.22
# Runway-26 approach track is 255 deg. Inbound arrivals sit in a wide arc
# around that; runway-08 departures head the opposite way (~075) and are
# excluded by this filter.
HDG_LO, HDG_HI = 215, 295
MAX_ALT_M = 3000            # ~10,000 ft. NOTE: OpenSky altitudes are METRES.

import pathlib
HERE = pathlib.Path(__file__).resolve().parent
CACHE = str(HERE / 'cache')
os.makedirs(CACHE, exist_ok=True)


def hour_of(dt: datetime) -> int:
    """Unix start-of-hour, which is how the `hour` partition is keyed."""
    return int(dt.replace(minute=0, second=0, microsecond=0, tzinfo=timezone.utc).timestamp())


SQL = """
SELECT
  COUNT(*)                                   AS n_points,
  COUNT(DISTINCT icao24)                     AS n_aircraft,
  COUNT(DISTINCT CAST(FLOOR(time/86400) AS BIGINT)) AS n_days_seen,
  MIN(baroaltitude)                          AS min_alt_m,
  APPROX_PERCENTILE(baroaltitude, 0.5)       AS median_alt_m
FROM state_vectors_data4
WHERE hour >= {h0} AND hour < {h1}
  AND lat BETWEEN {lat0} AND {lat1}
  AND lon BETWEEN {lon0} AND {lon1}
  AND baroaltitude IS NOT NULL
  AND baroaltitude < {maxalt}
  AND NOT onground
  AND heading BETWEEN {hlo} AND {hhi}
"""


def main() -> None:
    trino = Trino()
    rows = []
    for year in range(2016, 2027):
        # A representative summer week: peak season, so absence of flights
        # means absence of coverage rather than absence of traffic.
        start = datetime(year, 7, 8, tzinfo=timezone.utc)
        stop = datetime(year, 7, 15, tzinfo=timezone.utc)
        if stop > datetime.now(timezone.utc):
            break
        cache = f'{CACHE}/probe_{year}.csv'
        if os.path.exists(cache):
            df = pd.read_csv(cache)
            print(f'{year}: (cached)', end=' ')
        else:
            sql = SQL.format(h0=hour_of(start), h1=hour_of(stop),
                             lat0=LAT0, lat1=LAT1, lon0=LON0, lon1=LON1,
                             maxalt=MAX_ALT_M, hlo=HDG_LO, hhi=HDG_HI)
            t0 = _time.time()
            df = trino.query(sql)
            df.to_csv(cache, index=False)
            print(f'{year}: ({_time.time()-t0:.0f}s)', end=' ')
            _time.sleep(5)          # be a good citizen between queries
        r = df.iloc[0].to_dict()
        r['year'] = year
        rows.append(r)
        print(f"points={int(r['n_points'] or 0):>7,}  aircraft={int(r['n_aircraft'] or 0):>4}  "
              f"days_with_data={int(r['n_days_seen'] or 0):>2}/7")

    out = pd.DataFrame(rows)
    out.to_csv(str(HERE / 'coverage_probe.csv'), index=False)
    print(f'\nwrote {HERE / "coverage_probe.csv"}')
    print('\nRead this before pulling: only use years where days_with_data is 7/7')
    print('and the aircraft count is in the same ballpark as recent years.')
    print('Earlier years are a coverage artefact, not a traffic trend.')


if __name__ == '__main__':
    main()
