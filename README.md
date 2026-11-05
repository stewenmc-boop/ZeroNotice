# ⚡ ZeroNotice (제로노티스)

> **2026 KNU AI HACKATHON · Zero to One 출품작**
> 강원대학교 공지 탐색과 `.hwp` 첨부파일 열람의 **'숨은 비용(시간·에너지·금전·불안)'** 을 0(Zero)에 가깝게 만드는 AI 공지 비서

---

## 1. 한 문장 문제 정의

> **[누가]** 강원대학교(춘천·삼척·강릉·원주) 재학생, 외국인 유학생, 교직원 및 지역주민이
> **[언제]** 매주 장학금·학사일정·대외활동 공지를 찾고 신청을 준비할 때,
> **[무엇 때문에]** 통합 홈페이지의 캠퍼스별 공지 혼재와 `.hwp`/`.hwpx` 첨부파일 속에 숨겨진 자격요건(GPA·소득분위·재학생 지원불가 등), 그리고 행정실 문의 메일·지원서 작성 부담 때문에
> **[얼마나 큰 비용을]** 매주 50분 이상의 탐색·열람 시간, 무관한 공지를 읽는 에너지, 장학금을 놓치거나 한국어 경어 메일 작성에 망설이는 금전·불안의 **'숨은 비용'** 을 지불하고 있습니다.

### 기존 서비스로는 왜 부족한가
학교 홈페이지 검색은 **제목 키워드**만 찾습니다. 본문이 비어 있고 `.hwp` 첨부에만 모집요강이 있는 공고는 열어보지 못하며, 내 학점·소득구간·캠퍼스 조건과 대조해 주지도, 캘린더 등록·담당자 문의메일·지원서 초안까지 대신 해 주지도 않습니다.

---

## 2. 핵심 기능

1. **강원대 공식 게시판 연동** — 장학(721)·학사(720)·공모(719)·일반(504)·행사(715)의 실제 공지 22건, 담당 부서 연락처/이메일, 첨부파일 링크
2. **첨부파일 5종 텍스트 추출** — `.hwp` `.hwpx` `.pdf` `.xlsx` `.docx` 를 서버에서 직접 파싱. 본문이 0자인 공고도 첨부 안의 자격요건·제출서류까지 읽습니다
3. **내 학적 조건 1초 적합도 판정** — 캠퍼스·신분·GPA·소득구간을 규칙 엔진으로 대조해 `지원 가능` / `조건 확인` / `대상 아님` + 사유 표시
4. **한국어·중국어·영어 전환** — 유학생을 위한 공지 요약·판정 사유·UI 전체 번역
5. **일을 끝까지 해내는 AI 에이전트 3종** — `.ics` 마감 캘린더, 담당 부서 경어 문의메일, 500자 지원서 초안
6. **신청 정보 AI 추출** — 공지 본문·첨부에서 `신청 링크`·`접수 방법`·`제출 서류`·`문의처`를 뽑아 카드로 표시(출처·신뢰도 포함). 공고에 이메일이 없으면 메일 버튼을 숨기고 전화 문의를 안내합니다
7. **포스터 이미지에서 링크 추출** — `.png` 포스터는 Windows OCR로 텍스트를 뽑고, 정규식으로 URL/이메일/전화를 분리한 뒤 **실제 HTTP 요청으로 살아있는 링크만** 채택합니다. 링크가 이미지에만 있는 공고도 신청 버튼이 생깁니다
10. **플로팅 AI 비서** — 오른쪽 아래 구슬을 누르면 대화창이 열립니다. "이번 주 마감 공지", "내가 지원 가능한 공모전", "이 공지 구독해줘", "문의 메일 보내줘" 처럼 말로 시키면 실제 도구(검색·상세·구독·메일)를 호출해 처리합니다
8. **목록 필터** — `신청 링크만` / `지원 가능` / `HWP 파싱` 칩으로 바로 걸러볼 수 있고, 검색은 추출된 신청정보까지 대상입니다
9. **관심 공지 마감 알림** — 공지를 `관심 등록`하면 서버가 **마감 24시간 전에** 프로필 이메일로 "곧 마감, 지금 신청하세요" 메일을 보냅니다(`.ics` 첨부). 이메일은 왼쪽 패널에 이미 입력한 값을 그대로 사용합니다

---

## 3. 기술 스택

- **Frontend** (`frontend/`): React 18 + Vite 5 + TailwindCSS + lucide-react, 3단 워크스페이스, `localStorage`에 학적 조건·북마크·신청 진행 상태 저장
- **Backend** (`app.py`, `agent.py`, `scraper.py`): Python FastAPI + Groq LPU(`llama-3.3-70b-versatile`) + `.hwp`(UTF-16LE 스트림) / `.hwpx`(ZIP+XML) 파서
- **LLM 없이도 동작**: 키가 없으면 템플릿 엔진으로 폴백하고 응답의 `engine` 필드에 실제 엔진을 표기합니다.

---

## 4. 실행 방법

### 4.1 가장 빠른 실행 (Node 불필요)

저장소에 빌드 산출물 `frontend/dist` 가 포함되어 있어 clone 후 바로 실행됩니다.

