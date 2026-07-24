from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    host: str = "0.0.0.0"
    port: int = 8781
    data_dir: Path = ROOT / "data" / "jobs"
    max_upload_mb: int = 12
    default_provider: str = "local"

    # Local: HTTP worker (기존 GPU 서버) or optional in-process stub
    local_worker_url: str = ""
    local_worker_token: str = ""
    local_demo_mode: bool = False  # PIL soft filter when no GPU (dev only)

    # OpenAI Images API
    openai_api_key: str = ""
    openai_image_model: str = "gpt-image-1"
    openai_base_url: str = "https://api.openai.com/v1"

    # Fal — Qwen Image Edit (recommended cloud)
    fal_key: str = ""
    fal_person_model: str = "fal-ai/qwen-image-edit-2511"
    fal_landscape_model: str = "fal-ai/qwen-image-edit-2509"

    # Simple cookie-session login
    auth_user: str = ""
    auth_pass: str = ""
    session_secret: str = ""

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    secret = os.getenv("SESSION_SECRET", "").strip()
    if not secret:
        secret = secrets.token_hex(32)
    return Settings(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8781")),
        data_dir=Path(os.getenv("DATA_DIR", str(ROOT / "data" / "jobs"))),
        max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "12")),
        default_provider=os.getenv("DEFAULT_PROVIDER", "local").lower(),
        local_worker_url=os.getenv("LOCAL_WORKER_URL", "").rstrip("/"),
        local_worker_token=os.getenv("LOCAL_WORKER_TOKEN", ""),
        local_demo_mode=os.getenv("LOCAL_DEMO_MODE", "0") in {"1", "true", "True", "yes"},
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_image_model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1"),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        fal_key=os.getenv("FAL_KEY", ""),
        fal_person_model=os.getenv("FAL_PERSON_MODEL", "fal-ai/qwen-image-edit-2511"),
        fal_landscape_model=os.getenv("FAL_LANDSCAPE_MODEL", "fal-ai/qwen-image-edit-2509"),
        auth_user=os.getenv("AUTH_USER", "").strip(),
        auth_pass=os.getenv("AUTH_PASS", "").strip(),
        session_secret=secret,
    )
