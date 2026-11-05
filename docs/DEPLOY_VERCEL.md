# Vercel 배포 체크리스트 / Vercel 部署清单

> 증상: 배포 사이트에서 **AI·카카오 로그인·메일 발송이 모두 실패**하고, `/api/health/config` 의 `env` 가 **전부 false**.
> 원인은 거의 항상 **환경변수가 이 프로젝트의 Production 환경에 주입되지 않은 것**입니다.

---

## 0. 30초 진단

```bash
curl -s https://<your-domain>/api/health/config | python -m json.tool
```

- `env` 의 값이 `false` → 그 변수가 **없다**. 아래 1번부터.
- `env` 는 `true` 인데 `llm.configured` 가 `false` → 키 값이 비었거나 공백.
- `notices_source` 가 `local` → Supabase 변수 미설정(공지는 로컬 JSON 사용 중).
- `supabase.mode` 가 `local` → 익명 로그인 꺼짐 + 디바이스 SQL 미적용(2번 참고).

---

## 1. 환경변수 넣기 (가장 흔한 실수 3가지)

Vercel → **해당 프로젝트** → Settings → **Environment Variables**

| 실수 | 확인 방법 |
|---|---|
| 다른 프로젝트에 넣음 | 대시보드 상단 프로젝트명이 `zero-notice` 인지 확인 (프로젝트가 여러 개면 자주 발생) |
| **Preview/Development** 스코프에만 넣음 | 각 변수의 Environments 에 **Production** 체크되어 있는지 확인 |
| 넣고 **재배포 안 함** | 환경변수는 빌드 시점에 주입됨 → Deployments → 최신 → **Redeploy** |

필수 변수:

```ini
# Supabase (공지 공유 + 사용자별 데이터)
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=sb_publishable_...
SUPABASE_BUCKET=attachments
SUPABASE_RETENTION_DAYS=30

# LLM (OpenAI 호환)
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-flash

# 메일 (QQ 메일은 16자리 인증코드)
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_SECURITY=starttls
SMTP_USER=xxxx@qq.com
SMTP_AUTH_CODE=...
SMTP_FROM_NAME=ZeroNotice

# 크론 보호
CRON_SECRET=<임의의 긴 문자열>
```

> `SUPABASE_SERVICE_KEY` 는 **절대 Vercel 에 넣지 마세요.** 로컬 `scripts/sync_supabase.py` 전용입니다.

---

## 2. Supabase 쪽 두 가지 설정

1. **익명 로그인** (없으면 카카오 로그인 전까지 사용자 데이터가 로컬에만 저장됨)
   Authentication → Sign In / Providers → **Anonymous sign-ins → Enable → Save**
2. **Redirect URL** (카카오 로그인 후 돌아올 주소)
   Authentication → URL Configuration → Redirect URLs 에 추가:
   ```
   https://<your-domain>/**
   https://*-<team>.vercel.app/**
   ```

---

## 3. 카카오 로그인

1. [Kakao Developers](https://developers.kakao.com) → 내 애플리케이션 → **REST API 키**
2. 카카오 로그인 → 활성화 → Redirect URI:
   ```
   https://<project-ref>.supabase.co/auth/v1/callback
   ```
3. Supabase → Authentication → Providers → **Kakao** → REST API 키 + Client Secret 입력 → Enable
4. 앱에서 우측 상단 **카카오 로그인** 클릭

로그인 후 `/api/auth/me` 가 `{"user":{"user_id":"...","provider":"kakao"}}` 를 반환하면 성공입니다.

---

## 4. 메일이 안 나갈 때

| 증상 | 원인 / 조치 |
|---|---|
| `SMTP 자격증명이 없습니다: SMTP_USER` | 환경변수 미설정(위 1번) |
| `SMTP 인증 실패(535)` | QQ 비밀번호가 아니라 **인증코드**를 넣어야 함 |
| Vercel 에서 타임아웃 | 465 가 막히는 경우가 있음 → `SMTP_PORT=587`, `SMTP_SECURITY=starttls` |
| 로컬은 되는데 배포만 실패 | 환경변수 스코프(Production) 확인 |

로컬에서 SMTP 만 따로 확인:

```bash
python -c "import notifier; print(notifier.smtp_status()); print(notifier.send_mail('me@example.com','test','hello'))"
```

---

## 5. 화면이 하얗게 나올 때

- 배포 직후 브라우저가 **예전 index.html/JS 를 캐시**한 경우가 대부분입니다 → `Ctrl+Shift+R` 또는 시크릿 창.
- 현재 코드는 `/` 응답에 `Cache-Control: no-store`, `/assets/*` 는 해시 파일이라 `immutable` 캐시를 보냅니다.
- 그래도 하얗면 개발자도구 → Console 의 첫 에러를 확인하세요(대개 `/api/*` 500 또는 404).

---

## 6. 배포 후 3줄 검증

```bash
curl -s https://<domain>/api/health/config        # env 전부 true, llm.configured true
curl -s -X POST https://<domain>/api/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"이번 주 마감 공지"}],"lang":"ko"}'
curl -s "https://<domain>/api/cron/reminders?secret=$CRON_SECRET"
```
