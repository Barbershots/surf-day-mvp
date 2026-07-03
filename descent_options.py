#!/usr/bin/env python3
"""
Three side-profile graphs for Option A: how aircraft descend over Brockenhurst
TODAY vs a 3.0-degree continuous glide vs a 3.3-degree continuous glide.

Altitude (ft) against distance from the runway (nautical miles). Brockenhurst is
9.7 NM out. Built from the aircraft's own recorded heights (runway-26 large-jet
arrivals, 2023-2025).

    python descent_options.py  ->  outputs/sweep/descent_options.png
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
from brockenhurst import geometry as geo

TLAT, TLON = config.RWY26_THRESHOLD
VDIST = geo.dist_from_threshold_nm(*config.BROCKENHURST)   # ~9.67 NM
FT = geo.FT_PER_NM


def glide(deg, d):
    return np.tan(np.radians(deg)) * d * FT + config.EGHH_ELEV_FT


def load():
    ev = pd.concat([pd.read_parquet(f) for f in glob.glob("data/eghh_events_*.parquet")],
                   ignore_index=True)
    ev["flight_id"] = ev["flight_id"].astype("uint64")
    arr = pd.read_csv("outputs/sweep/arrivals.csv"); arr["flight_id"] = arr["id"].astype("uint64")
    lj = set(arr[arr["category"] == "Large jet"]["flight_id"])
    a = approach.annotate(ev[ev["flight_id"].isin(lj)])
    low = a[a["altitude"].between(200, 5000) & (a["dist_thr_nm"] < 12)]
    side = low.groupby("flight_id")["longitude"].mean()
    a = a[a["flight_id"].isin(set(side[side > TLON].index))]
    a = a[a["in_corridor"] & a["altitude"].between(200, 6500) & a["dist_thr_nm"].between(0, 18)]
    # drop points that sit well ABOVE a steep approach slope: near the airport these
    # are downwind / vectored traffic at altitude, not aircraft on final approach.
    ceil = np.tan(np.radians(4.0)) * a["dist_thr_nm"] * FT + config.EGHH_ELEV_FT + 800
    return a[a["altitude"] < ceil]


def pct_below(a, h):
    g = a[a["in_corridor"] & (a["altitude"].between(300, 5000)) & (a["d_brock_km"] < 3)]
    c = g.sort_values("d_brock_km").groupby("flight_id", as_index=False).first()
    return (c["altitude"] < h).mean() * 100, c["altitude"].median()


def build(out="outputs/sweep/descent_options.png"):
    a = load()
    # median measured profile (today), by distance bin -> shows the level-off shelf
    bins = np.arange(0, 18.5, 0.5)
    a = a.assign(db=pd.cut(a["dist_thr_nm"], bins))
    prof = a.groupby("db", observed=True)["altitude"].median()
    xd = np.array([iv.mid for iv in prof.index]); ymed = prof.values

    d = np.linspace(0, 17, 200)
    h30, h33 = glide(3.0, d), glide(3.3, d)
    b30, b33 = glide(3.0, VDIST), glide(3.3, VDIST)
    p30, med = pct_below(a, b30); p33, _ = pct_below(a, b33)

    fig, axes = plt.subplots(1, 3, figsize=(18, 6.2), sharey=True, sharex=True)
    panels = [
        ("Today: how they actually descend", None, None, None,
         f"Typical height over the village today: about {med:,.0f} ft,\nwith many levelling off (the flat shelf) instead of gliding."),
        (f"A 3.0° continuous glide", 3.0, b30, p30,
         f"A steady 3.0° glide would cross Brockenhurst at ~{b30:,.0f} ft.\nToday {p30:.0f}% of flights are LOWER than this."),
        (f"A 3.3° continuous glide (achievable)", 3.3, b33, p33,
         f"A 3.3° glide would cross at ~{b33:,.0f} ft.\nToday {p33:.0f}% of flights are LOWER than this."),
    ]
    for ax, (title, deg, bh, pc, note) in zip(axes, panels):
        # faint real data cloud on every panel
        ax.scatter(a["dist_thr_nm"], a["altitude"], s=3, color="#9aa7d0", alpha=0.06, zorder=1)
        # today's median descent line on every panel (grey, dashed on ideal panels)
        ax.plot(xd, ymed, color="#444", lw=2.2 if deg is None else 1.6,
                ls="-" if deg is None else "--", zorder=4,
                label="today's typical descent")
        if deg is not None:
            ax.plot(d, glide(deg, d), color="#1a9850", lw=2.6, zorder=5,
                    label=f"{deg:.1f}° continuous glide")
            ax.plot([VDIST], [bh], "o", color="#1a9850", ms=8, zorder=6)
        # Brockenhurst marker
        ax.axvline(VDIST, color="#c0392b", lw=1.2, ls=":", zorder=3)
        ax.annotate("Brockenhurst\n(9.7 NM out)", (VDIST, 6200), color="#c0392b",
                    fontsize=8.5, ha="center", va="top", fontweight="bold")
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_xlabel("miles from the runway  (airport on the right)", fontsize=9)
        ax.set_xlim(17, 0); ax.set_ylim(0, 6500)
        ax.grid(alpha=0.25)
        ax.text(0.5, -0.20, note, transform=ax.transAxes, ha="center", va="top", fontsize=8.7, color="#333")
        ax.legend(loc="upper right", fontsize=8.5, framealpha=0.9)
    axes[0].set_ylabel("height above sea level (ft)", fontsize=9.5)
    fig.suptitle("Option A: fly the quiet glide the rules already ask for — today vs a 3.0° and 3.3° continuous descent",
                 fontsize=14, fontweight="bold", y=1.0)
    fig.text(0.5, 0.005, "Each faint dot is one recorded aircraft position (runway-26 large-jet arrivals, 2023-2025, via OPDI / OpenSky). "
                         "A continuous glide keeps aircraft higher over the village and removes the level-offs that cause the noise.",
             ha="center", fontsize=8.5, color="#555")
    fig.tight_layout(rect=[0, 0.10, 1, 0.96])
    fig.savefig(out, dpi=145, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out} | 3.0deg={b30:,.0f}ft ({p30:.0f}% below) | 3.3deg={b33:,.0f}ft ({p33:.0f}% below) | median today={med:,.0f}ft")
    return out


if __name__ == "__main__":
    build()
