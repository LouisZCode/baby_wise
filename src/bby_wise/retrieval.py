"""v0 retrieval: token-overlap scorer over live chunks.

No embeddings, no vector store — deterministic keyword retrieval that is
good enough for the 109-row FAQ slice and honest about it. Replaced by
vector search when the corpus outgrows it (see architecture §11).
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from .models import GuidelineChunk

STOPWORDS = frozenset(
    "der die das den dem ein eine einer eines einem einen und oder aber "
    "mit von zu im am beim vom zum zur auf für ist sind war waren wird "
    "werden hat haben mein meine mein mein was wie wann warum weshalb wo "
    "welche welcher welches man sich nicht auch nur schon noch sehr als "
    "bei aus nach über durch mein meine meinen meiner meines uns unser "
    "unsere ihren ihrer es er sie wir ihr ich du denn doch mal da dort "
    "hier wenn dann soll sollte kann können muss müssen darf dürfen "
    "the a an and or but with from for are was were will would what when "
    "how why which who whom this that these those its our your their his "
    "her its not also very can could should must may might shall does did "
    "has have had been being about into than then there here".split()
)

_TOKEN = re.compile(r"[a-zäöüß]+")


def tokenize(text: str) -> set[str]:
    return {
        t for t in _TOKEN.findall(text.lower()) if len(t) > 2 and t not in STOPWORDS
    }


def search_scored(
    db: Session, query: str, limit: int = 3, lang: str = "de"
) -> list[tuple[GuidelineChunk, int]]:
    """Same as search, but with scores attached (for logging/eval)."""
    q = tokenize(query)
    if not q:
        return []
    scored = []
    rows = db.query(GuidelineChunk).filter_by(status="live", lang=lang).all()
    for chunk in rows:
        title_hits = len(q & tokenize(chunk.title or ""))
        text_hits = len(q & tokenize(chunk.text or ""))
        score = 3 * title_hits + text_hits
        if score > 0:
            scored.append((score, chunk.source_url, chunk))
    scored.sort(key=lambda s: (-s[0], s[1]))
    return [(c, s) for s, _, c in scored[:limit]]


def search(
    db: Session, query: str, limit: int = 3, lang: str = "de"
) -> list[GuidelineChunk]:
    """Return up to `limit` live chunks in `lang`, ranked by token overlap.

    Title matches weigh 3x — FAQ titles are the question, so they carry
    the intent.
    """
    return [c for c, _ in search_scored(db, query, limit, lang)]
