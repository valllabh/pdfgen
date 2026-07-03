---
name: pdfgen
description: Generate PDFs from HTML templates and JSON/YAML data using the pdfgen CLI. Wraps Playwright (Chromium) for rendering and pypdf for merge/outline. Use when the user asks to create, generate, build, or render a PDF, invoice, letter, report, or document from a template, or to merge PDFs and inspect bookmarks. Bundled templates are report, letter, invoice, blank. Custom templates are Jinja2 HTML files.
---

# pdfgen

CLI for template driven PDF generation. Lives at `/Users/vajoshi/Work/pdfgen`.

## Setup (one time)

```bash
cd /Users/vajoshi/Work/pdfgen
make install
make install-browser
```

The Python interpreter is `.venv/bin/python`. Always invoke the CLI via:

```bash
PY=/Users/vajoshi/Work/pdfgen/.venv/bin/python
$PY -m pdfgen <command>
```

## Commands

```bash
$PY -m pdfgen templates                                   # list bundled templates
$PY -m pdfgen new <dir> --template <name>                 # scaffold a project
$PY -m pdfgen build -t <name> -d <data.json> -o <out.pdf> # build a PDF
$PY -m pdfgen merge a.pdf b.pdf -o merged.pdf             # merge PDFs
$PY -m pdfgen outline <pdf>                               # show bookmarks
$PY -m pdfgen outline <pdf> --add "Title@page" --level 0  # add bookmarks
$PY -m pdfgen info <pdf>                                  # page count, size, outline
```

## Build options

```
--template NAME        bundled template (report, letter, invoice, blank)
--template-dir PATH    custom template directory containing template.html
--html PATH            pre rendered HTML file (skips templating)
--data PATH            JSON or YAML data file
--output PATH          output PDF
--format A4            paper format (A4, Letter, Legal, ...)
--landscape            landscape orientation
--margin 20mm          uniform margin
--no-outline           disable Chromium native bookmarks (h1-h6)
--keep-html            keep the rendered HTML next to the PDF
```

## Templates

Bundled templates live in `src/pdfgen/templates/<name>/` with a `template.html` (Jinja2) and a `manifest.json` describing required variables.

| name    | variables                                                                 |
|---------|---------------------------------------------------------------------------|
| report  | title, author?, date?, sections[]: {heading, body?, subsections?[]}       |
| letter  | from, to, date?, subject, body                                            |
| invoice | seller, buyer, invoiceNumber, date?, currency?, items[]: {description, qty, unitPrice}, taxRate? |
| blank   | title, body?                                                              |

`date: "auto"` resolves to today at build time.

## How to use as an agent

1. Pick a template with `pdfgen templates` or use `--template-dir` for a custom one.
2. Write the data file (JSON or YAML) matching the template variables. Read the template's `manifest.json` for the contract.
3. Run `pdfgen build -t <name> -d <data> -o <out.pdf>`.
4. For multi part documents, build each part then `pdfgen merge part1.pdf part2.pdf -o final.pdf`.
5. Inspect with `pdfgen info final.pdf`.

## Creating a custom template

```bash
$PY -m pdfgen new my-doc --template blank
# edit my-doc/template.html (Jinja2) and my-doc/data.json
$PY -m pdfgen build --template-dir my-doc --data my-doc/data.json -o my-doc.pdf
```

Template HTML is standard Jinja2. Use `{{ var }}` for values, `{% for x in items %}` for loops, and CSS `@page` for paper size and margins. Headings `h1`-`h6` become PDF bookmarks automatically (unless `--no-outline`).

## Examples

Ready to build examples live in `examples/{report,letter,invoice}/data/data.json`:

```bash
$PY -m pdfgen build -t report -d examples/report/data/data.json -o out/report.pdf
$PY -m pdfgen build -t invoice -d examples/invoice/data/data.json -o out/invoice.pdf
$PY -m pdfgen build -t letter -d examples/letter/data/data.json -o out/letter.pdf
```

## Backend

Renderer is Playwright (Chromium), the maintained Python successor to Puppeteer. Same engine, same `page.pdf()` semantics. The renderer module is swappable: replace `src/pdfgen/renderer.py` to switch engines without touching the CLI.
