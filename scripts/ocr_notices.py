"""OCR poster/image attachments and pull links, emails, phones out of them.

Korean OCR is not installed on this machine, but the Windows OCR engine still
recognises latin fragments inside Korean posters - which is exactly where the
application URL, e-mail and phone number live. We keep the raw OCR text, then
validate every link with a real HTTP request so we never show a dead URL.

Output: data/notice_images.json
  { "<notice_id>": { "images": [{name, chars, text}], "links": [...],
                     "emails": [...], "phones": [...], "checked_at": "..." } }

Usage: python scripts/ocr_notices.py [--limit N] [--force]
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "real_knu_notices.json"
OUT = ROOT / "data" / "notice_images.json"
PS1 = ROOT / "scripts" / "ocr_image.ps1"

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
URL_RE = re.compile(r"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%\-]+", re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"0\d{1,2}[\s.\-·]{1,3}\d{3,4}[\s.\-·]{1,3}\d{4}")


def abs_url(url: str) -> str:
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return "https://kangwon.ac.kr" + url
    return url


def download(url: str, dest: Path, timeout: float = 25.0) -> bool:
    try:
        req = urllib.request.Request(
            urllib.parse.quote(abs_url(url), safe=":/?&=#"),
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        if len(data) > 15_000_000:
            return False
        dest.write_bytes(data)
        return True
    except Exception:
        return False


def ocr(path: Path, timeout: float = 120.0) -> str:
    try:
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(PS1),
                "-Path",
                str(path),
            ],
            capture_output=True,
            timeout=timeout,
        )
        out = (proc.stdout or b"").decode("utf-8", errors="ignore")
        return "\n".join(line for line in out.splitlines() if not line.startswith("# engine"))
    except Exception:
        return ""


def check_link(url: str, timeout: float = 10.0):
    """Return the URL that really answers (with OCR fixes), else None."""
    candidates = [url]
    fixed = url.replace("cIoud", "cloud").replace("ClOUD", "CLOUD")
    if fixed != url:
        candidates.insert(0, fixed)
    for candidate in candidates:
        for method in ("HEAD", "GET"):
            try:
                req = urllib.request.Request(
                    candidate, method=method, headers={"User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if 200 <= resp.status < 400:
                        return candidate
            except Exception:
                continue
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    notices = json.loads(DATA.read_text(encoding="utf-8"))
    existing = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    targets = notices[: args.limit] if args.limit else notices

    tmp = Path(tempfile.mkdtemp(prefix="ocr-"))
    done = 0
    for notice in targets:
        nid = notice["id"]
        if not args.force and nid in existing:
            continue
        images = [
            a
            for a in notice.get("attachments", [])
            if a.get("name", "").lower().endswith(IMAGE_EXT)
        ][:2]
        if not images:
            continue

        texts, links, emails, phones = [], [], [], []
        for idx, att in enumerate(images):
            dest = tmp / f"{nid}-{idx}{Path(att['name']).suffix or '.png'}"
            if not download(att.get("url", ""), dest):
                print(f"[skip-img] {nid} {att['name']}")
                continue
            text = ocr(dest)
            texts.append({"name": att["name"], "chars": len(text), "text": text})
            links += URL_RE.findall(text)
            emails += EMAIL_RE.findall(text)
            phones += PHONE_RE.findall(text)
            print(f"[ocr] {nid} {att['name']} chars={len(text)}")

        if not texts:
            continue

        clean_links = []
        for link in dict.fromkeys(link.rstrip(".,);") for link in links):
            verified = check_link(link)
            if verified and verified not in clean_links:
                clean_links.append(verified)
        existing[nid] = {
            "images": texts,
            "links": clean_links,
            "rejected_links": [
                link for link in dict.fromkeys(links) if link not in clean_links
            ][:5],
            "emails": sorted(set(emails)),
            "phones": sorted(set(phones)),
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        done += 1
        OUT.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nimages processed: {done}, notices in store: {len(existing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
