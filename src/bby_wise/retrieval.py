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
    "hier wenn dann soll sollte kann können muss müssen darf dürfen".split()
)

_TOKEN = re.compile(r"[a-zäöüß]+")


def tokenize(text: str) -> set[str]:
    return {
        t for t in _TOKEN.findall(text.lower()) if len(t) > 2 and t not in STOPWORDS
    }


def search(db: Session, query: str, limit: int = 3) -> list[GuidelineChunk]:
    """Return up to `limit` live chunks ranked by token overlap.

    Title matches weigh 3x — FAQ titles are the question, so they carry
    the intent.
    """
    q = tokenize(query)
    if not q:
        return []
    scored = []
    for chunk in db.query(GuidelineChunk).filter_by(status="live").all():
        title_hits = len(q & tokenize(chunk.title or ""))
        text_hits = len(q & tokenize(chunk.text or ""))
        score = 3 * title_hits + text_hits
        if score > 0:
            scored.append((score, chunk.source_url, chunk))
    scored.sort(key=lambda s: (-s[0], s[1]))
    return [c for _, _, c in scored[:limit]]
