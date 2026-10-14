"""Fixed-window per-client-IP rate limiting (in-memory, per process)."""

import time
from collections import defaultdict

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .config import get_settings

_SKIP_PATHS = {"/health", "/health/db"}
_WINDOW_SECONDS = 60


class RateLimitMiddleware:
    """Reject clients exceeding the per-minute limit with 429.

    Counts requests per direct client host in a fixed 60-second window.
    Disabled when ``APP_RATE_LIMIT_PER_MINUTE`` is 0 or negative; health
    check paths are never counted.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._window_start = time.monotonic()
        self._hits: defaultdict[str, int] = defaultdict(int)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        limit = get_settings().rate_limit_per_minute
        if limit <= 0 or scope["path"] in _SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        host = client[0] if client else "unknown"
        if time.monotonic() - self._window_start >= _WINDOW_SECONDS:
            self._window_start = time.monotonic()
            self._hits.clear()
        self._hits[host] += 1
        if self._hits[host] > limit:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": "Rate limit exceeded. Try again later.",
                        "details": None,
                    }
                },
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
