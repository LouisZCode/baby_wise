"""Temporary /ask observability: one JSON line per request.

Stopgap until Langfuse tracing lands (needs an account + key). Local file,
gitignored — lets us replay exactly what a user saw: question, retrieved
claim ids + scores, composed answer, latency.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

LOG_PATH = Path("ask_log.jsonl")


def log_ask(
    *,
    question: str,
    lang: str,
    compose: bool,
    model: str | None,
    claims: list[tuple[str, str, int]],
    answer: str | None,
    latency_ms: int,
) -> None:
    entry = {
        "ts": dt.datetime.now(dt.UTC).isoformat(),
        "question": question,
        "lang": lang,
        "compose": compose,
        "model": model,
        "claims": [
            {"url": url, "lang": clang, "score": score}
            for url, clang, score in claims
        ],
        "answer": answer,
        "latency_ms": latency_ms,
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
