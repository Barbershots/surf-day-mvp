"""Sanity checks on the geometry and the compliance thresholds."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config
from brockenhurst import geometry as geo


def test_brockenhurst_distance_and_bearing():
    # Brockenhurst is ~10 NM from the field, on the runway-26 approach line.
    d_km = geo.haversine_km(*config.EGHH, *config.BROCKENHURST)
    assert 18 < d_km < 20, d_km
    brg = geo.initial_bearing_deg(*config.EGHH, *config.BROCKENHURST)
    # Within a few degrees of the 075-degree outbound approach track.
    assert abs(brg - config.RWY26_OUTBOUND_TRACK_DEG) < 6, brg


def test_brockenhurst_on_corridor_centreline():
    # Cross-track distance from the extended centreline should be small (<2 km).
    xtk = geo.cross_track_km(*config.BROCKENHURST, config.EGHH,
                             config.RWY26_OUTBOUND_TRACK_DEG)
    assert abs(xtk) < 2.0, xtk


def test_glideslope_318ft_per_nm():
    # A 3-degree path climbs ~318 ft per NM.
    step = geo.glideslope_altitude_ft(2) - geo.glideslope_altitude_ft(1)
    assert 310 < step < 325, step


def test_expected_cda_altitude_band():
    # Compliant CDA over Brockenhurst should be ~3,000-3,200 ft.
    alt = geo.expected_cda_altitude_ft()
    assert 2900 < alt < 3300, alt
    # ...and well above the 2,000 ft regulatory floor.
    assert alt > config.HARD_FLOOR_FT


def test_gate_membership():
    # The village itself is inside the gate; a point 30 km away is not.
    assert bool(geo.in_brockenhurst_gate(*config.BROCKENHURST))
    assert not bool(geo.in_brockenhurst_gate(51.15, -0.18))  # ~Gatwick-ish


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("all geometry tests passed")
