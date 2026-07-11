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
    "application/octet-stream",
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


def validate_content_type(content_type: str | None, suffix: str) -> None:
    if not content_type:
        return
    normalized = content_type.split(";")[0].strip().lower()
    if normalized not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Unsupported MIME type. Please upload a PDF, TXT, or DOCX file.")
    expected = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    if normalized != "application/octet-stream" and expected.get(suffix) != normalized:
        raise ValueError("File extension and MIME type do not match.")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ensure_within_directory(base: Path, path: Path) -> Path:
    base_resolved = base.resolve()
    path_resolved = path.resolve()
    if base_resolved not in path_resolved.parents and path_resolved != base_resolved:
        raise ValueError("Invalid file path.")
    return path_resolved
