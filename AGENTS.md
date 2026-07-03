# AGENTS.md

Project rules for `pdfgen`. Read this before working in the repo.

## What this is

`pdfgen` is a Python CLI that turns HTML templates (Jinja2) + JSON/YAML data into PDFs using Playwright (Chromium). Templates are identified by `pdfgen:` meta tags in the HTML `<head>` (no manifest.json needed). The renderer is swappable: replace `src/pdfgen/renderer.py` with another backend and the CLI keeps working.

## Commands

```bash
make install          # create venv, install deps (uses system Chrome/Edge)
make install-browser  # optional: install Playwright Chromium if no system browser
make test             # run unit tests (no browser)
make run-example      # build examples/report/data/data.json -> out/report.pdf
make clean            # remove venv, outputs, caches
```

Run the CLI directly without global install:

```bash
.venv/bin/python -m pdfgen --help
.venv/bin/python -m pdfgen templates
.venv/bin/python -m pdfgen build -t report -d examples/report/data/data.json -o out/report.pdf --browser chrome
.venv/bin/python -m pdfgen merge a.pdf b.pdf -o merged.pdf
.venv/bin/python -m pdfgen info out/report.pdf
```

Browser selection priority: `--browser` flag > `PDFGEN_BROWSER` env var > auto detect (system Chrome, then Edge).

## Template format

A template is any `.html` file with `pdfgen:` meta tags in `<head>`:

```html
<meta name="pdfgen:name" content="my-template">          <!-- required -->
<meta name="pdfgen:description" content="...">           <!-- optional -->
<meta name="pdfgen:variable" content="title" data-type="string" data-required="true">  <!-- optional, repeatable -->
<meta name="pdfgen:variable" content="body" data-type="string" data-default="">
```

No manifest.json, no fixed directory layout. The HTML body is Jinja2 with `{{ var }}` and `{% for %}`.

## Layout

```
src/pdfgen/
  cli.py          Typer CLI entrypoint (commands: templates, new, build, merge, outline, info)
  renderer.py     Playwright HTML -> PDF renderer (swappable backend)
  templating.py   Jinja2 template + data binding, meta tag parsing, template resolution
  merge.py        pypdf merge + outline (bookmark) helpers
  scaffold.py     template scaffolding
  templates/      bundled templates (report, letter, invoice, blank)
    <name>/
      template.html   Jinja2 HTML with pdfgen: meta tags
examples/         ready to build example projects with data.json
tests/            unit tests for pure modules
```

## Adding a template

Templates are discovered from three sources (first match wins for `--template <name>`):
1. Bundled: `src/pdfgen/templates/<name>/template.html`
2. Local: any `.html` with `pdfgen:name` meta tag found recursively in cwd
3. .pdfgen: `.pdfgen/templates/` walking up from cwd to home (project -> parent dirs -> `~/.pdfgen/templates/`)

To add a bundled template:
1. Create `src/pdfgen/templates/<name>/template.html` with pdfgen: meta tags and Jinja2 body.
2. The CLI auto discovers it via `pdfgen templates` and `pdfgen new --template <name>`.
3. Add an example under `examples/<name>/data/data.json`.
4. Add a unit test in `tests/test_core.py` asserting the template renders with sample data.

To add a user level template: `pdfgen new <name> --template blank --user` (creates `~/.pdfgen/templates/<name>/`).
To add a project level template: put a `.html` file with pdfgen: meta tags in `.pdfgen/templates/<name>/` at the project root.
To add a standalone template: just add pdfgen: meta tags to any `.html` file in your project.

## Conventions

- Python 3.11+, ESM style imports, type hints everywhere.
- Typer for CLI, Rich for output, Jinja2 for templates, pypdf for merge/outline.
- StrictUndefined in Jinja2 so missing variables fail loudly.
- Keep `renderer.py` backend agnostic in spirit: all Playwright specifics stay there.
- No emojis in markdown or source comments.
- Makefile is the source of truth for build/test/run commands.

## Swapping the backend

`renderer.render_html_to_pdf(html_path, output, options)` is the only entrypoint the CLI uses. To switch engines (WeasyPrint, Typst, headless Chromium via subprocess, ...) reimplement that function with the same signature. `PdfOptions` carries Puppeteer style options; map them inside the new backend.
