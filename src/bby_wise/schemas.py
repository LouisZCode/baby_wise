from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field


class ChildIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    birthdate: dt.date


class ChildOut(BaseModel):
    id: str
    name: str
    birthdate: dt.date

    model_config = {"from_attributes": True}


class EventIn(BaseModel):
    child_id: str
    type: str
    occurred_at: dt.datetime
    payload: dict = Field(default_factory=dict)
    note: str | None = None


class EventOut(BaseModel):
    id: str
    child_id: str
    type: str
    occurred_at: dt.datetime
    payload: dict
    note: str | None

    model_config = {"from_attributes": True}


class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    lang: str = Field(default="de", min_length=2, max_length=8)


class ClaimOut(BaseModel):
    text: str
    source: str
    source_url: str
    title: str | None
    topics: list[str]
    lang: str
    translation_of: str | None = None

    model_config = {"from_attributes": True}


class AskOut(BaseModel):
    claims: list[ClaimOut]
    conflicts: list[dict] = Field(default_factory=list)
