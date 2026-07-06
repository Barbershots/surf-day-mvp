# OpenSky receiver: setup guide

*A one-page plan for the Brockenhurst Community Action Group. Running a small
ADS-B receiver earns us access to OpenSky's full historical flight archive, and
records the low arrivals over the village into an independent public dataset.
Prices are approximate (July 2026) and worth a quick check before buying.*

---

## Why we're doing it

- **Data access.** OpenSky grant historical database access to contributors. A receiver is the agreed route to the archive we asked for.
- **Our own record.** From the day it is switched on, it captures the flights over Brockenhurst into a public, timestamped dataset that nobody can dismiss as third-party.
- **Better local coverage.** ADS-B is line of sight, and coverage over the New Forest is thin. A receiver here improves it, which strengthens any comparison over time.

## Shopping list

| Item | What it is and why | Approx price |
| --- | --- | --- |
| Raspberry Pi 4 (2GB) | The little computer that runs it. A Pi 3B+ is fine too. | £40 to £55 |
| Official USB-C power supply | Steady power matters; cheap chargers cause dropouts. | £10 |
| microSD card, 16 to 32GB | Holds the software image. | £8 |
| RTL-SDR dongle | Receives the 1090 MHz signals. A FlightAware Pro Stick Plus has a built-in filter and is the easy choice. | £25 to £35 |
| 1090 MHz ADS-B antenna | The single biggest factor in how much you pick up. A proper 1090 antenna beats any stock one. | £20 to £40 |
| Coax cable (if loft or roof mounted) | Connects antenna to dongle. Keep it short. | £10 |
| Case (optional) | Keeps the Pi tidy. | £8 |

**Realistic total: about £120 for a good setup**, or nearer £70 if you go lean (a Pi Zero 2 W and a basic antenna).

## Where to buy

Search these exact product names at a trusted retailer rather than the cheapest listing:

- Raspberry Pi and power supply: **The Pi Hut** (thepihut.com) or **Pimoroni**.
- RTL-SDR dongle: **FlightAware Pro Stick Plus**, or **RTL-SDR Blog V4** (rtl-sdr.com).
- 1090 MHz antenna: **FlightAware 1090 MHz ADS-B antenna**.

If a group member already runs a receiver for FlightAware, Flightradar24 or ADS-B Exchange, we may not need new hardware at all. OpenSky can usually be added as an extra feed on the same box. Ask around first.

## Where to put it (the one decision that matters)

1090 MHz is line of sight, so **higher and clearer wins every time**.

- Best host: someone in or near Brockenhurst with an open view of the sky toward the **south and east**, the side the arrivals come in from.
- A loft or an upstairs window usually works. A roof or short mast is better.
- It needs mains power and wifi or ethernet, and runs 24/7. Power use is a few watts, so the electricity cost is negligible.

Sited well, it will record the exact low overflights this campaign is about.

## Setup, step by step (for whoever hosts it)

The official instructions are at **opensky-network.org/feed/raspberry**. Follow those for the exact download and commands. Here is what each stage means so it is not a mystery:

- **1. Flash the image.** Download OpenSky's Raspberry Pi image and write it to the SD card using Raspberry Pi Imager or Balena Etcher. This is the whole operating system plus their feeder software, ready to go.
- **2. Connect the hardware.** Plug the SDR dongle into a USB port, screw the antenna onto the dongle, insert the SD card, connect network and power. Place the antenna as high and clear as you can.
- **3. Register the receiver.** Log in to the OpenSky account, add the sensor, and enter the antenna's exact location: latitude, longitude and height above ground. Accuracy here directly affects data quality, so measure it properly.
- **4. Check it is feeding.** The OpenSky account page shows your sensor as online once data is flowing. Give it a few minutes.
- **5. Follow up.** Once it is confirmed feeding, reply to Martin (Ticket #835878) to request the historical (Trino) access.

## After it is running

- Leave it powered on. The value grows the longer it collects.
- We will then have both the historical archive to analyse and a live local feed of our own.
- If it drops offline, it is almost always power or network. A reboot usually fixes it.

*Any group member comfortable with a Raspberry Pi can do this in an afternoon. If nobody is, the guide is simple enough to follow, or a local enthusiast can help. Michael will coordinate the setup and the OpenSky side.*
