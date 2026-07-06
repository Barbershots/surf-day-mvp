#!/usr/bin/env python3
"""
Two-panel chart backing the response to the airport:
  (1) large jets below 2,000 ft over Brockenhurst by year (breach of the blanket
      "not below 2,000 ft QNH before intercepting the glidepath" rule), and
  (2) the share of low crossings that had NO other arrival to sequence against.

    python case_chart.py  ->  outputs/sweep/case_chart.png
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RED, AMBER, BLUE, GREY, INK = "#c0392b", "#e8a020", "#2c6fbb", "#9aa0aa", "#222"


def data():
    arr = pd.read_csv("outputs/sweep/arrivals.csv")
    arr["t"] = pd.to_datetime(arr["last_seen"], errors="coerce").dt.tz_localize("UTC").dt.tz_convert("Europe/London")
    tt = np.sort(arr.dropna(subset=["t"])["t"].values)
    pf = pd.read_csv("outputs/sweep/per_flight.csv")
    pf["t"] = pd.to_datetime(pf["last_seen"], errors="coerce").dt.tz_localize("UTC").dt.tz_convert("Europe/London")
    lj = pf[(pf["category"] == "Large jet") & pf["gate_alt_ft"].notna()
            & (pf["t"].dt.year.isin([2023, 2024, 2025]))].copy()
    lj["year"] = lj["t"].dt.year

    def others(t, m):
        lo = np.datetime64(t) - np.timedelta64(m, "m"); hi = np.datetime64(t) + np.timedelta64(m, "m")
        return int(np.searchsorted(tt, hi, "right") - np.searchsorted(tt, lo, "left") - 1)
    lj["o30"] = [others(t, 30) for t in lj["t"]]
    sub2000 = lj[lj["gate_alt_ft"] < 2000].groupby("year").size().reindex([2023, 2024, 2025], fill_value=0)
    low = lj[lj["gate_alt_ft"] < 3116]
    lone = int((low["o30"] == 0).sum())
    return sub2000, len(low), lone


def build(out="outputs/sweep/case_chart.png"):
    sub2000, n_low, lone = data()
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.4))

    ax = axes[0]
    yrs = [2023, 2024, 2025]; vals = [int(sub2000[y]) for y in yrs]
    bars = ax.bar([str(y) for y in yrs], vals, color=[BLUE, AMBER, RED], width=0.62, zorder=3)
    for y, v in zip(yrs, vals):
        ax.annotate(f"{v}", (str(y), v), xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=13, fontweight="bold", color=INK)
    ax.set_title("Large jets crossing Brockenhurst below 2,000 ft\n"
                 "(breach of the blanket ILS rule, and rising)", fontsize=12, fontweight="bold")
    ax.set_ylabel("large jets below 2,000 ft over the village", fontsize=10)
    ax.set_ylim(0, max(vals) * 1.25)
    ax.grid(axis="y", alpha=0.25, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    ax2 = axes[1]
    other = n_low - lone
    ax2.bar(["Low crossings\nover the village"], [other], color=GREY, width=0.5, label="other traffic within 30 min", zorder=3)
    ax2.bar(["Low crossings\nover the village"], [lone], bottom=[other], color=RED, width=0.5,
            label="NO other arrival within 30 min\n(nothing to sequence)", zorder=3)
    ax2.annotate(f"{lone}\n({lone/n_low*100:.0f}%)", (0, other + lone / 2), ha="center", va="center",
                 fontsize=13, fontweight="bold", color="white")
    ax2.annotate(f"{other}", (0, other / 2), ha="center", va="center", fontsize=12, color="white")
    ax2.set_title("The 'sequencing' excuse fails:\n1 in 4 low crossings had no other traffic to sequence",
                  fontsize=12, fontweight="bold")
    ax2.set_ylabel("large jets below the quiet-descent line over the village", fontsize=10)
    ax2.legend(fontsize=9.5, loc="upper right", framealpha=0.9)
    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)
    ax2.set_xlim(-0.8, 0.8)

    fig.suptitle("Bournemouth arrivals over Brockenhurst: breaches the radar-vectoring defence does not explain",
                 fontsize=13.5, fontweight="bold", y=0.99)
    fig.text(0.5, 0.008, "Large jets with a measured height over the village, 2023-2025, via OPDI / OpenSky. "
             "Counts are minimums (about 1 in 5 measured). 'Other traffic' counts arrivals in our data within 30 minutes.",
             ha="center", fontsize=8.7, color="#555")
    fig.tight_layout(rect=[0, 0.04, 1, 0.95])
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out, "| sub2000:", list(sub2000), "| low:", n_low, "| lone:", lone)
    return out


if __name__ == "__main__":
    build()
