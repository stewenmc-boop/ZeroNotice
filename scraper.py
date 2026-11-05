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


_NOTICE_CACHE: Dict[str, Any] = {"ts": 0.0, "rows": [], "source": "local"}


def load_notices(force: bool = False) -> List[Dict[str, Any]]:
    """Shared notices: Supabase first (single source for every install), local JSON as fallback."""
    import time

    try:
        import storage

        if storage.enabled():
            if not force and _NOTICE_CACHE["rows"] and time.time() - _NOTICE_CACHE["ts"] < 60:
                return _NOTICE_CACHE["rows"]
            result = storage.fetch_notices(200)
            rows = result.get("data") or []
            payloads = [row.get("payload") for row in rows if isinstance(row, dict) and row.get("payload")]
            if result.get("ok") and payloads:
                _NOTICE_CACHE.update({"ts": time.time(), "rows": payloads, "source": "supabase"})
                return payloads
    except Exception:
        pass
    rows = load_real_knu_notices()
    _NOTICE_CACHE.update({"ts": time.time(), "rows": rows, "source": "local"})
    return rows


def notices_source() -> str:
    return _NOTICE_CACHE.get("source", "local")


def load_real_knu_notices() -> List[Dict[str, Any]]:
    if REAL_NOTICES_PATH.exists():
        with open(REAL_NOTICES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def clean_notice_title(raw_title: str) -> str:
    t = re.sub(r"\s+", " ", raw_title)
    t = re.sub(r"\s*(?:등록일|수정일|조회수|작성자).*$", "", t)
    return t.strip()


def extract_deadline_from_notice(title: str, body: str, att_text: str) -> str:
    combined = title + "\n" + body + "\n" + att_text
    
    # Range end date first (e.g. ~ 11. 12.(목) 18시, ~ 11/13, ~ 2026.11.13)
    m_end = re.search(
        r"[~～]\s*(?:202[4-7][\.\-\/])?\s*([01]?\d)[\.\-\/]\s*([0-3]?\d)(?:\([가-힣]\))?(?:\s*([0-2]?\d)(?:시|:(\d\d)))?",
        combined,
    )
    if m_end:
        mon = int(m_end.group(1))
        day = int(m_end.group(2))
        hr = int(m_end.group(3)) if m_end.group(3) else 18
        if 1 <= mon <= 12 and 1 <= day <= 31:
            return f"2026-{mon:02d}-{day:02d} {hr:02d}:00"

    # Single date pattern (e.g. 2026-11-15 18:00)
    m1 = re.search(
        r"202[4-7][\.\-\/]\s*([01]?\d)[\.\-\/]\s*([0-3]?\d)(?:\([가-힣]\))?(?:\s*([0-2]?\d)(?:시|:(\d\d)))?",
        combined,
    )
    if m1:
        mon = int(m1.group(1))
        day = int(m1.group(2))
        hr = int(m1.group(3)) if m1.group(3) else 18
        if 1 <= mon <= 12 and 1 <= day <= 31:
            return f"2026-{mon:02d}-{day:02d} {hr:02d}:00"

    fallback = datetime.now() + timedelta(days=14)
    return fallback.strftime("%Y-%m-%d 18:00")


def infer_rules_from_notice(title: str, body: str, att_text: str) -> Dict[str, Any]:
    combined = (title + " " + body + " " + att_text).lower()

    campuses = ["춘천", "삼척", "강릉", "원주"]
    if "춘천" in title and not any(c in title for c in ["삼척", "강릉", "원주"]):
        campuses = ["춘천"]
    elif "삼척" in title and "춘천" not in title:
        campuses = ["삼척"]
    elif ("강릉" in title or "원주" in title) and "춘천" not in title:
        campuses = ["강릉", "원주"]

    status_allowed = ["undergrad_kr", "intl"]
    if "재학생 지원 불가" in combined or ("졸업생" in combined and "재학생" not in title):
        if "재학생 지원 불가" in combined:
            status_allowed = ["leave_grad"]
    if "외국인" in combined and ("제외" in combined or "불가" in combined):
        status_allowed = ["undergrad_kr"]
    elif "외국인 유학생" in combined and "전용" in combined:
        status_allowed = ["intl"]

    min_gpa = 0.0
    gpa_m = re.search(r"(?:평점|성적|gpa|평점평균).*?(\d\.\d)", combined)
    if gpa_m:
        val = float(gpa_m.group(1))
        if 1.5 <= val <= 4.3:
            min_gpa = val

    max_income = 10
    inc_m = re.search(r"([0-9]|10)\s*구간", combined)
    if inc_m:
        max_income = int(inc_m.group(1))

    return {
        "campuses": campuses,
        "status_allowed": status_allowed,
        "min_gpa": min_gpa,
        "max_income": max_income,
        "note_ko": "학적 및 캠퍼스 조건 충족 시 지원 가능",
        "note_zh": "符合学籍及校区条件时可申请",
        "note_en": "Eligible if campus and status requirements are met",
    }


def generate_notice_metadata(title_ko: str, body: str, category: str) -> Dict[str, str]:
    """Generates localized titles, summaries, and benefit labels using LLM or rule-based fallback."""
    try:
        from agent import call_llm
        prompt = (
            f"Analyze this university notice and return JSON with:\n"
            f"title_zh: string\n"
            f"title_en: string\n"
            f"summary_ko: 1-2 sentences Korean summary\n"
            f"summary_zh: 1-2 sentences Chinese summary\n"
            f"summary_en: 1-2 sentences English summary\n"
            f"benefit_label_ko: short label (max 18 chars)\n"
            f"benefit_label_zh: short label\n"
            f"benefit_label_en: short label\n\n"
            f"Notice Title: {title_ko}\n"
            f"Notice Body: {body[:800]}\n"
            f"Respond ONLY in valid JSON."
        )
        res = call_llm("You are an expert academic notice processor.", prompt, max_tokens=500)
        if res.get("ok") and res.get("text"):
            raw_text = res["text"].strip()
            if "```" in raw_text:
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)
            parsed = json.loads(raw_text)
            if all(k in parsed for k in ["title_zh", "title_en", "summary_ko", "summary_zh", "summary_en"]):
                return parsed
    except Exception:
        pass

    # High-craft rule-based fallback
    return {
        "title_zh": title_ko.replace("안내", "通知").replace("모집", "招募").replace("선발", "选拔"),
        "title_en": title_ko.replace("안내", "Notice").replace("모집", "Recruitment"),
        "summary_ko": (body[:120].strip() or title_ko) + "...",
        "summary_zh": f"这是江原大学官方发布的【{title_ko}】相关通知，请确认申请资格及截止时间。",
        "summary_en": f"Kangwon National University official announcement: {title_ko}. Please check eligibility and deadline.",
        "benefit_label_ko": f"{category} 관련 지원 및 일정",
        "benefit_label_zh": f"{category}相关安排与支持",
        "benefit_label_en": f"{category} program & schedule",
    }


