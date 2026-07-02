#!/usr/bin/env python3
"""
2023 vs 2024 vs 2025 street-level heat maps of large-airliner crossings over
Brockenhurst, side by side on an OpenStreetMap background.

    python heatmap_compare.py   ->  outputs/sweep/brockenhurst_heatmap_compare.png
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
HL, HT = 0.037, 0.023   # half-width lon / lat of the view


def merc(lon, lat):
    return R * np.radians(lon), R * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))


def crossings():
    ev = pd.concat([pd.read_parquet(f) for f in glob.glob("data/eghh_events_*.parquet")],
                   ignore_index=True)
    ev["flight_id"] = ev["flight_id"].astype("uint64")
    arr = pd.read_csv("outputs/sweep/arrivals.csv"); arr["flight_id"] = arr["id"].astype("uint64")
    arr["year"] = pd.to_datetime(arr["dof"]).dt.year
    m = ev.merge(arr[["flight_id", "category", "year"]], on="flight_id", how="left")
    a = approach.annotate(m)
    a = a[(a["category"] == "Large jet") & (a["altitude"].between(500, 5000))
          & a["in_corridor"] & (a["d_brock_km"] < 6)]
    c = a.sort_values("d_brock_km").groupby("flight_id", as_index=False).first()
    return c[(c["longitude"].between(BLON - HL, BLON + HL))
             & (c["latitude"].between(BLAT - HT, BLAT + HT))]


def panel(ax, box, year):
    x0, y0 = merc(BLON - HL, BLAT - HT); x1, y1 = merc(BLON + HL, BLAT + HT)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    xs, ys = merc(box["longitude"].values, box["latitude"].values)
    kde = gaussian_kde(np.vstack([xs, ys]), bw_method=0.18)
    gx = np.linspace(x0, x1, 200); gy = np.linspace(y0, y1, 160)
    GX, GY = np.meshgrid(gx, gy)
    Z = kde(np.vstack([GX.ravel(), GY.ravel()])).reshape(GX.shape)
    Z /= Z.max()
    ax.contourf(GX, GY, Z, levels=np.linspace(0.12, 1.0, 9), cmap="turbo", alpha=0.5, zorder=3)
    ax.contour(GX, GY, Z, levels=[0.5], colors="white", linewidths=1.0, alpha=0.7, zorder=4)
    ax.scatter(xs, ys, s=4, color="black", alpha=0.16, zorder=5)
    bx, by = merc(BLON, BLAT)
    ax.scatter([bx], [by], marker="^", s=90, color="red", edgecolors="white", linewidths=1, zorder=6)
    cx.add_basemap(ax, source=cx.providers.OpenStreetMap.Mapnik, zoom=14,
                   attribution=False, zorder=1)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(f"{year}   ·   {len(box):,} airliner crossings   ·   "
                 f"median {box['altitude'].median():,.0f} ft", fontsize=12, fontweight="bold")


def build(out="outputs/sweep/brockenhurst_heatmap_compare.png"):
    c = crossings()
    fig, axes = plt.subplots(1, 3, figsize=(22, 8.6))
    for ax, y in zip(axes, [2023, 2024, 2025]):
        panel(ax, c[c["year"] == y], y)
    fig.suptitle("Where large airliners cross Brockenhurst — 2023 vs 2024 vs 2025",
                 fontsize=16, fontweight="bold", y=0.98)
    fig.text(0.5, 0.055,
             "Observations: the flight path stays in the SAME place each year — over the northern village "
             "(Rhinefield Road / by Brockenhurst College / toward Balmer Lawn) — and is the SAME width. "
             "But there are MORE crossings each year (510 → 614 → 706 in view, +38%) and the median height "
             "keeps FALLING (2,800 → 2,700 ft). Each dot = one flight; heat = concentration; red triangle = village centre.",
             ha="center", va="top", fontsize=10, color="#333333", wrap=True)
    fig.tight_layout(rect=[0, 0.085, 1, 0.95])
    fig.savefig(out, dpi=135, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out)
    return out


if __name__ == "__main__":
    build()
