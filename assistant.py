"""ZeroNotice assistant: a tool-calling agent over the app's own capabilities.

The assistant can search notices, read one in detail, list upcoming deadlines,
subscribe / unsubscribe, draft an inquiry e-mail, send it to the department, and
report the student's own profile. It never invents data: every tool reads the
same JSON/Supabase records the UI uses.
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import agent
import notifier
import reminders
from scraper import load_notices

MAX_ROUNDS = 4

SYSTEM_PROMPT = (
    "당신은 강원대학교 공지 도우미 'ZeroNotice'의 AI 비서입니다. "
    "반드시 제공된 도구(tool)로 실제 데이터를 확인한 뒤 답하세요. 추측 금지. "
    "사용자가 공지를 특정하면 그 공지의 마감·자격·신청 링크·접수 방법을 요약해 주고, "
    "필요하면 구독(알림)이나 문의 메일 작성까지 실행하세요. "
    "답변은 간결한 한국어(사용자가 중국어로 물으면 중국어)로, 핵심 숫자와 링크를 포함하세요. "
    "자격 판정은 규칙 엔진 결과를 그대로 인용하고, 없는 정보는 '공고에 없음'이라고 말하세요."
)

TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_notices",
            "description": "공지를 키워드/카테고리/마감일/자격으로 검색한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색어(제목·본문·첨부)"},
                    "category": {"type": "string", "description": "장학/학사/공모/일반/행사"},
                    "within_days": {"type": "integer", "description": "며칠 안에 마감되는 것만"},
                    "eligible_only": {"type": "boolean", "description": "내 조건에 맞는 것만"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_notice",
            "description": "공지 1건의 상세(마감, 자격, 신청 링크, 접수 방법, 제출 서류)를 가져온다.",
            "parameters": {
                "type": "object",
                "properties": {"notice_id": {"type": "string"}},
                "required": ["notice_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_upcoming",
            "description": "곧 마감되는 공지 목록.",
            "parameters": {
                "type": "object",
                "properties": {"days": {"type": "integer", "description": "기본 7일"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "subscribe_notice",
            "description": "공지를 관심 등록하거나 해제한다(마감 24시간 전 메일 알림).",
            "parameters": {
                "type": "object",
                "properties": {
                    "notice_id": {"type": "string"},
                    "subscribe": {"type": "boolean"},
                },
                "required": ["notice_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_subscriptions",
            "description": "내가 구독 중인 공지 목록.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_inquiry_email",
            "description": "담당 부서에 보낼 문의 메일 초안을 만든다(발송은 하지 않음).",
            "parameters": {
                "type": "object",
                "properties": {
                    "notice_id": {"type": "string"},
                    "question": {"type": "string"},
                },
                "required": ["notice_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_inquiry_email",
            "description": "공고 담당 부서로 문의 메일을 실제 발송한다. 담당자 이메일이 없으면 실패한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "notice_id": {"type": "string"},
                    "question": {"type": "string"},
                },
                "required": ["notice_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_profile",
            "description": "내 학적 정보(이름·학번·캠퍼스·학과·학년·GPA·소득구간·이메일)를 확인한다.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _notices() -> List[Dict[str, Any]]:
    return load_notices()


def _fields(notice_id: str) -> Dict[str, Any]:
    try:
        with open("data/notice_fields.json", "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return (data.get(notice_id) or {}).get("fields") or {}
    except Exception:
        return {}


def _dday(deadline: str) -> str:
    try:
        dt = datetime.strptime((deadline or "").strip(), "%Y-%m-%d %H:%M")
        left = (dt.date() - datetime.now().date()).days
        return "마감" if left < 0 else ("D-Day" if left == 0 else f"D-{left}")
    except Exception:
        return "-"


def _summary(n: Dict[str, Any], profile: Dict[str, Any], lang: str = "ko") -> Dict[str, Any]:
    judged = agent.evaluate_real_notice(n, profile) if profile else {}
    title = n.get(f"title_{lang}") or n.get("title_ko") or n.get("title", "")
    return {
        "id": n.get("id"),
        "title": title[:90],
        "category": n.get("category"),
        "deadline": n.get("deadline"),
        "dday": _dday(n.get("deadline", "")),
        "match": judged.get("match_status"),
        "verdict": judged.get(f"verdict_{lang}") or judged.get("verdict_ko"),
        "has_application_link": bool(_fields(n.get("id", "")).get("application_url")),
    }


def _query(args: Dict[str, Any], profile: Dict[str, Any], lang: str) -> str:
    query = (args.get("query") or "").strip().lower()
    category = (args.get("category") or "").strip()
    within = args.get("within_days")
    eligible_only = bool(args.get("eligible_only"))

    rows = []
    for n in _notices():
        if category and category not in (n.get("category") or ""):
            continue
        if within:
            try:
                dt = datetime.strptime(n.get("deadline", ""), "%Y-%m-%d %H:%M")
                if (dt - datetime.now()).days > int(within):
                    continue
            except Exception:
                pass
        if query:
            haystack = " ".join(
                str(n.get(k) or "")
                for k in ("title", "title_ko", "title_zh", "title_en", "summary_ko", "body",
                          "attachment_extracted_text", "author")
            ).lower()
            if query not in haystack:
                continue
        item = _summary(n, profile, lang)
        if eligible_only and item.get("match") == "ineligible":
            continue
        rows.append(item)

    rows.sort(key=lambda r: r.get("deadline") or "9999")
    return json.dumps({"count": len(rows), "notices": rows[:8]}, ensure_ascii=False)


def _get_notice(args: Dict[str, Any], profile: Dict[str, Any], lang: str) -> str:
    nid = args.get("notice_id")
    n = next((x for x in _notices() if x.get("id") == nid), None)
    if not n:
        return json.dumps({"error": "notice not found", "notice_id": nid}, ensure_ascii=False)
    fields = _fields(nid)
    judged = agent.evaluate_real_notice(n, profile) if profile else {}
    return json.dumps({
        "id": nid,
        "title": n.get(f"title_{lang}") or n.get("title_ko") or n.get("title"),
        "category": n.get("category"),
        "author": n.get("author"),
        "phone": n.get("phone"),
        "email": n.get("email"),
        "deadline": n.get("deadline"),
        "dday": _dday(n.get("deadline", "")),
        "url": n.get("url"),
        "match": judged.get("match_status"),
        "verdict": judged.get(f"verdict_{lang}") or judged.get("verdict_ko"),
        "application_url": fields.get("application_url"),
        "application_method": fields.get(f"application_method_{lang}") or fields.get("application_method_ko"),
        "required_documents": fields.get("required_documents") or [],
        "contact_email": fields.get("contact_email") or n.get("email"),
        "contact_phone": fields.get("contact_phone") or n.get("phone"),
        "subscribed": reminders.is_subscribed(nid),
    }, ensure_ascii=False)


def _upcoming(args: Dict[str, Any], profile: Dict[str, Any], lang: str) -> str:
    days = int(args.get("days") or 7)
    rows = []
    now = datetime.now()
    for n in _notices():
        try:
            dt = datetime.strptime(n.get("deadline", ""), "%Y-%m-%d %H:%M")
        except Exception:
            continue
        delta = (dt - now).days
        if 0 <= delta <= days:
            rows.append(_summary(n, profile, lang))
    rows.sort(key=lambda r: r.get("deadline") or "")
    return json.dumps({"days": days, "count": len(rows), "notices": rows[:10]}, ensure_ascii=False)


def _execute(name: str, args: Dict[str, Any], profile: Dict[str, Any], lang: str) -> Dict[str, Any]:
    if name == "search_notices":
        return {"ok": True, "result": _query(args, profile, lang)}
    if name == "get_notice":
        return {"ok": True, "result": _get_notice(args, profile, lang)}
    if name == "list_upcoming":
        return {"ok": True, "result": _upcoming(args, profile, lang)}
    if name == "subscribe_notice":
        nid = args.get("notice_id", "")
        subscribe = bool(args.get("subscribe", True))
        result = reminders.subscribe(nid, subscribe)
        return {"ok": True, "result": json.dumps(result, ensure_ascii=False)}
    if name == "list_subscriptions":
        own = reminders.list_subscriptions()
        titles = []
        for nid in own:
            n = next((x for x in _notices() if x.get("id") == nid), None)
            if n:
                titles.append(_summary(n, profile, lang))
        return {"ok": True, "result": json.dumps({"count": len(titles), "notices": titles}, ensure_ascii=False)}
    if name in ("draft_inquiry_email", "send_inquiry_email"):
        nid = args.get("notice_id", "")
        n = next((x for x in _notices() if x.get("id") == nid), None)
        if not n:
            return {"ok": False, "error": "notice not found"}
        draft = agent.generate_polite_email_agent(n, profile, args.get("question", ""))
        if name == "draft_inquiry_email":
            return {"ok": True, "result": json.dumps({
                "to": draft.get("email", ""),
                "subject": draft.get("subject", ""),
                "body": (draft.get("body") or "")[:1200],
                "has_email": draft.get("has_email"),
            }, ensure_ascii=False)}
        if not draft.get("has_email"):
            return {"ok": False, "error": "이 공고에는 담당자 이메일이 없습니다. 전화 문의가 필요합니다."}
        sent = notifier.send_mail(
            draft["email"], draft["subject"], draft["body"],
            [(f"{nid}.ics", agent.generate_ics_content(n, lang=lang).encode("utf-8"), "calendar")],
        )
        return {"ok": bool(sent.get("ok")), "result": json.dumps(sent, ensure_ascii=False),
                "error": sent.get("error")}
    if name == "get_my_profile":
        allowed = ("name", "student_id", "campus", "department", "grade",
                   "gpa", "income_bracket", "phone", "email", "status")
        clean = {k: (profile or {}).get(k) for k in allowed if (profile or {}).get(k) not in (None, "")}
        return {"ok": True, "result": json.dumps(clean, ensure_ascii=False)}
    return {"ok": False, "error": f"unknown tool {name}"}


# --------------------------------------------------------------------------- #
# chat loop
# --------------------------------------------------------------------------- #
def _chat(messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    import requests

    cfg = agent.RUNTIME_CONFIG
    base = (cfg.get("base_url") or "").rstrip("/")
    key = cfg.get("api_key") or ""
    if not base or not key:
        return {"ok": False, "error": "no llm configured"}
    payload: Dict[str, Any] = {
        "model": cfg.get("model") or "deepseek-flash",
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 900,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    if cfg.get("provider") == "deepseek":
        payload["thinking"] = {"type": "disabled"}
    try:
        resp = requests.post(
            f"{base}/chat/completions",
            headers=agent._headers(),
            json=payload,
            timeout=90,
        )
        if resp.status_code != 200:
            return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:160]}"}
        return {"ok": True, "message": resp.json()["choices"][0]["message"]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:160]}"}


def chat(history: List[Dict[str, str]], profile: Dict[str, Any], lang: str = "ko") -> Dict[str, Any]:
    messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [{"role": m["role"], "content": m["content"]} for m in history[-12:]]

    used: List[Dict[str, Any]] = []
    for _ in range(MAX_ROUNDS):
        step = _chat(messages, TOOLS)
        if not step.get("ok"):
            return {"reply": "지금은 AI에 연결하지 못했어요. 잠시 후 다시 시도해 주세요.",
                    "error": step.get("error"), "tool_calls": used}
        msg = step["message"]
        calls = msg.get("tool_calls") or []
        if not calls:
            return {"reply": (msg.get("content") or "").strip(), "tool_calls": used}

        messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
        for call in calls:
            name = call["function"]["name"]
            try:
                args = json.loads(call["function"].get("arguments") or "{}")
            except Exception:
                args = {}
            outcome = _execute(name, args, profile, lang)
            used.append({"name": name, "args": args, "ok": outcome.get("ok")})
            messages.append({
                "role": "tool",
                "tool_call_id": call.get("id"),
                "content": json.dumps(outcome, ensure_ascii=False)[:4000],
            })

    return {"reply": "요청을 처리하는 데 시간이 걸렸어요. 조금 더 구체적으로 다시 물어봐 주세요.",
            "tool_calls": used}
