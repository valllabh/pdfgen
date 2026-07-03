"""Unit tests for pure (non browser) modules. Browser tests are marked slow."""
import json
from pathlib import Path

import pytest

from pdfgen.templating import BUNDLED_TEMPLATES_DIR, load_data, render_template, resolve_template_dir
from pdfgen.scaffold import scaffold_project, scaffold_template


def test_bundled_templates_present():
    names = {p.name for p in BUNDLED_TEMPLATES_DIR.iterdir() if p.is_dir()}
    assert {"report", "letter", "invoice", "blank"} <= names


def test_resolve_template_dir():
    d = resolve_template_dir(name="report")
    assert (d / "template.html").exists()
    with pytest.raises(FileNotFoundError):
        resolve_template_dir(name="does-not-exist")


def test_render_report_template(tmp_path: Path):
    tdir = resolve_template_dir(name="report")
    data = {"title": "T", "author": "A", "sections": [{"heading": "H", "body": "B"}]}
    out = render_template(tdir, data, tmp_path / "out.html")
    text = out.read_text()
    assert "<h1>T</h1>" in text
    assert "H" in text


def test_load_data_json_yaml(tmp_path: Path):
    j = tmp_path / "d.json"; j.write_text(json.dumps({"a": 1}))
    y = tmp_path / "d.yaml"; y.write_text("a: 2\n")
    assert load_data(j) == {"a": 1}
    assert load_data(y) == {"a": 2}


def test_scaffold_project(tmp_path: Path):
    p = scaffold_project(tmp_path / "proj", name="demo")
    assert (p / "template.html").exists()
    assert (p / "data.json").exists()
    assert (p / "manifest.json").exists()


def test_scaffold_template(tmp_path: Path):
    p = scaffold_template("blank", tmp_path / "copy")
    assert (p / "template.html").exists()
