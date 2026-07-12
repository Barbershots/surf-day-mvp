# Project handoff — Brockenhurst aircraft-noise campaign

A complete context export so a fresh Claude account (with access to this repo)
can continue the work. The conversation itself does not transfer; this document
plus the repo is the equivalent. Read this first.

---

## 1. What this is

An evidence-led campaign against low, non-continuous-descent aircraft noise from
**Bournemouth Airport (EGHH)** arrivals over **Brockenhurst**, a village in the
**New Forest National Park**. Built for a residents' working group (Brockenhurst
Community Action Group, BCAG). Everything is built from the aircraft's own
broadcast GPS (ADS-B) so it is independent and reproducible.

**Goal:** get the airport / the airspace redesign to (1) enforce continuous
descent, (2) raise the height over the village, (3) route new paths away from
Brockenhurst, and to secure mitigation comparable to other UK communities.

## 2. Standing rules (the user's hard preferences — follow these)

- **Accuracy is non-negotiable.** "We can't afford any data that's not accurate
  and verified." Cross-check every figure against the data before using it.
  Never invent numbers, quotes, or geometry. Flag uncertainty honestly.
- **No em dashes** in anything the user might send or publish. Use commas or
  full stops.
- **Nautical miles only** for distances (not statute miles).
- **Plain English.** The audience is residents, not aviators.
- Documents are **rendered HTML → PDF via headless Chromium** (see §7), never a
  Markdown-to-PDF library.

## 3. People

- **Michael Barber** (mjcb20@gmail.com) — the user. Brockenhurst resident,
  builds the data and graphics.
- **John Stanton** — leads BCAG; owns the master document.
- **Guy** — liaises with the airport; sends 24-hour WhatsApp snapshots.
- **Avery** — focused on complaints; found the AIP night rule.
- **Andrew** — expert reviewer (flagged the UKADS process change and departures).
- Anne, Steve, Sue — group members. "Dave" — a group contact Andrew emails.
- **Martin Strohmeier** — OpenSky Network; offered historical-data access if the
  group runs a receiver.

## 4. Data (in `data/`, gitignored where large)

- `flight_list_YYYYMM.parquet` — **Europe-wide** OPDI monthly flight lists
  (columns incl. `id`, `icao24`, `adep`, `ades`, `registration`, `typecode`,
  `icao_aircraft_class`, `first_seen`, `last_seen`). Covers 2022–2026.
- `eghh_events_*.parquet` — **arrival** track points for EGHH (flight_id, lat,
  lon, altitude), 2023–2025, filtered from the Europe-wide event windows.
- `eghh_dep_events_*.parquet` — **departure** track points for EGHH, full
  3 years (28,319 departures). Built by `pull_departures.py`.
- Join key: `flight_list.id` (uint64) = events `flight_id`. **Cast pitfall:** the
  202512 file stores `id` as int64 (bit-wrapped); reinterpret with
  `np.asarray(s).view("uint64")`. 2022 event files use an incompatible id scheme
  — excluded.
- Track points are sparse OPDI *milestone* fixes (~9 per approach), so counts of
  aircraft "measured over the village" are **minimums** (~1 in 5 get a height).

**OpenSky:** REST client creds are set in the env (`OPENSKY_CLIENT_ID/SECRET`)
for the live/recent API (`recent_snapshot.py`). Historical (Trino) needs an
account with data access — Martin will grant it **if the group runs an ADS-B
receiver** (see `OPENSKY_RECEIVER_GUIDE.md`). Not yet set up.

## 5. Key verified figures (safe to quote)

- Brockenhurst is **9.7 NM** from the runway-26 threshold; population **3,488**
  (2021). ~**76%** of arrivals overfly it (rwy26); the rest land the other way.
- **77%** of arrivals cross below the 3° quiet-descent line (**70/74/81%** by
  year 2023/24/25). Median height over the village **~2,725 ft**. The 3° glide
  is **3,116 ft** at the village (3.3° = 3,437 ft, 3.5° = 3,643 ft).
- **44%** level off during the approach. **50** large jets crossed below 2,000 ft
  (12 at night); by year **8 / 16 / 26**.
- Arrivals **9,819 → 12,574** (+28%, 2023→2025); large jets **2,943 → 4,854**
  (+65%). Over-village large jets (measured) **572 → 693 → 786**.
- **Direction:** the robust figure is **~62% from the south side** of the village
  line (holds at every honest measuring distance from 12 NM out). A three-way
  NE/ESE/S split is ~**40/20/40** but is measurement-sensitive — do not lean on
  it; the NE figure inflates close-in because everything merges onto the ~075°
  final line.
- **Night:** after-11pm arrivals over the village **+137%** (27 → 64, 2023→2025).
  Busiest hour is 23:00; at summer peak ~**2 large jets/hr**, bunching to one
  every 12–15 min on busy nights.
- **Passengers:** 1.08m (2007) → **1.38m (2025)**; +27% YoY; ×1.88 over 2022–25.
  Approved cap **3 million** (2007 & 2010 planning permissions).
