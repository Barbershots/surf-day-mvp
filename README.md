# Bournemouth → Brockenhurst noise compliance

Are aircraft arriving into Bournemouth Airport (EGHH) flying the quiet,
**low-power continuous descent approaches (CDA)** the airport's noise-abatement
rules require — or are they being dragged in **low and level**, adding engine
power (and noise) over Brockenhurst and the New Forest National Park?

This repo answers that with **public ADS-B data** (the aircraft's own reported
altitude), independent of the airport, and produces evidence you can put in front
of the airport, the council, or a consultation response.

> **The data gap this closes:** you had landing times but no mass altitude data
> over Brockenhurst. The OPDI **flight-events** dataset (same source as your
> `last_seen` landing times) contains each aircraft's **actual reported altitude
> and position** on the way in — including where it **levels off**. So the
> overfly height is now *measured*, not estimated as "landing − 3 min".

## What the data shows (sample: 4–24 June 2025)

1,318 EGHH arrivals; 891 produced usable low-level trajectory events.

| Finding | Value |
|--------|-------|
| Compliant 3° continuous-descent height over Brockenhurst | **~3,120 ft** |
| Median **measured** altitude over Brockenhurst | **~2,450 ft** |
| Arrivals **levelling off right over Brockenhurst** (≤6 km) | **24%** (median level-off **2,300 ft**) |
| Of flights with a direct reading: **below the CDA profile** | **82%** |
| Of flights with a direct reading: **below the 2,000 ft procedure floor** | **14%** |
| Any level-off in the inbound corridor (incl. routine short-final) | 45% (50% of large jets) |

A continuous descent has, by definition, **no level flight**. A quarter of
arrivals levelling off over the village — typically ~800 ft below where a
continuous descent would have them, some below the airport's own 2,000 ft floor —
is direct evidence of **non-continuous, powered, low approaches**, exactly the
noise behaviour described. See `outputs/` for the charts.

![Altitude over Brockenhurst](outputs/gate_altitude_hist.png)
![Altitude vs the compliant descent profile](outputs/descent_profile.png)

*(Headline numbers are for one 20-day sample so the demo runs quickly; run the
full multi-year sweep to match the 2023–2025 framing of your dashboards.)*

## Quickstart

```bash
pip install -r requirements.txt

# One ~20-day sample (downloads ~2 OPDI files, caches them in ./data)
python run_opdi.py --start 2025-06-04 --end 2025-06-24

# A full year, large commercial jets only
python run_opdi.py --start 2025-01-01 --end 2026-01-01 --large-jet-only
```

Outputs (in `outputs/`):
- `per_flight.csv` — one row per arrival with measured gate altitude + breach flags
- `summary.json` — headline numbers
- `descent_profile.png`, `gate_altitude_hist.png`, `leveloff_summary.png`

## How it works

```
config.py                 all assumptions in one place (geography, thresholds, classes)
brockenhurst/
  geometry.py             great-circle maths + the 3° compliant-descent profile
  opdi.py                 download/cache OPDI flight_list + flight_events, filter EGHH arrivals
  approach.py             detect level-offs & gate altitudes, flag CDA breaches
  charts.py               dashboard-styled charts (blue/gold/red)
  opensky.py              OPTIONAL: dense per-flight altitude from raw OpenSky state vectors
run_opdi.py               CLI: --start/--end → outputs/
tests/test_geometry.py    geometry & threshold sanity checks
docs/                     the airport's own source documents (noise abatement page, ILS plate, your dashboards)
```

**Read [`METHODOLOGY.md`](METHODOLOGY.md) before quoting any number** — it derives
the geometry and thresholds, ties them to the airport's own published rules
(`docs/noise_abatement_arrivals.jpeg`), explains the WebTrak cross-validation
step, and is honest about the limitations.

## Data sources
- **OPDI** (opdi.aero, EUROCONTROL PRU) — open Parquet derived from OpenSky ADS-B. Used by default; no account needed.
- **OpenSky Network** — raw state vectors for dense per-flight altitude (`brockenhurst/opensky.py`); free account required.
- **Bournemouth WebTrak** — the airport's own published tracks, for spot-check validation.
