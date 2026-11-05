import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# LLM layer: any OpenAI-compatible endpoint (OpenRouter / OpenAI / Groq / custom)
# ---------------------------------------------------------------------------
PROVIDERS: Dict[str, Dict[str, str]] = {
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "",
        "keys_url": "https://openrouter.ai/keys",
    },
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "keys_url": "https://platform.openai.com/api-keys",
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-flash",
        "keys_url": "https://platform.deepseek.com/api_keys",
    },
    "groq": {
        "label": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "keys_url": "https://console.groq.com/keys",
    },
    "custom": {
        "label": "Custom",
        "base_url": "",
        "default_model": "",
        "keys_url": "",
    },
}


def _env_key() -> str:
    for name in ("LLM_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY"):
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _initial_provider() -> str:
    explicit = os.getenv("LLM_PROVIDER", "").strip().lower()
    if explicit in PROVIDERS:
        return explicit
    if os.getenv("OPENROUTER_API_KEY", "").strip():
        return "openrouter"
    if os.getenv("OPENAI_API_KEY", "").strip():
        return "openai"
    return "groq"


RUNTIME_CONFIG: Dict[str, str] = {
    "provider": _initial_provider(),
    "base_url": os.getenv("LLM_BASE_URL", "").strip(),
    "api_key": _env_key(),
    "model": os.getenv("LLM_MODEL", "").strip(),
}

if not RUNTIME_CONFIG["base_url"]:
    RUNTIME_CONFIG["base_url"] = PROVIDERS[RUNTIME_CONFIG["provider"]]["base_url"]
if not RUNTIME_CONFIG["model"]:
    RUNTIME_CONFIG["model"] = PROVIDERS[RUNTIME_CONFIG["provider"]]["default_model"]

_MODELS_CACHE: Dict[str, Any] = {"ts": 0.0, "provider": "", "models": []}


def get_llm_status() -> Dict[str, Any]:
    key = RUNTIME_CONFIG["api_key"] or _env_key()
    provider = RUNTIME_CONFIG["provider"]
    meta = PROVIDERS.get(provider, {})
    return {
        "configured": bool(key),
        "provider": provider,
        "label": meta.get("label", provider),
        "base_url": RUNTIME_CONFIG["base_url"],
        "model": RUNTIME_CONFIG["model"],
        "providers": [
            {
                "id": pid,
                "label": p["label"],
                "base_url": p["base_url"],
                "default_model": p["default_model"],
            }
            for pid, p in PROVIDERS.items()
        ],
    }


