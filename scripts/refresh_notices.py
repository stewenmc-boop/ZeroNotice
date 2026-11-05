"""Refresh data/real_knu_notices.json from live kangwon.ac.kr pages.

For every notice with a source URL:
  - fetch the detail page,
  - re-extract body text, phone, email, attachments,
  - download up to 3 attachments (.pdf/.xlsx/.docx/.hwp/.hwpx) and extract text,
  - keep the existing title/summary/translations, but record the live title,
  - stamp `verified_at` and `source_status`.

Only successful fetches are written, so a network hiccup never destroys data.

Usage:  python scripts/refresh_notices.py [--limit N] [--delay 1.5]
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scraper import parse_knu_detail_url  # noqa: E402

DATA_PATH = ROOT / "data" / "real_knu_notices.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="only first N notices")
    ap.add_argument("--delay", type=float, default=1.5, help="sleep between requests")
    args = ap.parse_args()

    notices = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    targets = notices[: args.limit] if args.limit else notices

    ok = fail = 0
    for notice in targets:
        url = (notice.get("url") or "").strip()
        if not url:
            continue
        try:
            page = parse_knu_detail_url(url)
        except Exception as exc:  # noqa: BLE001
            print(f"[skip] {notice['id']} {type(exc).__name__}: {exc}")
            fail += 1
            time.sleep(args.delay)
            continue

        body = (page.get("body") or "").strip()
        if len(body) < 40 and not page.get("attachment_extracted_text"):
            print(f"[skip] {notice['id']} empty body")
            fail += 1
            time.sleep(args.delay)
            continue

        notice["body"] = body or notice.get("body", "")
        notice["char_count"] = len(notice["body"])
        notice["attachments"] = page.get("attachments") or notice.get("attachments", [])
        notice["attachment_extracted_text"] = page.get("attachment_extracted_text") or ""
        notice["has_hwp_extracted"] = bool(
            notice["attachment_extracted_text"]
        ) and any(
            (a.get("name", "").lower().endswith((".hwp", ".hwpx")))
            for a in notice["attachments"]
        )
        if page.get("phone"):
            notice["phone"] = page["phone"]
        if page.get("email"):
            notice["email"] = page["email"]
        notice["source_title"] = page.get("title", "")
        notice["verified_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        notice["source_status"] = "live"
        ok += 1
        print(
            f"[ok]   {notice['id']} body={len(notice['body'])} att={len(notice['attachments'])} "
            f"text={len(notice['attachment_extracted_text'])}"
        )
        time.sleep(args.delay)

    DATA_PATH.write_text(
        json.dumps(notices, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nrefreshed: {ok} ok, {fail} failed, {len(notices)} total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
