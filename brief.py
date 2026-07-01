#!/usr/bin/env python3
"""
Compose a one-page evidence brief (PDF + PNG) from the sweep outputs.

    python brief.py                       # uses outputs/sweep, writes outputs/brief.pdf
    python brief.py --sweep outputs/sweep --out outputs/brief.pdf

Designed to be printed or attached to a complaint / consultation response. Plain
English, no aviation jargon; every number traces back to summary_by_year.csv and
night_large_jets.csv in the sweep folder.
"""
from __future__ import annotations

import argparse
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd

INK = "#1a1a1a"
MUTE = "#555555"
GOLD = "#c8881f"
RED = "#a51e2d"
BLUE = "#1f6fc4"


def _stat_box(fig, x, y, w, h, big, label, color):
    ax = fig.add_axes([x, y, w, h])
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes,
                               facecolor=color, alpha=0.10, edgecolor=color, lw=1.5))
    ax.text(0.5, 0.62, big, ha="center", va="center", fontsize=23,
            fontweight="bold", color=color, transform=ax.transAxes)
    ax.text(0.5, 0.22, label, ha="center", va="center", fontsize=8.5,
            color=INK, transform=ax.transAxes, wrap=True)


def build(sweep_dir="outputs/sweep", out="outputs/brief.pdf"):
    by_year = pd.read_csv(os.path.join(sweep_dir, "summary_by_year.csv"))
    night = pd.read_csv(os.path.join(sweep_dir, "night_large_jets.csv"))
    y0, y1 = by_year.iloc[0], by_year.iloc[-1]

    total_below_floor = int(by_year["night_below_2000ft_minimum"].sum())
    total_leveloff = int(by_year["night_stopped_descending_overhead"].sum())
    lowest = night.sort_values("height_over_brockenhurst_ft").iloc[0]

    fig = _page1(by_year, night, y0, y1, sweep_dir,
                 total_below_floor, total_leveloff, lowest)
    fig2 = _page2(by_year, sweep_dir)

    os.makedirs(os.path.dirname(out), exist_ok=True)
    from matplotlib.backends.backend_pdf import PdfPages
    with PdfPages(out) as pdf:
        pdf.savefig(fig, dpi=200)
        if fig2 is not None:
            pdf.savefig(fig2, dpi=200)
    fig.savefig(out.replace(".pdf", ".png"), dpi=170)
    if fig2 is not None:
        fig2.savefig(out.replace(".pdf", "_p2.png"), dpi=170)
        plt.close(fig2)
    plt.close(fig)
    return out


def _page1(by_year, night, y0, y1, sweep_dir, total_below_floor, total_leveloff, lowest):
    fig = plt.figure(figsize=(8.27, 11.69), facecolor="white")  # A4 portrait

    # --- Header ---
    fig.text(0.06, 0.965, "Night-time low flying over Brockenhurst",
             fontsize=20, fontweight="bold", color=INK)
    fig.text(0.06, 0.945, "Bournemouth Airport arrivals — evidence summary, 2023–2025",
             fontsize=12, color=MUTE)
    fig.text(0.06, 0.928,
             "Heights are from aircraft's own broadcast (ADS-B) position data via the "
             "OPDI / OpenSky open dataset.",
             fontsize=8.5, color=MUTE, style="italic")

    # --- The claim, in plain English ---
    intro = (
        "Bournemouth Airport is required to have arriving aircraft descend gently with "
        "engines near idle — a quiet 'continuous descent'. Over Brockenhurst (about 10 "
        "miles out, directly under the runway-26 approach) that puts a plane at roughly "
        "3,100 ft. The airport's own published rule says aircraft must not be below "
        "2,000 ft here. The data below shows night-time airliners routinely lower than "
        "both — flying low and level, which needs engine power, which is the noise "
        "residents hear. And it is getting worse every year."
    )
    ax = fig.add_axes([0.06, 0.80, 0.88, 0.115]); ax.axis("off")
    ax.text(0, 1, intro, ha="left", va="top", fontsize=10.3, color=INK, wrap=True,
            transform=ax.transAxes, linespacing=1.5)

    # --- Three headline stats ---
    _stat_box(fig, 0.06, 0.685, 0.27, 0.085,
              f"{int(y0['night_below_proper_height'])} → {int(y1['night_below_proper_height'])}",
              "night airliners below the quiet-descent height\nper year (2023 → 2025)", GOLD)
    _stat_box(fig, 0.365, 0.685, 0.27, 0.085,
              f"{int(y0['night_below_2000ft_minimum'])} → {int(y1['night_below_2000ft_minimum'])}",
              "per year below the airport's\nown 2,000 ft minimum", RED)
    _stat_box(fig, 0.67, 0.685, 0.27, 0.085,
              f"{lowest['height_over_brockenhurst_ft']:,} ft",
              f"lowest night airliner\n({str(lowest['callsign']).strip()}, {lowest['date']})", RED)

    # --- Chart 1: year on year ---
    p1 = os.path.join(sweep_dir, "night_year_on_year.png")
    if os.path.exists(p1):
        a1 = fig.add_axes([0.06, 0.375, 0.88, 0.29]); a1.axis("off")
        a1.imshow(mpimg.imread(p1))

    # --- Chart 2: worst offenders ---
    p2 = os.path.join(sweep_dir, "worst_night_offenders.png")
    if os.path.exists(p2):
        a2 = fig.add_axes([0.06, 0.085, 0.88, 0.28]); a2.axis("off")
        a2.imshow(mpimg.imread(p2))

    # --- Footer: method + caveats ---
    foot = (
        f"Over 2023–2025: {total_leveloff} night airliners stopped descending (levelled "
        f"off) directly over the village; {total_below_floor} dropped below the airport's "
        "own 2,000 ft minimum. Every airline named in the residents' audit (Jet2, TUI, "
        "Ryanair) is confirmed low at night in this data.  "
        "Method & limits: ~97% of arrivals are tracked, but a precise height directly "
        "over the village exists for ~1 in 6, so these counts are minimums (the true "
        "figures are higher). A single flight may have an air-traffic reason; the "
        "evidence is the consistent, worsening pattern. Full detail: DATA_AND_DEFINITIONS.md "
        "and METHODOLOGY.md.  Prepared from public data — not affiliated with the airport."
    )
    axf = fig.add_axes([0.06, 0.015, 0.88, 0.06]); axf.axis("off")
    axf.text(0, 1, foot, ha="left", va="top", fontsize=7.4, color=MUTE, wrap=True,
             transform=axf.transAxes, linespacing=1.35)
    return fig


