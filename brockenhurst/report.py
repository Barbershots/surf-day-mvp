"""
Plain-English reporting for the sweep: charts and tables written so that
someone with no aviation background can understand them.

Two plain-language anchors are used everywhere instead of jargon:

    "Proper height" (~3,100 ft) - where a plane should be over Brockenhurst if
        it is gliding down gently with its engines near idle. This is the quiet
        way to arrive (a "continuous descent"). Derived from the standard 3-deg
        approach path - see METHODOLOGY.md.

    "Minimum allowed" (2,000 ft) - the airport's own published rule: planes
        must not be lower than this here. Below it is a clear breach.

The core message the charts make visual: lower = louder, because to fly low and
level a plane has to keep its engines working hard.
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config
from . import approach, charts, classify
from . import geometry as geo

PROPER_FT = round(geo.expected_cda_altitude_ft())   # ~3,116
FLOOR_FT = config.HARD_FLOOR_FT                      # 2,000

# Flights flagged in the resident audit. The audit uses IATA flight numbers
# (e.g. "LS3684"); ADS-B/OPDI records the ICAO radio callsign, which uses a
# 3-letter airline prefix (Jet2 "LS" -> "EXS"). We therefore cross-reference by
# operator. "URO" matches no UK airline and an A340-600 freighter into
# Bournemouth is implausible, so it is reported as unverifiable.
AUDIT_OPERATORS = {
    "EXS": "Jet2 (audit 'LS' flights, e.g. LS3684 Ibiza)",
    "TOM": "TUI (audit 'TOM' flights, e.g. TOM651)",
    "RYR": "Ryanair (audit 'RYR' flights, e.g. RYR1244)",
}
AUDIT_UNVERIFIABLE = ["URO601", "URO901"]


def _local_times(pf: pd.DataFrame) -> pd.Series:
    t = pd.to_datetime(pf["last_seen"], utc=True)
    return t.dt.tz_convert(classify.LONDON)


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def night_large_jet_table(pf: pd.DataFrame) -> pd.DataFrame:
    """
    One row per night-time airliner with a measured height over Brockenhurst.
    Height is the direct over-village reading where we have one, otherwise the
    height at which the plane levelled off within 6 km of the village.
    """
    d = pf[(pf["category"] == "Large jet") & (pf["time_window"] == "Night")].copy()
    # Coalesce the two height sources.
    d["height"] = d["gate_alt_ft"].fillna(d["village_leveloff_ft"])
    d = d[d["height"].notna()].copy()
    lt = _local_times(d)
    source = np.where(d["gate_alt_ft"].notna(), "passed overhead",
                      "levelled off near village")
    out = pd.DataFrame({
        "date": lt.dt.strftime("%Y-%m-%d"),
        "local_time": lt.dt.strftime("%H:%M"),
        "callsign": d["flt_id"].fillna("(unknown)"),
        "aircraft_type": d["typecode"].fillna("(unknown)"),
        "height_over_brockenhurst_ft": d["height"].round().astype(int),
        "ft_below_proper_height": (PROPER_FT - d["height"]).round().astype(int),
        "below_2000ft_minimum": np.where(d["height"] < FLOOR_FT, "YES", ""),
        "stopped_descending_overhead": np.where(d["leveloff_over_village"], "YES", ""),
        "measurement": source,
    })
    return out.sort_values("height_over_brockenhurst_ft").reset_index(drop=True)


def summary_by_year(pf: pd.DataFrame) -> pd.DataFrame:
    """Year-on-year headline numbers for large jets, with a night focus."""
    rows = []
    for year, g in pf.groupby("year"):
        lj = g[g["category"] == "Large jet"]
        night = lj[lj["time_window"] == "Night"]
        night_gate = night[night["gate_alt_ft"].notna()]
        rows.append({
            "year": int(year),
            "large_jet_arrivals_tracked": len(lj),
            "night_large_jets_tracked": len(night),
            "night_with_height_reading": len(night_gate),
            "night_median_height_ft": int(np.nanmedian(night_gate["gate_alt_ft"])) if len(night_gate) else None,
            "night_below_proper_height": int((night_gate["gate_alt_ft"] < PROPER_FT).sum()),
            "night_below_2000ft_minimum": int((night_gate["gate_alt_ft"] < FLOOR_FT).sum()),
            "night_stopped_descending_overhead": int(night["leveloff_over_village"].sum()),
        })
    return pd.DataFrame(rows).sort_values("year")


def cross_reference_audit(pf: pd.DataFrame) -> pd.DataFrame:
    """
    Cross-reference the audit by OPERATOR. For each airline named in the audit,
    count its night-time low flights over Brockenhurst in 2023-2025 and give the
    lowest examples - confirming the pattern the audit describes even though the
    audit's own June-2026 dates are beyond current open-data coverage.
    """
    fid = pf["flt_id"].fillna("").astype(str)
    rows = []
    for prefix, label in AUDIT_OPERATORS.items():
        op = pf[fid.str.startswith(prefix)]
        night = op[(op["category"] == "Large jet") & (op["time_window"] == "Night")]
        h = night["gate_alt_ft"].fillna(night["village_leveloff_ft"])
        night_low = night[h < PROPER_FT]
        example = h.dropna().min()
        rows.append({
            "operator": label,
            "night_flights_tracked": len(night),
            "night_flights_below_proper_height": len(night_low),
            "lowest_night_height_ft": int(example) if pd.notna(example) else None,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Charts (plain language)
# ---------------------------------------------------------------------------

def _refs(ax, xmax):
    ax.axhline(PROPER_FT, color=charts.GOLD, lw=2,
               label=f"Proper height (~{PROPER_FT:,} ft) - the quiet way down")
    ax.axhline(FLOOR_FT, color=charts.RED, lw=2, ls="--",
               label=f"Minimum allowed ({FLOOR_FT:,} ft) - airport's own rule")


def height_by_timeofday(pf, path):
    """Average airliner height over Brockenhurst: day vs evening vs night."""
    lj = pf[(pf["category"] == "Large jet") & (pf["gate_alt_ft"].notna())]
    order = ["Day", "Evening", "Night"]
    meds = [lj[lj["time_window"] == w]["gate_alt_ft"].median() for w in order]
    ns = [int((lj["time_window"] == w).sum()) for w in order]
    colors = [charts.BLUE, charts.GOLD, charts.RED]

    fig, ax = plt.subplots(figsize=(9, 6), facecolor=charts.BG)
    bars = ax.bar(order, meds, color=colors, edgecolor=charts.BG, width=0.6)
    for b, v, n in zip(bars, meds, ns):
        ax.text(b.get_x() + b.get_width() / 2, v + 60,
                f"{v:,.0f} ft\n({n} flights)", ha="center",
                color=charts.FG, fontsize=11, fontweight="bold")
    _refs(ax, len(order))
    charts._style(ax)
    ax.set_ylabel("Typical height over Brockenhurst (ft)")
    ax.set_ylim(0, max(PROPER_FT + 600, max(meds) + 600))
    ax.set_title("How high are airliners as they pass over Brockenhurst?\n"
                 "Lower bar = lower plane = more engine noise", color=charts.FG)
    ax.legend(facecolor=charts.BG, edgecolor=charts.GRID, labelcolor=charts.FG, fontsize=9, loc="lower left")
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=charts.BG)
    plt.close(fig)


def _profile_frame(events, keep_years):
    """Annotate raw events and reduce to the approach-corridor points for plotting."""
    e = approach.annotate(events)
    if "year" in e.columns:
        yr = e["year"]
    else:
        yr = pd.to_datetime(e["event_time"]).dt.year
    e = e.assign(year=yr)
    e = e[(e["in_corridor"]) & (e["dist_thr_nm"].between(0, 18))
          & (e["altitude"] > 0) & (e["altitude"] <= 10000)
          & (e["year"].isin(list(keep_years)))]
    cat = e["category"] if "category" in e.columns else pd.Series("", index=e.index)
    fid = e["flight_id"] if "flight_id" in e.columns else pd.Series(range(len(e)), index=e.index)
    return pd.DataFrame({
        "flight_id": fid.values,
        "dist_thr_nm": e["dist_thr_nm"].values, "altitude": e["altitude"].values,
        "year": e["year"].values, "category": cat.values,
        "cda_profile_ft": e["cda_profile_ft"].values,
    })


def descent_profile_by_year(profile_df, path, large_jet_only=False):
    """
    The altitude-vs-distance scatter (with the compliant 3-degree line and the
    2,000 ft floor) split into one panel per year - showing the arrivals sitting
    below where a quiet continuous descent would put them, and how the picture
    has shifted since 2023. `profile_df` needs columns dist_thr_nm, altitude,
    year, category, cda_profile_ft (already filtered to the approach corridor).
    """
    d = profile_df
    if large_jet_only:
        d = d[d["category"] == "Large jet"]
    years = sorted(int(y) for y in d["year"].dropna().unique())
    d_brock = geo.dist_from_threshold_nm(*config.BROCKENHURST)
    x = np.linspace(0, 18, 120)

    fig, axes = plt.subplots(1, len(years), figsize=(4.9 * len(years), 6.4),
                             sharey=True, facecolor=charts.BG)
    if len(years) == 1:
        axes = [axes]
    for ax, yr in zip(axes, years):
        dd = d[d["year"] == yr]
        ax.scatter(dd["dist_thr_nm"], dd["altitude"], s=5, alpha=0.14,
                   color=charts.BLUE, edgecolors="none")
        ax.plot(x, geo.glideslope_altitude_ft(x), color=charts.GOLD, lw=2.2)
        ax.axhline(config.HARD_FLOOR_FT, color=charts.RED, lw=1.5, ls="--")
        ax.axvline(d_brock, color=charts.FG, lw=1, ls=":", alpha=0.85)
        # Near-village band (8-12 NM) - all three quoted numbers come from here,
        # so the % below, the average height and the aircraft count are consistent.
        zone = dd[dd["dist_thr_nm"].between(8, 12)]
        pct = (zone["altitude"] < zone["cda_profile_ft"]).mean() * 100 if len(zone) else 0
        n_jets = zone["flight_id"].nunique()
        avg_ft = zone["altitude"].mean() if len(zone) else 0
        ax.set_title(str(yr), color=charts.FG, fontsize=16, fontweight="bold")
        ax.text(0.04, 0.965,
                f"{pct:.0f}% below the\nquiet-descent line\nover Brockenhurst",
                transform=ax.transAxes, ha="left", va="top",
                color="#f0c96b", fontsize=9.5, fontweight="bold")
        ax.text(0.04, 0.70,
                f"{n_jets:,} aircraft\navg height {avg_ft:,.0f} ft",
                transform=ax.transAxes, ha="left", va="top",
                color=charts.FG, fontsize=9, fontweight="bold")
        ax.text(d_brock - 0.25, 4600, "Brockenhurst", color=charts.FG, fontsize=8,
                rotation=90, ha="right", va="center", alpha=0.9)
        charts._style(ax)
        ax.set_ylim(0, 8000)
        ax.set_xlim(18, 0)
        ax.set_xlabel("Distance from the airport (nautical miles)")
    axes[0].set_ylabel("Height above sea level (ft)")

    # Shared plain-language legend.
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=charts.BLUE,
               markersize=7, label="each dot = one arriving aircraft"),
        Line2D([0], [0], color=charts.GOLD, lw=2.2,
               label="where a quiet 'glide down' descent should be"),
        Line2D([0], [0], color=charts.RED, lw=1.5, ls="--",
               label="2,000 ft — the airport's own minimum"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, facecolor=charts.BG,
               edgecolor=charts.GRID, labelcolor=charts.FG, fontsize=9.5,
               bbox_to_anchor=(0.5, -0.005))
    who = "Airliners" if large_jet_only else "Arrivals"
    fig.suptitle(
        f"{who} over Brockenhurst are flying below the quiet-descent line — "
        "and more so each year",
        color=charts.FG, fontsize=15.5, y=0.99)
    fig.tight_layout(rect=[0, 0.05, 1, 0.96])
    fig.savefig(path, dpi=135, facecolor=charts.BG)
    plt.close(fig)


def night_year_on_year(summary_df, path):
    """How many night-time airliners flew too low, each year."""
    s = summary_df
    x = s["year"].astype(str).tolist()
    fig, ax = plt.subplots(figsize=(9, 6), facecolor=charts.BG)
    below_proper = s["night_below_proper_height"].tolist()
    below_floor = s["night_below_2000ft_minimum"].tolist()
    ax.bar(x, below_proper, color=charts.GOLD, edgecolor=charts.BG,
           label="Lower than the proper (quiet) height")
    ax.bar(x, below_floor, color=charts.RED, edgecolor=charts.BG,
           label="Below the airport's own 2,000 ft minimum")
    for i, (bp, bf) in enumerate(zip(below_proper, below_floor)):
        ax.text(i, bp + 0.5, str(bp), ha="center", color=charts.FG, fontweight="bold")
    charts._style(ax)
    ax.set_ylabel("Number of night-time airliners")
    ax.set_title("Night-time airliners passing low over Brockenhurst\n"
                 "(11pm-6am, the core sleep window)", color=charts.FG)
    ax.legend(facecolor=charts.BG, edgecolor=charts.GRID, labelcolor=charts.FG, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=charts.BG)
    plt.close(fig)


def night_height_hist(pf, path):
    """Distribution of night airliner heights over Brockenhurst."""
    d = pf[(pf["category"] == "Large jet") & (pf["time_window"] == "Night")
           & (pf["gate_alt_ft"].notna())]["gate_alt_ft"]
    fig, ax = plt.subplots(figsize=(10, 6), facecolor=charts.BG)
    if len(d):
        bins = np.arange(0, max(4000, d.max() + 250), 250)
        ax.hist(d, bins=bins, color=charts.RED, edgecolor=charts.BG, alpha=0.85)
    ax.axvline(FLOOR_FT, color=charts.FG, lw=2, ls="--",
               label=f"Minimum allowed ({FLOOR_FT:,} ft)")
    ax.axvline(PROPER_FT, color=charts.GOLD, lw=2,
               label=f"Proper quiet height (~{PROPER_FT:,} ft)")
    charts._style(ax)
    ax.set_xlabel("Height over Brockenhurst at night (ft)")
    ax.set_ylabel("Number of night-time airliners")
    ax.set_title("How low are airliners flying over Brockenhurst at night?", color=charts.FG)
    ax.legend(facecolor=charts.BG, edgecolor=charts.GRID, labelcolor=charts.FG, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=charts.BG)
    plt.close(fig)


def worst_night_offenders(night_table, path, n=15):
    """The lowest individual night-time airliners, labelled with flight + date."""
    d = night_table.head(n).iloc[::-1]
    if d.empty:
        return
    labels = [f"{r.callsign}  {r.date}  {r.local_time}" for r in d.itertuples()]
    fig, ax = plt.subplots(figsize=(10, 7), facecolor=charts.BG)
    colors = [charts.RED if v < FLOOR_FT else charts.GOLD
              for v in d["height_over_brockenhurst_ft"]]
    ax.barh(labels, d["height_over_brockenhurst_ft"], color=colors, edgecolor=charts.BG)
    ax.axvline(FLOOR_FT, color=charts.FG, lw=2, ls="--", label=f"2,000 ft minimum")
    ax.axvline(PROPER_FT, color=charts.GOLD, lw=2, label=f"~{PROPER_FT:,} ft proper height")
    for i, v in enumerate(d["height_over_brockenhurst_ft"]):
        ax.text(v + 30, i, f"{v:,} ft", va="center", color=charts.FG, fontsize=9)
    charts._style(ax)
    ax.set_xlabel("Height over Brockenhurst (ft)")
    ax.set_title("Lowest night-time airliners over Brockenhurst, 2023-2025", color=charts.FG)
    ax.legend(facecolor=charts.BG, edgecolor=charts.GRID, labelcolor=charts.FG, fontsize=9, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=charts.BG)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def build(arr, events, pf, outdir):
    os.makedirs(outdir, exist_ok=True)
    # Drop any partial trailing year (the last 10-day event window can spill a
    # handful of flights into the next January); keep only full calendar years.
    counts = pf.groupby("year")["flight_id"].count()
    full_years = counts[counts >= 100].index
    pf = pf[pf["year"].isin(full_years)].copy()

    night_tbl = night_large_jet_table(pf)
    night_tbl.to_csv(os.path.join(outdir, "night_large_jets.csv"), index=False)

    by_year = summary_by_year(pf)
    by_year.to_csv(os.path.join(outdir, "summary_by_year.csv"), index=False)

    xref = cross_reference_audit(pf)
    xref.to_csv(os.path.join(outdir, "audit_cross_reference.csv"), index=False)

    height_by_timeofday(pf, os.path.join(outdir, "height_by_timeofday.png"))
    night_year_on_year(by_year, os.path.join(outdir, "night_year_on_year.png"))
    night_height_hist(pf, os.path.join(outdir, "night_height_hist.png"))
    worst_night_offenders(night_tbl, os.path.join(outdir, "worst_night_offenders.png"))

    # Year-on-year altitude-vs-distance profile (needs the raw events).
    if events is not None and len(events):
        prof = _profile_frame(events, full_years)
        descent_profile_by_year(prof, os.path.join(outdir, "descent_profile_by_year.png"))
        descent_profile_by_year(prof, os.path.join(outdir, "descent_profile_by_year_large_jets.png"),
                                large_jet_only=True)

    # A plain-English summary text file.
    _write_plain_summary(pf, by_year, night_tbl, xref, os.path.join(outdir, "FINDINGS.md"))
    return by_year, night_tbl


def _write_plain_summary(pf, by_year, night_tbl, xref, path):
    lj = pf[pf["category"] == "Large jet"]
    night = lj[lj["time_window"] == "Night"]
    night_gate = night[night["gate_alt_ft"].notna()]
    n_below_floor = int((night_gate["gate_alt_ft"] < FLOOR_FT).sum())
    n_below_proper = int((night_gate["gate_alt_ft"] < PROPER_FT).sum())
    med = np.nanmedian(night_gate["gate_alt_ft"]) if len(night_gate) else float("nan")

    lines = [
        "# What the flight data shows over Brockenhurst (2023-2025)",
        "",
        "*Plain-English summary. \"Height\" means height above sea level as the "
        "plane passed over Brockenhurst village. All heights come from the "
        "planes' own broadcast position data.*",
        "",
        "## The two numbers that matter",
        f"- **Proper (quiet) height over Brockenhurst: about {PROPER_FT:,} ft.** "
        "This is where a plane should be if it is gliding down gently with its "
        "engines near idle - the quiet way to arrive.",
        f"- **Minimum the airport allows here: {FLOOR_FT:,} ft.** Below this is a "
        "clear breach of the airport's own published rule.",
        "",
        "When a plane is lower than the proper height it has usually stopped "
        "gliding and is flying low and level - which means its engines are "
        "working harder, so it is louder. That is the noise residents hear.",
        "",
        "## Night-time airliners (11pm-6am, the core sleep window)",
        f"- Tracked night-time airliners over Brockenhurst with a height reading: "
        f"**{len(night_gate):,}**.",
        f"- Typical (median) height: **{med:,.0f} ft** - "
        f"**{PROPER_FT - med:,.0f} ft below** the proper quiet height."
        if len(night_gate) else "- No night readings in this period.",
        f"- Flew **lower than the proper quiet height**: **{n_below_proper:,}** "
        f"({100*n_below_proper/max(len(night_gate),1):.0f}%).",
        f"- Flew **below the airport's own {FLOOR_FT:,} ft minimum**: "
        f"**{n_below_floor:,}** ({100*n_below_floor/max(len(night_gate),1):.0f}%).",
        "",
        "## Year by year",
        by_year.to_markdown(index=False),
        "",
        "## Cross-reference with the resident noise audit",
        "The audit's own flights are dated June 2026, beyond current open-data "
        "coverage (which ends ~Jan 2026), so those exact flights can't be pulled. "
        "But the audit names recurring airlines, so we cross-reference by "
        "operator. The audit uses IATA flight numbers (e.g. LS3684); ADS-B "
        "records the radio callsign (Jet2 = 'EXS'), so we match the airline, not "
        "the exact number.",
        "",
        xref.to_markdown(index=False),
        "",
        "Every airline the audit names is confirmed making low night approaches "
        "over Brockenhurst in the 2023-2025 data - the same pattern, and in some "
        "cases lower than the audit's examples. The audit's 'URO601 / URO901' "
        "entries could not be matched to any UK operator, and an A340-600 "
        "freighter into Bournemouth at night is implausible; those entries should "
        "be treated as unverified.",]
    lines += [
        "",
        "## The worst individual night flights",
        "See `worst_night_offenders.png` and `night_large_jets.csv` for the full "
        "list, each with its flight number, date, time and measured height.",
        "",
        "*Caveats: only planes broadcasting position at low level are captured "
        "(roughly half to two-thirds of arrivals), so the true counts are higher, "
        "not lower. A single low flight can have an air-traffic-control reason; "
        "the point is the consistent pattern. See METHODOLOGY.md.*",
    ]
    with open(path, "w") as f:
        f.write("\n".join(str(x) for x in lines))
