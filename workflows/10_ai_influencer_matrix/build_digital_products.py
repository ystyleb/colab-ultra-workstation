#!/usr/bin/env python3
"""10 AI Influencer Matrix: 0-CCU Printable Multi-Page Digital Product PDF Generator.

Renders the 6 V3.1 A4 PDF products (Vivian / June / Wen, free lead magnet + paid guide each) defined in
`products_v3.py`, via offline HTML/CSS and local headless Chrome into `products/*.pdf`.
This file keeps the shared stylesheet, page helpers and the render/verify loop.
"""

from __future__ import annotations

import html
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRODUCTS_DIR = HERE / "products"
HTML_DIR = HERE / "work" / "pdf_html"
CONFIG_PATH = HERE / "influencer_config.json"

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]


def find_chrome() -> str:
    """Locate local Chrome/Chromium executable."""
    for p in CHROME_CANDIDATES:
        if Path(p).exists():
            return p
    raise FileNotFoundError("Google Chrome executable not found in /Applications.")


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def pdf_page_count(pdf_path: Path) -> int:
    """Count PDF pages robustly without third-party dependencies."""
    raw = pdf_path.read_bytes()
    if not raw.startswith(b"%PDF-"):
        return 0
    # Count /Type /Page dictionary objects (excluding /Pages)
    import re
    matches = re.findall(rb"/Type\s*/Page\b", raw)
    return len(matches)


def wrap_doc(title: str, css_vars: dict[str, str], pages_html: list[str], footer_brand: str) -> str:
    """Wrap page sections in a self-contained offline A4 editorial stylesheet."""
    body_pages = "\n".join(pages_html)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{esc(title)}</title>
<style>
  @page {{
    size: A4 portrait;
    margin: 13mm 14mm 14mm 14mm;
  }}
  :root {{
    --bg-tint: {css_vars['bg_tint']};
    --accent: {css_vars['accent']};
    --accent-soft: {css_vars['accent_soft']};
    --ink: {css_vars['ink']};
    --muted: {css_vars['muted']};
    --border: {css_vars['border']};
    --gold: {css_vars['gold']};
  }}
  * {{
    box-sizing: border-box;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}
  body {{
    margin: 0;
    padding: 0;
    color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "Avenir Next", "Helvetica Neue", Arial, sans-serif;
    font-size: 10.2pt;
    line-height: 1.48;
    background: #ffffff;
  }}
  h1, h2, h3, .serif {{
    font-family: "Georgia", "Baskerville", "Times New Roman", serif;
    margin-top: 0;
  }}
  .page {{
    position: relative;
    min-height: 263mm;
    page-break-after: always;
    break-after: page;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    padding-bottom: 10mm;
  }}
  .page:last-child {{
    page-break-after: auto;
    break-after: auto;
  }}
  .cover-page {{
    background: linear-gradient(155deg, var(--bg-tint) 0%, #ffffff 55%, var(--accent-soft) 100%);
    border: 2px solid var(--accent);
    border-radius: 10px;
    padding: 18mm 16mm;
    justify-content: space-between;
  }}
  .kicker {{
    display: inline-block;
    background: var(--accent);
    color: #ffffff;
    font-size: 8.5pt;
    font-weight: 700;
    letter-spacing: 1.8px;
    text-transform: uppercase;
    padding: 5px 12px;
    border-radius: 999px;
  }}
  .cover-title {{
    font-size: 30pt;
    line-height: 1.12;
    color: var(--accent);
    margin: 14px 0 10px 0;
  }}
  .cover-sub {{
    font-size: 13pt;
    color: var(--muted);
    margin-bottom: 18px;
    max-width: 90%;
  }}
  .cover-box {{
    background: #ffffff;
    border: 1px solid var(--border);
    border-left: 5px solid var(--gold);
    border-radius: 8px;
    padding: 14px 16px;
    margin: 14px 0;
  }}
  .cover-meta {{
    border-top: 1px solid var(--border);
    padding-top: 12px;
    display: flex;
    justify-content: space-between;
    font-size: 9pt;
    color: var(--muted);
  }}
  .hdr-bar {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    border-bottom: 2px solid var(--accent);
    padding-bottom: 5px;
    margin-bottom: 12px;
  }}
  .hdr-bar .tag {{
    font-size: 8.5pt;
    font-weight: 700;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    color: var(--accent);
  }}
  .hdr-bar .pg {{
    font-size: 8.5pt;
    color: var(--muted);
  }}
  h2 {{
    font-size: 18pt;
    color: var(--accent);
    margin-bottom: 8px;
  }}
  h3 {{
    font-size: 12pt;
    color: var(--ink);
    margin-bottom: 5px;
  }}
  p {{
    margin: 0 0 8px 0;
  }}
  .card {{
    background: var(--bg-tint);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 13px;
    margin-bottom: 10px;
    break-inside: avoid;
  }}
  .callout {{
    background: var(--accent-soft);
    border-left: 4px solid var(--accent);
    border-radius: 0 8px 8px 0;
    padding: 10px 13px;
    margin: 10px 0;
    break-inside: avoid;
  }}
  .grid-2 {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }}
  .day-card {{
    border: 1px solid var(--border);
    border-radius: 7px;
    padding: 8px 11px;
    margin-bottom: 7px;
    background: #ffffff;
    break-inside: avoid;
  }}
  .day-head {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 3px;
  }}
  .day-badge {{
    font-weight: 700;
    font-size: 9pt;
    color: #ffffff;
    background: var(--accent);
    padding: 2px 8px;
    border-radius: 4px;
  }}
  .day-check {{
    font-size: 9.5pt;
    color: var(--muted);
    font-weight: 600;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0 12px 0;
    font-size: 9.3pt;
  }}
  th {{
    background: var(--accent);
    color: #ffffff;
    text-align: left;
    padding: 6px 8px;
    font-weight: 600;
  }}
  td {{
    border: 1px solid var(--border);
    padding: 6px 8px;
    vertical-align: top;
  }}
  tr:nth-child(even) td {{
    background: var(--bg-tint);
  }}
  .check-grid {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 7px;
    margin-top: 8px;
  }}
  .check-cell {{
    border: 1.5px solid var(--accent);
    border-radius: 6px;
    padding: 7px;
    text-align: center;
    background: var(--bg-tint);
  }}
  .check-cell strong {{
    display: block;
    color: var(--accent);
    font-size: 9.5pt;
  }}
  .check-cell span {{
    font-size: 13pt;
    color: var(--ink);
  }}
  .write-line {{
    border-bottom: 1px dashed var(--muted);
    height: 18px;
    margin-bottom: 6px;
  }}
  .footer-note {{
    margin-top: auto;
    padding-top: 8px;
    border-top: 1px solid var(--border);
    font-size: 8.2pt;
    color: var(--muted);
    display: flex;
    justify-content: space-between;
  }}
  .cta-box {{
    background: var(--accent);
    color: #ffffff;
    border-radius: 8px;
    padding: 12px 15px;
    margin-top: 10px;
  }}
  .cta-box h3 {{
    color: #ffffff;
    margin-bottom: 4px;
  }}
