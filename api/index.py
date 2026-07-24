from __future__ import annotations

import base64
import sys
import tempfile
import time
from pathlib import Path

# Vercel loads api/index.py as a function entry; ensure project root is importable.
_ROOT = Path(__file__).resolve().parent.parent
_API = Path(__file__).resolve().parent
for _p in (_ROOT, _API):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

try:
    from api.ai_providers import EditRequest, get_provider, list_providers
    from api.config import get_settings
    from api.presets_data import category_dicts, get_preset, preset_dicts
except ImportError:
    from ai_providers import EditRequest, get_provider, list_providers
    from config import get_settings
    from presets_data import category_dicts, get_preset, preset_dicts

app = FastAPI(title="Aigraphers", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = get_settings()

# Fallback when Vercel routes all traffic through FastAPI (framework autodetection).
_STATIC_ROOT = _ROOT / "public" if (_ROOT / "public" / "index.html").exists() else _ROOT


@app.get("/")
def index_page() -> FileResponse:
    return FileResponse(_STATIC_ROOT / "index.html")


@app.get("/api/health")
def health() -> dict:
    providers = list_providers(settings)
    return {
        "ok": True,
        "default_provider": settings.default_provider,
        "providers": providers,
    }


@app.get("/api/providers")
def providers() -> dict:
    return {
        "default": settings.default_provider,
        "providers": list_providers(settings),
    }


@app.get("/api/presets")
def presets(category: str | None = None) -> dict:
    if category and category not in {"person", "landscape"}:
        raise HTTPException(status_code=400, detail="category must be person or landscape")
    return {
        "categories": category_dicts(),
        "presets": preset_dicts(category),
    }


@app.post("/api/transform")
async def transform(
    image: UploadFile = File(...),
    style_id: str = Form(...),
    provider: str | None = Form(None),
    place: str | None = Form(None),
    seed: str | None = Form(None),
) -> dict:
    preset = get_preset(style_id)
    if not preset:
        raise HTTPException(status_code=400, detail=f"Unknown style_id: {style_id}")

    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty image")
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Max upload {settings.max_upload_mb}MB",
        )

    content_type = (image.content_type or "").lower()
    name = image.filename or "upload.jpg"
    if content_type and not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="JPEG / PNG / WebP only")

    seed_val: int | None = None
    if seed is not None and str(seed).strip() != "":
        try:
            seed_val = int(seed)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="seed must be an integer") from exc

    provider_id = (provider or settings.default_provider).strip().lower()
    try:
        engine = get_provider(provider_id, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not engine.is_configured():
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{provider_id}' is not configured (missing API key)",
        )

    suffix = Path(name).suffix.lower() or ".jpg"
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"

    started = time.time()
    try:
        with tempfile.TemporaryDirectory(prefix="aigraphers-") as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / f"input{suffix}"
            output_path = tmp_path / "output.png"
            input_path.write_bytes(raw)

            result = engine.edit(
                EditRequest(
                    image_path=input_path,
                    output_path=output_path,
                    preset=preset,
                    place=(place or "").strip() or None,
                    seed=seed_val,
                )
            )
            out_bytes = result.output_path.read_bytes()
            meta = result.meta
            usage = meta.get("usage") if isinstance(meta, dict) else {}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — surface provider errors to client
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    elapsed = round(time.time() - started, 1)
    return {
        "ok": True,
        "image_base64": base64.b64encode(out_bytes).decode("ascii"),
        "mime": "image/png",
        "usage": usage or {},
        "meta": meta,
        "elapsed_sec": elapsed,
        "provider": provider_id,
        "style_id": style_id,
    }


def _safe_static(subdir: str, filename: str) -> FileResponse:
    base = (_STATIC_ROOT / subdir).resolve()
    path = (base / filename).resolve()
    if not str(path).startswith(str(base)) or not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path)


@app.get("/css/{filename}")
def css_file(filename: str) -> FileResponse:
    return _safe_static("css", filename)


@app.get("/js/{filename}")
def js_file(filename: str) -> FileResponse:
    return _safe_static("js", filename)


@app.get("/images/{filename}")
def images_file(filename: str) -> FileResponse:
    return _safe_static("images", filename)
