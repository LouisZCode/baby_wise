"""Loading: hash-gated upserts. Hash decides change; old rows supersede."""

from __future__ import annotations

import datetime as dt
import hashlib

from sqlalchemy.orm import Session

from ..models import GuidelineChunk, Linkout


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def upsert_chunk(
    db: Session,
    *,
    source: str,
    url: str,
    title: str | None,
    text: str,
    lang: str,
    precedence_key: str | None = None,
    topics: list[str] | None = None,
    published_date: dt.date | None = None,
    guideline_version: str | None = None,
    quarantined: bool = False,
) -> tuple[str, GuidelineChunk]:
    h = sha256(text)
    existing = (
        db.query(GuidelineChunk)
        .filter_by(source_url=url, status="live")
        .one_or_none()
    )
    if existing is not None and existing.content_hash == h:
        return ("unchanged", existing)
    if existing is not None:
        existing.status = "superseded"
    chunk = GuidelineChunk(
        source=source,
        source_url=url,
        title=title,
        text=text,
        lang=lang,
        precedence_key=precedence_key,
        topics=topics or [],
        published_date=published_date,
        guideline_version=guideline_version,
        content_hash=h,
        crawl_date=_now(),
        status="quarantined" if quarantined else "live",
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return ("superseded" if existing is not None else "inserted", chunk)


def upsert_linkout(
    db: Session,
    *,
    topic: str,
    url: str,
    lastmod: str | None = None,
) -> tuple[str, Linkout]:
    existing = db.query(Linkout).filter_by(topic=topic, url=url).one_or_none()
    if existing is not None:
        existing.lastmod = lastmod
        existing.crawl_date = _now()
        db.commit()
        db.refresh(existing)
        return ("unchanged", existing)
    row = Linkout(topic=topic, url=url, lastmod=lastmod, crawl_date=_now())
    db.add(row)
    db.commit()
    db.refresh(row)
    return ("inserted", row)
