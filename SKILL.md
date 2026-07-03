---
name: pdfgen
description: Generate PDFs from HTML templates and JSON/YAML data using the pdfgen CLI. Wraps Playwright (Chromium) for rendering and pypdf for merge/outline. Use when the user asks to create, generate, build, or render a PDF, invoice, letter, report, or document from a template, or to merge PDFs and inspect bookmarks. Templates are HTML files with pdfgen: meta tags (like Open Graph). Bundled templates are report, letter, invoice, blank. Custom templates are just HTML files with meta tags.
---

# pdfgen

CLI for template driven PDF generation. Lives at `/Users/vajoshi/Work/pdfgen`.

## Setup (one time)

```bash
cd /Users/vajoshi/Work/pdfgen
make install
```

Uses system Chrome or Edge directly. No browser download needed.

The Python interpreter is `.venv/bin/python`. The `pdfgen` binary is symlinked to `~/.local/bin/pdfgen`.

## Template format

A template is any `.html` file with `pdfgen:` meta tags in `<head>` (like Open Graph):

```html
<meta name="pdfgen:name" content="my-template">          <!-- required -->
<meta name="pdfgen:description" content="A custom template">  <!-- optional -->
<meta name="pdfgen:variable" content="title" data-type="string" data-required="true">
<meta name="pdfgen:variable" content="body" data-type="string" data-default="">
```

The HTML body is Jinja2: `{{ var }}`, `{% for item in items %}`, `{% if %}`. No manifest.json needed.

## Commands

```bash
pdfgen templates                                   # list all templates (bundled + local + .pdfgen)
pdfgen new <dir> --template <name>                 # scaffold a template
pdfgen new <dir> --template <name> --user          # scaffold into ~/.pdfgen/templates/ (global)
pdfgen build -t <name> -d <data.json> -o <out.pdf> # build from template name
pdfgen build --html <file.html> -o <out.pdf>       # render any HTML file directly
pdfgen build --template-dir <dir> -d <data> -o <out.pdf>  # build from a directory
pdfgen merge a.pdf b.pdf -o merged.pdf             # merge PDFs
pdfgen outline <pdf>                               # show bookmarks
pdfgen outline <pdf> --add "Title@page" --level 0  # add bookmarks
pdfgen info <pdf>                                  # page count, size, outline
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

## Template discovery

Templates are discovered from three sources (first match wins for `--template <name>`):
1. **Bundled** - shipped with pdfgen (report, letter, invoice, blank)
2. **Local** - any `.html` with `pdfgen:name` meta tag found recursively in cwd
3. **.pdfgen** - `.pdfgen/templates/` walking up from cwd to home (project -> parent dirs -> `~/.pdfgen/templates/`)

## Bundled templates

| name    | variables                                                                 |
|---------|---------------------------------------------------------------------------|
| report  | title, author?, date?, sections[]: {heading, body?, subsections?[]}       |
| letter  | from, to, date?, subject, body                                            |
| invoice | seller, buyer, invoiceNumber, date?, currency?, items[]: {description, qty, unitPrice}, taxRate? |
| blank   | title, body?                                                              |

`date: "auto"` resolves to today at build time.

## How to use as an agent

1. Pick a template with `pdfgen templates` or use `--html` for any HTML file.
2. Write the data file (JSON or YAML) matching the template variables. Read the template's `pdfgen:variable` meta tags for the contract.
3. Run `pdfgen build -t <name> -d <data> -o <out.pdf> --browser chrome`.
4. For multi part documents, build each part then `pdfgen merge part1.pdf part2.pdf -o final.pdf`.
5. Inspect with `pdfgen info final.pdf`.

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
pdfgen new my-doc --template blank
# edit my-doc/template.html and my-doc/data.json
pdfgen build --template-dir my-doc --data my-doc/data.json -o my-doc.pdf
```

## Examples

```bash
pdfgen build -t report -d examples/report/data/data.json -o out/report.pdf --browser chrome
pdfgen build -t invoice -d examples/invoice/data/data.json -o out/invoice.pdf --browser chrome
pdfgen build -t letter -d examples/letter/data/data.json -o out/letter.pdf --browser chrome
```

## Backend

Renderer is Playwright (Chromium), the maintained Python successor to Puppeteer. Same engine, same `page.pdf()` semantics. Uses system Chrome or Edge directly. The renderer module is swappable: replace `src/pdfgen/renderer.py` to switch engines without touching the CLI.
