"""pdfgen: template driven PDF generation CLI for agents.

HTML templates (Jinja2) + JSON/YAML data -> PDF via Playwright (Chromium).
Supports merge, outline (bookmarks from h1-h6), and a project scaffold command.

See AGENTS.md and SKILL.md for agent usage.
"""
from __future__ import annotations

__version__ = "0.1.0"
