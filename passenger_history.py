#!/usr/bin/env python3
"""
Bournemouth Airport passenger history (2007-2025) against the approved 3.0m cap.
Passenger figures are the airport's published / CAA annual totals (calendar year),
via CAA UK airport data and the airport's statistics; the 3.0m ceiling is the
approved planning capacity.

    python passenger_history.py  ->  outputs/sweep/passenger_history.png
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Calendar-year terminal passengers, UK CAA airport statistics.
# Cross-checked: every figure matches the CAA-sourced series; 2007-2012 also
# corroborated by AirportWatch, and 2025 (1.38m) matches the airport's own
# "1.4m for the year to March 2026" (financial-year basis).
PAX = {
    2007: 1_083_379, 2008: 1_078_941, 2009: 868_445, 2010: 751_331,
    2011: 613_755, 2012: 689_913, 2013: 660_272, 2014: 661_584,
    2015: 706_776, 2016: 667_981, 2017: 694_660, 2018: 674_972,
    2019: 803_307, 2020: 175_907, 2021: 200_640, 2022: 734_530,
    2023: 950_206, 2024: 1_088_370, 2025: 1_380_454,
}
CAP = 3_000_000
INK, BLUE, RED, AMBER = "#222222", "#2c6fbb", "#c0392b", "#e8a020"


def build(out="outputs/sweep/passenger_history.png"):
    years = list(PAX); vals = [PAX[y] for y in years]
    fig, ax = plt.subplots(figsize=(12, 6.4))
    bars = ax.bar(years, vals, color=BLUE, width=0.72, zorder=3)
    bars[years.index(2025)].set_color(RED)   # highlight the latest record
    # approved cap
    ax.axhline(CAP, color=AMBER, lw=2.2, ls="--", zorder=4)
    ax.annotate("Approved capacity: 3,000,000 passengers  (more than double today)",
                (2007.5, CAP), xytext=(0, 8), textcoords="offset points",
                color="#9a6a00", fontsize=11, fontweight="bold", va="bottom")
    # value labels
    for y, v in PAX.items():
        ax.annotate(f"{v/1e6:.2f}m" if v >= 1e6 else f"{v/1e3:.0f}k",
                    (y, v), xytext=(0, 3), textcoords="offset points",
                    ha="center", fontsize=7.5, color=INK)
    ax.annotate("COVID", (2020.5, 200_000), xytext=(0, 26), textcoords="offset points",
                ha="center", fontsize=8, color="#777")
    ax.annotate("record high\n1.38m (2025)", (2025, 1_380_454), xytext=(-4, 40),
                textcoords="offset points", ha="center", fontsize=9, fontweight="bold",
                color=RED, arrowprops=dict(arrowstyle="->", color=RED))
    ax.set_ylim(0, 3_300_000)
    ax.set_yticks([0, 1e6, 2e6, 3e6])
    ax.set_yticklabels(["0", "1m", "2m", "3m"])
    ax.set_xticks(years); ax.set_xticklabels(years, rotation=45, fontsize=8.5)
    ax.set_ylabel("Passengers per year", fontsize=10)
    ax.set_title("Bournemouth Airport passengers: back above 2007 levels and rising fast,\n"
                 "with permission to more than double again to 3 million",
                 fontsize=13, fontweight="bold")
    ax.grid(axis="y", alpha=0.25, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.text(0.5, 0.01,
             "Terminal passengers, calendar year, from CAA UK airport data and the airport's published figures. "
             "The airport quotes 1.4m for the year to March 2026. Approved capacity is 3.0m passengers a year "
             "(2007 and 2010 planning permissions).",
             ha="center", fontsize=8.3, color="#555")
    fig.tight_layout(rect=[0, 0.035, 1, 1])
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out)
    return out


if __name__ == "__main__":
    build()
