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
# Kept short and minimal on purpose: the target reader is someone who rarely
# complains, so the barrier must be low. It is generic to any aircraft over the
# village (arrival or departure). A copy goes to the campaign so every complaint
# counts toward our total. The fuller, evidence-heavy version is a later option.
CC = "aircraft@yourbrockenhurst.org"
subject = "Aircraft noise complaint - Brockenhurst"
body = (
    "Dear Bournemouth Airport,\n\n"
    "I wish to make a complaint about aircraft noise over Brockenhurst.\n\n"
    "Date: \n"
    "Approximate time: \n"
    "My location (road or postcode): \n\n"
    "Please log this as a formal noise complaint and confirm which aircraft it was.\n\n"
    "Name: \n"
    "Address: \n"
)
mailto = (
    "mailto:environment@bournemouthairport.com?cc="
    + urllib.parse.quote(CC)
    + "&subject="
    + urllib.parse.quote(subject)
    + "&body="
    + urllib.parse.quote(body)
)
qr(mailto, "outputs/complain/qr_email.png")
print("mailto length:", len(mailto))
print()
print(mailto)
