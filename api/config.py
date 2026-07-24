from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


@dataclass(frozen=True)
class Settings:
    max_upload_mb: int = 12
    default_provider: str = "local"

    local_worker_url: str = ""
    local_worker_token: str = ""

    openai_api_key: str = ""
    openai_image_model: str = "gpt-image-1"
    openai_base_url: str = "https://api.openai.com/v1"

    fal_key: str = ""
    fal_person_model: str = "fal-ai/qwen-image-edit-2511"
    fal_landscape_model: str = "fal-ai/qwen-image-edit-2509"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings(
        max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "12")),
        default_provider=os.getenv("DEFAULT_PROVIDER", "local").lower(),
        local_worker_url=os.getenv("LOCAL_WORKER_URL", "").rstrip("/"),
        local_worker_token=os.getenv("LOCAL_WORKER_TOKEN", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_image_model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1"),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        fal_key=os.getenv("FAL_KEY", ""),
        fal_person_model=os.getenv("FAL_PERSON_MODEL", "fal-ai/qwen-image-edit-2511"),
        fal_landscape_model=os.getenv("FAL_LANDSCAPE_MODEL", "fal-ai/qwen-image-edit-2509"),
    )
