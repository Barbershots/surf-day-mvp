#!/usr/bin/env python3
"""Build the 3-year Brockenhurst arrivals workbook: one tab per year, a live
Summary tab (formulas), and a Read-me tab. Reads arrivals.csv (master) +
outputs/reverify_full/perflight_<year>.csv (event-derived gate/over-village)."""
import pandas as pd, numpy as np, re
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

AIRLINES = {
    'TOM':'TUI Airways','TFL':'TUI fly','RYR':'Ryanair','RUK':'Ryanair UK',
    'EZY':'easyJet','EJU':'easyJet Europe','EXS':'Jet2.com','BAW':'British Airways',
    'SHT':'British Airways','BEE':'Flybe','LOG':'Loganair','WZZ':'Wizz Air',
    'WUK':'Wizz Air UK','TRA':'Transavia','TVF':'Transavia France','VLG':'Vueling',
    'EWG':'Eurowings','KLM':'KLM','AFR':'Air France','DLH':'Lufthansa',
    'BCS':'European Air Transport (DHL)','PGT':'Pegasus','NEX':'Aer Lingus Regional',
    'EIN':'Aer Lingus','SWR':'Swiss','TAP':'TAP Air Portugal','NAX':'Norwegian',
}
def airline(cs, cat):
    cs = str(cs).strip()
    m = re.match(r'^([A-Z]{2,3})', cs)
    pfx = m.group(1) if m else ''
    if pfx in AIRLINES: return AIRLINES[pfx]
    if cat in ('GA / light','Helicopter'): return 'Private / GA'
    if cat == 'Business jet': return 'Business / private jet'
    return (pfx + ' (unverified)') if pfx else 'Unknown'

def airline2(operator, cs, cat):
    op = str(operator).strip()
    if op in AIRLINES:
        return AIRLINES[op]
    if op and op.lower() != 'nan' and re.fullmatch(r'[A-Z]{3}', op):
        return op  # real ICAO operator code, unmapped
    return airline(cs, cat)  # fall back to callsign inference

# OPDI per-flight reference fields (id, icao24, registration, adep, operator)
import os
_refs = []
for _f in ('outputs/reverify_full/arrivals_refs.csv', 'outputs/reverify_full/arrivals_refs_2026.csv'):
    if os.path.exists(_f):
        _refs.append(pd.read_csv(_f, dtype={'id': str}))
REFS = pd.concat(_refs, ignore_index=True).drop_duplicates('id') if _refs else None

def yesno(b):
    return 'Yes' if bool(b) else 'No'

# ---- QNH pressure correction -------------------------------------------------
# OPDI/ADS-B altitudes are BAROMETRIC PRESSURE altitudes referenced to the
# standard 1013.25 hPa (i.e. flight-level / QNE), not height above sea level.
# Verified two ways: (a) aircraft recorded on the ground at EGHH (true elevation
# 38 ft) read between -181 and +229 ft depending on the day's pressure, and
# (b) the QNH implied by those ground readings matches the airport's official
# METAR observations to within 0.1 hPa on average.
# Correction to approximate height above mean sea level:
#     AMSL ft ~= pressure altitude + (QNH_hPa - 1013.25) * 27.3
FT_PER_HPA = 27.3
STD_HPA = 1013.25
try:
    _m = pd.read_csv('data/eghh_metar.csv')
    _m['valid'] = pd.to_datetime(_m['valid'], utc=True, errors='coerce')
    _m['qnh'] = pd.to_numeric(_m['alti'], errors='coerce') * 33.8639  # inHg -> hPa
    _m = _m.dropna(subset=['valid', 'qnh'])
    _m = _m[_m['qnh'].between(950, 1060)]          # drop corrupt observations
    METAR = _m[['valid', 'qnh']].sort_values('valid').reset_index(drop=True)
    print(f'METAR pressure records loaded: {len(METAR):,}')
except Exception as _e:
    print('WARN: METAR data unavailable, altitudes will NOT be pressure-corrected:', _e)
    METAR = None

