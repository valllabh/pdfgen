"""Scaffold a new pdfgen project or a custom template into a target directory."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .templating import BUNDLED_TEMPLATES_DIR

# Sample placeholders per declared variable type, used to seed data.json.
_SAMPLE: dict[str, Any] = {
    "string": "sample",
    "number": 0,
    "array": [],
}


def _sample_data_from_manifest(manifest_path: Path) -> dict[str, Any]:
    """Build a data.json skeleton from a manifest.json variable contract."""
    if not manifest_path.exists():
        return {"title": "sample"}
    try:
        spec = json.loads(manifest_path.read_text())
    except Exception:
        return {"title": "sample"}
    out: dict[str, Any] = {}
    for name, var in (spec.get("variables") or {}).items():
        if "default" in var and var.get("default") != "auto":
            out[name] = var["default"]
        else:
            out[name] = _SAMPLE.get(var.get("type", "string"), "sample")
    return out


def scaffold_project(target: Path, name: str | None = None) -> Path:
    """Create a new pdfgen project skeleton at target.

    Layout:
      <target>/
        data.json
        template.html
        manifest.json
    """
    target.mkdir(parents=True, exist_ok=True)
    project_name = name or target.name
    (target / "data.json").write_text(json.dumps({
        "title": project_name,
        "body": "Hello from pdfgen.",
    }, indent=2))
    (target / "template.html").write_text(
        '<!DOCTYPE html>\n<html><head><meta charset="UTF-8">\n'
        '<title>{{ title }}</title>\n'
        '<style>@page{size:A4;margin:20mm}body{font-family:sans-serif}</style>\n'
        '</head><body>\n  <h1>{{ title }}</h1>\n  <div>{{ body }}</div>\n'
        '</body></html>\n'
    )
    (target / "manifest.json").write_text(json.dumps({
        "name": project_name,
        "description": "Custom pdfgen template.",
        "variables": {
            "title": {"type": "string", "required": True},
            "body": {"type": "string", "required": False, "default": ""},
        },
    }, indent=2))
    return target


def scaffold_template(name: str, target: Path) -> Path:
    """Copy a bundled template into target dir (for customization).

    Updates the manifest.json `name` field to match the target directory name
    so discovery reports the correct name.
    """
    src = BUNDLED_TEMPLATES_DIR / name
    if not src.exists():
        available = sorted(p.name for p in BUNDLED_TEMPLATES_DIR.iterdir() if p.is_dir())
        raise FileNotFoundError(f"template '{name}' not found. Available: {', '.join(available)}")
    target.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        shutil.copy2(f, target / f.name)
    # Update manifest name to match target dir name.
    manifest = target / "manifest.json"
    if manifest.exists():
        try:
            spec = json.loads(manifest.read_text())
            spec["name"] = target.name
            manifest.write_text(json.dumps(spec, indent=2))
        except Exception:
            pass
    return target
