import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_documind.db"
os.environ["JWT_SECRET"] = "test-secret-key-with-enough-length"
os.environ["UPLOAD_DIR"] = "test_uploads"
os.environ["CHROMA_DIR"] = "test_chroma"

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app


class FakeVectorStore:
    def __init__(self) -> None:
        self.docs: dict[tuple[str, str], list] = {}

    def upsert_document_chunks(self, user_id, document_id, document_name, chunks):
        self.docs[(user_id, document_id)] = [(document_name, chunk) for chunk in chunks]

    def delete_document(self, user_id, document_id):
        self.docs.pop((user_id, document_id), None)

    def search(self, user_id, question, document_ids=None, top_k=5):
        from app.services.vector_store import RetrievedChunk

        results = []
        for (stored_user, doc_id), chunks in self.docs.items():
            if stored_user != user_id or (document_ids and doc_id not in document_ids):
                continue
            for document_name, chunk in chunks:
                results.append(
                    RetrievedChunk(
                        text=chunk.text,
                        document_id=doc_id,
                        document_name=document_name,
                        page_number=chunk.page_number,
                        chunk_number=chunk.chunk_number,
                        relevance_score=0.91,
                    )
                )
        return results[:top_k]


class FakeLLM:
    async def answer(self, question, chunks):
        if not chunks or "unknown" in question.lower():
            return "I could not find that answer in the uploaded documents."
        return f"{chunks[0].text[:120]} [1]"


@pytest.fixture(autouse=True)
def reset_db(monkeypatch):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    fake_store = FakeVectorStore()
    monkeypatch.setattr("app.services.documents.get_vector_store", lambda: fake_store)
    monkeypatch.setattr("app.api.chat.get_vector_store", lambda: fake_store)
    monkeypatch.setattr("app.api.chat.get_llm_service", lambda: FakeLLM())
    yield
    Base.metadata.drop_all(bind=engine)
    for folder in (Path("test_uploads"), Path("test_chroma")):
        if folder.exists():
            for child in sorted(folder.rglob("*"), reverse=True):
                if child.is_file():
                    child.unlink()
                elif child.is_dir():
                    child.rmdir()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    response = client.post("/api/auth/register", json={"email": "user@example.com", "password": "strongpass123", "full_name": "Test User"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
