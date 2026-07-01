# Methodology — are Bournemouth arrivals flying continuous descent over Brockenhurst?

This document sets out exactly how the analysis turns public flight data into
evidence about noise compliance, so that every number can be checked or
challenged. It is written to stand up to scrutiny from the airport.

## 1. The obligation being tested

Bournemouth Airport's published **Noise Abatement Procedures** say, in the
airport's own words (quoted **verbatim** below). Source: **UK AIP, EGHH AD 2.21**
(Noise Abatement Procedures), AIRAC cycle effective **11 June 2026**, published by
NATS on behalf of the CAA — the official rule-book that binds arriving pilots.
The same text is reproduced on the Jeppesen "Noise Abatement (GEN, ARRS)" chart
photographed in `docs/`. (Note: the Jeppesen wording differs trivially — e.g.
"practicable" for the AIP's "practical", "GS" for "glidepath"; the AIP is the
primary source and is quoted here.)

- **Continuous descent** — *"Turbine powered aircraft are expected to apply
  continuous descent, low power, low drag approach techniques **at all times**."*
- *"Subject to ATC instructions, inbound aircraft are to maintain **as high an
  altitude as practical** and adopt a low power, low drag, continuous descent
  approach profile."*
- *"The object will be to join the glidepath at the appropriate height for the
  distance **without level flight**."*
- **ILS approaches** — *"all turbine powered aircraft and all other aircraft with
  a MTWA of 5700 KG or more, **shall not descend below 2000 FT QNH** before
  intercepting the glidepath, nor thereafter fly below it."*
- **Night self-positioning** — *"Between 2130-0630 (2030-0530) all aircraft that
  wish to self position for an ILS or a visual approach shall establish on final
  approach at **no less than 8 DME and not below 2500 FT QNH**."*

Live source URL: <https://www.aurora.nats.co.uk/htmlAIP/Publications/2026-06-11-AIRAC/html/eAIP/EG-AD-2.EGHH-en-GB.html>
(search the page for "Noise Abatement"; verify the current AIRAC cycle when citing).

The complaint is that aircraft are instead being brought in **low and level**,
then using **high engine power** (including powered turns) over Brockenhurst —
the opposite of a low-power continuous descent, and the cause of the noise.

A continuous descent has one defining, *measurable* property: the aircraft is
**always descending** — there is **no level flight**. Levelling off is
significant because to hold level altitude on approach an aircraft must **add
engine power** (and later add drag/power again to resume descent). Level flight
on approach is therefore both a breach of the "without level flight" expectation
**and** the direct cause of the extra noise.

So the test is two-pronged and entirely objective:

1. **Did the aircraft level off** on the way in (over/near Brockenhurst)? and
2. **How high was it** over Brockenhurst, compared with where a compliant
   continuous descent would put it?

## 2. Geometry — why Brockenhurst, and what "compliant" height means there

| Point | Latitude | Longitude |
|------|----------|-----------|
| Bournemouth Airport (EGHH) ref | 50.7805 | −1.8396 |
| Runway 26 threshold (ILS DME `IBH` = 0) | 50.7793 | −1.8226 |
| Brockenhurst village | 50.8189 | −1.5757 |

- Brockenhurst bears **~077°(T) at ~10.3 NM** from the airport. Runway 26's final
  approach is **255°(T) inbound** (≈ magnetic; local variation ≈ 0°), i.e. the
  inbound corridor runs out along **075°**. Cross-track distance of the village
  from the extended centreline is **< 2 km** — **Brockenhurst sits essentially
  directly under the runway-26 approach** (`tests/test_geometry.py` checks this).
  That is why nearly every westerly arrival overflies it.
- The ILS DME (`IBH`) reads zero at the runway-26 threshold (Jeppesen note 2), so
  **DME-from-IBH = distance-from-threshold**. Brockenhurst is **~9.8 NM** from the
  26 threshold.
- A standard **3° glidepath** gains **~318 ft per NM** (`tan 3° × 6076 ft`). A
  continuous 3° descent extended back from the threshold (elev 38 ft) therefore
  passes over Brockenhurst at:

  > **38 + 9.8 × 318 ≈ 3,120 ft AMSL** — the *compliant CDA profile height*.

  This is the benchmark. A genuinely continuous, "as high as practicable"
  approach is **at or above ~3,100 ft** over Brockenhurst. The airport's own
  hard floor — *"not below 2000' before intercepting the GS"* — is **1,100 ft
  below** that. Anything over the village **below 2,000 ft is a clear breach of
  the published procedure**; anything materially below ~3,100 ft is lower than a
  continuous descent would produce.

All of this is encoded in `config.py` and `brockenhurst/geometry.py`.

## 3. Data sources

