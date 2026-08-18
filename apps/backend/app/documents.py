from io import BytesIO
from pathlib import Path
from docx import Document as DocxDocument
from pypdf import PdfReader

ALLOWED = {"application/pdf", "text/plain", "text/markdown", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
MAX_SIZE = 15 * 1024 * 1024


def extract_text(data: bytes, content_type: str) -> str:
    if content_type == "application/pdf":
        return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(data)).pages)
    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return "\n".join(p.text for p in DocxDocument(BytesIO(data)).paragraphs)
    return data.decode("utf-8", errors="replace")


def safe_name(filename: str) -> str:
    return "".join(c for c in Path(filename).name if c.isalnum() or c in "._-") or "documento"
