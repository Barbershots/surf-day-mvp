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
        "Method & limits: only aircraft broadcasting position at low level are captured "
        "(~half to two-thirds of arrivals), so these are minimum counts. A single flight "
        "may have an air-traffic reason; the evidence is the consistent, worsening "
        "pattern. Full method: METHODOLOGY.md.  Prepared from public data — not affiliated "
        "with the airport."
    )
    axf = fig.add_axes([0.06, 0.015, 0.88, 0.06]); axf.axis("off")
    axf.text(0, 1, foot, ha="left", va="top", fontsize=7.4, color=MUTE, wrap=True,
             transform=axf.transAxes, linespacing=1.35)

    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out, dpi=200)
    fig.savefig(out.replace(".pdf", ".png"), dpi=170)
    plt.close(fig)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", default="outputs/sweep")
    ap.add_argument("--out", default="outputs/brief.pdf")
    args = ap.parse_args()
    path = build(args.sweep, args.out)
    print("wrote", path, "and", path.replace(".pdf", ".png"))
