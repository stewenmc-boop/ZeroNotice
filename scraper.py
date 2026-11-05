import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).parent / "data"
REAL_NOTICES_PATH = DATA_DIR / "real_knu_notices.json"

KNU_BOARDS = [
    ("장학", "https://kangwon.ac.kr/ko/bbs/721/list.do"),
    ("학사", "https://kangwon.ac.kr/ko/bbs/720/list.do"),
    ("공모", "https://kangwon.ac.kr/ko/bbs/719/list.do"),
    ("일반", "https://kangwon.ac.kr/ko/bbs/504/list.do"),
    ("행사", "https://kangwon.ac.kr/ko/bbs/715/list.do"),
]


def extract_hwpx_bytes(raw_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
            texts = []
            for name in sorted(z.namelist()):
                if name.startswith("Contents/section") and name.endswith(".xml"):
                    root = ET.fromstring(z.read(name))
                    for elem in root.iter():
                        if elem.text and elem.text.strip():
                            texts.append(elem.text.strip())
            return "\n".join(texts)
    except Exception:
        return ""


def extract_hwp_bytes(raw_bytes: bytes) -> str:
    try:
        txt16 = raw_bytes.decode("utf-16le", errors="ignore")
        matches = re.findall(
            r"[가-힣a-zA-Z0-9\s\.\,\-\(\)\[\]\~\:\!\?\%\/\@★○□■◇◆※ㆍ]{25,}", txt16
        )
        cleaned = [m.strip() for m in matches if len(re.findall(r"[가-힣]", m)) >= 10]
        return "\n".join(cleaned[:8])
    except Exception:
        return ""


def load_real_knu_notices() -> List[Dict[str, Any]]:
    if REAL_NOTICES_PATH.exists():
        with open(REAL_NOTICES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def parse_knu_detail_url(url: str, timeout: float = 6.0) -> Dict[str, Any]:
    """
    Fetches any live kangwon.ac.kr/ko/bbs/.../detail.do URL, parses its body,
    and extracts text from any attached .hwp / .hwpx files on the fly!
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=timeout)
    soup = BeautifulSoup(r.text, "html.parser")

    title_el = soup.select_one(".card-header")
    title = re.sub(r"\s+", " ", title_el.get_text(" ", strip=True)) if title_el else url

    editor = soup.select_one(".editor-wrap")
    body_text = editor.get_text("\n", strip=True) if editor else ""

    card_text = (
        soup.select_one(".card.detail").get_text(" ", strip=True)
        if soup.select_one(".card.detail")
        else ""
    )
    phone_m = re.search(r"033-\d{3}-\d{4}", card_text + " " + body_text)
    phone = phone_m.group(0) if phone_m else "033-250-6114"
    email_m = re.search(
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", body_text
    )
    email = email_m.group(0).rstrip(".") if email_m else ""

    attachments = []
    extracted_att_texts = []
    for fa in soup.select(".view-file-item a, .view-file-list a"):
        if fa.get("href"):
            fn = re.sub(r"chevron_forward$", "", fa.get_text(strip=True)).strip()
            furl = (
                "https://kangwon.ac.kr" + fa["href"]
                if fa["href"].startswith("/")
                else fa["href"]
            )
            attachments.append({"name": fn, "url": furl})
            if len(extracted_att_texts) < 2 and (
                fn.lower().endswith(".hwpx") or fn.lower().endswith(".hwp")
            ):
                try:
                    fr = requests.get(furl, headers=headers, timeout=5.0)
                    if fr.status_code == 200:
                        t = (
                            extract_hwpx_bytes(fr.content)
                            if fn.lower().endswith(".hwpx")
                            else extract_hwp_bytes(fr.content)
                        )
                        if len(t) > 30:
                            extracted_att_texts.append(f"[{fn} 추출 원문]\n{t[:2500]}")
                except Exception:
                    pass

    return {
        "title": title,
        "url": url,
        "phone": phone,
        "email": email,
        "body": body_text,
        "attachment_extracted_text": "\n\n".join(extracted_att_texts),
        "attachments": attachments,
    }


def sync_live_knu_notices(live_check: bool = False) -> Dict[str, Any]:
    notices = load_real_knu_notices()
    live_ok = True
    if live_check:
        try:
            r = requests.get(
                "https://kangwon.ac.kr/ko/bbs/721/list.do",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=3.0,
            )
            live_ok = r.status_code == 200
        except Exception:
            live_ok = False

    return {
        "notices": notices,
        "synced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "live_portal_connected": live_ok,
    }
