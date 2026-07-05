#!/usr/bin/env python3
"""
Printable A4 'how to complain' card for Brockenhurst residents: WebTrak in four
taps, plus a ready-made email. Embeds the two QR codes.

    python complain_card.py  ->  outputs/complain/complain_card.png (+ .pdf)
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

INK, BLUE, RED, AMBER, GREY = "#12233b", "#2c6fbb", "#c0392b", "#e8a020", "#5b6472"


def box(bg, x, y, w, h, fc, ec):
    bg.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.006,rounding_size=0.014",
                                linewidth=1.6, edgecolor=ec, facecolor=fc, zorder=1))


def qr(fig, path, x, y, w, h):
    ax = fig.add_axes([x, y, w, h], zorder=5); ax.imshow(plt.imread(path)); ax.axis("off")


def build(out="outputs/complain/complain_card"):
    fig = plt.figure(figsize=(8.27, 11.69))  # A4 portrait
    fig.patch.set_facecolor("white")
    bg = fig.add_axes([0, 0, 1, 1], zorder=0); bg.axis("off")
    bg.set_xlim(0, 1); bg.set_ylim(0, 1)

    fig.text(0.5, 0.955, "Bothered by a low plane over Brockenhurst?",
             ha="center", fontsize=21, fontweight="bold", color=INK)
    fig.text(0.5, 0.925, "Report it in under two minutes. Every complaint is logged, and it counts.",
             ha="center", fontsize=12.5, color=GREY)

    # ---- Option 1: WebTrak ----
    box(bg, 0.06, 0.545, 0.88, 0.345, "#eef4fb", BLUE)
    fig.text(0.10, 0.855, "1.  WebTrak  (the airport's own official record)",
             fontsize=15, fontweight="bold", color=BLUE)
    steps = [
        "Scan the code, or go to",
        "Scroll the time bar back to",
        "Tap the plane: it shows you the",
        "Tap 'Report' and send it",
    ]
    steps2 = [
        "webtrak.emsbk.com/boh",
        "when the plane went over",
        "flight and its height",
        "",
    ]
    for i, (s, s2) in enumerate(zip(steps, steps2)):
        yy = 0.82 - i * 0.052
        fig.text(0.115, yy, f"{i+1}", fontsize=13, fontweight="bold", color="white",
                 ha="center", va="center",
                 bbox=dict(boxstyle="circle,pad=0.3", fc=BLUE, ec="none"))
        fig.text(0.15, yy + 0.008, s, fontsize=12, color=INK, va="center")
        if s2:
            fig.text(0.15, yy - 0.017, s2, fontsize=11.5, color=INK, va="center", fontweight="bold")
    fig.text(0.10, 0.575, "You do NOT need the flight number, WebTrak finds the plane for you.",
             fontsize=10.5, color=GREY, style="italic")
    qr(fig, "outputs/complain/qr_webtrak.png", 0.71, 0.60, 0.185, 0.185)

    # ---- Option 2: ready-made email ----
    box(bg, 0.06, 0.235, 0.88, 0.285, "#fff8ee", AMBER)
    fig.text(0.10, 0.485, "2.  Or send a ready-made email",
             fontsize=15, fontweight="bold", color="#9a6a00")
    fig.text(0.10, 0.45,
             "Scan the code to open an email\n"
             "already written for you. Just add\n"
             "the date, time and one line about\n"
             "what you heard, then press send.",
             fontsize=12, color=INK, va="top")
    fig.text(0.10, 0.305, "Prefer to type it yourself?  environment@bournemouthairport.com",
             fontsize=11, color=INK)
    fig.text(0.10, 0.278, "Only got the date and time? Send those to our group, we can find the flight.",
             fontsize=10.5, color=GREY, style="italic")
    qr(fig, "outputs/complain/qr_email.png", 0.71, 0.335, 0.175, 0.175)

    # ---- Why it matters ----
    box(bg, 0.06, 0.065, 0.88, 0.15, "#fbeeee", RED)
    fig.text(0.5, 0.19, "Why bother?", ha="center", fontsize=14, fontweight="bold", color=RED)
    fig.text(0.5, 0.16,
             "The airport must log and report every complaint to its committee and the regulator.\n"
             "Numbers get noticed. Report EVERY disturbance, not just the worst night.\n"
             "Complain in your own name: many people each complaining beats one person complaining often.",
             ha="center", fontsize=10.5, color=INK, va="top")

    fig.text(0.5, 0.028, "Brockenhurst Community Action Group  ·  aircraft noise campaign",
             ha="center", fontsize=9.5, color=GREY)

    fig.savefig(out + ".png", dpi=150, facecolor="white")
    fig.savefig(out + ".pdf", facecolor="white")
    plt.close(fig)
    print("wrote", out + ".png", "and", out + ".pdf")
    return out + ".png"


if __name__ == "__main__":
    build()
