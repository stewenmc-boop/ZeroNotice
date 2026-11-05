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
8. **목록 필터** — `신청 링크만` / `지원 가능` / `HWP 파싱` 칩으로 바로 걸러볼 수 있고, 검색은 추출된 신청정보까지 대상입니다

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