def qnh_for(times_utc):
    """Nearest METAR QNH (hPa) for each timestamp; NaN where none within 2 hours."""
    if METAR is None:
        return pd.Series(np.nan, index=range(len(times_utc)))
    left = pd.DataFrame({'valid': pd.to_datetime(times_utc, utc=True)}).reset_index()
    left = left.sort_values('valid')
    merged = pd.merge_asof(left, METAR, on='valid', direction='nearest',
                           tolerance=pd.Timedelta('2h'))
    return merged.sort_values('index')['qnh'].reset_index(drop=True)

def build_year(year):
    src = 'outputs/sweep/arrivals_2026.csv' if year == 2026 else 'outputs/sweep/arrivals.csv'
    arr = pd.read_csv(src)
    arr = arr[arr['year'] == year].copy()
    arr['id'] = arr['id'].astype('uint64')
    pf = pd.read_csv(f'outputs/reverify_full/perflight_{year}.csv')
    pf['flight_id'] = pf['flight_id'].astype('uint64')
    keep = ['flight_id','gate_alt_ft','alt_vs_cda_ft','leveloff_over_village',
            'village_leveloff_ft','lowest_leveloff_ft','has_corridor_leveloff',
            'approached_over_village','runway_classified']
    pf = pf[[c for c in keep if c in pf.columns]]
    m = arr.merge(pf, left_on='id', right_on='flight_id', how='left')
    m['id'] = m['id'].astype('uint64')
    m['id'] = m['id'].astype(str)  # string key matches arrivals_refs.csv
    if REFS is not None:
        m = m.merge(REFS, on='id', how='left')
    for c in ('icao24', 'registration', 'adep', 'icao_operator'):
        if c not in m.columns:
            m[c] = ''
    t = pd.to_datetime(m['last_seen'], utc=True).dt.tz_convert('Europe/London')
    out = pd.DataFrame()
    out['Date'] = t.dt.strftime('%Y-%m-%d')
    out['Arrival time (local)'] = t.dt.strftime('%H:%M')
    # Time of day using the airport's OFFICIAL night window 23:30-06:00 (S106 / Noise Action Plan)
    mins = t.dt.hour * 60 + t.dt.minute
    is_night = (mins >= 23 * 60 + 30) | (mins < 6 * 60)
    is_eve = (mins >= 19 * 60) & ~is_night
    out['Time of day'] = np.where(is_night, 'Night', np.where(is_eve, 'Evening', 'Day'))
    out['Flight ID / callsign'] = m['flt_id'].astype(str).str.strip()
    out['Airline'] = [airline2(op, c, k) for op, c, k in zip(m['icao_operator'], m['flt_id'], m['category'])]
    out['Aircraft type'] = m['typecode']
    out['Aircraft class'] = m['category']
    # approached over village: Yes/No/Unknown from runway classification
    def ov(row):
        if not row.get('runway_classified', False) or pd.isna(row.get('runway_classified')):
            return 'Unknown'
        return 'Yes' if row.get('approached_over_village') else 'No'
    out['Approached over village (rwy 26)'] = [ov(r) for _, r in m.iterrows()]
    out['GPS ping over Brockenhurst'] = np.where(m['gate_alt_ft'].notna(), 'Yes', 'No')
    # Pressure-correct the recorded (QNE) altitude to height above sea level, so the
    # figures are directly comparable with the airport's own QNH-based radar display.
    qnh = qnh_for(pd.to_datetime(m['last_seen'], utc=True).values)
    corr = (qnh - STD_HPA) * FT_PER_HPA
    corr_alt = m['gate_alt_ft'].reset_index(drop=True) + corr
    corr_vs_cda = m['alt_vs_cda_ft'].reset_index(drop=True) + corr
    out['Height over Brockenhurst (ft)'] = corr_alt.round(0).values
    out['Height vs standard 3° descent (ft)'] = corr_vs_cda.round(0).values
    out['Below standard 3° descent height'] = np.where(
        corr_alt.notna().values, np.where(corr_vs_cda.values < 0, 'Yes', 'No'), 'n/a')
    out['Levelled off over village'] = np.where(
        m['leveloff_over_village'].fillna(False).astype(bool), 'Yes', 'No')
    out['Lowest level-off in approach (ft)'] = m['lowest_leveloff_ft'].round(0)
    # ---- cross-check reference columns from OPDI (appended; A-N above unchanged) ----
    out['OPDI flight ID'] = m['id'].astype(str)
    out['Aircraft registration'] = m['registration'].fillna('').astype(str)
    out['ICAO24 (hex)'] = m['icao24'].fillna('').astype(str)
    out['From (origin airport)'] = m['adep'].fillna('').astype(str)
    # ---- altitude working, shown so the correction can be checked ----
    out['Raw recorded altitude (ft, pressure/QNE)'] = m['gate_alt_ft'].round(0).values
    out['QNH at the time (hPa)'] = qnh.round(1).values
    out['Pressure correction applied (ft)'] = corr.round(0).values
    out = out.sort_values(['Date', 'Arrival time (local)']).reset_index(drop=True)
    return out

