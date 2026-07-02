#!/usr/bin/env python3
"""
Side-by-side density maps: where the AIRLINERS fly vs where the LIGHT / TRAINING
aircraft fly, from the aircraft's own recorded positions. Answers whether the
training fleet crosses Brockenhurst or stays around the airport.

    python light_map.py   ->  outputs/sweep/light_vs_airliner_map.png
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

BG, FG, GRID, RED, GOLD = "#0b0b0f", charts.FG, charts.GRID, "#e23b3b", "#e0a01f"
EXT = (-2.02, -1.34, 50.64, 50.96)   # lon0, lon1, lat0, lat1


def load():
    ev = pd.concat([pd.read_parquet(f) for f in glob.glob("data/eghh_events_*.parquet")],
                   ignore_index=True)
    ev["flight_id"] = ev["flight_id"].astype("uint64")
    arr = pd.read_csv("outputs/sweep/arrivals.csv"); arr["flight_id"] = arr["id"].astype("uint64")
    ev = ev.merge(arr[["flight_id", "category"]], on="flight_id", how="left")
    a = approach.annotate(ev)
    a = a[a["altitude"].between(0, 5000)]
    a = a[(a["longitude"].between(EXT[0], EXT[1])) & (a["latitude"].between(EXT[2], EXT[3]))]
    return a


def panel(ax, d, title, cmap):
    ax.set_facecolor("#101014")
    hb = ax.hexbin(d["longitude"], d["latitude"], gridsize=80, bins="log",
                   cmap=cmap, mincnt=1, linewidths=0.0)
    # landmarks
    for name, la, lo, col, mk, s in [
        ("BROCKENHURST", 50.8189, -1.5757, RED, "^", 90),
        ("Airport", config.RWY26_THRESHOLD[0], config.RWY26_THRESHOLD[1], GOLD, "*", 200)]:
        ax.scatter([lo], [la], marker=mk, s=s, color=col, edgecolors="k", zorder=6)
        ax.annotate(name, (lo, la), textcoords="offset points", xytext=(6, 5),
                    color="white" if name == "BROCKENHURST" else FG,
                    fontsize=9 if name == "BROCKENHURST" else 8,
                    fontweight="bold" if name == "BROCKENHURST" else "normal", zorder=6)
    th = np.linspace(0, 2 * np.pi, 90)
    ax.plot(-1.5757 + (2 / (111 * np.cos(np.radians(50.82)))) * np.cos(th),
            50.8189 + (2 / 111.0) * np.sin(th), color=RED, lw=0.8, ls=":", alpha=0.7)
    ax.set_aspect(1 / np.cos(np.radians(50.8)))
    ax.set_xlim(EXT[0], EXT[1]); ax.set_ylim(EXT[2], EXT[3])
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color(GRID)
    ax.set_title(title, color=FG, fontsize=12)
    return hb


def build(out="outputs/sweep/light_vs_airliner_map.png"):
    a = load()
    lj = a[a["category"] == "Large jet"]
    light = a[a["category"] == "GA / light"]
    fig, axes = plt.subplots(1, 2, figsize=(15, 7), facecolor=BG)
    panel(axes[0], lj, f"AIRLINERS  (large jets, {lj['flight_id'].nunique():,} flights)", "inferno")
    panel(axes[1], light, f"LIGHT / TRAINING aircraft  ({light['flight_id'].nunique():,} flights)", "viridis")
    fig.suptitle("Where they fly: airliners funnel over Brockenhurst · light/training aircraft cluster at the airport",
                 color=FG, fontsize=14, y=0.98)
    fig.text(0.5, 0.02, "Recorded positions below 5,000 ft, 2023–2025, from ADS-B via OPDI/OpenSky. "
                        "Brighter = more aircraft. Red triangle = Brockenhurst; star = Bournemouth Airport.",
             ha="center", color="#8a8a90", fontsize=8.5)
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    fig.savefig(out, dpi=135, facecolor=BG)
    plt.close(fig)
    # quick stat: share of each fleet's points within 3 km of the village
    for name, d in [("airliners", lj), ("light/training", light)]:
        near = (d["d_brock_km"] < 3).mean() * 100
        print(f"{name}: {100*len(d)/len(d):.0f}%  |  {near:.0f}% of recorded points within 3 km of Brockenhurst")
    print("wrote", out)
    return out


if __name__ == "__main__":
    build()
