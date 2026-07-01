#!/usr/bin/env python3
"""
Map of where arriving aircraft actually fly over the Brockenhurst area (from the
aircraft's own recorded positions), with the current approach line and two
ILLUSTRATIVE alternative corridors (north / south of the village, over open
forest) for the residents' proposal.

    python route_map.py   ->  outputs/sweep/route_map.png

The alternative corridors are illustrative only - they show the *principle*
(join the final approach after passing the village, not before). A real change
would be designed by NATS/the airport through the CAA airspace-change process.
"""
from __future__ import annotations

import glob

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config
from brockenhurst import approach, charts
from brockenhurst import geometry as geo

BG, FG, GRID, BLUE, GOLD, RED = (charts.BG, charts.FG, charts.GRID,
                                 charts.BLUE, charts.GOLD, charts.RED)

# Approximate landmark positions (lat, lon) for orientation.
LANDMARKS = {
    "BROCKENHURST": (50.8189, -1.5757, RED, 13, "bold"),
    "Lyndhurst": (50.8725, -1.5747, FG, 10, "normal"),
    "Sway": (50.7830, -1.6120, FG, 10, "normal"),
    "Boldre": (50.7870, -1.5470, FG, 10, "normal"),
    "Lymington": (50.7585, -1.5450, FG, 10, "normal"),
    "Beaulieu": (50.8180, -1.4530, FG, 10, "normal"),
}


def _offset_track(rejoin_nm, abeam_km, side):
    """Illustrative track: on the centreline in to `rejoin_nm`, offset before that."""
    tlat, tlon = config.RWY26_THRESHOLD
    brg = np.radians(config.RWY26_OUTBOUND_TRACK_DEG)
    # sample distances (NM) from threshold, 0..18
    ds = np.linspace(0, 18, 200)
    lats, lons = [], []
    for d in ds:
        # base point on centreline at distance d
        km = d * geo.KM_PER_NM
        clat = tlat + (km / 111.0) * np.cos(brg)
        clon = tlon + (km / 111.0) * np.sin(brg) / np.cos(np.radians(tlat))
        # perpendicular offset that grows once past the rejoin distance
        if d <= rejoin_nm:
            off = 0.0
        else:
            off = abeam_km * min(1.0, (d - rejoin_nm) / 3.0)  # ramp in over 3 NM
        # perpendicular bearing (+90 deg = left/north-ish of outbound track)
        pbrg = brg + (np.pi / 2) * side
        clat += (off / 111.0) * np.cos(pbrg)
        clon += (off / 111.0) * np.sin(pbrg) / np.cos(np.radians(tlat))
        lats.append(clat); lons.append(clon)
    return np.array(lons), np.array(lats)


def build(out="outputs/sweep/route_map.png"):
    ev = pd.concat([pd.read_parquet(f) for f in glob.glob("data/eghh_events_*.parquet")],
                   ignore_index=True)
    ev["flight_id"] = ev["flight_id"].astype("uint64")
    arr = pd.read_csv("outputs/sweep/arrivals.csv"); arr["flight_id"] = arr["id"].astype("uint64")
    lj = set(arr[arr["category"] == "Large jet"]["flight_id"])
    a = approach.annotate(ev[ev["flight_id"].isin(lj)])
    b = a[(a["altitude"].between(500, 6000)) & (a["d_brock_km"] < 20) & (a["longitude"] > -1.86)]

    fig, ax = plt.subplots(figsize=(12, 8.5), facecolor=BG)
    ax.set_facecolor("#101014")

    # density of actual aircraft positions
    hb = ax.hexbin(b["longitude"], b["latitude"], gridsize=90, bins="log",
                   cmap="inferno", mincnt=1, linewidths=0.0)

    # current approach centreline (extended runway 26)
    lon0, lat0 = _offset_track(0, 0, 1)
    ax.plot(lon0, lat0, color="#5aa0ff", lw=2.4, ls="-",
            label="Current approach line (straight over the village)")

    # illustrative alternatives (+90 deg from the 075 outbound track points south,
    # -90 deg points north, so north = -1, south = +1)
    lonN, latN = _offset_track(5.5, 2.6, -1)
    lonS, latS = _offset_track(5.5, 2.6, +1)
    ax.plot(lonN, latN, color="#39d353", lw=2.6, ls="--",
            label="Illustrative: join final NORTH of the village")
    ax.plot(lonS, latS, color="#f0c96b", lw=2.6, ls="--",
            label="Illustrative: join final SOUTH of the village")

    # landmarks
    for name, (la, lo, col, fs, w) in LANDMARKS.items():
        ax.scatter([lo], [la], s=70 if name == "BROCKENHURST" else 34,
                   marker="^" if name == "BROCKENHURST" else "o",
                   color=col, edgecolors="k", zorder=6)
        ax.annotate(name, (lo, la), textcoords="offset points", xytext=(7, 5),
                    color=col, fontsize=fs, fontweight=w, zorder=6)

    # a 2 km ring around the village
    th = np.linspace(0, 2 * np.pi, 120)
    blat, blon = 50.8189, -1.5757
    ax.plot(blon + (2 / (111 * np.cos(np.radians(blat)))) * np.cos(th),
            blat + (2 / 111.0) * np.sin(th), color=RED, lw=1, ls=":", alpha=0.8)

    ax.set_aspect(1 / np.cos(np.radians(50.82)))
    ax.set_xlim(-1.85, -1.36); ax.set_ylim(50.70, 50.90)
    for s in ax.spines.values():
        s.set_color(GRID)
    ax.tick_params(colors=FG, labelsize=8)
    ax.set_xlabel("Longitude", color=FG); ax.set_ylabel("Latitude", color=FG)
    ax.set_title("Where Bournemouth arrivals actually fly over the New Forest\n"
                 "Brighter = more aircraft. The hotspot runs straight through Brockenhurst.",
                 color=FG, fontsize=13)
    ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=FG, fontsize=9.5, loc="upper right")
    cb = fig.colorbar(hb, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("number of recorded aircraft positions", color=FG)
    cb.ax.tick_params(colors=FG)
    fig.text(0.5, 0.008,
             "Aircraft positions: large jets, 500-6,000 ft, 2023-2025, from ADS-B via OPDI/OpenSky. "
             "Alternative corridors are illustrative (principle: join final approach after passing the village). "
             "Landmark positions approximate.",
             ha="center", color="#8a8a90", fontsize=8)
    fig.savefig(out, dpi=140, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out)
    return out


if __name__ == "__main__":
    build()