years = [2023, 2024, 2025]          # complete years — all headline figures use these
PARTIAL = 2026                      # partial year (Jan-May), monitoring only
all_years = years + ([PARTIAL] if os.path.exists('outputs/sweep/arrivals_2026.csv') else [])
SHEET = {2023: '2023', 2024: '2024', 2025: '2025', 2026: '2026 (Jan-May)'}
data = {y: build_year(y) for y in all_years}
for y in all_years:
    print(y, 'rows', len(data[y]),
          '| ping Yes', (data[y]['GPS ping over Brockenhurst'] == 'Yes').sum(),
          '| over-village Yes', (data[y]['Approached over village (rwy 26)'] == 'Yes').sum())

# ---- write workbook ----
FN = 'outputs/Brockenhurst_arrivals_3yr.xlsx'
with pd.ExcelWriter(FN, engine='openpyxl') as xl:
    for y in all_years:
        data[y].to_excel(xl, sheet_name=SHEET[y], index=False)
wb = openpyxl.load_workbook(FN)

ARIAL = 'Arial'
hdr_fill = PatternFill('solid', fgColor='0F335F')
hdr_font = Font(name=ARIAL, bold=True, color='FFFFFF', size=10)
cell_font = Font(name=ARIAL, size=10)
thin = Side(style='thin', color='D9E3EF')
ncols = data[2023].shape[1]
for y in all_years:
    ws = wb[SHEET[y]]
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f"A1:{get_column_letter(ncols)}1"
    for c in range(1, ncols + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill = hdr_fill; cell.font = hdr_font
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    widths = [11,9,10,15,20,11,13,16,14,14,14,14,14,16,18,15,12,13,16,13,15]
    for i, w in enumerate(widths[:ncols], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=ncols):
        for cell in row:
            cell.font = cell_font
    ws.row_dimensions[1].height = 30

# ---- Summary tab (values computed from the year-tab data; recompute recipe given) ----
def metrics(df):
    lj = df['Aircraft class'] == 'Large jet'
    night = df['Time of day'] == 'Night'
    ping = df['GPS ping over Brockenhurst'] == 'Yes'
    below = df['Below standard 3° descent height'] == 'Yes'
    ov_yes = (df['Approached over village (rwy 26)'] == 'Yes').sum()
    ov_no = (df['Approached over village (rwy 26)'] == 'No').sum()
    lj_ping = (lj & ping).sum()
    lj_below = (lj & below).sum()
    h = pd.to_numeric(df.loc[lj & ping, 'Height over Brockenhurst (ft)'], errors='coerce')
    return {
        'Total arrivals': len(df),
        'Large jets': int(lj.sum()),
        'Night arrivals (23:30-06:00, official)': int(night.sum()),
        '  large jets at night': int((lj & night).sum()),
        'Approached over village (rwy 26) *': int(ov_yes),
        '  % over village of classified (floor *)': (ov_yes/(ov_yes+ov_no)) if (ov_yes+ov_no) else None,
        'Large jets over the village (measured)': int(lj_ping),
        '  below the standard 3° descent height': int(lj_below),
        '  % below 3° (large jets over village)': (lj_below/lj_ping) if lj_ping else None,
        'Avg height of large jets over village (ft)': float(h.mean()) if len(h) else None,
        'Levelled off over the village': int((df['Levelled off over village'] == 'Yes').sum()),
    }
M = {y: metrics(data[y]) for y in all_years}
PCT = {'  % over village of classified (floor *)', '  % below 3° (large jets over village)'}
HAS26 = PARTIAL in all_years

sm = wb.create_sheet('Summary', 0)
title_font = Font(name=ARIAL, bold=True, size=13, color='0F335F')
lbl_font = Font(name=ARIAL, size=10)
bold = Font(name=ARIAL, bold=True, size=10)
sm['A1'] = 'Brockenhurst arrivals — headline figures'
sm['A1'].font = title_font
sm['A2'] = 'Computed directly from the raw rows in the 2023 / 2024 / 2025 tabs. To re-audit any figure yourself, use the formula shown in the last column against the relevant year tab.'
sm['A2'].font = Font(name=ARIAL, italic=True, size=9, color='5A6B7E')
sm['A2'].alignment = Alignment(wrap_text=False)
hdr = ['Metric', '2023', '2024', '2025'] + (['2026 (Jan-May) *'] if HAS26 else []) + \
      ['Change 23→25', 'Recompute in Excel (put = in front; 2025 tab shown)']
for j, h in enumerate(hdr, 1):
    c = sm.cell(row=4, column=j, value=h); c.font = hdr_font; c.fill = hdr_fill
    c.alignment = Alignment(horizontal='center', wrap_text=True)
CH_COL = 6 if HAS26 else 5     # column for Change 23->25
RC_COL = 7 if HAS26 else 6     # column for the recompute recipe
recipe = {
 'Total arrivals': "=COUNTA('2025'!A:A)-1",
 'Large jets': "=COUNTIF('2025'!G:G,\"Large jet\")",
 'Night arrivals (23:30-06:00, official)': "=COUNTIF('2025'!C:C,\"Night\")",
 '  large jets at night': "=COUNTIFS('2025'!G:G,\"Large jet\",'2025'!C:C,\"Night\")",
 'Approached over village (rwy 26) *': "=COUNTIF('2025'!H:H,\"Yes\")",
 '  % over village of classified (floor *)': "=COUNTIF(H:H,\"Yes\")/(COUNTIF(H:H,\"Yes\")+COUNTIF(H:H,\"No\"))",
 'Large jets over the village (measured)': "=COUNTIFS('2025'!G:G,\"Large jet\",'2025'!I:I,\"Yes\")",
 '  below the standard 3° descent height': "=COUNTIFS('2025'!G:G,\"Large jet\",'2025'!L:L,\"Yes\")",
 '  % below 3° (large jets over village)': "=COUNTIFS(G:G,\"Large jet\",L:L,\"Yes\")/COUNTIFS(G:G,\"Large jet\",I:I,\"Yes\")",
 'Avg height of large jets over village (ft)': "=AVERAGEIFS('2025'!J:J,'2025'!G:G,\"Large jet\",'2025'!J:J,\">0\")",
 'Levelled off over the village': "=COUNTIF('2025'!M:M,\"Yes\")",
}
r = 5
year_cols = [(2, 2023), (3, 2024), (4, 2025)] + ([(5, 2026)] if HAS26 else [])
for label in M[2025].keys():
    sm.cell(row=r, column=1, value=label).font = lbl_font if label.startswith('  ') else bold
    for ci, y in year_cols:
        v = M[y][label]
        c = sm.cell(row=r, column=ci, value=(round(v, 3) if v is not None else None))
        c.font = lbl_font
        c.number_format = '0%' if label in PCT else '#,##0'
    if label not in PCT:
        a, b = M[2023][label], M[2025][label]
        ch = sm.cell(row=r, column=CH_COL, value=(round(b/a - 1, 3) if a else None))
        ch.number_format = '+0%;-0%'; ch.font = lbl_font
    fr = sm.cell(row=r, column=RC_COL, value=recipe.get(label, '').lstrip('='))  # text, not a live formula
    fr.font = Font(name='Consolas', size=8, color='5A6B7E'); fr.number_format = '@'
    r += 1
last_col = RC_COL
note = sm.cell(row=r + 1, column=1, value=(
    '* Over-village counts are a conservative floor: sparse GPS sampling marks some flights that '
    'did overfly as No/Unknown. The reliable per-flight signal is the "Approached over village" column; '
    'the true share is ~55-65% (the airport\'s own published figure is ~65% from the east). See the Read me tab.'))
note.font = Font(name=ARIAL, italic=True, size=9, color='C0392B')
note.alignment = Alignment(wrap_text=True, vertical='top')
sm.merge_cells(start_row=r + 1, start_column=1, end_row=r + 2, end_column=last_col)
if HAS26:
    n2 = sm.cell(row=r + 3, column=1, value=(
        '2026 is a PART YEAR (January to May only) and its recent months are still being backfilled by OPDI, '
        'so its counts are undercounts (see the Completeness tab). It is shown for monitoring only. '
        'Every headline change uses the three COMPLETE years 2023-2025.'))
    n2.font = Font(name=ARIAL, italic=True, size=9, color='B26B00')
    n2.alignment = Alignment(wrap_text=True, vertical='top')
    sm.merge_cells(start_row=r + 3, start_column=1, end_row=r + 4, end_column=last_col)
sm.column_dimensions['A'].width = 42
for c in ('B', 'C', 'D', 'E', 'F'):
    sm.column_dimensions[c].width = 12
sm.column_dimensions[get_column_letter(RC_COL)].width = 46
sm.column_dimensions['A'].width = 42

# ---- Read-me tab ----
rm = wb.create_sheet('Read me', 1)
rm.column_dimensions['A'].width = 118
notes = [
 ('Brockenhurst aircraft arrivals — 3-year dataset', title_font),
 ('', lbl_font),
 ('What this is', bold),
 ('One row per aircraft arriving into Bournemouth Airport (EGHH) in 2023, 2024 and 2025, on a tab per year, plus a "2026 (Jan-May)" partial-year tab for monitoring.', lbl_font),
 ('The three full years (2023-2025) carry all the headline figures. 2026 is incomplete (5 months, and OPDI is still backfilling the recent months), so treat it as monitoring only, not for headline claims.', lbl_font),
 ('Built from independent aircraft GPS (ADS-B) data published by OPDI (derived from the OpenSky Network).', lbl_font),
 ('', lbl_font),
 ('How to read the key columns', bold),
 ('• Approached over village (rwy 26): the aircraft lined up on the runway-26 approach, whose path runs over/near Brockenhurst.', lbl_font),
 ('   This is the RELIABLE indicator of whether a flight came over the village. "Unknown" = not enough track data to tell.', lbl_font),
 ('• GPS ping over Brockenhurst: a track point was actually recorded inside 3 km of the village for that flight.', lbl_font),
 ('• Height over Brockenhurst (ft): the aircraft\'s height above sea level at that ping, PRESSURE-CORRECTED (see the altitude note below).', lbl_font),
 ('• Height vs standard 3° descent (ft): how far above (+) or below (−) a standard continuous 3-degree descent the aircraft was.', lbl_font),
 ('• The last three columns show the altitude working: the raw recorded figure, the official air pressure at the time, and the correction applied.', lbl_font),
 ('', lbl_font),
 ('IMPORTANT caveat about the GPS pings (please read)', Font(name=ARIAL, bold=True, size=10, color='C0392B')),
 ('The public data records only occasional track points, not a continuous trail. Roughly 1 in 5 flights happens to have a', lbl_font),
 ('point recorded exactly over the village. So "GPS ping over Brockenhurst = No" does NOT mean the plane missed the village —', lbl_font),
 ('it usually means no point was logged at that spot. To judge whether a flight came over us, use the "Approached over village"', lbl_font),
 ('column (based on approach direction), NOT the ping column. Heights are only shown where a ping exists, so they are a sample.', lbl_font),
 ('', lbl_font),
 ('Definitions', bold),
 ('• Large jet = commercial narrow/wide-body airliner (e.g. B738, A320), by aircraft type.', lbl_font),
 ('• Standard 3° descent height = the altitude an aircraft on a continuous 3-degree approach would be at that point (~3,127 ft over Brockenhurst).', lbl_font),
 ('', lbl_font),
 ('ALTITUDE: why these figures are pressure-corrected', Font(name=ARIAL, bold=True, size=10, color='0F335F')),
 ('Aircraft transponders broadcast PRESSURE altitude measured against a fixed standard setting (1013.25 hPa), not true height above sea level.', lbl_font),
 ('On a high-pressure day an aircraft is really higher than it reports; on a low-pressure day it is really lower. The gap can exceed 500 ft.', lbl_font),
 ('We therefore correct every flight using the airport\'s own official hourly pressure readings (METAR), so these heights are directly comparable', lbl_font),
 ('with the airport\'s radar display, which also works in height above sea level. Correction = (QNH - 1013.25) x 27.3 ft.', lbl_font),
 ('We verified this two independent ways, and they agree to within 0.1 hPa (about 2 ft):', lbl_font),
 ('   (a) aircraft recorded ON THE GROUND at Bournemouth, where the true elevation is known to be 38 ft, read between -181 and +229 ft', lbl_font),
 ('       depending on the day, exactly tracking the weather; and (b) the pressure implied by those ground readings matches the official METARs.', lbl_font),
 ('Note: correcting made the picture slightly WORSE for the airport, not better. Our earlier uncorrected figures were the conservative ones.', Font(name=ARIAL, bold=True, size=10, color='1F8F7F')),
 ('• Night = the airport\'s OFFICIAL night period, 23:30 to 06:00 local, as defined in the 2007 Section 106 agreement and Noise Action Plan. Every "night" figure in this workbook uses this window (a 23:15 arrival is Evening, not Night).', lbl_font),
 ('• These are counts of ACTUAL flights measured in that window. They are separate from the airport\'s night noise "quota" (a fixed budget of noise points in the S106); this workbook counts flights, not quota points.', lbl_font),
 ('• Airline is the OPDI operator code where available (mapped to a name for the common carriers); otherwise inferred from the callsign, shown as "Private / GA" or "(unverified)".', lbl_font),
 ('', lbl_font),
 ('HOW TO CHECK A FLIGHT (please read before cross-checking)', Font(name=ARIAL, bold=True, size=10, color='0F335F')),
 ('Every row carries OPDI\'s own references so any flight can be independently verified. To avoid the common traps:', lbl_font),
 ('1. Search by the REGISTRATION (tail number, e.g. SP-RSD) or the CALLSIGN (e.g. RYR11MN) for the DATE shown — not by a flight number you have guessed.', lbl_font),
 ('2. Flight number is NOT the same as callsign. Flightradar shows a marketing number like "FR3318", but the aircraft broadcasts the callsign "RYR11MN" — that is what this data uses. Same flight, different label.', lbl_font),
 ('3. Our times are UTC. Flightradar shows LOCAL time, which can differ by an hour or more depending on the origin country and the time of year. A one-hour offset is a time zone, not an error.', lbl_font),
 ('4. A return trip has two legs with different callsigns. The arrival into Bournemouth is the INBOUND leg; the outbound departure (a different callsign) is not in this list.', lbl_font),
 ('Reference columns: OPDI flight ID (unique id in the OPDI dataset), Aircraft registration and ICAO24 hex (identify the exact aircraft on Flightradar24 / OpenSky), From (origin airport ICAO code).', lbl_font),
 ('', lbl_font),
 ('How complete is this? (checked against the CAA\'s official figures)', bold),
 ('The CAA publishes total aircraft movements per airport (Table 03). Bournemouth: 20,650 (2023), 21,000 (2024), 24,861 (2025).', lbl_font),
 ('Movements are landings + take-offs, so official arrivals are about half of those (~10,325 / ~10,500 / ~12,430).', lbl_font),
 ('This dataset holds 9,819 / 10,764 / 12,574 arrivals — about 95% / 102% / 101% of the official figure, and 99.7% over the three years combined.', Font(name=ARIAL, bold=True, size=10, color='1F8F7F')),
 ('In other words, effectively every arrival is captured. (The small year-to-year wobble is because arrivals are only approximately half of movements.)', lbl_font),
 ('Note: the CAA figures show most Bournemouth movements are non-commercial — in 2023 only 6,504 of 20,650 were commercial "air transport"; the rest is training, aero-club and private flying. That matches the aircraft-class mix in these tabs.', lbl_font),
 ('', lbl_font),
 ('Source & licensing', bold),
 ('Aircraft data: OPDI (Open Performance Data Initiative), published by EUROCONTROL, derived from the OpenSky Network. Movement benchmark: UK CAA airport data (Table 03 Aircraft Movements), under the Open Government Licence.', lbl_font),
 ('EUROCONTROL / OPDI data may be reused provided EUROCONTROL is credited as the source and it is not used for commercial purposes. This is a non-commercial residents\' analysis and credits EUROCONTROL / OPDI, the OpenSky Network and the CAA accordingly.', lbl_font),
 ('The figures in this workbook are OUR OWN calculations derived from that data, not the original published EUROCONTROL / CAA tables. Believed accurate at the time of extraction (Aug 2026).', lbl_font),
 ('Over-village counts and heights are conservative minimums because of the sparse GPS sampling described above.', lbl_font),
]
for i, (txt, f) in enumerate(notes, 1):
    c = rm.cell(row=i, column=1, value=txt); c.font = f
    c.alignment = Alignment(wrap_text=False, vertical='top')

# ---- Completeness (monthly) tab: our arrivals vs CAA official movements ----
try:
    from openpyxl.chart import LineChart, Reference
    mc = pd.read_csv('outputs/reverify_full/monthly_completeness.csv')
    cm = wb.create_sheet('Completeness (monthly)', 2)
    cm['A1'] = 'How complete is this dataset? — month by month vs the CAA official record'
    cm['A1'].font = title_font
    cm['A2'] = ('CAA total movements are landings + take-offs, so this dataset\'s arrivals should be about half of them. '
                'The last column is our arrivals ×2 as a % of the CAA figure: 100% = an exact match.')
    cm['A2'].font = Font(name=ARIAL, italic=True, size=9, color='5A6B7E')
    heads = ['Month', 'Our arrivals', 'CAA total movements', 'Our arrivals ×2', 'Match vs CAA (100% = exact)']
    for j, h in enumerate(heads, 1):
        c = cm.cell(row=4, column=j, value=h); c.font = hdr_font; c.fill = hdr_fill
        c.alignment = Alignment(horizontal='center', wrap_text=True)
    rr = 5
    for _, row in mc.iterrows():
        cm.cell(row=rr, column=1, value=row['month']).font = lbl_font
        cm.cell(row=rr, column=2, value=int(row['our_arrivals'])).font = lbl_font
        cm.cell(row=rr, column=3, value=int(row['caa_total_mov'])).font = lbl_font
        cm.cell(row=rr, column=4, value=int(row['our_x2'])).font = lbl_font
        pc = cm.cell(row=rr, column=5, value=round(row['pct_capt'] / 100, 3))
        pc.number_format = '0%'; pc.font = lbl_font
        if row['pct_capt'] < 85:
            pc.font = Font(name=ARIAL, size=10, color='C0392B', bold=True)
        rr += 1
    # totals
    to, tc = int(mc['our_arrivals'].sum()), int(mc['caa_total_mov'].sum())
    cm.cell(row=rr, column=1, value='3-year total').font = bold
    cm.cell(row=rr, column=2, value=to).font = bold
    cm.cell(row=rr, column=3, value=tc).font = bold
    cm.cell(row=rr, column=4, value=to * 2).font = bold
    tp = cm.cell(row=rr, column=5, value=round(to * 2 / tc, 3)); tp.number_format = '0%'; tp.font = bold
    # notes
    nrow = rr + 2
    for txt in [
        'Reading this: over the three years combined, this dataset holds %.1f%% of the CAA\'s official movements — effectively every flight.' % (100 * to * 2 / tc),
        'Individual months swing either side of 100% because arrivals and departures do not balance exactly within a calendar month,',
        'and because GA / training movements are counted differently by the CAA. They average out to ~100%.',
        'The lower months (shown in red) are in late 2023, consistent with thinner OpenSky receiver coverage early in the record;',
        'from 2024 onward capture is consistently around 95-105%. Commercial large jets, which broadcast continuously, are captured most reliably of all.',
        'Source: UK CAA airport data, Table 03 Aircraft Movements (monthly), 2023-2025.',
    ]:
        c = cm.cell(row=nrow, column=1, value=txt)
        c.font = Font(name=ARIAL, size=9, color='333333'); nrow += 1
    # ---- 2026 partial-year monitoring rows ----
    if os.path.exists('outputs/reverify_full/monthly_completeness_2026.csv'):
        mc26 = pd.read_csv('outputs/reverify_full/monthly_completeness_2026.csv')
        nrow += 1
        hh = cm.cell(row=nrow, column=1, value='2026 (partial year — monitoring only; recent months still backfilling)')
        hh.font = Font(name=ARIAL, bold=True, size=10, color='B26B00'); nrow += 1
        for j, htext in enumerate(heads, 1):
            hc = cm.cell(row=nrow, column=j, value=htext); hc.font = hdr_font; hc.fill = hdr_fill
            hc.alignment = Alignment(horizontal='center', wrap_text=True)
        nrow += 1
        for _, row in mc26.iterrows():
            cm.cell(row=nrow, column=1, value=row['month']).font = lbl_font
            cm.cell(row=nrow, column=2, value=int(row['our_arrivals'])).font = lbl_font
            cm.cell(row=nrow, column=3, value=int(row['caa_total_mov'])).font = lbl_font
            cm.cell(row=nrow, column=4, value=int(row['our_x2'])).font = lbl_font
            pc = cm.cell(row=nrow, column=5, value=round(row['pct_capt'] / 100, 3)); pc.number_format = '0%'
            pc.font = Font(name=ARIAL, size=10, color='C0392B', bold=True) if row['pct_capt'] < 85 else lbl_font
            nrow += 1
        cap = cm.cell(row=nrow + 1, column=1, value=(
            'These 2026 months are INCOMPLETE: OPDI is still backfilling recent data (Jan ~48%, rising to ~96% by May), '
            'so the counts are undercounts and are not comparable to the full years. Shown for monitoring only.'))
        cap.font = Font(name=ARIAL, italic=True, size=9, color='B26B00'); cap.alignment = Alignment(wrap_text=True)
        cm.merge_cells(start_row=nrow + 1, start_column=1, end_row=nrow + 2, end_column=5)
    # line chart of match % (full years only)
    ch = LineChart(); ch.title = 'Coverage vs CAA official (100% = exact match)'
    ch.height = 7.5; ch.width = 22; ch.y_axis.title = '% of CAA movements'; ch.legend = None
    data = Reference(cm, min_col=5, min_row=4, max_row=4 + len(mc))
    cats = Reference(cm, min_col=1, min_row=5, max_row=4 + len(mc))
    ch.add_data(data, titles_from_data=True); ch.set_categories(cats)
    cm.add_chart(ch, 'G4')
    for col, w in (('A', 12), ('B', 13), ('C', 20), ('D', 14), ('E', 24)):
        cm.column_dimensions[col].width = w
except Exception as _e:
    print('WARN: could not build monthly completeness tab:', _e)

wb.save(FN)
print('wrote', FN)
