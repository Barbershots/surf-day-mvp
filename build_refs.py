import sys; sys.path.insert(0, '.')
import pandas as pd, numpy as np
from brockenhurst import opdi
import config

def to_u64(s):
    a = s.to_numpy()
    return a.view('uint64') if a.dtype == np.int64 else a.astype('uint64')

rows = []
for y in (2023, 2024, 2025):
    for m in range(1, 13):
        try:
            fl = opdi.load_flight_list(y, m)
        except Exception as e:
            print('skip', y, m, e, flush=True); continue
        arr = fl[fl['ades'] == config.DEST_AIRPORT].copy()
        arr['id'] = to_u64(arr['id'])          # normalise per month BEFORE concat
        arr['id'] = arr['id'].astype(str)      # keep as string key (no float upcast, exact)
        rows.append(arr[['id', 'icao24', 'registration', 'adep', 'model', 'icao_operator']])
        print(y, m, len(arr), flush=True)
refs = pd.concat(rows, ignore_index=True).drop_duplicates('id')
refs.to_csv('outputs/reverify_full/arrivals_refs.csv', index=False)
print('SAVED', len(refs), flush=True)
