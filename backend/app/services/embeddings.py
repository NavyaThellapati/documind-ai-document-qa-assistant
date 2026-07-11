import hashlib
import math
from functools import lru_cache

from app.core.config import get_settings


class EmbeddingService:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or get_settings().embedding_model
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            vectors = self._load_model().encode(texts, normalize_embeddings=True)
            return [list(map(float, vector)) for vector in vectors]
        except Exception:
            return [self._fallback_embedding(text) for text in texts]

    def _fallback_embedding(self, text: str, dims: int = 384) -> list[float]:
        vector = [0.0] * dims
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:2], "big") % dims
            sign = 1.0 if digest[2] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