def set_runtime_llm(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    if provider and provider in PROVIDERS:
        RUNTIME_CONFIG["provider"] = provider
        RUNTIME_CONFIG["base_url"] = (base_url or PROVIDERS[provider]["base_url"] or "").strip()
        RUNTIME_CONFIG["model"] = (model or PROVIDERS[provider]["default_model"] or "").strip()
    else:
        if base_url:
            RUNTIME_CONFIG["base_url"] = base_url.strip()
        if model:
            RUNTIME_CONFIG["model"] = model.strip()
    if api_key is not None and api_key.strip():
        RUNTIME_CONFIG["api_key"] = api_key.strip()
    return get_llm_status()


def _headers() -> Dict[str, str]:
    key = RUNTIME_CONFIG["api_key"] or _env_key()
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if RUNTIME_CONFIG["provider"] == "openrouter":
        headers["HTTP-Referer"] = "https://github.com/stewenmc-boop/ZeroNotice"
        headers["X-Title"] = "ZeroNotice · KNU AI Hackathon"
    return headers


def _engine_label(model: str, latency_ms: int) -> str:
    label = PROVIDERS.get(RUNTIME_CONFIG["provider"], {}).get("label", RUNTIME_CONFIG["provider"])
    return f"{label} · {model} · {latency_ms}ms"


def _auto_model() -> str:
    """When no model is pinned, use the first live free model of the provider."""
    try:
        found = list_models(provider=RUNTIME_CONFIG["provider"], free_only=True)
        if found.get("ok") and found.get("models"):
            return found["models"][0]
    except Exception:
        pass
    return "gpt-4o-mini"


def _candidate_models(primary: str) -> List[str]:
    provider_meta = PROVIDERS.get(RUNTIME_CONFIG["provider"], {})
    raw = [
        primary,
        provider_meta.get("default_model", ""),
        "meta-llama/llama-3.3-70b-instruct:free",
        "gpt-4o-mini",
        "llama-3.1-8b-instant",
    ]
    seen: List[str] = []
    for item in raw:
        if item and item not in seen:
            seen.append(item)
    return seen


def _fallback_chain(primary: str) -> List[str]:
    """Only try models the configured provider can actually serve."""
    provider = RUNTIME_CONFIG["provider"]
    meta = PROVIDERS.get(provider, {})
    if provider == "openrouter":
        raw = [primary, "meta-llama/llama-3.3-70b-instruct:free", "deepseek/deepseek-chat:free"]
    else:
        raw = [primary, meta.get("default_model", "")]
    chain: List[str] = []
    for item in raw:
        if item and item not in chain:
            chain.append(item)
    return chain


def _post_completion(base: str, payload: Dict[str, Any]) -> requests.Response:
    return requests.post(
        f"{base}/chat/completions",
        headers=_headers(),
        json=payload,
        timeout=90.0,
    )


def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.25,
    max_tokens: int = 900,
) -> Dict[str, Any]:
    """Call the configured OpenAI-compatible endpoint; never raises."""
    api_key = RUNTIME_CONFIG["api_key"] or _env_key()
    if not api_key:
        return {
            "ok": False,
            "text": "",
            "latency_ms": 0,
            "model": "built-in",
            "provider": "none",
            "error": "no api key",
            "engine": "Built-in Template Engine",
        }

    base = (RUNTIME_CONFIG["base_url"] or "").rstrip("/")
    if not base:
        return {
            "ok": False,
            "text": "",
            "latency_ms": 0,
            "model": RUNTIME_CONFIG["model"],
            "provider": RUNTIME_CONFIG["provider"],
            "error": "no base url",
            "engine": "Built-in Template Engine",
        }

    primary_model = RUNTIME_CONFIG["model"] or _auto_model()
    provider = RUNTIME_CONFIG["provider"]
    last_error = ""
    started = time.time()

    for model_name in _fallback_chain(primary_model):
        # Reasoning models can spend the whole budget on hidden reasoning,
        # leaving `content` empty. First budget is the requested one, the
        # second is a wider retry when we hit finish_reason == "length".
        for budget in (max_tokens, min(max(max_tokens * 3, 2000), 4000)):
            payload: Dict[str, Any] = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
                "max_tokens": budget,
            }
            # DeepSeek V4 family: skip the thinking phase for task output.
            if provider == "deepseek":
                payload["thinking"] = {"type": "disabled"}

            attempt_start = time.time()
            try:
                resp = _post_completion(base, payload)
                if resp.status_code != 200:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:180]}"
                    break  # same model with a bigger budget will not help
                data = resp.json()
                choice = (data.get("choices") or [{}])[0]
                message = choice.get("message") or {}
                content = (message.get("content") or "").strip()
                finish = choice.get("finish_reason")
                if not content and finish == "length" and budget < 4000:
                    last_error = "empty content (budget consumed by reasoning)"
                    continue  # retry this model with the wider budget
                if not content:
                    # last resort: some reasoning models only fill reasoning_content
                    content = (message.get("reasoning_content") or "").strip()
                if content:
                    latency = int((time.time() - attempt_start) * 1000)
                    return {
                        "ok": True,
                        "text": content,
                        "latency_ms": latency,
                        "model": model_name,
                        "provider": provider,
                        "engine": _engine_label(model_name, latency),
                    }
                last_error = "empty completion"
                break
            except Exception as exc:  # noqa: BLE001 - demo must never crash
                last_error = f"{type(exc).__name__}: {str(exc)[:160]}"
                break

    return {
        "ok": False,
        "text": "",
        "latency_ms": int((time.time() - started) * 1000),
        "model": primary_model,
        "provider": provider,
        "error": last_error,
        "engine": "Built-in Template Engine",
    }


