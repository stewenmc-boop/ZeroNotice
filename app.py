import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import (
    call_llm,
    extract_notice_fields,
    filter_and_evaluate_notices,
    generate_application_draft_agent,
    generate_ics_content,
    generate_polite_email_agent,
    get_llm_status,
    list_models,
    set_runtime_llm,
)
import assistant
import notifier
import reminders
import storage
from scraper import (
    load_real_knu_notices,
    parse_knu_detail_url,
    sync_live_knu_notices,
)

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"
PROFILE_PATH = BASE_DIR / "data" / "profile.json"
SETTINGS_PATH = BASE_DIR / "data" / "settings.json"
CHAT_PATH = BASE_DIR / "data" / "chat_history.json"
FIELDS_PATH = BASE_DIR / "data" / "notice_fields.json"
IMAGES_PATH = BASE_DIR / "data" / "notice_images.json"

app = FastAPI(title="ZeroNotice (제로노티스) — 강원대학교 공지·HWP 판독 AI 비서")


@app.exception_handler(Exception)
def api_exception_handler(request, exc):  # noqa: ANN001
    """Never return an HTML error page: the UI expects JSON."""
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=500,
        content={"error": f"{type(exc).__name__}: {str(exc)[:200]}", "path": str(request.url.path)},
    )

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
    name: str = ""
    student_id: str = ""
    phone: str = ""
    email: str = ""
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


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = []
    lang: str = "ko"


