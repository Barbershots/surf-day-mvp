"""Generate the two complaint QR codes and print their embedded URLs.

- qr_webtrak.png : the airport's WebTrak radar replay (find the flight).
- qr_email.png   : a mailto: link that opens a pre-filled complaint email.

Distances use nautical miles to stay consistent with the rest of the pack.
Run from the repo root:  python3 gen_complaint_qr.py
"""
import urllib.parse
import qrcode


def qr(data, path):
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=2)
    q.add_data(data)
    q.make(fit=True)
    img = q.make_image(fill_color="#12233b", back_color="white")
    img.save(path)
    print("wrote", path)


# 1) WebTrak
WEBTRAK = "https://webtrak.emsbk.com/boh"
qr(WEBTRAK, "outputs/complain/qr_webtrak.png")

# 2) Pre-filled complaint email (mailto)
subject = "Aircraft noise complaint - Brockenhurst"
body = (
    "Dear Bournemouth Airport Environment Team,\n\n"
    "I wish to make a formal complaint about aircraft noise over Brockenhurst.\n\n"
    "Date: \n"
    "Approximate time: \n"
    "My location (road/postcode): \n"
    "What I experienced (e.g. very low, loud, woke me): \n\n"
    "Brockenhurst sits about 9.7 nautical miles from the runway, directly under the arrivals path "
    "and inside the New Forest National Park. Arrivals over the village are frequently lower than a "
    "continuous 3-degree descent (about 3,100 ft here) and often level off overhead, which is when "
    "the engine noise is worst. At night your own rule is that aircraft should not be below 2,500 ft "
    "until within 8 nautical miles.\n\n"
    "Please investigate this flight against your published noise-abatement procedures (UK AIP EGHH "
    "AD 2.21) and your Section 106 continuous-descent obligation, and confirm the aircraft, its "
    "height over Brockenhurst, and whether it flew a continuous descent. Please log this as a formal "
    "noise complaint and send me your response.\n\n"
    "Name: \n"
    "Address: \n"
)
mailto = (
    "mailto:environment@bournemouthairport.com?subject="
    + urllib.parse.quote(subject)
    + "&body="
    + urllib.parse.quote(body)
)
qr(mailto, "outputs/complain/qr_email.png")
print("mailto length:", len(mailto))
print()
print(mailto)