def list_models(provider: Optional[str] = None, free_only: bool = True) -> Dict[str, Any]:
    """Fetch the provider's /models list (cached for 10 minutes)."""
    prov = provider if provider in PROVIDERS else RUNTIME_CONFIG["provider"]
    base = (PROVIDERS.get(prov, {}).get("base_url") or "").rstrip("/")
    if not base:
        return {"ok": False, "models": [], "error": "no base url for provider"}

    now = time.time()
    if (
        _MODELS_CACHE["models"]
        and _MODELS_CACHE["provider"] == prov
        and now - _MODELS_CACHE["ts"] < 600
    ):
        return {"ok": True, "models": _MODELS_CACHE["models"], "cached": True}

    key = RUNTIME_CONFIG["api_key"] or _env_key()
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    try:
        resp = requests.get(f"{base}/models", headers=headers, timeout=15.0)
        if resp.status_code != 200:
            return {"ok": False, "models": [], "error": f"HTTP {resp.status_code}"}
        payload = resp.json()
        raw_items = payload.get("data") or payload.get("models") or []
        ids = []
        for item in raw_items:
            if isinstance(item, dict) and item.get("id"):
                ids.append(str(item["id"]))
            elif isinstance(item, str):
                ids.append(item)
        if prov == "openrouter" and free_only:
            free = [i for i in ids if i.endswith(":free")]
            ids = free or ids
        ids = sorted(set(ids))
        _MODELS_CACHE.update({"ts": now, "provider": prov, "models": ids})
        return {"ok": True, "models": ids, "count": len(ids)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "models": [], "error": str(exc)[:160]}


# --- backward-compatible aliases (older app.py imports) ---------------------
def set_runtime_groq_key(api_key: str, model: Optional[str] = None) -> Dict[str, Any]:
    return set_runtime_llm(api_key=api_key, model=model)


def get_groq_status() -> Dict[str, Any]:
    return get_llm_status()


