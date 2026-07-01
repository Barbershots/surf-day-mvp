# Data sources, completeness, caveats & glossary

A plain reference for the Bournemouth → Brockenhurst noise analysis, so anyone
(including the airport or council) can see exactly where the numbers come from,
how complete they are, and precisely how each term is defined. Figures are for
the three full calendar years **2023–2025** unless stated.

---

## 1. Where the data comes from

Every height and position in this analysis ultimately comes from the
**aircraft themselves**. Modern airliners continuously broadcast their GPS
position, altitude, speed and identity over radio (a system called **ADS-B**).
Anyone with a receiver can pick this up — which is what makes this evidence
**independent of the airport**.

The chain of custody is:

1. **Aircraft ADS-B broadcast** — the plane transmits its own position and
   altitude (~ once per second).
2. **OpenSky Network** — a non-profit research network of ground receivers that
   records these broadcasts. (opensky-network.org)
3. **OPDI v0.0.2** — the *Open Performance Data Initiative*, run by
   **EUROCONTROL's Performance Review Unit**, republishes the OpenSky data as
   clean, checked, downloadable files. This analysis uses OPDI. (opdi.aero)
4. **This analysis** — filters OPDI to arrivals at Bournemouth (EGHH), measures
   each aircraft's height as it passes Brockenhurst, and compares it to the
   quiet-descent profile.

Two OPDI tables are used:

- **Flight list** (one row per flight): callsign, aircraft type, origin,
  destination, date, first/last seen. Used to pick out Bournemouth arrivals and
  classify the aircraft.
- **Flight events** (points along each flight): each has a time, latitude,
  longitude and **altitude in feet**, tagged with what happened there — e.g.
  *level-off start/end* or *crossing 5,000 / 7,000 / 10,000 ft*.

**Intended cross-check (WebTrak):** the airport publishes its own radar/ADS-B
tracks on its *WebTrak* website. The plan is to spot-check a sample of flights
(matched by callsign and time) against WebTrak so the airport cannot dismiss the
public-data finding without contradicting its own published data. WebTrak has no
bulk download, so it is a *validation* layer, not the mass-data source.

---

## 2. What period and how much data

- **Period analysed:** 1 January 2023 → 1 January 2026 (the three full years
  2023, 2024, 2025 are reported).
- **OPDI data availability:** January 2022 to ~January 2026, refreshed
  periodically. (This is why the June-2026 resident audit dates cannot yet be
  matched — they are beyond current coverage.)
- **Files processed:** the events come in 10-day files. Of **111** files across
  the period, **110** were processed; **1 was missing on the server** (the
  window 2–12 Oct 2025) and one further window returned no Bournemouth records —
  together about **20 days (~1.8%)** of the three years are absent. This does not
  materially affect the yearly totals or trends.

---

## 3. How complete it is

This is the most important section to read before quoting any single number.

**Flights tracked (very high):**

| Measure (2023–2025) | Value |
|---|---|
| Total Bournemouth arrivals (all aircraft) | 33,157 |
| — of which large passenger jets | 11,453 |
| Arrivals with usable trajectory data | 32,197 (**97%**) |
| Large jets with usable trajectory data | 11,091 (**97%**) |

So **almost every arrival is captured** — this is not a small or cherry-picked
sample of flights.

**Exact height *directly over the village* (a smaller subset):**

| Measure (2023–2025) | Value |
|---|---|
| Arrivals with a precise over-Brockenhurst height | 4,938 (**15%**) |
| Large jets with a precise over-Brockenhurst height | 2,051 (**18%**) |
| Night large jets with a precise height | 217 |
| Night large jets with a height at/near the village | 321 |

Why the drop from 97% to ~15–18%? The public data records **key moments** along
each flight (levelling off, crossing set altitudes), **not** a continuous line.
A precise "over the village" height exists only when one of those recorded
moments happens to fall right at Brockenhurst — roughly **1 flight in 6**.

**What this means for the numbers:**

- The **descent-profile graph** (height vs distance) uses *all* recorded points
  in the approach corridor — **99,655 data points** — so it is a large, robust
  sample.
- The **exact-height counts** ("N airliners below 2,000 ft over the village")
  are drawn from that ~1-in-6 subset, so they are **minimums**. The true numbers
  are **higher**, not lower — there is no mechanism that would make them
  overstated.

---

## 4. Caveats & things to be aware of

- **Counts are floors, not ceilings.** Because precise over-village heights
  exist for ~1 in 6 flights, every "how many were too low" figure understates
  the real total.
- **Milestone data, not a continuous track.** OPDI records events (level-offs,
  altitude crossings), not a second-by-second path. The level-off evidence is
  robust; the exact-height evidence is a representative subset.
- **A single low or level flight can be innocent.** Air traffic control may level
  an aircraft for separation or weather. The argument here is **statistical**: a
  large and *growing* share of arrivals lower than a continuous descent is
  inconsistent with "continuous descent … at all times", whatever any individual
  justification.
