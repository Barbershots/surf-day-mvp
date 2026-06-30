"""
Classify each arrival into an aircraft category and a time-of-day window.

Categories mirror the existing dashboards (Large jet / Business jet / Turboprop /
GA-light / Helicopter / Other). "Large jet" means a commercial narrow- or
wide-body airliner (B737, A320 family, etc.) - NOT a business jet. The
classification is by ICAO type designator, with the OPDI `icao_aircraft_class`
as a fallback. Sets are explicit on purpose: in a compliance context it must be
auditable exactly which types were counted as airliners.
"""
from __future__ import annotations

from zoneinfo import ZoneInfo

import pandas as pd

import config

LONDON = ZoneInfo("Europe/London")

# --- Commercial airliners (the "large jet" group the case is about) -----------
LARGE_JET = {
    # Airbus narrowbody
    "A318", "A319", "A320", "A321", "A19N", "A20N", "A21N",
    # Airbus widebody
    "A300", "A306", "A310", "A332", "A333", "A338", "A339",
    "A342", "A343", "A345", "A346", "A359", "A35K", "A388",
    # Airbus A220 (formerly C-series)
    "BCS1", "BCS3",
    # Boeing 737 (classic, NG, MAX)
    "B731", "B732", "B733", "B734", "B735", "B736", "B737", "B738", "B739",
    "B37M", "B38M", "B39M", "B3XM",
    # Boeing 727 / 757 / 767 / 777 / 787 / 747 / 717
    "B722", "B752", "B753", "B762", "B763", "B764",
    "B772", "B773", "B77L", "B77W", "B788", "B789", "B78X",
    "B741", "B742", "B743", "B744", "B748", "B712",
    # Embraer E-jets
    "E170", "E75L", "E75S", "E190", "E195", "E290", "E295",
    # Regional jets / older types
    "CRJ1", "CRJ2", "CRJ7", "CRJ9", "CRJX",
    "RJ85", "RJ1H", "F70", "F100", "MD81", "MD82", "MD83", "MD87", "MD88",
    "MD90", "SU95", "E135", "E145",
}

# --- Business / executive jets (explicitly NOT "large jet") --------------------
BUSINESS_JET = {
    "FA10", "FA20", "FA50", "FA7X", "FA8X", "F2TH", "F900", "F900EX",
    "GLF2", "GLF3", "GLF4", "GLF5", "GLF6", "G150", "G280", "GALX",
    "GL5T", "GL7T", "GLEX", "CL30", "CL35", "CL60", "CL64",
    "C25A", "C25B", "C25C", "C500", "C501", "C510", "C525", "C526",
    "C550", "C551", "C560", "C56X", "C650", "C680", "C68A", "C700", "C750",
    "LJ31", "LJ35", "LJ40", "LJ45", "LJ55", "LJ60", "LJ70", "LJ75",
    "E50P", "E55P", "PC24", "H25A", "H25B", "H25C", "HA4T", "BE40", "BE4W",
    "PRM1", "EA50", "SF50", "G650", "G550", "G450",
}

TURBOPROP = {
    "AT43", "AT44", "AT45", "AT46", "AT72", "AT73", "AT75", "AT76",
    "DH8A", "DH8B", "DH8C", "DH8D", "DH8", "SF34", "SB20", "SW4", "SW3",
    "JS31", "JS32", "JS41", "B190", "E110", "E120", "D328", "C208", "C212",
    "PC12", "PC6T", "BE20", "B350", "BE9L", "BE10", "DHC6", "DHC7", "F27",
    "AN24", "AN26", "L410",
}

GA_LIGHT_CLASSES = {"L1P", "L2P"}     # single/twin piston
HELICOPTER_PREFIX = "H"               # icao_aircraft_class H1T, H2T, H1P ...


def _clean(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip().upper()


def aircraft_category(typecode, icao_class) -> str:
    tc = _clean(typecode)
    cls = _clean(icao_class)
    if cls.startswith(HELICOPTER_PREFIX):
        return "Helicopter"
    if tc in LARGE_JET:
        return "Large jet"
    if tc in BUSINESS_JET:
        return "Business jet"
    if tc in TURBOPROP:
        return "Turboprop"
    # Fall back to the ICAO class when the exact type isn't in our lists.
    if cls in GA_LIGHT_CLASSES:
        return "GA / light"
    if cls.endswith("J"):
        # An unlisted jet: treat as business/other jet, not a commercial airliner.
        return "Business jet"
    if cls.endswith("T"):
        return "Turboprop"
    if cls.endswith("P"):
        return "GA / light"
    return "Other"


def time_window(landing_utc) -> str:
    """Day / Evening / Night using UK local time at the landing moment."""
    if pd.isna(landing_utc):
        return "Unknown"
    ts = pd.Timestamp(landing_utc)
    ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts
    h = ts.tz_convert(LONDON).hour
    if config.NIGHT_START_H <= h or h < config.NIGHT_END_H:
        return "Night"
    if config.EVENING_START_H <= h < config.NIGHT_START_H:
        return "Evening"
    return "Day"


def add_classification(df: pd.DataFrame,
                       typecode_col="typecode",
                       class_col="icao_aircraft_class",
                       landing_col="last_seen") -> pd.DataFrame:
    out = df.copy()
    out["category"] = [
        aircraft_category(tc, cl)
        for tc, cl in zip(out[typecode_col], out[class_col])
    ]
    out["is_large_jet"] = out["category"] == "Large jet"
    out["time_window"] = out[landing_col].map(time_window)
    return out
