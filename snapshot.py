#!/usr/bin/env python3
"""
Automated 24-hour snapshot for any date: every large-jet arrival over Brockenhurst
that day, on a time-of-day vs height chart, plus a table. For validating against
the airport's WebTrak record day by day.

    python snapshot.py --date 2025-05-25

Works for any date in our dataset (2023 to early 2026). It cannot cover last night,
because our source (OPDI) is published with a lag; for very recent days that is
FlightRadar24 / WebTrak territory.
"""
from __future__ import annotations

import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROPER, FLOOR = 3116, 2000
RED, GOLD, BLUE, INK = "#c0392b", "#e8a020", "#2c6fbb", "#222"
NAMES = {"RYR": "Ryanair", "EXS": "Jet2", "TOM": "TUI", "EZY": "easyJet", "TUI": "TUI fly",
         "WZZ": "Wizz Air", "EIN": "Aer Lingus", "VIR": "Virgin", "LAV": "AlbaStar",
         "BRO": "2Excel", "RUK": "Ryanair UK", "EJU": "easyJet", "URO": "European Cargo"}


def col(a):
    return RED if a < FLOOR else GOLD if a < PROPER else BLUE


def build(date_str):
    day = pd.to_datetime(date_str).date()
    arr = pd.read_csv("outputs/sweep/arrivals.csv")
    arr["t"] = pd.to_datetime(arr["last_seen"], errors="coerce").dt.tz_localize("UTC").dt.tz_convert("Europe/London")
    arr = arr[arr["t"].dt.date == day]
    n_all = len(arr); n_lj = int((arr["category"] == "Large jet").sum())

    pf = pd.read_csv("outputs/sweep/per_flight.csv")
    pf["t"] = pd.to_datetime(pf["last_seen"], errors="coerce").dt.tz_localize("UTC").dt.tz_convert("Europe/London")
    d = pf[(pf["t"].dt.date == day) & (pf["category"] == "Large jet") & (pf["gate_alt_ft"].notna())].copy()
    d["hr"] = d["t"].dt.hour + d["t"].dt.minute / 60
    d["airline"] = d["flt_id"].astype(str).str[:3].map(NAMES).fillna(d["flt_id"].astype(str).str[:3])
    d = d.sort_values("hr")

    fig, ax = plt.subplots(figsize=(13, 7))
    ax.axvspan(0, 6.5, color="#1b2a4a", alpha=0.06, zorder=0)
    ax.axvspan(21.5, 24, color="#1b2a4a", alpha=0.06, zorder=0)
    ax.axhline(PROPER, color=GOLD, lw=1.8, ls="--", zorder=2, label="quiet 3-degree descent (3,116 ft)")
    ax.axhline(FLOOR, color=RED, lw=1.6, ls=":", zorder=2, label="2,000 ft floor")
    for _, r in d.iterrows():
        ax.scatter(r["hr"], r["gate_alt_ft"], s=90, color=col(r["gate_alt_ft"]),
                   edgecolors="white", linewidths=0.8, zorder=4)
        ax.annotate(f"{str(r['flt_id']).strip()}", (r["hr"], r["gate_alt_ft"]),
                    xytext=(0, 9), textcoords="offset points", ha="center", fontsize=7.5, color=INK)
    ax.set_xlim(0, 24); ax.set_ylim(0, 5200)
    ax.set_xticks(range(0, 25, 2)); ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 25, 2)], fontsize=8.5)
    ax.set_xlabel("time of day (local)", fontsize=10)
    ax.set_ylabel("height over Brockenhurst (ft)", fontsize=10)
    ax.grid(alpha=0.2, zorder=0)
    ax.text(3.25, 4950, "night", ha="center", fontsize=9, color="#33415c", style="italic")
    ax.text(22.75, 4950, "night", ha="center", fontsize=9, color="#33415c", style="italic")
    below = int((d["gate_alt_ft"] < PROPER).sum())
    ax.set_title(f"Brockenhurst arrivals snapshot, {day:%A %d %B %Y}\n"
                 f"{n_all} arrivals that day ({n_lj} large jets); {len(d)} large jets pinned over the village, "
                 f"{below} below the quiet line",
                 fontsize=13, fontweight="bold")
    ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
    fig.text(0.5, 0.005,
             "Each dot is a large jet with a height fix directly over the village (about 1 in 5 of the day's arrivals, so this is a floor). "
             "Cross-check against the airport's WebTrak for the same day. Via OPDI / OpenSky.",
             ha="center", fontsize=8.5, color="#555")
    out_png = f"outputs/sweep/snapshot_{day:%Y%m%d}.png"
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)

    # table
    tbl = d[["t", "flt_id", "airline", "typecode", "gate_alt_ft", "time_window"]].copy()
    tbl["time"] = tbl["t"].dt.strftime("%H:%M")
    tbl["height_ft"] = tbl["gate_alt_ft"].round().astype(int)
    tbl = tbl[["time", "flt_id", "airline", "typecode", "height_ft", "time_window"]].rename(
        columns={"flt_id": "callsign", "typecode": "type", "time_window": "period"})
    out_csv = f"outputs/sweep/snapshot_{day:%Y%m%d}.csv"
    tbl.to_csv(out_csv, index=False)
    print("wrote", out_png, "and", out_csv)
    print(tbl.to_string(index=False))
    return out_png


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    build(ap.parse_args().date)
