from __future__ import annotations

import base64
import os
import platform
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# Vercel loads api/index.py as a function entry; ensure project root is importable.
_ROOT = Path(__file__).resolve().parent.parent
_API = Path(__file__).resolve().parent
for _p in (_ROOT, _API):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from api.ai_providers import EditRequest, get_provider, list_providers
    from api.config import get_settings
    from api.presets_data import category_dicts, get_preset, preset_dicts
except ImportError:
    from ai_providers import EditRequest, get_provider, list_providers
    from config import get_settings
    from presets_data import category_dicts, get_preset, preset_dicts

app = FastAPI(title="Aigraphers", version="0.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = get_settings()

# Fallback when Vercel routes all traffic through FastAPI (framework autodetection).
_STATIC_ROOT = _ROOT / "public" if (_ROOT / "public" / "index.html").exists() else _ROOT


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _environment_info() -> dict[str, str | None]:
    return {
        "runtime": "vercel" if os.getenv("VERCEL") else "local",
        "vercel_env": os.getenv("VERCEL_ENV"),
        "vercel_region": os.getenv("VERCEL_REGION"),
        "python": platform.python_version(),
    }


def _server_temp_c() -> float | None:
    raw = (settings.server_temp_c or "").strip()
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    thermal_root = Path("/sys/class/thermal")
    if thermal_root.is_dir():
        for path in sorted(thermal_root.glob("thermal_zone*/temp")):
            try:
                millideg = int(path.read_text().strip())
                return millideg / 1000.0
            except (OSError, ValueError):
                continue
    return None


def _usage_field(usage: dict[str, Any], key: str) -> Any:
    val = usage.get(key)
    return val if val is not None else None


async def _emit_run_log(
    *,
    elapsed_sec: float | None,
    result: str,
    error: str | None,
    style_id: str | None,
    provider: str | None,
    usage: dict[str, Any] | None,
) -> None:
    """Await webhooks in-request — Vercel kills daemon threads after the response."""
    url = (settings.n8n_runlog_webhook_url or "").strip()
    if not url:
        return

    usage_obj = usage if isinstance(usage, dict) else {}
    run_id = uuid.uuid4().hex[:12]
    ts = _utc_now_iso()
    env = _environment_info()

    run_log_payload: dict[str, Any] = {
        "type": "run_log",
        "elapsed_sec": elapsed_sec,
        "result": result,
        "error": error,
        "style_id": style_id,
        "provider": provider,
        "environment": env,
        "ts": ts,
        "total_tokens": _usage_field(usage_obj, "total_tokens"),
        "input_tokens": _usage_field(usage_obj, "input_tokens"),
        "output_tokens": _usage_field(usage_obj, "output_tokens"),
        "est_usd": _usage_field(usage_obj, "est_usd"),
        "usage": usage_obj,
        "run_id": run_id,
    }

    server_temp_payload: dict[str, Any] = {
        "type": "server_temp",
        "ts": ts,
        "server_temp_c": _server_temp_c(),
        "environment": env,
        "run_id": run_id,
        "result": result,
        "provider": provider,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json=run_log_payload)
            await client.post(url, json=server_temp_payload)
    except Exception:  # noqa: BLE001 — logging must never break the API
        pass


class ContactBody(BaseModel):
    name: str = ""
    email: str = ""
    message: str = ""
    rating: int | None = Field(default=None, ge=1, le=5)


class VisitBody(BaseModel):
    path: str = "/"
    referrer: str = ""
    theme: str = "clay"


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


@app.get("/api/config")
def public_config() -> dict:
    """Public config — no webhook URLs or secrets."""
    return {
        "google_form_url": settings.google_form_url or "",
        "features": {
            "contact": bool(settings.n8n_contact_webhook_url),
            "runlog": bool(settings.n8n_runlog_webhook_url),
            "visit": bool(settings.n8n_visit_webhook_url),
        },
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


@app.post("/api/contact")
async def contact(body: ContactBody) -> dict:
    name = (body.name or "").strip()
    message = (body.message or "").strip()
    email = (body.email or "").strip()
    if not name or not message:
        raise HTTPException(
            status_code=400,
            detail="이름과 문의 내용을 입력해 주세요",
        )

    payload = {
        "type": "contact",
        "name": name,
        "email": email,
        "message": message,
        "rating": body.rating,
        "ts": _utc_now_iso(),
        "environment": _environment_info(),
    }

    forwarded = False
    if settings.n8n_contact_webhook_url:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(settings.n8n_contact_webhook_url, json=payload)
                resp.raise_for_status()
            forwarded = True
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=502,
                detail="문의 전달에 실패했습니다. 잠시 후 다시 시도해 주세요.",
            ) from exc

    out: dict[str, Any] = {"ok": True, "forwarded": forwarded}
    if settings.google_form_url:
        out["google_form_url"] = settings.google_form_url
    return out


@app.post("/api/visit")
async def visit(body: VisitBody) -> dict:
    session_id = str(uuid.uuid4())
    payload = {
        "type": "visit",
        "path": (body.path or "/").strip() or "/",
        "referrer": (body.referrer or "").strip(),
        "theme": (body.theme or "clay").strip() or "clay",
        "session_id": session_id,
        "ts": _utc_now_iso(),
        "environment": _environment_info(),
    }
    if settings.n8n_visit_webhook_url:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(settings.n8n_visit_webhook_url, json=payload)
        except Exception:  # noqa: BLE001 — visit tracking must not block UX
            pass
    return {"ok": True, "session_id": session_id}


@app.post("/api/transform")
async def transform(
    image: UploadFile = File(...),
    style_id: str = Form(...),
    provider: str | None = Form(None),
    place: str | None = Form(None),
    seed: str | None = Form(None),
) -> dict:
    started = time.time()
    provider_id = (provider or settings.default_provider).strip().lower()
    run_result = "error"
    run_error: str | None = None
    elapsed: float | None = None
    usage: dict = {}

    try:
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
                raw_usage = meta.get("usage") if isinstance(meta, dict) else {}
                usage = raw_usage if isinstance(raw_usage, dict) else {}
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001 — surface provider errors to client
            msg = str(exc)
            status = 502 if msg.startswith("Fal ") or "Fal " in msg else 500
            low = msg.lower()
            if "잔액" in msg or "exhausted balance" in low or "user is locked" in low:
                status = 402
            raise HTTPException(status_code=status, detail=msg) from exc

        elapsed = round(time.time() - started, 1)
        run_result = "ok"
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
    except HTTPException as exc:
        elapsed = round(time.time() - started, 1)
        detail = exc.detail
        run_error = detail if isinstance(detail, str) else str(detail)
        raise
    except Exception as exc:  # noqa: BLE001
        elapsed = round(time.time() - started, 1)
        run_error = str(exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        await _emit_run_log(
            elapsed_sec=elapsed if elapsed is not None else round(time.time() - started, 1),
            result=run_result,
            error=run_error,
            style_id=style_id,
            provider=provider_id,
            usage=usage,
        )


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
