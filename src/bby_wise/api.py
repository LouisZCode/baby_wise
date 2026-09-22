from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from .models import EVENT_TYPES, Child, Event
from .retrieval import search
from .schemas import AskIn, AskOut, ChildIn, ChildOut, EventIn, EventOut
from .settings import settings

app = FastAPI(title=settings.app_name)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}


@app.post("/children", response_model=ChildOut, status_code=201)
def create_child(body: ChildIn, db: Session = Depends(get_db)) -> Child:
    child = Child(name=body.name, birthdate=body.birthdate)
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


@app.post("/events", response_model=EventOut, status_code=201)
def create_event(body: EventIn, db: Session = Depends(get_db)) -> Event:
    if body.type not in EVENT_TYPES:
        raise HTTPException(
            status_code=422, detail=f"unknown event type: {body.type}"
        )
    if db.get(Child, body.child_id) is None:
        raise HTTPException(status_code=404, detail="child not found")
    event = Event(
        child_id=body.child_id,
        type=body.type,
        occurred_at=body.occurred_at,
        payload=body.payload,
        note=body.note,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@app.get("/timeline", response_model=list[EventOut])
def timeline(child_id: str, db: Session = Depends(get_db)) -> list[Event]:
    if db.get(Child, child_id) is None:
        raise HTTPException(status_code=404, detail="child not found")
    return (
        db.query(Event)
        .filter(Event.child_id == child_id)
        .order_by(Event.occurred_at)
        .all()
    )


@app.post("/ask", response_model=AskOut)
def ask(body: AskIn, db: Session = Depends(get_db)) -> AskOut:
    # v0 extractive: verbatim top chunks in the requested language with
    # source labels, no LLM. conflicts[] stays empty until a second
    # source exists.
    return AskOut(claims=search(db, body.question, lang=body.lang))
