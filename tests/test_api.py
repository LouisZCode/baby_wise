from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from bby_wise.api import app, get_db
from bby_wise.ingest.load import upsert_chunk
from bby_wise.models import Base

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base.metadata.create_all(engine)


def _override():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override
client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "app": "bby_wise"}


def test_child_event_timeline():
    child = client.post(
        "/children", json={"name": "Milo", "birthdate": "2026-03-01"}
    ).json()

    e1 = client.post(
        "/events",
        json={
            "child_id": child["id"],
            "type": "feeding",
            "occurred_at": "2026-09-21T08:00:00Z",
            "payload": {"ml": 120},
        },
    )
    assert e1.status_code == 201

    e2 = client.post(
        "/events",
        json={
            "child_id": child["id"],
            "type": "sleep",
            "occurred_at": "2026-09-21T07:00:00Z",
            "note": "morning nap",
        },
    )
    assert e2.status_code == 201

    tl = client.get("/timeline", params={"child_id": child["id"]}).json()
    assert [e["type"] for e in tl] == ["sleep", "feeding"]  # ordered by time


def test_bad_event_type_rejected():
    child = client.post(
        "/children", json={"name": "Mia", "birthdate": "2026-01-15"}
    ).json()
    r = client.post(
        "/events",
        json={
            "child_id": child["id"],
            "type": "teleport",
            "occurred_at": "2026-09-21T08:00:00Z",
        },
    )
    assert r.status_code == 422


def test_timeline_unknown_child_404():
    r = client.get("/timeline", params={"child_id": "nope"})
    assert r.status_code == 404


def _seed_chunks():
    db = TestingSession()
    upsert_chunk(
        db, source="biog", url="https://x.de/schlaf", title="Wie viel schlafen Babys?",
        text="Babys schlafen in den ersten Wochen 16 bis 18 Stunden. " * 5,
        lang="de", topics=["schlaf"],
    )
    upsert_chunk(
        db, source="biog", url="https://x.de/brei", title="Wann startet Beikost?",
        text="Beikost startet zwischen dem fünften und siebten Monat mit Brei. " * 5,
        lang="de", topics=["ernaehrung"],
    )
    db.close()


def test_ask_returns_ranked_verbatim_claims():
    _seed_chunks()
    r = client.post("/ask", json={"question": "Wie lange schlafen Babys nachts?"})
    assert r.status_code == 200
    body = r.json()
    assert body["conflicts"] == []
    assert body["claims"][0]["source_url"] == "https://x.de/schlaf"
    assert body["claims"][0]["source"] == "biog"
    assert "Babys schlafen" in body["claims"][0]["text"]


def test_ask_no_match_returns_empty_claims():
    r = client.post("/ask", json={"question": "Xylophon Reparaturanleitung"})
    assert r.status_code == 200
    assert r.json()["claims"] == []


def test_ask_rejects_short_question():
    r = client.post("/ask", json={"question": "hi"})
    assert r.status_code == 422


def test_ask_compose_off_by_default():
    _seed_chunks()
    body = client.post("/ask", json={"question": "Wie viel Schlaf Babys?"}).json()
    assert body["answer"] is None
    assert body["claims"]


def test_conversation_turn_no_match_without_history():
    cid = client.post("/conversations").json()["id"]
    turn = client.post(
        f"/conversations/{cid}/messages",
        json={"question": "Xylophon Reparaturanleitung", "lang": "de"},
    )
    assert turn.status_code == 200
    body = turn.json()
    assert body["error"]["code"] == "no_match"
    assert body["assistant_message"]["sources"] == []
    hist = client.get(f"/conversations/{cid}").json()
    assert [m["role"] for m in hist] == ["user", "assistant"]


def test_conversation_unknown_404():
    assert client.get("/conversations/nope").status_code == 404
    assert client.post(
        "/conversations/nope/messages",
        json={"question": "Wie viel Schlaf?"},
    ).status_code == 404


def test_ask_lang_scoping():
    db = TestingSession()
    _, de = upsert_chunk(
        db, source="biog", url="https://x.de/scope", title="Wie viel Schlaf?",
        text="Deutscher Text über Schlaf Babys Nächte. " * 6,
        lang="de", topics=["schlaf"],
    )
    _, en = upsert_chunk(
        db, source="biog", url="https://x.de/scope", title="How much sleep?",
        text="English text about babies sleep nights. " * 6,
        lang="en", topics=["schlaf"], translation_of=de.id,
    )
    db.close()
    de_hits = client.post(
        "/ask", json={"question": "Wie viel Schlaf Babys?", "lang": "de"}
    ).json()["claims"]
    assert {c["lang"] for c in de_hits} == {"de"}
    en_hits = client.post(
        "/ask", json={"question": "how much sleep babies nights?", "lang": "en"}
    ).json()["claims"]
    assert en_hits[0]["lang"] == "en"
    assert en_hits[0]["translation_of"] == de.id


def test_ask_english_plural_stemming():
    # Needs the scope rows from test_ask_lang_scoping (definition order).
    body = client.post(
        "/ask", json={"question": "how often does my baby sleep?", "lang": "en"}
    ).json()
    assert body["error"] is None
    assert body["claims"][0]["source_url"] == "https://x.de/scope"
