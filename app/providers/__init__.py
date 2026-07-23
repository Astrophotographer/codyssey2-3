from __future__ import annotations

from app.config import Settings
from app.providers.base import ImageProvider
from app.providers.fal_provider import FalProvider
from app.providers.local import LocalProvider
from app.providers.openai_provider import OpenAIProvider


def get_provider(name: str, settings: Settings) -> ImageProvider:
    key = (name or settings.default_provider).strip().lower()
    if key == "openai":
        return OpenAIProvider(settings)
    if key == "fal":
        return FalProvider(settings)
    if key == "local":
        return LocalProvider(settings)
    raise ValueError(f"Unknown provider: {name}. Use local | openai | fal")


def list_providers(settings: Settings) -> list[dict]:
    local = LocalProvider(settings)
    local_demo = local.uses_demo()
    return [
        {
            "id": "local",
            "name": "로컬 GPU",
            "description": (
                "데모 PIL 필터 (GPU 워커 없음)"
                if local_demo
                else "기존처럼 로컬 Qwen / HTTP 워커로 변환"
            ),
            "ready": local.is_configured(),
            "recommended_for": "비용 없음 · 기존 머신 재사용",
            "billing": "local",
            "cost_hint": (
                "데모 · 로컬 무료"
                if local_demo
                else "토큰 없음 · GPU 워커 · 무료"
            ),
            "mode": "demo" if local_demo else "worker",
        },
        {
            "id": "fal",
            "name": "Fal (Qwen)",
            "description": "지금 쓰는 Qwen-Image-Edit와 동일 계열 · 추천",
            "ready": FalProvider(settings).is_configured(),
            "recommended_for": "퀄리티·가격 균형 · Aigraphers와 가장 비슷",
            "billing": "per_image",
            "cost_hint": "약 $0.03–0.05 / 장 (토큰 단위 아님)",
            "est_usd_per_image": 0.04,
        },
        {
            "id": "openai",
            "name": "OpenAI",
            "description": "gpt-image 편집 API",
            "ready": OpenAIProvider(settings).is_configured(),
            "recommended_for": "지시 따르기·상용 안정성",
            "billing": "tokens",
            "cost_hint": "입력·출력 토큰 + 대략 비용 표시 (gpt-image-1 기준)",
        },
    ]
