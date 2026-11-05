"""Filesystem layout that also works on read-only serverless hosts (Vercel).

Bundled data ships inside the repo (`data/`), but runtime writes must go to a
writable directory. Order of preference:

1. $DATA_DIR (set this to /tmp/zeronotice on Vercel)
2. ./data next to the code (normal machine)
3. /tmp/zeronotice (fallback when ./data is not writable)

Read-only helpers copy a bundled seed file into the writable directory on first
use, so the app still sees its JSON cache after a cold start.
"""

import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent
BUNDLED_DATA = BASE_DIR / "data"


def _pick_dir() -> Path:
    explicit = os.getenv("DATA_DIR", "").strip()
    if explicit:
        target = Path(explicit)
    elif os.getenv("VERCEL"):
        target = Path("/tmp/zeronotice")
    else:
        target = BUNDLED_DATA
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return target
    except Exception:
        fallback = Path("/tmp/zeronotice")
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


DATA_DIR = _pick_dir()


def writable(name: str, seed: bool = True) -> Path:
    """Path inside the writable dir; seeds it from the bundled copy if needed."""
    target = DATA_DIR / name
    if seed and not target.exists():
        source = BUNDLED_DATA / name
        if source.exists() and source.resolve() != target.resolve():
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            except Exception:
                pass
    return target


def readable(name: str) -> Path:
    """Prefer the writable copy, fall back to the bundled one."""
    target = DATA_DIR / name
    if target.exists():
        return target
    return BUNDLED_DATA / name


def is_writable() -> bool:
    return DATA_DIR != BUNDLED_DATA
