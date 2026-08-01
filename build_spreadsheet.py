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

def yesno(b):
    return 'Yes' if bool(b) else 'No'

def build_year(year):
    arr = pd.read_csv('outputs/sweep/arrivals.csv')
    arr = arr[arr['year'] == year].copy()
    arr['id'] = arr['id'].astype('uint64')
    pf = pd.read_csv(f'outputs/reverify_full/perflight_{year}.csv')
    pf['flight_id'] = pf['flight_id'].astype('uint64')
    keep = ['flight_id','gate_alt_ft','alt_vs_cda_ft','leveloff_over_village',
            'village_leveloff_ft','lowest_leveloff_ft','has_corridor_leveloff',
            'approached_over_village','runway_classified']
    pf = pf[[c for c in keep if c in pf.columns]]
    m = arr.merge(pf, left_on='id', right_on='flight_id', how='left')
    t = pd.to_datetime(m['last_seen'], utc=True).dt.tz_convert('Europe/London')
    out = pd.DataFrame()
    out['Date'] = t.dt.strftime('%Y-%m-%d')
    out['Arrival time (local)'] = t.dt.strftime('%H:%M')
    out['Time of day'] = m['time_window']
    out['Flight ID / callsign'] = m['flt_id'].astype(str).str.strip()
    out['Airline (inferred)'] = [airline(c, k) for c, k in zip(m['flt_id'], m['category'])]
    out['Aircraft type'] = m['typecode']
    out['Aircraft class'] = m['category']
    # approached over village: Yes/No/Unknown from runway classification
    def ov(row):
        if not row.get('runway_classified', False) or pd.isna(row.get('runway_classified')):
            return 'Unknown'
        return 'Yes' if row.get('approached_over_village') else 'No'
    out['Approached over village (rwy 26)'] = [ov(r) for _, r in m.iterrows()]
    out['GPS ping over Brockenhurst'] = np.where(m['gate_alt_ft'].notna(), 'Yes', 'No')
    out['Height over Brockenhurst (ft)'] = m['gate_alt_ft'].round(0)
    out['Height vs standard 3° descent (ft)'] = m['alt_vs_cda_ft'].round(0)
    out['Below standard 3° descent height'] = np.where(
        m['gate_alt_ft'].notna(), np.where(m['alt_vs_cda_ft'] < 0, 'Yes', 'No'), 'n/a')
    out['Levelled off over village'] = np.where(
        m['leveloff_over_village'].fillna(False).astype(bool), 'Yes', 'No')
    out['Lowest level-off in approach (ft)'] = m['lowest_leveloff_ft'].round(0)
    out = out.sort_values(['Date', 'Arrival time (local)']).reset_index(drop=True)
    return out

years = [2023, 2024, 2025]
data = {y: build_year(y) for y in years}
for y in years:
    print(y, 'rows', len(data[y]),
          '| ping Yes', (data[y]['GPS ping over Brockenhurst'] == 'Yes').sum(),
          '| over-village Yes', (data[y]['Approached over village (rwy 26)'] == 'Yes').sum())

# ---- write workbook ----
FN = 'outputs/Brockenhurst_arrivals_3yr.xlsx'
with pd.ExcelWriter(FN, engine='openpyxl') as xl:
    for y in years:
        data[y].to_excel(xl, sheet_name=str(y), index=False)
wb = openpyxl.load_workbook(FN)

ARIAL = 'Arial'
hdr_fill = PatternFill('solid', fgColor='0F335F')
hdr_font = Font(name=ARIAL, bold=True, color='FFFFFF', size=10)
cell_font = Font(name=ARIAL, size=10)
thin = Side(style='thin', color='D9E3EF')
ncols = data[2023].shape[1]
for y in years:
    ws = wb[str(y)]
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f"A1:{get_column_letter(ncols)}1"
    for c in range(1, ncols + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill = hdr_fill; cell.font = hdr_font
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    widths = [11,9,10,15,20,11,13,16,14,14,14,14,14,16]
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
        'Night arrivals (23:00-06:00)': int(night.sum()),
        '  large jets at night': int((lj & night).sum()),
        'Approached over village (rwy 26) *': int(ov_yes),
        '  % over village of classified (floor *)': (ov_yes/(ov_yes+ov_no)) if (ov_yes+ov_no) else None,
        'Large jets over the village (measured)': int(lj_ping),
        '  below the standard 3° descent height': int(lj_below),
        '  % below 3° (large jets over village)': (lj_below/lj_ping) if lj_ping else None,
        'Avg height of large jets over village (ft)': float(h.mean()) if len(h) else None,
        'Levelled off over the village': int((df['Levelled off over village'] == 'Yes').sum()),
    }
M = {y: metrics(data[y]) for y in years}
PCT = {'  % over village of classified (floor *)', '  % below 3° (large jets over village)'}

sm = wb.create_sheet('Summary', 0)
title_font = Font(name=ARIAL, bold=True, size=13, color='0F335F')
lbl_font = Font(name=ARIAL, size=10)
bold = Font(name=ARIAL, bold=True, size=10)
sm['A1'] = 'Brockenhurst arrivals — headline figures'
sm['A1'].font = title_font
sm['A2'] = 'Computed directly from the raw rows in the 2023 / 2024 / 2025 tabs. To re-audit any figure yourself, use the formula shown in the last column against the relevant year tab.'
sm['A2'].font = Font(name=ARIAL, italic=True, size=9, color='5A6B7E')
sm['A2'].alignment = Alignment(wrap_text=False)
hdr = ['Metric', '2023', '2024', '2025', 'Change 23→25', 'Recompute in Excel (put = in front; 2025 tab shown)']
for j, h in enumerate(hdr, 1):
    c = sm.cell(row=4, column=j, value=h); c.font = hdr_font; c.fill = hdr_fill
    c.alignment = Alignment(horizontal='center', wrap_text=True)
