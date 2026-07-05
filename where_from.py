#!/usr/bin/env python3
"""
"Where do the arrivals come from?" A compass rose of the direction each runway-26
large-jet arrival was still tracking from when ~15 NM out (before it merged onto
the final approach line over the village).

    python where_from.py  ->  outputs/sweep/where_from.png
"""
from __future__ import annotations

import glob

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config
from brockenhurst import approach

TLAT, TLON = config.RWY26_THRESHOLD
BLUE = "#2c6fbb"


def bearings():
    ev = pd.concat([pd.read_parquet(f) for f in glob.glob("data/eghh_events_*.parquet")],
                   ignore_index=True)
    ev["flight_id"] = ev["flight_id"].astype("uint64")
    arr = pd.read_csv("outputs/sweep/arrivals.csv"); arr["flight_id"] = arr["id"].astype("uint64")
    lj = set(arr[arr["category"] == "Large jet"]["flight_id"])
    a = approach.annotate(ev[ev["flight_id"].isin(lj)])
    low = a[a["altitude"].between(200, 5000) & (a["dist_thr_nm"] < 12)]
    side = low.groupby("flight_id")["longitude"].mean()
    a = a[a["flight_id"].isin(set(side[side > TLON].index))]
    la1 = np.radians(TLAT); la2 = np.radians(a["latitude"].values)
    dlon = np.radians(a["longitude"].values - TLON)
    y = np.sin(dlon) * np.cos(la2)
    x = np.cos(la1) * np.sin(la2) - np.sin(la1) * np.cos(la2) * np.cos(dlon)
    a = a.assign(brg=(np.degrees(np.arctan2(y, x)) % 360))
    b = a[(a["dist_thr_nm"].between(12, 18)) & (a["altitude"].between(500, 7000))].copy()
    b["dd"] = (b["dist_thr_nm"] - 15).abs()
    pf = b.sort_values("dd").groupby("flight_id", as_index=False).first()
    return pf["brg"].values


def build(out="outputs/sweep/where_from.png"):
    brg = bearings()
    n = len(brg)
    step = 15
    edges = np.arange(0, 360 + step, step)
    counts, _ = np.histogram(brg, bins=edges)
    pct = 100 * counts / n
    centres = np.radians(edges[:-1] + step / 2)

    fig = plt.figure(figsize=(9.5, 8.4))
    ax = fig.add_subplot(111, projection="polar")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.bar(centres, pct, width=np.radians(step) * 0.92, color=BLUE, alpha=0.85,
           edgecolor="white", linewidth=0.6, zorder=3)
    ax.set_xticks(np.radians([0, 45, 90, 135, 180, 225, 270, 315]))
    ax.set_xticklabels(["N", "NE", "E", "SE", "S", "SW", "W", "NW"], fontsize=12, fontweight="bold")
    ax.set_yticks([5, 10, 15])
    ax.set_yticklabels(["5%", "10%", "15%"], fontsize=8, color="#666")
    ax.set_ylim(0, max(pct) * 1.15)
    ax.set_title("Where the arrivals come from\n"
                 "(direction each large jet was still tracking from at ~15 miles out,\n"
                 "before it turned onto the final line over the village)",
                 fontsize=13, fontweight="bold", pad=24)

    # split by which side of the straight-in line (75 deg) they approach from
    north_side = (brg < 75).mean() * 100      # NE side, curving down
    south_side = (brg >= 75).mean() * 100      # SE / coast side, curving up
    fig.text(0.5, 0.045,
             f"About {north_side:.0f}% approach from the NORTH side of the line (the north-east, curving down) "
             f"and about {south_side:.0f}% from the SOUTH side (the south-east and coast, curving up).\n"
             "Almost none come from due north or the west. Whichever side they start, they all converge onto "
             f"the same line over Brockenhurst. Runway-26 large jets, 2023-2025, {n:,} flights, via OPDI / OpenSky.",
             ha="center", va="bottom", fontsize=9.5, color="#333")
    fig.tight_layout(rect=[0, 0.09, 1, 1])
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out} | north-side={north_side:.0f}% south-side={south_side:.0f}% n={n}")
    return out


if __name__ == "__main__":
    build()
