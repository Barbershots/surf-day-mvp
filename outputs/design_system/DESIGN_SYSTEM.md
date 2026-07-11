# Aircraft-noise case-pack — design system (portable export)

This is everything needed to recreate the blue "case pack / leaflet" look in a
fresh Claude account. Hand Claude the three files in this folder
(`design_system.css`, `template.html`, this `DESIGN_SYSTEM.md`) plus the
starter prompt at the bottom.

---

## 1. What it is

A **print-first A4 document system** for evidence-led community campaign
material: case packs, leaflets, one-pagers. Clean, credible, "quiet confidence"
rather than shouty. Blue palette, a single gold accent, generous whitespace,
vector plane motif, data figures in framed cards.

The look is deliberately restrained so that data and quotes carry the weight.

## 2. How it is rendered (important)

Pages are **plain HTML + CSS, rendered to PDF by headless Chromium** using its
built-in "print to PDF". Do **not** use a Markdown-to-PDF library (fpdf/pandoc)
for this look — it cannot do the gradients, cards and layout. The pipeline:

1. Write a self-contained `.html` file (inline the CSS into a `<style>` block).
2. Render:

   ```bash
   CHROME=/path/to/chrome        # e.g. the bundled Chromium binary
   "$CHROME" --headless --no-sandbox --disable-gpu --no-pdf-header-footer \
     --print-to-pdf=out.pdf "file://$PWD/page.html"
   ```

   (A `dbus` warning on Linux is harmless. `--no-pdf-header-footer` removes the
   browser's default URL/date margins.)
3. Preview by rendering the PDF to PNG (e.g. PyMuPDF `get_pixmap`) and eyeball
   each page; adjust and re-render. Iterate on layout by looking, not guessing.

Everything must be **self-contained**: system fonts, inline `<svg>`, images as
local files or `data:` URIs. No external CSS/fonts/JS.

## 3. Fonts

Body/heading font is **Liberation Sans** (bundled on Linux), falling back to
DejaVu Sans. Arial/Helvetica are visually equivalent substitutes on other
machines. Weight does the work: 800 for headings and numbers, 600–700 for
labels, normal for body. No external/Google fonts (keeps it self-contained).

## 4. Palette

| Token | Hex | Use |
|---|---|---|
| `--ink` | `#16202e` | body text |
| `--muted` | `#5a6b7e` | captions, footnotes |
| `--blue` | `#1b4f8f` | mid blue |
| `--deep` | `#0f335f` | dark cards, headings on cards |
| `--bright` | `#2c6fbb` | accent blue: kickers, links, step circles |
| `--sky` | `#eef4fb` | pale card background |
| `--line` | `#d9e3ef` | hairline borders |
| `--gold` | `#e8a020` | the single accent: divider rule + warning left-bar |
| `--red` | `#c0392b` | breach / danger |
| `--green` | `#1f8f7f` | positive (e.g. continuous descent) |

Banners and dark callouts use `linear-gradient(135deg, var(--deep), var(--blue))`
(the hero banner extends to `var(--bright)` at 130%).

## 5. Layout rules

- Every page is a fixed `.page` (210mm × 297mm), `@page{margin:0}` so banners
  bleed to the edge. Content sits inside `.pad` (14mm 15mm).
- A `.foot` is absolutely pinned to the bottom of each page (org name + page no.).
- The **signature move**: `kicker` (small caps blue label) → `h2.sec` heading →
  gold `divider` rule → body.
- Keep figures in `<figure>` cards with a `<figcaption>` citing the source.
- One dark element per page maximum (a `.stat.accent`, a `.callout`, or a
  `.partband`) so emphasis stays scarce.

## 6. Component catalogue

All classes are defined and commented in `design_system.css`; `template.html`
shows each one in place. Summary:

- **`.banner`** — full-bleed gradient header with `.mark` (logo + org), optional
  `.tag`, `h1`, `.sub`, and a faint `.bigplane` SVG watermark.
- **`.kicker` / `h2.sec` / `.divider` / `p.body`** — the core text rhythm.
- **`.stat`** (stacked) and **`.bigstats`/.bs`** (4-across band) — number cards;
  add `.accent`/`.a` for one dark card.
- **`.partband`** — big numbered section divider.
- **`.row3` + `.idea`** — three-up icon explainer.
- **`figure` / `figcaption`** — framed chart with caption.
- **`.fact`** (`.blue` / `.red` variants) — light highlighted fact with left-bar.
- **`.callout`** — dark gradient box for the single strongest point.
- **`.steps` + `.step`** — numbered process row with `&rarr;` arrows.
- **`table.t`** — data table; `td.k` label cells, `tr.us` to spotlight your row,
  `.verdict` pills (`v-good`/`v-part`/`v-bad`).
- **`.panels` / `.panel`** — two-up "heading + image + text" (asks with diagrams).
- **`.note`** — light single-point note.
- **`.qrrow` / `.qrbox`** — QR / complaint-card blocks.

### The plane SVG (reuse everywhere)

```html
<svg viewBox="0 0 512 512"><path fill="#fff" d="M256 8c18 0 32 42 32 95v66l176 108v44l-176-52v94l50 40v33l-82-22-82 22v-33l50-40v-94L16 361v-44l176-108V103c0-53 14-95 32-95z"/></svg>
```

Use it white at `opacity:.10` as a banner watermark (`.bigplane`), and small
inside the `.mark` disc. Simple flat icons for `.ic`/`.card` come from the same
family of single-path SVGs (see `template.html`).

## 7. Charts

Data figures are made separately (matplotlib) and embedded as PNGs in `<figure>`
cards. To match the system, use the palette above: bars in `--bright`, one
series highlighted in `--gold` or `--deep`, thin `--line` gridlines, muted
captions. Reference lines dashed in `--gold`/`--red`. Keep chart titles short;
let the `figcaption` carry the source note.

---

## 8. Starter prompt for the other Claude account

> I'm giving you a design system as three files: `design_system.css` (the
> stylesheet), `template.html` (a page skeleton using every component), and
> `DESIGN_SYSTEM.md` (the spec). I want to make print-ready A4 documents in this
> exact style.
>
> Please work like this: I describe a page or document; you write a
> self-contained HTML file (inline the CSS from `design_system.css` into a
> `<style>` block), using the components from the template. Then render it to PDF
> with headless Chromium's `--print-to-pdf` (self-contained only: system fonts,
> inline SVG, local images). Render each page to a PNG and check it visually,
> then fix spacing/overflow and re-render until it looks right. Keep the palette,
> the kicker → heading → gold-divider rhythm, one dark emphasis element per page,
> framed figures with source captions, and the plane motif. First, confirm you
> can render the attached `template.html` to a clean 2-page PDF, then we'll build.

---

## 9. Files in this export

- `design_system.css` — the full commented stylesheet.
- `template.html` — a 2-page skeleton demonstrating every component.
- `DESIGN_SYSTEM.md` — this document.

Optional reference (from the original project) — finished examples in this
style: the opener, full case pack, comparison page, departures section and the
2-page leaflet.
