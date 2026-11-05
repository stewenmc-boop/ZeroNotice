"""Subscription store + deadline reminder engine.

A subscription means: "이 공지를 관심 등록했으니, 마감 하루 전에 메일로 찔러줘."
Reminders go to the e-mail saved in the user's profile (sidebar), never to a
separate address.
"""

import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import notifier
import paths
from agent import generate_ics_content

SUBS_PATH = paths.writable("subscriptions.json")
REMIND_BEFORE_HOURS = 24
_CHECK_INTERVAL_SECONDS = 300
_lock = threading.Lock()


def _load() -> Dict[str, Any]:
    if not SUBS_PATH.exists():
        return {}
    try:
        with open(SUBS_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(data: Dict[str, Any]) -> None:
    SUBS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SUBS_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def parse_deadline(value: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime((value or "").strip(), fmt)
        except Exception:
            continue
    return None


def list_subscriptions() -> Dict[str, Any]:
    return _load()


def is_subscribed(notice_id: str) -> bool:
    return notice_id in _load()


def subscribe(notice_id: str, subscribed: bool) -> Dict[str, Any]:
    with _lock:
        data = _load()
        if subscribed:
            data[notice_id] = data.get(notice_id) or {
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "reminded_at": None,
            }
        else:
            data.pop(notice_id, None)
        _save(data)
    return {"notice_id": notice_id, "subscribed": subscribed, "total": len(data)}


def due_reminders(notices: List[Dict[str, Any]], force_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Which subscribed notices need a nudge right now."""
    data = _load()
    now = datetime.now()
    due = []
    for notice in notices:
        nid = notice.get("id")
        if nid not in data:
            continue
        entry = data[nid]
        if entry.get("reminded_at"):
            continue
        deadline = parse_deadline(notice.get("deadline", ""))
        if not deadline:
            continue
        remind_at = deadline - timedelta(hours=REMIND_BEFORE_HOURS)
        forced = bool(force_ids and nid in force_ids)
        if forced or now >= remind_at:
            due.append({"notice": notice, "deadline": deadline, "remind_at": remind_at})
    return due


def mark_reminded(notice_id: str, ok: bool) -> None:
    with _lock:
        data = _load()
        if notice_id in data:
            data[notice_id]["last_attempt_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data[notice_id]["last_ok"] = ok
            if ok:
                data[notice_id]["reminded_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            _save(data)


def send_reminder(notice: Dict[str, Any], profile: Dict[str, Any], lang: str = "ko") -> Dict[str, Any]:
    to_email = (profile.get("email") or "").strip()
    if not to_email:
        return {"ok": False, "error": "프로필에 이메일이 없습니다. 왼쪽 '내 학적 조건'에서 먼저 입력하세요."}

    title = notice.get(f"title_{lang}") or notice.get("title_ko") or notice.get("title", "")
    deadline = notice.get("deadline", "")
    name = (profile.get("name") or "").strip() or "학생"
    fields = notice.get("fields") or {}
    apply_url = fields.get("application_url") or ""

    subject = f"[ZeroNotice] 마감 임박 · {title[:38]}"
    lines = [
        f"{name}님, 관심 등록하신 공지의 마감이 다가옵니다.",
        "",
        f"공지: {title}",
        f"마감: {deadline}",
        f"담당: {notice.get('author', '')} {notice.get('phone', '')}".strip(),
    ]
    if apply_url:
        lines += ["", f"신청 링크: {apply_url}"]
    lines += [
        "",
        "지금 바로 신청하세요. 첨부한 .ics 파일을 열면 캘린더에도 자동 등록됩니다.",
        f"원문: {notice.get('url', '')}",
    ]

    ics = generate_ics_content(notice, lang=lang).encode("utf-8")
    result = notifier.send_mail(
        to_email,
        subject,
        "\n".join(lines),
        [(f"{notice.get('id', 'notice')}.ics", ics, "calendar")],
    )
    mark_reminded(notice.get("id", ""), bool(result.get("ok")))
    return result


def run_check(notices: List[Dict[str, Any]], profile: Dict[str, Any], lang: str = "ko",
              force_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    due = due_reminders(notices, force_ids=force_ids)
    sent, failed = [], []
    for item in due:
        result = send_reminder(item["notice"], profile, lang)
        if result.get("ok"):
            sent.append(item["notice"].get("id"))
        else:
            failed.append({"id": item["notice"].get("id"), "error": result.get("error")})
    return {"checked": len(due), "sent": sent, "failed": failed}


def start_background_worker(notices_loader, profile_loader, interval: int = _CHECK_INTERVAL_SECONDS):
    """Fire a reminder check every few minutes while the server runs."""

    def loop():
        while True:
            try:
                time.sleep(interval)
                if not notifier.smtp_status().get("configured"):
                    continue
                profile = profile_loader() or {}
                if not (profile.get("email") or "").strip():
                    continue
                run_check(notices_loader(), profile)
            except Exception:
                continue

    thread = threading.Thread(target=loop, name="zeronotice-reminder", daemon=True)
    thread.start()
    return thread
