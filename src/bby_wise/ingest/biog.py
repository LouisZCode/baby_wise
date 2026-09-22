"""BIÖG: FAQ index crawl (paginated) + sitemap for topic passes."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from .chunk import chunk_faq, precedence_key
from .extract import extract_main
from .fetch import PoliteFetcher
from .load import upsert_chunk
from .screen import screen
from .sitemap import parse_sitemap, sitemap_kind
from .topics import infer_topics

SITEMAP = "https://www.kindergesundheit-info.de/sitemap.xml"
BASE = "https://www.kindergesundheit-info.de"
FAQ_INDEX = BASE + "/themen/faq/"
_FAQ_SLUG = re.compile(r"/themen/faq/[a-z0-9äöü-]+/$")


def collect_urls(fetcher: PoliteFetcher) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    def walk(loc: str) -> None:
        if loc in seen:
            return
        seen.add(loc)
        r = fetcher.get(loc)
        r.raise_for_status()
        if sitemap_kind(r.text) == "index":
            for sub, _ in parse_sitemap(r.text):
                walk(sub)
        else:
            urls.extend([u for u, _ in parse_sitemap(r.text)])

    walk(SITEMAP)
    return urls


def collect_faq_urls(fetcher: PoliteFetcher) -> list[str]:
    """BFS over the paginated FAQ index; harvest /themen/faq/<slug>/ links."""
    found: list[str] = []
    visited: set[str] = set()
    queue = [FAQ_INDEX]
    while queue:
        page = queue.pop(0)
        if page in visited:
            continue
        visited.add(page)
        r = fetcher.get(page)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if _FAQ_SLUG.fullmatch(href):
                url = BASE + href
                if url not in found:
                    found.append(url)
            elif "tx_bzgairfaq" in href and "currentPage" in href:
                url = urljoin(page, href)
                if not url.startswith(("http://", "https://")):
                    continue
                if url not in visited and url not in queue:
                    queue.append(url)
    return found


def crawl_faq(
    db: Session, fetcher: PoliteFetcher, limit: int | None = None
) -> dict[str, int]:
    stats = {
        "inserted": 0, "unchanged": 0, "superseded": 0,
        "quarantined": 0, "empty": 0, "failed": 0,
    }
    urls = collect_faq_urls(fetcher)
    if limit is not None:
        urls = urls[:limit]
    for url in urls:
        r = fetcher.get(url)
        if r.status_code != 200:
            stats["failed"] += 1
            continue
        doc = extract_main(r.text)
        if not doc["text"]:
            stats["empty"] += 1
            continue
        for part in chunk_faq(doc["title"], doc["text"]):
            flags = screen(part["text"])
            action, _ = upsert_chunk(
                db,
                source="biog",
                url=url,
                title=doc["title"],
                text=part["text"],
                lang="de",
                precedence_key=precedence_key(part["heading"]),
                topics=infer_topics(url, doc["title"]),
                quarantined=bool(flags),
            )
            stats[action] += 1
            if flags:
                stats["quarantined"] += 1
    return stats
