"""Pydantic models mirroring frontend/src/types.ts — this is the JSON API contract.

Field names are camelCase to match the TypeScript types exactly, so the frontend
consumes/produces these payloads without any mapping. If you change these, change
frontend/src/types.ts accordingly (and vice versa).
"""

from pydantic import BaseModel, ConfigDict


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LabelSchema(Schema):
    id: str
    name: str
    bg: str
    fg: str
    dot: str


class ChecklistItemSchema(Schema):
    id: str
    text: str
    done: bool


class CardSchema(Schema):
    id: str
    title: str
    labels: list[str]
    checklist: list[ChecklistItemSchema]
    description: str
    archived: bool
    archivedFrom: str | None = None
    archivedAt: int | None = None


class ColumnSchema(Schema):
    id: str
    title: str
    cardIds: list[str]


class BoardData(Schema):
    columns: list[ColumnSchema]
    cards: dict[str, CardSchema]
    labels: list[LabelSchema]
