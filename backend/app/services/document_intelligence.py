import re
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Document, DocumentInsight
from app.services.text_processing import Chunk, TextSection, clean_text, extract_text_sections, split_sections

SummaryLength = Literal["brief", "standard", "detailed"]

MISSING_LLM_NOTICE = "Basic summary generated without an LLM. Add an OpenAI API key or configure Llama for richer abstractive summaries."

SUMMARY_PROMPT = """You are a document summarization assistant.

Summarize the supplied document in your own words.

Rules:
- Do not reproduce the document.
- Do not copy long passages.
- Do not list every detail.
- Remove repetition.
- Focus on purpose, main ideas, conclusions, obligations, findings, or actions.
- Keep the summary under the specified word limit.
- Use only information contained in the document.
- If information is unclear, say so rather than guessing."""

SUMMARY_WORD_LIMITS: dict[SummaryLength, tuple[int, int]] = {
    "brief": (50, 80),
    "standard": (120, 200),
    "detailed": (250, 400),
}

SECTION_KEYWORDS: dict[str, list[str]] = {
    "resume": ["summary", "skills", "experience", "projects", "education", "certifications"],
    "research paper": ["abstract", "objective", "method", "findings", "results", "conclusion"],
    "contract": ["parties", "agreement", "obligations", "payment", "deadline", "termination", "liability"],
    "policy": ["purpose", "policy", "scope", "responsibilities", "exceptions", "compliance"],
    "invoice": ["invoice", "vendor", "customer", "total", "due date", "payment"],
    "medical report": ["patient", "findings", "diagnosis", "assessment", "recommendations"],
    "technical document": ["overview", "architecture", "components", "setup", "api", "troubleshooting"],
    "meeting notes": ["attendees", "decisions", "action items", "owners", "deadlines"],
}

TECH_TERMS = [
    "Python", "FastAPI", "React", "TypeScript", "JavaScript", "PostgreSQL", "SQLAlchemy", "Docker",
    "AWS", "Azure", "OpenAI", "LangChain", "ChromaDB", "Sentence-Transformers", "Machine Learning",
    "RAG", "REST", "API", "GitHub Actions", "Pytest",
]

STOPWORDS = {
    "about", "after", "also", "and", "are", "because", "been", "but", "can", "for", "from", "has",
    "have", "into", "its", "more", "must", "not", "only", "that", "the", "their", "this", "with",
    "will", "within", "without", "users", "document",
}


class SummarySection(BaseModel):
    title: str
    description: str


class SummaryEntity(BaseModel):
    name: str
    type: str


class StructuredDocumentSummary(BaseModel):
    document_type: str
    overview: str = Field(max_length=320)
    summary: str
    key_points: list[str] = Field(min_length=1, max_length=7)
    sections: list[SummarySection] = Field(default_factory=list)
    entities: list[SummaryEntity] = Field(default_factory=list)
    suggested_questions: list[str] = Field(min_length=1, max_length=6)

    @field_validator("overview")
    @classmethod
    def overview_word_limit(cls, value: str) -> str:
        if len(value.split()) > 40:
            return _limit_words(value, 40)
        return value


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9+-]*", text.lower())


def _limit_words(text: str, limit: int) -> str:
    words = text.split()
    if len(words) <= limit:
        return text.strip()
    return " ".join(words[:limit]).rstrip(" ,;:.") + "."


def _sentences(text: str) -> list[str]:
    normalized = clean_text(text)
    parts = re.split(r"(?<=[.!?])\s+|\n+", normalized)
    return [part.strip(" -•\t") for part in parts if len(part.strip()) > 25]


def _fingerprint(text: str) -> set[str]:
    return {word for word in _words(text) if len(word) > 3 and word not in STOPWORDS}


def _similarity(left: str, right: str) -> float:
    left_terms = _fingerprint(left)
    right_terms = _fingerprint(right)
    if not left_terms or not right_terms:
        return 0.0
    return len(left_terms & right_terms) / len(left_terms | right_terms)


