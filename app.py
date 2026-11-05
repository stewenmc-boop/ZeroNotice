import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import (
    call_llm,
    filter_and_evaluate_notices,
    generate_application_draft_agent,
    generate_ics_content,
    generate_polite_email_agent,
    get_llm_status,
    list_models,
    set_runtime_llm,
)
from scraper import (
    load_real_knu_notices,
    parse_knu_detail_url,
    sync_live_knu_notices,
)

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"

app = FastAPI(title="ZeroNotice (제로노티스) — 강원대학교 공지·HWP 판독 AI 비서")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProfileRequest(BaseModel):
    campus: str = "춘천"
    status: str = "undergrad_kr"  # undergrad_kr | intl | leave_grad | staff_citizen
    department: str = "첨단AI공학부"
    grade: int = 3
    gpa: float = 3.8
    income_bracket: int = 3
    name: str = "김강원"
    student_id: str = "202411234"
    live_check: bool = False


class ActionRequest(BaseModel):
    notice_id: str
    profile: ProfileRequest
    custom_question: Optional[str] = ""
    lang: str = "ko"


class ParseUrlRequest(BaseModel):
    url_or_text: str
    profile: ProfileRequest
    lang: str = "ko"


class LlmConfigRequest(BaseModel):
    api_key: Optional[str] = ""
    model: Optional[str] = ""
    provider: Optional[str] = ""
    base_url: Optional[str] = ""


@app.get("/api/status")
def api_status() -> Dict[str, Any]:
    llm = get_llm_status()
    return {
        "status": "ok",
        "llm": llm,
        "groq": llm,  # backward compatibility for older UI builds
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


@app.post("/api/config/llm")
def api_set_llm(req: LlmConfigRequest) -> Dict[str, Any]:
    status = set_runtime_llm(
        api_key=req.api_key or None,
        model=req.model or None,
        provider=req.provider or None,
        base_url=req.base_url or None,
    )
    return {"status": "updated", "llm": status, "groq": status}


@app.post("/api/config/groq")
def api_set_groq(req: LlmConfigRequest) -> Dict[str, Any]:
    # legacy endpoint kept so old clients keep working
    return api_set_llm(req)


@app.get("/api/llm/models")
def api_llm_models(provider: str = Query(""), free_only: bool = Query(True)) -> Dict[str, Any]:
    return list_models(provider=provider or None, free_only=free_only)


@app.post("/api/notices")
def api_get_notices(req: ProfileRequest) -> Dict[str, Any]:
    sync_res = sync_live_knu_notices(live_check=req.live_check)
    profile_dict = req.model_dump()
    evaluated = filter_and_evaluate_notices(sync_res["notices"], profile_dict)
    return {
        "synced_at": sync_res["synced_at"],
        "live_portal_connected": sync_res["live_portal_connected"],
        "llm": get_llm_status(),
        "groq": get_llm_status(),
        **evaluated,
    }


@app.get("/api/agent/ics/{notice_id}")
def api_download_ics(notice_id: str, lang: str = Query("ko")) -> Response:
    notices = load_real_knu_notices()
    target = next((n for n in notices if n.get("id") == notice_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Notice not found")
    ics_text = generate_ics_content(target, lang=lang)
    return Response(
        content=ics_text.encode("utf-8"),
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{notice_id}_deadline.ics"'
        },
    )


@app.post("/api/agent/email")
def api_generate_email(req: ActionRequest) -> Dict[str, Any]:
    notices = load_real_knu_notices()
    target = next((n for n in notices if n.get("id") == req.notice_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Notice not found")
    return generate_polite_email_agent(
        target, req.profile.model_dump(), req.custom_question or ""
    )


@app.post("/api/agent/application")
def api_generate_application(req: ActionRequest) -> Dict[str, Any]:
    notices = load_real_knu_notices()
    target = next((n for n in notices if n.get("id") == req.notice_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Notice not found")
    return generate_application_draft_agent(target, req.profile.model_dump())


@app.post("/api/parse-url")
def api_parse_live_url(req: ParseUrlRequest) -> Dict[str, Any]:
    raw = req.url_or_text.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty input")

    extracted_info = {}
    if raw.startswith("http") and "kangwon.ac.kr" in raw:
        try:
            extracted_info = parse_knu_detail_url(raw)
            content_to_analyze = (
                f"제목: {extracted_info.get('title', '')}\n"
                f"본문:\n{extracted_info.get('body', '')}\n"
                f"첨부파일 추출 원문:\n{extracted_info.get('attachment_extracted_text', '')}"
            )
        except Exception as e:
            content_to_analyze = f"URL 로드 실패 ({e}). 입력값: {raw}"
    else:
        content_to_analyze = raw

    p = req.profile
    sys_prompt = (
        "당신은 강원대학교 공지사항 및 HWP 첨부파일 분석 비서입니다. "
        "주어진 공고 내용을 읽고 사용자의 학적 조건과 대조하여: "
        "1) 지원 가능 여부 (한 줄 결론), 2) 핵심 자격요건 및 제외대상, 3) 마감일 및 제출방법, 4) 중국어/한국어 요약 브리핑을 간결하게 출력하세요."
    )
    user_prompt = (
        f"[내 조건] {p.campus}캠퍼스 / {p.status} / {p.department} {p.grade}학년 / GPA {p.gpa} / 소득 {p.income_bracket}구간\n\n"
        f"[공고 내용]\n{content_to_analyze[:3000]}"
    )
    llm_res = call_llm(sys_prompt, user_prompt, temperature=0.2, max_tokens=700)
    if llm_res["ok"] and len(llm_res["text"]) > 40:
        summary = llm_res["text"]
        engine = llm_res["engine"]
    else:
        summary = (
            f"✓ 분석 완료 (원문 {len(content_to_analyze)}자 판독)\n"
            f"• 내 조건({p.campus}캠퍼스, GPA {p.gpa}, 소득 {p.income_bracket}구간) 기준 지원 자격 및 마감일을 확인하세요.\n"
            + (
                f"• 추출된 첨부파일 수: {len(extracted_info.get('attachments', []))}개"
                if extracted_info
                else ""
            )
        )
        engine = "Built-in Parser"

    return {
        "extracted": extracted_info,
        "analysis": summary,
        "engine": engine,
    }


if (FRONTEND_DIST_DIR / "assets").exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_DIST_DIR / "assets")),
        name="assets",
    )

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def serve_index() -> FileResponse:
    dist_index = FRONTEND_DIST_DIR / "index.html"
    if dist_index.exists():
        return FileResponse(str(dist_index))
    return FileResponse(str(STATIC_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app:app", host="127.0.0.1", port=port, reload=False)
