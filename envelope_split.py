#!/usr/bin/env python3
"""
Where runway-26 arrivals approach from, mapped to the three design envelopes
(NE / ESE / S), with the honest "which side of the village line" cut alongside so
the three-way bucketing does not mislead.

    python envelope_split.py  ->  outputs/sweep/envelope_split.png
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import where_from

BLUE, AMBER, RED, GREY, INK = "#2c6fbb", "#e8a020", "#c0392b", "#9aa0aa", "#222"
CL = 75.0  # straight-in-over-the-village bearing


def build(out="outputs/sweep/envelope_split.png"):
    b = where_from.bearings(); n = len(b)
    def p(lo, hi):
        return ((b >= lo) & (b < hi)).mean() * 100
    ne, ese, s = p(0, 90), p(90, 120), p(120, 200)
    north, south = p(0, CL), p(CL, 200)

    fig = plt.figure(figsize=(15, 7.2))

    # ---- left: compass rose coloured by envelope sector ----
    ax = fig.add_subplot(121, projection="polar")
    ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)
    step = 15; edges = np.arange(0, 360 + step, step)
    counts, _ = np.histogram(b, bins=edges); pct = 100 * counts / n
    centres = np.radians(edges[:-1] + step / 2)
    colors = []
    for e in edges[:-1]:
        colors.append(BLUE if e < 90 else AMBER if e < 120 else RED if e < 200 else "#dddddd")
    ax.bar(centres, pct, width=np.radians(step) * 0.92, color=colors, edgecolor="white", linewidth=0.6, zorder=3)
    ax.plot([np.radians(CL), np.radians(CL)], [0, max(pct) * 1.1], color=INK, lw=1.6, ls="--", zorder=4)
    ax.set_xticks(np.radians([0, 45, 90, 135, 180, 225, 270, 315]))
    ax.set_xticklabels(["N", "NE", "E", "SE", "S", "SW", "W", "NW"], fontsize=11, fontweight="bold")
    ax.set_yticks([5, 10, 15]); ax.set_yticklabels(["5%", "10%", "15%"], fontsize=8, color="#666")
    ax.set_ylim(0, max(pct) * 1.15)
    ax.set_title("Where arrivals approach from, by design envelope\n(dashed line = straight in over the village)",
                 fontsize=12, fontweight="bold", pad=22)

    # ---- right: the two cuts as stacked bars ----
    ax2 = fig.add_subplot(122)
    ax2.set_xlim(0, 100); ax2.set_ylim(-0.5, 2.2); ax2.axis("off")

    def stack(y, segs, label):
        x = 0
        for val, col, txt in segs:
            ax2.barh(y, val, left=x, color=col, edgecolor="white", height=0.5)
            ax2.text(x + val / 2, y, f"{txt}\n{val:.0f}%", ha="center", va="center",
                     color="white", fontsize=11, fontweight="bold")
            x += val
        ax2.text(0, y + 0.4, label, fontsize=11.5, fontweight="bold", color=INK)

    stack(1.6, [(north, GREY, "NORTH side"), (south, "#7a4b78", "SOUTH side")],
          "Which side of the village line?  (the honest cut)")
    stack(0.5, [(ne, BLUE, "NE"), (ese, AMBER, "ESE"), (s, RED, "S")],
          "By design envelope direction")
    ax2.text(50, -0.35, "Runway-26 large-jet arrivals, measured ~15 miles out. Approximate, and shifts with\n"
             "measurement point. Our independent estimate, to check against the airport's per-envelope forecast.",
             ha="center", va="top", fontsize=8.7, color="#555")

    fig.suptitle(f"Most arrivals approach from the SOUTH side of the village line (about {south:.0f}% vs {north:.0f}%)",
                 fontsize=13.5, fontweight="bold", y=0.99)
    fig.tight_layout(rect=[0, 0.02, 1, 0.95])
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out} | NE {ne:.0f} ESE {ese:.0f} S {s:.0f} | north {north:.0f} south {south:.0f}")
    return out


if __name__ == "__main__":
    build()
