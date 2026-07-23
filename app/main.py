from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import ROOT, get_settings
from app.jobs import JobStore
from app.presets import category_dicts, get_preset, preset_dicts
from app.providers import list_providers

settings = get_settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
store = JobStore(settings)

app = FastAPI(title="Aigraphers", version="0.2.0")
static_dir = ROOT / "static"

PUBLIC_PATHS = {
    "/login",
    "/styles.css",
    "/favicon.ico",
}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in PUBLIC_PATHS:
            return await call_next(request)
        if request.session.get("user"):
            return await call_next(request)
        if path.startswith("/api/"):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return RedirectResponse(url="/login", status_code=303)


# Auth runs after SessionMiddleware populates request.session
app.add_middleware(AuthMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="aigraphers_session",
    same_site="lax",
    https_only=False,
)


def _login_html(error: str | None = None) -> str:
    template = (static_dir / "login.html").read_text(encoding="utf-8")
    err_block = (
        f'<p class="login-error">{error}</p>' if error else ""
    )
    return template.replace("__ERROR__", err_block)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse(url="/", status_code=303)
    return HTMLResponse(_login_html())


@app.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    # Fail closed: empty AUTH_USER/AUTH_PASS never authenticate.
    if (
        settings.auth_user
        and settings.auth_pass
        and username == settings.auth_user
        and password == settings.auth_pass
    ):
        request.session["user"] = username
        return RedirectResponse(url="/", status_code=303)
    return HTMLResponse(_login_html("아이디 또는 비밀번호가 올바르지 않습니다."), status_code=401)


@app.get("/logout")
def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


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


@app.post("/api/jobs")
async def create_job(
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
        raise HTTPException(status_code=400, detail=f"Max upload {settings.max_upload_mb}MB")

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
        job = store.create(
            style_id=style_id,
            provider=provider_id,
            image_bytes=raw,
            filename=name,
            place=(place or "").strip() or None,
            seed=seed_val,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return job.public_dict()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = store.get(job_id)
    if not job:
        meta = settings.data_dir / job_id / "job.json"
        if meta.exists():
            import json

            return json.loads(meta.read_text())
        raise HTTPException(status_code=404, detail="job not found")
    return job.public_dict()


@app.get("/api/jobs/{job_id}/input")
def get_input(job_id: str) -> FileResponse:
    path = store.input_path(job_id)
    if not path:
        raise HTTPException(status_code=404, detail="input not found")
    return FileResponse(path)


@app.get("/api/jobs/{job_id}/output")
def get_output(job_id: str) -> FileResponse:
    path = store.output_path(job_id)
    if not path:
        raise HTTPException(status_code=404, detail="output not found")
    return FileResponse(path, filename=f"atelier-{job_id}.png")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/app.js")
def app_js() -> FileResponse:
    return FileResponse(static_dir / "app.js", media_type="application/javascript")


@app.get("/styles.css")
def styles_css() -> FileResponse:
    return FileResponse(static_dir / "styles.css", media_type="text/css")


def main() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
