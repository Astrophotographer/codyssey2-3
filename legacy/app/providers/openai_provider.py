from __future__ import annotations

import base64
import io
from pathlib import Path

import httpx
from PIL import Image

from app.config import Settings
from app.providers.base import EditRequest, EditResult, ImageProvider


class OpenAIProvider(ImageProvider):
    id = "openai"
    label = "OpenAI"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def is_configured(self) -> bool:
        return bool(self.settings.openai_api_key)

    def edit(self, req: EditRequest) -> EditResult:
        if not self.is_configured():
            raise RuntimeError("OPENAI_API_KEY 가 없습니다. .env 에 설정하세요.")

        prompt = req.preset.build_prompt(req.place)
        url = f"{self.settings.openai_base_url}/images/edits"
        headers = {"Authorization": f"Bearer {self.settings.openai_api_key}"}

        image_bytes, filename = self._as_png_bytes(req.image_path)
        data = {
            "model": self.settings.openai_image_model,
            "prompt": prompt,
            "n": "1",
            "size": "auto",
            "quality": "high",
        }
        files = {"image": (filename, image_bytes, "image/png")}

        with httpx.Client(timeout=300.0) as client:
            res = client.post(url, headers=headers, data=data, files=files)
            if res.status_code >= 400:
                raise RuntimeError(f"OpenAI error {res.status_code}: {res.text[:800]}")
            payload = res.json()

        item = (payload.get("data") or [None])[0] or {}
        b64 = item.get("b64_json")
        out_url = item.get("url")

        if b64:
            req.output_path.write_bytes(base64.b64decode(b64))
        elif out_url:
            with httpx.Client(timeout=120.0) as client:
                img = client.get(out_url)
                img.raise_for_status()
                req.output_path.write_bytes(img.content)
        else:
            raise RuntimeError(f"OpenAI response missing image: {payload}")

        return EditResult(
            output_path=req.output_path,
            meta={
                "provider": "openai",
                "model": self.settings.openai_image_model,
                "prompt": prompt,
                "usage": self._extract_usage(payload),
            },
        )

    @staticmethod
    def _extract_usage(payload: dict) -> dict:
        usage = payload.get("usage") or {}
        if not isinstance(usage, dict):
            return {}
        details = usage.get("input_tokens_details") or {}
        out: dict = {
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "total_tokens": usage.get("total_tokens"),
        }
        if isinstance(details, dict):
            out["text_tokens"] = details.get("text_tokens")
            out["image_tokens"] = details.get("image_tokens")
        out = {k: v for k, v in out.items() if v is not None}
        est = OpenAIProvider._estimate_usd(out)
        if est is not None:
            out["est_usd"] = round(est, 4)
            out["est_usd_note"] = "대략치 (gpt-image-1 기준)"
        return out

    @staticmethod
    def _estimate_usd(usage: dict) -> float | None:
        """Rough USD estimate for gpt-image-1 style token billing."""
        # Official-ish rates per 1M tokens
        text_in = 5.0
        image_in = 10.0
        image_out = 40.0

        text_tokens = usage.get("text_tokens")
        image_tokens = usage.get("image_tokens")
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens") or 0

        if text_tokens is None and image_tokens is None and input_tokens is None:
            return None

        if text_tokens is not None or image_tokens is not None:
            tin = float(text_tokens or 0)
            iin = float(image_tokens or 0)
        else:
            # No breakdown: treat input as image input (edits are image-heavy)
            tin = 0.0
            iin = float(input_tokens or 0)

        cost = (tin / 1_000_000.0) * text_in
        cost += (iin / 1_000_000.0) * image_in
        cost += (float(output_tokens) / 1_000_000.0) * image_out
        return cost

    @staticmethod
    def _as_png_bytes(path: Path) -> tuple[bytes, str]:
        if path.suffix.lower() == ".png":
            return path.read_bytes(), path.name
        img = Image.open(path).convert("RGBA")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue(), path.stem + ".png"
