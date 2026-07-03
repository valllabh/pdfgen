"""Jinja2 template engine wrapper.

Templates are HTML files with Jinja2 variables. Data is loaded from JSON or
YAML and injected. The result is a self contained HTML file ready for the
renderer.

A template is a single .html file with pdfgen meta tags in its <head>
(inspired by Open Graph meta tags). No manifest.json or fixed directory
layout required.

Meta tag format (standard HTML, in <head>):
  <meta name="pdfgen:name" content="my-template">
  <meta name="pdfgen:description" content="A custom template">
  <meta name="pdfgen:variable" content="title" data-type="string" data-required="true">
  <meta name="pdfgen:variable" content="body" data-type="string" data-default="">

Required: pdfgen:name (identifies the file as a template).
Optional: pdfgen:description, pdfgen:variable (repeatable).

Template resolution order (first match wins):
  1. --html <file>        -> a single HTML file (rendered directly)
  2. --template-dir <p>   -> a directory containing template.html
  3. --template <name>    -> bundled template (src/pdfgen/templates/<name>/template.html)
  4. <name> in cwd tree   -> any .html with pdfgen:name=<name> discovered
                             recursively from cwd
  5. <name> in .pdfgen    -> .pdfgen/templates/ walking up from cwd to home
"""
from __future__ import annotations

import json
import re
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
# Meta tag name prefix that identifies pdfgen template metadata.
META_PREFIX = "pdfgen:"

# Regex to extract <meta> tags from HTML head. Captures name + attributes.
META_RE = re.compile(
    r'<meta\s+([^>]*?)/?>',
    re.IGNORECASE,
)
ATTR_RE = re.compile(
    r'(\w[\w-]*)\s*=\s*"([^"]*)"|(\w[\w-]*)\s*=\s*\'([^\']*)\'',
)


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


# ---------- meta tag parsing ----------

def _parse_meta_attrs(attr_string: str) -> dict[str, str]:
    """Parse HTML attribute string into a dict."""
    attrs: dict[str, str] = {}
    for m in ATTR_RE.finditer(attr_string):
        key = m.group(1) or m.group(3)
        val = m.group(2) or m.group(4)
        if key:
            attrs[key.lower()] = val
    return attrs


def parse_template_meta(html_path: Path) -> dict[str, Any]:
    """Parse pdfgen meta tags from an HTML file.

    Returns dict with keys: name, description, variables (list of dicts),
    raw (the matched meta tag strings). Returns empty dict if no pdfgen meta
    tags are found.
    """
    try:
        text = html_path.read_text()
    except Exception:
        return {}
    out: dict[str, Any] = {"name": "", "description": "", "variables": []}
    for m in META_RE.finditer(text):
        attrs = _parse_meta_attrs(m.group(1))
        name_attr = attrs.get("name", "")
        if not name_attr.lower().startswith(META_PREFIX):
            continue
        key = name_attr[len(META_PREFIX):].lower()
        content = attrs.get("content", "")
        if key == "name":
            out["name"] = content
        elif key == "description":
            out["description"] = content
        elif key == "variable":
            var = {
                "name": content,
                "type": attrs.get("data-type", "string"),
                "required": attrs.get("data-required", "false").lower() == "true",
            }
            # Only include default if the attribute was present (even if empty string).
            if "data-default" in attrs:
                var["default"] = attrs["data-default"]
            out["variables"].append(var)
    if not out["name"]:
        return {}
    return out


def meta_to_manifest(meta: dict[str, Any]) -> dict[str, Any]:
    """Convert parsed meta tags into a manifest style dict for internal use."""
    variables: dict[str, Any] = {}
    for v in meta.get("variables", []):
        vn = v.pop("name")
        variables[vn] = v
    return {
        "name": meta.get("name", ""),
        "description": meta.get("description", ""),
        "variables": variables,
    }


# ---------- template resolution ----------

