"""Chunking: FAQ pages = one chunk; topic pages = split on H2."""

from __future__ import annotations

import re
import unicodedata

from bs4 import BeautifulSoup


def precedence_key(*parts: str) -> str:
    slug = "-".join(p for p in parts if p)
    slug = re.sub(r"[–—−]", "-", slug)  # en/em dash, minus -> hyphen
    slug = unicodedata.normalize("NFKD", slug).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")


def chunk_faq(title: str | None, text: str) -> list[dict[str, str]]:
    return [{"heading": title or "", "text": text}]


def chunk_by_h2(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()
    root = soup.find("main") or soup.find("article") or soup.body
    if root is None:
        return []
    chunks: list[dict[str, str]] = []
    heading: str | None = None
    buf: list[str] = []

    def flush() -> None:
        if buf and heading:
            chunks.append({"heading": heading, "text": "\n".join(buf)})
        buf.clear()

    for el in root.find_all(["h2", "p", "li"], recursive=True):
        if el.name == "h2":
            flush()
            heading = el.get_text(strip=True)
        else:
            t = el.get_text(strip=True)
            if t:
                buf.append(t)
    flush()
    if not chunks and buf:
        chunks.append({"heading": "", "text": "\n".join(buf)})
    return chunks
