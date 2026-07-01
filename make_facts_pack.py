#!/usr/bin/env python3
"""
Build the "facts only" pack: analysis restricted to flights with a DIRECTLY
MEASURED height over Brockenhurst (no inference), plus a single-flight case
study. Writes FACTS_AND_CASE_STUDY.md and renders it to a PDF.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import case_study as CS
import md_to_pdf
from brockenhurst import charts

PROPER, FLOOR = 3116, 2000
SWEEP = "outputs/sweep"


def facts_hist(g_lj, path):
    night = g_lj[g_lj["time_window"] == "Night"]["gate_alt_ft"]
    fig, ax = plt.subplots(figsize=(10, 5.4), facecolor=charts.BG)
    bins = np.arange(0, max(4500, g_lj["gate_alt_ft"].max() + 250), 250)
    ax.hist(g_lj["gate_alt_ft"], bins=bins, color=charts.BLUE, edgecolor=charts.BG,
            label=f"all large jets ({len(g_lj):,})")
    ax.hist(night, bins=bins, color=charts.RED, edgecolor=charts.BG, alpha=0.9,
            label=f"of which at night ({len(night)})")
    ax.axvline(FLOOR, color=charts.FG, lw=2, ls="--", label=f"{FLOOR:,} ft — airport minimum")
    ax.axvline(PROPER, color=charts.GOLD, lw=2, label=f"~{PROPER:,} ft — quiet-descent height")
    charts._style(ax)
    ax.set_xlabel("Measured height directly over Brockenhurst (ft)")
    ax.set_ylabel("Number of large jets")
    ax.set_title("Measured height over Brockenhurst — large jets only, directly recorded",
                 color=charts.FG)
    ax.set_xlim(0, 6000)
    ax.legend(facecolor=charts.BG, edgecolor=charts.GRID, labelcolor=charts.FG, fontsize=9)
    fig.tight_layout(); fig.savefig(path, dpi=135, facecolor=charts.BG); plt.close(fig)


def stats_block(g, label):
    n = len(g)
    med = g["gate_alt_ft"].median()
    bp = (g["gate_alt_ft"] < PROPER).sum()
    bf = (g["gate_alt_ft"] < FLOOR).sum()
    return (f"| {label} | {n:,} | {med:,.0f} ft | {bp:,} ({100*bp/n:.0f}%) | "
            f"{bf:,} ({100*bf/n:.0f}%) |")


def main():
    pf = pd.read_csv(f"{SWEEP}/per_flight.csv")
    pf = pf[pf["year"].isin([2023, 2024, 2025])]
    g = pf[pf["gate_alt_ft"].notna()].copy()
    g_lj = g[g["category"] == "Large jet"]
    g_ljn = g_lj[g_lj["time_window"] == "Night"]

    facts_hist(g_lj, f"{SWEEP}/facts_large_jets_hist.png")
    CS.figure(CS.load_track(12760204430688483207), "EXS3618 (Jet2)",
              "12 Oct 2025, 23:28 local (night)", "Dalaman", 2025,
              f"{SWEEP}/case_study.png")

    by_year = (g_ljn.groupby("year")["gate_alt_ft"]
               .agg(n="size", median="median").round(0).astype(int))
    yr_rows = "\n".join(
        f"| {y} | {r['n']} | {r['median']:,} ft | "
        f"{(g_ljn[(g_ljn.year==y)]['gate_alt_ft']<FLOOR).sum()} |"
        for y, r in by_year.iterrows())

    md = f"""# Facts-only analysis & a worked example

This companion uses **only** flights for which we have a **directly measured
height as the aircraft passed over Brockenhurst** — no estimation, no inference.
It is the ~1-in-6 subset described in `DATA_AND_DEFINITIONS.md`. Every number
below is a recorded altitude from the aircraft's own broadcast.

## 1. Measured heights over Brockenhurst, 2023–2025

| Group | Measured | Median | Below ~{PROPER:,} ft | Below 2,000 ft |
|---|---|---|---|---|
{stats_block(g, "All arrivals")}
{stats_block(g_lj, "Large passenger jets")}
{stats_block(g_ljn, "Large jets at night (23:00–06:00)")}

Read the large-jet row: of **{len(g_lj):,}** airliners with a directly measured
height over the village, **{(g_lj['gate_alt_ft']<PROPER).sum():,}** were lower
than a quiet continuous descent would put them, and
**{(g_lj['gate_alt_ft']<FLOOR).sum():,}** were below the airport's own 2,000 ft
minimum — all measured, none inferred.

![Measured large-jet heights over Brockenhurst]({SWEEP}/facts_large_jets_hist.png)

### Night airliners, measured, year by year

| Year | Measured | Median | Below 2,000 ft |
|---|---|---|---|
{yr_rows}

## 2. Worked example — a recent night flight

**EXS3618 (Jet2), Dalaman → Bournemouth, night of 12 October 2025.** The aircraft
levelled off at about **2,050 ft directly over Brockenhurst** at **23:28 local**
— roughly **1,050 ft below** where a quiet continuous descent would have it, and
right on the airport's own 2,000 ft minimum. Moments earlier it had also levelled
at ~3,500 ft: a stepped, non-continuous descent rather than a steady glide. Both
the ground track and the height profile below are built purely from the
aircraft's own recorded positions.

![Case study: EXS3618 over Brockenhurst]({SWEEP}/case_study.png)

*This single flight is an illustration, not the argument on its own — the case is
the consistent pattern across thousands of flights in Section 1. Method, sources
and definitions: DATA_AND_DEFINITIONS.md and METHODOLOGY.md.*
"""
    with open("FACTS_AND_CASE_STUDY.md", "w") as f:
        f.write(md)
    md_to_pdf.render("FACTS_AND_CASE_STUDY.md", "outputs/facts_and_case_study.pdf")
    print("wrote FACTS_AND_CASE_STUDY.md and outputs/facts_and_case_study.pdf")


if __name__ == "__main__":
    main()
