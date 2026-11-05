# AGENTS.md — ZeroNotice (제로노티스)

강원대학교(KNU) 공지 탐색·`.hwp` 첨부 열람·자격 판정·행정 문의/지원서 작성을 대신하는 AI 비서.
**2026 KNU AI HACKATHON "Zero to One"** 출품작. 주제: 캠퍼스의 "숨은 비용(시간·에너지·금전·불안)"을 AI로 0에 가깝게.

> 이 파일은 에이전트/협업자를 위한 프로젝트 메모리다. 저장소 상태가 바뀌면 갱신할 것.
> 마지막 갱신: 2026-11-05 20:20 (HEAD `39a9b85`)

---

## 1. 하드 데드라인 (가장 중요)

| 항목 | 값 |
|---|---|
| 제출 마감 | **2026-11-06 11:30** (이후 제출은 심사 제외) |
| 발표·심사 | 11-06 12:00–14:00, 팀당 展示 + Q&A |
| 코드 동결 | 11-06 10:30 이후 커밋 금지 (데모 리스크 관리) |
| 제출물 | GitHub 링크(또는 zip) + PPT/PDF + 배포 URL(권장) |
| 금지 | 17:00 이전 작성 코드 반입, 대회 중 사전 작성 코드 사용, 타인 결과물 표절 |

배점: 문제정의 20 / 구현완성도 30 / 창의성 20 / 실용성·확장성 15 / 발표·협업 15.
**"비용이 실제로 줄었다는 증명"이 문제의 핵심** — 데모만으로는 부족하고 before/after 수치가 필요하다.

---

## 2. 실행 방법

```bash
# 백엔드 (Python 3.11+; 이 PC에서는 C:\Python314\python.exe 에 의존성 설치됨)
pip install -r requirements.txt
cp .env.example .env          # GROQ_API_KEY 입력 (또는 웹 UI 상단 "Groq API" 버튼)
python app.py                 # http://127.0.0.1:8000

# 프론트엔드 개발 서버 (HMR, /api → 8000 프록시)
cd frontend && npm install && npm run dev    # http://localhost:5173

# 단일 포트 배포용: 빌드 산출물을 FastAPI가 그대로 서빙
cd frontend && npm run build                 # → frontend/dist
python app.py                                # / 가 dist/index.html 로 서빙됨
```

- `app.py`는 `frontend/dist/index.html`이 있으면 그것을, 없으면 `static/index.html`(구 버전 단일 파일 UI)을 서빙한다.
- DSH 번들 Python에는 fastapi/uvicorn이 **없다**. 시스템 Python(`C:\Python314`)을 쓸 것.

---

## 3. 구조

```
app.py                  FastAPI 라우팅(7 endpoint) + 정적 서빙
agent.py                Groq 호출, 자격 판정 규칙, .ics/메일/지원서 생성, 비용 추정
scraper.py              게시판 상세 파싱, .hwp/.hwpx 텍스트 추출, 데이터 로드
data/real_knu_notices.json    실제 공지 22건 (수동/스크립트 수집 스냅샷)
data/fallback_notices.json   오프라인 데모용 대체 데이터
data/user_logs.json          사용 기록 8건 — 코드에서 참조되지 않음(발표 자료용)
frontend/src/           React 18 + Vite 5 + Tailwind + lucide-react
  App.jsx               3-pane 워크스페이스, /api/notices 호출, localStorage 상태
  components/           TopNavbar / SidebarFilter / NoticeListPane / NoticeDetailPane / Modals
  i18n/                 KO·ZH·EN 문자열
static/index.html       구 버전 단일 파일 UI (dist 없을 때 폴백)
```

---

## 4. API 계약

프로필(모든 곳에서 동일):

```json
{"campus":"춘천","status":"undergrad_kr","department":"첨단AI공학부","grade":3,
 "gpa":3.8,"income_bracket":3,"name":"김강원","student_id":"202411234","live_check":false}
```

| Method | Path | Body | 응답 핵심 |
|---|---|---|---|
| GET | `/api/status` | – | `{status, groq:{configured,model}, time}` |
| POST | `/api/config/groq` | `{api_key, model}` | 런타임 키 주입(메모리만, 저장 안 함) |
| POST | `/api/notices` | 프로필 | `{synced_at, live_portal_connected, notices[], stats}` |
| GET | `/api/agent/ics/{notice_id}?lang=` | – | `text/calendar` 파일 |
| POST | `/api/agent/email` | `{notice_id, profile, custom_question, lang}` | `{department,email,phone,subject,body,engine}` |
| POST | `/api/agent/application` | `{notice_id, profile, lang}` | `{notice_title, draft, attachments, engine}` |
| POST | `/api/parse-url` | `{url_or_text, profile, lang}` | `{extracted, analysis, engine}` — 임의 URL/텍스트 분석 |

`stats` = `{total, eligible, conditional, ineligible, saved_minutes, hwp_parsed_count}`.

---

## 5. 데이터 모델 (`data/real_knu_notices.json`, 22건)

필드: `id, category, campus, title, author, posted_date, phone, email, url, body, char_count,
attachments[], attachment_extracted_text, deadline("YYYY-MM-DD HH:MM"), benefit_label_{ko,zh,en},
benefit_krw, title_{ko,zh,en}, summary_{ko,zh,en}, rules, has_hwp_extracted`

