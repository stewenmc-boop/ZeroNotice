"""Supabase client for ZeroNotice (shared notices + per-user data).

Two keys, deliberately separated:

* SUPABASE_ANON_KEY    - shipped inside the .exe/.dmg build. Each install signs
                         in anonymously once and gets its own auth.uid(); RLS
                         makes sure a student can only touch their own rows.
* SUPABASE_SERVICE_KEY - owner-only, used by scripts/sync_supabase.py to write
                         shared notices and upload files. Never ship this.

Without configuration every helper is a no-op and the app keeps using its local
JSON files, so the demo never breaks.
"""

import hashlib
import json
import os
import time
import uuid
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import paths
import requests
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent
IDENTITY_PATH = paths.writable("identity.json")
TIMEOUT = 20.0
_LAST_AUTH_ERROR = ""
_DEVICE_COLUMNS = None


# --------------------------------------------------------------------------- #
# config / identity
# --------------------------------------------------------------------------- #
def cfg() -> Dict[str, Any]:
    return {
        "url": (os.getenv("SUPABASE_URL") or "").strip().rstrip("/"),
        "anon_key": (os.getenv("SUPABASE_ANON_KEY") or "").strip(),
        "service_key": (os.getenv("SUPABASE_SERVICE_KEY") or "").strip(),
        "bucket": (os.getenv("SUPABASE_BUCKET") or "attachments").strip(),
        "retention_days": int(os.getenv("SUPABASE_RETENTION_DAYS") or 30),
    }


def enabled() -> bool:
    c = cfg()
    return bool(c["url"] and c["anon_key"])


def can_write_shared() -> bool:
    c = cfg()
    return bool(c["url"] and c["service_key"])


