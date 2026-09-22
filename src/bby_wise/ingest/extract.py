"""HTML -> {title, text}. Trafilatura first, structural fallback."""

from __future__ import annotations

import trafilatura
from bs4 import BeautifulSoup

_STRIP = ("script", "style", "nav", "header", "footer", "aside")

# Cookie-consent walls (e.g. Matomo opt-in) sometimes leak into the main
# text as a leading block ending in a privacy-notice footer. Paragraphs
# carrying these markers are boilerplate, not content.
_CONSENT_MARKERS = (
    "einwilligung",
    "matomo",
    "webanalyse",
    "datenerfassung",
    "widerrufen",
    "welcher dienst",
)
# Extended set: wall middle paragraphs carry no strict markers
# (device lists etc.). Only used for context, not for dropping.
_WALL_MARKERS = _CONSENT_MARKERS + (
    "ip-adresse",
    "kennzahlen",
    "verweildauer",
    "referrer",
    "suchbegriffe",
    "cookie",
    "rechtsgrundlage",
    "gespeichert",
    "aufgerufene urls",
    "betriebssystem",
)
# Stable footer closing the wall on BIÖG pages.
_WALL_FOOTER = ("datenschutzerklärung", "weitere informationen zur verarbeitung")

# Strict set: only ever boilerplate. The wall is dropped as the span from
# the first to the last strict hit, so these must not occur in real content.
_STRICT = _CONSENT_MARKERS + _WALL_FOOTER


def _has_any(paragraph: str, markers: tuple[str, ...]) -> bool:
    low = paragraph.lower()
    return any(m in low for m in markers)


def strip_consent(text: str) -> str:
    """Drop the consent-wall block from extracted text.

    The wall is one contiguous paragraph run (answer may precede or
    follow it), so drop everything from the first to the last
    wall-marker paragraph, inclusive.
    """
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    hits = [i for i, p in enumerate(paras) if _has_any(p, _STRICT)]
    if hits:
        drop = set(range(hits[0], hits[-1] + 1))
        paras = [p for i, p in enumerate(paras) if i not in drop]
    return "\n".join(p for p in paras if not _has_any(p, _STRICT))


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
    text = strip_consent(text or "")
    return {"title": title, "text": text}