def _dedupe_sentences(sentences: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for sentence in sentences:
        compact = re.sub(r"\s+", " ", sentence).strip()
        key = compact.lower()
        if key in seen or any(_similarity(compact, existing) > 0.72 for existing in deduped):
            continue
        seen.add(key)
        deduped.append(compact)
    return deduped


def _infer_document_type(text: str, filename: str) -> str:
    lowered = f"{filename}\n{text}".lower()
    signals = {
        "resume": ["resume", "professional summary", "technical skills", "experience", "education"],
        "research paper": ["abstract", "methodology", "findings", "references", "hypothesis"],
        "contract": ["agreement", "party", "parties", "obligations", "termination", "governing law"],
        "policy": ["policy", "handbook", "compliance", "responsibilities", "exceptions"],
        "invoice": ["invoice", "vendor", "customer", "amount due", "total", "due date"],
        "medical report": ["patient", "diagnosis", "findings", "treatment", "recommendations"],
        "technical document": ["architecture", "api", "setup", "configuration", "deployment", "components", "user guide", "troubleshooting"],
        "meeting notes": ["meeting", "attendees", "decisions", "action items", "owner", "deadline"],
    }
    scores = {kind: sum(1 for signal in kind_signals if signal in lowered) for kind, kind_signals in signals.items()}
    best, score = max(scores.items(), key=lambda item: item[1])
    return best if score else "document"


def _keywords(text: str, limit: int = 12) -> list[str]:
    counts = Counter(word for word in _words(text) if len(word) > 3 and word not in STOPWORDS)
    return [word for word, _ in counts.most_common(limit)]


def _rank_sentences(sentences: list[str], document_type: str, keywords: list[str]) -> list[str]:
    type_terms = set(SECTION_KEYWORDS.get(document_type, []))
    keyword_set = set(keywords)
    scored = []
    for index, sentence in enumerate(sentences):
        terms = set(_words(sentence))
        score = len(terms & keyword_set) * 2 + len(terms & type_terms) * 3
        if re.search(r"\b(must|required|deadline|total|result|finding|skill|project|decision|action)\b", sentence, re.I):
            score += 3
        score += max(0, 3 - index / 20)
        scored.append((score, -index, sentence))
    scored.sort(reverse=True)
    return [sentence for _, _, sentence in scored]


def _logical_groups(sentences: list[str], size: int = 12) -> list[list[str]]:
    return [sentences[index:index + size] for index in range(0, len(sentences), size)]


def _group_summaries(sentences: list[str], document_type: str, keywords: list[str]) -> list[str]:
    summaries = []
    for group in _logical_groups(sentences):
        ranked = _rank_sentences(group, document_type, keywords)
        summaries.extend(ranked[:2])
    return _dedupe_sentences(summaries)


def _synthesize_summary(sentences: list[str], document_type: str, summary_length: SummaryLength) -> str:
    _, max_words = SUMMARY_WORD_LIMITS[summary_length]
    keywords = _keywords(" ".join(sentences))
    intermediate = _group_summaries(sentences, document_type, keywords)
    ranked = _rank_sentences(intermediate, document_type, keywords)
    selected: list[str] = []
    for sentence in _dedupe_sentences(ranked):
        candidate = " ".join(selected + [sentence])
        if len(candidate.split()) > max_words:
            continue
        selected.append(sentence)
        if len(" ".join(selected).split()) >= max_words * 0.7:
            break
    if not selected and ranked:
        selected = [_limit_words(ranked[0], max_words)]
    return " ".join(selected)


def _overview(document_type: str, summary: str) -> str:
    lead = _limit_words(summary, 26)
    if document_type == "resume":
        prefix = "Resume covering"
    elif document_type == "policy":
        prefix = "Policy document outlining"
    elif document_type == "invoice":
        prefix = "Invoice summarizing"
    elif document_type == "contract":
        prefix = "Contract describing"
    elif document_type == "meeting notes":
        prefix = "Meeting notes capturing"
    elif document_type == "technical document":
        prefix = "Technical document explaining"
    elif document_type == "research paper":
        prefix = "Research paper summarizing"
    elif document_type == "medical report":
        prefix = "Medical report documenting"
    else:
        prefix = "Document summarizing"
    return _limit_words(f"{prefix} {lead[0].lower() + lead[1:] if lead else 'the main information in the upload.'}", 40)


def _extract_sections(sections: list[TextSection], sentences: list[str], document_type: str) -> list[SummarySection]:
    found: list[str] = []
    known = SECTION_KEYWORDS.get(document_type, [])
    for section in sections:
        lines = [line.strip().strip(":") for line in section.text.splitlines()]
        for line in lines:
            normalized = line.lower()
            if 2 <= len(line) <= 70 and (normalized in known or line.isupper() or bool(re.match(r"^[A-Z][A-Za-z0-9/& ]+$", line))):
                if line not in found:
                    found.append(line)
    if not found:
        found = [term.title() for term in known[:5]]
    output = []
    for title in found[:8]:
        related = next((sentence for sentence in sentences if title.lower().split()[0] in sentence.lower()), "")
        output.append(SummarySection(title=title, description=_limit_words(related or f"Covers {title.lower()} information found in the document.", 18)))
    return output


def _append_entity(entities: list[SummaryEntity], name: str, entity_type: str) -> None:
    if not any(entity.name.lower() == name.lower() for entity in entities):
        entities.append(SummaryEntity(name=name, type=entity_type))


def _key_entities(text: str) -> list[SummaryEntity]:
    entities: list[SummaryEntity] = []
    for term in TECH_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE):
            _append_entity(entities, term, "technology")
    for match in re.findall(r"\b(?:19|20)\d{2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{4}\b", text):
        _append_entity(entities, match, "date")
    for match in re.findall(r"\$\s?\d[\d,]*(?:\.\d{2})?|\b\d[\d,]*(?:\.\d{2})?\s?(?:USD|dollars)\b", text, flags=re.IGNORECASE):
        _append_entity(entities, match, "amount")
    for match in re.findall(r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z&]+){1,3}\b", text):
        if len(match) <= 50:
            _append_entity(entities, match, "topic")
    return entities[:18]


