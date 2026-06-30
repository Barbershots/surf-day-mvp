"""
Great-circle geometry helpers and the expected continuous-descent profile.

Vectorised: every function accepts scalars or numpy arrays / pandas Series, so
it can be applied to a whole column of event positions at once.
"""
from __future__ import annotations

import numpy as np

import config

EARTH_R_KM = 6371.0088
FT_PER_NM = 6076.12
KM_PER_NM = 1.852


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in kilometres."""
    p = np.pi / 180.0
    lat1, lon1, lat2, lon2 = (np.asarray(x, dtype=float) for x in (lat1, lon1, lat2, lon2))
    a = (
        np.sin((lat2 - lat1) * p / 2) ** 2
        + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2
    )
    return 2 * EARTH_R_KM * np.arcsin(np.sqrt(a))


def initial_bearing_deg(lat1, lon1, lat2, lon2):
    """Initial bearing (degrees true, 0-360) from point 1 to point 2."""
    p = np.pi / 180.0
    lat1, lon1, lat2, lon2 = (np.asarray(x, dtype=float) for x in (lat1, lon1, lat2, lon2))
    dlon = (lon2 - lon1) * p
    y = np.sin(dlon) * np.cos(lat2 * p)
    x = np.cos(lat1 * p) * np.sin(lat2 * p) - np.sin(lat1 * p) * np.cos(lat2 * p) * np.cos(dlon)
    return (np.degrees(np.arctan2(y, x)) + 360.0) % 360.0


def cross_track_km(lat, lon, origin, track_deg):
    """
    Signed perpendicular distance (km) of a point from the great-circle line that
    starts at `origin` and runs along bearing `track_deg`. Sign indicates side;
    we only care about the magnitude for corridor membership.
    """
    olat, olon = origin
    d13 = haversine_km(olat, olon, lat, lon) / EARTH_R_KM  # angular distance
    theta13 = np.radians(initial_bearing_deg(olat, olon, lat, lon))
    theta12 = np.radians(track_deg)
    return np.arcsin(np.sin(d13) * np.sin(theta13 - theta12)) * EARTH_R_KM


def dist_from_threshold_nm(lat, lon):
    """Distance from the runway-26 threshold in nautical miles (== DME from IBH)."""
    tlat, tlon = config.RWY26_THRESHOLD
    return haversine_km(lat, lon, tlat, tlon) / KM_PER_NM


def glideslope_altitude_ft(dist_nm, gs_deg=None, threshold_elev_ft=None):
    """
    Altitude (ft AMSL) of a `gs_deg` glidepath at `dist_nm` from the threshold.
    This is the height a *compliant continuous-descent* aircraft should be at.
    """
    gs_deg = config.GLIDESLOPE_DEG if gs_deg is None else gs_deg
    elev = config.EGHH_ELEV_FT if threshold_elev_ft is None else threshold_elev_ft
    return elev + np.tan(np.radians(gs_deg)) * np.asarray(dist_nm, dtype=float) * FT_PER_NM


def expected_cda_altitude_ft():
    """The 3-degree CDA profile altitude directly over Brockenhurst."""
    d_nm = dist_from_threshold_nm(*config.BROCKENHURST)
    return float(glideslope_altitude_ft(d_nm))


def in_brockenhurst_gate(lat, lon, radius_km=None, corridor_half_width_km=None):
    """
    Boolean mask: point is within `radius_km` of Brockenhurst AND within the
    runway-26 approach corridor (|cross-track| <= corridor_half_width_km).
    """
    radius_km = config.GATE_RADIUS_KM if radius_km is None else radius_km
    half = config.CORRIDOR_HALF_WIDTH_KM if corridor_half_width_km is None else corridor_half_width_km
    near = haversine_km(lat, lon, *config.BROCKENHURST) <= radius_km
    xtk = np.abs(cross_track_km(lat, lon, config.EGHH, config.RWY26_OUTBOUND_TRACK_DEG))
    return near & (xtk <= half)


def in_approach_corridor(lat, lon, max_dist_km=40.0, corridor_half_width_km=None):
    """
    Boolean mask for the wider approach corridor east of the field: on the
    approach side, within the corridor half-width, out to `max_dist_km`.
    Used to find level-offs anywhere on the inbound path, not just at the gate.
    """
    half = config.CORRIDOR_HALF_WIDTH_KM if corridor_half_width_km is None else corridor_half_width_km
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    d = haversine_km(lat, lon, *config.EGHH)
    xtk = np.abs(cross_track_km(lat, lon, config.EGHH, config.RWY26_OUTBOUND_TRACK_DEG))
    on_approach_side = lon > config.EGHH[1]  # east of the field
    return (d <= max_dist_km) & (xtk <= half) & on_approach_side
