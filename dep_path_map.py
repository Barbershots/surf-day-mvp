#!/usr/bin/env python3
"""
Departure rope map: every Bournemouth departure over the busiest month of each
of three years (July 2023, 2024, 2025), drawn as a line through its own recorded
GPS fixes, on an OpenStreetMap background. Shows the easterly (runway-08)
climb-out fanning north-east straight over Brockenhurst, alongside the westerly
(runway-26) departures heading the other way.

Points are ordered along each track by distance from the airport (departures
climb monotonically outbound), so a turn is drawn as a few straight segments.

    python dep_path_map.py  ->  outputs/sweep/brockenhurst_departures.png
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
from brockenhurst import geometry as geo

BLAT, BLON = config.BROCKENHURST
ALAT, ALON = config.EGHH
R = 6378137.0
LON0, LON1, LAT0, LAT1 = -2.02, -1.36, 50.66, 50.96
BLUE = "#1f5fb0"


def merc(lon, lat):
    return (R * np.radians(np.asarray(lon)),
            R * np.log(np.tan(np.pi / 4 + np.radians(np.asarray(lat)) / 2)))


def load():
    import glob
    ev = pd.concat([pd.read_parquet(f) for f in glob.glob("data/eghh_dep_events_*.parquet")],
                   ignore_index=True)
    ev = ev.dropna(subset=["latitude", "longitude", "altitude"])
    for c in ("latitude", "longitude", "altitude"):
        ev[c] = pd.to_numeric(ev[c], errors="coerce")
    ev = ev.dropna(subset=["latitude", "longitude", "altitude"])
    # keep the near-airport departure fan (drop distant cruise fixes)
    ev["d_ap"] = geo.haversine_km(ev["latitude"], ev["longitude"], ALAT, ALON)
    ev = ev[(ev["d_ap"] < 40) & (ev["altitude"] < 12000)]
    ev = ev[(ev["longitude"].between(LON0, LON1)) & (ev["latitude"].between(LAT0, LAT1))]
    return ev


def build(out="outputs/sweep/brockenhurst_departures.png"):
    ev = load()
    x0, y0 = merc(LON0, LAT0); x1, y1 = merc(LON1, LAT1)
    fig, ax = plt.subplots(figsize=(12, 10 * (y1 - y0) / (x1 - x0)))
    ndrawn = 0
    for fid, g in ev.groupby("flight_id"):
        if len(g) < 2:
            continue
        g = g.sort_values("d_ap")               # order outbound
        mx, my = merc(g["longitude"].values, g["latitude"].values)
        ax.plot(mx, my, color=BLUE, lw=0.5, alpha=0.015, solid_capstyle="round", zorder=3)
        ndrawn += 1
    # markers
    for (lo, la, name, dx, dy, ha) in [
        (ALON, ALAT, "Bournemouth Airport", 8, -16, "left"),
        (BLON, BLAT, "BROCKENHURST", 8, 8, "left")]:
        mx, my = merc(lo, la)
        ax.scatter([mx], [my], s=90, color="#111", edgecolors="white", linewidths=1.6, zorder=6)
        ax.annotate(name, (mx, my), xytext=(dx, dy), textcoords="offset points",
                    fontsize=12, fontweight="bold", color="#111", zorder=7,
                    path_effects=[], ha=ha,
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.75))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    ax.set_xticks([]); ax.set_yticks([])
    try:
        cx.add_basemap(ax, source=cx.providers.CartoDB.Positron, zoom=11, attribution_size=6)
    except Exception as e:
        print("basemap failed:", e)
    ax.set_title("Every Bournemouth departure fans out over Brockenhurst on easterly ops\n"
                 f"2023 to 2025 ({ndrawn:,} departures) - their own GPS tracks",
                 fontsize=14, fontweight="bold", pad=12)
    ax.legend([Line2D([0], [0], color=BLUE, lw=3)],
              ["one departure's path"], loc="lower left", fontsize=10, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out, "| departures drawn:", ndrawn)
    return out


if __name__ == "__main__":
    build()
