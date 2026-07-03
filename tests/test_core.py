"""Unit tests for pure (non browser) modules. Browser tests are marked slow."""
import json
from pathlib import Path

import pytest

from pdfgen.templating import (
    BUNDLED_TEMPLATES_DIR,
    discover_templates,
    find_template_by_name,
    load_data,
    meta_to_manifest,
    parse_template_meta,
    render_template,
    resolve_template,
)
from pdfgen.scaffold import scaffold_template, _sample_data_from_manifest


def test_bundled_templates_present():
    names = {p.name for p in BUNDLED_TEMPLATES_DIR.iterdir() if p.is_dir()}
    assert {"report", "letter", "invoice", "blank"} <= names


def test_parse_template_meta_report():
    tfile = BUNDLED_TEMPLATES_DIR / "report" / "template.html"
    meta = parse_template_meta(tfile)
    assert meta["name"] == "report"
    assert "Multi section" in meta["description"]
    var_names = {v["name"] for v in meta["variables"]}
    assert "title" in var_names
    assert "sections" in var_names


def test_parse_template_meta_no_tags(tmp_path: Path):
    f = tmp_path / "plain.html"
    f.write_text("<html><body>no meta</body></html>")
    assert parse_template_meta(f) == {}


def test_resolve_template_bundled():
    tpath, manifest = resolve_template(name="report")
    assert tpath.name == "template.html"
    assert manifest["name"] == "report"


def test_resolve_template_not_found():
    with pytest.raises(FileNotFoundError):
        resolve_template(name="does-not-exist")


def test_resolve_template_html_direct(tmp_path: Path):
    f = tmp_path / "my.html"
    f.write_text(
        '<meta name="pdfgen:name" content="mytpl">'
        '<meta name="pdfgen:variable" content="title" data-required="true">'
        '<h1>{{ title }}</h1>'
    )
    tpath, manifest = resolve_template(html=f)
    assert tpath == f
    assert manifest["name"] == "mytpl"
    assert "title" in manifest["variables"]


def test_render_report_template(tmp_path: Path):
    tpath, manifest = resolve_template(name="report")
    data = {"title": "T", "author": "A", "sections": [{"heading": "H", "body": "B"}]}
    out = render_template(tpath, manifest, data, tmp_path / "out.html")
    text = out.read_text()
    assert "<h1>T</h1>" in text
    assert "H" in text


def test_discover_templates_finds_standalone(tmp_path: Path):
    f = tmp_path / "sub" / "custom.html"
    f.parent.mkdir()
    f.write_text(
        '<meta name="pdfgen:name" content="custom">'
        '<meta name="pdfgen:description" content="A standalone template">'
        '<h1>Hi</h1>'
    )
    found = discover_templates(tmp_path)
    names = [t["name"] for t in found]
    assert "custom" in names


def test_find_template_by_name(tmp_path: Path):
    f = tmp_path / "x.html"
    f.write_text('<meta name="pdfgen:name" content="xname"><h1>Hi</h1>')
    assert find_template_by_name("xname", root=tmp_path) == f


def test_load_data_json_yaml(tmp_path: Path):
    j = tmp_path / "d.json"; j.write_text(json.dumps({"a": 1}))
    y = tmp_path / "d.yaml"; y.write_text("a: 2\n")
    assert load_data(j) == {"a": 1}
    assert load_data(y) == {"a": 2}


def test_scaffold_template_updates_name(tmp_path: Path):
    p = scaffold_template("blank", tmp_path / "mytpl")
    assert (p / "template.html").exists()
    meta = parse_template_meta(p / "template.html")
    assert meta["name"] == "mytpl"


def test_sample_data_from_manifest():
    manifest = {
        "variables": {
            "title": {"type": "string", "required": True},
            "items": {"type": "array", "default": []},
            "name": {"type": "string", "default": "auto"},
        }
    }
    sample = _sample_data_from_manifest(manifest)
    assert sample["title"] == "sample"
    assert sample["items"] == []
    assert sample["name"] == "auto"