`rules` = `{campuses[], status_allowed[], min_gpa, max_income, note_ko, note_zh, note_en}`
- `status_allowed` 값: `undergrad_kr` | `intl` | `leave_grad` | `staff_citizen`
- 22건 전부 `rules` 보유, 7건 HWP 본문 추출 완료, 7건 담당자 이메일 보유

---

## 6. 구현 규칙 (깨면 심사에서 바로 티난다)

1. **자격 판정은 LLM이 아니라 코드로.** `agent.evaluate_real_notice()`의 규칙 비교가 유일한 판정 근거. LLM은 요약/작문만.
2. **3개 언어 필드 동시 유지**: `verdict_{ko,zh,en}`, `title_*`, `summary_*`. 새 공지 추가 시 3개 언어 모두 채울 것.
3. **키는 절대 커밋 금지.** `.env`는 gitignore 처리됨. `RUNTIME_CONFIG`는 메모리만, 재시작 시 소실.
4. **LLM 실패 시 폴백 필수.** `call_groq_llm()`이 `ok:False`면 템플릿 문구로 대체하고 `engine` 필드에 실제 엔진을 표기한다(데모 중 거짓 표기 금지).
5. **비용 수치의 출처를 밝힐 것.** `saved_minutes = clamp(chars/350 + (hwp?3.5:1.0), min 2.0)` — 공지당 **추정치**다. 발표에서는 "추정 공식"임을 명시하고, 실측(사용자 타이머)과 섞지 말 것.

---

## 7. 현재 알려진 문제 (우선순위 순)

| P | 문제 | 근거/영향 |
|---|---|---|
| P0 | `GROQ_API_KEY` 비어 있음 → 메일/지원서/요약이 전부 템플릿 폴백 | `.env` 확인. "AI가 실제로 생성" 데모가 무너짐 |
| P0 | `data/user_logs.json` 8건이 전부 동일 타임스탬프·동일 수치(120.8분/₩4,180,000)·`Guest User` | 실제 사용 기록으로 오인되면 표절/조작 리스크. 실측으로 교체하거나 "가상 시나리오"로 명시 |
| P0 | README의 "실시간 연동"은 과장 — `sync_live_knu_notices()`는 게시판 접속 여부만 확인하고 **정적 JSON을 반환** | 교수 심사위원이 "새 공지가 올라오면?" 질문 시 방어 필요 |
| P1 | 배포 URL 없음(localhost만) | 제출 권장 항목, 데모 리스크 |
| P1 | `frontend/dist`가 소스와 어긋날 수 있음 | 코드 수정 후 `npm run build` 필수 |
| P2 | `Real_time_translation.npm-cache/` 미추적 디렉터리 | 저장소 청결도. gitignore 추가 권장 |

---

## 8. 협업 주의

- 이 저장소는 **여러 세션이 동시에 편집**한 이력이 있다(19:17 초기 릴리스 → 19:57 React 마이그레이션). 커밋 전 `git status` / `git diff` 확인.
- `deck.pdf`, `deck.txt`, `.tmp/`, `.tools/`는 분석용 부산물이며 gitignore 대상. 제출물에 포함하지 말 것.
- UI 문구는 한국어 우선, 중국어/영어 병기. 새 문자열은 `frontend/src/i18n/`에만 추가하고 컴포넌트에 하드코딩하지 말 것.

---

## 9. UI 디자인 시스템 (2026-11-05 重构)

`tailwind.config.js` + `frontend/src/index.css` 에 정의된 토큰만 사용한다. 임의의 `zinc-*`, `text-[13px]`, `rounded-xl` 같은 값을 새로 만들지 말 것.

**색**: `ink`(#0b0b0f 主文字) · `muted`(#6f6f78 次文字) · `faint`(#a1a1aa 元信息) · `line`(#ededf0 唯一描边色) · `canvas`(#fafafa 面板底) · `accent.soft`(#f4f4f5 浅底)。语义色只用于状态：emerald=可申请, amber=需确认, zinc=不符合。

**字号**（全部走 scale，禁止任意值）: `text-meta` 11 / `text-label` 12 / `text-body` 13 / `text-title` 14 / `text-h3` 16 / `text-h1` 20。正文行高 20/24，长文 28。

**圆角**: `rounded-card` 14（卡片）/ `rounded-control` 10（输入框、按钮）/ `rounded-chip` 8（小标签）。

**复用的组件类**（`index.css` 的 `@layer components`）
- `.field` — 输入框/下拉，h-9 + 1px `line` 描边
- `.seg` / `.seg-item` / `.seg-item-active` — 分段控件（进度、语言切换）
- `.icon-btn` — 32×32 图标按钮
- `.hairline` — 单线分隔

**布局契约**
| 区域 | 宽度 | 说明 |
|---|---|---|
| TopNavbar | h-14 | 左侧品牌+同步状态，右侧「省时」胶囊、URL 按钮、Groq、语言 |
| SidebarFilter | 248px（≥1120px 才显示） | 板块导航 / 资格开关 / 学籍条件 |
| NoticeListPane | 340px（≥1280px 为 420px） | 搜索 + 子筛选 + 列表 |
| NoticeDetailPane | 自适应，内容 `max-w-[860px] px-7` | 粘性头部 + 4 个 tab + 内容 |

**三条硬规则**
1. 嵌套卡片最多一层：不要再给「卡片里的卡片」加描边，用 `divide-y divide-line` 或留白分隔。
2. 一个页面只有一个强调色（`ink`）。状态色只出现在 11px 的圆点/文字上，不做大面积填充。
3. 数字一律 `tabular-nums`；D-day 只出现一次（详情页判定卡右上角）。

