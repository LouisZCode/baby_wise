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

# Minimum score for a claim to count as a match. Calibrated: exact FAQ
# hits score 7+, token-soup ("baby" matching everything) scores 1-4.
MIN_SCORE = 5


def _stem_en(token: str) -> str:
    """Light English plural stemming (babies→baby, infants→infant)."""
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize(text: str, lang: str = "de") -> set[str]:
    tokens = {
        t for t in _TOKEN.findall(text.lower()) if len(t) > 2 and t not in STOPWORDS
    }
    if lang == "en":
        tokens = {_stem_en(t) for t in tokens}
    return tokens


def search_scored(
    db: Session, query: str, limit: int = 3, lang: str = "de",
    topics: list[str] | None = None,
) -> list[tuple[GuidelineChunk, int]]:
    """Same as search, but with scores attached (for logging/eval).

    `topics` (from the JEV router) restricts the pool to matching rows;
    None searches everything.
    """
    q = tokenize(query, lang)
    if not q:
        return []
    scored = []
    rows = db.query(GuidelineChunk).filter_by(status="live", lang=lang).all()
    if topics:
        rows = [c for c in rows if set(topics) & set(c.topics or [])]
    for chunk in rows:
        title_hits = len(q & tokenize(chunk.title or "", lang))
        text_hits = len(q & tokenize(chunk.text or "", lang))
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
