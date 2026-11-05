"""Push shared ZeroNotice data to Supabase (owner machine only).

Needs SUPABASE_URL + SUPABASE_SERVICE_KEY (service_role). Never ships with the
desktop build.

    python scripts/sync_supabase.py            # notices + fields + images + files
    python scripts/sync_supabase.py --no-files # skip attachment uploads
    python scripts/sync_supabase.py --purge    # also delete rows older than 30 days
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import storage  # noqa: E402

DATA = ROOT / "data"
UPLOAD_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".xlsx", ".docx", ".hwp", ".hwpx")
MAX_BYTES = 15 * 1024 * 1024
MIME = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
    ".webp": "image/webp", ".pdf": "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".hwp": "application/x-hwp", ".hwpx": "application/x-hwpx",
}


def load(name, default):
    path = DATA / name
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def fetch(url: str) -> bytes:
    req = urllib.request.Request(
        urllib.parse.quote(url, safe=":/?&=#"), headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-files", action="store_true")
    ap.add_argument("--purge", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    status = storage.status()
    print("supabase:", status)
    if not status["configured"] or not status["shared_write"]:
        print("!! SUPABASE_URL / SUPABASE_SERVICE_KEY 가 필요합니다.")
        return 2

    notices = load("real_knu_notices.json", [])
    # never push rows the retention policy would delete right away
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=30)
    kept = []
    for n in notices:
        try:
            posted = datetime.strptime((n.get("posted_date") or "")[:10], "%Y-%m-%d")
        except Exception:
            kept.append(n)
            continue
        if posted >= cutoff:
            kept.append(n)
        else:
            print(f"  [retention] skip {n.get('id')} (posted {n.get('posted_date')})")
    notices = kept
    if args.limit:
        notices = notices[: args.limit]
    print(f"notices: {len(notices)} 건 push…")
    print("  →", storage.push_notices(notices))

    fields = load("notice_fields.json", {})
    print(f"fields: {len(fields)} 건 push…")
    print("  →", storage.push_fields(fields))

    images = load("notice_images.json", {})
    print(f"images: {len(images)} 건 push…")
    print("  →", storage.push_images(images))

    if not args.no_files:
        uploaded = skipped = failed = 0
        for notice in notices:
            nid = notice.get("id")
            for att in notice.get("attachments", []):
                name = att.get("name") or ""
                if not name.lower().endswith(UPLOAD_EXT):
                    continue
                url = att.get("url") or ""
                if url.startswith("/"):
                    url = "https://kangwon.ac.kr" + url
                try:
                    raw = fetch(url)
                except Exception as exc:  # noqa: BLE001
                    print(f"  [fail] {nid} {name}: {exc}")
                    failed += 1
                    continue
                if len(raw) > MAX_BYTES:
                    print(f"  [skip] {nid} {name}: {len(raw) // 1024}KB > 8MB")
                    skipped += 1
                    continue
                ext = Path(name).suffix.lower()
                up = storage.upload_attachment(nid, name, raw, MIME.get(ext, "application/octet-stream"))
                if not up.get("ok"):
                    print(f"  [fail] upload {nid} {name}: {up.get('error')}")
                    failed += 1
                    continue
                uploaded += 1
                print(f"  [ok]   {nid} {name} ({len(raw) // 1024}KB)")
        print(f"files: uploaded={uploaded} skipped={skipped} failed={failed}")

    if args.purge:
        print("purge >30d:", storage.purge_old(30))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
