"""Environment-based configuration for the offline-first demo."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv() -> None:
    """Load a small .env file without making python-dotenv a runtime requirement."""
    env_file = BASE_DIR / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _env_bool(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    demo_mode: bool
    tavily_api_key: str
    database_path: Path
    rag_backend: str


def get_settings() -> Settings:
    _load_dotenv()
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    database_path = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "citizen_schemes.sqlite3")))
    if not database_path.is_absolute():
        database_path = BASE_DIR / database_path
    return Settings(
        base_dir=BASE_DIR,
        demo_mode=_env_bool("DEMO_MODE", True),
        tavily_api_key=api_key,
        database_path=database_path,
        rag_backend=os.getenv("RAG_BACKEND", "local").strip().lower(),
    )
