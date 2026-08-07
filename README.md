# Aigraphers

사진 업로드 → 스타일 프리셋 → AI 변환 (Local / Fal / OpenAI).  
Vercel 정적 프론트 + Python (FastAPI) 서버리스 API.

## 배포 URL · 주요 3페이지

| # | 페이지 | URL |
|---|--------|-----|
| 1 | 작업실 (변환) | https://aigraphers.vercel.app/ |
| 2 | 문의 / 피드백 | https://aigraphers.vercel.app/contact.html |
| 3 | 운영 · 측정 | https://aigraphers.vercel.app/ops.html |

API 스모크: [health](https://aigraphers.vercel.app/api/health) · [config](https://aigraphers.vercel.app/api/config) · [providers](https://aigraphers.vercel.app/api/providers)

증빙(스크린샷·배포 로그·기획서): [`docs/evidence/`](docs/evidence/) · [`docs/aigraphers-기획서.pdf`](docs/aigraphers-기획서.pdf)

## Folder structure

```
aigraphers/
  index.html          # 1) 작업실 UI
  contact.html        # 2) 문의 페이지
  ops.html            # 3) 운영·측정 페이지
  css/styles.css
  js/app.js
  images/
  public/             # Vercel CDN mirror
  api/                # FastAPI (Vercel entry)
  docs/
    aigraphers-기획서.pdf
    n8n-google-sheets.md
    evidence/         # 스크린샷·배포/API 로그
  requirements.txt
  vercel.json
  .env.example
  legacy/
```

## Environment variables

Copy `.env.example` → `.env` for local use. On Vercel, set the same names in Project Settings → Environment Variables.

| Name | Required | Description |
|------|----------|-------------|
| `OPENAI_API_KEY` | for OpenAI | OpenAI Images edits |
| `FAL_KEY` | for Fal | Fal Qwen Image Edit (**잔액 필요**) |
| `DEFAULT_PROVIDER` | optional | `local` / `fal` / `openai` (권장: 잔액 있는 쪽) |
| `LOCAL_WORKER_URL` | optional | GPU worker; 없으면 Local = 데모 PIL |
| `N8N_CONTACT_WEBHOOK_URL` | optional | 문의 → n8n → Sheets |
| `N8N_RUNLOG_WEBHOOK_URL` | optional | `run_log` + `server_temp` |
| `N8N_VISIT_WEBHOOK_URL` | optional | 방문 분석 |
| `GOOGLE_FORM_URL` | optional | 구글폼 링크/임베드 |
| `SERVER_TEMP_C` | optional | 실행 로그용 °C |

Do **not** commit `.env`.  
n8n + Sheets: [docs/n8n-google-sheets.md](docs/n8n-google-sheets.md).

## Local development

```bash
cd aigraphers
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill keys
npx vercel dev
```

Smoke:

- `GET /api/health` · `/api/config` · `/api/presets` · `/api/providers`
- `POST /api/transform` — multipart `image`, `style_id`, `provider`
- `POST /api/contact` · `POST /api/visit`

## Deploy to Vercel

```bash
npx vercel --prod
npx vercel env add OPENAI_API_KEY production
npx vercel env add FAL_KEY production
# + N8N_* / GOOGLE_FORM_URL as needed
```

GitHub: `Astrophotographer/codyssey2-1`.

---

## Troubleshooting (로그 · 콘솔 · 재배포)

### 브라우저에서 확인

1. 사이트 열기 → DevTools **Console** / **Network**
2. 변환 실패 시 Network에서 `POST /api/transform` 응답 JSON의 `detail` 확인
3. 흔한 원인
   - **Fal 402/403 · 잔액 소진** → OpenAI 또는 Local로 전환, [fal.ai billing](https://fal.ai/dashboard/billing) 충전
   - **400 missing key** → Vercel env에 `OPENAI_API_KEY` / `FAL_KEY` 미설정
   - **타임아웃(~55s)** → 큰 이미지 축소 후 재시도, OpenAI는 응답이 길 수 있음

### Vercel 배포/런타임 로그

```bash
# 최근 배포 상태
npx vercel ls

# 특정 배포 검사
npx vercel inspect aigraphers.vercel.app

# 런타임 로그(실시간)
npx vercel logs aigraphers.vercel.app --follow

# 대시보드
# https://vercel.com → Project aigraphers → Deployments → (배포 선택) → Logs / Functions
```

### 재배포 · 문제 해결 순서

1. `npx vercel env ls` 로 Production 키 존재 확인 (값은 숨김)
2. `curl -s https://aigraphers.vercel.app/api/health | jq` — providers `ready`
3. Local로 `POST /api/transform` 스모크 (항상 데모 동작)
4. Fal 실패 시 메시지에 「잔액」포함 여부 확인 → 충전 또는 provider 변경
5. `npx vercel --prod` 재배포 후 동일 curl 재실행
6. n8n 문의 전달 실패(502) → n8n Production Webhook·워크플로 Active 여부

증빙 로그 예시: [`docs/evidence/api-smoke-log.txt`](docs/evidence/api-smoke-log.txt), [`docs/evidence/deploy-log.txt`](docs/evidence/deploy-log.txt)

---

## 시크릿 유출 대응

즉시 절차:

1. **폐기** — 노출된 키를 해당 콘솔에서 revoke  
   - OpenAI: API keys  
   - Fal: API keys  
   - n8n: webhook URL 재발급(워크플로 Webhook path 변경)  
   - Vercel/GitHub 토큰이 노출된 경우도 즉시 revoke
2. **롤오버** — 새 키 발급 → `npx vercel env rm <NAME> production` 후 `env add` 또는 Dashboard에서 교체 → `npx vercel --prod`
3. **로그 조사** — Vercel Function Logs, n8n Executions, Git 히스토리에서 커밋 여부 확인  
   - `.env`가 커밋됐다면 history에서 제거(또는 키 폐기만으로 무효화) 후 force-push는 팀 합의 하에
4. **재발방지** — `.gitignore`에 `.env` 유지, README/이슈/채팅에 키 붙여넣지 않기, Vercel Sensitive env 사용

---

## 지연·비용 개선 옵션 (요약)

| 방안 | 효과 | 비고 |
|------|------|------|
| 프리셋/providers 응답 캐시 (CDN/`Cache-Control` 또는 엣지) | TTFB↓ | 정적에 가깝고 변경 드묾 |
| 업로드 전 클라이언트 리사이즈 (긴 변 ≤1024~1536) | 전송·토큰·Fal 비용↓ | UX도 개선 |
| 기본 provider를 잔액 있는 쪽으로 | 실패율↓ | Fal 소진 시 OpenAI/Local |
| 변환 비동기 큐 (DB + worker / Inngest 등) | 타임아웃 회피 | Vercel 60s 한도 우회 |
| 실패 시 지수 백오프 재시도 (idempotent job id) | 일시 오류 흡수 | 과금 API는 1회 제한 권장 |
| Local GPU worker | 단가↓ | `LOCAL_WORKER_URL` |

현재는 동기 `await` transform + n8n 로그 await(Vercel-safe). 큐 도입 시 `/api/transform`는 job id 반환 → 폴링/웹훅 완료 통지가 다음 단계.

---

## 프레임워크 변경 시 영향 (간단 분석)

현재: **정적 HTML/JS + FastAPI(Vercel Python)**.

| 대안 | 장점 | 단점 | 마이그레이션 범위 |
|------|------|------|-------------------|
| **Next.js (App Router)** | RSC, 라우팅·이미지 최적화, Vercel 최적 | Python 프로바이더를 Route Handler/별도 서비스로 이전 필요 | 중~대: UI 재작성, `api/` → Route Handlers 또는 외부 API |
| **FastAPI 단독 (Docker/Cloud Run)** | GPU worker 동일 스택, 긴 타임아웃 | CDN·엣지 이점↓, 인프라 관리↑ | 중: `legacy/` 방향, 프론트는 정적 유지 가능 |
| **Streamlit / Gradio** | 데모 속도↑ | 커스텀 UX·다페이지·브랜딩 약함 | 소~중: 프로토타입 교체, 과제용 브랜딩 재작업 |

권장 유지: 과제·운영(n8n) 연동이 단순한 현재 구조. Next.js는 UI/SEO가 커질 때, Docker FastAPI는 Local GPU를 상시 붙일 때.

---

## Features

- Clay Cafe UI, Aigraphers 브랜딩, **3개 독립 페이지**
- Dark mode · 마이크로 인터랙션 · 방문 측정
- 문의 → n8n → Sheets + 구글폼 병렬
- 실행로그(토큰/비용) · 서버온도 시트 분기
- Local / Fal / OpenAI · Fal 잔액 소진 시 한국어 안내
- 에러 배너(입력·4xx/5xx·타임아웃)

## Legacy

`legacy/` — 이전 Docker + 로그인 FastAPI 참고용.
