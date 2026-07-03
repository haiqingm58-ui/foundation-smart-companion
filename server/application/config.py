from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
SERVER_DIR = ROOT_DIR / "server"


@dataclass(frozen=True)
class Settings:
    database_url: str
    secret_key: str
    data_dir: Path
    upload_dir: Path
    session_ttl_seconds: int
    captcha_ttl_seconds: int
    cookie_secure: bool
    llm_api_url: str
    llm_api_key: str
    llm_model: str


def load_settings() -> Settings:
    data_dir = Path(os.getenv("FOUNDATION_DATA_DIR", SERVER_DIR / "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    upload_dir = Path(os.getenv("FOUNDATION_UPLOAD_DIR", data_dir / "uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)
    database_url = os.getenv("FOUNDATION_DATABASE_URL", f"sqlite:///{data_dir / 'platform.db'}")
    return Settings(
        database_url=database_url,
        secret_key=os.getenv("FOUNDATION_SECRET_KEY", "development-only-change-me"),
        data_dir=data_dir,
        upload_dir=upload_dir,
        session_ttl_seconds=int(os.getenv("FOUNDATION_SESSION_TTL_SECONDS", str(60 * 60 * 12))),
        captcha_ttl_seconds=int(os.getenv("FOUNDATION_CAPTCHA_TTL_SECONDS", "120")),
        cookie_secure=os.getenv("FOUNDATION_COOKIE_SECURE", "false").lower() == "true",
        llm_api_url=os.getenv("FOUNDATION_LLM_API_URL", "").strip(),
        llm_api_key=os.getenv("FOUNDATION_LLM_API_KEY", "").strip(),
        llm_model=os.getenv("FOUNDATION_LLM_MODEL", "gpt-4o-mini").strip(),
    )
