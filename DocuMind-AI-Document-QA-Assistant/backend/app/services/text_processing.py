import re
from dataclasses import dataclass
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader
from pypdf.errors import PdfReadError


@dataclass
class TextSection:
    text: str
    page_number: int | None = None


@dataclass
class Chunk:
    text: str
    page_number: int | None
    chunk_number: int


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_sections(path: Path, suffix: str) -> list[TextSection]:
    try:
        if suffix == ".txt":
            return [TextSection(clean_text(path.read_text(encoding="utf-8", errors="ignore")), None)]
        if suffix == ".pdf":
            reader = PdfReader(str(path))
            sections = []
            for index, page in enumerate(reader.pages, start=1):
                sections.append(TextSection(clean_text(page.extract_text() or ""), index))
            return sections
        if suffix == ".docx":
            doc = DocxDocument(str(path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return [TextSection(clean_text("\n".join(paragraphs)), None)]
    except (PdfReadError, OSError, ValueError) as exc:
        raise ValueError("The file could not be read. It may be corrupted or password protected.") from exc
    raise ValueError("Unsupported file type.")


def split_sections(sections: list[TextSection], chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    if chunk_overlap >= chunk_size:
        raise ValueError("Chunk overlap must be smaller than chunk size.")
    chunks: list[Chunk] = []
    chunk_number = 1
    for section in sections:
        text = clean_text(section.text)
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            if end < len(text):
                boundary = max(text.rfind("\n", start, end), text.rfind(". ", start, end), text.rfind(" ", start, end))
                if boundary > start + max(120, chunk_size // 3):
                    end = boundary + 1
            chunk_text = clean_text(text[start:end])
            if chunk_text:
                chunks.append(Chunk(text=chunk_text, page_number=section.page_number, chunk_number=chunk_number))
                chunk_number += 1
            if end >= len(text):
                break
            start = max(0, end - chunk_overlap)
    return chunks
