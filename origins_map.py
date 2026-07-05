#!/usr/bin/env python3
"""
The full picture: where Bournemouth's large-jet arrivals come from. Every origin
airport (2023-2025) joined to Bournemouth, line weight by number of flights, on a
Europe-wide map.

These lines are origin-to-destination connections (showing where flights start),
not the exact flown tracks. Counts are from the flight list.

    python origins_map.py  ->  outputs/sweep/origins_map.png
"""
from __future__ import annotations

import glob

import contextily as cx
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

R = 6378137.0
EGHH = (50.78, -1.84)
# Airport coordinates (lat, lon) for the origins that appear in the data.
APT = {
    "LEPA": (39.55, 2.74, "Palma"), "LEAL": (38.28, -0.56, "Alicante"),
    "LEMG": (36.67, -4.50, "Malaga"), "LPFR": (37.01, -7.97, "Faro"),
    "EGDY": (51.00, -2.64, "Yeovilton"), "LMML": (35.86, 14.48, "Malta"),
    "EPKK": (50.08, 19.78, "Krakow"), "LSGG": (46.24, 6.11, "Geneva"),
    "EGPH": (55.95, -3.37, "Edinburgh"), "LEGE": (41.90, 2.76, "Girona"),
    "EGNV": (54.51, -1.43, "Teesside"), "LEMI": (37.80, -1.12, "Murcia"),
    "LIPZ": (45.51, 12.35, "Venice"), "LGRP": (36.41, 28.09, "Rhodes"),
    "EPWR": (51.10, 16.89, "Wroclaw"), "EGJJ": (49.21, -2.20, "Jersey"),
    "EGLF": (51.28, -0.78, "Farnborough"), "EGHQ": (50.44, -5.00, "Newquay"),
    "EIDW": (53.43, -6.27, "Dublin"), "LHBP": (47.44, 19.26, "Budapest"),
    "EGJB": (49.43, -2.60, "Guernsey"), "EGSS": (51.89, 0.23, "Stansted"),
    "EGKB": (51.33, 0.03, "Biggin Hill"), "EGGW": (51.87, -0.37, "Luton"),
    "LEIB": (38.87, 1.37, "Ibiza"), "LFMN": (43.66, 7.22, "Nice"),
    "LEBL": (41.30, 2.08, "Barcelona"), "GCTS": (28.04, -16.57, "Tenerife"),
    "LICJ": (38.18, 13.10, "Palermo"), "LGKR": (39.60, 19.91, "Corfu"),
    "EHAM": (52.31, 4.76, "Amsterdam"), "LFPB": (48.97, 2.44, "Paris"),
    "EGHH": (50.78, -1.84, "Bournemouth"),
}
LABEL_MIN = 90   # only label origins with at least this many flights


def merc(lon, lat):
    return R * np.radians(lon), R * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))


def counts():
    """Origins for the SAME canonical large-jet arrival set the rest of the pack
    uses (arrivals.csv), joined to the flight list for the departure airport."""
    arr = pd.read_csv("outputs/sweep/arrivals.csv"); arr["flight_id"] = arr["id"].astype("uint64")
    arr["year"] = pd.to_datetime(arr["dof"]).dt.year
    lj = arr[(arr["category"] == "Large jet") & (arr["year"].isin([2023, 2024, 2025]))]
    rows = []
    for f in (glob.glob("data/flight_list_2023*.parquet") + glob.glob("data/flight_list_2024*.parquet")
              + glob.glob("data/flight_list_2025*.parquet")):
        d = pd.read_parquet(f, columns=["id", "adep", "ades"])
        d = d[d["ades"] == "EGHH"].copy()
        ids = d["id"].to_numpy()
        d["id"] = ids.view("uint64") if ids.dtype == "int64" else ids.astype("uint64")
        rows.append(d[["id", "adep"]])
    fl = pd.concat(rows, ignore_index=True)
    m = lj.merge(fl[["id", "adep"]].drop_duplicates("id"), left_on="flight_id",
                 right_on="id", how="left")
    return m["adep"].value_counts(), len(lj), int(m["adep"].notna().sum())


def build(out="outputs/sweep/origins_map.png"):
    vc, canonical_total, with_origin = counts()
    known = {k: v for k, v in vc.items() if k in APT and k != "EGHH"}
    shown = sum(known.values())
    ex, ey = merc(*EGHH[::-1])

    fig, ax = plt.subplots(figsize=(14, 12))
    lons = [APT[k][1] for k in known] + [EGHH[1]]
    lats = [APT[k][0] for k in known] + [EGHH[0]]
    xs, ys = merc(np.array(lons), np.array(lats))
    pad = 5.5e5
    ax.set_xlim(xs.min() - pad, xs.max() + pad)
    ax.set_ylim(ys.min() - pad * 0.55, ys.max() + pad * 1.4)

    mx = max(known.values())
    for k, n in sorted(known.items(), key=lambda kv: kv[1]):
        la, lo, name = APT[k]
        ox, oy = merc(lo, la)
        lw = 0.6 + 4.4 * (n / mx)
        ax.plot([ox, ex], [oy, ey], color="#2c6fbb", lw=lw, alpha=0.30 + 0.5 * (n / mx),
                solid_capstyle="round", zorder=3)
        ax.scatter([ox], [oy], s=18 + 120 * (n / mx), color="#1a4f8a", edgecolors="white",
                   linewidths=0.6, zorder=4)
        if n >= LABEL_MIN:
            ax.annotate(f"{name} ({n:,})", (ox, oy), textcoords="offset points",
                        xytext=(5, 4), fontsize=8.5, color="#12233b", fontweight="bold", zorder=6)
    ax.scatter([ex], [ey], marker="*", s=460, color="#c0392b", edgecolors="white",
               linewidths=1.4, zorder=7)
    ax.annotate("BOURNEMOUTH", (ex, ey), textcoords="offset points", xytext=(8, 8),
                fontsize=11, color="#c0392b", fontweight="bold", zorder=7)

    cx.add_basemap(ax, source=cx.providers.CartoDB.Positron, zoom=5, attribution=False, zorder=1)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title("Where Bournemouth's arrivals come from, the full picture\n"
                 f"{with_origin:,} large-jet arrivals with an identified origin (2023-2025), "
                 f"from {vc.size} airports across Europe (the busiest labelled)",
                 fontsize=14, fontweight="bold")
    fig.text(0.5, 0.045,
             "Each line joins an origin airport to Bournemouth; thicker = more flights. These show where flights "
             "start (holiday and charter routes across Spain, Portugal, Malta, Greece, the Alps and beyond), not the "
             "exact flown tracks. Every one of them arrives over Brockenhurst.\n"
             f"Of our {canonical_total:,} large-jet arrivals, {with_origin:,} had an origin airport recorded in the "
             "data; the rest were first picked up already in flight. Via OPDI / OpenSky.",
             ha="center", va="bottom", fontsize=9.5, color="#333")
    fig.tight_layout(rect=[0, 0.085, 1, 1])
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out} | canonical={canonical_total} with_origin={with_origin} airports={vc.size} mapped={len(known)} ({shown} flights)")
    return out


if __name__ == "__main__":
    build()
