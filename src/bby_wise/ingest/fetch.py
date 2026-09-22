"""Polite HTTP fetching: identifiable UA, spacing, conditional GET."""

from __future__ import annotations

import time

import httpx

USER_AGENT = "bby_wise/0.1 (+personal research project)"
DEFAULT_DELAY = 1.0


class PoliteFetcher:
    def __init__(self, delay: float = DEFAULT_DELAY, timeout: float = 30.0):
        self.delay = delay
        self._last = 0.0
        self._client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
            follow_redirects=True,
        )

    def get(
        self,
        url: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> httpx.Response:
        wait = self.delay - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        headers: dict[str, str] = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        try:
            return self._client.get(url, headers=headers)
        finally:
            self._last = time.monotonic()
