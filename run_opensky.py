#!/usr/bin/env python3
"""
Dense per-flight altitude over Brockenhurst from raw OpenSky state vectors.

This fills the coverage gap in the OPDI path: instead of only the ~1-in-5 night
arrivals that happen to broadcast a level-off/crossing event near the village,
this reads the full 10-second trajectory and gives an EXACT over-village height
(plus groundspeed and vertical rate) for essentially every arrival that passes
through the Brockenhurst box.

Requires a free OpenSky account with Trino access:
    pip install "pyopensky>=2.0"
    # put credentials in ~/.config/pyopensky/settings.conf  (see
    #   https://opensky-network.org/data/trino )

Example (one night):
    python run_opensky.py --start "2025-06-08 22:00" --stop "2025-06-09 06:00"

Output: outputs/opensky_overflights.csv - one row per pass through the box, with
height over Brockenhurst, vs the 2,000 ft floor and the ~3,116 ft profile, and
whether the aircraft was level (near-zero vertical rate) directly overhead.
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime

import pandas as pd

from brockenhurst import opensky


def _dt(s: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise SystemExit(f"bad datetime: {s!r} (use 'YYYY-MM-DD HH:MM')")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", action="store_true",
                    help="snapshot of aircraft over Brockenhurst RIGHT NOW via the "
                         "anonymous live API (no account needed) - for a quick check")
    ap.add_argument("--start", type=_dt, help="historical window start 'YYYY-MM-DD HH:MM'")
    ap.add_argument("--stop", type=_dt, help="historical window stop")
    ap.add_argument("--out", default="outputs/opensky_overflights.csv")
    ap.add_argument("--arriving-icao24", default=None,
                    help="optional CSV/parquet with an 'icao24' column (e.g. sweep "
                         "arrivals.csv) to keep only EGHH arrivals and drop through-traffic")
    args = ap.parse_args()

    if args.live:
        sv = opensky.fetch_live_box()
        print(f"Live snapshot: {len(sv)} aircraft in the Brockenhurst area now")
    else:
        if not (args.start and args.stop):
            raise SystemExit("provide --start and --stop for a historical run, or --live")
        # Credentials come from env vars OPENSKY_CLIENT_ID / OPENSKY_CLIENT_SECRET
        # (or OPENSKY_USERNAME / OPENSKY_PASSWORD). pyopensky reads them itself.
        if not (os.environ.get("OPENSKY_CLIENT_ID") or os.environ.get("OPENSKY_USERNAME")):
            raise SystemExit(
                "No OpenSky credentials found. Set OPENSKY_CLIENT_ID and "
                "OPENSKY_CLIENT_SECRET (from opensky-network.org -> Account -> API "
                "clients) as environment variables/secrets, then re-run. See README.")
        print(f"Querying OpenSky history in the Brockenhurst box "
              f"{args.start} .. {args.stop} ...")
        sv = opensky.fetch_box(args.start, args.stop)
        print(f"  {len(sv):,} state vectors")

    keep = None
    if args.arriving_icao24:
        f = args.arriving_icao24
        ref = pd.read_parquet(f) if f.endswith(".parquet") else pd.read_csv(f)
        keep = set(ref["icao24"].dropna().astype(str))

    out = opensky.overflight_altitudes(sv, arriving_icao24=keep)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    out.to_csv(args.out, index=False)
    print(f"\n{len(out)} overflights -> {args.out}")
    if len(out):
        below = int((out["below_hard_floor"]).sum())
        level = int((out["level_over_village"]).sum())
        print(f"  below 2,000 ft floor: {below}")
        print(f"  level (near-zero climb/descent) directly overhead: {level}")


if __name__ == "__main__":
    main()
