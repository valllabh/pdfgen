"""pdfgen CLI.

Template driven PDF generation for agents and humans.

Quick start:
  pdfgen templates                       # list templates (bundled + local + .pdfgen)
  pdfgen new my-report --template report # scaffold a template
  pdfgen build --template report --data data.json -o report.pdf
  pdfgen build --html my.html -o out.pdf # render any HTML file directly
  pdfgen merge a.pdf b.pdf -o merged.pdf
  pdfgen info report.pdf                 # page count, outline, size

The build flow: data (JSON/YAML) + template (Jinja2 HTML with pdfgen: meta tags)
-> HTML -> PDF (Chromium).
Bundled templates: report, letter, invoice, blank.

A template is any .html file with a <meta name="pdfgen:name" content="..."> tag.
Variables are declared with <meta name="pdfgen:variable" content="title" data-required="true">.
No manifest.json needed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .merge import Bookmark, add_outline, extract_outline, merge_pdfs
from .renderer import PdfOptions, render_html_to_pdf
from .scaffold import scaffold_template, _sample_data_from_manifest
from .templating import (
    BUNDLED_TEMPLATES_DIR,
    USER_TEMPLATES_DIR,
    discover_dotpdfgen_templates,
    discover_templates,
    load_data,
    meta_to_manifest,
    parse_template_meta,
    render_template,
    resolve_template,
)

app = typer.Typer(add_completion=False, help="Template driven PDF generation CLI.")
console = Console()


def _print_version(ctx: typer.Context, value: bool) -> None:
    if value:
        console.print(f"pdfgen {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", callback=_print_version, is_eager=True),
) -> None:
    """pdfgen: template driven PDF generation CLI."""


@app.command()
def templates(
    cwd: bool = typer.Option(True, "--cwd/--no-cwd", help="Also list templates discovered in the current directory tree and .pdfgen dirs."),
) -> None:
    """List bundled, local and user level templates.

    Three sources are scanned:
      1. Bundled templates shipped with pdfgen.
      2. Local templates: any .html with a pdfgen:name meta tag found
         recursively in the current working directory tree.
      3. .pdfgen templates: .pdfgen/templates/ dirs walking up from cwd to
         home (project -> parent dirs -> user level at ~/.pdfgen/templates).
    """
    # Bundled
    bundled = Table(title="Bundled templates")
    bundled.add_column("name", style="cyan")
    bundled.add_column("description")
    for d in sorted(BUNDLED_TEMPLATES_DIR.iterdir()):
        if not d.is_dir():
            continue
        tfile = d / "template.html"
        if not tfile.exists():
            continue
        meta = parse_template_meta(tfile)
        bundled.add_row(meta.get("name", d.name), meta.get("description", ""))
    console.print(bundled)

    if not cwd:
        return

    # Local (recursive from cwd)
    local = discover_templates(Path.cwd())
    bundled_resolved = BUNDLED_TEMPLATES_DIR.resolve()
    local = [t for t in local if t["path"].resolve() != bundled_resolved and
             not t["path"].resolve().is_relative_to(bundled_resolved)]
    if local:
        table = Table(title="Local templates (current directory tree)")
        table.add_column("name", style="cyan")
        table.add_column("description")
        table.add_column("path", style="dim")
        for t in sorted(local, key=lambda x: x["name"]):
            table.add_row(t["name"], t["description"], str(t["path"]))
        console.print(table)
    else:
        console.print("[dim]No local templates found in current directory.[/dim]")

    # .pdfgen templates (walking up from cwd to home)
    dot = discover_dotpdfgen_templates()
    if dot:
        table = Table(title=".pdfgen templates (cwd up to ~/.pdfgen)")
        table.add_column("name", style="cyan")
        table.add_column("description")
        table.add_column("source", style="dim")
        table.add_column("path", style="dim")
        for t in sorted(dot, key=lambda x: (str(x["source"]), x["name"])):
            table.add_row(t["name"], t["description"], str(t["source"]), str(t["path"]))
        console.print(table)
    else:
        console.print("[dim]No .pdfgen templates found. Put .html templates in ~/.pdfgen/templates/<name>/[/dim]")


@app.command()
def new(
    target: Path = typer.Argument(..., help="Target directory for the new template."),
    template: str = typer.Option("blank", "--template", "-t", help="Bundled template to start from."),
    user: bool = typer.Option(False, "--user", help="Scaffold into ~/.pdfgen/templates/<target> so it is available everywhere."),
) -> None:
    """Scaffold a new pdfgen template at <target>.

    Creates a template.html (with pdfgen: meta tags) and a data.json skeleton.
    With --user, the template is created under ~/.pdfgen/templates/<target> and
    becomes available to pdfgen from any working directory.
    """
    if user:
        target = USER_TEMPLATES_DIR / target
    if target.exists() and any(target.iterdir()):
        raise typer.BadParameter(f"{target} is not empty")
    scaffold_template(template, target)
    # Generate a data.json skeleton from the template's meta tags.
    meta = parse_template_meta(target / "template.html")
    manifest = meta_to_manifest(meta) if meta else {"variables": {}}
    sample = _sample_data_from_manifest(manifest)
    (target / "data.json").write_text(json.dumps(sample, indent=2))
    console.print(f"[green]created[/green] template at {target}")
    if user:
        console.print(f"  available globally as: pdfgen build -t {target.name} -d {target / 'data.json'} -o out.pdf")
    else:
        console.print(f"  edit {target / 'data.json'} then run:")
        console.print(f"  pdfgen build --template-dir {target} --data {target / 'data.json'} -o out.pdf")


@app.command()
def build(
    template: str = typer.Option(None, "--template", "-t", help="Template name (bundled, local or .pdfgen)."),
    template_dir: Path = typer.Option(None, "--template-dir", help="Directory with template.html, or a direct .html file."),
    html: Path = typer.Option(None, "--html", help="Pre rendered HTML file to convert directly."),
    data: Path = typer.Option(None, "--data", "-d", help="JSON/YAML data file."),
    output: Path = typer.Option(Path("output.pdf"), "--output", "-o", help="Output PDF path."),
    fmt: str = typer.Option("A4", "--format", help="Paper format (A4, Letter, Legal, ...)."),
    landscape: bool = typer.Option(False, "--landscape", help="Landscape orientation."),
    margin: str = typer.Option("20mm", "--margin", help="Uniform margin, e.g. 20mm or 1in."),
    no_outline: bool = typer.Option(False, "--no-outline", help="Disable Chromium native bookmarks."),
    keep_html: bool = typer.Option(False, "--keep-html", help="Write the rendered HTML next to the PDF."),
    browser: str = typer.Option("", "--browser", help="Browser to use: chrome, msedge, chromium, or path to binary."),
) -> None:
    """Build a PDF from a template + data, or from a pre rendered HTML file."""
    if html is None and template is None and template_dir is None:
        raise typer.BadParameter("provide --template, --template-dir or --html")

    if html is not None:
        html_path = html
    else:
        tpath, manifest = resolve_template(name=template, template_dir=template_dir, html=html)
        payload = load_data(data) if data else {}
        html_path = output.with_suffix(".html")
        render_template(tpath, manifest, payload, html_path)

    # Resolve browser: --browser flag, then PDFGEN_BROWSER env, then auto detect.
    channel = ""
    executable_path = ""
    raw = browser or os.environ.get("PDFGEN_BROWSER", "")
    if raw:
        if raw in ("chrome", "msedge", "chromium"):
            channel = raw
        else:
            executable_path = raw

    opts = PdfOptions(
        format=fmt,
        landscape=landscape,
        margin_top=margin, margin_right=margin, margin_bottom=margin, margin_left=margin,
        outline=not no_outline,
        channel=channel,
        executable_path=executable_path,
    )
    out = render_html_to_pdf(html_path, output, opts)
    if not keep_html and html is None and html_path.exists():
        html_path.unlink()
    console.print(f"[green]built[/green] {out} ({out.stat().st_size} bytes)")


@app.command()
def merge(
    inputs: list[Path] = typer.Argument(..., help="PDF files to merge in order."),
    output: Path = typer.Option(Path("merged.pdf"), "--output", "-o", help="Output PDF."),
) -> None:
    """Merge multiple PDFs into one (in order)."""
    for p in inputs:
        if not p.exists():
            raise typer.BadParameter(f"missing: {p}")
    out = merge_pdfs(inputs, output)
    console.print(f"[green]merged[/green] {len(inputs)} files -> {out}")


@app.command()
def outline(
    pdf: Path = typer.Argument(..., help="PDF to inspect or augment."),
    add: list[str] = typer.Option(None, "--add", help="Add bookmark: 'title@page' (page is 1 indexed)."),
    level: int = typer.Option(0, "--level", help="Outline level for --add bookmarks."),
    output: Path = typer.Option(None, "--output", "-o", help="Output PDF (defaults to overwrite)."),
) -> None:
    """Inspect or add bookmarks (outline) to a PDF."""
    if add:
        bms = []
        for spec in add:
            if "@" not in spec:
                raise typer.BadParameter(f"expected 'title@page', got {spec!r}")
            title, page = spec.rsplit("@", 1)
            bms.append(Bookmark(title=title, page=int(page) - 1, level=level))
        out = add_outline(pdf, bms, output)
        console.print(f"[green]added[/green] {len(bms)} bookmarks -> {out}")
    else:
        bms = extract_outline(pdf)
        if not bms:
            console.print("[yellow]no outline found[/yellow]")
            return
        table = Table(title=f"Outline of {pdf.name}")
        table.add_column("level", style="cyan")
        table.add_column("page", style="magenta")
        table.add_column("title")
        for bm in bms:
            table.add_row(str(bm.level), str(bm.page + 1), bm.title)
        console.print(table)


@app.command(name="info")
def info_(pdf: Path = typer.Argument(..., help="PDF file.")) -> None:
    """Show page count, file size and outline of a PDF."""
    from pypdf import PdfReader
    reader = PdfReader(str(pdf))
    size_kb = pdf.stat().st_size / 1024
    console.print(f"[cyan]{pdf.name}[/cyan]  {len(reader.pages)} pages  {size_kb:.1f} KB")
    bms = extract_outline(pdf)
    if bms:
        console.print(f"[green]{len(bms)}[/green] bookmarks")
        for bm in bms[:20]:
            indent = "  " * bm.level
            console.print(f"  {indent}- {bm.title}  (p.{bm.page + 1})")
        if len(bms) > 20:
            console.print(f"  ... and {len(bms) - 20} more")


if __name__ == "__main__":
    app()
