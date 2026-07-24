from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import Settings
from app.presets import Preset, get_preset
from app.providers import get_provider
from app.providers.base import EditRequest


@dataclass
class Job:
    id: str
    style_id: str
    provider: str
    status: str = "queued"  # queued | running | done | failed
    progress: int = 0
    error: str | None = None
    elapsed_sec: float | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    place: str | None = None
    seed: int | None = None
    created_at: float = field(default_factory=time.time)

    def public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "style_id": self.style_id,
            "provider": self.provider,
            "status": self.status,
            "progress": self.progress,
            "error": self.error,
            "elapsed_sec": self.elapsed_sec,
            "meta": self.meta,
            "place": self.place,
            "seed": self.seed,
        }


class JobStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.root = settings.data_dir
        self.root.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._worker_lock = threading.Lock()  # one GPU/API job at a time (like original)

    def create(
        self,
        *,
        style_id: str,
        provider: str,
        image_bytes: bytes,
        filename: str,
        place: str | None,
        seed: int | None,
    ) -> Job:
        preset = get_preset(style_id)
        if not preset:
            raise ValueError(f"Unknown style_id: {style_id}")

        job_id = uuid.uuid4().hex[:12]
        job_dir = self.root / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(filename).suffix.lower() or ".jpg"
        if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
            suffix = ".jpg"
        input_path = job_dir / f"input{suffix}"
        input_path.write_bytes(image_bytes)

        job = Job(
            id=job_id,
            style_id=style_id,
            provider=provider,
            place=place,
            seed=seed,
        )
        (job_dir / "job.json").write_text(json.dumps(job.public_dict(), ensure_ascii=False, indent=2))

        with self._lock:
            self._jobs[job_id] = job

        thread = threading.Thread(
            target=self._run_job,
            args=(job_id, preset, input_path),
            daemon=True,
        )
        thread.start()
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def input_path(self, job_id: str) -> Path | None:
        d = self.root / job_id
        if not d.exists():
            return None
        for name in ("input.jpg", "input.jpeg", "input.png", "input.webp"):
            p = d / name
            if p.exists():
                return p
        matches = list(d.glob("input.*"))
        return matches[0] if matches else None

    def output_path(self, job_id: str) -> Path | None:
        p = self.root / job_id / "output.png"
        return p if p.exists() else None

    def _update(self, job_id: str, **kwargs: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            for k, v in kwargs.items():
                setattr(job, k, v)
            dump = job.public_dict()
        (self.root / job_id / "job.json").write_text(
            json.dumps(dump, ensure_ascii=False, indent=2)
        )

    def _run_job(self, job_id: str, preset: Preset, input_path: Path) -> None:
        with self._worker_lock:
            started = time.time()
            self._update(job_id, status="running", progress=8)
            try:
                job = self.get(job_id)
                if not job:
                    return
                provider = get_provider(job.provider, self.settings)
                out = self.root / job_id / "output.png"
                self._update(job_id, progress=20)
                result = provider.edit(
                    EditRequest(
                        image_path=input_path,
                        output_path=out,
                        preset=preset,
                        place=job.place,
                        seed=job.seed,
                    )
                )
                elapsed = round(time.time() - started, 1)
                self._update(
                    job_id,
                    status="done",
                    progress=100,
                    elapsed_sec=elapsed,
                    meta=result.meta,
                )
            except Exception as exc:  # noqa: BLE001 — surface to client
                elapsed = round(time.time() - started, 1)
                self._update(
                    job_id,
                    status="failed",
                    progress=100,
                    elapsed_sec=elapsed,
                    error=str(exc),
                )
