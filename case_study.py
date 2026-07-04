#!/usr/bin/env python3
"""
Build a single-flight case-study figure: the approach ground track over
Brockenhurst plus the altitude profile, both from the aircraft's own recorded
ADS-B points (OPDI flight events).

    python case_study.py            # defaults to the EXS3618 example below

The default flight is chosen because it is a recent (Oct 2025) night arrival that
levelled off almost exactly over the village; to feature a different flight, pass
its OPDI flight_id and label.
"""
from __future__ import annotations

import argparse
import glob

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config
from brockenhurst import approach, charts
from brockenhurst import geometry as geo

BG, FG, GRID = charts.BG, charts.FG, charts.GRID
BLUE, GOLD, RED = charts.BLUE, charts.GOLD, charts.RED


def load_track(flight_id: int) -> pd.DataFrame:
    ev = pd.concat([pd.read_parquet(f) for f in glob.glob("data/eghh_events_*.parquet")],
                   ignore_index=True)
    ev["flight_id"] = ev["flight_id"].astype("uint64")
    e = ev[ev["flight_id"] == np.uint64(flight_id)].copy()
    return approach.annotate(e).sort_values("event_time")


def figure(track: pd.DataFrame, callsign: str, when_local: str, origin: str,
           gate_ft: float, out: str):
    # Approach portion for the map: within 34 NM, sensible altitudes.
    ap = track[(track["dist_thr_nm"] <= 34) & (track["altitude"].between(0, 8000))].copy()
    ap = ap.sort_values("dist_thr_nm", ascending=False)

    fig = plt.figure(figsize=(9.2, 10.6), facecolor=BG)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.15, 1], hspace=0.22)

    # ---- Panel 1: ground track (map) ----
    ax = fig.add_subplot(gs[0]); ax.set_facecolor(BG)
    b_lat, b_lon = config.BROCKENHURST
    a_lat, a_lon = config.RWY26_THRESHOLD
    # extended runway-26 approach centreline, out to 22 NM
    L = 22 * geo.KM_PER_NM / 111.0
    brg = np.radians(config.RWY26_OUTBOUND_TRACK_DEG)
    c_lat = a_lat + L * np.cos(brg)
    c_lon = a_lon + L * np.sin(brg) / np.cos(np.radians(a_lat))
    ax.plot([a_lon, c_lon], [a_lat, c_lat], color=GRID, lw=8, alpha=0.5,
            solid_capstyle="round", zorder=1, label="Runway-26 approach corridor")

    # flight path
    ax.plot(ap["longitude"], ap["latitude"], color=BLUE, lw=1.6, alpha=0.7, zorder=2)
    sc = ax.scatter(ap["longitude"], ap["latitude"], c=ap["altitude"], cmap="viridis",
                    s=55, zorder=3, edgecolors=BG, linewidths=0.5, vmin=0, vmax=5000)
    # Label points, but skip any within ~1.5 km of an already-labelled one so the
    # near-duplicate points in each level segment don't overprint.
    last = None
    for _, r in ap.iterrows():
        if last is not None and geo.haversine_km(r["latitude"], r["longitude"], *last) < 4.5:
            continue
        ax.annotate(f"{r['altitude']:,.0f} ft", (r["longitude"], r["latitude"]),
                    textcoords="offset points", xytext=(6, -12), color=FG, fontsize=8.5)
        last = (r["latitude"], r["longitude"])

    ax.scatter([a_lon], [a_lat], marker="*", s=260, color=GOLD, edgecolors="k",
               zorder=5)
    ax.annotate("Bournemouth Airport", (a_lon, a_lat), textcoords="offset points",
                xytext=(8, -12), color=FG, fontsize=9, fontweight="bold")
    ax.scatter([b_lon], [b_lat], marker="^", s=150, color=RED, edgecolors="k", zorder=5)
    ax.annotate("BROCKENHURST", (b_lon, b_lat), textcoords="offset points",
                xytext=(8, 8), color=RED, fontsize=10, fontweight="bold")
    # 3 km ring around the village
    th = np.linspace(0, 2 * np.pi, 100)
    ax.plot(b_lon + (3 / (111 * np.cos(np.radians(b_lat)))) * np.cos(th),
            b_lat + (3 / 111.0) * np.sin(th), color=RED, lw=0.8, ls=":", alpha=0.7)

    ax.set_aspect(1 / np.cos(np.radians(b_lat)))
    for s in ax.spines.values():
        s.set_color(GRID)
    ax.tick_params(colors=FG, labelsize=8)
    ax.set_xlabel("Longitude", color=FG); ax.set_ylabel("Latitude", color=FG)
    ax.set_title(f"{callsign}  ·  {origin} → Bournemouth  ·  {when_local}\n"
                 f"Ground track over Brockenhurst (dots = the aircraft's own reported points)",
                 color=FG, fontsize=12)
    ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=FG, fontsize=8, loc="upper left")
    cb = fig.colorbar(sc, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("height (ft)", color=FG); cb.ax.yaxis.set_tick_params(color=FG)
    plt.setp(cb.ax.get_yticklabels(), color=FG)

    # ---- Panel 2: FULL descent profile, top of descent to touchdown ----
    # include the near-runway touchdown points (their barometric altitude dips
    # slightly negative) so the profile runs all the way to landing; clip at 0 ft.
    prof = track[(track["altitude"].between(-600, 11000)) & (track["dist_thr_nm"] <= 55)].copy()
    prof = prof.sort_values("dist_thr_nm", ascending=False)
    prof["altitude"] = prof["altitude"].clip(lower=config.EGHH_ELEV_FT)
    top = prof.iloc[0]
    ax2 = fig.add_subplot(gs[1]); ax2.set_facecolor(BG)
    ax2.plot(prof["dist_thr_nm"], prof["altitude"], color=BLUE, lw=1.8, marker="o",
             markersize=6, markeredgecolor=BG, zorder=3, label="this flight (its own reported points)")
    # the quiet 3-degree descent, drawn where it is the relevant benchmark (last ~18 NM)
    x = np.linspace(0, 18, 100)
    ax2.plot(x, geo.glideslope_altitude_ft(x), color=GOLD, lw=2.2,
             label="quiet 3° continuous descent (should be here)")
    ax2.axhline(config.HARD_FLOOR_FT, color=RED, lw=1.6, ls="--",
                label=f"{config.HARD_FLOOR_FT:,} ft — airport's own minimum")
    # highlight the level-off segments (level-start -> level-end pairs)
    seg_start = None
    labelled = False
    for _, r in prof.iterrows():
        if r["type"] == "level-start":
            seg_start = r
        elif r["type"] == "level-end" and seg_start is not None:
            ax2.plot([seg_start["dist_thr_nm"], r["dist_thr_nm"]],
                     [seg_start["altitude"], r["altitude"]], color=RED, lw=5,
                     alpha=0.65, solid_capstyle="round", zorder=4,
                     label="levelled off (engines up = noise)" if not labelled else None)
            labelled = True
            seg_start = None
    d_brock = geo.dist_from_threshold_nm(*config.BROCKENHURST)
    quiet_here = geo.glideslope_altitude_ft(d_brock)
    ax2.axvline(d_brock, color=FG, lw=1, ls=":", alpha=0.85)
    ax2.annotate(f"over Brockenhurst\n{gate_ft:,.0f} ft — levelled off\n"
                 f"(~{quiet_here - gate_ft:,.0f} ft below a quiet descent)",
                 (d_brock, gate_ft), textcoords="offset points", xytext=(20, 34),
                 color=RED, fontsize=9, fontweight="bold",
                 arrowprops=dict(arrowstyle="->", color=RED))
    ax2.annotate("lands", (0, config.EGHH_ELEV_FT), textcoords="offset points",
                 xytext=(2, 16), color=GOLD, fontsize=9, fontweight="bold")
    for s in ax2.spines.values():
        s.set_color(GRID)
    ax2.tick_params(colors=FG); ax2.grid(True, color=GRID, lw=0.5, alpha=0.6)
    ax2.set_xlim(max(50, top["dist_thr_nm"] + 2), -1.5); ax2.set_ylim(0, 11000)
    ax2.set_xlabel("Distance from the airport (nautical miles) — airport on the right", color=FG)
    ax2.set_ylabel("Height above sea level (ft)", color=FG)
    ax2.set_title("The full descent into Bournemouth — a stepped, engine-on approach with two level-offs",
                  color=FG, fontsize=11.5)
    ax2.legend(facecolor=BG, edgecolor=GRID, labelcolor=FG, fontsize=8.5, loc="upper right")

    fig.savefig(out, dpi=140, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--flight-id", type=int, default=12760204430688483207)
    ap.add_argument("--callsign", default="EXS3618 (Jet2)")
    ap.add_argument("--when", default="12 Oct 2025, 23:28 local (night)")
    ap.add_argument("--origin", default="Dalaman")
    ap.add_argument("--gate-ft", type=float, default=2025)
    ap.add_argument("--out", default="outputs/sweep/case_study.png")
    a = ap.parse_args()
    print("wrote", figure(load_track(a.flight_id), a.callsign, a.when, a.origin,
                          a.gate_ft, a.out))
