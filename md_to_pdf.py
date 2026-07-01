#!/usr/bin/env python3
"""
Render a Markdown document to a clean, shareable A4 PDF.

    python md_to_pdf.py DATA_AND_DEFINITIONS.md outputs/data_and_definitions.pdf

Deliberately supports only the subset of Markdown used in this project's docs:
headings (#/##/###), bullet lists (-), pipe tables, horizontal rules (---),
blank-line paragraphs, and inline **bold** / `code`. No external converters
(pandoc etc.) required - just fpdf2.
"""
from __future__ import annotations

import re
import sys

from fpdf import FPDF

INK = (26, 26, 26)
MUTE = (90, 90, 90)
RULE = (200, 200, 200)
HEADBG = (238, 240, 243)


FONT_DIR = "/usr/share/fonts/truetype/dejavu"
FONT = "DejaVu"  # a Unicode TTF so arrows, degrees and em-dashes render


class Doc(FPDF):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.add_font(FONT, "", f"{FONT_DIR}/DejaVuSans.ttf")
        self.add_font(FONT, "B", f"{FONT_DIR}/DejaVuSans-Bold.ttf")
        self.add_font(FONT, "I", f"{FONT_DIR}/DejaVuSans.ttf")  # no separate oblique face

    def header(self):
        pass

    def footer(self):
        self.set_y(-13)
        self.set_font(FONT, "", 7.5)
        self.set_text_color(*MUTE)
        self.cell(0, 6, f"Bournemouth / Brockenhurst noise analysis  ·  page {self.page_no()}",
                  align="C")


def _inline(t: str) -> str:
    """Keep **bold** (fpdf supports it); drop single-asterisk *emphasis* markers."""
    return t.replace("**", "\0").replace("*", "").replace("\0", "**")


def _callout(pdf: Doc, lines: list[str], accent=(31, 111, 196)):
    """A shaded box with an accent left bar, for key facts / asks."""
    txt = "\n".join(lines).strip()
    usable = pdf.w - pdf.l_margin - pdf.r_margin
    inner = usable - 12
    pdf.set_font(FONT, "", 10)
    n = len(pdf.multi_cell(inner, 5.6, _inline(txt), dry_run=True, output="LINES", markdown=True))
    h = max(1, n) * 5.6 + 6
    if pdf.get_y() + h > pdf.page_break_trigger:
        pdf.add_page()
    x, y = pdf.l_margin, pdf.get_y()
    pdf.set_fill_color(238, 242, 247); pdf.rect(x, y, usable, h, style="F")
    pdf.set_fill_color(*accent); pdf.rect(x, y, 2.4, h, style="F")
    pdf.set_xy(x + 7, y + 3)
    pdf.set_text_color(*INK)
    pdf.multi_cell(inner, 5.6, _inline(txt), markdown=True)
    pdf.set_y(y + h + 2.5)


def _table(pdf: Doc, rows: list[list[str]]):
    rows = [r for r in rows if not set("".join(r)) <= {"-", " ", ":"}]  # drop |---| separator
    if not rows:
        return
    ncol = max(len(r) for r in rows)
    usable = pdf.w - pdf.l_margin - pdf.r_margin
    # First column wider for the label; remaining columns share the rest evenly.
    if ncol == 1:
        widths = [usable]
    elif ncol == 2:
        widths = [usable * 0.62, usable * 0.38]
    else:
        w0 = usable * 0.34
        widths = [w0] + [(usable - w0) / (ncol - 1)] * (ncol - 1)
    line_h = 6
    for i, row in enumerate(rows):
        head = i == 0
        pdf.set_font(FONT, "B" if head else "", 9)
        pdf.set_fill_color(*HEADBG)
        pdf.set_text_color(*INK)
        # measure tallest cell (wrap)
        cells = (row + [""] * ncol)[:ncol]
        heights = []
        for w, txt in zip(widths, cells):
            n = max(1, pdf.multi_cell(w, line_h, _inline(txt), dry_run=True, output="LINES", markdown=True).__len__())
            heights.append(n * line_h)
        h = max(heights)
        if pdf.get_y() + h > pdf.page_break_trigger:
            pdf.add_page()
        x0, y0 = pdf.get_x(), pdf.get_y()
        for w, txt in zip(widths, cells):
            x, y = pdf.get_x(), pdf.get_y()
            pdf.multi_cell(w, line_h, _inline(txt), border=0, fill=head, align="L", markdown=True,
                           new_x="RIGHT", new_y="TOP", max_line_height=line_h)
            pdf.set_xy(x + w, y)
        pdf.set_xy(x0, y0 + h)
    pdf.ln(2)


