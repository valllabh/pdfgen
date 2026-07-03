"""Playwright (Chromium) based HTML to PDF renderer.

This is the maintained Python equivalent of Puppeteer. Same browser engine,
same `page.pdf()` semantics. Swappable behind the CLI: replace this module
with another backend (WeasyPrint, Typst, ...) and the CLI keeps working.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright


@dataclass
class PdfOptions:
    """Mirrors Puppeteer's PDFOptions. All optional with sensible defaults."""
    format: str = "A4"
    print_background: bool = True
    margin_top: str = "20mm"
    margin_right: str = "20mm"
    margin_bottom: str = "20mm"
    margin_left: str = "20mm"
    landscape: bool = False
    scale: float = 1.0
    display_header_footer: bool = False
    header_template: str = "<p></p>"
    footer_template: str = "<p></p>"
    page_ranges: str = ""
    width: str = ""
    height: str = ""
    prefer_css_page_size: bool = False
    outline: bool = True  # Chromium native outline from h1-h6
    tagged: bool = True   # accessibility tags
    channel: str = ""     # "chrome", "msedge", "chromium" or "" for auto
    executable_path: str = ""  # explicit browser binary path
    extra: dict[str, Any] = field(default_factory=dict)

    def to_playwright(self) -> dict[str, Any]:
        """Convert to playwright page.pdf() kwargs (drops keys it does not accept)."""
        opts: dict[str, Any] = {
            "format": self.format,
            "print_background": self.print_background,
            "margin": {
                "top": self.margin_top,
                "right": self.margin_right,
                "bottom": self.margin_bottom,
                "left": self.margin_left,
            },
            "landscape": self.landscape,
            "scale": self.scale,
            "display_header_footer": self.display_header_footer,
            "header_template": self.header_template,
            "footer_template": self.footer_template,
            "prefer_css_page_size": self.prefer_css_page_size,
            "tagged": self.tagged,
        }
        if self.page_ranges:
            opts["page_ranges"] = self.page_ranges
        if self.width:
            opts["width"] = self.width
        if self.height:
            opts["height"] = self.height
        return opts


def render_html_to_pdf(
    html_path: Path,
    output: Path,
    options: PdfOptions | None = None,
    wait_until: str = "networkidle",
    timeout_ms: int = 30000,
) -> Path:
    """Render a single HTML file to PDF. Returns the output path.

    Loads the file via file:// URL, emulates print media, waits for network idle,
    then calls page.pdf(). Chromium's native outline (h1-h6 -> bookmarks) is
    enabled by default via options.outline.

    Browser selection (in priority order):
      1. options.executable_path  -> explicit binary
      2. options.channel          -> "chrome", "msedge", "chromium"
      3. env PDFGEN_BROWSER       -> same values as channel
      4. auto                     -> system Chrome, then Edge, then Playwright Chromium
    """
    import os
    options = options or PdfOptions()
    output.parent.mkdir(parents=True, exist_ok=True)
    url = html_path.resolve().as_uri()

    launch_kwargs: dict[str, Any] = {}
    if options.executable_path:
        launch_kwargs["executable_path"] = options.executable_path
    else:
        channel = options.channel or os.environ.get("PDFGEN_BROWSER", "")
        if channel:
            launch_kwargs["channel"] = channel
        else:
            # Auto detect: prefer system Chrome, then Edge.
            for ch in ("chrome", "msedge"):
                if _browser_exists(ch):
                    launch_kwargs["channel"] = ch
                    break

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        try:
            page = browser.new_page()
            page.emulate_media(media="print")
            page.goto(url, wait_until=wait_until, timeout=timeout_ms)
            page.wait_for_timeout(200)
            page.pdf(path=str(output), **options.to_playwright())
        finally:
            browser.close()
    return output


def _browser_exists(channel: str) -> bool:
    """Check whether a system browser for the given Playwright channel is installed."""
    import shutil
    if channel == "chrome":
        return shutil.which("google-chrome") is not None or \
               Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome").exists()
    if channel == "msedge":
        return shutil.which("microsoft-edge") is not None or \
               Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge").exists()
    return False
