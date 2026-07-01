#!/usr/bin/env python3
"""
Analytics dashboard for large passenger jets arriving over Brockenhurst at night
(23:00-06:00), using only flights with a DIRECTLY MEASURED over-village height.

Multiple views on one page: worst-offending airlines, average height, worst days
of the week, worst times of night, worst aircraft types, and the trend over time.

    python dashboard.py   ->  outputs/sweep/night_dashboard.png
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from brockenhurst import charts, classify

BG, FG, GRID, BLUE, GOLD, RED = (charts.BG, charts.FG, charts.GRID,
                                 charts.BLUE, charts.GOLD, charts.RED)
PROPER, FLOOR = 3116, 2000
CARD = "#2a2a2e"

AIRLINE = {"TOM": "TUI", "EXS": "Jet2", "RYR": "Ryanair", "RUK": "Ryanair",
           "ENT": "Enter Air", "EZY": "easyJet", "WZZ": "Wizz Air",
           "BAW": "British Airways", "AMC": "Air Malta", "MLT": "Air Malta"}
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _ax(ax, title):
    ax.set_facecolor(BG)
    for s in ax.spines.values():
        s.set_color(GRID)
    ax.tick_params(colors=FG, labelsize=9)
    ax.grid(True, axis="y", color=GRID, lw=0.5, alpha=0.5)
    ax.set_title(title, color=FG, fontsize=12, fontweight="bold", pad=8)


def _card(fig, x, y, w, h, big, label, color):
    ax = fig.add_axes([x, y, w, h]); ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes,
                               facecolor=CARD, edgecolor=color, lw=2))
    ax.text(0.5, 0.60, big, ha="center", va="center", transform=ax.transAxes,
            color=color, fontsize=25, fontweight="bold")
    ax.text(0.5, 0.20, label, ha="center", va="center", transform=ax.transAxes,
            color=FG, fontsize=9.5)


def _bar_labels(ax, bars, labels, dy=20):
    for b, t in zip(bars, labels):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + dy, t,
                ha="center", va="bottom", color=FG, fontsize=8.5)


def build(out="outputs/sweep/night_dashboard.png"):
    pf = pd.read_csv("outputs/sweep/per_flight.csv")
    pf = pf[pf["year"].isin([2023, 2024, 2025])]
    d = pf[(pf["category"] == "Large jet") & (pf["time_window"] == "Night")
           & (pf["gate_alt_ft"].notna())].copy()
    lt = pd.to_datetime(d["last_seen"], utc=True).dt.tz_convert(classify.LONDON)
    d["hour"] = lt.dt.hour
    d["dow"] = lt.dt.strftime("%a")
    d["airline"] = d["flt_id"].astype(str).str[:3].map(lambda p: AIRLINE.get(p, p))
    h = d["gate_alt_ft"]
    n = len(d)

    fig = plt.figure(figsize=(16, 15.5), facecolor=BG)
    fig.text(0.06, 0.975, "Night-time airliners over Brockenhurst — analytics",
             color=FG, fontsize=22, fontweight="bold")
    fig.text(0.06, 0.957,
             f"Large passenger jets, 23:00–06:00, 2023–2025 · {n} flights with a "
             "directly measured over-village height · lower = louder",
             color="#b0b0b8", fontsize=12)

    # ---- KPI cards ----
    _card(fig, 0.06, 0.86, 0.20, 0.075, f"{n}", "night airliners measured", BLUE)
    _card(fig, 0.28, 0.86, 0.20, 0.075, f"{h.mean():,.0f} ft", "average height over Brockenhurst", GOLD)
    _card(fig, 0.50, 0.86, 0.20, 0.075, f"{100*(h<PROPER).mean():.0f}%",
          "below the quiet-descent height", GOLD)
    _card(fig, 0.72, 0.86, 0.22, 0.075, f"{int((h<FLOOR).sum())}",
          "below the 2,000 ft minimum", RED)

    gs = fig.add_gridspec(2, 3, left=0.06, right=0.96, top=0.80, bottom=0.06,
                          hspace=0.32, wspace=0.24)

    # ---- 1. Worst airlines (avg height, lower = worse) ----
    ax = fig.add_subplot(gs[0, 0])
    grp = d.groupby("airline")["gate_alt_ft"].agg(["size", "mean"])
    # keep meaningful samples; sort so the lowest-average (worst) sits at the TOP
    grp = grp[grp["size"] >= 3].sort_values("mean", ascending=False)
    bars = ax.barh(grp.index, grp["mean"], color=RED)
    ax.axvline(PROPER, color=GOLD, lw=2); ax.axvline(FLOOR, color=FG, lw=1.5, ls="--")
    for i, (_, r) in enumerate(grp.iterrows()):
        ax.text(r["mean"] - 80, i, f"{r['mean']:,.0f} ft  (n={int(r['size'])})",
                ha="right", va="center", color="white", fontsize=8.5)
    _ax(ax, "Worst airlines — average night height")
    ax.grid(False); ax.set_xlim(0, max(PROPER + 400, grp["mean"].max() + 300))
    ax.set_xlabel("average height (ft) — gold = quiet-descent, dashed = 2,000 ft min", fontsize=8, color=FG)

    # ---- 2. Aircraft types ----
    ax = fig.add_subplot(gs[0, 1])
    t = d.groupby("typecode")["gate_alt_ft"].agg(["size", "mean"]).sort_values("size", ascending=False).head(6)
    bars = ax.bar(t.index, t["size"], color=BLUE)
    _bar_labels(ax, bars, [f"{m:,.0f} ft" for m in t["mean"]], dy=2)
    _ax(ax, "Worst aircraft types (count · avg height)")
    ax.set_ylabel("night flights", color=FG)

    # ---- 3. Trend over time ----
    ax = fig.add_subplot(gs[0, 2])
    y = d.groupby("year")["gate_alt_ft"].agg(["size", "mean"])
    bars = ax.bar(y.index.astype(str), y["size"], color=BLUE, label="night flights")
    _bar_labels(ax, bars, [str(int(s)) for s in y["size"]], dy=1)
    ax2 = ax.twinx()
    ax2.plot(y.index.astype(str), y["mean"], color=GOLD, lw=2.5, marker="o", label="avg height")
    ax2.set_ylim(2000, 3400); ax2.tick_params(colors=GOLD, labelsize=8)
    ax2.set_ylabel("avg height (ft)", color=GOLD)
    ax2.axhline(PROPER, color=GOLD, lw=1, ls=":", alpha=0.6)
    _ax(ax, "Trend over time"); ax.set_ylabel("night flights", color=FG)

    # ---- 4. Worst days of week ----
    ax = fig.add_subplot(gs[1, 0])
    dw = d.groupby("dow")["gate_alt_ft"].agg(["size", "mean"]).reindex(DOW)
    # highlight the weekend (busiest) in red, weekdays in blue
    bars = ax.bar(DOW, dw["size"], color=[RED if day in ("Sat", "Sun") else BLUE for day in DOW])
    _bar_labels(ax, bars, [f"{m:,.0f} ft" for m in dw["mean"]], dy=0.5)
    _ax(ax, "Busiest nights of the week (label = avg height)")
    ax.set_ylabel("night flights", color=FG)

    # ---- 5. Worst times of night ----
    ax = fig.add_subplot(gs[1, 1])
    order = [23, 0, 1, 2, 3, 4, 5]
    hh = d.groupby("hour")["gate_alt_ft"].agg(["size", "mean"]).reindex(order).fillna(0)
    labels = [f"{x:02d}:00" for x in order]
    bars = ax.bar(labels, hh["size"], color=GOLD)
    _bar_labels(ax, bars, [f"{m:,.0f} ft" if s else "" for m, s in zip(hh["mean"], hh["size"])], dy=1)
    _ax(ax, "Worst times of night (local)")
    ax.set_ylabel("night flights", color=FG)

    # ---- 6. Height distribution ----
    ax = fig.add_subplot(gs[1, 2])
    bins = np.arange(0, 4500, 250)
    ax.hist(h, bins=bins, color=RED, edgecolor=BG, alpha=0.9)
    ax.axvline(FLOOR, color=FG, lw=2, ls="--", label="2,000 ft min")
    ax.axvline(PROPER, color=GOLD, lw=2, label="quiet-descent")
    _ax(ax, "How high at night (measured)")
    ax.grid(False); ax.set_xlabel("height over Brockenhurst (ft)", color=FG, fontsize=9)
    ax.set_ylabel("night flights", color=FG)
    ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=FG, fontsize=8)

    fig.text(0.06, 0.028,
             "Source: aircraft's own broadcast (ADS-B) positions via OPDI / OpenSky. "
             "\"Measured\" = a recorded point within 3 km of the village. A precise "
             "over-village height exists for ~1 in 6 arrivals, so counts are minimums. "
             "Prepared from public data — not affiliated with the airport.",
             color="#9a9aa2", fontsize=8)
    fig.savefig(out, dpi=130, facecolor=BG)
    plt.close(fig)
    # Also emit a shareable landscape-A4 PDF of the dashboard.
    pdf_path = out.rsplit("/", 1)[0].replace("/sweep", "") + "/night_dashboard.pdf"
    try:
        from fpdf import FPDF
        from PIL import Image
        iw, ih = Image.open(out).size
        pdf = FPDF(orientation="L", format="A4"); pdf.add_page()
        w = pdf.w - 20
        pdf.image(out, x=10, y=max(8, (pdf.h - w * ih / iw) / 2), w=w)
        pdf.output(pdf_path)
        print("wrote", pdf_path)
    except Exception as e:
        print("PDF skipped:", e)
    print("wrote", out)
    return out


if __name__ == "__main__":
    build()
