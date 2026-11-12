from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from openpyxl import load_workbook
from pypdf import PdfReader


@dataclass(frozen=True)
class ExtractedPart:
    locator: str
    text: str


TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".json", ".yaml", ".yml", ".xml", ".html", ".htm", ".log"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | IMAGE_EXTENSIONS | {".pdf", ".docx", ".xlsx", ".csv", ".tsv", ".zip"}


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _clean(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def _chunk(locator: str, text: str, target: int = 3600, overlap: int = 320) -> list[ExtractedPart]:
    text = _clean(text)
    if not text:
        return []
    def line_locator(start: int, end: int) -> str:
        first = text.count("\n", 0, start) + 1
        last = text.count("\n", 0, end) + 1
        return f"{locator}, line {first}" if first == last else f"{locator}, lines {first}-{last}"

    if len(text) <= target:
        return [ExtractedPart(line_locator(0, len(text)), text)]
    result: list[ExtractedPart] = []
    start = 0
    part = 1
    while start < len(text):
        end = min(len(text), start + target)
        if end < len(text):
            boundary = max(text.rfind("\n", start, end), text.rfind(". ", start, end))
            if boundary > start + target // 2:
                end = boundary + 1
        result.append(ExtractedPart(f"{line_locator(start, end)}, chunk {part}", text[start:end].strip()))
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
        part += 1
    return result


def extract_bytes(filename: str, data: bytes, *, zip_depth: int = 0) -> list[ExtractedPart]:
    suffix = Path(filename).suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return []
    if suffix in TEXT_EXTENSIONS:
        return _chunk("text", _decode(data))
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        parts: list[ExtractedPart] = []
        for page_no, page in enumerate(reader.pages, start=1):
            parts.extend(_chunk(f"page {page_no}", page.extract_text() or ""))
        return parts
    if suffix == ".docx":
        document = Document(io.BytesIO(data))
        paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
        for table_no, table in enumerate(document.tables, start=1):
            paragraphs.append(f"[Table {table_no}]")
            paragraphs.extend(" | ".join(cell.text.strip() for cell in row.cells) for row in table.rows)
        return _chunk("document", "\n".join(paragraphs))
    if suffix == ".xlsx":
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        parts = []
        for sheet in workbook.worksheets:
            rows = []
            for row_no, values in enumerate(sheet.iter_rows(values_only=True), start=1):
                rendered = " | ".join("" if value is None else str(value) for value in values).strip(" |")
                if rendered:
                    rows.append(f"row {row_no}: {rendered}")
            parts.extend(_chunk(f"sheet {sheet.title}", "\n".join(rows)))
        return parts
    if suffix in {".csv", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else ","
        reader = csv.reader(io.StringIO(_decode(data)), delimiter=delimiter)
        rows = [f"row {number}: " + " | ".join(values) for number, values in enumerate(reader, start=1)]
        return _chunk("table", "\n".join(rows))
    if suffix == ".zip":
        if zip_depth >= 1:
            raise ValueError("Nested ZIP files are not supported.")
        parts = []
        total_uncompressed = 0
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            files = [info for info in archive.infolist() if not info.is_dir()]
            if len(files) > 100:
                raise ValueError("ZIP contains more than 100 files.")
            for info in files:
                member = Path(info.filename)
                if member.is_absolute() or ".." in member.parts:
                    raise ValueError(f"Unsafe ZIP path: {info.filename}")
                total_uncompressed += info.file_size
                if total_uncompressed > 100 * 1024 * 1024:
                    raise ValueError("ZIP expands beyond the 100 MB safety limit.")
                if member.suffix.lower() not in SUPPORTED_EXTENSIONS or member.suffix.lower() == ".zip":
                    continue
                nested = extract_bytes(member.name, archive.read(info), zip_depth=zip_depth + 1)
                parts.extend(ExtractedPart(f"{info.filename}: {part.locator}", part.text) for part in nested)
        return parts
    raise ValueError(f"Unsupported file type: {suffix or 'unknown'}")


def summarize_parts(parts: list[ExtractedPart]) -> dict[str, int]:
    return {"chunks": len(parts), "characters": sum(len(part.text) for part in parts)}

