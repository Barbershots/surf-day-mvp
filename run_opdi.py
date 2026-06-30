#!/usr/bin/env python3
"""
End-to-end analysis of Bournemouth (EGHH) arrivals over Brockenhurst, using
OPDI open data (no account required).

Examples
--------
    # One 10-day window (fast, ~1 file to download)
    python run_opdi.py --start 2025-06-04 --end 2025-06-14

    # A whole year (downloads ~36 event files; cached in ./data afterwards)
    python run_opdi.py --start 2025-01-01 --end 2025-12-31 --large-jet-only

Outputs (written to --outdir, default ./outputs):
    per_flight.csv   one row per arrival with compliance flags
    summary.json     headline numbers
    *.png            charts
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime

from brockenhurst import approach, charts, opdi


def _d(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", required=True, type=_d, help="YYYY-MM-DD (inclusive)")
    ap.add_argument("--end", required=True, type=_d, help="YYYY-MM-DD (exclusive)")
    ap.add_argument("--large-jet-only", action="store_true",
                    help="restrict to multi-engine commercial jets")
    ap.add_argument("--outdir", default="outputs")
    ap.add_argument("--no-charts", action="store_true")
    args = ap.parse_args()

    print(f"Loading EGHH arrivals {args.start} .. {args.end} from OPDI ...")
    arr, events = opdi.load_period(args.start, args.end,
                                   large_jet_only=args.large_jet_only)
    print(f"  {len(arr)} arrivals, {events['flight_id'].nunique()} with trajectory events")

    pf = approach.per_flight(arr, events)
    summ = approach.summary(pf)
    summ["period"] = {"start": args.start.isoformat(), "end": args.end.isoformat(),
                      "large_jet_only": args.large_jet_only}

    os.makedirs(args.outdir, exist_ok=True)
    pf.to_csv(os.path.join(args.outdir, "per_flight.csv"), index=False)
    with open(os.path.join(args.outdir, "summary.json"), "w") as f:
        json.dump(summ, f, indent=2, default=str)

    if not args.no_charts:
        charts.make_all(arr, events, pf, summ, args.outdir)

    print("\n=== Summary ===")
    print(json.dumps(summ, indent=2, default=str))
    print(f"\nWrote per_flight.csv, summary.json and charts to {args.outdir}/")


if __name__ == "__main__":
    main()
