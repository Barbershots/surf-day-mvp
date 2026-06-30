"""
OPTIONAL: dense altitude-over-Brockenhurst readings from OpenSky state vectors.

The OPDI path (opdi.py) gives sparse *milestone* events - level-offs and flight-
level crossings - which is enough to prove non-continuous descent. If you want a
direct altitude reading for *every single* arrival exactly as it passes over
Brockenhurst (e.g. to publish a per-flight table), pull the raw ADS-B state
vectors from OpenSky, which OPDI is itself derived from.

This needs a free OpenSky account with Trino access. Install + configure:

    pip install "pyopensky>=2.0"
    # then put your credentials in ~/.config/pyopensky/settings.conf
    # see https://opensky-network.org/data/trino

Each state vector has barometric + geometric altitude on a ~10-second cadence,
so closest-approach altitude to the village is essentially exact.
"""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

import config
from . import geometry as geo

# Bounding box around Brockenhurst (west, south, east, north) ~ +/- 4 km.
_DLAT = 4.0 / 111.0
_DLON = 4.0 / (111.0 * np.cos(np.radians(config.BROCKENHURST[0])))
BROCKENHURST_BBOX = (
    config.BROCKENHURST[1] - _DLON,  # west
    config.BROCKENHURST[0] - _DLAT,  # south
    config.BROCKENHURST[1] + _DLON,  # east
    config.BROCKENHURST[0] + _DLAT,  # north
)


def fetch_box(start: datetime, stop: datetime, bbox=BROCKENHURST_BBOX) -> pd.DataFrame:
    """All state vectors inside the Brockenhurst box between start and stop."""
    from pyopensky.trino import Trino  # imported lazily; only needed for this path

    trino = Trino()
    return trino.history(
        start, stop, bounds=bbox,
        selected_columns=(
            "time", "icao24", "callsign", "lat", "lon",
            "baroaltitude", "geoaltitude", "velocity", "vertrate", "onground",
        ),
    )


def overflight_altitudes(state_vectors: pd.DataFrame,
                         arriving_icao24: set | None = None) -> pd.DataFrame:
    """
    Reduce raw state vectors to one row per overflight: the altitude (and
    groundspeed / vertical rate as power proxies) at closest approach to the
    village. A near-zero vertical rate here is a level-off directly overhead.

    Pass `arriving_icao24` (from opdi.arrivals()['icao24']) to keep only EGHH
    arrivals and drop overflying through-traffic.
    """
    sv = state_vectors.dropna(subset=["lat", "lon"]).copy()
    if arriving_icao24 is not None:
        sv = sv[sv["icao24"].isin(arriving_icao24)]
    sv["alt_ft"] = sv["geoaltitude"].fillna(sv["baroaltitude"]) * 3.28084
    sv["d_brock_km"] = geo.haversine_km(sv["lat"], sv["lon"], *config.BROCKENHURST)

    # One pass = one contiguous run of points for a given aircraft. Split when
    # the same icao24 reappears after a > 20 min gap.
    sv = sv.sort_values(["icao24", "time"])
    gap = sv.groupby("icao24")["time"].diff().dt.total_seconds().fillna(0) > 1200
    sv["pass_id"] = sv["icao24"].astype(str) + "_" + gap.groupby(sv["icao24"]).cumsum().astype(str)

    closest = sv.sort_values("d_brock_km").groupby("pass_id", as_index=False).first()
    closest["below_hard_floor"] = closest["alt_ft"] < config.HARD_FLOOR_FT
    closest["alt_vs_cda_ft"] = closest["alt_ft"] - geo.expected_cda_altitude_ft()
    # |vertrate| < ~1.5 ft/s (~90 fpm) over the village == levelling off overhead.
    closest["level_over_village"] = closest["vertrate"].abs() < 1.5 * 0.3048
    return closest[["pass_id", "icao24", "callsign", "time", "alt_ft",
                    "alt_vs_cda_ft", "below_hard_floor", "vertrate",
                    "velocity", "level_over_village", "d_brock_km"]]
