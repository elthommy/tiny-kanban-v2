"""Pydantic models mirroring frontend/src/types.ts — this is the JSON API contract.

Field names are camelCase to match the TypeScript types exactly, so the frontend
consumes/produces these payloads without any mapping. If you change these, change
frontend/src/types.ts accordingly (and vice versa).
"""

from typing import Literal

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
    dueDate: str | None = None  # ISO date "YYYY-MM-DD"


class ColumnSchema(Schema):
    id: str
    title: str
    cardIds: list[str]


class BoardData(Schema):
    # None on input means "keep the stored subtitle" (older exports predate the
    # field); get_board always emits a string.
    subtitle: str | None = None
    columns: list[ColumnSchema]
    cards: dict[str, CardSchema]
    labels: list[LabelSchema]


# --- mutation request bodies (Phase 2 per-resource API) ----------------------


class BoardPatch(Schema):
    subtitle: str


class ColumnCreate(Schema):
    title: str


class ColumnPatch(Schema):
    title: str


class ColumnMove(Schema):
    beforeColumnId: str | None = None


class CardCreate(Schema):
    title: str
    position: Literal["top", "bottom"] = "bottom"


class CardTextPatch(Schema):
    title: str | None = None
    description: str | None = None


class CardMove(Schema):
    toColumnId: str
    beforeCardId: str | None = None


class CardDueDate(Schema):
    dueDate: str | None = None  # None clears the due date


class ChecklistCreate(Schema):
    text: str


class ChecklistPatch(Schema):
    done: bool | None = None
    text: str | None = None


class LabelCreate(Schema):
    name: str | None = None


class LabelPatch(Schema):
    name: str | None = None
    bg: str | None = None
    fg: str | None = None
    dot: str | None = None
