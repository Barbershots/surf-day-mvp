#!/usr/bin/env python3
"""
Recent 24-hour snapshot from the OpenSky REST API (your client credentials), for
cross-checking against the airport's WebTrak while the data is still live there.

Unlike the OPDI snapshots (sparse milestone points, ~1 in 5 with a height), this
reads the FULL trajectory of every arrival, so the over-village height is exact
and coverage is complete.

    python recent_snapshot.py --date 2026-07-04     # a recent complete local day

Needs OPENSKY_CLIENT_ID / OPENSKY_CLIENT_SECRET in the environment (already set).
Only works for the last ~30 days (OpenSky retention).
"""
from __future__ import annotations

import argparse
import os
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

import config
from brockenhurst import geometry as geo

PROPER, FLOOR = 3116, 2000
RED, GOLD, BLUE, INK = "#c0392b", "#e8a020", "#2c6fbb", "#222"
NAMES = {"RYR": "Ryanair", "EXS": "Jet2", "TOM": "TUI", "EZY": "easyJet", "TUI": "TUI fly",
         "WZZ": "Wizz Air", "EIN": "Aer Lingus", "VIR": "Virgin", "LAV": "AlbaStar",
         "BRO": "2Excel", "RUK": "Ryanair UK", "EJU": "easyJet", "URO": "European Cargo"}
API = "https://opensky-network.org/api"


def token():
    r = requests.post("https://auth.opensky-network.org/auth/realms/opensky-network/"
                      "protocol/openid-connect/token",
                      data={"grant_type": "client_credentials",
                            "client_id": os.environ["OPENSKY_CLIENT_ID"],
                            "client_secret": os.environ["OPENSKY_CLIENT_SECRET"]}, timeout=40)
    r.raise_for_status()
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def build(date_str):
    day = pd.Timestamp(date_str, tz="Europe/London")
    begin = int(day.tz_convert("UTC").timestamp())
    end = int((day + pd.Timedelta(days=1)).tz_convert("UTC").timestamp())
    h = token()
    arr = requests.get(f"{API}/flights/arrival",
                       params={"airport": "EGHH", "begin": begin, "end": end},
                       headers=h, timeout=90)
    arr.raise_for_status()
    flights = arr.json()
    print(f"{len(flights)} arrivals into EGHH on {day:%Y-%m-%d}")

    rows = []
    for i, f in enumerate(flights):
        try:
            tr = requests.get(f"{API}/tracks/all",
                              params={"icao24": f["icao24"], "time": f["firstSeen"]},
                              headers=h, timeout=60)
            if tr.status_code != 200:
                continue
            path = tr.json().get("path", [])
        except Exception:
            continue
        time.sleep(0.25)
        if not path:
            continue
        p = pd.DataFrame(path, columns=["time", "lat", "lon", "baro_m", "trk", "onground"])
        p = p.dropna(subset=["lat", "lon", "baro_m"])
        if p.empty:
            continue
        p["d"] = geo.haversine_km(p["lat"], p["lon"], *config.BROCKENHURST)
        near = p[p["d"] < 3.0]
        if near.empty:
            continue
        c = near.loc[near["d"].idxmin()]
        alt_ft = c["baro_m"] * 3.28084
        if not (300 < alt_ft < 6000):
            continue
        rows.append(dict(t=pd.to_datetime(c["time"], unit="s", utc=True).tz_convert("Europe/London"),
                         callsign=str(f.get("callsign", "")).strip(),
                         adep=f.get("estDepartureAirport"),
                         alt_ft=round(alt_ft)))
    d = pd.DataFrame(rows)
    if d.empty:
        print("no over-village crossings found (aircraft may have landed the other way)")
        return
    d["hr"] = d["t"].dt.hour + d["t"].dt.minute / 60
    d["airline"] = d["callsign"].str[:3].map(NAMES).fillna(d["callsign"].str[:3])
    d = d.sort_values("hr")

    fig, ax = plt.subplots(figsize=(13, 7))
    ax.axvspan(0, 6.5, color="#1b2a4a", alpha=0.06); ax.axvspan(21.5, 24, color="#1b2a4a", alpha=0.06)
    ax.axhline(PROPER, color=GOLD, lw=1.8, ls="--", label="quiet 3-degree descent (3,116 ft)")
    ax.axhline(FLOOR, color=RED, lw=1.6, ls=":", label="2,000 ft floor")
    for _, r in d.iterrows():
        c = RED if r["alt_ft"] < FLOOR else GOLD if r["alt_ft"] < PROPER else BLUE
        ax.scatter(r["hr"], r["alt_ft"], s=95, color=c, edgecolors="white", linewidths=0.8, zorder=4)
        ax.annotate(r["callsign"], (r["hr"], r["alt_ft"]), xytext=(0, 9),
                    textcoords="offset points", ha="center", fontsize=7.5, color=INK)
    ax.set_xlim(0, 24); ax.set_ylim(0, 5200)
    ax.set_xticks(range(0, 25, 2)); ax.set_xticklabels([f"{x:02d}:00" for x in range(0, 25, 2)], fontsize=8.5)
    ax.set_xlabel("time of day (local)", fontsize=10); ax.set_ylabel("height over Brockenhurst (ft)", fontsize=10)
    ax.grid(alpha=0.2)
    lowband = int((d["alt_ft"] <= PROPER).sum())
    ax.set_ylabel("approx height over Brockenhurst (ft, nearest 1,000)", fontsize=10)
    ax.set_title(f"Brockenhurst arrivals, {day:%A %d %B %Y}  (independent OpenSky pull)\n"
                 f"{len(d)} arrivals crossed the village; {lowband} in the low band (about 2,000 ft or below)",
                 fontsize=13, fontweight="bold")
    ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
    fig.text(0.5, 0.005, "The free OpenSky tracks API reports altitude only to the nearest 1,000 ft, so use this to CONFIRM which flights "
             f"came over and flag the lowest, then read the exact height on WebTrak for {day:%d %b %Y} while it is still live. Source: OpenSky REST API.",
             ha="center", fontsize=8.5, color="#555")
    out = f"outputs/sweep/recent_snapshot_{day:%Y%m%d}.png"
    fig.tight_layout(rect=[0, 0.03, 1, 1]); fig.savefig(out, dpi=150, bbox_inches="tight"); plt.close(fig)
    csv = f"outputs/sweep/recent_snapshot_{day:%Y%m%d}.csv"
    d.assign(time=d["t"].dt.strftime("%H:%M"))[["time", "callsign", "airline", "adep", "alt_ft"]].to_csv(csv, index=False)
    print("wrote", out, "and", csv)
    print(d.assign(time=d["t"].dt.strftime("%H:%M"))[["time", "callsign", "airline", "adep", "alt_ft"]].to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    build(ap.parse_args().date)
