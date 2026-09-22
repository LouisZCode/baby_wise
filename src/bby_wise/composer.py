"""v1 composer: ground an LLM answer in retrieved claims (Ollama).

The LLM never answers from its own knowledge: it receives the question
plus the verbatim claims and paraphrases them in the requested language,
naming the source body for each statement. Unreachable LLM → None, the
extractive claims still stand on their own.
"""

from __future__ import annotations

import httpx

from .schemas import ClaimOut


OLLAMA_URL = "http://localhost:11434/v1/chat/completions"

SYSTEM = (
    "You answer parents' baby-health questions using ONLY the SOURCES below. "
    "Reply in {lang_name}. Keep it short: 2-4 sentences plus one line per "
    "source like 'Source: BIÖG (German federal parenting health)'. "
    "If the sources do not answer the question, say so in one sentence. "
    "Never add facts from your own knowledge. No diagnosis, no urgency "
    "claims."
)

LANG_NAMES = {"de": "German", "en": "English"}


def compose(
    question: str, claims: list[ClaimOut], lang: str = "de", model: str = "qwen3:1.7b"
) -> str | None:
    """Return a grounded answer string, or None if the LLM is unreachable."""
    if not claims:
        return None
    sources = "\n\n".join(
        f"SOURCE {i + 1} ({c.source}, {c.title}):\n{c.text}"
        for i, c in enumerate(claims)
    )
    try:
        r = httpx.post(
            OLLAMA_URL,
            json={
                "model": model,
                "messages": [
                    {"role": "system",
                     "content": SYSTEM.format(lang_name=LANG_NAMES.get(lang, lang))},
                    {"role": "user",
                     "content": f"QUESTION: {question}\n\nSOURCES:\n{sources}"},
                ],
                "temperature": 0.2,
            },
            timeout=120.0,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, IndexError):
        return None