def evaluate_real_notice(
    notice: Dict[str, Any], profile: Dict[str, Any]
) -> Dict[str, Any]:
    rules = notice.get("rules", {})
    user_campus = profile.get("campus", "춘천")
    user_status = profile.get("status", "undergrad_kr")  # undergrad_kr | intl | leave_grad | staff_citizen
    user_gpa = float(profile.get("gpa", 3.8))
    user_income = int(profile.get("income_bracket", 3))

    allowed_campuses = rules.get("campuses", ["춘천", "삼척", "강릉", "원주"])
    allowed_status = rules.get("status_allowed", ["undergrad_kr", "intl"])
    min_gpa = float(rules.get("min_gpa", 0.0))
    max_income = int(rules.get("max_income", 10))

    ineligible_ko = []
    ineligible_zh = []
    ineligible_en = []
    cond_ko = []
    cond_zh = []
    cond_en = []

    # 1. Campus check
    if user_campus not in allowed_campuses:
        target_str = "·".join(allowed_campuses)
        ineligible_ko.append(f"타 캠퍼스({target_str}) 전용 공지")
        ineligible_zh.append(f"仅限其他校区（{target_str}）")
        ineligible_en.append(f"For {target_str} campus only")

    # 2. Enrollment / Citizenship Status check
    if user_status not in allowed_status:
        if allowed_status == ["leave_grad"]:
            ineligible_ko.append("재학생 지원 불가 (졸업생·장기휴학생 전용)")
            ineligible_zh.append("在读生不可申请（限毕业生/长期休学生）")
            ineligible_en.append("Enrolled students ineligible (Grads/Leave only)")
        elif allowed_status == ["undergrad_kr"] and user_status == "intl":
            ineligible_ko.append("대한민국 국적자(한국장학재단) 한정")
            ineligible_zh.append("仅限韩国籍学生（国家奖学财团项目）")
            ineligible_en.append("Korean nationals only (KOSAF requirement)")
        elif allowed_status == ["staff_citizen"]:
            ineligible_ko.append("창업기업·교직원·고교생 대상 (학부생 해당 없음)")
            ineligible_zh.append("非本科生项目（面向企业/外部人员）")
            ineligible_en.append("Not applicable to undergraduate students")
        else:
            ineligible_ko.append("신청 대상 신분 아님")
            ineligible_zh.append("不在申请身份范围内")
            ineligible_en.append("Status not eligible")

    # 3. GPA & Income checks for active students
    if not ineligible_ko and user_status in ("undergrad_kr", "intl"):
        if min_gpa > 0 and user_gpa < min_gpa:
            ineligible_ko.append(f"평점 기준 미달 (기준 {min_gpa} 이상, 본인 {user_gpa})")
            ineligible_zh.append(f"GPA未达标（要求 ≥ {min_gpa}，当前 {user_gpa}）")
            ineligible_en.append(f"GPA below {min_gpa} (Your GPA: {user_gpa})")

        if max_income < 10 and user_status == "undergrad_kr":
            if user_income > max_income:
                cond_ko.append(f"소득구간 {max_income}구간 이하 요건 확인 필요 (현재 {user_income}구간)")
                cond_zh.append(f"需满足所得分位 ≤ {max_income}区间（当前设为 {user_income}区间）")
                cond_en.append(f"Requires Income Tier <= {max_income} (Current: {user_income})")

    if ineligible_ko:
        match_status = "ineligible"
        verdict_ko = ineligible_ko[0]
        verdict_zh = ineligible_zh[0]
        verdict_en = ineligible_en[0]
    elif cond_ko:
        match_status = "conditional"
        verdict_ko = cond_ko[0]
        verdict_zh = cond_zh[0]
        verdict_en = cond_en[0]
    else:
        match_status = "eligible"
        verdict_ko = rules.get("note_ko", "내 학적·캠퍼스 조건 충족")
        verdict_zh = rules.get("note_zh", "符合您的校区与学籍条件")
        verdict_en = rules.get("note_en", "Matches your campus and status")

    # Calculate reading time saved (especially when HWP/HWPX attachments are involved)
    total_chars = notice.get("char_count", 500) + len(
        notice.get("attachment_extracted_text", "")
    )
    has_hwp = len(notice.get("attachments", [])) > 0
    saved_mins = round(max(2.0, (total_chars / 350.0) + (3.5 if has_hwp else 1.0)), 1)

    # Compute D-Day
    dl_str = notice.get("deadline", "2026-11-15 18:00")
    try:
        dl_dt = datetime.strptime(dl_str, "%Y-%m-%d %H:%M")
        days_left = (dl_dt.date() - datetime(2026, 11, 5).date()).days
        if days_left < 0:
            d_day = "마감"
        elif days_left == 0:
            d_day = "D-Day"
        else:
            d_day = f"D-{days_left}"
    except Exception:
        d_day = "진행중"

    return {
        **notice,
        "match_status": match_status,
        "verdict_ko": verdict_ko,
        "verdict_zh": verdict_zh,
        "verdict_en": verdict_en,
        "saved_minutes": saved_mins,
        "d_day": d_day,
    }


def filter_and_evaluate_notices(
    notices: List[Dict[str, Any]], profile: Dict[str, Any]
) -> Dict[str, Any]:
    evaluated = [evaluate_real_notice(n, profile) for n in notices]

    eligible_cnt = sum(1 for n in evaluated if n["match_status"] == "eligible")
    cond_cnt = sum(1 for n in evaluated if n["match_status"] == "conditional")
    ineligible_cnt = sum(1 for n in evaluated if n["match_status"] == "ineligible")
    total_saved_mins = round(sum(n["saved_minutes"] for n in evaluated), 1)
    hwp_parsed_cnt = sum(1 for n in evaluated if len(n.get("attachments", [])) > 0)

    return {
        "notices": evaluated,
        "stats": {
            "total": len(evaluated),
            "eligible": eligible_cnt,
            "conditional": cond_cnt,
            "ineligible": ineligible_cnt,
            "saved_minutes": total_saved_mins,
            "hwp_parsed_count": hwp_parsed_cnt,
        },
    }


