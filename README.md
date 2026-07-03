# pdfgen

Template driven PDF generation CLI for agents and humans. HTML templates (Jinja2) + JSON/YAML data -> PDF via Playwright (Chromium). Merge and outline (bookmarks) supported.

Uses your system Google Chrome or Microsoft Edge directly, no Playwright Chromium download required.

## Templates

A template is any `.html` file with `pdfgen:` meta tags in its `<head>` (inspired by Open Graph meta tags). No manifest.json, no fixed directory layout needed.

```html
<meta name="pdfgen:name" content="my-template">
<meta name="pdfgen:description" content="A custom template">
<meta name="pdfgen:variable" content="title" data-type="string" data-required="true">
<meta name="pdfgen:variable" content="body" data-type="string" data-default="">
```

- `pdfgen:name` (required) - identifies the file as a template
- `pdfgen:description` (optional) - human readable description
- `pdfgen:variable` (optional, repeatable) - declares a variable with `data-type`, `data-required`, `data-default`

Templates are discovered from three sources (first match wins for `--template <name>`):
1. **Bundled** - shipped with pdfgen in `src/pdfgen/templates/`
2. **Local** - any `.html` with `pdfgen:name` found recursively in the current working directory
3. **.pdfgen** - `.pdfgen/templates/` walking up from cwd to home (project -> parent dirs -> `~/.pdfgen/templates/`)

## Install

```bash
make install
```

The CLI auto detects system Chrome (then Edge). If you have neither, run `make install-browser`.

## Global access

```bash
mkdir -p ~/.local/bin
ln -sf "$PWD/.venv/bin/pdfgen" ~/.local/bin/pdfgen
```

## Usage

```bash
pdfgen templates                                   # list all templates
pdfgen new my-report --template report             # scaffold a template
pdfgen build -t report -d data.json -o report.pdf  # build from template name
pdfgen build --html my.html -o out.pdf             # render any HTML file directly
pdfgen merge a.pdf b.pdf -o merged.pdf             # merge PDFs
pdfgen outline report.pdf                          # show bookmarks
pdfgen outline report.pdf --add "Intro@1" --add "Body@3"
pdfgen info report.pdf                             # page count, size, outline
```

## Build options

```
--template NAME        template name (bundled, local or .pdfgen)
--template-dir PATH    directory with template.html, or a direct .html file
--html PATH            pre rendered HTML file (skips templating)
--data PATH            JSON or YAML data file
--output PATH          output PDF
--format A4            paper format (A4, Letter, Legal, ...)
--landscape            landscape orientation
--margin 20mm          uniform margin
--no-outline           disable Chromium native bookmarks (h1-h6)
--keep-html            keep the rendered HTML next to the PDF
--browser chrome       browser to use: chrome, msedge, chromium, or path to binary
```

Browser selection priority: `--browser` flag > `PDFGEN_BROWSER` env var > auto detect (system Chrome, then Edge).

## Bundled templates

| name    | description                                          |
|---------|------------------------------------------------------|
| report  | multi section report with cover, TOC, bookmarks      |
| letter  | single page business letter                          |
| invoice | invoice with line items, tax and totals              |
| blank   | minimal one title + body template, good starting point |

## Creating a custom template

Just add `pdfgen:` meta tags to any HTML file:

```html
<!DOCTYPE html>
<html><head>
<meta name="pdfgen:name" content="my-doc">
<meta name="pdfgen:description" content="My custom document">
<meta name="pdfgen:variable" content="title" data-type="string" data-required="true">
<meta name="pdfgen:variable" content="items" data-type="array" data-required="true">
<title>{{ title }}</title>
<style>@page{size:A4;margin:20mm}body{font-family:sans-serif}</style>
</head><body>
<h1>{{ title }}</h1>
{% for item in items %}<p>{{ item }}</p>{% endfor %}
</body></html>
```

Save it anywhere in your project and `pdfgen templates` will find it. Or scaffold from a bundled template:

```bash
# local template
pdfgen new custom-doc --template blank
pdfgen build --template-dir custom-doc --data custom-doc/data.json -o custom-doc.pdf

# user level template (available everywhere)
pdfgen new my-tpl --template blank --user
pdfgen build -t my-tpl -d ~/.pdfgen/templates/my-tpl/data.json -o out.pdf
```

## Examples

```bash
make run-example    # builds examples/report/data/data.json -> out/report.pdf
```

See `examples/{report,letter,invoice}/data/data.json` for sample data shapes.

## Architecture

```
data (JSON/YAML) + template (HTML with pdfgen: meta tags)
        |
        v
   render_template()  ->  intermediate HTML (Jinja2)
        |
        v
   render_html_to_pdf()  (Playwright/Chromium, swappable)
        |
        v
   PDF  ->  merge / outline (pypdf)
```

The renderer is the only backend specific module. Replace `src/pdfgen/renderer.py` to switch engines without touching the CLI.

See `AGENTS.md` for contributor rules and `SKILL.md` for agent usage.
