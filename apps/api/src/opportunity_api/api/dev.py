"""Dev-only testing console: serves a self-contained HTML page at /dev/console.

The page is a manual test harness for the API. It signs in directly against
Supabase Auth (GoTrue) using the browser-safe publishable key, then calls the
API with the resulting bearer token.

Nothing here exposes privileged credentials: /dev/config returns only the
Supabase project URL and the publishable key, both of which are already
public by design.
"""

from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Response
from fastapi.responses import HTMLResponse

from ..core.config import get_settings

router = APIRouter(tags=["dev"])

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@lru_cache
def _console_html() -> str:
    return (_STATIC_DIR / "dev_console.html").read_text(encoding="utf-8")


@router.get("/dev/config")
def dev_config() -> dict[str, str]:
    """Browser-safe config so the console can prefill the sign-in form."""
    settings = get_settings()
    return {
        "supabase_url": settings.supabase_url,
        "publishable_key": settings.supabase_publishable_key,
    }


@router.get("/dev/console", response_class=HTMLResponse)
def dev_console() -> Response:
    return HTMLResponse(_console_html())
