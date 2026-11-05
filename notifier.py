"""SMTP delivery for calendar reminders (.ics) and deadline digests.

Credentials come from the environment only (never from the repo):
    SMTP_HOST=smtp.qq.com
    SMTP_PORT=465
    SMTP_USER=1541881974@qq.com
    SMTP_AUTH_CODE=<16 char authorization code>
    SMTP_FROM_NAME=ZeroNotice
"""

import os
import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv

load_dotenv()


def smtp_config() -> Dict[str, Any]:
    return {
        "host": os.getenv("SMTP_HOST", "smtp.qq.com").strip(),
        "port": int(os.getenv("SMTP_PORT", "465") or 465),
        "user": (os.getenv("SMTP_USER") or "").strip(),
        "auth_code": (os.getenv("SMTP_AUTH_CODE") or "").strip(),
        "from_name": (os.getenv("SMTP_FROM_NAME") or "ZeroNotice").strip(),
    }


def smtp_status() -> Dict[str, Any]:
    cfg = smtp_config()
    user = cfg["user"]
    masked = ""
    if user:
        local, _, domain = user.partition("@")
        masked = (local[:3] + "***@" + domain) if local else user
    return {
        "configured": bool(user and cfg["auth_code"]),
        "host": cfg["host"],
        "port": cfg["port"],
        "user": masked,
        "from_name": cfg["from_name"],
    }


def send_mail(
    to_email: str,
    subject: str,
    body_text: str,
    attachments: List[Tuple[str, bytes, str]] | None = None,
) -> Dict[str, Any]:
    """attachments: [(filename, raw_bytes, mime_subtype)] e.g. ('a.ics', b'..', 'calendar')."""
    cfg = smtp_config()
    if not (cfg["user"] and cfg["auth_code"]):
        return {"ok": False, "error": "SMTP 자격증명이 없습니다. .env 의 SMTP_USER / SMTP_AUTH_CODE 를 확인하세요."}
    if not to_email or "@" not in to_email:
        return {"ok": False, "error": "수신 이메일 형식이 올바르지 않습니다."}

    message = MIMEMultipart()
    message["From"] = formataddr([cfg["from_name"], cfg["user"]])
    message["To"] = formataddr(["", to_email])
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=True)
    message.attach(MIMEText(body_text, "plain", "utf-8"))

    for filename, payload, subtype in attachments or []:
        part = MIMEBase("text", subtype)
        part.set_payload(payload)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename=filename)
        part.add_header("Content-Class", "urn:content-classes:calendarmessage")
        message.attach(part)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=context, timeout=25) as server:
            server.login(cfg["user"], cfg["auth_code"])
            server.sendmail(cfg["user"], [to_email], message.as_string())
        return {"ok": True, "to": to_email, "attachments": len(attachments or [])}
    except smtplib.SMTPAuthenticationError as exc:
        return {"ok": False, "error": f"SMTP 인증 실패(535). QQ메일은 '인증코드'가 필요합니다: {exc.smtp_code}"}
    except Exception as exc:  # noqa: BLE001 - never crash the demo
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:180]}"}
