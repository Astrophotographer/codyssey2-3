from __future__ import annotations

import io
from pathlib import Path

import httpx
from PIL import Image, ImageEnhance, ImageFilter

from app.config import Settings
from app.providers.base import EditRequest, EditResult, ImageProvider


class LocalProvider(ImageProvider):
    """Local GPU via HTTP worker, or demo PIL fallback for UI testing."""

    id = "local"
    label = "로컬 GPU"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def is_configured(self) -> bool:
        # Always selectable: real GPU worker when URL is set, otherwise demo filter.
        return True

    def uses_demo(self) -> bool:
        return not bool(self.settings.local_worker_url)

    def edit(self, req: EditRequest) -> EditResult:
        if self.settings.local_worker_url:
            return self._via_worker(req)
        # Demo fallback when no worker (LOCAL_DEMO_MODE optional; always available)
        return self._demo_filter(req)

    def _via_worker(self, req: EditRequest) -> EditResult:
        url = f"{self.settings.local_worker_url}/edit"
        headers = {}
        if self.settings.local_worker_token:
            headers["Authorization"] = f"Bearer {self.settings.local_worker_token}"

        data = {
            "style_id": req.preset.id,
            "prompt": req.preset.build_prompt(req.place),
            "engine": req.preset.engine,
            "steps": str(req.preset.steps),
            "guidance": str(req.preset.guidance),
        }
        if req.seed is not None:
            data["seed"] = str(req.seed)
        if req.place:
            data["place"] = req.place

        with req.image_path.open("rb") as f:
            files = {"image": (req.image_path.name, f, "application/octet-stream")}
            with httpx.Client(timeout=600.0) as client:
                res = client.post(url, data=data, files=files, headers=headers)
                res.raise_for_status()
                content_type = res.headers.get("content-type", "")
                if "application/json" in content_type:
                    payload = res.json()
                    out_url = payload.get("output_url") or payload.get("url")
                    if not out_url:
                        raise RuntimeError(f"Worker JSON missing output: {payload}")
                    img = client.get(out_url, timeout=120.0)
                    img.raise_for_status()
                    req.output_path.write_bytes(img.content)
                return EditResult(
                        output_path=req.output_path,
                        meta={
                            "provider": "local",
                            "mode": "http",
                            "worker": payload,
                            "usage": {"billing": "local", "total_tokens": 0, "note": "로컬 · 토큰 소모 없음"},
                        },
                    )
                req.output_path.write_bytes(res.content)
                return EditResult(
                    output_path=req.output_path,
                    meta={
                        "provider": "local",
                        "mode": "http",
                        "bytes": len(res.content),
                        "usage": {"billing": "local", "total_tokens": 0, "note": "로컬 · 토큰 소모 없음"},
                    },
                )

    def _demo_filter(self, req: EditRequest) -> EditResult:
        """Lightweight stand-in so UI works without GPU/API keys."""
        img = Image.open(req.image_path).convert("RGB")
        style = req.preset.id
        if style in {"business_suit", "studio_headshot", "resume_id"}:
            img = ImageEnhance.Contrast(img).enhance(1.15)
            img = ImageEnhance.Color(img).enhance(0.92)
            img = ImageEnhance.Sharpness(img).enhance(1.2)
        elif style in {"outdoor_natural", "lighting_fix"}:
            img = ImageEnhance.Brightness(img).enhance(1.12)
            img = ImageEnhance.Color(img).enhance(1.1)
        elif style == "upscale_sharp":
            img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
            img = ImageEnhance.Sharpness(img).enhance(1.6)
        elif style in {"pixel_character", "anime_character_grid", "pixel_game"}:
            small = img.resize((max(64, img.width // 12), max(64, img.height // 12)), Image.Resampling.BILINEAR)
            img = small.resize(img.size, Image.Resampling.NEAREST)
            img = ImageEnhance.Color(img).enhance(1.4)
        elif style in {"lego_diorama", "mini_figure"}:
            img = ImageEnhance.Color(img).enhance(1.35)
            img = ImageEnhance.Contrast(img).enhance(1.2)
            img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
        elif style in {"warm_handdrawn", "origami_world"}:
            img = ImageEnhance.Color(img).enhance(1.25)
            img = ImageEnhance.Brightness(img).enhance(1.05)
            img = img.filter(ImageFilter.SMOOTH_MORE)
        else:
            img = ImageEnhance.Color(img).enhance(1.2)
            img = ImageEnhance.Contrast(img).enhance(1.1)

        req.output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(req.output_path, format="PNG")
        return EditResult(
            output_path=req.output_path,
            meta={
                "provider": "local",
                "mode": "demo",
                "note": "LOCAL_DEMO_MODE — real Qwen output needs LOCAL_WORKER_URL or fal/openai",
                "usage": {"billing": "local", "total_tokens": 0, "note": "로컬 · 토큰 소모 없음"},
            },
        )
