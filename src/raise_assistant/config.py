from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


APP_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(APP_ROOT / ".env")


def _path_env(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default)).expanduser()
    return value if value.is_absolute() else APP_ROOT / value


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    app_root: Path = APP_ROOT
    host: str = os.getenv("RAISE_HOST", "127.0.0.1")
    port: int = _int_env("RAISE_PORT", 8765)
    data_dir: Path = _path_env("RAISE_DATA_DIR", "./data")
    max_upload_mb: int = _int_env("RAISE_MAX_UPLOAD_MB", 30)
    max_output_tokens: int = _int_env("RAISE_MAX_OUTPUT_TOKENS", 100000)
    retrieval_limit: int = _int_env("RAISE_RETRIEVAL_LIMIT", 12)

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.5")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    google_cloud_project: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    vertex_location: str = os.getenv("VERTEX_LOCATION", "global")
    vertex_gemini_model: str = os.getenv("VERTEX_GEMINI_MODEL", "gemini-3.8-flash")
    vertex_claude_model: str = os.getenv("VERTEX_CLAUDE_MODEL", "claude-opus-4-8")
    vertex_claude_location: str = os.getenv("VERTEX_CLAUDE_LOCATION", "global")

    @property
    def database_path(self) -> Path:
        return self.data_dir / "raise.db"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def exports_dir(self) -> Path:
        return self.app_root / "exports"

    def prepare_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()