def render(md_path: str, pdf_path: str):
    with open(md_path) as f:
        lines = f.read().split("\n")

    pdf = Doc(format="A4")
    pdf.set_auto_page_break(True, margin=16)
    pdf.set_margins(18, 16, 18)
    pdf.add_page()

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        pdf.set_x(pdf.l_margin)  # always start a block at the left margin

        if not stripped:
            pdf.ln(2.5)
            i += 1
            continue

        if stripped.startswith("### "):
            pdf.ln(1); pdf.set_font(FONT, "B", 11); pdf.set_text_color(*INK)
            pdf.multi_cell(0, 6, _inline(stripped[4:]), markdown=True); pdf.ln(0.5)
        elif stripped.startswith("## "):
            pdf.ln(2); pdf.set_font(FONT, "B", 14); pdf.set_text_color(*INK)
            pdf.multi_cell(0, 7.5, _inline(stripped[3:])); pdf.ln(1)
        elif stripped.startswith("# "):
            pdf.set_font(FONT, "B", 19); pdf.set_text_color(*INK)
            pdf.multi_cell(0, 9, _inline(stripped[2:])); pdf.ln(1.5)
        elif stripped.startswith("!["):
            m = re.match(r"!\[[^\]]*\]\(([^)]+)\)", stripped)
            if m:
                usable = pdf.w - pdf.l_margin - pdf.r_margin
                from PIL import Image
                iw, ih = Image.open(m.group(1)).size
                h = usable * ih / iw
                if pdf.get_y() + h > pdf.page_break_trigger:
                    pdf.add_page()
                pdf.image(m.group(1), x=pdf.l_margin, w=usable)
                pdf.ln(2)
        elif stripped.startswith(">"):
            block = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                block.append(lines[i].strip().lstrip(">").strip())
                i += 1
            # a callout that starts with "ASK" or an emoji flag gets a gold accent
            accent = (200, 136, 31) if block and block[0].upper().startswith(("ASK", "PROPOS")) else (31, 111, 196)
            _callout(pdf, block, accent)
            continue
        elif stripped == "---":
            pdf.ln(1); pdf.set_draw_color(*RULE)
            y = pdf.get_y(); pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y); pdf.ln(2)
        elif stripped.startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            _table(pdf, block)
            continue
        elif stripped.startswith("- "):
            pdf.set_font(FONT, "", 10); pdf.set_text_color(*INK)
            pdf.set_x(pdf.l_margin + 3)
            pdf.multi_cell(pdf.w - pdf.r_margin - (pdf.l_margin + 3), 5.6,
                           "•  " + _inline(stripped[2:]), markdown=True,
                           new_x="LMARGIN", new_y="NEXT")
        elif (stripped.startswith("*") and stripped.endswith("*")
              and not stripped.startswith("**") and len(stripped) > 2):
            pdf.set_font(FONT, "I", 9); pdf.set_text_color(*MUTE)
            pdf.multi_cell(0, 5.4, _inline(stripped.strip("*")))
        else:
            pdf.set_font(FONT, "", 10); pdf.set_text_color(*INK)
            pdf.multi_cell(0, 5.6, _inline(stripped), markdown=True)
        i += 1

    pdf.output(pdf_path)
    return pdf_path


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "DATA_AND_DEFINITIONS.md"
    dst = sys.argv[2] if len(sys.argv) > 2 else "outputs/data_and_definitions.pdf"
    print("wrote", render(src, dst))
