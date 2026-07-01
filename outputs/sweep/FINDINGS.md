# What the flight data shows over Brockenhurst (2023-2025)

*Plain-English summary. "Height" means height above sea level as the plane passed over Brockenhurst village. All heights come from the planes' own broadcast position data.*

## The two numbers that matter
- **Proper (quiet) height over Brockenhurst: about 3,116 ft.** This is where a plane should be if it is gliding down gently with its engines near idle - the quiet way to arrive.
- **Minimum the airport allows here: 2,000 ft.** Below this is a clear breach of the airport's own published rule.

When a plane is lower than the proper height it has usually stopped gliding and is flying low and level - which means its engines are working harder, so it is louder. That is the noise residents hear.

## Night-time airliners (11pm-6am, the core sleep window)
- Tracked night-time airliners over Brockenhurst with a height reading: **217**.
- Typical (median) height: **2,775 ft** - **341 ft below** the proper quiet height.
- Flew **lower than the proper quiet height**: **161** (74%).
- Flew **below the airport's own 2,000 ft minimum**: **9** (4%).

## Year by year
|   year |   large_jet_arrivals_tracked |   night_large_jets_tracked |   night_with_height_reading |   night_median_height_ft |   night_below_proper_height |   night_below_2000ft_minimum |   night_stopped_descending_overhead |
|-------:|-----------------------------:|---------------------------:|----------------------------:|-------------------------:|----------------------------:|-----------------------------:|------------------------------------:|
|   2023 |                         2943 |                        263 |                          45 |                     2950 |                          28 |                            0 |                                  63 |
|   2024 |                         3656 |                        332 |                          69 |                     2750 |                          53 |                            2 |                                  95 |
|   2025 |                         4492 |                        583 |                         103 |                     2725 |                          80 |                            7 |                                 157 |

## Cross-reference with the resident noise audit
The audit's own flights are dated June 2026, beyond current open-data coverage (which ends ~Jan 2026), so those exact flights can't be pulled. But the audit names recurring airlines, so we cross-reference by operator. The audit uses IATA flight numbers (e.g. LS3684); ADS-B records the radio callsign (Jet2 = 'EXS'), so we match the airline, not the exact number.

| operator                                     |   night_flights_tracked |   night_flights_below_proper_height |   lowest_night_height_ft |
|:---------------------------------------------|------------------------:|------------------------------------:|-------------------------:|
| Jet2 (audit 'LS' flights, e.g. LS3684 Ibiza) |                     225 |                                  50 |                     1300 |
| TUI (audit 'TOM' flights, e.g. TOM651)       |                     583 |                                 131 |                     1600 |
| Ryanair (audit 'RYR' flights, e.g. RYR1244)  |                     357 |                                  38 |                     1350 |

Every airline the audit names is confirmed making low night approaches over Brockenhurst in the 2023-2025 data - the same pattern, and in some cases lower than the audit's examples. The audit's 'URO601 / URO901' entries could not be matched to any UK operator, and an A340-600 freighter into Bournemouth at night is implausible; those entries should be treated as unverified.

## The worst individual night flights
See `worst_night_offenders.png` and `night_large_jets.csv` for the full list, each with its flight number, date, time and measured height.

*Caveats: only planes broadcasting position at low level are captured (roughly half to two-thirds of arrivals), so the true counts are higher, not lower. A single low flight can have an air-traffic-control reason; the point is the consistent pattern. See METHODOLOGY.md.*