"""v1 composer: ground an LLM answer in retrieved claims (LangChain).

Provider is swappable: OpenRouter (API, default when a key is set) or
local Ollama (free, private). The LLM never answers from its own
knowledge: it receives the question plus the verbatim claims and
paraphrases them in the requested language, naming the source body.
Unreachable LLM → None, the extractive claims still stand on their own.
"""

from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from .schemas import ClaimOut
from .settings import settings

SYSTEM = (
    "You answer parents' baby-health questions using ONLY the SOURCES below. "
    "Reply in {lang_name}. Keep it short: 2-4 sentences plus one line per "
    "source like 'Source: BIÖG (German federal parenting health)'. "
    "If the sources do not answer the question, say so in one sentence. "
    "Never add facts from your own knowledge. No diagnosis, no urgency "
    "claims."
)

LANG_NAMES = {"de": "German", "en": "English"}

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM),
        ("user", "QUESTION: {question}\n\nSOURCES:\n{sources}"),
    ]
)


def _chat_model(model: str):
    if settings.llm_provider == "openrouter":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.2,
        )
    from langchain_ollama import ChatOllama

    return ChatOllama(model=model, temperature=0.2)


def _run_chain(question: str, sources: str, lang: str, model: str) -> str:
    chain = _PROMPT | _chat_model(model) | StrOutputParser()
    return chain.invoke(
        {
            "lang_name": LANG_NAMES.get(lang, lang),
            "question": question,
            "sources": sources,
        }
    ).strip()


def compose(question: str, claims: list[ClaimOut], lang: str = "de") -> str | None:
    """Return a grounded answer string, or None if the LLM is unreachable."""
    if not claims:
        return None
    sources = "\n\n".join(
        f"SOURCE {i + 1} ({c.source}, {c.title}):\n{c.text}"
        for i, c in enumerate(claims)
    )
    for model in (settings.llm_model, settings.llm_fallback_model):
        try:
            return _run_chain(question, sources, lang, model)
        except Exception:
            continue
    return None
