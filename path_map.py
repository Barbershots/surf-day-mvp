#!/usr/bin/env python3
"""
Path map: every runway-26 (Brockenhurst-direction) large-jet arrival drawn as a
line through its own recorded GPS points, on an OpenStreetMap background. Shows
the SHAPE of the approach, straight in over the village vs curving up from the
south, not just a single dot.

Lines connect the aircraft's real logged fixes (median ~9 per approach). They
are approximate between fixes, so a turn is drawn as a few straight segments
rather than a perfectly smooth curve.

    python path_map.py  ->  outputs/sweep/brockenhurst_paths.png
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
from scipy.interpolate import splev, splprep

import config
from brockenhurst import approach

BLAT, BLON = config.BROCKENHURST
TLAT, TLON = config.RWY26_THRESHOLD
R = 6378137.0
LON0, LON1, LAT0, LAT1 = -1.95, -1.42, 50.66, 50.88
# street-level view centred on the village (road names visible)
VHL, VHT = 0.055, 0.034
BLUE, ORANGE = "#1f5fb0", "#e8720c"
SE_CUT = 88.0


def merc(lon, lat):
    return (R * np.radians(np.asarray(lon)),
            R * np.log(np.tan(np.pi / 4 + np.radians(np.asarray(lat)) / 2)))


def load():
    ev = pd.concat([pd.read_parquet(f) for f in glob.glob("data/eghh_events_*.parquet")],
                   ignore_index=True)
    ev["flight_id"] = ev["flight_id"].astype("uint64")
    arr = pd.read_csv("outputs/sweep/arrivals.csv"); arr["flight_id"] = arr["id"].astype("uint64")
    m = ev.merge(arr[["flight_id", "category"]], on="flight_id", how="left")
    a = approach.annotate(m)
    a = a[a["category"] == "Large jet"]
    low = a[a["altitude"].between(200, 5000) & (a["dist_thr_nm"] < 12)]
    side = low.groupby("flight_id")["longitude"].mean()
    rwy26 = set(side[side > TLON].index)
    a = a[a["flight_id"].isin(rwy26)]
    # approach points only: from ~22 NM in to short final, drop ground points
    a = a[(a["dist_thr_nm"] < 22) & (a["altitude"].between(300, 9000))]
    # bearing from threshold, to classify the ~9 NM join
    la1 = np.radians(TLAT); la2 = np.radians(a["latitude"].values)
    dlon = np.radians(a["longitude"].values - TLON)
    yb = np.sin(dlon) * np.cos(la2)
    xb = np.cos(la1) * np.sin(la2) - np.sin(la1) * np.cos(la2) * np.cos(dlon)
    a = a.assign(brg=(np.degrees(np.arctan2(yb, xb)) % 360))
    j = a[(a["dist_thr_nm"].between(6, 13))].copy()
    j["d9"] = (j["dist_thr_nm"] - 9).abs()
    cls = j.sort_values("d9").groupby("flight_id", as_index=False).first()[["flight_id", "brg"]]
    cls["from_se"] = (cls["brg"] >= SE_CUT) & (cls["brg"] < 160)
    return a, cls.set_index("flight_id")["from_se"].to_dict()


def smooth(x, y):
    """Light spline through the real fixes so the path reads as a curve.
    Falls back to the raw polyline if too few unique points."""
    if len(x) < 4:
        return x, y
    try:
        tck, _ = splprep([x, y], s=0, k=min(3, len(x) - 1))
        u = np.linspace(0, 1, 120)
        return splev(u, tck)
    except Exception:
        return x, y


def _draw(ax, a, from_se, box, zoom, lw, alpha_st, alpha_se, smooth_on=True,
          min_pts=4, clip_margin=None, mono=False):
    lon0, lon1, lat0, lat1 = box
    x0, y0 = merc(lon0, lat0); x1, y1 = merc(lon1, lat1)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    if clip_margin is not None:
        # keep only points inside the view (+margin) so long approach tails from
        # far-out fixes don't streak across a zoomed frame
        m = clip_margin
        a = a[(a["longitude"].between(lon0 - m, lon1 + m))
              & (a["latitude"].between(lat0 - m, lat1 + m))]
    n_se = n_st = 0
    for fid, g in a.groupby("flight_id"):
        g = g.sort_values("dist_thr_nm", ascending=False)
        if len(g) < min_pts:
            continue
        se = from_se.get(fid, False)
        n_se += se; n_st += (not se)
        mx, my = merc(g["longitude"].values, g["latitude"].values)
        sx, sy = smooth(mx, my) if smooth_on else (mx, my)
        col = BLUE if (mono or not se) else ORANGE
        ax.plot(sx, sy, color=col, lw=lw,
                alpha=alpha_se if se else alpha_st, zorder=3, solid_capstyle="round")
    bx, by = merc(BLON, BLAT)
    ax.scatter([bx], [by], marker="^", s=150, color="red", edgecolors="white",
               linewidths=1.5, zorder=7)
    ax.annotate("Brockenhurst", (bx, by), color="black", fontsize=11, fontweight="bold",
                xytext=(9, 5), textcoords="offset points", zorder=8,
                path_effects=None)
    cx.add_basemap(ax, source=cx.providers.OpenStreetMap.Mapnik, zoom=zoom,
                   attribution=False, zorder=1)
    ax.set_xticks([]); ax.set_yticks([])
    return n_st, n_se


def build(out="outputs/sweep/brockenhurst_paths.png"):
    a, from_se = load()
    fig, ax = plt.subplots(figsize=(13, 8.8))
    n_st, n_se = _draw(ax, a, from_se, (LON0, LON1, LAT0, LAT1), 12, 1.3, 0.06, 0.06, mono=True)
    tx, ty = merc(TLON, TLAT)
    ax.scatter([tx], [ty], marker="*", s=240, color="#111", edgecolors="white",
               linewidths=1.1, zorder=7)
    ax.annotate("Bournemouth Airport", (tx, ty), color="black", fontsize=9,
                xytext=(8, -14), textcoords="offset points", zorder=8)
    tot = n_se + n_st
    ax.set_title("The path each airliner flew into Brockenhurst (runway-26 arrivals, 2023-2025)\n"
                 f"{tot:,} approaches · they fan in from the north-east, east and south and "
                 "converge onto one line over the village",
                 fontsize=12.5, fontweight="bold")
    ax.legend(handles=[
        Line2D([0], [0], color=BLUE, lw=2.4, label="one airliner's path (each line = one flight)")],
        loc="lower left", fontsize=10, framealpha=0.92)
    fig.text(0.5, 0.006,
             "Each line is one flight through its own recorded GPS fixes (median ~9 per approach), lightly smoothed. "
             "Approximate between fixes. Large jets only, via OPDI / OpenSky.",
             ha="center", va="bottom", fontsize=9, color="#333")
    fig.tight_layout(rect=[0, 0.028, 1, 1])
    fig.savefig(out, dpi=145, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out} | approaches={tot} from_south={100*n_se/tot:.0f}%")
    return out


def build_zoom(out="outputs/sweep/brockenhurst_paths_village.png"):
    """Street-level zoom over the village so road names / landmarks show."""
    a, from_se = load()
    box = (BLON - VHL, BLON + VHL, BLAT - VHT, BLAT + VHT)
    fig, ax = plt.subplots(figsize=(13, 9.2))
    n_st, n_se = _draw(ax, a, from_se, box, 14, 1.7, 0.16, 0.16, smooth_on=False,
                       min_pts=2, clip_margin=0.02, mono=True)
    tot = n_se + n_st
    ax.set_title("Every airliner's path directly over Brockenhurst (runway-26 arrivals, 2023-2025)\n"
                 f"each line is one flight · {tot:,} large-jet approaches",
                 fontsize=12.5, fontweight="bold")
    ax.legend(handles=[
        Line2D([0], [0], color=BLUE, lw=2.6, label="one airliner's path over the village")],
        loc="lower left", fontsize=10, framealpha=0.92)
    fig.text(0.5, 0.006,
             f"{tot:,} large-jet approaches, 2023-2025, showing the part of each track crossing the village, "
             "drawn straight between the aircraft's own recorded GPS fixes. Via OPDI / OpenSky.",
             ha="center", va="bottom", fontsize=9, color="#333")
    fig.tight_layout(rect=[0, 0.028, 1, 1])
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out} | approaches in view drawn")
    return out


if __name__ == "__main__":
    import sys
    if "--zoom" in sys.argv:
        build_zoom()
    else:
        build()
