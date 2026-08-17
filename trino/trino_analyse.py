#!/usr/bin/env python3
"""
STEP 3 of 3. Ten-year analysis of arrivals over Brockenhurst.

Answers four questions:
  1. Volume      - how many arrivals cross the village, year by year.
  2. Height      - how high they are, year by year.
  3. Track       - WHERE they cross, measured as lateral offset from the
                   runway-26 extended centreline.
  4. Change      - whether the track moved or narrowed, and when.

Question 3 is the interesting one. For every flight we compute how far north
or south of the approach centreline it passed. Two things then matter:
  * the MEDIAN offset, which says whether the path has moved sideways;
  * the SPREAD of offsets, which says whether traffic has been concentrated
    into a narrower corridor. Narrowing is what a "noise highway" looks like
    in the data, and it is the specific risk from satellite-based approaches.

A health warning that governs everything here: OpenSky's receiver coverage
grew hugely over the decade, so raw flight COUNTS from this source are not a
usable traffic trend. Use the CAA official movement figures for volume. What
OpenSky is good for is the shape of the approach: heights and lateral position,
which are far less sensitive to how many receivers were listening.

    python trino_analyse.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent

M_TO_FT = 3.280839895
BLAT, BLON = 50.8217, -1.5739
TLAT, TLON = 50.7793, -1.8226          # runway-26 threshold
APPROACH_TRACK_DEG = 255.0             # inbound track over the village
GEOID_FT = 155.0                       # WGS-84 ellipsoid to sea level, southern England


def to_local_xy(lat, lon):
    """Kilometres east/north of the runway-26 threshold."""
    x = (lon - TLON) * 111.320 * np.cos(np.radians(TLAT))
    y = (lat - TLAT) * 110.574
    return x, y


def along_across(lat, lon):
    """Distance along the approach centreline, and lateral offset from it.

    Positive lateral offset means north of the centreline.
    """
    x, y = to_local_xy(lat, lon)
    # Unit vector pointing outbound from the threshold along the approach
    # (aircraft inbound on 255 come FROM a bearing of 075).
    brg = np.radians(75.0)
    ux, uy = np.sin(brg), np.cos(brg)
    along = x * ux + y * uy                 # km from threshold
    across = -x * uy + y * ux               # km left/right of centreline
    return along, across


def main() -> None:
    df = pd.read_parquet(str(HERE / 'brockenhurst_gate_10yr.parquet'))
    df['dt'] = pd.to_datetime(df['time'], unit='s', utc=True)
    df['year'] = df['dt'].dt.year
    df['ym'] = df['dt'].dt.to_period('M').astype(str)
    df['baro_ft'] = df['baroaltitude'] * M_TO_FT
    df['geo_ft'] = df['geoaltitude'] * M_TO_FT
    df['geo_amsl_ft'] = df['geo_ft'] - GEOID_FT      # sea-level equivalent
    df['along_km'], df['across_km'] = along_across(df['lat'].values, df['lon'].values)

    # Keep flights that genuinely crossed near the village on the approach.
    d = df[(df['d_km'] < 4) & (df['baro_ft'].between(500, 9000))].copy()

    print('=' * 78)
    print('1. VOLUME  (OpenSky coverage grew over time: use CAA figures for the')
    print('   real traffic trend. This table shows what OpenSky SAW.)')
    print('=' * 78)
    v = d.groupby('year').agg(flights_seen=('icao24', 'size'),
                              distinct_aircraft=('icao24', 'nunique'))
    print(v.to_string())

    print()
    print('=' * 78)
    print('2. HEIGHT OVER THE VILLAGE, by year (feet)')
    print('=' * 78)
    h = d.groupby('year').agg(
        n=('baro_ft', 'size'),
        median_baro=('baro_ft', 'median'),
        p25=('baro_ft', lambda s: s.quantile(.25)),
        p75=('baro_ft', lambda s: s.quantile(.75)),
        median_geo_amsl=('geo_amsl_ft', 'median'),
    ).round(0)
    print(h.to_string())
    print()
    print('The last column is the GNSS height above sea level, an independent')
    print('check on the pressure-based figure. If the two track each other, both')
    print('methods are sound.')

    print()
    print('=' * 78)
    print('3. WHERE THEY CROSS: lateral offset from the approach centreline (km,')
    print('   positive = north of the line)')
    print('=' * 78)
    t = d.groupby('year').agg(
        n=('across_km', 'size'),
        median_offset=('across_km', 'median'),
        spread_iqr=('across_km', lambda s: s.quantile(.75) - s.quantile(.25)),
        p10=('across_km', lambda s: s.quantile(.10)),
        p90=('across_km', lambda s: s.quantile(.90)),
    ).round(2)
    t['corridor_width_km'] = (t['p90'] - t['p10']).round(2)
    print(t.to_string())
    print()
    print('median_offset moving  = the flight path shifted sideways.')
    print('corridor_width_km falling = traffic squeezed into a narrower corridor,')
    print('which is the "noise highway" concentration effect.')

    print()
    print('=' * 78)
    print('4. WHEN DID IT CHANGE? Monthly series, biggest shifts flagged')
    print('=' * 78)
    m = d.groupby('ym').agg(
        n=('across_km', 'size'),
        med_offset=('across_km', 'median'),
        width=('across_km', lambda s: s.quantile(.90) - s.quantile(.10)),
        med_height=('baro_ft', 'median'),
    )
    m = m[m['n'] >= 20]                       # ignore thin months
    for col in ('med_offset', 'width', 'med_height'):
        m[f'{col}_shift'] = m[col].diff()
    m.to_csv(str(HERE / 'monthly_series.csv'))
    print(f'{len(m)} usable months written to {HERE / "monthly_series.csv"}')
    print()
    for col, label, unit in (('med_offset', 'sideways move', 'km'),
                             ('width', 'corridor width change', 'km'),
                             ('med_height', 'height change', 'ft')):
        s = m[f'{col}_shift'].dropna()
        if s.empty:
            continue
        big = s.reindex(s.abs().sort_values(ascending=False).index).head(5)
        print(f'Largest month-on-month {label}:')
        for ym, val in big.items():
            print(f'   {ym}: {val:+.2f} {unit}   (now {m.loc[ym, col]:.2f})')
        print()

    d.to_parquet(str(HERE / 'brockenhurst_analysed.parquet'), index=False)
    print(f'wrote {HERE / "brockenhurst_analysed.parquet"}')
    print()
    print('Caveats to carry into anything published:')
    print(' * OpenSky counts reflect receiver coverage as well as traffic.')
    print(' * baroaltitude is pressure altitude vs 1013.25 and needs the same')
    print('   QNH correction we applied to the OPDI data before comparing with')
    print("   the airport's radar.")
    print(' * geoaltitude is WGS-84 ellipsoid height; 155 ft has been subtracted')
    print('   to approximate height above sea level.')


if __name__ == '__main__':
    main()
