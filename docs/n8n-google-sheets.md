# n8n → Google Sheets (문의 + 실행로그 + 서버온도)


## Live setup (자동 구성됨)

| 항목 | 링크 |
|------|------|
| n8n 워크플로 | https://n8n.chanuk.theworkpc.com/workflow/T1rEP5xqSu60CuNQ |
| Production Webhook | `https://n8n.chanuk.theworkpc.com/webhook/aigraphers-ops` (contact / runlog / visit 공통) |
| Google Sheets | https://docs.google.com/spreadsheets/d/1O3ceQaqoNW9BDQrUwq4IRYovkLmT5k6AeQvUXj70Quk/edit |
| Google Form | https://docs.google.com/forms/d/1ZNL9Qaj2AvpeGv3nZenqgHAPetGraDVsHWXlDWw2BpA/viewform |

시트 탭: `문의` / `실행로그` / `서버온도` / `방문`. 폼 질문은 이름·이메일·문의 내용(장문, 필수).

Aigraphers는 네 가지 이벤트를 n8n Webhook으로 보냅니다. Google Form entry ID는 **코드에 넣지 않습니다**. Sheets 컬럼 매핑은 n8n에서 합니다.

공개 설정은 `GET /api/config`로 확인합니다 (`google_form_url` + feature 플래그만, webhook URL은 노출하지 않음).

## 환경 변수

| Env | 용도 |
|-----|------|
| `N8N_CONTACT_WEBHOOK_URL` | 문의/피드백 (`POST /api/contact`) → Sheet `문의` |
| `N8N_RUNLOG_WEBHOOK_URL` | AI 변환 후 `run_log` + `server_temp` 두 페이로드 (`POST /api/transform` finally에서 await) |
| `N8N_VISIT_WEBHOOK_URL` | 방문 기록 (`POST /api/visit`) |
| `GOOGLE_FORM_URL` | (선택) `GET /api/config`·문의 응답에 포함 → UI 링크 + `#googleFormEmbed` iframe |
| `SERVER_TEMP_C` | (선택) 서버 온도 °C. 없으면 Linux `/sys/class/thermal/thermal_zone*/temp` 시도, 그래도 없으면 `null` |

Webhook env가 비어 있으면 해당 기능은 no-op입니다 (문의는 `forwarded: false`, runlog/visit은 조용히 스킵).

## Google Sheets 권장 구조 (3시트)

### Sheet `문의` — from contact webhook

| timestamp | name | email | message | rating |
|-----------|------|-------|---------|--------|

Contact webhook body 예:

```json
{
  "type": "contact",
  "name": "홍길동",
  "email": "you@example.com",
  "message": "피드백…",
  "rating": 5,
  "ts": "2026-07-24T05:00:00+00:00",
  "environment": { "runtime": "vercel", "vercel_env": "production", "vercel_region": "icn1", "python": "3.12.x" }
}
```

### Sheet `실행로그` — from `type: "run_log"`

| timestamp | elapsed_sec | total_tokens | est_usd | result | provider | style_id | environment |
|-----------|-------------|--------------|---------|--------|----------|----------|-------------|

Run log body 예:

```json
{
  "type": "run_log",
  "elapsed_sec": 12.3,
  "result": "ok",
  "error": null,
  "style_id": "studio_id",
  "provider": "openai",
  "environment": {
    "runtime": "vercel",
    "vercel_env": "production",
    "vercel_region": "icn1",
    "python": "3.12.x"
  },
  "ts": "2026-07-24T05:01:00+00:00",
  "total_tokens": 4200,
  "input_tokens": 3100,
  "output_tokens": 1100,
  "est_usd": 0.042,
  "usage": { "total_tokens": 4200, "input_tokens": 3100, "output_tokens": 1100, "est_usd": 0.042 },
  "run_id": "a1b2c3d4e5f6"
}
```

토큰/비용 필드는 provider meta에 없으면 `null`입니다. `usage`는 전체 객체입니다.

### Sheet `서버온도` — from `type: "server_temp"`

