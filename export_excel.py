#!/usr/bin/env python3
"""
Export the facts-only flights (those with a directly measured height over
Brockenhurst) to an Excel workbook with one clean, simple table per sheet:

    Date | Time (local) | Flight | Aircraft type | Height over Brockenhurst (ft)
    ... plus a few helpful extra columns (period, below-minimum flags).

    python export_excel.py   ->  outputs/brockenhurst_measured_flights.xlsx
"""
from __future__ import annotations

import pandas as pd
from openpyxl.styles import Font

from brockenhurst import classify

PROPER, FLOOR = 3116, 2000
OUT = "outputs/brockenhurst_measured_flights.xlsx"


def table(df: pd.DataFrame) -> pd.DataFrame:
    lt = pd.to_datetime(df["last_seen"], utc=True).dt.tz_convert(classify.LONDON)
    h = df["gate_alt_ft"].round().astype(int)
    out = pd.DataFrame({
        "Date": lt.dt.strftime("%Y-%m-%d"),
        "Time (local)": lt.dt.strftime("%H:%M"),
        "Flight": df["flt_id"].fillna("(unknown)").astype(str).str.strip(),
        "Aircraft type": df["typecode"].fillna("(unknown)"),
        "Height over Brockenhurst (ft)": h,
        "Aircraft category": df["category"],
        "Period": df["time_window"],
        "Below 2,000 ft minimum": (h < FLOOR).map({True: "YES", False: ""}),
        "Ft below quiet-descent height": (PROPER - h),
        "Day of week": lt.dt.strftime("%a"),
    })
    return out.sort_values(["Date", "Time (local)"]).reset_index(drop=True)


def main():
    pf = pd.read_csv("outputs/sweep/per_flight.csv")
    pf = pf[pf["year"].isin([2023, 2024, 2025])]
    g = pf[pf["gate_alt_ft"].notna()].copy()
    lj = g[g["category"] == "Large jet"]
    ljn = lj[lj["time_window"] == "Night"]

    sheets = {
        "Large jets - night": table(ljn),
        "Large jets - all": table(lj),
        "All aircraft - measured": table(g),
    }

    with pd.ExcelWriter(OUT, engine="openpyxl") as xw:
        for name, t in sheets.items():
            t.to_excel(xw, sheet_name=name, index=False)
            ws = xw.sheets[name]
            # Freeze header, autofilter, and set sensible column widths.
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            widths = [12, 12, 12, 13, 16, 16, 10, 18, 16, 11]
            for i, w in enumerate(widths, start=1):
                ws.column_dimensions[chr(64 + i)].width = w
            for cell in ws[1]:
                cell.font = Font(bold=True)

    print(f"wrote {OUT}")
    for name, t in sheets.items():
        print(f"  '{name}': {len(t)} flights")


if __name__ == "__main__":
    main()
