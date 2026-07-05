#!/usr/bin/env python3
"""
Night arrivals over Brockenhurst and how many break the airport's own night rule.
Night window is the airport's own 21:30-06:30; height measured over the village.

    python night_chart.py  ->  outputs/sweep/night_chart.png
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BLUE, RED, AMBER, INK = "#2c6fbb", "#c0392b", "#e8a020", "#222222"


def data():
    pf = pd.read_csv("outputs/sweep/per_flight.csv")
    pf["t"] = pd.to_datetime(pf["last_seen"], errors="coerce")
    pf = pf.dropna(subset=["t"])
    pf["t"] = pf["t"].dt.tz_localize("UTC").dt.tz_convert("Europe/London")
    pf["hr"] = pf["t"].dt.hour + pf["t"].dt.minute / 60
    pf["year"] = pf["t"].dt.year
    lj = pf[(pf["category"] == "Large jet") & (pf["year"].isin([2023, 2024, 2025]))]
    night = lj[(lj["hr"] >= 21.5) | (lj["hr"] < 6.5)]
    out = {}
    for y in (2023, 2024, 2025):
        g = night[night["year"] == y]
        meas = g[g["gate_alt_ft"].notna()]
        out[y] = dict(total=len(g),
                      below2500=int((meas["gate_alt_ft"] < 2500).sum()),
                      below2000=int((meas["gate_alt_ft"] < 2000).sum()),
                      median=meas["gate_alt_ft"].median())
    return out


def build(out="outputs/sweep/night_chart.png"):
    d = data(); years = [2023, 2024, 2025]
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.2))

    # Left: night arrivals over the village
    ax = axes[0]
    tot = [d[y]["total"] for y in years]
    bars = ax.bar([str(y) for y in years], tot, color=BLUE, width=0.6, zorder=3)
    bars[-1].set_color(RED)
    for y, v in zip(years, tot):
        ax.annotate(f"{v:,}", (str(y), v), xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=11, fontweight="bold", color=INK)
    ax.set_title("Night arrivals over Brockenhurst have nearly doubled\n(21:30-06:30, large jets)",
                 fontsize=12, fontweight="bold")
    ax.set_ylabel("large-jet night arrivals over the village", fontsize=10)
    ax.set_ylim(0, max(tot) * 1.18)
    ax.grid(axis="y", alpha=0.25, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    # Right: breaking the airport's own night minimum
    ax2 = axes[1]
    b2500 = [d[y]["below2500"] for y in years]
    b2000 = [d[y]["below2000"] for y in years]
    x = np.arange(3)
    ax2.bar(x - 0.19, b2500, width=0.36, color=AMBER, label="below 2,500 ft (their night minimum)", zorder=3)
    ax2.bar(x + 0.19, b2000, width=0.36, color=RED, label="below 2,000 ft (hard floor)", zorder=3)
    for i, (a, b) in enumerate(zip(b2500, b2000)):
        ax2.annotate(f"{a}", (i - 0.19, a), xytext=(0, 4), textcoords="offset points",
                     ha="center", fontsize=10, fontweight="bold", color="#9a6a00")
        ax2.annotate(f"{b}", (i + 0.19, b), xytext=(0, 4), textcoords="offset points",
                     ha="center", fontsize=10, fontweight="bold", color=RED)
    ax2.set_xticks(x); ax2.set_xticklabels([str(y) for y in years])
    ax2.set_title("Night arrivals crossing the village too low\n(measured minimums, real numbers ~5x higher)",
                  fontsize=12, fontweight="bold")
    ax2.set_ylabel("large jets over Brockenhurst at night", fontsize=10)
    ax2.set_ylim(0, max(b2500) * 1.25)
    ax2.legend(fontsize=9, loc="upper left", framealpha=0.9)
    ax2.grid(axis="y", alpha=0.25, zorder=0)
    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)

    fig.suptitle("Night flying over Brockenhurst against the airport's own night rule (21:30-06:30, no lower than 2,500 ft)",
                 fontsize=13.5, fontweight="bold", y=0.99)
    fig.text(0.5, 0.005,
             f"Median night height over the village fell {d[2023]['median']:,.0f} to {d[2025]['median']:,.0f} ft. "
             "The airport's night rule says arrivals should not be below 2,500 ft until within 8 miles; Brockenhurst is at 9.7 miles. "
             "Heights measured for the ~1 in 5 with a fix over the village, so counts are minimums. Large jets, via OPDI / OpenSky.",
             ha="center", fontsize=9, color="#444")
    fig.tight_layout(rect=[0, 0.045, 1, 0.95])
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out, "|", {y: d[y] for y in years})
    return out


if __name__ == "__main__":
    build()
