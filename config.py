"""
Configuration for the Bournemouth / Brockenhurst noise-compliance analysis.

All distances are in kilometres unless a name ends in `_nm` (nautical miles)
or `_ft` (feet). Coordinates are WGS-84 decimal degrees.

The numbers here are the *assumptions the whole analysis rests on*. They are
deliberately collected in one place so they can be challenged, cited, or tuned
without touching the analysis code. See METHODOLOGY.md for how each was derived.
"""

# --- Geography ----------------------------------------------------------------

# Bournemouth Airport (EGHH) aerodrome reference point.
EGHH = (50.7805, -1.8396)
EGHH_ELEV_FT = 38  # AIP aerodrome elevation

# Runway 26 threshold (the end aircraft land *towards* on a westerly approach;
# it is the eastern threshold, i.e. the one nearest Brockenhurst). The ILS DME
# (IBH) reads zero here, so DME-from-IBH == distance-from-26-threshold.
# Offset ~0.6 NM east of the reference point along the runway.
RWY26_THRESHOLD = (50.7793, -1.8226)

# Brockenhurst village centre (the community being overflown).
BROCKENHURST = (50.8189, -1.5757)

# Final approach track for runway 26, degrees TRUE. Charted as 255 deg
# (magnetic); UK magnetic variation here is ~0 deg, so true ~= magnetic.
RWY26_APPROACH_TRACK_DEG = 255.0
# The reciprocal: the bearing FROM the airport OUT along the approach corridor,
# i.e. the direction inbound traffic comes from. Brockenhurst sits on this line.
RWY26_OUTBOUND_TRACK_DEG = (RWY26_APPROACH_TRACK_DEG + 180.0) % 360.0  # 075 deg

# --- The Brockenhurst gate ----------------------------------------------------

# An aircraft is treated as "over Brockenhurst" when it is within this radius of
# the village AND within the approach corridor (cross-track limit below).
GATE_RADIUS_KM = 3.0
# "Near the village" - a slightly wider radius used to count level-offs that
# happen over/around Brockenhurst specifically (as opposed to the normal ILS
# platform level-off on short final, ~4 NM from touchdown).
NEAR_VILLAGE_KM = 6.0
# Half-width of the approach corridor about the extended runway-26 centreline.
# Inbound jets fanned out wider than this are being radar-vectored, not yet
# established, and are handled separately.
CORRIDOR_HALF_WIDTH_KM = 4.0

# --- Compliance thresholds ----------------------------------------------------

# A standard 3-degree approach gains/loses ~318 ft per nautical mile.
GLIDESLOPE_DEG = 3.0

# Regulatory hard floor from the Bournemouth Noise Abatement (Arrivals) page:
# turbo-powered / >5700 kg aircraft "shall not descend below 2000' before
# intercepting the GS". Anything crossing Brockenhurst below this is a clear
# breach of the published procedure.
HARD_FLOOR_FT = 2000

# Altitude a textbook continuous-descent approach (CDA) would be at when over
# Brockenhurst, computed from the 3-deg path extended back from the 26 threshold.
# Filled in at runtime by geometry.expected_cda_altitude_ft(); this is a cached
# convenience value (~3,100 ft) used for labelling charts.
CDA_PROFILE_FT = 3100

# CDA means an *uninterrupted* descent. Any level segment detected inside the
# corridor below this altitude is treated as a non-CDA event (the aircraft has
# levelled off, which requires re-applying engine power -> noise).
LEVEL_OFF_CEILING_FT = 6000

# --- Aircraft classification (mirrors the user's existing dashboards) ----------

# ICAO aircraft class codes in OPDI flight_list (icao_aircraft_class):
# L = landplane, digit = engine count, J=jet/T=turboprop/P=piston.
# "Large jet" (commercial narrow/widebody) ~= multi-engine jet.
LARGE_JET_CLASSES = {"L2J", "L3J", "L4J"}

# --- Time periods (Heathrow-style curfew framing, matching your dashboards) ----
# Local-time hour boundaries.
DAY_START_H, EVENING_START_H, NIGHT_START_H, NIGHT_END_H = 6, 19, 23, 6

# --- OPDI data source ---------------------------------------------------------

OPDI_BASE = "https://www.eurocontrol.int/performance/data/download/OPDI/v002"
OPDI_FLIGHT_LIST = OPDI_BASE + "/flight_list/flight_list_{ym}.parquet"
OPDI_FLIGHT_EVENTS = OPDI_BASE + "/flight_events/flight_events_{start}_{end}.parquet"

DEST_AIRPORT = "EGHH"