def generate_ics_content(notice: Dict[str, Any], lang: str = "ko") -> str:
    deadline_str = notice.get("deadline", "2026-11-13 18:00")
    try:
        dt_end = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")
    except Exception:
        dt_end = datetime(2026, 11, 13, 18, 0)

    dt_start = dt_end - timedelta(hours=1)
    fmt = "%Y%m%dT%H%M%S"

    title = notice.get(f"title_{lang}") or notice.get("title_ko") or notice.get("title", "")
    summary = notice.get(f"summary_{lang}") or notice.get("summary_ko") or ""
    att_names = ", ".join(a["name"] for a in notice.get("attachments", []))

    desc = (
        f"[강원대 공지 마감 알림]\\n"
        f"요약: {summary}\\n"
        f"담당부서: {notice.get('author', '')} ({notice.get('phone', '')})\\n"
        f"첨부파일: {att_names}\\n"
        f"원문 링크: {notice.get('url', '')}"
    )

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//KNU Notice Assistant//KO",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{notice.get('id', 'knu')}@kangwon.ac.kr",
        f"DTSTAMP:{datetime.utcnow().strftime(fmt)}Z",
        f"DTSTART;TZID=Asia/Seoul:{dt_start.strftime(fmt)}",
        f"DTEND;TZID=Asia/Seoul:{dt_end.strftime(fmt)}",
        f"SUMMARY:[마감] {title}",
        f"LOCATION:{notice.get('author', '강원대학교')}",
        f"DESCRIPTION:{desc}",
        "BEGIN:VALARM",
        "TRIGGER:-PT24H",
        "ACTION:DISPLAY",
        "DESCRIPTION:강원대 공지 마감 24시간 전 알림",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines)


def generate_polite_email_agent(
    notice: Dict[str, Any], profile: Dict[str, Any], custom_question: str = ""
) -> Dict[str, Any]:
    dept = notice.get("author", "담당 부서")
    email = notice.get("email") or "knu@kangwon.ac.kr"
    phone = notice.get("phone", "033-250-6114")
    title_ko = notice.get("title_ko") or notice.get("title", "")
    user_dept = profile.get("department", "첨단AI공학부")
    user_grade = profile.get("grade", 3)
    user_gpa = profile.get("gpa", 3.8)
    user_name = profile.get("name", "김강원")
    user_id = profile.get("student_id", "202411234")

    q_text = (
        custom_question.strip()
        if custom_question.strip()
        else "공고문 및 첨부파일을 확인하였으며, 세부 제출서류 양식 및 접수 관련하여 문의드리고자 합니다."
    )

    sys_prompt = (
        "당신은 강원대학교 학생을 위한 행정 문의 이메일 작성 비서입니다. "
        "실제 공고문 내용과 담당 부서 정보를 바탕으로 한국 대학 행정실에 보낼 정중하고 명확한 경어 이메일 본문을 작성하세요."
    )
    user_prompt = (
        f"공고명: {title_ko}\n"
        f"담당부서: {dept} ({phone}, {email})\n"
        f"공고 요약: {notice.get('summary_ko', '')}\n"
        f"학생 정보: 강원대학교 {profile.get('campus', '춘천')}캠퍼스 {user_dept} {user_grade}학년 {user_name} (학번: {user_id}, 평점: {user_gpa})\n"
        f"문의 내용: {q_text}\n\n"
        "곧바로 복사해 발송할 수 있는 정중한 이메일 본문만 출력해 주세요."
    )

    llm_res = call_llm(sys_prompt, user_prompt, temperature=0.25, max_tokens=600)
    subject = f"[문의] {title_ko[:40]} 관련 문의드립니다 ({user_dept} {user_id} {user_name})"

    if llm_res["ok"] and len(llm_res["text"]) > 60:
        body = llm_res["text"]
        engine = llm_res["engine"]
    else:
        att_list = ", ".join(a["name"] for a in notice.get("attachments", [])[:2]) or "관련 서류"
        body = (
            f"안녕하십니까, {dept} 담당자님.\n"
            f"강원대학교 {profile.get('campus', '춘천')}캠퍼스 {user_dept} {user_grade}학년에 재학 중인 {user_name}(학번: {user_id})입니다.\n\n"
            f"학교 홈페이지 공지사항에 게시된 『{title_ko}』 공고를 확인하고 신청을 준비하던 중 문의사항이 있어 메일 드립니다.\n\n"
            f"1. 공고문에 안내된 자격 요건(현재 평점 {user_gpa}/4.5) 및 제출 기한({notice.get('deadline', '')})을 확인하였습니다.\n"
            f"2. {q_text}\n"
            f"3. 첨부해주신 서식({att_list})을 작성하여 기한 내에 제출하고자 하는데, 추가 유의사항이 있는지 확인 부탁드립니다.\n\n"
            f"바쁘신 와중에도 읽어주셔서 감사드리며, 답변 기다리겠습니다.\n\n"
            f"감사합니다.\n"
            f"{user_name} 올림\n"
            f"(학번: {user_id} / 소속: {user_dept})"
        )
        engine = "Built-in Template Engine"

    return {
        "department": dept,
        "email": email,
        "phone": phone,
        "subject": subject,
        "body": body,
        "engine": engine,
    }