```bash
git clone https://github.com/stewenmc-boop/ZeroNotice.git
cd ZeroNotice
pip install -r requirements.txt
cp .env.example .env        # GROQ_API_KEY 입력(선택)
python app.py               # http://127.0.0.1:8000
```

### 4.2 프론트엔드를 수정할 때

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173, /api → 127.0.0.1:8000 프록시
npm run build               # 수정 후 반드시 재빌드 → frontend/dist 갱신 → 커밋
```

### 4.3 데모용 옵션

- `?lang=ko` / `?lang=zh` / `?lang=en` — 언어를 URL로 고정 (시연·스크린샷용)
- `?modal=llm` — AI 모델 연결 창을 바로 열기
- 우측 상단 AI 버튼 — 실행 중 API 키 주입 (메모리에만 보관, 저장 안 함)

### 4.5 마감 알림 (관심 등록 → 자동 메일)

1. 왼쪽 `내 학적 조건` 에 **이메일**을 입력합니다(프로필에 저장됨).
2. 공지 상세에서 `알림 받기`(🔔)를 누르면 `data/subscriptions.json` 에 구독이 저장됩니다.
3. 서버가 5분마다 구독 목록을 확인해 **마감 24시간 전**이 되면 프로필 이메일로 알림을 발송합니다(`reminded_at` 기록으로 중복 발송 방지).
4. 데모에서는 `지금 테스트 발송` 버튼으로 즉시 확인할 수 있습니다.

```bash
GET  /api/subscriptions            # 구독 목록
POST /api/subscriptions            # {notice_id, subscribed}
POST /api/subscriptions/run        # {lang, force_ids?} 즉시 점검·발송
```

### 4.6 메일 발송 (SMTP)

`.env` 에 메일 계정을 넣으면 실제 발송이 켜집니다 (QQ메일은 **인증코드** 필요: 설정 → 계정 → POP3/SMTP 사용 → 인증코드 발급).

```ini
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your@qq.com
SMTP_AUTH_CODE=16자리인증코드
SMTP_FROM_NAME=ZeroNotice
```

- `GET /api/notify/status` — 설정 여부(비밀번호는 마스킹되어 반환)
- `POST /api/notify/notice`, `/api/notify/digest` — 수동 발송(데모 보조)
- `POST /api/notify/notice` — 특정 공지 1건을 `.ics` 첨부로 발송
- `POST /api/notify/digest` — 마감 임박 N건을 한 번에 발송(공지별 `.ics` 첨부)
- UI: 상세 페이지 `캘린더 구독` 카드에 이메일 입력 → `저장하고 받기`

> 자격증명은 `.env`(gitignore)에만 두고 절대 커밋하지 않습니다. 대회 종료 후 인증코드는 재발급하세요.

### 4.4 AI 모델 연결 (OpenRouter · OpenAI 호환)

| 제공자 | Base URL | 비고 |
|---|---|---|
| **OpenRouter** | `https://openrouter.ai/api/v1` | `:free` 모델은 무료. 키: <https://openrouter.ai/keys> |
| **OpenAI** | `https://api.openai.com/v1` | 유료. 키: <https://platform.openai.com/api-keys> |
| **DeepSeek** | `https://api.deepseek.com` | `deepseek-flash` / `deepseek-v4-pro`. 키: <https://platform.deepseek.com/api_keys> |
| **Groq** | `https://api.groq.com/openai/v1` | 무료 쿼터. 키: <https://console.groq.com/keys> |
| **Custom** | 직접 입력 | 사내/로컬 OpenAI 호환 엔드포인트(vLLM, Ollama, LM Studio 등) |

세 가지 설정 방법 중 아무거나:

1. **`.env`** — `LLM_PROVIDER` / `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` (서버 재시작 필요)
2. **웹 UI** — 우측 상단 AI 버튼 → 제공자 선택 → 키 입력 → `모델 목록 불러오기` → 모델 선택 → 저장 (재시작 불필요)
3. **기존 변수** — `GROQ_API_KEY` / `GROQ_MODEL` 도 그대로 인식합니다.

`LLM_MODEL` 을 비워 두면 제공자의 무료 모델 목록에서 첫 번째를 자동 선택합니다.

**문제 해결**

| 증상 | 원인 / 조치 |
|---|---|
| `engine` 이 `Built-in Template Engine` | 키 미설정, 401, 429. `/api/status` 의 `llm.configured` 확인 후 키 재입력 |
| 모델 목록이 비어 있음 | 제공자 `/models` 응답 실패. 모델 ID를 직접 입력 |
| 응답이 20초 이상 | 무료 모델 혼잡. 더 작은 모델로 변경 |

---

## 5. 데이터 신뢰성

