from __future__ import annotations

import httpx

import bby_wise.api as api
from bby_wise.router import TOPIC_CRITERIA, route_question

from test_api import TestingSession, client
from test_ingest import fresh_db
from bby_wise.ingest.load import upsert_chunk
from bby_wise.retrieval import search_scored


def test_router_returns_none_on_failure(monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "post", boom)
    assert route_question("Wie lange schlafen Babys?") is None


def test_router_covers_all_topics():
    assert set(TOPIC_CRITERIA) >= {
        "schlaf", "ernaehrung", "krankheit", "sicherheit", "medien", "vorsorge",
    }


def test_topic_filter_narrows_pool():
    s = fresh_db()
    upsert_chunk(s, source="biog", url="https://x.de/s", title="Babys Schlaf",
                 text="Babys schlafen nachts. " * 6, lang="de", topics=["schlaf"])
    upsert_chunk(s, source="biog", url="https://x.de/e", title="Babys Brei",
                 text="Babys essen Brei. " * 6, lang="de", topics=["ernaehrung"])
    all_hits = search_scored(s, "Babys", lang="de")
    schlaf_hits = search_scored(s, "Babys", lang="de", topics=["schlaf"])
    assert len(all_hits) == 2
    assert [c.source_url for c, _ in schlaf_hits] == ["https://x.de/s"]
    s.close()


def test_ask_uses_router_topic_and_reports_route(monkeypatch):
    monkeypatch.setattr(
        api, "route_question",
        lambda q: {"topic": "schlaf", "topic_confidence": 0.9,
                   "urgent": 0.05, "answerable": 0.99},
    )
    body = client.post(
        "/ask", json={"question": "Babys Schlaf", "lang": "de"}
    ).json()
    assert body["route"] == {"topic": "schlaf", "urgent": False}
    assert all("schlaf" in c["topics"] for c in body["claims"])


def test_ask_router_failure_falls_back_unfiltered(monkeypatch):
    monkeypatch.setattr(api, "route_question", lambda q: None)
    body = client.post(
        "/ask", json={"question": "Babys Schlaf", "lang": "de"}
    ).json()
    assert body["route"] is None
    assert body["claims"]
