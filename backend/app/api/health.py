import shutil

from fastapi import APIRouter
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from fastapi import Depends

from app.core.config import get_settings
from app.core.database import get_db
from app.services.vector_store import get_vector_store

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    settings = get_settings()
    required_tables = {"users", "documents", "conversations", "messages", "sources", "feedback", "refresh_tokens"}
    checks = {
        "database": {"status": "unknown"},
        "chroma": {"status": "unknown"},
        "openai": {"status": "not_configured"},
        "disk": {"status": "unknown"},
    }
    try:
        db.execute(text("SELECT 1"))
        tables = set(inspect(db.bind).get_table_names()) if db.bind is not None else set()
        missing_tables = sorted(required_tables - tables)
        if missing_tables:
            checks["database"] = {
                "status": "error",
                "detail": "Database is reachable but migrations have not been applied. Run `alembic upgrade head`.",
                "missing_tables": missing_tables,
            }
        else:
            checks["database"] = {"status": "ok"}
    except Exception as exc:
        checks["database"] = {"status": "error", "detail": str(exc)}
    try:
        collection = get_vector_store().collection
        checks["chroma"] = {"status": "ok", "collection": collection.name, "count": collection.count()}
    except Exception as exc:
        checks["chroma"] = {"status": "error", "detail": str(exc)}
    if settings.openai_api_key:
        checks["openai"] = {"status": "configured"}
    usage = shutil.disk_usage(".")
    checks["disk"] = {
        "status": "ok",
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
    }
    overall = "ok" if all(value["status"] in {"ok", "configured", "not_configured"} for value in checks.values()) else "degraded"
    return {
        "status": overall,
        "app": settings.app_name,
        "version": "1.0.0",
        "environment": settings.environment,
        "checks": checks,
    }