recipe = {
 'Total arrivals': "=COUNTA('2025'!A:A)-1",
 'Large jets': "=COUNTIF('2025'!G:G,\"Large jet\")",
 'Night arrivals (23:00-06:00)': "=COUNTIF('2025'!C:C,\"Night\")",
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
for label in M[2025].keys():
    sm.cell(row=r, column=1, value=label).font = lbl_font if label.startswith('  ') else bold
    for ci, y in ((2, 2023), (3, 2024), (4, 2025)):
        v = M[y][label]
        c = sm.cell(row=r, column=ci, value=(round(v, 3) if v is not None else None))
        c.font = lbl_font
        c.number_format = '0%' if label in PCT else '#,##0'
    if label not in PCT:
        a, b = M[2023][label], M[2025][label]
        ch = sm.cell(row=r, column=5, value=(round(b/a - 1, 3) if a else None))
        ch.number_format = '+0%;-0%'; ch.font = lbl_font
    fr = sm.cell(row=r, column=6, value=recipe.get(label, '').lstrip('='))  # text, not a live formula
    fr.font = Font(name='Consolas', size=8, color='5A6B7E'); fr.number_format = '@'
    r += 1
note = sm.cell(row=r + 1, column=1, value=(
    '* Over-village counts are a conservative floor: sparse GPS sampling marks some flights that '
    'did overfly as No/Unknown. The reliable per-flight signal is the "Approached over village" column; '
    'the true share is ~55-65% (the airport\'s own published figure is ~65% from the east). See the Read me tab.'))
note.font = Font(name=ARIAL, italic=True, size=9, color='C0392B')
note.alignment = Alignment(wrap_text=True, vertical='top')
sm.merge_cells(start_row=r + 1, start_column=1, end_row=r + 2, end_column=6)
sm.column_dimensions['A'].width = 42
for c in ('B', 'C', 'D', 'E'):
    sm.column_dimensions[c].width = 12
sm.column_dimensions['F'].width = 46

# ---- Read-me tab ----
rm = wb.create_sheet('Read me', 1)
rm.column_dimensions['A'].width = 118
notes = [
 ('Brockenhurst aircraft arrivals — 3-year dataset', title_font),
 ('', lbl_font),
 ('What this is', bold),
 ('One row per aircraft arriving into Bournemouth Airport (EGHH) in 2023, 2024 and 2025, on a tab per year.', lbl_font),
 ('Built from independent aircraft GPS (ADS-B) data published by OPDI (derived from the OpenSky Network).', lbl_font),
 ('', lbl_font),
 ('How to read the key columns', bold),
 ('• Approached over village (rwy 26): the aircraft lined up on the runway-26 approach, whose path runs over/near Brockenhurst.', lbl_font),
 ('   This is the RELIABLE indicator of whether a flight came over the village. "Unknown" = not enough track data to tell.', lbl_font),
 ('• GPS ping over Brockenhurst: a track point was actually recorded inside 3 km of the village for that flight.', lbl_font),
 ('• Height over Brockenhurst (ft): the aircraft\'s altitude at that ping.', lbl_font),
 ('• Height vs standard 3° descent (ft): how far above (+) or below (−) a standard continuous 3-degree descent the aircraft was.', lbl_font),
 ('', lbl_font),
 ('IMPORTANT caveat about the GPS pings (please read)', Font(name=ARIAL, bold=True, size=10, color='C0392B')),
 ('The public data records only occasional track points, not a continuous trail. Roughly 1 in 5 flights happens to have a', lbl_font),
 ('point recorded exactly over the village. So "GPS ping over Brockenhurst = No" does NOT mean the plane missed the village —', lbl_font),
 ('it usually means no point was logged at that spot. To judge whether a flight came over us, use the "Approached over village"', lbl_font),
 ('column (based on approach direction), NOT the ping column. Heights are only shown where a ping exists, so they are a sample.', lbl_font),
 ('', lbl_font),
 ('Definitions', bold),
 ('• Large jet = commercial narrow/wide-body airliner (e.g. B738, A320), by aircraft type.', lbl_font),
 ('• Standard 3° descent height = the altitude an aircraft on a continuous 3-degree approach would be at that point (~3,100 ft over Brockenhurst).', lbl_font),
 ('• Night = arrival between 23:00 and 06:00 local. (The airport\'s planning night is 23:30–06:00; both are shown in our analysis.)', lbl_font),
 ('• Airline is inferred from the callsign prefix; "(unverified)" or "Private / GA" where it could not be matched confidently.', lbl_font),
 ('', lbl_font),
 ('Source & status', bold),
 ('Aircraft data via OPDI / OpenSky. Figures are our own calculations and are believed accurate at the time of extraction (Aug 2026).', lbl_font),
 ('Counts of flights "over the village" and heights are conservative minimums because of the sparse sampling described above.', lbl_font),
]
for i, (txt, f) in enumerate(notes, 1):
    c = rm.cell(row=i, column=1, value=txt); c.font = f
    c.alignment = Alignment(wrap_text=False, vertical='top')

wb.save(FN)
print('wrote', FN)
