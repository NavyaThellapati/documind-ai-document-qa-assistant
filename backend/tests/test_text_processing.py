from app.services.text_processing import TextSection, clean_text, split_sections


def test_clean_text_and_chunking():
    text = clean_text("Hello     world\n\n\nPolicy sentence. " * 80)
    chunks = split_sections([TextSection(text=text, page_number=2)], chunk_size=220, chunk_overlap=30)
    assert chunks
    assert chunks[0].page_number == 2
    assert chunks[0].chunk_number == 1
    assert "Hello world" in chunks[0].text
