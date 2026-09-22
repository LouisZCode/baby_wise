from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from bby_wise.api import app, get_db
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
