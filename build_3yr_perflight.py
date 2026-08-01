#!/usr/bin/env python3
"""Rebuild the full 3-year per-arrival table (with over-Brockenhurst ping,
gate height and runway direction) by streaming OPDI event windows: download a
window, keep only EGHH-arrival rows, delete the raw file, move on. Uses the
committed arrivals.csv as the arrival master so flight lists are not re-pulled.
Writes one perflight_<year>.csv per year."""
import sys; sys.path.insert(0, '.')
from datetime import date
import pandas as pd, numpy as np
from brockenhurst import opdi, approach
import config

TLAT, TLON = config.RWY26_THRESHOLD
def nm(la, lo):
    R = 3440.065
    dlat = np.radians(la - TLAT); dlon = np.radians(lo - TLON)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(TLAT))*np.cos(np.radians(la))*np.sin(dlon/2)**2
    return 2*R*np.arcsin(np.sqrt(a))

arr_all = pd.read_csv('outputs/sweep/arrivals.csv')
arr_all['id'] = arr_all['id'].astype('uint64')

for y in (2023, 2024, 2025):
    arr = arr_all[arr_all['year'] == y].copy()
    ids = set(arr['id'])
    parts = []
    for ws, we in opdi.event_windows(date(y, 1, 1), date(y+1, 1, 1)):
        try:
            ev = opdi.load_flight_events(ws, we, only_ids=ids, delete_after=True)
        except Exception as e:
            print(f'  skip {ws}: {e}', flush=True); continue
        parts.append(ev)
        print(f'  {y} window {ws} kept {len(ev)}', flush=True)
    cols = ['flight_id', 'type', 'event_time', 'longitude', 'latitude', 'altitude']
    events = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=cols)
    pf = approach.per_flight(arr, events)
    # runway direction: mean longitude of near-field low points (east of thr = over village)
    ev2 = events.copy()
    for c in ('latitude', 'longitude', 'altitude'):
        ev2[c] = pd.to_numeric(ev2[c], errors='coerce')
    ev2 = ev2.dropna(subset=['latitude', 'longitude', 'altitude'])
    low = ev2[ev2['altitude'].between(200, 5000)].copy()
    low['dthr'] = nm(low['latitude'].values, low['longitude'].values)
    near = low[low['dthr'] < 12]
    mlon = near.groupby('flight_id')['longitude'].mean()
    rwy26 = set(mlon[mlon > TLON].index)
    classified = set(mlon.index)
    pf['approached_over_village'] = pf['flight_id'].isin(rwy26)
    pf['runway_classified'] = pf['flight_id'].isin(classified)
    pf.to_csv(f'outputs/reverify_full/perflight_{y}.csv', index=False)
    print(f'YEAR {y}: arrivals={len(arr)} with_events={len(pf)} rwy26={len(rwy26)} classified={len(classified)}', flush=True)
print('DONE', flush=True)