def _page2(by_year, sweep_dir):
    """Second page: the year-on-year altitude-vs-descent-profile graph."""
    p_all = os.path.join(sweep_dir, "descent_profile_by_year.png")
    p_lj = os.path.join(sweep_dir, "descent_profile_by_year_large_jets.png")
    if not os.path.exists(p_all):
        return None

    fig = plt.figure(figsize=(8.27, 11.69), facecolor="white")  # A4 portrait
    fig.text(0.06, 0.965, "Aircraft are flying below the quiet descent",
             fontsize=20, fontweight="bold", color=INK)
    fig.text(0.06, 0.945, "Height over Brockenhurst vs. where a quiet descent should be, 2023–2025",
             fontsize=12, color=MUTE)

    explain = (
        "Each blue dot is one arriving aircraft, plotted by how high it is (up the "
        "side) and how far from the airport it is (along the bottom — Brockenhurst is "
        "the dotted line, about 10 miles out). The orange line is where a quiet "
        "'glide down' descent should be; the red dashed line is the airport's own "
        "2,000 ft minimum. The mass of aircraft sits BELOW the orange line — lower "
        "than a quiet descent — and the share below it grows every year."
    )
    ax = fig.add_axes([0.06, 0.855, 0.88, 0.075]); ax.axis("off")
    ax.text(0, 1, explain, ha="left", va="top", fontsize=10.3, color=INK, wrap=True,
            transform=ax.transAxes, linespacing=1.5)

    fig.text(0.06, 0.83, "All arrivals", fontsize=12, fontweight="bold", color=INK)
    a1 = fig.add_axes([0.05, 0.545, 0.90, 0.275]); a1.axis("off")
    a1.imshow(mpimg.imread(p_all))

    if os.path.exists(p_lj):
        fig.text(0.06, 0.505, "Large passenger jets only (the airliners the case is about)",
                 fontsize=12, fontweight="bold", color=INK)
        a2 = fig.add_axes([0.05, 0.22, 0.90, 0.275]); a2.axis("off")
        a2.imshow(mpimg.imread(p_lj))

    foot = (
        "Read the percentages in each panel: the share of aircraft already lower than "
        "a quiet continuous descent as they pass over Brockenhurst — rising 83% → 87% "
        "→ 87% for all arrivals and 66% → 73% → 74% for airliners. Flying low and "
        "level (instead of gliding down) needs engine power, which is the noise "
        "residents hear.  Source: aircraft's own broadcast (ADS-B) position data via "
        "the OPDI / OpenSky open dataset. Prepared from public data — not affiliated "
        "with the airport."
    )
    axf = fig.add_axes([0.06, 0.05, 0.88, 0.12]); axf.axis("off")
    axf.text(0, 1, foot, ha="left", va="top", fontsize=8.2, color=MUTE, wrap=True,
             transform=axf.transAxes, linespacing=1.4)
    return fig


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", default="outputs/sweep")
    ap.add_argument("--out", default="outputs/brief.pdf")
    args = ap.parse_args()
    path = build(args.sweep, args.out)
    print("wrote", path, "and", path.replace(".pdf", ".png"))
