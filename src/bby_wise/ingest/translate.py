"""Translation hook: machine-translate chunks at ingest time (later).

Design: translations are stored as their own rows (`translation_of`
points at the source chunk), so retrieval stays monolingual per `lang`.
For the MVP the first translations are done by hand; the full corpus
goes through a provider (Google Translate ≈ $2–4 for the whole FAQ
slice) once a key exists. Provider callables register here.
"""

from __future__ import annotations

from collections.abc import Callable

Provider = Callable[[str, str, str], str]
_providers: dict[str, Provider] = {}


def register_provider(name: str, fn: Provider) -> None:
    _providers[name] = fn


def translate(text: str, *, source_lang: str, target_lang: str, provider: str = "google") -> str:
    """Translate `text`. Raises until a provider is registered + keyed."""
    if source_lang == target_lang:
        return text
    fn = _providers.get(provider)
    if fn is None:
        raise NotImplementedError(
            f"no {provider!r} provider registered — set one up with "
            f"register_provider() (needs an API key) or insert "
            f"hand translations with translation_of set"
        )
    return fn(text, source_lang, target_lang)
