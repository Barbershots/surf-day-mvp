#!/usr/bin/env python3
"""
Street-level heat map of where large airliners actually fly over Brockenhurst
(2025), overlaid on an OpenStreetMap background so road names / landmarks show.

    python heatmap_streets.py   ->  outputs/sweep/brockenhurst_heatmap_2025.png
"""
from __future__ import annotations

import glob

import contextily as cx
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde

import config
from brockenhurst import approach

BLAT, BLON = config.BROCKENHURST
R = 6378137.0


def merc(lon, lat):
    x = R * np.radians(lon)
    y = R * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))
    return x, y


def build(out="outputs/sweep/brockenhurst_heatmap_2025.png",
          half_lon=0.037, half_lat=0.023):
    ev = pd.concat([pd.read_parquet(f) for f in glob.glob("data/eghh_events_2025*.parquet")
                    + glob.glob("data/eghh_events_20250*.parquet")], ignore_index=True)
    ev["flight_id"] = ev["flight_id"].astype("uint64")
    arr = pd.read_csv("outputs/sweep/arrivals.csv"); arr["flight_id"] = arr["id"].astype("uint64")
    arr["year"] = pd.to_datetime(arr["dof"]).dt.year
    lj = set(arr[(arr["category"] == "Large jet") & (arr["year"] == 2025)]["flight_id"])
    a = approach.annotate(ev[ev["flight_id"].isin(lj)])
    # ONE point per flight: where it actually crosses over the village (closest
    # recorded point to Brockenhurst, within the corridor and below 5,000 ft).
    a = a[(a["altitude"].between(500, 5000)) & a["in_corridor"] & (a["d_brock_km"] < 6)]
    box = a.sort_values("d_brock_km").groupby("flight_id", as_index=False).first()
    box = box[(box["longitude"].between(BLON - half_lon, BLON + half_lon))
              & (box["latitude"].between(BLAT - half_lat, BLAT + half_lat))]
    print("2025 large-jet village crossings in view:", len(box))

    xs, ys = merc(box["longitude"].values, box["latitude"].values)
    x0, y0 = merc(BLON - half_lon, BLAT - half_lat)
    x1, y1 = merc(BLON + half_lon, BLAT + half_lat)

    fig, ax = plt.subplots(figsize=(12, 9))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)

    # KDE density on a grid
    kde = gaussian_kde(np.vstack([xs, ys]), bw_method=0.18)
    gx = np.linspace(x0, x1, 260); gy = np.linspace(y0, y1, 200)
    GX, GY = np.meshgrid(gx, gy)
    Z = kde(np.vstack([GX.ravel(), GY.ravel()])).reshape(GX.shape)
    Z = Z / Z.max()
    levels = np.linspace(0.12, 1.0, 9)
    cf = ax.contourf(GX, GY, Z, levels=levels, cmap="turbo", alpha=0.5, zorder=3)
    ax.contour(GX, GY, Z, levels=[0.5], colors="white", linewidths=1.2, alpha=0.7, zorder=4)
    ax.scatter(xs, ys, s=5, color="black", alpha=0.18, zorder=5)  # each dot = one flight crossing

    # village marker
    bx, by = merc(BLON, BLAT)
    ax.scatter([bx], [by], marker="^", s=110, color="red", edgecolors="white",
               linewidths=1.2, zorder=6)

    cx.add_basemap(ax, source=cx.providers.OpenStreetMap.Mapnik, zoom=14,
                   attribution_size=6, zorder=1)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title("Where large airliners fly over Brockenhurst — 2025\n"
                 "heat = concentration of aircraft (each dot = one flight crossing the village · from the aircraft's own GPS)",
                 fontsize=13)
    # legend for the heat
    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(color=plt.cm.turbo(0.9), alpha=0.6, label="busiest (most aircraft)"),
        Patch(color=plt.cm.turbo(0.35), alpha=0.6, label="fewer aircraft"),
        Patch(facecolor="none", edgecolor="white", label="core corridor (white line)")],
        loc="lower left", fontsize=9, framealpha=0.85)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out)
    return out


if __name__ == "__main__":
    build()
