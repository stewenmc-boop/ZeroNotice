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

import io
import re
import zipfile
from typing import Optional


def _xml_text(xml_bytes: bytes) -> str:
    """Crude but dependency-free text sweep over OOXML/ODF-ish XML."""
    try:
        text = xml_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return ""
    text = re.sub(r"<w:tab[^>]*/>", "\t", text)
    text = re.sub(r"<w:br[^>]*/>", "\n", text)
    text = re.sub(r"</w:p>", "\n", text)
    text = re.sub(r"</(a:p|text:p|row|si|c)>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&apos;", "'")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_docx_bytes(raw_bytes: bytes) -> str:
    """.docx = zip + word/document.xml (+ headers/footers)."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            parts = [
                name
                for name in zf.namelist()
                if name.startswith("word/") and name.endswith(".xml")
                and ("document" in name or "header" in name or "footer" in name)
            ]
            chunks = [_xml_text(zf.read(name)) for name in sorted(parts)]
            return "\n".join(chunk for chunk in chunks if chunk)[:20000]
    except Exception:
        return ""


def extract_xlsx_bytes(raw_bytes: bytes) -> str:
    """.xlsx = zip of sharedStrings + worksheets; no openpyxl needed."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            shared: list[str] = []
            if "xl/sharedStrings.xml" in zf.namelist():
                shared_xml = _xml_text(zf.read("xl/sharedStrings.xml"))
                shared = [line.strip() for line in shared_xml.split("\n") if line.strip()]
            sheets = sorted(
                name
                for name in zf.namelist()
                if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
            )
            rows_out = []
            for sheet in sheets[:3]:
                xml = zf.read(sheet).decode("utf-8", errors="ignore")
                for row in re.findall(r"<row[^>]*>(.*?)</row>", xml, re.S):
                    cells = []
                    for cell in re.findall(r"<c[^>]*?(?:t=\"(\w+)\")?[^>]*>(.*?)</c>", row, re.S):
                        ctype, inner = cell
                        value = re.search(r"<v>(.*?)</v>", inner, re.S)
                        inline = re.search(r"<is>(.*?)</is>", inner, re.S)
                        text = ""
                        if inline:
                            text = _xml_text(inline.group(1))
                        elif value:
                            raw_value = value.group(1)
                            if ctype == "s":
                                try:
                                    text = shared[int(raw_value)]
                                except Exception:
                                    text = raw_value
                            else:
                                text = raw_value
                        if text:
                            cells.append(text.strip())
                    if cells:
                        rows_out.append(" | ".join(cells))
            return "\n".join(rows_out)[:20000]
    except Exception:
        return ""


def extract_pdf_bytes(raw_bytes: bytes) -> str:
    """PDF via pypdf when available; empty string otherwise."""
    try:
        from pypdf import PdfReader  # imported lazily: optional dependency
    except Exception:
        return ""
    try:
        reader = PdfReader(io.BytesIO(raw_bytes))
        pages = []
        for page in reader.pages[:20]:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(pages).strip()[:20000]
    except Exception:
        return ""


def extract_attachment_text(filename: str, raw_bytes: bytes) -> str:
    """Dispatch by extension. Returns '' for unsupported or scanned files."""
    name = (filename or "").lower()
    if name.endswith(".hwpx"):
        return extract_hwpx_bytes(raw_bytes)
    if name.endswith(".hwp"):
        return extract_hwp_bytes(raw_bytes)
    if name.endswith(".docx"):
        return extract_docx_bytes(raw_bytes)
    if name.endswith((".xlsx", ".xlsm")):
        return extract_xlsx_bytes(raw_bytes)
    if name.endswith(".pdf"):
        return extract_pdf_bytes(raw_bytes)
    return ""


SUPPORTED_ATTACHMENT_EXTS = (".hwp", ".hwpx", ".docx", ".xlsx", ".xlsm", ".pdf")


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
    phone = phone_m.group(0) if phone_m else ""
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
            if len(extracted_att_texts) < 3 and fn.lower().endswith(SUPPORTED_ATTACHMENT_EXTS):
                try:
                    fr = requests.get(furl, headers=headers, timeout=12.0)
                    if fr.status_code == 200 and len(fr.content) < 12_000_000:
                        t = extract_attachment_text(fn, fr.content)
                        if len(t) > 30:
                            extracted_att_texts.append(f"[{fn} 추출 원문]\n{t[:4000]}")
                        else:
                            extracted_att_texts.append(
                                f"[{fn} — 텍스트 추출 실패(스캔본/암호화/구형 바이너리 가능)]"
                            )
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
