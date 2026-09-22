"""HTML -> {title, text}. Trafilatura first, structural fallback."""

from __future__ import annotations

import trafilatura
from bs4 import BeautifulSoup

_STRIP = ("script", "style", "nav", "header", "footer", "aside")


def extract_main(html: str) -> dict[str, str | None]:
    text = trafilatura.extract(html, include_comments=False, include_tables=True)
    soup = BeautifulSoup(html, "lxml")
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else None
    if not text:
        for tag in soup(_STRIP):
            tag.decompose()
        main = soup.find("main") or soup.find("article") or soup.body
        text = main.get_text("\n", strip=True) if main else ""
        if title is None and soup.title and soup.title.string:
            title = soup.title.string.strip()
    return {"title": title, "text": text or ""}
