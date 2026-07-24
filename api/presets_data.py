from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Category:
    id: str
    name: str
    name_en: str
    description: str
    emoji: str
    engine_label: str


@dataclass(frozen=True)
class Preset:
    id: str
    category: str
    engine: str
    name: str
    name_en: str
    description: str
    emoji: str
    needs_place: bool
    prompt: str
    steps: int = 6
    guidance: float = 3.5

    def build_prompt(self, place: str | None = None) -> str:
        text = self.prompt
        if self.needs_place:
            label = (place or "").strip() or "Travel"
            text = text.replace("{place}", label)
        return text

    def public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "engine": self.engine,
            "name": self.name,
            "name_en": self.name_en,
            "description": self.description,
            "emoji": self.emoji,
            "needs_place": self.needs_place,
        }


CATEGORIES: list[Category] = [
    Category(
        id="person",
        name="AI 프로필 사진",
        name_en="AI Profile Photo",
        description="셀카 → 프로필·이력서·픽셀/애니 캐릭터 (Qwen-Image-Edit-2511, 4–6스텝)",
        emoji="📸",
        engine_label="2511",
    ),
    Category(
        id="landscape",
        name="풍경·스타일",
        name_en="Landscape / Style",
        description="여행·디오라마·애니 장면 변환. Qwen-Image-Edit-2509",
        emoji="🌄",
        engine_label="2509",
    ),
]