def parse_knu_detail_url(url: str, timeout: float = 6.0) -> Dict[str, Any]:
    """
    Fetches any live kangwon.ac.kr/ko/bbs/.../detail.do URL, parses its body,
    and extracts text from any attached .hwp / .hwpx files on the fly!
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=timeout)
    soup = BeautifulSoup(r.text, "html.parser")

    title_el = soup.select_one(".card-header")
    raw_title = title_el.get_text(" ", strip=True) if title_el else url
    title = clean_notice_title(raw_title)

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


def sync_live_knu_notices(live_check: bool = False, max_new_notices: int = 5) -> Dict[str, Any]:
    """
    Real-time synchronization against Kangwon National University official boards.
    When live_check is False: loads locally cached real notices in < 1ms.
    When live_check is True: scans the 5 boards for new posts, parses their detail pages,
    extracts attached HWP text, generates translations and rules, and prepends them!
    """
    notices = load_real_knu_notices()
    live_ok = True
    new_count = 0

    if live_check:
        try:
            # Build known URL and pstSn sets
            known_psts = set()
            for n in notices:
                url = n.get("url") or ""
                m = re.search(r"pstSn=(\d+)", url)
                if m:
                    known_psts.add(m.group(1))

            headers = {"User-Agent": "Mozilla/5.0"}
            candidates = []

            for cat, board_url in KNU_BOARDS:
                try:
                    r = requests.get(board_url, headers=headers, timeout=4.0)
                    if r.status_code != 200:
                        continue
                    soup = BeautifulSoup(r.text, "html.parser")
                    for tr in soup.select("table tbody tr"):
                        tds = [td.get_text(strip=True) for td in tr.select("td")]
                        a = tr.select_one("a")
                        if not a or not a.has_attr("href") or "pstSn=" not in a["href"]:
                            continue
                        m = re.search(r"pstSn=(\d+)", a["href"])
                        if not m:
                            continue
                        pst_sn = m.group(1)
                        if pst_sn in known_psts:
                            continue

                        # Extract metadata from table row
                        # Typical row: [번호, 캠퍼스, 제목, 작성자, 등록일시, 조회수]
                        raw_title = a.get_text(" ", strip=True)
                        title_clean = clean_notice_title(raw_title)
                        author = tds[3] if len(tds) > 3 else "강원대학교"
                        posted_date = tds[4] if len(tds) > 4 else datetime.now().strftime("%Y-%m-%d")
                        campus_code = tds[1] if len(tds) > 1 else "ALL"
                        detail_url = "https://kangwon.ac.kr" + a["href"]

                        candidates.append({
                            "pstSn": pst_sn,
                            "category": cat,
                            "title": title_clean,
                            "author": author,
                            "posted_date": posted_date,
                            "campus_code": campus_code,
                            "url": detail_url,
                        })
                except Exception:
                    continue

            # Fetch details for new candidates (up to max_new_notices)
            new_items = []
            for item in candidates[:max_new_notices]:
                try:
                    parsed = parse_knu_detail_url(item["url"], timeout=6.0)
                    title = parsed.get("title") or item["title"]
                    body = parsed.get("body") or ""
                    att_text = parsed.get("attachment_extracted_text") or ""
                    attachments = parsed.get("attachments") or []

                    rules = infer_rules_from_notice(title, body, att_text)
                    deadline = extract_deadline_from_notice(title, body, att_text)
                    meta = generate_notice_metadata(title, body, item["category"])

                    has_hwp = bool(att_text) and any(
                        a.get("name", "").lower().endswith((".hwp", ".hwpx")) for a in attachments
                    )

                    new_notice = {
                        "id": f"knu-live-{item['pstSn']}",
                        "category": item["category"],
                        "campus": item["campus_code"] if item["campus_code"] in ("춘천", "삼척", "강릉", "원주") else "ALL",
                        "title": title,
                        "author": item["author"],
                        "posted_date": item["posted_date"].replace(".", "-"),
                        "phone": parsed.get("phone") or "",
                        "email": parsed.get("email") or "",
                        "url": item["url"],
                        "body": body,
                        "char_count": len(body),
                        "attachments": attachments,
                        "attachment_extracted_text": att_text,
                        "deadline": deadline,
                        "benefit_label_ko": meta.get("benefit_label_ko", "공식 일정 및 지원"),
                        "benefit_label_zh": meta.get("benefit_label_zh", "官方通知事项"),
                        "benefit_label_en": meta.get("benefit_label_en", "Official Schedule"),
                        "benefit_krw": 0,
                        "title_ko": title,
                        "title_zh": meta.get("title_zh", title),
                        "title_en": meta.get("title_en", title),
                        "summary_ko": meta.get("summary_ko", body[:150]),
                        "summary_zh": meta.get("summary_zh", title),
                        "summary_en": meta.get("summary_en", title),
                        "rules": rules,
                        "has_hwp_extracted": has_hwp,
                        "source_status": "live_realtime",
                        "verified_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    new_items.append(new_notice)
                except Exception:
                    continue

            if new_items:
                notices = new_items + notices
                new_count = len(new_items)
                try:
                    REAL_NOTICES_PATH.write_text(
                        json.dumps(notices, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                except Exception:
                    pass

        except Exception:
            live_ok = False

    return {
        "notices": notices,
        "new_count": new_count,
        "synced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "live_portal_connected": live_ok,
    }