def generate_application_draft_agent(
    notice: Dict[str, Any], profile: Dict[str, Any]
) -> Dict[str, Any]:
    title_ko = notice.get("title_ko") or notice.get("title", "")
    body_ko = (notice.get("body", "") + "\n" + notice.get("attachment_extracted_text", ""))[:1800]
    user_dept = profile.get("department", "첨단AI공학부")
    user_grade = profile.get("grade", 3)
    user_gpa = profile.get("gpa", 3.8)
    user_name = profile.get("name", "김강원")
    user_id = profile.get("student_id", "202411234")

    sys_prompt = (
        "당신은 강원대학교 장학금·공모전·학사 프로그램 지원서 작성을 돕는 AI 에이전트입니다. "
        "실제 공고문 내용에 맞춰 곧바로 제출 서식(.hwp)에 붙여넣을 수 있는 구체적이고 설득력 있는 한국어 지원서/계획서 초안(약 500~600자)을 작성하세요."
    )
    user_prompt = (
        f"공고명: {title_ko}\n"
        f"공고 본문 요약 및 추출 원문:\n{body_ko}\n\n"
        f"지원자: 강원대학교 {profile.get('campus', '춘천')}캠퍼스 {user_dept} {user_grade}학년 {user_name} (GPA {user_gpa}/4.5)\n\n"
        "위 공고의 목적과 평가 기준에 정확히 부합하는: 1) 신청인 기본사항, 2) 지원동기 및 문제의식, 3) 구체적 실행/학업 계획 초안을 작성해 주세요."
    )

    llm_res = call_llm(sys_prompt, user_prompt, temperature=0.3, max_tokens=800)
    if llm_res["ok"] and len(llm_res["text"]) > 100:
        draft = llm_res["text"]
        engine = llm_res["engine"]
    else:
        draft = (
            f"[신청서/계획서 초안 — {title_ko}]\n"
            f"• 소속: 강원대학교 {profile.get('campus', '춘천')}캠퍼스 {user_dept} {user_grade}학년\n"
            f"• 성명 / 학번: {user_name} ({user_id}) / 평점: {user_gpa} / 4.5\n"
            f"──────────────────────────────────────────────\n\n"
            f"1. 지원동기 및 배경\n"
            f"강원대학교 {user_dept}에서 전공 역량을 쌓으며 실제 캠퍼스와 지역사회의 문제를 AI 및 소프트웨어 기술로 해결하는 데 깊은 관심을 가져왔습니다. "
            f"이번 『{title_ko}』의 취지인 '{notice.get('summary_ko', '')}'에 깊이 공감하여 지원하게 되었습니다.\n\n"
            f"2. 핵심 아이디어 및 활동/학업 계획\n"
            f"- 목표: 학내외 구성원들이 겪는 정보 탐색 및 문서 처리의 숨은 비용(시간·에너지)을 줄이는 AI 자동화 워크플로우 구축\n"
            f"- 실행 방안: 재학 중 습득한 전공 지식과 해커톤 프로젝트 경험을 바탕으로 실사용 가능한 프로토타입을 고도화하고, 결과물을 학내 구성원들과 공유하겠습니다.\n"
            f"- 기대 효과: 선발 이후 성실히 학업 및 프로젝트를 완수하여 강원대학교의 우수 인재로서 실질적인 성과를 도출하겠습니다."
        )
        engine = "Built-in Template Engine"

    return {
        "notice_id": notice.get("id"),
        "notice_title": title_ko,
        "draft": draft,
        "attachments": notice.get("attachments", []),
        "engine": engine,
    }