- **Departures:** easterly ops (runway 08) **23%** of the time. Runway-08
  climb-outs cross the village (~2.3/day in July), median **~6,900 ft** (higher
  than arrivals but full climb power). AIP routes them 075° straight at the
  village to 5.6 DME before turning.
- **Airport volumes 2025 (our data):** Bournemouth 12,574; Farnborough 14,460;
  Gatwick 132,718; Heathrow 233,416; Stansted 101,807; Luton 69,671;
  Southampton 18,265. (Close to published movement figures.)

## 6. Legal / regulatory context (verified against the live AIP, AMDT 06/2026)

- **AIP AD 2.21 (Noise Abatement):** *"Between 2130-0630 (2030-0530) all aircraft
  that wish to **self position** for an ILS or a visual approach shall establish
  on final approach at no less than **8 DME** and **not below 2500 FT QNH**."* And
  turbine aircraft *"apply continuous descent, low power, low drag ... **at all
  times**"* and *"maintain as high an altitude as practical."*
- **The loophole:** the airport argues these apply only to *self-positioning*
  aircraft, not the radar-vectored majority. Rebutting that is central.
- Three different **night windows**, do not conflate: operating/noise-abatement
  night **21:30–06:30**; the AD 2.21 8DME/2500ft rule **21:30–06:30**; the
  **Night Noise Budget (quota count) 23:30–06:00** (airport's 2024 Noise Action
  Plan). Airport operating hours are 06:15–01:00.
- **Section 106** planning obligation (least disturbance; ILS-equivalent landing
  descent path). **Levelling Up and Regeneration Act 2023** + **Sandford
  Principle** (National Park conservation first).
- **AIRSPACE PROCESS CHANGED (important):** FASI-South / the standalone
  ACP-2019-43 is **superseded**. Bournemouth's change is being absorbed into a
  single **London TMA Region ACP** run by **UKADS** (UK Airspace Design Service,
  est. 2 June 2025, provider NERL). Onboarding (CAP 3129) + CAP 1616 v6 guidance
  expected **summer 2026**; public consultation is later; deployment target
  **2032–2035**. Any pack section framed around "an imminent airport-led
  consultation" is out of date — reframe around UKADS and registering concerns
  early. The alignment/join point in the NE design envelope has moved inward to
  **~7 NM** (vs the village at 9.7 NM), a potential ~860 ft height concern to
  confirm.

## 7. Rendering pipeline (how the documents are made)

Self-contained HTML (inline CSS, inline SVG, local PNGs) → PDF via Chromium:

```bash
CHROME=/opt/pw-browsers/chromium-1194/chrome-linux/chrome   # path varies by env
"$CHROME" --headless --no-sandbox --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=out.pdf "file://$PWD/page.html"
```

Preview by rendering the PDF to PNG (PyMuPDF `get_pixmap`) and **look at every
page**, then fix and re-render. The design system is documented in
`outputs/design_system/` (CSS + template + spec + starter prompt). Charts are
matplotlib PNGs embedded in `<figure>` cards, in the same palette.

## 8. Deliverables already built (in `outputs/`)

- **`onepager/full_pack.(html|pdf)`** — the 17-page case pack (Parts 1–4 +
  complaint card).
- **`onepager/opener`, `leaflet`, `comparison`, `departures`** — styled sections.
- **`onepager/*.png`** — quieter_descent, arr_vs_dep_height, airport_volumes,
  cda_schematic, avoid_concept.
- **`sweep/*.png`** — all data charts/maps (rope maps, heatmaps, night, descent,
  envelope, snapshots). See `charts_export/INDEX.md` for the full catalogue.
- **`design_system/`** — portable style export. **`charts_export/`** — all 46
  figures. **`OPENSKY_RECEIVER_GUIDE.(md|pdf)`** — how to unlock historical data.
- Analysis scripts at repo root and in `brockenhurst/` (geometry, opdi, opensky).
  `config.py` holds the constants (EGHH, thresholds, Brockenhurst, gates, etc.).

## 9. Open threads / next steps

- **Two graphics were in progress when this handoff was written:** (1) a clean
  "Potential new flight paths (avoiding Brockenhurst)" map in the polished
  rope-map style with the parish boundary, and (2) a "Raise the height over
  Brockenhurst" chart (height over the village at 3.0° / 3.3° / 3.5° vs today).
- Reframe the pack's Part 2 around **UKADS** (see §6).
- Add the **departures** section into the main pack; consider the **comparison**
  page after the Southampton night-flights section.
- If the receiver gets installed, pull the **10-year OpenSky history** (with a
  coverage-bias caveat) for a "the route has moved before" argument.
- A **1-minute Attenborough-style voiceover** script exists (in chat) for a video.

## 10. How to continue in the new account

1. Give the new account access to the repo (`barbershots/surf-day-mvp`), branch
   `claude/bournemouth-noise-compliance-rzcqio`.
2. Have it read this file, then `outputs/design_system/DESIGN_SYSTEM.md` and
   `outputs/charts_export/INDEX.md`.
3. Confirm it can render `outputs/design_system/template.html` to a clean PDF
   (proves the pipeline works in that environment).
4. Re-state the standing rules (§2) to it. Then continue.
