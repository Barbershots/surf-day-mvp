"""
Turn raw flight_events into approach-compliance evidence.

The core question: are arrivals flying a quiet, low-power *continuous descent
approach* (CDA) over Brockenhurst, or are they dragged in low and level (which
needs engine power, hence noise)?

Two independent lines of evidence are produced:

1. LEVEL-OFFS IN THE CORRIDOR. A CDA has no level flight. Every `level-start`
   event inside the approach corridor below `LEVEL_OFF_CEILING_FT` is a flight
   interrupting its descent. We record the lowest such level-off per flight.

2. ALTITUDE vs THE 3-DEGREE PROFILE. For every event with a position, we know
   its distance from the runway-26 threshold and therefore the altitude a
   compliant 3-degree continuous descent would be at. Events at or below that
   line near Brockenhurst show aircraft no higher than the glidepath far too
   early, i.e. not "as high as practicable".
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config
from . import geometry as geo

LEVEL_TYPES = ("level-start", "level-end")


def annotate(events: pd.DataFrame) -> pd.DataFrame:
    """Add geometry + the compliant-profile altitude to every event."""
    e = events.dropna(subset=["latitude", "longitude", "altitude"]).copy()
    e["d_brock_km"] = geo.haversine_km(e["latitude"], e["longitude"], *config.BROCKENHURST)
    e["d_eghh_km"] = geo.haversine_km(e["latitude"], e["longitude"], *config.EGHH)
    e["dist_thr_nm"] = geo.dist_from_threshold_nm(e["latitude"], e["longitude"])
    e["xtk_km"] = np.abs(geo.cross_track_km(e["latitude"], e["longitude"],
                                            config.EGHH, config.RWY26_OUTBOUND_TRACK_DEG))
    e["cda_profile_ft"] = geo.glideslope_altitude_ft(e["dist_thr_nm"])
    e["in_corridor"] = geo.in_approach_corridor(e["latitude"], e["longitude"])
    e["in_gate"] = geo.in_brockenhurst_gate(e["latitude"], e["longitude"])
    return e


def corridor_level_offs(events: pd.DataFrame) -> pd.DataFrame:
    """Every level-start inside the approach corridor below the ceiling."""
    e = events
    mask = (
        (e["type"] == "level-start")
        & e["in_corridor"]
        & (e["altitude"] <= config.LEVEL_OFF_CEILING_FT)
        & (e["altitude"] > 0)
    )
    return e[mask].copy()


def village_level_offs(events: pd.DataFrame) -> pd.DataFrame:
    """
    Level-starts within NEAR_VILLAGE_KM of Brockenhurst. These are the
    directly-relevant ones: an aircraft levelling off (and therefore adding
    power) right over the community - not the routine ILS platform on short
    final, which is ~9 km closer to the airport.
    """
    e = events
    mask = (
        (e["type"] == "level-start")
        & (e["d_brock_km"] <= config.NEAR_VILLAGE_KM)
        & e["in_corridor"]
        & (e["altitude"] > 0)
    )
    return e[mask].copy()


def gate_altitudes(events: pd.DataFrame) -> pd.DataFrame:
    """
    The altitude of each flight as it passes through the Brockenhurst gate.
    Where several events fall in the gate, keep the one closest to the village.
    This is the closest thing the sparse event data gives to a direct
    "altitude over Brockenhurst" reading.
    """
    g = events[events["in_gate"] & (events["altitude"] > 0)].copy()
    g = g.sort_values("d_brock_km").groupby("flight_id", as_index=False).first()
    g["alt_vs_cda_ft"] = g["altitude"] - g["cda_profile_ft"]
    g["below_hard_floor"] = g["altitude"] < config.HARD_FLOOR_FT
    return g


def per_flight(arrivals: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """
    One row per arrival flight that produced usable events, with the compliance
    flags that matter for the noise case.
    """
    e = annotate(events)
    los = corridor_level_offs(e)
    village = village_level_offs(e)
    gates = gate_altitudes(e)

    # Lowest corridor level-off per flight.
    lo = (
        los.sort_values("altitude")
        .groupby("flight_id", as_index=False)
        .agg(lowest_leveloff_ft=("altitude", "first"),
             leveloff_d_brock_km=("d_brock_km", "first"),
             n_leveloffs=("altitude", "size"))
    )

    # Level-offs specifically over/around the village.
    vlo = (
        village.sort_values("altitude")
        .groupby("flight_id", as_index=False)
        .agg(village_leveloff_ft=("altitude", "first"),
             n_village_leveloffs=("altitude", "size"))
    )

    base = (
        arrivals[["id", "flt_id", "typecode", "icao_aircraft_class",
                  "is_large_jet", "last_seen", "dof"]]
        .rename(columns={"id": "flight_id"})
    )
    # Keep only flights we actually have events for.
    seen = set(e["flight_id"])
    out = base[base["flight_id"].isin(seen)].merge(lo, on="flight_id", how="left")
    out = out.merge(vlo, on="flight_id", how="left")
    out = out.merge(
        gates[["flight_id", "altitude", "alt_vs_cda_ft", "below_hard_floor"]]
        .rename(columns={"altitude": "gate_alt_ft"}),
        on="flight_id", how="left",
    )

    out["has_corridor_leveloff"] = out["n_leveloffs"].fillna(0) > 0
    out["n_leveloffs"] = out["n_leveloffs"].fillna(0).astype(int)
    out["n_village_leveloffs"] = out["n_village_leveloffs"].fillna(0).astype(int)
    out["leveloff_over_village"] = out["n_village_leveloffs"] > 0
    # A flight is flagged non-CDA if it levelled off in the corridor on the way in.
    out["non_cda"] = out["has_corridor_leveloff"]
    # Hard breach: an actual gate reading below the 2000' floor.
    out["breach_hard_floor"] = out["below_hard_floor"].fillna(False)
    return out.drop(columns=["below_hard_floor"])


def summary(per_flight_df: pd.DataFrame) -> dict:
    """Headline numbers for the report."""
    d = per_flight_df
    n = len(d)
    lj = d[d["is_large_jet"]]
    have_gate = d["gate_alt_ft"].notna()
    have_village = d["leveloff_over_village"]
    return {
        "arrivals_with_events": int(n),
        "large_jet_arrivals": int(len(lj)),
        # Level-offs anywhere in the inbound corridor (includes routine short-final platform).
        "with_corridor_leveloff": int(d["non_cda"].sum()),
        "pct_with_corridor_leveloff": round(100 * d["non_cda"].mean(), 1) if n else 0.0,
        "lj_pct_with_corridor_leveloff": round(100 * lj["non_cda"].mean(), 1) if len(lj) else 0.0,
        # Level-offs specifically over the village (the directly-relevant signal).
        "leveloff_over_village": int(have_village.sum()),
        "pct_leveloff_over_village": round(100 * have_village.mean(), 1) if n else 0.0,
        "median_village_leveloff_ft": float(np.nanmedian(d.loc[have_village, "village_leveloff_ft"])) if have_village.any() else None,
        # Direct altitude readings at the Brockenhurst gate vs the compliant 3-deg profile.
        "flights_with_gate_reading": int(have_gate.sum()),
        "median_gate_alt_ft": float(np.nanmedian(d.loc[have_gate, "gate_alt_ft"])) if have_gate.any() else None,
        "gate_below_hard_floor": int(d["breach_hard_floor"].sum()),
        "gate_below_cda_profile": int((d["alt_vs_cda_ft"] < 0).sum()),
        "expected_cda_alt_over_brockenhurst_ft": round(geo.expected_cda_altitude_ft()),
        "hard_floor_ft": config.HARD_FLOOR_FT,
    }