def _key_points(sentences: list[str], document_type: str, summary: str) -> list[str]:
    ranked = _rank_sentences(sentences, document_type, _keywords(summary))
    points = []
    for sentence in _dedupe_sentences(ranked):
        if _similarity(sentence, summary) > 0.88:
            continue
        points.append(_limit_words(sentence, 24))
        if len(points) == 7:
            break
    return points[:7] or [_limit_words(summary, 24)]


def _suggested_questions(document_type: str, sections: list[SummarySection], entities: list[SummaryEntity], filename: str) -> list[str]:
    questions_by_type = {
        "resume": [
            "What backend technologies does this candidate use?",
            "Summarize the candidate's professional experience.",
            "What AI projects are listed?",
            "What are the strongest skills in this resume?",
            "What education and certifications are included?",
        ],
        "research paper": ["What objective does the paper study?", "What method is used?", "What findings are reported?", "What conclusion does the paper reach?"],
        "contract": ["Who are the parties?", "What obligations are listed?", "What deadlines or payment terms matter?", "What risks or termination terms are included?"],
        "policy": ["What is the purpose of this policy?", "Who is responsible for following it?", "What rules or exceptions are listed?", "What actions are required?"],
        "invoice": ["Who is the vendor?", "Who is the customer?", "What total or due date is listed?", "What line items are included?"],
        "medical report": ["What findings are documented?", "What diagnosis or assessment is included?", "What recommendations are listed?", "What dates or follow-ups matter?"],
        "technical document": ["What architecture is described?", "What setup steps are required?", "What components or APIs are documented?", "What troubleshooting guidance is included?"],
        "meeting notes": ["What decisions were made?", "What action items are assigned?", "Who owns each follow-up?", "What deadlines are mentioned?"],
    }
    questions = list(questions_by_type.get(document_type, []))
    if sections:
        questions.append(f"What does the {sections[0].title} section say?")
    if entities:
        questions.append(f"What does the document say about {entities[0].name}?")
    questions.append(f"What should I know first about {filename}?")
    deduped = []
    for question in questions:
        if question not in deduped:
            deduped.append(question)
    return deduped[:6]


def _source_refs(chunks: list[Chunk]) -> list[dict]:
    return [{"page_number": chunk.page_number, "chunk_number": chunk.chunk_number, "excerpt": _limit_words(chunk.text, 35)} for chunk in chunks[:4]]


def build_document_insight(document: Document, sections: list[TextSection], chunks: list[Chunk], summary_length: SummaryLength = "standard") -> dict:
    full_text = "\n\n".join(section.text for section in sections if section.text.strip())
    sentences = _dedupe_sentences(_sentences(full_text))
    document_type = _infer_document_type(full_text, document.original_filename)
    summary = _synthesize_summary(sentences, document_type, summary_length)
    overview = _overview(document_type, summary)
    section_models = _extract_sections(sections, sentences, document_type)
    entities = _key_entities(full_text)
    structured = StructuredDocumentSummary(
        document_type=document_type,
        overview=overview,
        summary=summary,
        key_points=_key_points(sentences, document_type, summary)[:7],
        sections=section_models,
        entities=entities,
        suggested_questions=_suggested_questions(document_type, section_models, entities, document.original_filename),
    )

    return {
        "summary_length": summary_length,
        "document_type": structured.document_type,
        "status": "ready",
        "overview": structured.overview,
        "summary": structured.summary,
        "key_points": structured.key_points,
        "main_sections": [section.model_dump() for section in structured.sections],
        "key_entities": [entity.model_dump() for entity in structured.entities],
        "suggested_questions": structured.suggested_questions,
        "sources": _source_refs(chunks),
        "notice": None if get_settings().openai_api_key or get_settings().llm_provider.lower() == "llama" else MISSING_LLM_NOTICE,
        "llm_configured": bool(get_settings().openai_api_key or get_settings().llm_provider.lower() == "llama"),
    }


def normalize_summary_length(summary_length: str | None) -> SummaryLength:
    value = (summary_length or "standard").lower()
    if value not in SUMMARY_WORD_LIMITS:
        raise ValueError("Summary length must be brief, standard, or detailed.")
    return value  # type: ignore[return-value]


def get_or_create_document_insight(db: Session, document: Document, force: bool = False, summary_length: str | None = None) -> DocumentInsight:
    if document.status not in {"ready", "processed"}:
        raise ValueError("Document must be processed before it can be explained.")
    length = normalize_summary_length(summary_length)
    existing = next((insight for insight in document.insights if insight.summary_length == length), None)
    if existing and not force:
        return existing

    sections = extract_text_sections(Path(document.file_path), Path(document.original_filename).suffix.lower())
    settings = get_settings()
    chunks = split_sections(sections, settings.chunk_size, settings.chunk_overlap)
    payload = build_document_insight(document, sections, chunks, length)
    insight = existing or DocumentInsight(document_id=document.id, summary_length=length)
    for key, value in payload.items():
        setattr(insight, key, value)
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return insight
