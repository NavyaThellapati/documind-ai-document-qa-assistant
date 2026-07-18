import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Document, DocumentInsight
from app.services.text_processing import Chunk, TextSection, clean_text, extract_text_sections, split_sections

MISSING_LLM_NOTICE = "AI summarization requires an LLM API key. Showing an extractive document overview generated only from the uploaded text."

RESUME_HEADINGS = {
    "professional summary",
    "summary",
    "skills",
    "technical skills",
    "experience",
    "professional experience",
    "projects",
    "education",
    "certifications",
    "certificates",
}

TECH_TERMS = [
    "Python",
    "FastAPI",
    "React",
    "TypeScript",
    "JavaScript",
    "PostgreSQL",
    "SQLAlchemy",
    "Docker",
    "AWS",
    "Azure",
    "OpenAI",
    "LangChain",
    "ChromaDB",
    "Sentence-Transformers",
    "Machine Learning",
    "RAG",
    "REST",
    "API",
    "GitHub Actions",
    "Pytest",
]


def _sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", clean_text(text)) if len(sentence.strip()) > 20]


def _bullets(text: str) -> list[str]:
    bullets = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^[-*•]\s+", stripped):
            bullets.append(re.sub(r"^[-*•]\s+", "", stripped))
    return bullets


def _detect_sections(sections: list[TextSection]) -> list[str]:
    found: list[str] = []
    for section in sections:
        for line in section.text.splitlines():
            candidate = line.strip().strip(":")
            normalized = candidate.lower()
            looks_like_heading = 2 <= len(candidate) <= 60 and (
                normalized in RESUME_HEADINGS
                or candidate.isupper()
                or bool(re.match(r"^[A-Z][A-Za-z/& ]+$", candidate))
            )
            if looks_like_heading and candidate not in found:
                found.append(candidate)
    return found[:10]


def _document_kind(text: str, filename: str) -> str:
    lowered = f"{filename}\n{text}".lower()
    if any(term in lowered for term in ["resume", "professional experience", "technical skills", "certifications"]):
        return "resume"
    if any(term in lowered for term in ["policy", "handbook", "compliance", "procedure"]):
        return "policy"
    if any(term in lowered for term in ["user guide", "installation", "troubleshooting", "faq"]):
        return "guide"
    return "document"


def _key_entities(text: str) -> list[str]:
    entities: list[str] = []
    for term in TECH_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE) and term not in entities:
            entities.append(term)
    for match in re.findall(r"\b(?:19|20)\d{2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{4}\b", text):
        if match not in entities:
            entities.append(match)
    for match in re.findall(r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z&]+){1,3}\b", text):
        if match not in entities and len(match) <= 50:
            entities.append(match)
    return entities[:18]


def _suggested_questions(kind: str, sections: list[str], entities: list[str], filename: str) -> list[str]:
    lowered_sections = {section.lower() for section in sections}
    questions: list[str] = []
    if kind == "resume":
        questions.extend([
            "What backend technologies does this candidate use?",
            "Summarize the candidate's professional experience.",
            "What AI projects are listed?",
            "What are the strongest skills in this resume?",
            "What education and certifications are included?",
        ])
    elif kind == "policy":
        questions.extend([
            "What are the most important policy requirements?",
            "Who is affected by this policy?",
            "What actions are required for compliance?",
            "What dates or deadlines are mentioned?",
        ])
    elif kind == "guide":
        questions.extend([
            "What problem does this guide help solve?",
            "What setup steps are required?",
            "What troubleshooting advice is included?",
            "What features are explained?",
        ])
    if "experience" in lowered_sections or "professional experience" in lowered_sections:
        questions.append("Which roles and responsibilities are described in the experience section?")
    if entities:
        questions.append(f"What does the document say about {entities[0]}?")
    questions.append(f"What should I know first about {filename}?")
    deduped = []
    for question in questions:
        if question not in deduped:
            deduped.append(question)
    return deduped[:6]


def _source_refs(chunks: list[Chunk]) -> list[dict]:
    refs = []
    for chunk in chunks[:4]:
        refs.append({
            "page_number": chunk.page_number,
            "chunk_number": chunk.chunk_number,
            "excerpt": chunk.text[:280],
        })
    return refs


def build_document_insight(document: Document, sections: list[TextSection], chunks: list[Chunk]) -> dict:
    full_text = "\n\n".join(section.text for section in sections if section.text.strip())
    kind = _document_kind(full_text, document.original_filename)
    detected_sections = _detect_sections(sections)
    sentences = _sentences(full_text)
    bullets = _bullets(full_text)
    entities = _key_entities(full_text)
    page_count = document.page_count or len({section.page_number for section in sections if section.page_number}) or None

    if kind == "resume":
        overview = "This appears to be a resume or professional profile. It focuses on the candidate's skills, experience, projects, education, and credentials."
    elif kind == "policy":
        overview = "This appears to be a policy or handbook document. It explains rules, expectations, procedures, or guidance for a specific audience."
    elif kind == "guide":
        overview = "This appears to be a guide or FAQ. It is mainly intended to help readers understand features, setup steps, or troubleshooting guidance."
    else:
        overview = "This document contains extracted text that DocuMind can search, summarize, and answer questions about."
    if page_count:
        overview += f" It contains about {page_count} page{'s' if page_count != 1 else ''}."

    summary_parts = sentences[:2] or [chunks[0].text if chunks else "No readable summary text was found."]
    summary = " ".join(summary_parts)[:1200]
    key_points = (bullets[:6] + [sentence for sentence in sentences if sentence not in summary_parts])[:6]
    if not key_points:
        key_points = summary_parts[:4]

    return {
        "status": "ready",
        "overview": overview,
        "summary": summary,
        "key_points": key_points,
        "main_sections": detected_sections,
        "key_entities": entities,
        "suggested_questions": _suggested_questions(kind, detected_sections, entities, document.original_filename),
        "sources": _source_refs(chunks),
        "notice": None if get_settings().openai_api_key or get_settings().llm_provider.lower() == "llama" else MISSING_LLM_NOTICE,
        "llm_configured": bool(get_settings().openai_api_key or get_settings().llm_provider.lower() == "llama"),
    }


def get_or_create_document_insight(db: Session, document: Document, force: bool = False) -> DocumentInsight:
    if document.status not in {"ready", "processed"}:
        raise ValueError("Document must be processed before it can be explained.")
    if document.insight and not force:
        return document.insight

    sections = extract_text_sections(Path(document.file_path), Path(document.original_filename).suffix.lower())
    settings = get_settings()
    chunks = split_sections(sections, settings.chunk_size, settings.chunk_overlap)
    payload = build_document_insight(document, sections, chunks)
    insight = document.insight or DocumentInsight(document_id=document.id)
    for key, value in payload.items():
        setattr(insight, key, value)
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return insight
