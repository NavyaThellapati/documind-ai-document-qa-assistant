from dataclasses import dataclass

from app.core.config import get_settings
from app.services.embeddings import get_embedding_service
from app.services.text_processing import Chunk


@dataclass
class RetrievedChunk:
    text: str
    document_id: str
    document_name: str
    page_number: int | None
    chunk_number: int
    relevance_score: float | None


class VectorStoreService:
    def __init__(self) -> None:
        settings = get_settings()
        settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        import chromadb

        self.client = chromadb.PersistentClient(path=str(settings.chroma_dir))
        self.collection = self.client.get_or_create_collection(name="documind_chunks", metadata={"hnsw:space": "cosine"})
        self.embeddings = get_embedding_service()

    def upsert_document_chunks(self, user_id: str, document_id: str, document_name: str, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        ids = [f"{user_id}:{document_id}:{chunk.chunk_number}" for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        vectors = self.embeddings.embed(documents)
        metadatas = [
            {
                "user_id": user_id,
                "document_id": document_id,
                "document_name": document_name,
                "page_number": chunk.page_number or 0,
                "chunk_number": chunk.chunk_number,
            }
            for chunk in chunks
        ]
        self.collection.upsert(ids=ids, documents=documents, embeddings=vectors, metadatas=metadatas)

    def delete_document(self, user_id: str, document_id: str) -> None:
        self.collection.delete(where={"$and": [{"user_id": user_id}, {"document_id": document_id}]})

    def search(self, user_id: str, question: str, document_ids: list[str] | None = None, top_k: int | None = None) -> list[RetrievedChunk]:
        settings = get_settings()
        where: dict = {"user_id": user_id}
        if document_ids:
            where = {"$and": [{"user_id": user_id}, {"document_id": {"$in": document_ids}}]}
        result = self.collection.query(
            query_embeddings=self.embeddings.embed([question]),
            n_results=top_k or settings.retrieval_top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        retrieved: list[RetrievedChunk] = []
        for text, metadata, distance in zip(result.get("documents", [[]])[0], result.get("metadatas", [[]])[0], result.get("distances", [[]])[0]):
            retrieved.append(
                RetrievedChunk(
                    text=text,
                    document_id=metadata["document_id"],
                    document_name=metadata["document_name"],
                    page_number=metadata.get("page_number") or None,
                    chunk_number=int(metadata["chunk_number"]),
                    relevance_score=round(1 - float(distance), 4) if distance is not None else None,
                )
            )
        return retrieved


_vector_store: VectorStoreService | None = None


def get_vector_store() -> VectorStoreService:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService()
    return _vector_store