PRESETS: list[Preset] = [
    Preset(
        id="business_suit",
        category="person",
        engine="person_2511",
        name="정장 프로필",
        name_en="Business Profile",
        description="다크 정장, 중성 스튜디오 배경. 얼굴·신원은 그대로 유지합니다.",
        emoji="💼",
        needs_place=False,
        steps=4,
        prompt=(
            "Transform this selfie into a professional business profile photo. "
            "Keep the exact same face, identity, hairstyle, age, and expression. "
            "Dress the person in a dark formal suit with a clean collar. "
            "Use a neutral studio background, soft key light, sharp focus, LinkedIn-ready headshot."
        ),
    ),
    Preset(
        id="studio_headshot",
        category="person",
        engine="person_2511",
        name="스튜디오",
        name_en="Studio Headshot",
        description="소프트 림라이트, 다크 그레이 그라데이션 배경의 에디토리얼 스튜디오 초상.",
        emoji="🎬",
        needs_place=False,
        steps=4,
        prompt=(
            "Convert this photo into an editorial studio headshot. "
            "Preserve the person's face and identity exactly. "
            "Soft rim light, dark gray gradient backdrop, shallow depth of field, magazine quality."
        ),
    ),
    Preset(
        id="resume_id",
        category="person",
        engine="person_2511",
        name="이력서 반명함",
        name_en="Resume ID Photo",
        description="흰 배경, 정장, 정면·균일 조명의 증명/이력서용 초상.",
        emoji="📄",
        needs_place=False,
        steps=4,
        prompt=(
            "Make a clean resume / ID-style portrait from this selfie. "
            "Keep the face identical. White seamless background, formal attire, "
            "front-facing, even studio lighting, high clarity. Not for passport submission."
        ),
    ),
    Preset(
        id="outdoor_natural",
        category="person",
        engine="person_2511",
        name="야외 자연광",
        name_en="Outdoor Natural Light",
        description="부드럽게 흐린 사무실 배경, 자연광, 따뜻한 톤의 프로필.",
        emoji="🌤️",
        needs_place=False,
        steps=4,
        prompt=(
            "Create a natural outdoor-light profile photo. Preserve identity and face. "
            "Soft daylight, gently blurred outdoor or office window background, warm tone, candid-professional."
        ),
    ),
    Preset(
        id="upscale_sharp",
        category="person",
        engine="person_2511",
        name="또렷하게(업스케일)",
        name_en="Upscale & Sharpen",
        description="흐림을 줄이고 고해상도로 선명하게. 얼굴은 그대로 유지합니다.",
        emoji="✨",
        needs_place=False,
        steps=4,
        prompt=(
            "Enhance and sharpen this portrait while keeping the exact same face and identity. "
            "Reduce blur and noise, improve clarity and detail, natural skin texture, no beauty filter."
        ),
    ),
    Preset(
        id="lighting_fix",
        category="person",
        engine="person_2511",
        name="조명 보정",
        name_en="Lighting Fix",
        description="균일한 스튜디오 조명으로 보정. 구도와 얼굴은 유지합니다.",
        emoji="💡",
        needs_place=False,
        steps=4,
        prompt=(
            "Fix the lighting of this portrait to even studio quality. "
            "Keep composition, clothing, and face identical. Soft fill light, remove harsh shadows."
        ),
    ),
    Preset(
        id="pixel_character",
        category="person",
        engine="person_2511",
        name="픽셀·펄러 캐릭터",
        name_en="Pixel / Perler Character",
        description="셀카를 픽셀·펄러비드 캐릭터로. 얼굴·헤어·옷 특징 유지, 작업대 목업 느낌.",
        emoji="🧩",
        needs_place=False,
        steps=6,
        prompt=(
            "Turn this person into a cute pixel / perler-bead character figure. "
            "Keep recognizable face features, hair color, and outfit. "
            "Chunky bead style, toy-like, sitting on a craft workbench, vibrant colors."
        ),
    ),
    Preset(
        id="anime_character_grid",
        category="person",
        engine="person_2511",
        name="애니 4컷 캐릭터",
        name_en="Anime 4-Panel Character",
        description="같은 캐릭터로 표정·포즈 4종 2×2 그리드. 닮음·의상 일관 유지.",
        emoji="🎨",
        needs_place=False,
        steps=6,
        prompt=(
            "Create a 2x2 anime character expression sheet based on this person. "
            "Same character in four panels with different expressions/poses. "
            "Keep likeness, hair, and outfit consistent. Clean anime illustration style."
        ),
    ),
    Preset(
        id="travel_magnet",
        category="landscape",
        engine="landscape_2509",
        name="여행 마그넷",
        name_en="Travel Magnet",
        description="랜드마크와 장면을 기념품 마그넷처럼 구성합니다. 장소명을 넣으면 하단에 표기됩니다.",
        emoji="🧲",
        needs_place=True,
        steps=6,
        prompt=(
            "Turn this travel photo into a souvenir fridge magnet design. "
            "Keep the main landmark and scene recognizable. "
            "Add the place name '{place}' as bold souvenir text at the bottom. "
            "Slightly stylized, collectible magnet look, glossy finish."
        ),
    ),
    Preset(
        id="pixel_game",
        category="landscape",
        engine="landscape_2509",
        name="픽셀모드",
        name_en="Pixel Game Background",
        description="구도·분위기는 유지하고, 플레이 가능한 레트로 픽셀게임 배경처럼 굵은 도트로 재구성합니다.",
        emoji="👾",
        needs_place=False,
        steps=6,
        prompt=(
            "Transform this photo into a playable retro pixel-game background, not a simple pixelation filter. "
            "Keep the original composition and atmosphere. "
            "Simplify every element — buildings, people, trees, sky, signs — into chunky 8-bit to 16-bit game graphics with bold visible dots. "
            "It must look like an authentic low-resolution pixel art scene used inside a real retro video game, "
            "with maximized low-res retro game feeling where each pixel is sharp and clearly readable. "
            "Push further toward an extreme low-resolution pixel-game look."
        ),
    ),
    Preset(
        id="origami_world",
        category="landscape",
        engine="landscape_2509",
        name="종이접기",
        name_en="Origami Diorama",
        description="구도는 유지하고, 모든 요소를 접힘선과 각진 형태가 살아있는 종이접기 디오라마로 바꿉니다.",
        emoji="🦢",
        needs_place=False,
        steps=6,
        prompt=(
            "Transform this photo into an origami paper-folded world while keeping the original composition. "
            "Convert every element into folded paper crafts. "
            "Emphasize real crease lines, sharp angular folds, and paper edges. "
            "Make it look like a handcrafted origami diorama with tangible paper texture and folded forms."
        ),
    ),
    Preset(
        id="lego_diorama",
        category="landscape",
        engine="landscape_2509",
        name="레고",
        name_en="LEGO Diorama",
        description="분위기는 유지하고, 모든 요소를 실제 레고 브릭 디오라마처럼 사실적으로 표현합니다.",
        emoji="🧱",
        needs_place=False,
        steps=6,
        prompt=(
            "Rebuild this scene so every element looks naturally made of real LEGO bricks, "
            "while preserving the original atmosphere. "
            "Create a photorealistic LEGO diorama — as if photographing an actual physical LEGO build, "
            "with authentic brick studs, plastic material, and realistic lighting."
        ),
    ),
    Preset(
        id="warm_handdrawn",
        category="landscape",
        engine="landscape_2509",
        name="따뜻한 손그림 애니",
        name_en="Warm Hand-drawn Anime",
        description="풍경·장면을 부드러운 손그림 애니메이션 풍으로 따뜻하게 바꿉니다.",
        emoji="✏️",
        needs_place=False,
        steps=6,
        prompt=(
            "Redraw this landscape as a warm hand-drawn anime background. "
            "Keep layout and landmarks. Soft watercolor-ink feel, cozy lighting, Studio Ghibli-adjacent mood."
        ),
    ),
    Preset(
        id="fairy_3d",
        category="landscape",
        engine="landscape_2509",
        name="3D 동화 장면",
        name_en="3D Fairy Tale Scene",
        description="장면을 디즈니·픽사 감성의 부드러운 3D 동화 스타일로 변환합니다.",
        emoji="✨",
        needs_place=False,
        steps=6,
        prompt=(
            "Transform this scene into a soft 3D fairy-tale render (Pixar/Disney-like). "
            "Keep recognizable layout. Rounded forms, cinematic lighting, magical atmosphere."
        ),
    ),
    Preset(
        id="mini_figure",
        category="landscape",
        engine="landscape_2509",
        name="미니어처 디오라마",
        name_en="Miniature Diorama",
        description="장면을 틸트시프트 미니어처 디오라마처럼 보이게 만듭니다.",
        emoji="🎀",
        needs_place=False,
        steps=6,
        prompt=(
            "Make this scene look like a tilt-shift miniature diorama. "
            "Toy-like scale, shallow depth of field, vibrant miniature model look."
        ),
    ),
]

_PRESET_BY_ID = {p.id: p for p in PRESETS}


def get_preset(style_id: str) -> Preset | None:
    return _PRESET_BY_ID.get(style_id)


def category_dicts() -> list[dict[str, Any]]:
    return [
        {
            "id": c.id,
            "name": c.name,
            "name_en": c.name_en,
            "description": c.description,
            "emoji": c.emoji,
            "engine_label": c.engine_label,
        }
        for c in CATEGORIES
    ]


def preset_dicts(category: str | None = None) -> list[dict[str, Any]]:
    items = PRESETS
    if category:
        items = [p for p in PRESETS if p.category == category]
    return [p.public_dict() for p in items]
