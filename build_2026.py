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

fl = pd.concat([opdi.load_flight_list(2026, m) for m in range(1, 6)], ignore_index=True)
arr = opdi.arrivals(fl)                 # EGHH arrivals, classified
arr['id'] = arr['id'].astype('uint64')
arr['year'] = 2026
cols = ['id','flt_id','typecode','icao_aircraft_class','category','is_large_jet','time_window','last_seen','dof','year']
arr[cols].to_csv('outputs/sweep/arrivals_2026.csv', index=False)
arr[['id','icao24','registration','adep','model','icao_operator']].drop_duplicates('id') \
   .to_csv('outputs/reverify_full/arrivals_refs_2026.csv', index=False)
print('arrivals 2026 (Jan-May):', len(arr), flush=True)

ids = set(arr['id'])
parts = []
for ws, we in opdi.event_windows(date(2026, 1, 1), date(2026, 6, 1)):
    try:
        ev = opdi.load_flight_events(ws, we, only_ids=ids, delete_after=True)
    except Exception as e:
        print('  skip', ws, e, flush=True); continue
    parts.append(ev); print('  window', ws, 'kept', len(ev), flush=True)
ce = ['flight_id','type','event_time','longitude','latitude','altitude']
events = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=ce)
pf = approach.per_flight(arr, events)
ev2 = events.copy()
for c in ('latitude','longitude','altitude'):
    ev2[c] = pd.to_numeric(ev2[c], errors='coerce')
ev2 = ev2.dropna(subset=['latitude','longitude','altitude'])
low = ev2[ev2['altitude'].between(200, 5000)].copy()
low['dthr'] = nm(low['latitude'].values, low['longitude'].values)
near = low[low['dthr'] < 12]
mlon = near.groupby('flight_id')['longitude'].mean()
rwy26 = set(mlon[mlon > TLON].index); classified = set(mlon.index)
pf['approached_over_village'] = pf['flight_id'].isin(rwy26)
pf['runway_classified'] = pf['flight_id'].isin(classified)
pf.to_csv('outputs/reverify_full/perflight_2026.csv', index=False)
print('DONE perflight 2026:', len(pf), 'rwy26', len(rwy26), flush=True)
