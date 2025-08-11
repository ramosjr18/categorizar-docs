# backend/app/utils_fs.py
from pathlib import Path
from werkzeug.utils import safe_join  # OJO: utils, no security
from flask import abort

def ensure_dir(p: Path) -> Path:
    p = Path(p).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p

def safe_path(base_dir: Path, name: str) -> str:
    """
    Devuelve una ruta segura dentro de base_dir o 404 si es inválida.
    """
    joined = safe_join(str(Path(base_dir).resolve()), name)
    if joined is None:
        abort(404)
    return joined
