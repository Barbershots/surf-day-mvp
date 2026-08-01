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

# ---- Summary tab (live formulas so the group can audit the headline numbers) ----
sm = wb.create_sheet('Summary', 0)
title_font = Font(name=ARIAL, bold=True, size=13, color='0F335F')
lbl_font = Font(name=ARIAL, size=10)
bold = Font(name=ARIAL, bold=True, size=10)
sm['A1'] = 'Brockenhurst arrivals — headline figures (computed live from the year tabs)'
sm['A1'].font = title_font
sm['A2'] = 'Every number below is a formula reading the raw rows in the 2023/2024/2025 tabs. Change or filter the data and these update.'
sm['A2'].font = Font(name=ARIAL, italic=True, size=9, color='5A6B7E')
hdr = ['Metric', '2023', '2024', '2025', 'Change 23→25']
for j, h in enumerate(hdr, 1):
    c = sm.cell(row=4, column=j, value=h); c.font = hdr_font; c.fill = hdr_fill
    c.alignment = Alignment(horizontal='center')
cols = {2023: 'B', 2024: 'C', 2025: 'D'}
# (label, formula-template, number-format)  {s} = sheet name
rows = [
 ('Total arrivals',            "=COUNTA('{s}'!A:A)-1", '#,##0'),
 ('Large jets',                "=COUNTIF('{s}'!G:G,\"Large jet\")", '#,##0'),
 ('Approached over village (rwy 26)', "=COUNTIF('{s}'!H:H,\"Yes\")", '#,##0'),
 ('  classified by runway',    "=COUNTIF('{s}'!H:H,\"Yes\")+COUNTIF('{s}'!H:H,\"No\")", '#,##0'),
 ('  % over village (of classified)', "=IFERROR(COUNTIF('{s}'!H:H,\"Yes\")/(COUNTIF('{s}'!H:H,\"Yes\")+COUNTIF('{s}'!H:H,\"No\")),\"\")", '0%'),
 ('With a GPS ping over Brockenhurst', "=COUNTIF('{s}'!I:I,\"Yes\")", '#,##0'),
 ('  below the standard 3° descent height', "=COUNTIF('{s}'!L:L,\"Yes\")", '#,##0'),
 ('  % below 3° (of those pinged)', "=IFERROR(COUNTIF('{s}'!L:L,\"Yes\")/COUNTIF('{s}'!I:I,\"Yes\"),\"\")", '0%'),
 ('Avg height over Brockenhurst (ft)', "=IFERROR(AVERAGEIF('{s}'!J:J,\">0\"),\"\")", '#,##0'),
 ('Levelled off over the village',  "=COUNTIF('{s}'!M:M,\"Yes\")", '#,##0'),
 ('Night arrivals (23:00–06:00)',   "=COUNTIF('{s}'!C:C,\"Night\")", '#,##0'),
]
r = 5
for label, tmpl, fmt in rows:
    sm.cell(row=r, column=1, value=label).font = bold if not label.startswith('  ') else lbl_font
    for y, col in cols.items():
        c = sm.cell(row=r, column={2023:2,2024:3,2025:4}[y], value=tmpl.format(s=y))
        c.font = lbl_font; c.number_format = fmt
    # change 23->25
    if fmt == '#,##0':
        ch = sm.cell(row=r, column=5, value=f'=IFERROR(D{r}/B{r}-1,"")'); ch.number_format = '+0%;-0%'
        ch.font = lbl_font
    r += 1
sm.column_dimensions['A'].width = 34
for col in ('B', 'C', 'D', 'E'):
    sm.column_dimensions[col].width = 13

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
