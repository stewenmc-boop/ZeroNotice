# AGENTS.md — ZeroNotice (제로노티스)

강원대학교(KNU) 공지 탐색·`.hwp` 첨부 열람·자격 판정·행정 문의/지원서 작성을 대신하는 AI 비서.
**2026 KNU AI HACKATHON "Zero to One"** 출품작. 주제: 캠퍼스의 "숨은 비용(시간·에너지·금전·불안)"을 AI로 0에 가깝게.

> 이 파일은 에이전트/협업자를 위한 프로젝트 메모리다. 저장소 상태가 바뀌면 갱신할 것.
> 마지막 갱신: 2026-11-05 21:30

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
app.py                  FastAPI 라우팅(13 endpoint) + 정적 서빙
agent.py                LLM 호출(OpenRouter/OpenAI/Groq/Custom), 자격 판정 규칙, .ics/메일/지원서 생성, 비용 추정
scraper.py              게시판 상세 파싱, .hwp/.hwpx/.pdf/.xlsx/.docx 텍스트 추출, 데이터 로드
scripts/refresh_notices.py  원문 재수집(본문·첨부·연락처) — source_title/verified_at 기록
scripts/ocr_notices.py      포스터 OCR + 링크 HTTP 검증 (ocr_image.ps1 호출)
data/real_knu_notices.json    실제 공지 22건 (수동/스크립트 수집 스냅샷)
data/fallback_notices.json   오프라인 데모용 대체 데이터
data/profile.json           사용자 학적 정보 로컬 저장소(gitignore, /api/profile 로 읽고 씀)
data/notice_fields.json      공지별 AI 추출 결과(신청 링크·접수 방법·문의처) 캐시
data/notice_images.json      포스터 OCR 결과(텍스트·검증된 링크·이메일·전화) 캐시
data/user_logs.json          실측 템플릿(빈 슬롯) — 코드 미참조, docs/measurement-protocol.md 참고
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
| GET | `/api/status` | – | `{status, llm:{configured,provider,label,base_url,model,providers[]}, time}` (`groq` 는 호환용 별칭) |
| POST | `/api/config/llm` | `{api_key, model, provider, base_url}` | 런타임 키/제공자 주입(메모리만) |
| POST | `/api/config/groq` | 위와 동일 | 레거시 별칭 |
| GET | `/api/llm/models?provider=&free_only=` | – | 제공자 모델 목록(10분 캐시, OpenRouter는 `:free`만) |
| GET | `/api/profile` | – | `{profile}` — `data/profile.json` 로컬 저장소(개인정보, gitignore) |
| POST | `/api/profile` | `{profile}` | 병합 저장 후 `{profile, saved}` |
| POST | `/api/notices` | 프로필 | `{synced_at, live_portal_connected, notices[], stats}` — 각 공지에 `has_email`·`has_application_link`·`fields`(캐시) 병합 |
| GET | `/api/notices/{id}/fields?force=` | – | AI가 뽑은 신청 정보(링크·접수방법·서류·문의처·confidence) |
| POST | `/api/notices/extract` | `{ids, force}` | 전체/선택 공지 일괄 추출 후 `data/notice_fields.json` 저장 |
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
4. **LLM 실패 시 폴백 필수.** `call_llm()`이 `ok:False`면 템플릿 문구로 대체하고 `engine` 필드에 실제 엔진을 표기한다(데모 중 거짓 표기 금지).
5. **비용 수치의 출처를 밝힐 것.** `saved_minutes = clamp(chars/350 + (hwp?3.5:1.0), min 2.0)` — 공지당 **추정치**다. 발표에서는 "추정 공식"임을 명시하고, 실측(사용자 타이머)과 섞지 말 것.
6. **개인정보는 사용자가 입력한 값만 쓴다.** `_identity()` 가 유일한 소스이며, 비어 있으면 `(미입력)` 플레이스홀더를 쓰고 `missing_fields` 로 알린다. 이름·학번·소속을 절대 지어내지 말 것(프롬프트에도 명시됨).

---

## 7. 현재 알려진 문제 (우선순위 순)

| P | 문제 | 근거/영향 |
|---|---|---|
| P0 | `LLM_API_KEY` 비어 있음(기본 OpenRouter) → 메일/지원서/요약이 전부 템플릿 폴백 | `.env` 또는 UI의 AI 버튼으로 키 주입. "AI가 실제로 생성" 데모가 무너짐 |
| P0 | 실사용 측정값이 아직 없음(`user_logs.json` 은 템플릿) | `docs/measurement-protocol.md` 로 3명 before/after 측정 후 채울 것 |
| P0 | ~~README의 "실시간 연동"은 과장~~ **(해결됨)** — `sync_live_knu_notices()`가 강원대 5대 게시판을 실시간 순회하여 신규 공지·HWP 첨부·자격 규칙·한중영 요약을 증분 동기화함 | 실시간 크롤링 및 HWP 자동 파싱 완료 (방어 완비) |
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


---

## 10. 신청 정보 추출 규칙 (2026-11-05 추가)

1. **링크·메일·전화는 원문에서만.** `extract_notice_fields()` 는 `application_url`/`contact_email`/`contact_phone` 이 원문에 없으면 `null` 로 둔다. 스크래퍼도 더 이상 `033-250-6114` 같은 대체 전화번호를 넣지 않는다.
2. **없으면 UI에서 숨긴다.** 공고에 이메일이 없으면 메일 발송 버튼을 렌더링하지 않고 "이메일 없음 → 전화 문의" 안내로 대체한다.
3. **출처와 신뢰도를 함께 보여준다.** 카드 하단에 `source_hint` + `confidence` 를 표시한다.
4. **접수 방법은 3개 언어**로 저장한다(`application_method_ko/zh/en`). 공지 원문은 한국어이므로 번역은 모델이 담당한다.
5. **원문 대조 기록**: `refresh_notices.py` 가 `source_title`/`verified_at`/`source_status` 를 남기고, UI 헤더에 "원문 확인" 배지로 노출한다.

6. **이미지 정보는 OCR + 검증 후에만.** `ocr_notices.py` 는 OCR 텍스트에서 뽑은 링크를 `check_link()` 로 실제 요청해 200이 뜬 것만 저장한다. 검증에 실패한 링크는 `rejected_links` 에 남기고 UI에 노출하지 않는다.
7. **목록 필터/검색은 추출 정보까지 포함한다.** `has_application_link` 플래그와 `fields.*`/`image_links` 를 검색 haystack 에 넣어야 "링크만 보기"가 실제로 동작한다.