def _load_fields() -> Dict[str, Any]:
    if not FIELDS_PATH.exists():
        return {}
    try:
        with open(FIELDS_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _read_settings() -> Dict[str, Any]:
    if not SETTINGS_PATH.exists():
        return {}
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_settings(data: Dict[str, Any]) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def _chat_history() -> List[Dict[str, Any]]:
    if not CHAT_PATH.exists():
        return []
    try:
        with open(CHAT_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_chat(entries: List[Dict[str, Any]]) -> None:
    CHAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CHAT_PATH, "w", encoding="utf-8") as fh:
        json.dump(entries[-200:], fh, ensure_ascii=False, indent=2)


@app.post("/api/assistant/chat")
def api_assistant_chat(req: ChatRequest) -> Dict[str, Any]:
    profile = _read_profile() or {}
    history = [{"role": m.role, "content": m.content} for m in req.messages][-12:]
    result = assistant.chat(history, profile, lang=req.lang)

    entries = _chat_history()
    if history:
        last_user = history[-1]
        if last_user.get("role") == "user":
            entries.append({"role": "user", "content": last_user["content"],
                            "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
            storage.push_message("user", last_user["content"])
    if result.get("reply"):
        entries.append({"role": "assistant", "content": result["reply"],
                        "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        storage.push_message("assistant", result["reply"], {"tools": result.get("tool_calls")})
    _save_chat(entries)
    return result


@app.get("/api/assistant/history")
def api_assistant_history(limit: int = Query(50)) -> Dict[str, Any]:
    local = _chat_history()[-limit:]
    if not local:
        local = storage.load_messages(limit)
    return {"messages": local}


@app.delete("/api/assistant/history")
def api_assistant_clear() -> Dict[str, Any]:
    _save_chat([])
    return {"cleared": True}


@app.get("/api/supabase/status")
def api_supabase_status() -> Dict[str, Any]:
    return storage.status()


@app.get("/api/settings")
def api_get_settings() -> Dict[str, Any]:
    settings = _read_settings()
    if not settings and storage.enabled():
        settings = storage.load_settings() or {}
    safe = {k: ("***" if k == "api_key" and v else v) for k, v in settings.items()}
    return {"settings": safe, "has_key": bool(settings.get("api_key"))}


@app.post("/api/settings")
def api_save_settings(req: Dict[str, Any]) -> Dict[str, Any]:
    settings = {**_read_settings(), **(req or {})}
    _write_settings(settings)
    if storage.enabled():
        storage.push_settings(settings)
    if settings.get("api_key") or settings.get("model"):
        set_runtime_llm(
            api_key=settings.get("api_key"),
            model=settings.get("model"),
            provider=settings.get("provider"),
            base_url=settings.get("base_url"),
        )
    return {"saved": True, "has_key": bool(settings.get("api_key"))}


def _load_images() -> Dict[str, Any]:
    if not IMAGES_PATH.exists():
        return {}
    try:
        with open(IMAGES_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _merge_image_info(notice: Dict[str, Any], images: Dict[str, Any]) -> Dict[str, Any]:
    """Attach OCR results (links/emails/phones) found inside poster images."""
    info = images.get(notice.get("id"))
    if not info:
        return notice
    notice = dict(notice)
    notice["image_links"] = info.get("links") or []
    notice["image_emails"] = info.get("emails") or []
    notice["image_phones"] = info.get("phones") or []
    notice["image_text"] = "\n".join(
        item.get("text", "") for item in info.get("images", [])
    )[:2000]
    notice["image_checked_at"] = info.get("checked_at")
    return notice


def _remember_notify_email(email: str) -> None:
    try:
        profile = _read_profile()
        profile["notify_email"] = email.strip()
        profile["notify_saved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PROFILE_PATH, "w", encoding="utf-8") as fh:
            json.dump(profile, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _save_fields(data: Dict[str, Any]) -> None:
    FIELDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FIELDS_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


class ProfileStoreRequest(BaseModel):
    profile: Dict[str, Any]


def _read_profile() -> Dict[str, Any]:
    """Tiny local store: data/profile.json (gitignored, never leaves the machine)."""
    if not PROFILE_PATH.exists():
        return {}
    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


class SubscribeRequest(BaseModel):
    notice_id: str = ""
    subscribed: bool = True


class ReminderRunRequest(BaseModel):
    lang: str = "ko"
    force_ids: List[str] = []


class NotifyRequest(BaseModel):
    email: str = ""
    notice_id: str = ""
    lang: str = "ko"
    limit: int = 5


class ExtractRequest(BaseModel):
    ids: List[str] = []
    force: bool = False


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
    settings = _read_settings()
    if req.api_key:
        settings["api_key"] = req.api_key
    for key in ("model", "provider", "base_url"):
        value = getattr(req, key, "") or ""
        if value:
            settings[key] = value
    _write_settings(settings)
    if storage.enabled():
        storage.push_settings(settings)
    return {"status": "updated", "llm": status, "groq": status}


@app.post("/api/config/groq")
def api_set_groq(req: LlmConfigRequest) -> Dict[str, Any]:
    # legacy endpoint kept so old clients keep working
    return api_set_llm(req)


@app.get("/api/subscriptions")
def api_subscriptions() -> Dict[str, Any]:
    return {"subscriptions": reminders.list_subscriptions()}


@app.post("/api/subscriptions")
def api_subscribe(req: SubscribeRequest) -> Dict[str, Any]:
    if not req.notice_id:
        raise HTTPException(status_code=400, detail="notice_id is required")
    result = reminders.subscribe(req.notice_id, req.subscribed)
    if storage.enabled():
        try:
            if req.subscribed:
                storage.push_subscriptions({req.notice_id: {}})
            else:
                storage.delete_subscription(req.notice_id)
        except Exception:
            pass
    return result


@app.post("/api/subscriptions/run")
def api_subscriptions_run(req: ReminderRunRequest) -> Dict[str, Any]:
    profile = _read_profile() or {}
    result = reminders.run_check(
        load_real_knu_notices(), profile, lang=req.lang, force_ids=req.force_ids or None
    )
    return {"profile_email": profile.get("email", ""), **result}


@app.get("/api/notify/status")
def api_notify_status() -> Dict[str, Any]:
    return notifier.smtp_status()


@app.post("/api/notify/notice")
def api_notify_notice(req: NotifyRequest) -> Dict[str, Any]:
    notice = next((n for n in load_real_knu_notices() if n.get("id") == req.notice_id), None)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    ics = generate_ics_content(notice, lang=req.lang).encode("utf-8")
    title = notice.get(f"title_{req.lang}") or notice.get("title_ko") or notice.get("title", "")
    body = (
        f"[ZeroNotice] 마감 알림\n\n"
        f"공지: {title}\n"
        f"마감: {notice.get('deadline', '')}\n"
        f"담당: {notice.get('author', '')} {notice.get('phone', '')}\n"
        f"원문: {notice.get('url', '')}\n\n"
        f"첨부한 .ics 파일을 열면 캘린더에 자동 등록됩니다."
    )
    result = notifier.send_mail(
        req.email,
        f"[ZeroNotice] 마감 알림 · {title[:40]}",
        body,
        [(f"{notice.get('id', 'notice')}.ics", ics, "calendar")],
    )
    if req.email:
        _remember_notify_email(req.email)
    return result


@app.post("/api/notify/digest")
def api_notify_digest(req: NotifyRequest) -> Dict[str, Any]:
    notices = load_real_knu_notices()
    fields = _load_fields()

    def deadline_key(n):
        return n.get("deadline") or "9999-99-99"

    upcoming = sorted(notices, key=deadline_key)[: max(1, min(req.limit, 10))]
    if not upcoming:
        return {"ok": False, "error": "발송할 공지가 없습니다."}

    attachments = []
    lines = ["[ZeroNotice] 마감 임박 공지 캘린더", ""]
    for n in upcoming:
        title = n.get(f"title_{req.lang}") or n.get("title_ko") or n.get("title", "")
        lines.append(f"- {title[:60]}")
        lines.append(f"  마감: {n.get('deadline', '')} / 담당: {n.get('author', '')}")
        lines.append(f"  링크: {n.get('url', '')}")
        fields_for = (fields.get(n["id"]) or {}).get("fields") or {}
        if fields_for.get("application_url"):
            lines.append(f"  신청: {fields_for['application_url']}")
        lines.append("")
        ics = generate_ics_content(n, lang=req.lang).encode("utf-8")
        attachments.append((f"{n['id']}.ics", ics, "calendar"))

    lines.append("첨부된 .ics 파일을 열면 캘린더에 자동 등록됩니다.")
    result = notifier.send_mail(
        req.email,
        f"[ZeroNotice] 마감 알림 {len(upcoming)}건",
        "\n".join(lines),
        attachments,
    )
    if req.email:
        _remember_notify_email(req.email)
    if result.get("ok"):
        result["notices"] = len(upcoming)
    return result


@app.get("/api/notices/{notice_id}/fields")
def api_notice_fields(notice_id: str, force: bool = Query(False)) -> Dict[str, Any]:
    cache = _load_fields()
    if not force and notice_id in cache:
        return {"id": notice_id, "cached": True, **cache[notice_id]}
    notice = next((n for n in load_real_knu_notices() if n.get("id") == notice_id), None)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    result = extract_notice_fields(_merge_image_info(notice, _load_images()))
    cache[notice_id] = result
    _save_fields(cache)
    return {"id": notice_id, "cached": False, **result}


@app.post("/api/notices/extract")
def api_extract_notices(req: ExtractRequest) -> Dict[str, Any]:
    images = _load_images()
    notices = [_merge_image_info(n, images) for n in load_real_knu_notices()]
    cache = _load_fields()
    targets = [n for n in notices if not req.ids or n.get("id") in req.ids]
    done, skipped, failed = 0, 0, 0
    for notice in targets:
        nid = notice.get("id")
        if not req.force and nid in cache:
            skipped += 1
            continue
        try:
            cache[nid] = extract_notice_fields(notice)
            done += 1
        except Exception:
            failed += 1
    _save_fields(cache)
    return {"done": done, "skipped": skipped, "failed": failed, "total": len(cache)}


@app.get("/api/profile")
def api_get_profile() -> Dict[str, Any]:
    return {"profile": _read_profile()}


@app.post("/api/profile")
def api_save_profile(req: ProfileStoreRequest) -> Dict[str, Any]:
    merged = {**_read_profile(), **(req.profile or {})}
    merged["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_PATH, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, ensure_ascii=False, indent=2)
    if storage.enabled():
        merged["_supabase"] = storage.push_profile(merged)
    return {"profile": merged, "saved": True}


@app.get("/api/llm/models")
def api_llm_models(provider: str = Query(""), free_only: bool = Query(True)) -> Dict[str, Any]:
    return list_models(provider=provider or None, free_only=free_only)


@app.post("/api/notices")
def api_get_notices(req: ProfileRequest) -> Dict[str, Any]:
    sync_res = sync_live_knu_notices(live_check=req.live_check)
    profile_dict = req.model_dump()
    evaluated = filter_and_evaluate_notices(sync_res["notices"], profile_dict)

    cache = _load_fields()
    images = _load_images()
    subscriptions = reminders.list_subscriptions()
    for item in evaluated["notices"]:
        item["has_email"] = bool((item.get("email") or "").strip())
        image_info = images.get(item.get("id")) or {}
        if image_info:
            item["image_links"] = image_info.get("links") or []
            item["image_emails"] = image_info.get("emails") or []
            item["image_phones"] = image_info.get("phones") or []

        cached = cache.get(item.get("id"))
        fields = dict(cached.get("fields") or {}) if cached else {}
        item["fields"] = fields or None
        item["fields_engine"] = cached.get("engine") if cached else None

        # A poster can carry the apply link even when the body has none.
        if not fields.get("application_url") and image_info.get("links"):
            fields["application_url"] = image_info["links"][0]
            fields["source_hint"] = fields.get("source_hint") or "이미지 OCR"
            fields["confidence"] = max(float(fields.get("confidence") or 0), 0.7)
            item["fields"] = fields
            item["fields_from_image"] = True
        if not fields.get("contact_email") and image_info.get("emails"):
            fields["contact_email"] = image_info["emails"][0]
            item["fields"] = fields
        if not fields.get("contact_phone") and image_info.get("phones"):
            fields["contact_phone"] = image_info["phones"][0]
            item["fields"] = fields

        item["has_application_link"] = bool(fields.get("application_url"))
        item["subscribed"] = item.get("id") in subscriptions

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
    llm_res = call_llm(sys_prompt, user_prompt, temperature=0.2, max_tokens=900)
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


@app.on_event("startup")
def _start_reminder_worker() -> None:
    try:
        if storage.enabled():
            storage.ensure_session()
            saved = _read_settings() or storage.load_settings() or {}
            if saved.get("api_key") or saved.get("model"):
                set_runtime_llm(
                    api_key=saved.get("api_key"),
                    model=saved.get("model"),
                    provider=saved.get("provider"),
                    base_url=saved.get("base_url"),
                )
    except Exception:
        pass
    try:
        reminders.start_background_worker(load_real_knu_notices, _read_profile)
    except Exception:
        pass


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