| timestamp | server_temp_c | run_id | result | provider | environment |
|-----------|---------------|--------|--------|----------|-------------|

Server temp body 예 (같은 `N8N_RUNLOG_WEBHOOK_URL`로 두 번째 POST):

```json
{
  "type": "server_temp",
  "ts": "2026-07-24T05:01:00+00:00",
  "server_temp_c": null,
  "environment": {
    "runtime": "vercel",
    "vercel_env": "production",
    "vercel_region": "icn1",
    "python": "3.12.x"
  },
  "run_id": "a1b2c3d4e5f6",
  "result": "ok",
  "provider": "openai"
}
```

`server_temp_c`가 `null`이면 n8n에서 별도 센서 노드(Home Assistant, IoT, 모니터링 API 등)로 온도를 이어 붙이면 됩니다. `run_id`로 `실행로그` 행과 조인할 수 있습니다.

## n8n 워크플로 (Webhook → IF → Sheets append)

한 개의 Production Webhook으로 contact / run_log / server_temp / visit를 모두 받을 수도 있고, env별로 URL을 나눠도 됩니다. 라우팅은 **IF 노드**로 `type`을 분기합니다.

1. **Webhook** 노드 → Method `POST` → Path 예: `aigraphers-ops`  
   → Production URL을 Vercel env에 넣기 (`N8N_CONTACT_WEBHOOK_URL` / `N8N_RUNLOG_WEBHOOK_URL` / `N8N_VISIT_WEBHOOK_URL` — 같은 URL을 세 번 써도 됨).
2. **IF** (또는 Switch) 노드 → 조건:

| `type` | Sheet |
|--------|--------|
| `contact` | `문의` |
| `run_log` | `실행로그` |
| `server_temp` | `서버온도` |
| `visit` | (선택) 방문 시트 |

3. 각 분기에서 **Google Sheets** → Operation **Append**  
   - `문의`: `ts`→timestamp, `name`, `email`, `message`, `rating`  
   - `실행로그`: `ts`→timestamp, `elapsed_sec`, `total_tokens`, `est_usd`, `result`, `provider`, `style_id`, `environment` (JSON 문자열 OK: `{{ JSON.stringify($json.environment) }}`)  
   - `서버온도`: `ts`→timestamp, `server_temp_c`, `run_id`, `result`, `provider`, `environment`
4. Webhook에서 **Respond Immediately**를 켜면 n8n이 느려도 API 타임아웃(약 10초)을 피하기 쉽습니다.

### 팁

- Production Webhook URL만 Vercel Production env에 넣고, Test URL은 로컬 `.env`에 두세요.
- 시크릿이 들어 있는 URL은 README·커밋·채팅에 붙이지 마세요.
- Vercel은 응답 후 daemon thread를 죽이므로 run log는 **async await**로 보냅니다 (문의·visit과 동일).

## (선택) Google Form 병렬 수집

1. Google Form을 만들고 응답을 같은 스프레드시트(또는 별도 시트)로 연결합니다.
2. Form의 **공개 응답 URL**을 `GOOGLE_FORM_URL`에 넣습니다.
3. 프론트는 부팅 시 `/api/config`로 URL을 받아 「구글폼으로도 남기기」 링크와 `#googleFormEmbed` iframe을 표시합니다.
4. 사이트 폼(n8n → Sheets)과 구글폼은 **병렬** 수집 경로입니다. Form entry ID는 서버 코드에 없습니다.

## UX 측정과의 연결

- **방문 로그** + 푸터의 로컬 방문 횟수 → 배포 전후 트래픽·테마 사용을 수업에서 비교.
- **실행로그**의 `result` / `elapsed_sec` / `total_tokens` / `est_usd` / `provider` → 실패율·체감 속도·비용.
- **서버온도** + `run_id` → 실행과 온도를 같은 타임라인으로 묶기.
- **문의 rating** → 주관적 만족도.
- **다크 모드** (`theme` in visit payload) → 테마 토글 사용률.
