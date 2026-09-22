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