Both are public and both ultimately come from **ADS-B transmitted by the
aircraft themselves** (i.e. the aircraft's own reported position/altitude), which
is what makes this independent of the airport.

### Primary: OPDI (used here, no account needed)
The **Open Performance Data Initiative** (opdi.aero, run by EUROCONTROL's
Performance Review Unit) republishes OpenSky ADS-B as clean, joinable Parquet:

- **`flight_list`** (monthly) — one row per flight: `id`, `flt_id` (callsign),
  `icao24`, `typecode`, `icao_aircraft_class`, `adep`/**`ades`**,
  `first_seen`/`last_seen`. We filter to `ades == 'EGHH'`. *(This is the same
  table the existing dashboards used for the `last_seen` landing time.)*
- **`flight_events`** (10-day) — milestone events along each trajectory, joined
  on `flight_id == flight_list.id`. Each event has `latitude`, `longitude`,
  `altitude` (ft) and a `type`. The types that matter:
  - **`level-start` / `level-end`** — the start/end of a **level segment**. This
    is the direct fingerprint of non-continuous descent.
  - **`top-of-descent`**, **`first/last-xing-fl50/70/100/245`** — points on the
    descent profile, used to plot altitude vs distance.

> **This is the dataset that fills the gap you hit.** You were estimating the
> Brockenhurst overfly as *landing − 3 min*; the flight-events table gives the
> aircraft's **actual reported altitude and position** on the way in, so the
> overfly height is measured, not assumed.

### Optional: OpenSky raw state vectors (`brockenhurst/opensky.py`)
`flight_events` is *sparse* (milestones only). For a **direct altitude reading
for every single arrival exactly over the village**, query OpenSky's raw state
vectors (10-second cadence, barometric **and** geometric altitude) in a small box
around Brockenhurst. Needs a free OpenSky/Trino account. This is the same raw
feed OPDI is built from, so it cross-checks OPDI and yields a publishable
per-flight table with groundspeed and vertical rate (extra power proxies).

### Validation against the airport's own data (WebTrak)
The airport publishes its own radar/ADS-B tracks on **WebTrak**. The intended
final step is to spot-check a sample of flights — match by callsign + time — and
confirm the OPDI/OpenSky altitude over Brockenhurst agrees with WebTrak's. Once a
sample agrees, the airport cannot dismiss the public-data finding without
impeaching its own published data. (WebTrak has no bulk export, so it is a
*validation* layer, not the primary mass-data source — hence the OPDI pipeline.)

## 4. How a flight is classified

For each EGHH arrival that produced trajectory events:

- **`leveloff_over_village`** — had a `level-start` within **6 km** of
  Brockenhurst inside the approach corridor (`config.NEAR_VILLAGE_KM`). This is
  the headline non-CDA signal: levelling off *right over the community*.
- **`non_cda` / `has_corridor_leveloff`** — levelled off *anywhere* in the
  inbound corridor below 6,000 ft. Broader; note this also captures the routine
  ILS platform on short final (~4 NM), so it is reported but not leaned on.
- **`gate_alt_ft`** — measured altitude as the flight crossed the Brockenhurst
  gate (within 3 km of the village and inside the corridor), where an event falls
  in the gate.
- **`alt_vs_cda_ft`** — `gate_alt_ft − 3,120 ft`. Negative = lower than a
  continuous descent would be.
- **`breach_hard_floor`** — gate altitude **below 2,000 ft**: a clear breach of
  the published "not below 2000' before GS" rule.

"Large jet" mirrors the existing dashboards: multi-engine jet ICAO classes
(`L2J/L3J/L4J`). The CDA expectation explicitly covers turbo-powered / >5,700 kg
aircraft, which is this group.

## 5. Honest limitations (read before quoting numbers)

- **Coverage, not bias.** ~97% of arrivals are tracked (produce usable
  trajectory events), so this is not a small or cherry-picked sample. A *precise
  height directly over Brockenhurst* exists for a smaller subset (~15% of all
  arrivals, ~18% of large jets), because the events are milestones rather than a
  continuous track — so the exact-height counts are minimums, not overstatements.
  The descent-profile scatter uses all ~100k corridor points and is unaffected.
  See DATA_AND_DEFINITIONS.md for the full coverage table.
- **Sparse events.** `flight_events` gives milestones, not a continuous track, so
  not every flight has an event exactly at the gate. The level-off counts (which
  don't need a gate event) are the robust core; the gate-altitude histogram uses
  the subset with a gate event. Use `opensky.py` for full per-flight coverage.
- **Barometric altitude** is referenced to standard pressure below the transition
  altitude unless corrected; at these low levels the error is tens of feet, small
  next to the ~1,100 ft gap between observed heights and the CDA profile.
- **A single level-off isn't automatically unlawful** — ATC may level an aircraft
  for separation. The argument is **statistical**: a large, persistent share of
  arrivals levelling low over Brockenhurst is inconsistent with "continuous
  descent … at all times", whatever any individual justification.
- **3° is the standard glidepath**; if Bournemouth's ILS GS angle differs, change
  `GLIDESLOPE_DEG` in `config.py` and the profile updates everywhere.

## 6. Reproducing

```bash
pip install -r requirements.txt
python run_opdi.py --start 2025-06-04 --end 2025-06-24      # one ~20-day sample
python run_opdi.py --start 2025-01-01 --end 2026-01-01 --large-jet-only   # full year
```

Outputs land in `outputs/`: `per_flight.csv`, `summary.json`, and the charts.
Raw OPDI files cache in `data/` (git-ignored) so re-runs are instant.
