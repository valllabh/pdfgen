# pdfgen

Template driven PDF generation CLI for agents and humans. HTML templates (Jinja2) + JSON/YAML data -> PDF via Playwright (Chromium). Merge and outline (bookmarks) supported.

Uses your system Google Chrome or Microsoft Edge directly, no Playwright Chromium download required.

## Install

```bash
make install
```

That is it. The CLI auto detects system Chrome (then Edge) and uses it via Playwright's `channel` launch. If you have neither, run `make install-browser` to download Playwright's bundled Chromium.

## Global access

The `pdfgen` binary lives in `.venv/bin/pdfgen`. Symlink it onto your PATH:

```bash
mkdir -p ~/.local/bin
ln -sf "$PWD/.venv/bin/pdfgen" ~/.local/bin/pdfgen
```

Now `pdfgen` works from anywhere.

## Usage

```bash
pdfgen templates                                   # list bundled templates
pdfgen new my-report --template report             # scaffold a project
pdfgen build -t report -d data.json -o report.pdf  # build a PDF
pdfgen merge a.pdf b.pdf -o merged.pdf             # merge PDFs
pdfgen outline report.pdf                          # show bookmarks
pdfgen outline report.pdf --add "Intro@1" --add "Body@3"
pdfgen info report.pdf                             # page count, size, outline
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
--browser chrome       browser to use: chrome, msedge, chromium, or path to binary
```

Browser selection priority: `--browser` flag > `PDFGEN_BROWSER` env var > auto detect (system Chrome, then Edge).

## Templates

Templates are discovered from three sources (first match wins when using `--template <name>`):

1. **Bundled** - shipped with pdfgen in `src/pdfgen/templates/`
2. **Local** - any directory in the current working tree with `manifest.json` + `template.html` (recursive)
3. **.pdfgen** - `.pdfgen/templates/` directories walking up from cwd to home (project -> parent dirs -> user level at `~/.pdfgen/templates/`)

A template is any directory containing both `manifest.json` and `template.html`.

| name    | description                                          |
|---------|------------------------------------------------------|
| report  | multi section report with cover, TOC, bookmarks      |
| letter  | single page business letter                          |
| invoice | invoice with line items, tax and totals              |
| blank   | minimal one title + body template, good starting point |

To create a custom template, copy one and edit:

```bash
# local template (in current directory)
pdfgen new custom-doc --template blank
# edit custom-doc/template.html and custom-doc/data.json
pdfgen build --template-dir custom-doc --data custom-doc/data.json -o custom-doc.pdf

# user level template (available everywhere via ~/.pdfgen/templates/)
pdfgen new my-tpl --template blank --user
# edit ~/.pdfgen/templates/my-tpl/template.html and data.json
pdfgen build -t my-tpl -d ~/.pdfgen/templates/my-tpl/data.json -o out.pdf

# project level template (in .pdfgen/templates/ at project root)
mkdir -p .pdfgen/templates/my-tpl
# add template.html and manifest.json there
pdfgen build -t my-tpl -d data.json -o out.pdf
```

`pdfgen templates` lists all three sources.

## Examples

```bash
make run-example    # builds examples/report/data/data.json -> out/report.pdf
```

See `examples/{report,letter,invoice}/data/data.json` for sample data shapes.

## Architecture

```
data (JSON/YAML) + template (Jinja2 HTML)
        |
        v
   render_template()  ->  intermediate HTML
        |
        v
   render_html_to_pdf()  (Playwright/Chromium, swappable)
        |
        v
   PDF  ->  merge / outline (pypdf)
```

The renderer is the only backend specific module. Replace `src/pdfgen/renderer.py` to switch engines without touching the CLI.

See `AGENTS.md` for contributor rules and `SKILL.md` for agent usage.
