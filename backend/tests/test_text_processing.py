from app.services.embeddings import EmbeddingService
from app.services.text_processing import TextSection, clean_text, split_sections


def test_clean_text_and_chunking():
    text = clean_text("Hello     world\n\n\nPolicy sentence. " * 80)
    chunks = split_sections([TextSection(text=text, page_number=2)], chunk_size=220, chunk_overlap=30)
    assert chunks
    assert chunks[0].page_number == 2
    assert chunks[0].chunk_number == 1
    assert "Hello world" in chunks[0].text


def test_chunk_boundaries_do_not_split_words():
    text = " ".join(f"word{index:04d}" for index in range(180))
    chunks = split_sections([TextSection(text=text, page_number=1)], chunk_size=180, chunk_overlap=35)

    assert len(chunks) > 1

    cleaned = clean_text(text)
    search_from = 0
    for chunk in chunks:
        offset = cleaned.find(chunk.text, max(0, search_from - 60))
        assert offset >= 0
        end = offset + len(chunk.text)
        assert offset == 0 or not (cleaned[offset - 1].isalnum() and chunk.text[0].isalnum())
        assert end == len(cleaned) or not (chunk.text[-1].isalnum() and cleaned[end].isalnum())
        search_from = end


def test_chunking_preserves_paragraphs_and_bullets():
    text = "Overview paragraph.\n\n- First responsibility\n- Second responsibility\n\nClosing paragraph."
    chunks = split_sections([TextSection(text=text, page_number=3)], chunk_size=500, chunk_overlap=40)

    assert chunks[0].text == text


def test_chunk_overlap_prefers_sentence_starts():
    text = " ".join(
        [
            "First complete sentence explains the policy purpose.",
            "Second complete sentence describes who must follow the policy.",
            "Third complete sentence lists approval and review actions.",
        ]
        * 16
    )
    chunks = split_sections([TextSection(text=text, page_number=1)], chunk_size=190, chunk_overlap=70)

    assert len(chunks) > 1
    for chunk in chunks[1:]:
        assert chunk.text[0].isalnum()
        assert not chunk.text.startswith((",", ";", "and ", "or "))


def test_hashing_embedding_mode_is_deterministic():
    service = EmbeddingService("hashing")

    first = service.embed(["Remote work policy"])[0]
    second = service.embed(["Remote work policy"])[0]

    assert len(first) == 384
    assert first == second
    assert any(value != 0 for value in first)