</style>
</head>
<body>
{body_pages}
</body>
</html>
"""


def make_header(tag: str, page_num: int, total_pages: int) -> str:
    return f'<div class="hdr-bar"><span class="tag">{esc(tag)}</span><span class="pg">Page {page_num} of {total_pages}</span></div>'


def make_footer(brand: str, note: str) -> str:
    return f'<div class="footer-note"><span>{esc(brand)}</span><span>{esc(note)}</span></div>'


def render_day_cards(days: list[tuple[int, str, str, str]]) -> str:
    out = []
    for d_num, d_title, action, why in days:
        out.append(
            f'<div class="day-card">'
            f'<div class="day-head"><span class="day-badge">DAY {d_num:02d} — {esc(d_title)}</span>'
            f'<span class="day-check">&#9744; Completed &nbsp;&nbsp; &#9744; Logged</span></div>'
            f'<p><strong>Action:</strong> {esc(action)}</p>'
            f'<p style="color:var(--muted);font-size:9.2pt;margin-bottom:0;"><strong>Why it works:</strong> {esc(why)}</p>'
            f'</div>'
        )
    return "\n".join(out)


def html_to_pdf(chrome_bin: str, html_path: Path, pdf_path: Path) -> None:
    """Render standalone local HTML file to A4 PDF via headless Chrome."""
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_prof = Path(tempfile.mkdtemp(prefix="chrome_wf10_", dir="/tmp"))
    try:
        cmd = [
            chrome_bin,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--user-data-dir={tmp_prof}",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            html_path.resolve().as_uri(),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if res.returncode != 0 or not pdf_path.exists():
            raise RuntimeError(f"Chrome PDF export failed (rc={res.returncode}): {res.stderr[-400:]}")
    finally:
        shutil.rmtree(tmp_prof, ignore_errors=True)


def main() -> None:
    chrome_bin = find_chrome()
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)

    from products_v3 import BUILDERS as builders  # V3.1 内容；V2 旧版见 work/archive/

    for tier, fn in builders:
        fname, doc_html = fn()
        slug = Path(fname).stem
        html_path = HTML_DIR / f"{slug}.html"
        pdf_path = PRODUCTS_DIR / fname
        html_path.write_text(doc_html, encoding="utf-8")
        html_to_pdf(chrome_bin, html_path, pdf_path)

        size_kb = pdf_path.stat().st_size / 1024.0
        pages = pdf_page_count(pdf_path)
        min_pages = 4 if tier == "free" else 10
        assert pdf_path.read_bytes().startswith(b"%PDF-"), f"Invalid PDF header: {pdf_path}"
        assert pdf_path.stat().st_size > 25_000, f"PDF suspiciously small ({size_kb:.1f} KB): {pdf_path}"
        assert pages >= min_pages, f"PDF pages={pages} < expected {min_pages} for {pdf_path}"
        print(f"✅ {fname}: {pages} pages | {size_kb:.1f} KB", flush=True)


if __name__ == "__main__":
    main()
