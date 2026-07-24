# Aigraphers

사진 업로드 → 스타일 프리셋 → AI 변환 (Local / Fal / OpenAI).  
Vercel 정적 프론트 + Python (FastAPI) 서버리스 API.

## Folder structure

```
aigraphers/
  index.html          # UI
  css/styles.css
  js/app.js
  images/             # favicon 등
  api/
    index.py          # FastAPI app (Vercel entry)
    presets_data.py
    ai_providers.py
    config.py
  requirements.txt
  vercel.json
  .env.example
  legacy/             # 이전 Docker/FastAPI 앱 (참고용)
```

## Environment variables

Copy `.env.example` → `.env` for local use. On Vercel, set the same names in Project Settings → Environment Variables (or via CLI).

| Name | Required | Description |
|------|----------|-------------|
| `OPENAI_API_KEY` | for OpenAI chip | OpenAI Images edits |
| `FAL_KEY` | for Fal chip | Fal Qwen Image Edit |
| `DEFAULT_PROVIDER` | optional | `local` (default) / `fal` / `openai` |
| `LOCAL_WORKER_URL` | optional | GPU worker; without it Local = demo PIL filter |

Do **not** commit `.env`. Keys come from env only.

## Local development (`vercel dev`)

```bash
cd aigraphers
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# fill OPENAI_API_KEY and/or FAL_KEY
npx vercel dev
```

Open the URL printed by `vercel dev` (usually http://127.0.0.1:3000).

API smoke checks:

- `GET /api/health`
- `GET /api/presets`
- `GET /api/providers`
- `POST /api/transform` — multipart: `image`, `style_id`, `provider`, optional `place` / `seed`

## Deploy to Vercel (GitHub)

1. Push this repo to GitHub (already linked: `Astrophotographer/codyssey2-1`).
2. [Vercel Dashboard](https://vercel.com) → **Add New Project** → Import the GitHub repo.
3. Framework Preset: Other. Root directory: repo root.
4. Add env vars: `OPENAI_API_KEY`, `FAL_KEY` (Production + Preview as needed).
5. Deploy.

Or CLI (after `npx vercel login`):

```bash
npx vercel --prod
# set secrets without printing them:
npx vercel env add OPENAI_API_KEY production
npx vercel env add FAL_KEY production
```

## Features

- Clay Cafe UI (no orange), Aigraphers branding
- API segment: Local / Fal / OpenAI
- Landscape presets include `pixel_game`, `origami_world`, `lego_diorama`
- OpenAI usage / approx cost after a successful OpenAI run
- Brand click → home
- Error banner for missing input, API 4xx/5xx, and ~55s timeout

## Legacy

`legacy/` keeps the previous Docker + session-login FastAPI app for reference. The main path is static files + `api/` on Vercel (no login gate).
