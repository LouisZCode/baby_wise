"""AAP: sitemap parse only -> link-out table. No content fetch."""

from __future__ import annotations

from urllib.parse import unquote, urlparse

from sqlalchemy.orm import Session

from .fetch import PoliteFetcher
from .load import upsert_linkout
from .sitemap import parse_sitemap_bytes

SITEMAP = "https://www.healthychildren.org/sitemap.xml"
_SKIP = ("Pages", "Search", "WorkflowTasks")


def topic_for(url: str) -> str | None:
    parts = [unquote(p) for p in urlparse(url).path.split("/") if p]
    if "English" not in parts:
        return None
    tail = parts[parts.index("English") + 1 :]
    tail = [p for p in tail if p not in _SKIP and not p.endswith(".aspx")]
    if not tail:
        return None
    return "/".join(tail).lower()


def load_linkouts(
    db: Session, fetcher: PoliteFetcher, limit: int | None = None
) -> dict[str, int]:
    stats = {"inserted": 0, "unchanged": 0}
    r = fetcher.get(SITEMAP)
    r.raise_for_status()
    items = parse_sitemap_bytes(r.content)
    if limit is not None:
        items = items[:limit]
    for loc, lastmod in items:
        topic = topic_for(loc)
        if topic is None:
            continue
        action, _ = upsert_linkout(db, topic=topic, url=loc, lastmod=lastmod)
        stats[action] += 1
    return stats
