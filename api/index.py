"""Vercel entry point (ASGI).

Vercel's Python runtime imports this module and looks for `app`.
Everything else (routing, static files, /api/*) is handled by the FastAPI app.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app  # noqa: E402,F401
