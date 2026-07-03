"""Jinja2 template engine wrapper.

Templates are HTML files with Jinja2 variables. Data is loaded from JSON or
YAML and injected. The result is a self contained HTML file ready for the
renderer.

Template resolution order:
  1. --template <name>   -> bundled template dir (src/pdfgen/templates/<name>)
  2. --template-dir <p>  -> explicit directory containing template.html
  3. --html <file>       -> a single ad hoc HTML file (no data binding unless
                           it contains Jinja2 syntax; we still render it)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

# Directory of bundled templates shipped with the package.
BUNDLED_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def load_data(path: Path) -> dict[str, Any]:
    """Load JSON or YAML data file. Extension decides the parser."""
    text = path.read_text()
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text) or {}
    return json.loads(text)


def _make_env(search_path: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(search_path)),
        autoescape=select_autoescape(["html", "xml"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def resolve_template_dir(
    name: str | None = None,
    template_dir: Path | None = None,
) -> Path:
    """Resolve which directory holds the template.html to render."""
    if template_dir is not None:
        if not (template_dir / "template.html").exists():
            raise FileNotFoundError(f"template.html not found in {template_dir}")
        return template_dir
    if name:
        cand = BUNDLED_TEMPLATES_DIR / name
        if not cand.exists():
            available = sorted(p.name for p in BUNDLED_TEMPLATES_DIR.iterdir() if p.is_dir())
            raise FileNotFoundError(
                f"template '{name}' not found. Available: {', '.join(available)}"
            )
        return cand
    raise ValueError("either --template or --template-dir is required")


def _defaults_from_manifest(template_dir: Path) -> dict[str, Any]:
    """Read manifest.json variables and return a defaults dict for optional vars."""
    manifest = template_dir / "manifest.json"
    if not manifest.exists():
        return {}
    try:
        spec = json.loads(manifest.read_text())
    except Exception:
        return {}
    out: dict[str, Any] = {}
    for name, var in (spec.get("variables") or {}).items():
        if not var.get("required", False) and "default" in var:
            out[name] = var["default"]
    return out


def render_template(
    template_dir: Path,
    data: dict[str, Any],
    output_html: Path,
) -> Path:
    """Render template.html from template_dir with data, write to output_html.

    Optional variables declared in manifest.json with a `default` are injected
    when missing from `data`, so StrictUndefined still catches truly missing
    required variables.
    """
    defaults = _defaults_from_manifest(template_dir)
    merged = {**defaults, **data}
    env = _make_env(template_dir)
    template = env.get_template("template.html")
    rendered = template.render(**merged)
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(rendered)
    return output_html
