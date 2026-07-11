import hashlib
import re
from pathlib import Path
from uuid import uuid4

SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def sanitize_filename(filename: str) -> str:
    stem = Path(filename).stem[:80] or "document"
    suffix = Path(filename).suffix.lower()
    safe_stem = SAFE_NAME_RE.sub("_", stem).strip("._") or "document"
    return f"{safe_stem}_{uuid4().hex[:10]}{suffix}"


def validate_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file type. Please upload a PDF, TXT, or DOCX file.")
    return suffix


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ensure_within_directory(base: Path, path: Path) -> Path:
    base_resolved = base.resolve()
    path_resolved = path.resolve()
    if base_resolved not in path_resolved.parents and path_resolved != base_resolved:
        raise ValueError("Invalid file path.")
    return path_resolved
