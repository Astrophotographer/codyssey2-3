from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from app.presets import Preset


@dataclass
class EditRequest:
    image_path: Path
    output_path: Path
    preset: Preset
    place: str | None = None
    seed: int | None = None
    provider_hint: str | None = None


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
