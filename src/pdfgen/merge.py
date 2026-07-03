"""PDF merge and outline (bookmark) helpers using pypdf.

merge_pdfs: concatenate PDFs in order.
add_outline: rebuild a hierarchical outline from a list of (title, page, level).
extract_outline: read existing outline as a flat list.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import Fit


@dataclass
class Bookmark:
    title: str
    page: int  # 0 indexed
    level: int = 0  # 0 = top level


def merge_pdfs(inputs: list[Path], output: Path) -> Path:
    """Concatenate PDFs in order. Returns output path."""
    if not inputs:
        raise ValueError("merge requires at least one input PDF")
    writer = PdfWriter()
    for p in inputs:
        reader = PdfReader(str(p))
        for page in reader.pages:
            writer.add_page(page)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "wb") as fh:
        writer.write(fh)
    return output


def add_outline(pdf_path: Path, bookmarks: list[Bookmark], output: Path | None = None) -> Path:
    """Add a hierarchical outline to a PDF. Returns output path (overwrites if same).

    Bookmarks are processed in the given order. Hierarchy is derived from `level`:
    a bookmark's parent is the most recent preceding bookmark with level - 1.
    """
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter(clone_from=reader)
    # Clear any existing outline.
    writer._root_object.pop("/Outlines", None)

    # parents[i] holds the outline item ref for the most recent bookmark at level i.
    parents: dict[int, any] = {}  # type: ignore[valid-type]
    for bm in bookmarks:
        parent = parents.get(bm.level - 1) if bm.level > 0 else None
        item = writer.add_outline_item(
            title=bm.title,
            page_number=bm.page,
            parent=parent,
            fit=Fit.fit(),
        )
        parents[bm.level] = item
        # Invalidate any deeper levels so they don't get reused incorrectly.
        for deeper in list(parents):
            if deeper > bm.level:
                del parents[deeper]

    out = output or pdf_path
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as fh:
        writer.write(fh)
    return out


def extract_outline(pdf_path: Path) -> list[Bookmark]:
    """Read existing outline as a flat list of Bookmark."""
    reader = PdfReader(str(pdf_path))
    out: list[Bookmark] = []

    def walk(items, level: int = 0) -> None:
        for it in items:
            if isinstance(it, list):
                walk(it, level + 1)
            else:
                try:
                    page = reader.get_destination_page_number(it)
                except Exception:
                    page = 0
                out.append(Bookmark(title=str(it.title), page=page, level=level))

    try:
        walk(reader.outline)
    except Exception:
        pass
    return out
