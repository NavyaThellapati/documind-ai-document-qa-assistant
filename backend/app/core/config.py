from functools import lru_cache
from pathlib import Path
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DocuMind API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://documind:documind@localhost:5432/documind"
    jwt_secret: str = Field(default="change-me-in-production", min_length=16)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    refresh_token_expire_days: int = 14
    openai_api_key: str | None = None
    llama_base_url: str = "http://localhost:11434"
    llm_provider: str = "openai"
    openai_model: str = "gpt-4o-mini"
    llama_model: str = "llama3"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 900
    chunk_overlap: int = 120
    retrieval_top_k: int = 5
    max_upload_size_mb: int = 15
    upload_dir: Path = Path("uploads")
    chroma_dir: Path = Path("chroma_data")
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    auth_rate_limit_per_minute: int = 10
    chat_rate_limit_per_minute: int = 20
    llm_timeout_seconds: int = 30
    min_relevance_score: float = 0.05

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.environment.lower() == "production" and self.jwt_secret == "change-me-in-production":
            raise ValueError("JWT_SECRET must be set to a strong unique value in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