def _load_identity() -> Dict[str, Any]:
    if IDENTITY_PATH.exists():
        try:
            return json.loads(IDENTITY_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_identity(data: Dict[str, Any]) -> None:
    IDENTITY_PATH.parent.mkdir(parents=True, exist_ok=True)
    IDENTITY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _anon_headers() -> Dict[str, str]:
    c = cfg()
    return {"apikey": c["anon_key"], "Content-Type": "application/json"}


def _service_headers() -> Dict[str, str]:
    c = cfg()
    key = c["service_key"] or c["anon_key"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _user_headers() -> Dict[str, str]:
    c = cfg()
    identity = ensure_session()
    if identity.get("access_token"):
        return {
            "apikey": c["anon_key"],
            "Authorization": f"Bearer {identity.get('access_token', '')}",
            "Content-Type": "application/json",
        }
    return {
        "apikey": c["anon_key"],
        "x-device-key": _device_key(),
        "Content-Type": "application/json",
    }


def sign_in_anonymous() -> Dict[str, Any]:
    """Create (or reuse) an anonymous Supabase user for this installation."""
    c = cfg()
    if not enabled():
        return {"ok": False, "skipped": True, "error": "supabase not configured"}
    try:
        resp = requests.post(
            f"{c['url']}/auth/v1/signup",
            headers=_anon_headers(),
            json={"data": {"app": "ZeroNotice"}, "gotrue_meta_security": {}},
            timeout=TIMEOUT,
        )
        if resp.status_code not in (200, 201):
            global _LAST_AUTH_ERROR
            body = resp.text[:250]
            if "anonymous_provider_disabled" in body:
                _LAST_AUTH_ERROR = (
                    "Supabase 익명 로그인이 꺼져 있습니다. "
                    "Dashboard → Authentication → Sign In/Providers → Anonymous sign-ins 를 켜주세요."
                )
            else:
                _LAST_AUTH_ERROR = body
            return {"ok": False, "status": resp.status_code, "error": body}
        payload = resp.json()
        user = payload.get("user") or {}
        identity = {
            "user_id": user.get("id"),
            "access_token": payload.get("access_token"),
            "refresh_token": payload.get("refresh_token"),
            "expires_at": payload.get("expires_at") or (int(time.time()) + int(payload.get("expires_in") or 3600)),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_identity(identity)
        return {"ok": True, **identity}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:200]}"}


def set_session(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Persist a session returned by Supabase auth (password, OAuth, anonymous)."""
    user = payload.get("user") or {}
    identity = {
        "user_id": user.get("id"),
        "email": user.get("email"),
        "provider": (user.get("app_metadata") or {}).get("provider"),
        "access_token": payload.get("access_token"),
        "refresh_token": payload.get("refresh_token"),
        "expires_at": payload.get("expires_at") or (int(time.time()) + int(payload.get("expires_in") or 3600)),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    current = _load_identity()
    if current.get("device_key"):
        identity["device_key"] = current["device_key"]
    _save_identity(identity)
    _LAST_AUTH_ERROR = ""
    return identity


def current_user() -> Dict[str, Any]:
    identity = _load_identity()
    return {
        "user_id": identity.get("user_id"),
        "email": identity.get("email"),
        "provider": identity.get("provider") or ("anonymous" if identity.get("user_id") else None),
        "mode": mode(),
    }


def clear_session() -> None:
    identity = _load_identity()
    _save_identity({"device_key": identity.get("device_key", "")} if identity.get("device_key") else {})


def exchange_pkce(auth_code: str, code_verifier: str) -> Dict[str, Any]:
    c = cfg()
    try:
        resp = requests.post(
            f"{c['url']}/auth/v1/token?grant_type=pkce",
            headers=_anon_headers(),
            json={"auth_code": auth_code, "code_verifier": code_verifier},
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            return {"ok": False, "status": resp.status_code, "error": resp.text[:250]}
        return {"ok": True, **set_session(resp.json())}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:200]}"}


def _refresh(identity: Dict[str, Any]) -> Dict[str, Any]:
    c = cfg()
    refresh_token = identity.get("refresh_token")
    if not refresh_token:
        return {"ok": False}
    try:
        resp = requests.post(
            f"{c['url']}/auth/v1/token?grant_type=refresh_token",
            headers=_anon_headers(),
            json={"refresh_token": refresh_token},
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            return {"ok": False, "status": resp.status_code}
        payload = resp.json()
        identity.update({
            "access_token": payload.get("access_token"),
            "refresh_token": payload.get("refresh_token", refresh_token),
            "expires_at": payload.get("expires_at") or (int(time.time()) + int(payload.get("expires_in") or 3600)),
        })
        _save_identity(identity)
        return {"ok": True, **identity}
    except Exception:
        return {"ok": False}


def ensure_session() -> Dict[str, Any]:
    identity = _load_identity()
    if not identity.get("access_token"):
        result = sign_in_anonymous()
        return result if result.get("ok") else {}
    if int(identity.get("expires_at") or 0) - 60 < int(time.time()):
        refreshed = _refresh(identity)
        return refreshed if refreshed.get("ok") else identity
    return identity


def _device_key() -> str:
    identity = _load_identity()
    key = identity.get("device_key")
    if not key:
        key = uuid.uuid4().hex
        identity["device_key"] = key
        _save_identity(identity)
    return key


def _device_user_id() -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "zeronotice:" + _device_key()))


def _session_ok() -> bool:
    return bool(ensure_session().get("access_token"))


def _device_columns_exist() -> bool:
    """Probe once whether the fallback SQL has been applied."""
    global _DEVICE_COLUMNS
    if _DEVICE_COLUMNS is not None:
        return _DEVICE_COLUMNS
    c = cfg()
    try:
        resp = requests.get(
            f"{c['url']}/rest/v1/profiles?select=device_key&limit=1",
            headers={"apikey": c["anon_key"], "x-device-key": _device_key()},
            timeout=TIMEOUT,
        )
        _DEVICE_COLUMNS = resp.status_code == 200
    except Exception:
        _DEVICE_COLUMNS = False
    return _DEVICE_COLUMNS


def mode() -> str:
    """'auth' (anonymous JWT) | 'device' (x-device-key fallback) | 'local'."""
    if not enabled():
        return "local"
    if _session_ok():
        return "auth"
    if _device_columns_exist():
        return "device"
    return "local"


def status() -> Dict[str, Any]:
    c = cfg()
    identity = _load_identity()
    return {
        "configured": enabled(),
        "shared_write": can_write_shared(),
        "url": c["url"],
        "bucket": c["bucket"],
        "retention_days": c["retention_days"],
        "user_id": identity.get("user_id"),
        "anonymous": bool(identity.get("user_id")),
        "auth_error": _LAST_AUTH_ERROR,
        "mode": mode(),
        "per_user_sync": mode() in ("auth", "device"),
    }


# --------------------------------------------------------------------------- #
# low level
# --------------------------------------------------------------------------- #
def _request(method: str, path: str, headers: Dict[str, str], **kwargs) -> Dict[str, Any]:
    c = cfg()
    if not c["url"]:
        return {"ok": False, "skipped": True, "error": "supabase not configured"}
    try:
        resp = requests.request(method, f"{c['url']}{path}", headers=headers, timeout=TIMEOUT, **kwargs)
        if 200 <= resp.status_code < 300:
            body = None
            if resp.text:
                try:
                    body = resp.json()
                except Exception:
                    body = resp.text[:300]
            return {"ok": True, "status": resp.status_code, "data": body}
        return {"ok": False, "status": resp.status_code, "error": resp.text[:300]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:200]}"}


def _upsert(table: str, rows: List[Dict[str, Any]], on_conflict: str, service: bool = False) -> Dict[str, Any]:
    if not rows:
        return {"ok": True, "skipped": True, "count": 0}
    headers = _service_headers() if service else _user_headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    return _request(
        "POST",
        f"/rest/v1/{table}?on_conflict={urllib.parse.quote(on_conflict)}",
        headers=headers,
        json=rows,
    )


def _select(table: str, params: Dict[str, str], service: bool = False) -> Dict[str, Any]:
    headers = _service_headers() if service else _user_headers()
    query = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    return _request("GET", f"/rest/v1/{table}?{query}", headers=headers)


def _delete(table: str, params: Dict[str, str]) -> Dict[str, Any]:
    query = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    headers = _user_headers()
    headers["Prefer"] = "return=minimal"
    return _request("DELETE", f"/rest/v1/{table}?{query}", headers=headers)


# --------------------------------------------------------------------------- #
# shared notices (read: anon / write: service key)
# --------------------------------------------------------------------------- #
def fetch_notices(limit: int = 100) -> Dict[str, Any]:
    headers = _anon_headers()
    return _request(
        "GET",
        f"/rest/v1/notices?select=payload&order=deadline.asc&limit={int(limit)}",
        headers=headers,
    )


def push_notices(notices: Iterable[Dict[str, Any]], chunk: int = 50) -> Dict[str, Any]:
    rows = [_notice_row(n) for n in notices if n.get("id")]
    total = 0
    for i in range(0, len(rows), chunk):
        result = _upsert("notices", rows[i : i + chunk], "id", service=True)
        if not result.get("ok"):
            return {**result, "pushed": total}
        total += len(rows[i : i + chunk])
    return {"ok": True, "pushed": total}


def _iso(value: Any) -> Optional[str]:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).astimezone(timezone.utc).isoformat()
        except Exception:
            continue
    return None


def _notice_row(notice: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": notice.get("id"),
        "category": notice.get("category"),
        "campus": notice.get("campus"),
        "title_ko": notice.get("title_ko") or notice.get("title"),
        "deadline": _iso(notice.get("deadline")),
        "posted_date": (notice.get("posted_date") or "")[:10] or None,
        "source_url": notice.get("url"),
        "payload": notice,
        "verified_at": _iso(notice.get("verified_at")),
    }


def push_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    rows = [
        {"notice_id": nid, "payload": (p or {}).get("fields") or {}, "engine": (p or {}).get("engine")}
        for nid, p in (fields or {}).items()
    ]
    return _upsert("notice_fields", rows, "notice_id", service=True)


def push_images(images: Dict[str, Any]) -> Dict[str, Any]:
    rows = [
        {"notice_id": nid, "payload": p or {}, "checked_at": (p or {}).get("checked_at")}
        for nid, p in (images or {}).items()
    ]
    return _upsert("notice_images", rows, "notice_id", service=True)


def safe_object_path(notice_id: str, name: str) -> str:
    """Supabase Storage keys must be ASCII-safe; keep the original name in the DB."""
    ext = os.path.splitext(name or "")[1].lower()
    digest = hashlib.sha1((name or "").encode("utf-8")).hexdigest()[:12]
    return f"{notice_id}/{digest}{ext}"


def upload_attachment(notice_id: str, name: str, data: bytes, mime: str) -> Dict[str, Any]:
    """Upload with an ASCII-safe key, then register the row with the original name."""
    path = safe_object_path(notice_id, name)
    result = upload_file(path, data, mime or "application/octet-stream")
    if result.get("ok"):
        register_attachment(notice_id, name, path, mime, len(data))
    return result


def upload_file(path: str, data: bytes, content_type: str = "application/octet-stream") -> Dict[str, Any]:
    c = cfg()
    if not can_write_shared():
        return {"ok": False, "skipped": True, "error": "service key required for uploads"}
    try:
        resp = requests.post(
            f"{c['url']}/storage/v1/object/{c['bucket']}/{urllib.parse.quote(path)}",
            headers={
                "apikey": c["service_key"],
                "Authorization": f"Bearer {c['service_key']}",
                "Content-Type": content_type,
                "x-upsert": "true",
            },
            data=data,
            timeout=60.0,
        )
        if 200 <= resp.status_code < 300:
            return {
                "ok": True,
                "path": path,
                "url": f"{c['url']}/storage/v1/object/public/{c['bucket']}/{urllib.parse.quote(path)}",
                "bytes": len(data),
            }
        return {"ok": False, "status": resp.status_code, "error": resp.text[:200]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:180]}"}


def register_attachment(notice_id: str, name: str, storage_path: str, mime: str, size: int) -> Dict[str, Any]:
    return _upsert(
        "attachments",
        [{"notice_id": notice_id, "name": name, "storage_path": storage_path, "mime": mime, "bytes": size}],
        "notice_id,name",
        service=True,
    )


def purge_old(days: Optional[int] = None) -> Dict[str, Any]:
    c = cfg()
    if not can_write_shared():
        return {"ok": False, "skipped": True, "error": "service key required"}
    headers = _service_headers()
    return _request(
        "POST",
        "/rest/v1/rpc/purge_expired_notices",
        headers=headers,
        json={"days": int(days or c["retention_days"])},
    )


# --------------------------------------------------------------------------- #
# per-user data (RLS: auth.uid() in auth mode, x-device-key in fallback mode)
# --------------------------------------------------------------------------- #
def _owner() -> Dict[str, str]:
    """Who am I on this install?"""
    current = mode()
    if current == "auth":
        identity = ensure_session()
        return {"mode": "auth", "user_id": identity.get("user_id", ""), "device_key": ""}
    if current == "device":
        return {"mode": "device", "user_id": _device_user_id(), "device_key": _device_key()}
    return {"mode": "local", "user_id": "", "device_key": ""}


def _with_owner(row: Dict[str, Any]) -> Dict[str, Any]:
    owner = _owner()
    if owner["mode"] == "auth":
        row["user_id"] = owner["user_id"]
    elif owner["mode"] == "device":
        row["user_id"] = owner["user_id"]
        row["device_key"] = owner["device_key"]
    return row


def push_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    if not profile:
        return {"ok": True, "skipped": True}
    if mode() == "local":
        return {"ok": False, "skipped": True, "error": "per-user sync unavailable"}
    row = _with_owner({
        "payload": profile,
        "email": profile.get("email"),
        "student_id": profile.get("student_id"),
    })
    return _upsert("profiles", [row], "user_id")


def load_profile() -> Dict[str, Any]:
    if mode() == "local":
        return {}
    result = _select("profiles", {"select": "*", "limit": "1"})
    if result.get("ok") and result.get("data"):
        return result["data"][0].get("payload") or {}
    return {}


def push_subscriptions(subs: Dict[str, Any]) -> Dict[str, Any]:
    if mode() == "local":
        return {"ok": False, "skipped": True, "error": "per-user sync unavailable"}
    rows = [
        _with_owner({
            "notice_id": nid,
            "reminded_at": (meta or {}).get("reminded_at"),
        })
        for nid, meta in (subs or {}).items()
    ]
    return _upsert("subscriptions", rows, "user_id,notice_id")


def delete_subscription(notice_id: str) -> Dict[str, Any]:
    if mode() == "local":
        return {"ok": False, "skipped": True}
    return _delete("subscriptions", {"notice_id": f"eq.{notice_id}"})


def push_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    if mode() == "local":
        return {"ok": False, "skipped": True, "error": "per-user sync unavailable"}
    return _upsert("user_settings", [_with_owner({"payload": settings})], "user_id")


def load_settings() -> Dict[str, Any]:
    if mode() == "local":
        return {}
    result = _select("user_settings", {"select": "*", "limit": "1"})
    if result.get("ok") and result.get("data"):
        return result["data"][0].get("payload") or {}
    return {}


def push_message(role: str, content: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if mode() == "local":
        return {"ok": False, "skipped": True}
    row = _with_owner({"role": role, "content": content, "meta": meta or {}})
    return _request(
        "POST",
        "/rest/v1/assistant_messages",
        headers=_user_headers(),
        json=[row],
    )


def load_messages(limit: int = 50) -> List[Dict[str, Any]]:
    if mode() == "local":
        return []
    result = _select(
        "assistant_messages",
        {"select": "role,content,created_at", "order": "created_at.desc", "limit": str(limit)},
    )
    if result.get("ok") and isinstance(result.get("data"), list):
        return list(reversed(result["data"]))
    return []
