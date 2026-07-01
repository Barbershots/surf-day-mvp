#!/usr/bin/env python3
"""
Phone-friendly (portrait) version of the year-by-year descent-profile graph, for
sharing inline on WhatsApp. Stacks 2023/2024/2025 vertically with large, legible
text. Airliners only by default.

    python whatsapp_image.py   ->  outputs/sweep/descent_whatsapp.png
"""
from __future__ import annotations

import glob

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config
from brockenhurst import charts, report
from brockenhurst import geometry as geo

BG, FG, GRID, BLUE, GOLD, RED = (charts.BG, charts.FG, charts.GRID,
                                 charts.BLUE, charts.GOLD, charts.RED)


def load_profile():
    ev = pd.concat([pd.read_parquet(f) for f in glob.glob("data/eghh_events_*.parquet")],
                   ignore_index=True)
    ev["flight_id"] = ev["flight_id"].astype("uint64")
    arr = pd.read_csv("outputs/sweep/arrivals.csv")
    arr["flight_id"] = arr["id"].astype("uint64")
    arr["year"] = pd.to_datetime(arr["dof"]).dt.year
    ev = ev.merge(arr[["flight_id", "category", "year"]], on="flight_id", how="left")
    return report._profile_frame(ev, [2023, 2024, 2025])


def build(out="outputs/sweep/descent_whatsapp.png", large_jet_only=True):
    d = load_profile()
    if large_jet_only:
        d = d[d["category"] == "Large jet"]
    years = [2023, 2024, 2025]
    d_brock = geo.dist_from_threshold_nm(*config.BROCKENHURST)
    x = np.linspace(0, 18, 120)

    fig = plt.figure(figsize=(7.6, 13.0), facecolor=BG)
    gs = fig.add_gridspec(3, 1, left=0.12, right=0.96, top=0.885, bottom=0.16, hspace=0.30)

    who = "Airliners" if large_jet_only else "Arrivals"
    fig.text(0.5, 0.965, f"{who} over Brockenhurst are", ha="center", color=FG,
             fontsize=22, fontweight="bold")
    fig.text(0.5, 0.94, "flying below the quiet descent", ha="center", color=FG,
             fontsize=22, fontweight="bold")
    fig.text(0.5, 0.915, "and lower, and more of them, each year (2023–2025)",
             ha="center", color="#c9a24b", fontsize=13)

    for row, yr in enumerate(years):
        ax = fig.add_subplot(gs[row])
        ax.set_facecolor(BG)
        dd = d[d["year"] == yr]
        ax.scatter(dd["dist_thr_nm"], dd["altitude"], s=6, alpha=0.16,
                   color=BLUE, edgecolors="none")
        ax.plot(x, geo.glideslope_altitude_ft(x), color=GOLD, lw=2.6)
        ax.axhline(config.HARD_FLOOR_FT, color=RED, lw=1.8, ls="--")
        ax.axvline(d_brock, color=FG, lw=1, ls=":", alpha=0.8)

        zone = dd[dd["dist_thr_nm"].between(8, 12)]
        pct = (zone["altitude"] < zone["cda_profile_ft"]).mean() * 100 if len(zone) else 0
        n = zone["flight_id"].nunique()
        avg = zone["altitude"].mean() if len(zone) else 0
        ax.text(0.035, 0.93, str(yr), transform=ax.transAxes, ha="left", va="top",
                color=FG, fontsize=20, fontweight="bold")
        ax.text(0.035, 0.72, f"{pct:.0f}% below the\nquiet-descent line",
                transform=ax.transAxes, ha="left", va="top",
                color="#f0c96b", fontsize=13, fontweight="bold")
        ax.text(0.97, 0.93, f"{n:,} aircraft\navg {avg:,.0f} ft",
                transform=ax.transAxes, ha="right", va="top",
                color=FG, fontsize=12.5, fontweight="bold")
        ax.text(d_brock, 7550, "Brockenhurst", color=FG, fontsize=9,
                rotation=90, ha="center", va="top", alpha=0.9)

        for s in ax.spines.values():
            s.set_color(GRID)
        ax.tick_params(colors=FG, labelsize=10)
        ax.grid(True, color=GRID, lw=0.5, alpha=0.5)
        ax.set_ylim(0, 8000); ax.set_xlim(18, 0)
        ax.set_ylabel("height (ft)", color=FG, fontsize=11)
        if row == 2:
            ax.set_xlabel("nautical miles from the airport", color=FG, fontsize=11)

    # plain-language legend at the bottom
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=BLUE, markersize=8,
               label="each dot = one aircraft"),
        Line2D([0], [0], color=GOLD, lw=2.6, label="where a quiet glide-down should be"),
        Line2D([0], [0], color=RED, lw=1.8, ls="--", label="2,000 ft — airport's own minimum"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=1, facecolor=BG,
               edgecolor=GRID, labelcolor=FG, fontsize=10.5, bbox_to_anchor=(0.5, 0.045))
    fig.text(0.5, 0.02, "Source: aircraft's own GPS/ADS-B via OPDI/OpenSky · public data",
             ha="center", color="#8a8a90", fontsize=8)
    fig.savefig(out, dpi=150, facecolor=BG)
    plt.close(fig)
    print("wrote", out)
    return out


if __name__ == "__main__":
    build()
