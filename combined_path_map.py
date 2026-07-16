#!/usr/bin/env python3
"""
Combined rope map: arrivals and departures on one OpenStreetMap background,
in two colours. Blue = runway-26 large-jet arrivals (landing in over the
village). Orange = departures (taking off). Reuses the loaders from
path_map.py (arrivals) and dep_path_map.py (departures) so the geometry and
data are identical to the standalone maps.

    python combined_path_map.py  ->  outputs/sweep/brockenhurst_combined.png
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import contextily as cx
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

import config
import path_map as pm
import dep_path_map as dm

BLAT, BLON = config.BROCKENHURST
ALAT, ALON = config.EGHH
TLAT, TLON = config.RWY26_THRESHOLD

# union of the two standalone frames so both fans fit
LON0, LON1, LAT0, LAT1 = -2.02, -1.40, 50.66, 50.96
ARR = "#1560bd"   # arrivals: blue
DEP = "#e8720c"   # departures: orange


def build(out="outputs/sweep/brockenhurst_combined.png"):
    # ---- arrivals (large jets, runway 26) ----
    a, _ = pm.load()
    # ---- departures ----
    ev = dm.load()
    # like-for-like: keep only large-jet departures, matching the arrivals filter,
    # so we are not comparing big jets against all the light aircraft / helicopters.
    lj = pd.read_csv("outputs/sweep/dep_large_jet_ids.csv")["flight_id"].astype("uint64")
    ev = ev[ev["flight_id"].astype("uint64").isin(set(lj))]

    x0, y0 = pm.merc(LON0, LAT0); x1, y1 = pm.merc(LON1, LAT1)
    fig, ax = plt.subplots(figsize=(13, 13 * (y1 - y0) / (x1 - x0)))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)

    # departures first (many faint lines), arrivals on top
    n_dep = 0
    for fid, g in ev.groupby("flight_id"):
        if len(g) < 2:
            continue
        g = g.sort_values("d_ap")
        mx, my = pm.merc(g["longitude"].values, g["latitude"].values)
        ax.plot(mx, my, color=DEP, lw=0.9, alpha=0.04, solid_capstyle="round", zorder=3)
        n_dep += 1

    n_arr = 0
    for fid, g in a.groupby("flight_id"):
        g = g.sort_values("dist_thr_nm", ascending=False)
        if len(g) < 4:
            continue
        mx, my = pm.merc(g["longitude"].values, g["latitude"].values)
        sx, sy = pm.smooth(mx, my)
        ax.plot(sx, sy, color=ARR, lw=1.2, alpha=0.06, solid_capstyle="round", zorder=4)
        n_arr += 1

    # markers: airport + village
    for (lo, la, name, dx, dy) in [
        (ALON, ALAT, "Bournemouth Airport", 9, -16),
        (BLON, BLAT, "Brockenhurst", 9, 7)]:
        mx, my = pm.merc(lo, la)
        ax.scatter([mx], [my], s=95, color="#111", edgecolors="white",
                   linewidths=1.6, zorder=7)
        ax.annotate(name, (mx, my), xytext=(dx, dy), textcoords="offset points",
                    fontsize=11.5, fontweight="bold", color="#111", zorder=8, ha="left",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8))

    ax.set_xticks([]); ax.set_yticks([])
    try:
        cx.add_basemap(ax, source=cx.providers.CartoDB.Positron, zoom=11,
                       attribution=False, zorder=1)
    except Exception as e:
        print("basemap failed:", e)

    ax.set_title("Large-jet arrivals and departures over Brockenhurst, 2023 to 2025\n"
                 f"{n_arr:,} arrivals (blue) fan in and converge over the village; "
                 f"{n_dep:,} departures (orange) mostly climb out to the west",
                 fontsize=13, fontweight="bold", pad=12)
    ax.legend(handles=[
        Line2D([0], [0], color=ARR, lw=3, label="Arrivals (landing in over the village)"),
        Line2D([0], [0], color=DEP, lw=3, label="Departures (taking off)")],
        loc="lower left", fontsize=10.5, framealpha=0.93)
    fig.text(0.5, 0.006,
             "Each line is one flight through its own recorded GPS fixes, via OPDI / OpenSky. "
             "Large jets only, both directions, for a like-for-like comparison. Approximate between fixes.",
             ha="center", va="bottom", fontsize=9, color="#333")
    fig.tight_layout(rect=[0, 0.02, 1, 1])
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out} | arrivals={n_arr} departures={n_dep}")
    return out


if __name__ == "__main__":
    build()
