#!/usr/bin/env python3
"""
Animated map: Bournemouth arrivals streaming in over Brockenhurst across 2023-2025,
each aircraft coloured by height (low = red), leaving a fading trail so the
low-level hotspot builds over the village. Built from the aircraft's own recorded
positions (interpolated between recorded points).

    python animate.py            # full 3 years
    python animate.py --limit 400 --frames 120   # quick test

Output: outputs/sweep/arrivals_animation.gif
"""
from __future__ import annotations

import argparse
import glob

import matplotlib

matplotlib.use("Agg")
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config
from brockenhurst import approach, charts
from brockenhurst import geometry as geo

BG, FG, GRID, RED, GOLD, BLUE = ("#0b0b0f", charts.FG, charts.GRID,
                                 "#e23b3b", "#e0a01f", "#3a86ff")
PROPER, FLOOR = 3116, 2000
L = 16          # frames each flight takes to fly its approach
TRAIL_KEEP = 60  # how many recent flight-trails to keep on screen


def alt_color(a):
    if a < FLOOR:
        return RED
    if a < PROPER:
        return GOLD
    return BLUE


def load_flights(limit=None):
    ev = pd.concat([pd.read_parquet(f) for f in glob.glob("data/eghh_events_*.parquet")],
                   ignore_index=True)
    ev["flight_id"] = ev["flight_id"].astype("uint64")
    arr = pd.read_csv("outputs/sweep/arrivals.csv"); arr["flight_id"] = arr["id"].astype("uint64")
    lj = set(arr[arr["category"] == "Large jet"]["flight_id"])
    a = approach.annotate(ev[ev["flight_id"].isin(lj)])
    a = a[a["in_corridor"] & a["altitude"].between(0, 7000) & a["dist_thr_nm"].between(0, 25)]
    a = a.sort_values(["flight_id", "dist_thr_nm"], ascending=[True, False])

    flights = []
    for fid, g in a.groupby("flight_id"):
        if len(g) < 3:
            continue
        d = g["dist_thr_nm"].values
        # resample evenly along distance (far -> near)
        xs = np.linspace(d.max(), d.min(), L)
        lon = np.interp(xs[::-1], d[::-1], g["longitude"].values[::-1])[::-1]
        lat = np.interp(xs[::-1], d[::-1], g["latitude"].values[::-1])[::-1]
        alt = np.interp(xs[::-1], d[::-1], g["altitude"].values[::-1])[::-1]
        t = pd.to_datetime(g["event_time"]).min()
        # height as it passes the village (nearest point to Brockenhurst)
        over = g.loc[g["d_brock_km"].idxmin()]
        flights.append(dict(t=t, lon=lon, lat=lat, alt=alt,
                            over_alt=float(over["altitude"]),
                            over_d=float(over["d_brock_km"])))
    flights.sort(key=lambda f: f["t"])
    if limit:
        flights = flights[:: max(1, len(flights) // limit)]
    return flights


def _true_low_dates():
    """Real dates of measured airliners that crossed the village below the
    quiet-descent height - used for an accurate cumulative counter regardless
    of how many flights we draw."""
    pf = pd.read_csv("outputs/sweep/per_flight.csv")
    pf = pf[(pf["year"].isin([2023, 2024, 2025])) & (pf["category"] == "Large jet")
            & (pf["gate_alt_ft"].notna()) & (pf["gate_alt_ft"] < PROPER)]
    return np.sort(pd.to_datetime(pf["last_seen"]).values)


def _low_by_year():
    """Per-year sorted dates of measured low airliners, split gold/red, for the
    growing dot-tally."""
    pf = pd.read_csv("outputs/sweep/per_flight.csv")
    pf = pf[(pf["year"].isin([2023, 2024, 2025])) & (pf["category"] == "Large jet")
            & (pf["gate_alt_ft"].notna()) & (pf["gate_alt_ft"] < PROPER)].copy()
    pf["dt"] = pd.to_datetime(pf["last_seen"]).values
    out = {}
    for y in (2023, 2024, 2025):
        yy = pf[pf["year"] == y]
        out[y] = dict(gold=np.sort(yy[yy["gate_alt_ft"] >= FLOOR]["dt"].values),
                      red=np.sort(yy[yy["gate_alt_ft"] < FLOOR]["dt"].values))
    return out


def build(out="outputs/sweep/arrivals_animation.gif", limit=None, frames=320, fps=12):
    flights = load_flights(limit)
    n = len(flights)
    low_dates = _true_low_dates()
    by_year = _low_by_year()
    t0, t1 = flights[0]["t"], flights[-1]["t"]
    span = (t1 - t0).total_seconds() or 1
    release = frames - L
    for f in flights:
        f["start"] = int(((f["t"] - t0).total_seconds() / span) * release)

    fig, ax = plt.subplots(figsize=(9.2, 6.4), facecolor=BG)
    ax.set_facecolor(BG)
    blat, blon = config.BROCKENHURST
    ax.set_xlim(-1.86, -1.36); ax.set_ylim(50.70, 50.90)
    ax.set_aspect(1 / np.cos(np.radians(50.82)))
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color(GRID)
    # landmarks
    ax.scatter([blon], [blat], marker="^", s=130, color=RED, edgecolors="k", zorder=8)
    ax.annotate("BROCKENHURST", (blon, blat), textcoords="offset points", xytext=(9, 6),
                color="white", fontsize=11, fontweight="bold", zorder=8)
    ax.scatter([config.RWY26_THRESHOLD[1]], [config.RWY26_THRESHOLD[0]], marker="*",
               s=200, color=GOLD, edgecolors="k", zorder=8)
    ax.annotate("Bournemouth\nAirport", (config.RWY26_THRESHOLD[1], config.RWY26_THRESHOLD[0]),
                textcoords="offset points", xytext=(6, -22), color=FG, fontsize=8, zorder=8)
    th = np.linspace(0, 2 * np.pi, 80)
    ax.plot(blon + (3 / (111 * np.cos(np.radians(blat)))) * np.cos(th),
            blat + (3 / 111.0) * np.sin(th), color=RED, lw=0.8, ls=":", alpha=0.6)

    ax.set_title("Three years of arrivals over Brockenhurst\n"
                 "each streak is a plane · red = below 2,000 ft · gold = below a quiet descent",
                 color=FG, fontsize=12)
    date_txt = ax.text(0.015, 0.965, "", transform=ax.transAxes, color=FG,
                       fontsize=14, fontweight="bold", va="top")
    count_txt = ax.text(0.015, 0.905, "", transform=ax.transAxes, color="#ff6b6b",
                        fontsize=10.5, fontweight="bold", va="top")

    # --- top-right growing dot-tally: low airliners per year ---
    DOTV, NCOL, dx, gap = 15, 4, 1.0, 1.8   # 1 dot = DOTV flights
    years = [2023, 2024, 2025]
    year_x0 = {y: i * (NCOL * dx + gap) for i, y in enumerate(years)}
    ax2 = fig.add_axes([0.675, 0.45, 0.305, 0.32])
    ax2.set_facecolor((0, 0, 0, 0.35))
    ax2.set_xlim(-0.8, max(year_x0.values()) + NCOL * dx)
    ax2.set_ylim(-1.6, 13)
    ax2.set_xticks([]); ax2.set_yticks([])
    for sp in ax2.spines.values():
        sp.set_color(GRID)
    ax2.text(0.5, 1.02, "airliners low over the village, per year",
             transform=ax2.transAxes, ha="center", va="bottom", color=FG, fontsize=8)
    for y in years:
        ax2.text(year_x0[y] + (NCOL * dx) / 2 - dx / 2, -1.5, str(y),
                 ha="center", va="bottom", color=FG, fontsize=8.5, fontweight="bold")
    ax2.text(0.5, -0.14, "each dot = 15 flights", transform=ax2.transAxes,
             ha="center", va="top", color="#9a9aa2", fontsize=6.5)
    tally = ax2.scatter([], [], s=16, zorder=5)
    ytxt = {y: ax2.text(year_x0[y] + (NCOL * dx) / 2 - dx / 2, 12.4, "",
                        ha="center", va="top", color=FG, fontsize=7.5, fontweight="bold")
            for y in years}

    trail_lines, dot = [], ax.scatter([], [], s=0)
    # precompute per-frame active flights
    active_by_frame = {fr: [] for fr in range(frames)}
    for idx, f in enumerate(flights):
        for k in range(L):
            fr = f["start"] + k
            if 0 <= fr < frames:
                active_by_frame[fr].append((idx, k))

    def update(fr):
        nonlocal trail_lines
        # newly-completed flights add a faded trail coloured by over-village height
        for idx, f in enumerate(flights):
            if f["start"] + L - 1 == fr:
                col = alt_color(f["over_alt"])
                ln, = ax.plot(f["lon"], f["lat"], color=col, lw=1.0,
                              alpha=0.28 if col != RED else 0.5, zorder=3)
                trail_lines.append((ln, col))
        # cap trails
        while len(trail_lines) > TRAIL_KEEP:
            old, _ = trail_lines.pop(0)
            old.remove()
        # fade existing trails
        for ln, col in trail_lines:
            ln.set_alpha(max(0.05, ln.get_alpha() * 0.97))
        # moving dots for in-flight aircraft
        xs, ys, cs = [], [], []
        for idx, k in active_by_frame.get(fr, []):
            f = flights[idx]
            xs.append(f["lon"][k]); ys.append(f["lat"][k]); cs.append(alt_color(f["alt"][k]))
        dot.set_offsets(np.c_[xs, ys] if xs else np.empty((0, 2)))
        dot.set_color(cs if cs else "none")
        dot.set_sizes([26] * len(xs))
        dot.set_zorder(6)
        # date + counter
        frac = fr / max(1, release)
        cur = t0 + (t1 - t0) * min(1.0, frac)
        cur = min(cur, pd.Timestamp("2025-12-31"))   # this is a 2023-2025 story
        date_txt.set_text(cur.strftime("%b %Y"))
        so_far = int(np.searchsorted(low_dates, np.datetime64(cur), side="right"))
        count_txt.set_text(f"airliners measured low over the village: {so_far:,} (running total)")
        # update the per-year dot tally
        curd = np.datetime64(cur)
        pts, cols = [], []
        for y in years:
            ng = int(np.searchsorted(by_year[y]["gold"], curd, side="right"))
            nr = int(np.searchsorted(by_year[y]["red"], curd, side="right"))
            ndg, ndr = ng // DOTV, nr // DOTV
            for i in range(ndg + ndr):
                row, col = divmod(i, NCOL)
                pts.append((year_x0[y] + col * dx, row * 1.0))
                cols.append(GOLD if i < ndg else RED)
            ytxt[y].set_text(f"{ng + nr}" if (ng + nr) else "")
        tally.set_offsets(np.array(pts) if pts else np.empty((0, 2)))
        tally.set_color(cols if cols else "none")
        return [dot, date_txt, count_txt, tally]

    print(f"animating {n} flights over {frames} frames ...", flush=True)
    anim = animation.FuncAnimation(fig, update, frames=frames, interval=1000 / fps, blit=False)
    anim.save(out, writer=animation.PillowWriter(fps=fps), dpi=85)
    plt.close(fig)
    print("wrote", out, "| flights:", n)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--frames", type=int, default=320)
    ap.add_argument("--fps", type=int, default=12)
    ap.add_argument("--out", default="outputs/sweep/arrivals_animation.gif")
    a = ap.parse_args()
    build(a.out, a.limit, a.frames, a.fps)
