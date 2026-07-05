#!/usr/bin/env python3
"""
When the large jets come over Brockenhurst: by month (seasonality) and by hour of
day (daily profile), from our 2025 arrivals, with the future 3m-passenger scale.

    python flights_profile.py  ->  outputs/sweep/flights_profile.png
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BLUE, RED, AMBER, INK = "#2c6fbb", "#c0392b", "#e8a020", "#222222"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def load(year=2025):
    arr = pd.read_csv("outputs/sweep/arrivals.csv")
    arr["t"] = pd.to_datetime(arr["last_seen"], errors="coerce")
    arr = arr.dropna(subset=["t"])
    arr["t"] = arr["t"].dt.tz_localize("UTC").dt.tz_convert("Europe/London")
    arr = arr[(arr["t"].dt.year == year) & (arr["category"] == "Large jet")].copy()
    arr["month"] = arr["t"].dt.month; arr["hour"] = arr["t"].dt.hour
    return arr


def build(out="outputs/sweep/flights_profile.png", year=2025):
    a = load(year)
    fig, axes = plt.subplots(1, 2, figsize=(16, 6.2))

    # ---- seasonality by month ----
    mc = a.groupby("month").size().reindex(range(1, 13), fill_value=0)
    ax = axes[0]
    bars = ax.bar(range(1, 13), mc.values, color=BLUE, width=0.7, zorder=3)
    for m in (7, 8):
        bars[m - 1].set_color(RED)
    ax.set_xticks(range(1, 13)); ax.set_xticklabels(MONTHS, fontsize=9)
    ax.set_ylabel("Large-jet arrivals over Brockenhurst", fontsize=10)
    ax.set_title("It is seasonal: summer is roughly 3x January", fontsize=12, fontweight="bold")
    for m, v in mc.items():
        ax.annotate(f"{v}", (m, v), xytext=(0, 3), textcoords="offset points",
                    ha="center", fontsize=8, color=INK)
    ax.grid(axis="y", alpha=0.25, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    # ---- daily profile by hour (per day average in the summer peak) ----
    summer = a[a["month"].isin([7, 8])]
    days = max(1, summer["t"].dt.date.nunique())
    hc = summer.groupby("hour").size().reindex(range(0, 24), fill_value=0) / days
    ax2 = axes[1]
    colors = [RED if h >= 23 or h < 6 else BLUE for h in range(24)]
    ax2.bar(range(24), hc.values, color=colors, width=0.85, zorder=3)
    ax2.set_xticks(range(0, 24, 2)); ax2.set_xticklabels([f"{h:02d}" for h in range(0, 24, 2)], fontsize=8.5)
    ax2.set_xlabel("hour of day (local)", fontsize=9.5)
    ax2.set_ylabel("large jets per hour (summer average)", fontsize=10)
    ax2.set_title("Busiest at midday and late evening; the 23:00 hour is a peak",
                  fontsize=12, fontweight="bold")
    ax2.axhspan(0, hc.max() * 1.15, xmin=23 / 24, xmax=1, color=RED, alpha=0.05)
    peak = hc.idxmax()
    ax2.annotate(f"summer peak ~{hc.max():.1f} large jets/hour\n(about one every {60/hc.max():.0f} min)",
                 (peak, hc.max()), xytext=(-90, -6), textcoords="offset points",
                 fontsize=9, fontweight="bold", color=INK,
                 arrowprops=dict(arrowstyle="->", color=INK))
    ax2.set_ylim(0, hc.max() * 1.2)
    ax2.grid(axis="y", alpha=0.25, zorder=0)
    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)

    fig.suptitle(f"When the large jets come over Brockenhurst ({year}), and what 3m passengers would mean",
                 fontsize=14, fontweight="bold", y=0.99)
    fig.text(0.5, 0.005,
             f"Our {year} data: {len(a):,} large-jet arrivals over Brockenhurst. At summer peak that is about "
             f"{hc.max():.0f} an hour today; under the approved 3m-passenger growth (roughly double) that could reach "
             f"~{hc.max()*2:.0f} an hour, about one large jet every {60/(hc.max()*2):.0f} minutes, with the late-evening peak doubling too.",
             ha="center", fontsize=9, color="#444")
    fig.tight_layout(rect=[0, 0.045, 1, 0.95])
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out, "| summer peak/hour:", round(hc.max(), 1))
    return out


if __name__ == "__main__":
    build()