- **Altitude is barometric** (referenced to standard pressure below the
  transition altitude). Any error is tens of feet — small next to the ~1,100 ft
  gap between where aircraft are and where a quiet descent would put them.
- **Standard 3° glidepath assumed** for the quiet-descent line. If Bournemouth's
  instrument glidepath differs, the line shifts slightly; the value is a single
  configurable setting.
- **"Large jet" excludes business jets** (they are counted separately). It
  includes some smaller regional jets; see the glossary.
- **Landing time** is taken from the last recorded position; **day/evening/night**
  is then set in **UK local time** (so it follows British Summer Time correctly).
- **~20 days are missing** (Section 2); yearly trends are unaffected.
- **Reception thins at very low level** far from receivers, which is part of why
  close-in points are sparser — but 97% of flights are still captured overall.

---

## 5. Glossary — definitions and values

**ADS-B** — the radio signal an aircraft broadcasts with its own GPS position,
altitude, speed and identity. The raw source of all heights here.

**Bournemouth Airport (EGHH)** — the arrival airport. Reference point
**50.7805°N, 1.8396°W**, elevation **38 ft**. Runway 26 (landing towards the
west) is the relevant runway; its landing threshold is the eastern end, nearest
Brockenhurst.

**Brockenhurst** — the New Forest village being overflown, at
**50.8189°N, 1.5757°W**. It lies **~10.3 nautical miles** from the airport on a
bearing of **~077°**, which is **directly under the runway-26 approach line**
(final approach track 255°). It is **~9.8 nautical miles** from the runway
threshold. This is *why* nearly every westerly arrival passes over it.

**Quiet descent line / "continuous descent approach" (CDA)** — the ideal quiet
way to arrive: the aircraft descends steadily with engines near idle, never
levelling off. Modelled as a standard **3° glidepath**, which loses about
**318 ft per nautical mile**. Extended back from the runway threshold
(elevation 38 ft), this puts a compliant aircraft at about **3,116 ft over
Brockenhurst**. On the graphs this is the **orange line**; falling *below* it
means the aircraft is lower than a quiet descent would have it — usually flying
low and level under power, which is what makes the noise.

**2,000 ft procedure floor** — Bournemouth's own published Noise Abatement rule
states that turbo-powered / heavier aircraft "**shall not descend below 2000'**
before intercepting the glideslope". Over Brockenhurst that is the hard minimum;
below it is a clear breach. On the graphs this is the **red dashed line**.

**Level-off (non-continuous descent)** — a recorded segment where the aircraft
stops descending and flies level. A continuous descent has *no* level flight; to
hold level altitude on approach the engines must be pushed up, so a level-off is
both a departure from "continuous descent" and a direct cause of extra noise.
"**Level-off over the village**" = a level segment starting within **6 km** of
Brockenhurst.

**Over-Brockenhurst height ("gate" height)** — the aircraft's measured height as
it passes the village, taken from a recorded point within **3 km** of
Brockenhurst and within the approach corridor.

**Approach corridor** — the funnel along the extended runway-26 centreline used
to separate genuine arrivals from unrelated traffic: within **4 km** either side
of the centreline, on the approach side of the airport.

**Aircraft categories** — each flight is classified from its **ICAO type code**
(e.g. B738 = Boeing 737-800), with the aircraft's engine/type class as a
fallback:

- **Large jet** *(the "airliners" the case is about)* — commercial narrow-body
  and wide-body jets: Boeing 737 family (incl. MAX), Airbus A320 family, A220,
  A330/A340/A350/A380, Boeing 757/767/777/787/747, Embraer E-Jets, regional jets
  (CRJ), and similar. **Excludes business jets.**
- **Business jet** — executive jets (e.g. Falcon, Gulfstream, Citation, Learjet,
  Challenger, Phenom). Counted separately, *not* as airliners.
- **Turboprop** — propeller airliners/commuters (e.g. ATR 42/72, Dash 8).
- **GA / light** — small private piston aircraft (e.g. Cessna 172, Piper).
- **Helicopter** — all rotary-wing.
- **Other** — anything not identifiable into the above (e.g. missing type code).

**Time-of-day windows** — set in **UK local time** at the moment of landing:

- **Day** = 06:00–19:00
- **Evening** = 19:00–23:00
- **Night** = 23:00–06:00 *(the core sleep window; the same 7-hour period
  Heathrow treats as its night quota period)*

**Large jet (engine-class fallback)** — where the exact type code is missing,
classification falls back to the ICAO class: multi-engine jet → treated as a
jet, turboprop → turboprop, piston → GA/light, rotary → helicopter.

---

*Everything above is reproducible from the code in this repository. The full
technical derivation (geometry, formulae, thresholds) is in `METHODOLOGY.md`;
all tunable values live in `config.py`.*
