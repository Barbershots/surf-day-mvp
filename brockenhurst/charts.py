"""
Charts for the noise case, styled to match the existing WebTrak-comparison
dashboards (dark background, blue/gold/red period palette).
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import config
from . import approach
from . import geometry as geo

BG = "#1c1c1e"
FG = "#e5e5ea"
GRID = "#3a3a3c"
BLUE = "#1f6fc4"   # day / on-profile
GOLD = "#c8881f"   # evening / caution
RED = "#a51e2d"    # night / breach


def _style(ax):
    ax.set_facecolor(BG)
    for s in ax.spines.values():
        s.set_color(GRID)
    ax.tick_params(colors=FG)
    ax.yaxis.label.set_color(FG)
    ax.xaxis.label.set_color(FG)
    ax.title.set_color(FG)
    ax.grid(True, color=GRID, linewidth=0.5, alpha=0.6)


def descent_profile(events_annotated, path):
    """
    Altitude vs distance-from-threshold for every approach event, with the
    compliant 3-degree CDA line and the 2000' floor overlaid. Points sitting on
    or below the line near Brockenhurst are aircraft no higher than the
    glidepath far too early.
    """
    e = events_annotated
    # Approach phase only: in corridor, within 18 NM, and below 10,000 ft. The
    # last bound drops cruise points and a handful of corrupt ADS-B altitude
    # spikes (>40,000 ft directly over the field) that are not approach data.
    e = e[(e["in_corridor"]) & (e["dist_thr_nm"].between(0, 18))
          & (e["altitude"] > 0) & (e["altitude"] <= 10000)]
    fig, ax = plt.subplots(figsize=(10, 6), facecolor=BG)
    ax.scatter(e["dist_thr_nm"], e["altitude"], s=7, alpha=0.30, color=BLUE,
               edgecolors="none", label="Arrival events (level-offs & FL crossings)")
    x = np.linspace(0, 18, 100)
    ax.plot(x, geo.glideslope_altitude_ft(x), color=GOLD, lw=2,
            label="Compliant 3-deg continuous descent")
    ax.axhline(config.HARD_FLOOR_FT, color=RED, lw=1.5, ls="--",
               label=f"{config.HARD_FLOOR_FT} ft procedure floor")
    d_brock = geo.dist_from_threshold_nm(*config.BROCKENHURST)
    _style(ax)
    ax.set_xlabel("Distance from runway-26 threshold (NM)")
    ax.set_ylabel("Altitude (ft AMSL)")
    ax.set_ylim(0, 8000)
    ax.set_title("Bournemouth arrivals: altitude vs the compliant descent profile")
    ax.invert_xaxis()
    ax.axvline(d_brock, color=FG, lw=1, ls=":", alpha=0.8)
    ax.text(d_brock, 7700, " Brockenhurst", color=FG, fontsize=9, va="top", ha="center")
    ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=FG, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=BG)
    plt.close(fig)


def gate_altitude_hist(per_flight_df, path):
    """Distribution of altitude over Brockenhurst, vs floor and CDA profile."""
    g = per_flight_df["gate_alt_ft"].dropna()
    fig, ax = plt.subplots(figsize=(10, 5.5), facecolor=BG)
    bins = np.arange(0, max(4000, g.max() + 250), 250)
    ax.hist(g, bins=bins, color=BLUE, edgecolor=BG)
    cda = geo.expected_cda_altitude_ft()
    ax.axvline(config.HARD_FLOOR_FT, color=RED, lw=2, ls="--",
               label=f"{config.HARD_FLOOR_FT} ft procedure floor")
    ax.axvline(cda, color=GOLD, lw=2,
               label=f"compliant CDA profile ({round(cda)} ft)")
    _style(ax)
    ax.set_xlabel("Altitude over Brockenhurst (ft AMSL)")
    ax.set_ylabel("Number of arrivals")
    ax.set_title("How high are aircraft actually over Brockenhurst?")
    ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=FG, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=BG)
    plt.close(fig)


def leveloff_summary(summary_dict, path):
    """Headline bars: share of arrivals not flying a continuous descent."""
    s = summary_dict
    labels = ["Any corridor\nlevel-off", "Level-off over\nBrockenhurst",
              "Gate reading below\nCDA profile", "Gate reading below\n2000 ft floor"]
    n = s["arrivals_with_events"]
    gate_n = max(s["flights_with_gate_reading"], 1)
    vals = [
        s["pct_with_corridor_leveloff"],
        s["pct_leveloff_over_village"],
        round(100 * s["gate_below_cda_profile"] / gate_n, 1),
        round(100 * s["gate_below_hard_floor"] / gate_n, 1),
    ]
    colors = [GOLD, RED, GOLD, RED]
    fig, ax = plt.subplots(figsize=(9, 5.5), facecolor=BG)
    bars = ax.bar(labels, vals, color=colors, edgecolor=BG)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.0f}%",
                ha="center", color=FG, fontsize=11, fontweight="bold")
    _style(ax)
    ax.set_ylabel("% of arrivals")
    ax.set_ylim(0, 100)
    ax.set_title("Share of Bournemouth arrivals not flying a continuous descent")
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=BG)
    plt.close(fig)


def make_all(arrivals, events, per_flight_df, summary_dict, outdir):
    import os

    os.makedirs(outdir, exist_ok=True)
    ann = approach.annotate(events)
    descent_profile(ann, os.path.join(outdir, "descent_profile.png"))
    gate_altitude_hist(per_flight_df, os.path.join(outdir, "gate_altitude_hist.png"))
    leveloff_summary(summary_dict, os.path.join(outdir, "leveloff_summary.png"))
