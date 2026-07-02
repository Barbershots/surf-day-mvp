#!/usr/bin/env python3
"""
How large airliners join the final approach over Brockenhurst: straight in from
the east over the village, vs turning in from the south-east (the Lymington /
Sway side). Runway-26 (Brockenhurst-direction) arrivals only, on an
OpenStreetMap background.

Each dot is ONE flight, placed where it was ~9 NM out (its own GPS). BLUE =
straight in over the village; ORANGE = came in from the south-east and turned
onto final near the village. Grey = all the on-final positions (the shared
funnel). Split is stable across 2023-2025 (~80% straight-in / ~20% from the SE),
so this pools all three years.

    python full_track_map.py  ->  outputs/sweep/brockenhurst_join_direction.png
"""
from __future__ import annotations

import glob

import contextily as cx
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

import config
from brockenhurst import approach

BLAT, BLON = config.BROCKENHURST
TLAT, TLON = config.RWY26_THRESHOLD
R = 6378137.0
LON0, LON1, LAT0, LAT1 = -1.95, -1.42, 50.71, 50.87
BLUE, ORANGE = "#2c6fbb", "#e8720c"
SE_CUT = 88.0   # bearing (from threshold) above which the join is south of the centreline


def merc(lon, lat):
    return R * np.radians(lon), R * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))


def load():
    ev = pd.concat([pd.read_parquet(f) for f in glob.glob("data/eghh_events_*.parquet")],
                   ignore_index=True)
    ev["flight_id"] = ev["flight_id"].astype("uint64")
    arr = pd.read_csv("outputs/sweep/arrivals.csv"); arr["flight_id"] = arr["id"].astype("uint64")
    arr["year"] = pd.to_datetime(arr["dof"]).dt.year
    m = ev.merge(arr[["flight_id", "category", "year"]], on="flight_id", how="left")
    a = approach.annotate(m)
    a = a[a["category"] == "Large jet"]
    # keep only runway-26 (Brockenhurst-side) arrivals: low approach points sit
    # EAST of the threshold. Excludes runway-08 traffic that comes from the west.
    low = a[a["altitude"].between(200, 5000) & (a["dist_thr_nm"] < 12)]
    side = low.groupby("flight_id")["longitude"].mean()
    rwy26 = set(side[side > TLON].index)
    a = a[a["flight_id"].isin(rwy26)]
    # bearing from threshold to each point
    la1 = np.radians(TLAT); la2 = np.radians(a["latitude"].values)
    dlon = np.radians(a["longitude"].values - TLON)
    yb = np.sin(dlon) * np.cos(la2)
    xb = np.cos(la1) * np.sin(la2) - np.sin(la1) * np.cos(la2) * np.cos(dlon)
    a = a.assign(brg=(np.degrees(np.arctan2(yb, xb)) % 360))
    # per-flight join point (~9 NM, below 5,000 ft)
    j = a[(a["dist_thr_nm"].between(6, 13)) & (a["altitude"].between(500, 5000))].copy()
    j["d9"] = (j["dist_thr_nm"] - 9).abs()
    joins = j.sort_values("d9").groupby("flight_id", as_index=False).first()
    joins = joins[(joins["brg"] >= 40) & (joins["brg"] < 160)]   # drop the few odd ones
    joins["from_se"] = joins["brg"] >= SE_CUT
    # on-final context points (established, over the village)
    final = a[a["in_corridor"] & (a["altitude"].between(500, 5000)) & (a["dist_thr_nm"] < 12)]
    return joins, final


def build(out="outputs/sweep/brockenhurst_join_direction.png"):
    joins, final = load()
    jv = joins[(joins["longitude"].between(LON0, LON1)) & (joins["latitude"].between(LAT0, LAT1))]
    fv = final[(final["longitude"].between(LON0, LON1)) & (final["latitude"].between(LAT0, LAT1))]
    n_se = int(joins["from_se"].sum()); n_tot = len(joins)
    pct = 100 * n_se / n_tot

    fig, ax = plt.subplots(figsize=(12.5, 8.5))
    x0, y0 = merc(LON0, LAT0); x1, y1 = merc(LON1, LAT1)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    # shared funnel (grey)
    fx, fy = merc(fv["longitude"].values, fv["latitude"].values)
    ax.scatter(fx, fy, s=5, color="#555", alpha=0.10, zorder=3, linewidths=0)
    # join points, coloured
    st = jv[~jv["from_se"]]; se = jv[jv["from_se"]]
    sx, sy = merc(st["longitude"].values, st["latitude"].values)
    ex, ey = merc(se["longitude"].values, se["latitude"].values)
    ax.scatter(sx, sy, s=14, color=BLUE, alpha=0.35, zorder=4, linewidths=0)
    ax.scatter(ex, ey, s=16, color=ORANGE, alpha=0.55, zorder=5, linewidths=0)
    # landmarks
    bx, by = merc(BLON, BLAT); tx, ty = merc(TLON, TLAT)
    ax.scatter([bx], [by], marker="^", s=120, color="red", edgecolors="white",
               linewidths=1.3, zorder=7)
    ax.annotate("Brockenhurst", (bx, by), color="black", fontsize=10, fontweight="bold",
                xytext=(7, 5), textcoords="offset points", zorder=8)
    ax.scatter([tx], [ty], marker="*", s=230, color="#111", edgecolors="white",
               linewidths=1.1, zorder=7)
    ax.annotate("Bournemouth Airport", (tx, ty), color="black", fontsize=8.5,
                xytext=(8, -14), textcoords="offset points", zorder=8)
    cx.add_basemap(ax, source=cx.providers.OpenStreetMap.Mapnik, zoom=12,
                   attribution=False, zorder=1)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title("How airliners reach Brockenhurst: most fly straight in over the village, "
                 f"about 1 in 5 turn in from the south-east\n"
                 f"(runway-26 arrivals, 2023-2025 pooled · {n_tot:,} flights · {pct:.0f}% from the south-east · steady across all three years)",
                 fontsize=12.5, fontweight="bold")
    ax.legend(handles=[
        Line2D([0], [0], marker="o", color="none", markerfacecolor=BLUE, markersize=10,
               label=f"straight in over the village  ({100-pct:.0f}%)"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=ORANGE, markersize=10,
               label=f"turned in from the south-east, over Lymington / Sway  ({pct:.0f}%)"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor="#888", markersize=9,
               label="on final approach (the shared funnel)")],
        loc="lower left", fontsize=9.5, framealpha=0.9)
    fig.text(0.5, 0.008,
             "Each coloured dot is one flight, placed where it was about 9 miles out (the plane's own GPS). "
             "Both types cross near the village. Large jets only, via OPDI / OpenSky.",
             ha="center", va="bottom", fontsize=9, color="#333")
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(out, dpi=145, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out} | flights={n_tot} from_SE={pct:.0f}%")
    return out


if __name__ == "__main__":
    build()
