"""Jinja2 template engine wrapper.

Templates are HTML files with Jinja2 variables. Data is loaded from JSON or
YAML and injected. The result is a self contained HTML file ready for the
renderer.

Template resolution order (first match wins):
  1. --template-dir <p>  -> explicit directory containing template.html
  2. --template <name>   -> bundled template (src/pdfgen/templates/<name>)
  3. <name> in cwd tree  -> any dir with manifest.json + template.html
                            discovered recursively from cwd
  4. <name> in .pdfgen   -> .pdfgen/templates/<name> walking up from cwd
                            to home (project -> parent dirs -> user level)
  5. --html <file>       -> a single ad hoc HTML file (no data binding unless
                           it contains Jinja2 syntax; we still render it)
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

# Directory of bundled templates shipped with the package.
BUNDLED_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
# User level template directory.
USER_TEMPLATES_DIR = Path.home() / ".pdfgen" / "templates"
# Marker directory name walked up from cwd to discover project/parent templates.
PDFGEN_DIR_NAME = ".pdfgen"


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
    search_cwd: bool = True,
) -> Path:
    """Resolve which directory holds the template.html to render.

    Resolution order (first match wins):
      1. template_dir (explicit directory containing template.html)
      2. bundled template named <name> in src/pdfgen/templates/
      3. <name> discovered in the current working tree (recursive)
      4. <name> in .pdfgen/templates/ walking up from cwd to home
    """
    if template_dir is not None:
        if not (template_dir / "template.html").exists():
            raise FileNotFoundError(f"template.html not found in {template_dir}")
        return template_dir
    if name:
        # 2. Bundled
        cand = BUNDLED_TEMPLATES_DIR / name
        if cand.exists():
            return cand
        # 3. Local cwd tree (recursive)
        if search_cwd:
            local = find_local_template(name)
            if local is not None:
                return local
        # 4. .pdfgen/templates/ walking up from cwd to home
        dot = find_dotpdfgen_template(name)
        if dot is not None:
            return dot
        available = sorted(p.name for p in BUNDLED_TEMPLATES_DIR.iterdir() if p.is_dir())
        local_names = [t["name"] for t in discover_templates(Path.cwd())] if search_cwd else []
        dot_names = [t["name"] for t in discover_dotpdfgen_templates()]
        raise FileNotFoundError(
            f"template '{name}' not found. "
            f"Bundled: {', '.join(available) or '(none)'}. "
            f"Local: {', '.join(local_names) or '(none)'}. "
            f"User/.pdfgen: {', '.join(dot_names) or '(none)'}."
        )
    raise ValueError("either --template or --template-dir is required")


def discover_templates(root: Path) -> list[dict[str, Any]]:
    """Recursively find templates under root.

    A template is any directory containing both manifest.json and template.html.
    Returns a list of dicts: {name, description, path, bundled?}.
    """
    out: list[dict[str, Any]] = []
    if not root.exists() or not root.is_dir():
        return out
    for manifest in root.rglob("manifest.json"):
        tdir = manifest.parent
        if not (tdir / "template.html").exists():
            continue
        try:
            spec = json.loads(manifest.read_text())
        except Exception:
            spec = {}
        out.append({
            "name": spec.get("name") or tdir.name,
            "description": spec.get("description", ""),
            "path": tdir,
        })
    return out


def find_local_template(name: str, root: Path | None = None) -> Path | None:
    """Find a template by name in the current working tree.

    Matches either the manifest `name` field or the directory name.
    """
    root = root or Path.cwd()
    for t in discover_templates(root):
        if t["name"] == name or t["path"].name == name:
            return t["path"]
    return None


def dotpdfgen_dirs(start: Path | None = None) -> list[Path]:
    """Return .pdfgen directories walking up from start (cwd) to home.

    Order: closest to cwd first, then parents, then ~/.pdfgen last.
    Duplicates are removed while preserving order.
    """
    start = (start or Path.cwd()).resolve()
    home = Path.home().resolve()
    dirs: list[Path] = []
    seen: set[Path] = set()
    cur = start
    while True:
        cand = cur / PDFGEN_DIR_NAME
        if cand.is_dir():
            rp = cand.resolve()
            if rp not in seen:
                seen.add(rp)
                dirs.append(rp)
        if cur == home or cur.parent == cur:
            break
        cur = cur.parent
    # Always include ~/.pdfgen even if cwd is not under home.
    user_dir = (home / PDFGEN_DIR_NAME).resolve()
    if user_dir not in seen and user_dir.is_dir():
        dirs.append(user_dir)
    return dirs


def discover_dotpdfgen_templates() -> list[dict[str, Any]]:
    """Discover templates in all .pdfgen/templates/ dirs from cwd up to home.

    Each .pdfgen dir is treated as a templates root: we look for either
    .pdfgen/templates/<name>/{manifest.json,template.html} or
    .pdfgen/<name>/{manifest.json,template.html}.
    Returns list of {name, description, path, source} where source is the
    .pdfgen dir that contained it. Duplicates (same path found via multiple
    roots) are removed.
    """
    out: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for dot in dotpdfgen_dirs():
        # Prefer .pdfgen/templates/, fall back to .pdfgen/ itself.
        roots = [dot / "templates", dot]
        for root in roots:
            if not root.is_dir():
                continue
            for t in discover_templates(root):
                rp = t["path"].resolve()
                if rp in seen:
                    continue
                seen.add(rp)
                t["source"] = dot
                out.append(t)
    return out


def find_dotpdfgen_template(name: str) -> Path | None:
    """Find a template by name in any .pdfgen dir from cwd up to home."""
    for t in discover_dotpdfgen_templates():
        if t["name"] == name or t["path"].name == name:
            return t["path"]
    return None


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
