"""Print sheet of the main-text figures (design/sim_spec_ms3.md §1.4 item 4; design/figure_plan.md §5, "Export and
checks"): code/sim/out/figs/print_check.pdf, with each main-text figure that exists in paper/figures/ at 100% on a US
letter page, once in color and once converted to greyscale (Ghostscript's pdfwrite with ColorConversionStrategy=Gray,
vector; a 600-dpi greyscale raster if Ghostscript fails). A cover page lists the figures included, the ones skipped
because their PDF does not exist yet, and the sha256 of each figure PDF, so that the record print_check.md can name
what was checked. The sheet is printed, or rendered at 300 dpi in color and greyscale (as in the MS3 check of
2026-10-22/23), and the record code/sim/out/figs/print_check.md (not written here) gives per
figure the date, "legible at 100%" and "series distinguishable in greyscale", and the changes made.

The figure folder and the output folder follow style.output_dirs (SUBLET_FIGS_PDF_DIR, SUBLET_FIGS_OUT_DIR).
Run from code/sim: ``python -m figs.print_sheet``.

MS5 addition C28 (design/sim_spec_ms5.md §2.3): the sheet depends on the input PDFs alone, whatever the commit, the
date or the folder they are read from, so that the frozen rebuild (§8) can compare it byte for byte. The cover's second
line names neither a time nor a folder but the digest of the inputs (inputs_digest: the sha256 of the sorted lines
"<figure> <sha256>" of the included PDFs, its first 16 hex digits on the cover), and the sheet is saved with
no_new_id=True, so that MuPDF writes no new trailer /ID. The returned record keeps 'written' (the time of the build)
and the input paths.

MS5b addition C44 (design/sublet_v2.md §11, W12): main_figures() orders fig<N><suffix> by N and then by suffix, so that
fig4v2 (the paper's Fig. 4, C41) follows fig4 (the earlier key put every name with a suffix last); the order of fig1 to
fig7 is unchanged.

MS7 addition C62 (2026-11-24): the figure text the print check judges is no larger than the caption text,
IEEEtran's 8-pt \\footnotesize (style.CAPTION_PT, 7.970 bp): bold panel letters, axis labels and panel titles at
style.LABEL_PT (7.97 pt), every other text at style.TICK_PT (7 pt), nothing outside [style.TEXT_MIN_PT,
style.TEXT_MAX_PT] (finalize()). This replaces the 9-pt rule of the print check of 2026-10-22, after the IEEE Author
Center's "approximately 9-10 point" (literature/sources/ieee-graphics-guidelines.md). The cover's fourth line states
the scale (SCALE_LINE, from the style constants), so that the sheet names the rule its figures were drawn to.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import fitz

from figs import style

NAME = "print_check"
LETTER = (612.0, 792.0)          # US letter in bp
MARGIN = 36.0                    # 0.5 in: a W2 figure (514.07 bp) fits the 540-bp printable width
GS = "/usr/bin/gs"
GREY_DPI = 600
# C62: the figure type scale, on the cover
SCALE_LINE = (f"Figure text (C62): {style.TICK_PT:g} pt, panel letters and axis labels {style.LABEL_PT:.2f} pt; "
              f"nothing above the 8-pt caption ({style.TEXT_MAX_PT:.2f} bp) or below {style.TEXT_MIN_PT:g} pt.")


def _order(name: str) -> tuple:
    """C44: fig<N><suffix> by N, then by suffix (fig4, then fig4v2); any other name last."""
    m = re.fullmatch(r"fig(\d+)(.*)", name)
    return (int(m.group(1)), m.group(2)) if m else (99, name)


def main_figures() -> list[str]:
    """The main-text figures of the registry, in paper order (C44: fig4v2 right after fig4)."""
    return [k for k, s in sorted(style.FIGURES.items(), key=lambda kv: _order(kv[0])) if s.main]


def to_grey(pdf: Path, out: Path) -> str:
    """Greyscale copy of `pdf` at `out`; returns the method used."""
    r = subprocess.run([GS, "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite",
                        "-sColorConversionStrategy=Gray", "-dProcessColorModel=/DeviceGray", "-dAutoRotatePages=/None",
                        f"-o{out}", str(pdf)], capture_output=True, text=True, timeout=120) \
        if Path(GS).is_file() else None
    if r is not None and r.returncode == 0 and out.is_file():
        with fitz.open(out) as g, fitz.open(pdf) as c:
            if g.page_count == 1 and abs(g[0].rect.width - c[0].rect.width) < 0.5:
                return "ghostscript pdfwrite, ColorConversionStrategy=Gray (vector)"
    with fitz.open(pdf) as c:
        pix = c[0].get_pixmap(dpi=GREY_DPI, colorspace=fitz.csGRAY)
        doc = fitz.open()
        page = doc.new_page(width=c[0].rect.width, height=c[0].rect.height)
        page.insert_image(page.rect, pixmap=pix)
        doc.save(out)
        doc.close()
    return f"raster, {GREY_DPI} dpi greyscale"


def inputs_digest(shas: dict[str, str]) -> str:
    """C28: the sha256 of the sorted lines '<figure> <sha256>' of the included figure PDFs (`shas`: figure ->
    sha256 of its PDF), each line ending in a newline."""
    text = "".join(f"{line}\n" for line in sorted(f"{n} {sha}" for n, sha in shas.items()))
    return hashlib.sha256(text.encode()).hexdigest()


def _text(page, xy, s, size=9.0):
    page.insert_text(fitz.Point(*xy), s, fontname="helv", fontsize=size, color=(0, 0, 0))


def build(fig_dir: Path, out_pdf: Path) -> dict:
    names = main_figures()
    present = [n for n in names if (fig_dir / f"{n}.pdf").is_file()]
    missing = [n for n in names if n not in present]
    doc = fitz.open()
    doc.new_page(width=LETTER[0], height=LETTER[1])          # the cover, written once the figures are placed
    when = datetime.datetime.now().isoformat(timespec="seconds")      # the record's, never on the sheet (C28)
    shas = {n: hashlib.sha256((fig_dir / f"{n}.pdf").read_bytes()).hexdigest() for n in present}
    lines = [("Sublet main-text figures: print check at 100% (US letter)", 12.0, 22.0),
             ("Built by code/sim/figs/print_sheet.py from the main-text figures, inputs sha256 "
              f"{inputs_digest(shas)[:16]}", 9.0, 14.0),
             ("Print without scaling (100%, no 'fit to page'). Each figure: color, then greyscale.", 9.0, 14.0),
             (SCALE_LINE, 9.0, 22.0)]
    rows = []
    opened = []        # every source stays open until the save: show_pdf_page keys its graft map on id(src), and a
    #                    closed color copy's id reused by its greyscale copy made the sheet reuse the color objects
    with tempfile.TemporaryDirectory() as td:
        for n in present:
            src = fig_dir / f"{n}.pdf"
            sha = shas[n]
            grey = Path(td) / f"{n}_grey.pdf"
            method = to_grey(src, grey)
            page = doc.new_page(width=LETTER[0], height=LETTER[1])
            yy = MARGIN
            for label, path in (("color", src), ("greyscale", grey)):
                f = fitz.open(path)
                opened.append(f)
                w, h = f[0].rect.width, f[0].rect.height
                if w > LETTER[0] - 2 * MARGIN + 1e-6:
                    raise style.StyleError(f"{n} is {w:.1f} bp wide, wider than the printable letter width")
                _text(page, (MARGIN, yy + 9), f"{n} ({label}, 100%, {w:.2f} x {h:.2f} bp)")
                yy += 16
                x0 = (LETTER[0] - w) / 2
                page.show_pdf_page(fitz.Rect(x0, yy, x0 + w, yy + h), f, 0)
                yy += h + 28
            rows.append({"figure": n, "file": str(src), "sha256": sha, "greyscale": method})
            lines.append((f"{n}: included, sha256 {sha[:16]}..., greyscale by {method}", 9.0, 14.0))
        for n in missing:
            lines.append((f"{n}: skipped, {n}.pdf does not exist yet", 9.0, 14.0))
        cover = doc[0]
        y = MARGIN + 10
        for s_, size, dy in lines:
            _text(cover, (MARGIN, y), s_, size)
            y += dy
        out_pdf.parent.mkdir(parents=True, exist_ok=True)
        tmp = out_pdf.with_name(f".{out_pdf.name}.partial")
        doc.save(tmp, garbage=3, deflate=True, no_new_id=True)      # C28: no trailer /ID that changes per save
        doc.close()
        for f in opened:
            f.close()
        os.replace(tmp, out_pdf)
    return {"pdf": str(out_pdf), "included": rows, "skipped": missing, "written": when}


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.parse_args(argv)
    fig_dir, out_dir = style.output_dirs()
    rep = build(Path(fig_dir), Path(out_dir) / f"{NAME}.pdf")
    for r in rep["included"]:
        print(f"[{NAME}] {r['figure']}: included ({r['greyscale']})")
    for n in rep["skipped"]:
        print(f"[{NAME}] {n}: skipped, no PDF yet")
    print(f"[{NAME}] wrote {rep['pdf']}")
    return rep


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
