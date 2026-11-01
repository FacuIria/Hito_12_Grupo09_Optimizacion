"""Identificación del código realmente desplegado, sin recopilar secretos."""
import hashlib
import importlib.metadata
import platform
from pathlib import Path


def text_hash(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def build_info():
    package = Path(__file__).resolve().parent
    return {
        "python": platform.python_version(),
        "packages": {p: importlib.metadata.version(p) for p in
                     ("fastapi", "uvicorn", "pydantic", "httpx", "httpcore")},
        "app_files_sha256": {p.name: text_hash(p) for p in sorted(package.glob("*.py"))},
        "requirements_sha256": text_hash(package.parent / "requirements-lock.txt"),
    }
