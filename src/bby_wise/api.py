from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from .ask_log import log_ask
from .composer import compose, compose_turn
from .db import get_db
from .models import EVENT_TYPES, MESSAGE_ROLES, Chat, Child, Event, Message
from .retrieval import MIN_SCORE, search_scored
from .schemas import (
    AskIn, AskOut, ChildIn, ChildOut, ConversationOut, EventIn, EventOut,
    MessageOut, TurnIn, TurnOut,
)
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
    # Explicit states instead of weak-soup answers:
    # - no_match: nothing scored >= MIN_SCORE → localized message, no claims.
    # - llm_unavailable: compose requested but the model failed → localized
    #   message, claims kept in the payload (UI hides them in compose mode).
    import time

    t0 = time.perf_counter()
    scored = [
        (c, s) for c, s in search_scored(db, body.question, lang=body.lang)
        if s >= MIN_SCORE
    ]
    out = AskOut(claims=[c for c, _ in scored])
    if not scored:
        out.error = {"code": "no_match", "message": _message("no_match", body.lang)}
    elif body.compose:
        out.answer = compose(body.question, out.claims, lang=body.lang)
        if out.answer is None:
            out.error = {
                "code": "llm_unavailable",
                "message": _message("llm_unavailable", body.lang),
            }
    log_ask(
        question=body.question,
        lang=body.lang,
        compose=body.compose,
        model=settings.llm_model if body.compose else None,
        claims=[(c.source_url, c.lang, s) for c, s in scored],
        answer=out.answer,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    )
    return out


_MESSAGES = {
    "no_match": {
        "de": "Dazu habe ich keine passende Leitlinie gefunden. Formuliere die Frage gern um.",
        "en": "I couldn't find a matching guideline for that. Try rephrasing the question.",
    },
    "llm_unavailable": {
        "de": "Das Modell ist gerade nicht erreichbar. Bitte versuch es in etwa einer Minute erneut.",
        "en": "The model is currently unreachable. Please try again in a minute or so.",
    },
}


def _message(code: str, lang: str) -> str:
    return _MESSAGES[code].get(lang, _MESSAGES[code]["en"])


@app.post("/conversations", response_model=ConversationOut, status_code=201)
def create_conversation(db: Session = Depends(get_db)) -> Chat:
    chat = Chat()
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


@app.get("/conversations/{chat_id}", response_model=list[MessageOut])
def get_conversation(chat_id: str, db: Session = Depends(get_db)) -> list[Message]:
    chat = db.get(Chat, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    return (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at)
        .all()
    )


@app.post("/conversations/{chat_id}/messages", response_model=TurnOut)
def post_turn(chat_id: str, body: TurnIn, db: Session = Depends(get_db)) -> TurnOut:
    import time

    chat = db.get(Chat, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    if body.lang not in ("de", "en"):
        raise HTTPException(status_code=422, detail="lang must be de or en")

    t0 = time.perf_counter()
    user_msg = Message(chat_id=chat_id, role="user", content=body.question, lang=body.lang)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    scored = [
        (c, s) for c, s in search_scored(db, body.question, lang=body.lang)
        if s >= MIN_SCORE
    ]
    claims = [c for c, _ in scored]
    history = [
        (m.role, m.content)
        for m in db.query(Message)
        .filter(Message.chat_id == chat_id, Message.id != user_msg.id)
        .order_by(Message.created_at)
        .all()
    ]

    error = None
    content: str
    sources: list[str] = [c.source_url for c in claims]
    if not scored and not history:
        error = {"code": "no_match", "message": _message("no_match", body.lang)}
        content = error["message"]
        sources = []
    else:
        content = compose_turn(body.question, claims, history, lang=body.lang) or ""
        if not content:
            error = {"code": "llm_unavailable",
                     "message": _message("llm_unavailable", body.lang)}
            content = error["message"]
            sources = []

    asst_msg = Message(chat_id=chat_id, role="assistant", content=content,
                       lang=body.lang, sources=sources)
    db.add(asst_msg)
    db.commit()
    db.refresh(asst_msg)

    log_ask(
        question=f"[{chat_id}] {body.question}",
        lang=body.lang,
        compose=True,
        model=settings.llm_model,
        claims=[(c.source_url, c.lang, s) for c, s in scored],
        answer=content,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    )
    return TurnOut(user_message=user_msg, assistant_message=asst_msg, error=error)
