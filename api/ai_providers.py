from __future__ import annotations

import base64
import io
import mimetypes
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import httpx
from PIL import Image, ImageEnhance, ImageFilter

try:
    from api.config import Settings, get_settings
    from api.presets_data import Preset
except ImportError:
    from config import Settings, get_settings
    from presets_data import Preset


def _friendly_fal_error(status_code: int, body: str) -> str:
    text = (body or "")[:800]
    low = text.lower()
    if status_code in {402, 403} and (
        "exhausted balance" in low or "user is locked" in low or "insufficient" in low
    ):
        return (
            "Fal 잔액이 소진되었거나 계정이 잠겼습니다. "
            "fal.ai/dashboard/billing 에서 충전하거나 OpenAI / Local API로 전환하세요."
        )
    if status_code == 401:
        return "Fal API 키가 유효하지 않습니다. Vercel의 FAL_KEY를 확인하세요."
    return f"Fal error {status_code}: {text}"


@dataclass
class EditRequest:
    image_path: Path
    output_path: Path
    preset: Preset
    place: str | None = None
    seed: int | None = None


@dataclass
class EditResult:
    output_path: Path
    meta: dict


class ImageProvider(ABC):
    id: str
    label: str

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    def edit(self, req: EditRequest) -> EditResult:
        ...


class LocalProvider(ImageProvider):
    id = "local"
    label = "로컬 GPU"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def is_configured(self) -> bool:
        return True

    def uses_demo(self) -> bool:
        return not bool(self.settings.local_worker_url)

    def edit(self, req: EditRequest) -> EditResult:
        if self.settings.local_worker_url:
            return self._via_worker(req)
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
                            "usage": {
                                "billing": "local",
                                "total_tokens": 0,
                                "note": "로컬 · 토큰 소모 없음",
                            },
                        },
                    )
                req.output_path.write_bytes(res.content)
                return EditResult(
                    output_path=req.output_path,
                    meta={
                        "provider": "local",
                        "mode": "http",
                        "bytes": len(res.content),
                        "usage": {
                            "billing": "local",
                            "total_tokens": 0,
                            "note": "로컬 · 토큰 소모 없음",
                        },
                    },
                )

    def _demo_filter(self, req: EditRequest) -> EditResult:
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
            small = img.resize(
                (max(64, img.width // 12), max(64, img.height // 12)),
                Image.Resampling.BILINEAR,
            )
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
                "note": "LOCAL_DEMO — real Qwen needs LOCAL_WORKER_URL or fal/openai",
                "usage": {
                    "billing": "local",
                    "total_tokens": 0,
                    "note": "로컬 · 토큰 소모 없음",
                },
            },
        )


class FalProvider(ImageProvider):
    id = "fal"
    label = "Fal (Qwen)"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def is_configured(self) -> bool:
        return bool(self.settings.fal_key)

    def edit(self, req: EditRequest) -> EditResult:
        if not self.is_configured():
            raise RuntimeError("FAL_KEY 가 없습니다. Vercel 환경 변수에 설정하세요.")

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

        submit_url = f"https://fal.run/{model}"
        with httpx.Client(timeout=300.0) as client:
            res = client.post(submit_url, headers=headers, json=payload)
            if res.status_code >= 400:
                raise RuntimeError(_friendly_fal_error(res.status_code, res.text))
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


class OpenAIProvider(ImageProvider):
    id = "openai"
    label = "OpenAI"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def is_configured(self) -> bool:
        return bool(self.settings.openai_api_key)

    def edit(self, req: EditRequest) -> EditResult:
        if not self.is_configured():
            raise RuntimeError("OPENAI_API_KEY 가 없습니다. Vercel 환경 변수에 설정하세요.")

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


def get_provider(name: str, settings: Settings | None = None) -> ImageProvider:
    settings = settings or get_settings()
    key = (name or settings.default_provider).strip().lower()
    if key == "openai":
        return OpenAIProvider(settings)
    if key == "fal":
        return FalProvider(settings)
    if key == "local":
        return LocalProvider(settings)
    raise ValueError(f"Unknown provider: {name}. Use local | openai | fal")


def list_providers(settings: Settings | None = None) -> list[dict]:
    settings = settings or get_settings()
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
                "데모 · 로컬 무료" if local_demo else "토큰 없음 · GPU 워커 · 무료"
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
