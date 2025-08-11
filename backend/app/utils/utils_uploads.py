# backend/app/utils_uploads.py
from pathlib import Path
from uuid import uuid4
from werkzeug.utils import secure_filename
from flask import abort

# Extensiones permitidas (minimiza superficie)
ALLOWED_EXTS = {".pdf", ".docx", ".xlsx", ".csv"}

# Opcional: si instalas python-magic (mejor validación de tipo real)
import magic
def sniff_mime(file_bytes: bytes) -> str:
    return magic.from_buffer(file_bytes, mime=True) or ""

def ensure_allowed_and_name(file_storage, allowed_exts=ALLOWED_EXTS) -> tuple[str, bytes]:
    """Valida que exista archivo, que tenga extensión permitida y devuelve (nombre_nuevo, bytes)."""
    if not file_storage or not file_storage.filename:
        abort(400, "Archivo requerido")

    original = secure_filename(file_storage.filename)
    ext = Path(original).suffix.lower()
    if ext not in allowed_exts:
        abort(400, f"Extensión no permitida: {ext}")

    # Lee el contenido en memoria (si el tamaño lo permite; Flask aplica MAX_CONTENT_LENGTH)
    data = file_storage.read()
    
    mime = sniff_mime(data)
    if ext == ".pdf" and mime != "application/pdf": abort(400, "Tipo de archivo PDF inválido")
    if ext == ".csv" and mime not in {"text/csv", "application/vnd.ms-excel"}: abort(400, "CSV inválido")
    if ext == ".xlsx" and mime not in {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}: abort(400, "XLSX inválido")
    if ext == ".docx" and mime not in {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}: abort(400, "DOCX inválido")

    new_name = f"{uuid4().hex}{ext}"  # evita colisiones y traversal por nombre
    return new_name, data

def save_bytes(base_dir: Path, name: str, data: bytes) -> str:
    base_dir = Path(base_dir).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / name
    path.write_bytes(data)
    return str(path)
