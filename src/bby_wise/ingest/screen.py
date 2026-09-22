"""Injection screen: staged content is data, never instructions."""

from __future__ import annotations

import re

_PATTERNS = (
    r"ignore (all )?previous instructions",
    r"disregard .*instructions",
    r"you are (now |a new )",
    r"system prompt",
    r"reveal .*prompt",
    r"act as .*assistant",
    r"jailbreak",
    r"ignore .*policy",
)


def screen(text: str) -> list[str]:
    """Return the matched patterns (empty = clean)."""
    return [p for p in _PATTERNS if re.search(p, text, re.IGNORECASE)]
