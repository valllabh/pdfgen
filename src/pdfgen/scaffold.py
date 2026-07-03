"""Scaffold a new pdfgen template into a target directory.

Templates are single HTML files with pdfgen: meta tags. No manifest.json.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .templating import BUNDLED_TEMPLATES_DIR, parse_template_meta, meta_to_manifest

# Sample placeholders per declared variable type, used to seed data.json.
_SAMPLE: dict[str, Any] = {
    "string": "sample",
    "number": 0,
    "array": [],
}


def _sample_data_from_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Build a data.json skeleton from a manifest dict (from meta tags)."""
    out: dict[str, Any] = {}
    for name, var in (manifest.get("variables") or {}).items():
        if "default" in var:
            out[name] = var["default"]
        else:
            out[name] = _SAMPLE.get(var.get("type", "string"), "sample")
    return out


def scaffold_template(name: str, target: Path) -> Path:
    """Copy a bundled template HTML file into target (for customization).

    Updates the pdfgen:name meta tag to match the target name.
    """
    src = BUNDLED_TEMPLATES_DIR / name / "template.html"
    if not src.exists():
        available = sorted(p.name for p in BUNDLED_TEMPLATES_DIR.iterdir() if p.is_dir())
        raise FileNotFoundError(f"template '{name}' not found. Available: {', '.join(available)}")
    target.mkdir(parents=True, exist_ok=True)
    dst = target / "template.html"
    shutil.copy2(src, dst)
    # Update pdfgen:name meta tag to match target name.
    text = dst.read_text()
    import re
    text = re.sub(
        r'(name="pdfgen:name"\s+content=")[^"]*(")',
        rf'\g<1>{target.name}\g<2>',
        text,
        count=1,
    )
    dst.write_text(text)
    return target
