#!/usr/bin/env python3
"""Convert poster HTML to PDF via Playwright (Chromium headless)."""

import sys, os
from playwright.sync_api import sync_playwright

def html_to_pdf(html_path, pdf_path):
    html_path = os.path.abspath(html_path)
    pdf_path = os.path.abspath(pdf_path)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1889, "height": 2646},
            device_scale_factor=3,
        )
        page.goto(f"file://{html_path}", wait_until="networkidle")
        page.wait_for_timeout(2000)

        page.pdf(
            path=pdf_path,
            width="500mm",
            height="870mm",
            margin={"top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"},
            print_background=True,
            prefer_css_page_size=True,
        )

        browser.close()
    print(f"PDF generado: {pdf_path} ({os.path.getsize(pdf_path)/1024:.0f} KB)")

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "poster_cientifico.html"
    dst = sys.argv[2] if len(sys.argv) > 2 else src.replace(".html", ".pdf")
    html_to_pdf(src, dst)
