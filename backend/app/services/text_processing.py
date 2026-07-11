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


def estimate_page_count(sections: list[TextSection]) -> int | None:
    page_numbers = [section.page_number for section in sections if section.page_number]
    if page_numbers:
        return max(page_numbers)
    total_chars = sum(len(section.text) for section in sections)
    if total_chars == 0:
        return None
    return max(1, round(total_chars / 2400))


def search_sections(sections: list[TextSection], query: str, max_results: int = 8) -> list[tuple[int | None, str]]:
    terms = [term.lower() for term in query.split() if len(term) > 2]
    if not terms:
        return []
    matches: list[tuple[int, int | None, str]] = []
    for section in sections:
        lowered = section.text.lower()
        score = sum(lowered.count(term) for term in terms)
        if score == 0:
            continue
        first_index = min((lowered.find(term) for term in terms if term in lowered), default=0)
        start = max(0, first_index - 120)
        end = min(len(section.text), first_index + 380)
        excerpt = clean_text(section.text[start:end])
        matches.append((score, section.page_number, excerpt))
    matches.sort(reverse=True, key=lambda item: item[0])
    return [(page, excerpt) for _, page, excerpt in matches[:max_results]]


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
