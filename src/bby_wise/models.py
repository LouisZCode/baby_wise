from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

EVENT_TYPES = ("feeding", "weight", "sleep", "meds", "u_exam")
CHAT_VISIBILITY = ("shared", "private")


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class Child(Base):
    __tablename__ = "children"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120))
    birthdate: Mapped[dt.date]
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )

    events: Mapped[list[Event]] = relationship(
        back_populates="child", cascade="all, delete-orphan"
    )


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    child_id: Mapped[str] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE")
    )
    type: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    note: Mapped[str | None] = mapped_column(Text, default=None)

    child: Mapped[Child] = relationship(back_populates="events")


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    visibility: Mapped[str] = mapped_column(String(16), default="shared")
    author: Mapped[str | None] = mapped_column(String(120), default=None)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )

    messages: Mapped[list[Message]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )


MESSAGE_ROLES = ("user", "assistant")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    chat_id: Mapped[str] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    lang: Mapped[str] = mapped_column(String(8), default="de")
    # Assistant messages: source URLs behind the answer (empty = don't-know).
    sources: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )

    chat: Mapped[Chat] = relationship(back_populates="messages")


class GuidelineChunk(Base):
    __tablename__ = "guideline_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source: Mapped[str] = mapped_column(String(16), index=True)  # biog | nhs
    source_url: Mapped[str] = mapped_column(Text, index=True)
    title: Mapped[str | None] = mapped_column(String(512), default=None)
    text: Mapped[str] = mapped_column(Text)
    lang: Mapped[str] = mapped_column(String(8))
    guideline_version: Mapped[str | None] = mapped_column(
        String(64), default=None
    )
    published_date: Mapped[dt.date | None] = mapped_column(
        Date, default=None
    )
    crawl_date: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16), default="live")
    precedence_key: Mapped[str | None] = mapped_column(
        String(256), default=None, index=True
    )
    topics: Mapped[list] = mapped_column(JSON, default=list)
    # Bilingual store: translations are rows, not columns. A translated row
    # points at its source chunk; retrieval filters by `lang`.
    translation_of: Mapped[str | None] = mapped_column(String(36), default=None)
    # FTS: populated by a Postgres trigger (migration); TEXT on sqlite.
    search_tsv: Mapped[str | None] = mapped_column(
        TSVECTOR().with_variant(Text(), "sqlite"), nullable=True
    )


class Linkout(Base):
    __tablename__ = "linkouts"
    __table_args__ = (UniqueConstraint("topic", "url"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    topic: Mapped[str] = mapped_column(String(256), index=True)
    url: Mapped[str] = mapped_column(Text)
    lastmod: Mapped[str | None] = mapped_column(String(32), default=None)
    crawl_date: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )
