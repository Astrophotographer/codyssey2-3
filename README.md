# Aigraphers (Python)

사진 업로드 → 스타일 프리셋 → AI 변환.  
기존 [Aigraphers](http://100.119.70.25:8781/) UI를 유지하고, **로컬 / Fal(Qwen) / OpenAI** 를 엔진으로 고를 수 있습니다.

## OpenAI가 제일 좋나?

**이 앱(셀카→프로필·풍경 스타일 변환)에는 Fal의 Qwen-Image-Edit이 보통 더 잘 맞습니다.**

| 엔진 | 장점 | 단점 |
|------|------|------|
| **Fal (Qwen)** ★ | 지금 쓰던 2511/2509와 같은 계열, 얼굴 유지·스타일 변환에 강함, 장당 비용 보통 저렴 | 키 발급 필요 |
| **OpenAI** | 지시 따르기·상용 안정성·문서 | 비싸고, Qwen과 결과 톤이 다름 |
| **로컬** | 비용 0, 데이터 외부 미전송 | GPU 머신/워커 필요 |

추천 순서: **로컬(이미 GPU 있으면) → Fal → OpenAI**.

## 빠른 시작

```bash
cd aigraphers
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# 데모만: LOCAL_DEMO_MODE=1
# 로그인: .env의 AUTH_USER / AUTH_PASS 설정 (비어 있으면 로그인 불가)
.venv/bin/python -m app.main
```

브라우저: http://127.0.0.1:8781/

## 인증

로그인 자격 증명은 환경 변수 `AUTH_USER` / `AUTH_PASS`로 설정합니다 (`.env`에 기록).  
커밋된 파일에는 실제 비밀번호를 두지 마세요.

## API 키

`.env` 예시:

```env
DEFAULT_PROVIDER=fal
FAL_KEY=
# 또는
OPENAI_API_KEY=
```

UI 우측 상단 **엔진** 셀렉트에서 전환합니다. 키가 없는 엔진은 비활성 표시됩니다.

## 로컬 GPU 워커

기존 추론 서버가 `POST /edit` (multipart: `image` + `prompt`/`style_id` …) 를 받으면:

```env
LOCAL_DEMO_MODE=0
LOCAL_WORKER_URL=http://127.0.0.1:9000
DEFAULT_PROVIDER=local
```

워커가 이미지 바이너리 또는 `{ "output_url": "..." }` JSON을 반환하면 됩니다.

## API

- `GET /api/presets` · `GET /api/presets?category=person|landscape`
- `GET /api/providers`
- `POST /api/jobs` — `image`, `style_id`, optional `provider`, `place`, `seed`
- `GET /api/jobs/{id}` · `/input` · `/output`

작업은 원본과 같이 **한 장씩** 큐에서 처리합니다.
