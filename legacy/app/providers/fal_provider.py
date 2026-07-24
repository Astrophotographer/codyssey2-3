from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

import httpx

from app.config import Settings
from app.providers.base import EditRequest, EditResult, ImageProvider


class FalProvider(ImageProvider):
    """Fal-hosted Qwen-Image-Edit — closest to the original Aigraphers stack."""

    id = "fal"
    label = "Fal (Qwen)"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def is_configured(self) -> bool:
        return bool(self.settings.fal_key)

    def edit(self, req: EditRequest) -> EditResult:
        if not self.is_configured():
            raise RuntimeError("FAL_KEY 가 없습니다. https://fal.ai 에서 발급 후 .env 에 넣으세요.")

        model = (
            self.settings.fal_person_model
            if req.preset.category == "person"
            else self.settings.fal_landscape_model
        )
        prompt = req.preset.build_prompt(req.place)
        image_url = self._to_data_uri(req.image_path)

        payload: dict = {
            "prompt": prompt,
            "image_url": image_url,
            "num_inference_steps": req.preset.steps,
            "guidance_scale": req.preset.guidance,
            "enable_safety_checker": True,
        }
        if req.seed is not None:
            payload["seed"] = req.seed

        headers = {
            "Authorization": f"Key {self.settings.fal_key}",
            "Content-Type": "application/json",
        }

        # queue.fal.run is sync-ish; fal.run endpoint
        submit_url = f"https://fal.run/{model}"
        with httpx.Client(timeout=300.0) as client:
            res = client.post(submit_url, headers=headers, json=payload)
            if res.status_code >= 400:
                raise RuntimeError(f"Fal error {res.status_code}: {res.text[:800]}")
            data = res.json()

        out_url = self._extract_image_url(data)
        if not out_url:
            raise RuntimeError(f"Fal response missing image: {data}")

        with httpx.Client(timeout=120.0) as client:
            img = client.get(out_url)
            img.raise_for_status()
            req.output_path.write_bytes(img.content)

        return EditResult(
            output_path=req.output_path,
            meta={
                "provider": "fal",
                "model": model,
                "prompt": prompt,
                "seed": data.get("seed") or req.seed,
                "request_id": data.get("request_id"),
                "usage": {
                    "billing": "per_image",
                    "note": "Fal은 장당 과금 (토큰 단위 아님)",
                    "est_usd_per_image": 0.04,
                },
            },
        )

    @staticmethod
    def _to_data_uri(path: Path) -> str:
        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{b64}"

    @staticmethod
    def _extract_image_url(data: dict) -> str | None:
        images = data.get("images")
        if isinstance(images, list) and images:
            first = images[0]
            if isinstance(first, dict) and first.get("url"):
                return first["url"]
            if isinstance(first, str):
                return first
        image = data.get("image")
        if isinstance(image, dict) and image.get("url"):
            return image["url"]
        if isinstance(image, str):
            return image
        return data.get("url")