- `data/real_knu_notices.json` 22건은 **강원대 홈페이지 원문에서 다시 받아온 본문·첨부**입니다. 각 항목에 `source_title`, `verified_at`, `source_status` 가 기록됩니다.
- 갱신: `python scripts/refresh_notices.py` (원문 제목 22/22 일치 확인)
- 신청 정보 추출 결과는 `data/notice_fields.json` 에, 포스터 OCR 결과는 `data/notice_images.json` 에 캐시됩니다.
- OCR은 Windows 내장 엔진을 쓰며, 이 PC에는 한국어 팩이 없어 한글은 깨지지만 **URL·이메일·전화번호(라틴/숫자)는 인식**됩니다. 그래서 OCR 결과에서 뽑은 링크는 반드시 HTTP로 검증한 뒤에만 노출합니다.
- **없는 정보는 만들지 않습니다.** 이메일이 없는 공고는 메일 발송 버튼이 나타나지 않고, 신청 링크가 없으면 링크 버튼이 없습니다.

---

## 6. 비용 산정 방식 (정직성 고지)

- 화면의 `saved_minutes` 는 **추정치**입니다: `clamp(본문글자수/350 + (HWP첨부 ? 3.5 : 1.0), 최소 2.0)`
- **실사용 측정은 아직 템플릿 상태**입니다. `data/user_logs.json` 은 빈 측정 슬롯이며, 절차는 [`docs/measurement-protocol.md`](docs/measurement-protocol.md) 에 있습니다.
- 발표에서는 "추정 공식"과 "실측값"을 섞지 않고 구분해서 제시합니다.

---

## 6.5 Supabase (공유 데이터 + 사용자별 데이터)

데스크톱(.exe/.dmg)으로 배포하면 **공지는 모두가 공유**하고, **프로필·구독·AI 키는 각자**여야 합니다. 그래서 두 층으로 나눴습니다.

| 층 | 테이블 | 접근 |
|---|---|---|
| 공유 | `notices`, `notice_fields`, `notice_images`, `attachments` | 누구나 읽기(anon), 쓰기는 service_role만 |
| 사용자별 | `profiles`, `subscriptions`, `user_settings` | RLS `auth.uid() = user_id` — 자기 행만 |

- 설치본은 **anon key만** 포함하고, 첫 실행 때 Supabase **익명 로그인**으로 `user_id`를 받아 `data/identity.json` 에 저장합니다. 남의 행은 RLS가 막습니다.
- `service_role` 키는 **절대 배포본에 넣지 않습니다.** 공지 동기화/파일 업로드는 `scripts/sync_supabase.py` 로 소유자 PC에서만 실행합니다.
- 30일 보관: `purge_expired_notices(30)` 함수 + 야간 cron(선택). 오래된 공지가 지워지면 첨부/추출 캐시도 cascade로 함께 정리됩니다.

```bash
# 1) Supabase SQL editor 에 supabase/schema.sql 실행
# 2) Authentication → Providers → Anonymous sign-ins 활성화
# 3) .env 에 SUPABASE_URL / SUPABASE_ANON_KEY / SUPABASE_SERVICE_KEY 입력
python scripts/sync_supabase.py --purge     # 공지·첨부 업로드 + 30일 정리
```

첨부 파일은 Storage 버킷 `attachments/<notice_id>/<filename>` 에 올라가고, 공개 URL로 렌더링됩니다.

## 6.6 AI 비서 (플로팅 에이전트)

`assistant.py` 는 DeepSeek function calling 으로 아래 도구를 직접 실행합니다.

| 도구 | 하는 일 |
|---|---|
| `search_notices` | 키워드/카테고리/마감일/자격으로 검색 |
| `get_notice` | 마감·자격·신청 링크·접수 방법·제출 서류 |
| `list_upcoming` | N일 내 마감 목록 |
| `subscribe_notice` | 관심 등록/해제(마감 24시간 전 메일) |
| `list_subscriptions` | 내 구독 목록 |
| `draft_inquiry_email` / `send_inquiry_email` | 문의 메일 초안 / 실제 발송 |
| `get_my_profile` | 내 학적 정보 |

- 대화 기록은 `data/chat_history.json`(로컬) + Supabase `assistant_messages`(로그인/디바이스 모드)에 저장
- UI: 우측 하단 플로팅 볼 → 패널. `?chat=1` 로 바로 열 수 있음
- API: `POST /api/assistant/chat`, `GET/DELETE /api/assistant/history`

## 7. 프로젝트 구조

```
app.py            FastAPI 라우팅(7 endpoint) + 정적 서빙
agent.py          Groq 호출, 자격 판정 규칙, .ics/메일/지원서 생성, 비용 추정
scraper.py        게시판 상세 파싱, .hwp/.hwpx 추출, 데이터 로드
data/             real_knu_notices.json(22건) · fallback · user_logs 템플릿
frontend/         React 소스 + dist(빌드 산출물, 커밋됨)
static/           구 버전 단일 파일 UI (dist 없을 때 폴백)
docs/             측정 프로토콜\nscripts/          refresh_notices.py (원문 재수집)
AGENTS.md         개발 규칙·디자인 시스템·API 계약
```

---

## 8. 데이터 출처

- 공지 원문: `kangwon.ac.kr/ko/bbs/...` 공개 게시판 (2026-11-05 스냅샷). 각 공지의 `url` 필드에 원문 링크 유지
- 개인정보는 수집·저장하지 않습니다. API 키는 `.env` 에만 두며 저장소에 포함하지 않습니다.