def resolve_template(
    name: str | None = None,
    template_dir: Path | None = None,
    html: Path | None = None,
    search_cwd: bool = True,
) -> tuple[Path, dict[str, Any]]:
    """Resolve a template to (html_path, manifest_dict).

    Resolution order:
      1. html (explicit file)
      2. template_dir (directory with template.html)
      3. bundled template named <name>
      4. <name> discovered in cwd tree (recursive)
      5. <name> in .pdfgen/templates/ walking up to home
    """
    if html is not None:
        meta = parse_template_meta(html)
        manifest = meta_to_manifest(meta) if meta else {"name": html.stem, "description": "", "variables": {}}
        return html, manifest

    if template_dir is not None:
        tfile = template_dir / "template.html"
        if not tfile.exists():
            # Maybe template_dir IS the html file.
            if template_dir.is_file() and template_dir.suffix == ".html":
                meta = parse_template_meta(template_dir)
                manifest = meta_to_manifest(meta) if meta else {"name": template_dir.stem, "description": "", "variables": {}}
                return template_dir, manifest
            raise FileNotFoundError(f"template.html not found in {template_dir}")
        meta = parse_template_meta(tfile)
        manifest = meta_to_manifest(meta) if meta else {"name": template_dir.name, "description": "", "variables": {}}
        return tfile, manifest

    if name:
        # 3. Bundled
        cand = BUNDLED_TEMPLATES_DIR / name / "template.html"
        if cand.exists():
            meta = parse_template_meta(cand)
            manifest = meta_to_manifest(meta) if meta else {"name": name, "description": "", "variables": {}}
            return cand, manifest
        # 4. Local cwd tree (recursive)
        if search_cwd:
            local = find_template_by_name(name)
            if local is not None:
                meta = parse_template_meta(local)
                manifest = meta_to_manifest(meta) if meta else {"name": name, "description": "", "variables": {}}
                return local, manifest
        # 5. .pdfgen/templates/ walking up to home
        dot = find_dotpdfgen_template(name)
        if dot is not None:
            meta = parse_template_meta(dot)
            manifest = meta_to_manifest(meta) if meta else {"name": name, "description": "", "variables": {}}
            return dot, manifest
        available = sorted(p.name for p in BUNDLED_TEMPLATES_DIR.iterdir() if p.is_dir())
        local_names = [t["name"] for t in discover_templates(Path.cwd())] if search_cwd else []
        dot_names = [t["name"] for t in discover_dotpdfgen_templates()]
        raise FileNotFoundError(
            f"template '{name}' not found. "
            f"Bundled: {', '.join(available) or '(none)'}. "
            f"Local: {', '.join(local_names) or '(none)'}. "
            f"User/.pdfgen: {', '.join(dot_names) or '(none)'}."
        )
    raise ValueError("provide --template, --template-dir or --html")


# ---------- discovery ----------

def discover_templates(root: Path) -> list[dict[str, Any]]:
    """Recursively find templates under root.

    A template is any .html file with a pdfgen:name meta tag. Returns a list
    of dicts: {name, description, path}.
    """
    out: list[dict[str, Any]] = []
    if not root.exists() or not root.is_dir():
        return out
    for html in root.rglob("*.html"):
        meta = parse_template_meta(html)
        if not meta or not meta["name"]:
            continue
        out.append({
            "name": meta["name"],
            "description": meta.get("description", ""),
            "path": html,
        })
    return out


def find_template_by_name(name: str, root: Path | None = None) -> Path | None:
    """Find a template by name in the current working tree."""
    root = root or Path.cwd()
    for t in discover_templates(root):
        if t["name"] == name or t["path"].stem == name:
            return t["path"]
    return None


def dotpdfgen_dirs(start: Path | None = None) -> list[Path]:
    """Return .pdfgen directories walking up from start (cwd) to home."""
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
    user_dir = (home / PDFGEN_DIR_NAME).resolve()
    if user_dir not in seen and user_dir.is_dir():
        dirs.append(user_dir)
    return dirs


def discover_dotpdfgen_templates() -> list[dict[str, Any]]:
    """Discover templates in all .pdfgen dirs from cwd up to home."""
    out: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for dot in dotpdfgen_dirs():
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
        if t["name"] == name or t["path"].stem == name:
            return t["path"]
    return None


# ---------- defaults + rendering ----------

def _defaults_from_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return a defaults dict for optional variables that declare a default."""
    out: dict[str, Any] = {}
    for name, var in (manifest.get("variables") or {}).items():
        if not var.get("required", False) and "default" in var:
            out[name] = var["default"]
    return out


def render_template(
    html_path: Path,
    manifest: dict[str, Any],
    data: dict[str, Any],
    output_html: Path,
) -> Path:
    """Render an HTML template with data, write to output_html.

    Optional variables declared with a default are injected when missing from
    data, so StrictUndefined still catches truly missing required variables.
    """
    defaults = _defaults_from_manifest(manifest)
    merged = {**defaults, **data}
    env = _make_env(html_path.parent)
    template = env.get_template(html_path.name)
    rendered = template.render(**merged)
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(rendered)
    return output_html
