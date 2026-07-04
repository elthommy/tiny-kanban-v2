"""All board logic: reads, whole-board replace, and every mutation rule.

This module is the single owner of board rules — api.py endpoints and MCP tools
are thin wrappers around it. Keep new rules here, not in the frontend.
"""

import random
import string
import time

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import models
from .config import PALETTE
from .schemas import BoardData, CardSchema, ChecklistItemSchema, ColumnSchema, LabelSchema


INITIALIZED_KEY = "initialized"
VERSION_KEY = "version"

_ID_ALPHABET = string.digits + string.ascii_lowercase


def uid(prefix: str) -> str:
    """Short random id, same shape as the historical frontend uid()."""
    return prefix + "".join(random.choices(_ID_ALPHABET, k=6))


def now_ms() -> int:
    return int(time.time() * 1000)


class BoardValidationError(ValueError):
    """Payload is structurally valid JSON but violates board invariants."""


class NotFoundError(LookupError):
    """Referenced entity does not exist (HTTP 404)."""


def is_initialized(session: Session) -> bool:
    """True once a board has been written at least once (seed or user PUT).

    Distinguishes a fresh database (seed the demo board) from a board the
    user deliberately emptied (leave it empty).
    """
    return session.get(models.Meta, INITIALIZED_KEY) is not None


def get_version(session: Session) -> int:
    """Monotonic board version, bumped by every mutation. Backs the ETag header."""
    row = session.get(models.Meta, VERSION_KEY)
    return int(row.value) if row else 0


def _finalize(session: Session) -> None:
    """Common tail of every mutation: mark initialized, bump version, commit."""
    session.merge(models.Meta(key=INITIALIZED_KEY, value="1"))
    session.merge(models.Meta(key=VERSION_KEY, value=str(get_version(session) + 1)))
    session.commit()


def get_board(session: Session) -> BoardData:
    """Return the stored board (empty BoardData if nothing is stored)."""
    columns = session.scalars(
        select(models.BoardColumn).order_by(models.BoardColumn.position)
    ).all()
    cards = session.scalars(select(models.Card)).all()
    labels = session.scalars(
        select(models.Label).order_by(models.Label.position)
    ).all()

    card_labels: dict[str, list[str]] = {}
    for cl in session.scalars(
        select(models.CardLabel).order_by(models.CardLabel.position)
    ):
        card_labels.setdefault(cl.card_id, []).append(cl.label_id)

    checklists: dict[str, list[ChecklistItemSchema]] = {}
    for item in session.scalars(
        select(models.ChecklistItem).order_by(models.ChecklistItem.position)
    ):
        checklists.setdefault(item.card_id, []).append(
            ChecklistItemSchema(id=item.id, text=item.text, done=item.done)
        )

    cards_by_column: dict[str, list[models.Card]] = {}
    for card in cards:
        if card.column_id is not None:
            cards_by_column.setdefault(card.column_id, []).append(card)
    for column_cards in cards_by_column.values():
        column_cards.sort(key=lambda c: c.position or 0)

    return BoardData(
        columns=[
            ColumnSchema(
                id=col.id,
                title=col.title,
                cardIds=[c.id for c in cards_by_column.get(col.id, [])],
            )
            for col in columns
        ],
        cards={
            card.id: CardSchema(
                id=card.id,
                title=card.title,
                labels=card_labels.get(card.id, []),
                checklist=checklists.get(card.id, []),
                description=card.description,
                archived=card.archived,
                archivedFrom=card.archived_from,
                archivedAt=card.archived_at,
            )
            for card in cards
        },
        labels=[
            LabelSchema(id=lb.id, name=lb.name, bg=lb.bg, fg=lb.fg, dot=lb.dot)
            for lb in labels
        ],
    )


def validate_board(board: BoardData) -> None:
    """Enforce referential integrity the JSON shape alone cannot express."""
    label_ids = {lb.id for lb in board.labels}
    if len(label_ids) != len(board.labels):
        raise BoardValidationError("duplicate label id")

    column_ids = {col.id for col in board.columns}
    if len(column_ids) != len(board.columns):
        raise BoardValidationError("duplicate column id")

    seen_card_ids: set[str] = set()
    for col in board.columns:
        for card_id in col.cardIds:
            if card_id not in board.cards:
                raise BoardValidationError(
                    f"column {col.id!r} references unknown card {card_id!r}"
                )
            if card_id in seen_card_ids:
                raise BoardValidationError(
                    f"card {card_id!r} appears in more than one place on the board"
                )
            seen_card_ids.add(card_id)

    for card in board.cards.values():
        if card.id in seen_card_ids and card.archived:
            raise BoardValidationError(
                f"card {card.id!r} is archived but still placed in a column"
            )
        for label_id in card.labels:
            if label_id not in label_ids:
                raise BoardValidationError(
                    f"card {card.id!r} references unknown label {label_id!r}"
                )
        checklist_ids = {item.id for item in card.checklist}
        if len(checklist_ids) != len(card.checklist):
            raise BoardValidationError(f"duplicate checklist item id on card {card.id!r}")

    for key, card in board.cards.items():
        if key != card.id:
            raise BoardValidationError(f"cards key {key!r} does not match card id {card.id!r}")


def replace_board(session: Session, board: BoardData) -> None:
    """Transactionally replace the whole board (Phase 1 write path)."""
    validate_board(board)

    card_column: dict[str, tuple[str, int]] = {}
    for col in board.columns:
        for position, card_id in enumerate(col.cardIds):
            card_column[card_id] = (col.id, position)

    # Children first, though CASCADE would also handle it
    session.execute(delete(models.CardLabel))
    session.execute(delete(models.ChecklistItem))
    session.execute(delete(models.Card))
    session.execute(delete(models.BoardColumn))
    session.execute(delete(models.Label))

    session.add_all(
        models.Label(id=lb.id, name=lb.name, bg=lb.bg, fg=lb.fg, dot=lb.dot, position=i)
        for i, lb in enumerate(board.labels)
    )
    session.add_all(
        models.BoardColumn(id=col.id, title=col.title, position=i)
        for i, col in enumerate(board.columns)
    )
    for card in board.cards.values():
        column_id, position = card_column.get(card.id, (None, None))
        session.add(
            models.Card(
                id=card.id,
                title=card.title,
                description=card.description,
                archived=card.archived,
                archived_from=card.archivedFrom,
                archived_at=card.archivedAt,
                column_id=column_id,
                position=position,
            )
        )
    # Without relationship() mappings SQLAlchemy won't order inserts by FK
    # dependency, so flush parents before their children
    session.flush()
    for card in board.cards.values():
        session.add_all(
            models.CardLabel(card_id=card.id, label_id=label_id, position=i)
            for i, label_id in enumerate(card.labels)
        )
        session.add_all(
            models.ChecklistItem(
                id=item.id, card_id=card.id, text=item.text, done=item.done, position=i
            )
            for i, item in enumerate(card.checklist)
        )
    _finalize(session)


# --- entity lookups ----------------------------------------------------------

def _column(session: Session, column_id: str) -> models.BoardColumn:
    col = session.get(models.BoardColumn, column_id)
    if col is None:
        raise NotFoundError(f"unknown column {column_id!r}")
    return col


def _card(session: Session, card_id: str) -> models.Card:
    card = session.get(models.Card, card_id)
    if card is None:
        raise NotFoundError(f"unknown card {card_id!r}")
    return card


def _label(session: Session, label_id: str) -> models.Label:
    label = session.get(models.Label, label_id)
    if label is None:
        raise NotFoundError(f"unknown label {label_id!r}")
    return label


def _column_cards(session: Session, column_id: str) -> list[models.Card]:
    """Non-archived cards of a column, in board order."""
    return list(
        session.scalars(
            select(models.Card)
            .where(models.Card.column_id == column_id)
            .order_by(models.Card.position)
        )
    )


def _place_cards(cards: list[models.Card], column_id: str) -> None:
    """Renumber a column's cards to match the given list order."""
    for i, card in enumerate(cards):
        card.column_id = column_id
        card.position = i


def _archive_card_row(session: Session, card: models.Card) -> None:
    card.archived = True
    card.archived_from = card.column_id
    card.archived_at = now_ms()
    card.column_id = None
    card.position = None


# --- column mutations ---------------------------------------------------------

def add_column(session: Session, title: str) -> str:
    max_pos = max(
        (c.position for c in session.scalars(select(models.BoardColumn))), default=-1
    )
    column_id = uid("col")
    session.add(models.BoardColumn(id=column_id, title=title, position=max_pos + 1))
    _finalize(session)
    return column_id


def rename_column(session: Session, column_id: str, title: str) -> None:
    _column(session, column_id).title = title
    _finalize(session)


def delete_column(session: Session, column_id: str) -> None:
    """Delete a column; its cards move to the archive (never silently destroyed)."""
    col = _column(session, column_id)
    for card in _column_cards(session, column_id):
        _archive_card_row(session, card)
    session.delete(col)
    _finalize(session)


def archive_all(session: Session, column_id: str) -> None:
    _column(session, column_id)
    for card in _column_cards(session, column_id):
        _archive_card_row(session, card)
    _finalize(session)


# --- card mutations -----------------------------------------------------------

def add_card(session: Session, column_id: str, title: str, position: str = "bottom") -> str:
    _column(session, column_id)
    cards = _column_cards(session, column_id)
    card_id = uid("c")
    card = models.Card(id=card_id, title=title, description="", archived=False)
    session.add(card)
    cards.insert(0, card) if position == "top" else cards.append(card)
    _place_cards(cards, column_id)
    _finalize(session)
    return card_id


def update_card_text(
    session: Session, card_id: str, title: str | None = None, description: str | None = None
) -> None:
    card = _card(session, card_id)
    if title is not None:
        card.title = title
    if description is not None:
        card.description = description
    _finalize(session)


def move_card(
    session: Session, card_id: str, to_column_id: str, before_card_id: str | None = None
) -> None:
    """Port of the frontend drag & drop rule: remove from current spot, insert
    before the anchor card (or append when the anchor is absent/None)."""
    card = _card(session, card_id)
    _column(session, to_column_id)
    if card.archived:
        raise BoardValidationError(f"card {card_id!r} is archived and cannot be moved")
    if before_card_id == card_id:
        return

    target = [c for c in _column_cards(session, to_column_id) if c.id != card_id]
    if card.column_id is not None and card.column_id != to_column_id:
        _place_cards([c for c in _column_cards(session, card.column_id) if c.id != card_id],
                     card.column_id)
    index = next((i for i, c in enumerate(target) if c.id == before_card_id), len(target))
    target.insert(index, card)
    _place_cards(target, to_column_id)
    _finalize(session)


def archive_card(session: Session, card_id: str) -> None:
    card = _card(session, card_id)
    if card.archived:
        return  # idempotent; keeps the original archived_from/archived_at
    _archive_card_row(session, card)
    _finalize(session)


def restore_card(session: Session, card_id: str) -> None:
    """Restore to the column it was archived from, else the first column."""
    card = _card(session, card_id)
    if not card.archived:
        return
    target = None
    if card.archived_from is not None:
        target = session.get(models.BoardColumn, card.archived_from)
    if target is None:
        target = session.scalars(
            select(models.BoardColumn).order_by(models.BoardColumn.position)
        ).first()
    if target is None:
        raise BoardValidationError("cannot restore: the board has no columns")
    card.archived = False
    card.archived_from = None
    card.archived_at = None
    cards = _column_cards(session, target.id)
    cards.append(card)
    _place_cards(cards, target.id)
    _finalize(session)


def delete_card(session: Session, card_id: str) -> None:
    session.delete(_card(session, card_id))  # card_labels/checklist rows cascade
    _finalize(session)


# --- card labels ---------------------------------------------------------------

def add_card_label(session: Session, card_id: str, label_id: str) -> None:
    _card(session, card_id)
    _label(session, label_id)
    if session.get(models.CardLabel, (card_id, label_id)) is not None:
        return
    existing = session.scalars(
        select(models.CardLabel).where(models.CardLabel.card_id == card_id)
    ).all()
    max_pos = max((cl.position for cl in existing), default=-1)
    session.add(models.CardLabel(card_id=card_id, label_id=label_id, position=max_pos + 1))
    _finalize(session)


def remove_card_label(session: Session, card_id: str, label_id: str) -> None:
    _card(session, card_id)
    _label(session, label_id)
    link = session.get(models.CardLabel, (card_id, label_id))
    if link is None:
        return
    session.delete(link)
    _finalize(session)


# --- checklist ------------------------------------------------------------------

def add_checklist_item(session: Session, card_id: str, text: str) -> str:
    _card(session, card_id)
    existing = session.scalars(
        select(models.ChecklistItem).where(models.ChecklistItem.card_id == card_id)
    ).all()
    max_pos = max((it.position for it in existing), default=-1)
    item_id = uid("ck")
    session.add(
        models.ChecklistItem(
            id=item_id, card_id=card_id, text=text, done=False, position=max_pos + 1
        )
    )
    _finalize(session)
    return item_id


def _checklist_item(session: Session, card_id: str, item_id: str) -> models.ChecklistItem:
    item = session.get(models.ChecklistItem, item_id)
    if item is None or item.card_id != card_id:
        raise NotFoundError(f"unknown checklist item {item_id!r} on card {card_id!r}")
    return item


def update_checklist_item(
    session: Session,
    card_id: str,
    item_id: str,
    done: bool | None = None,
    text: str | None = None,
) -> None:
    item = _checklist_item(session, card_id, item_id)
    if done is not None:
        item.done = done
    if text is not None:
        item.text = text
    _finalize(session)


def delete_checklist_item(session: Session, card_id: str, item_id: str) -> None:
    session.delete(_checklist_item(session, card_id, item_id))
    _finalize(session)


# --- labels ----------------------------------------------------------------------

def add_label(session: Session, name: str | None = None, colors: dict[str, str] | None = None) -> str:
    """New label; colors default to the next palette entry (same rule the UI had)."""
    labels = session.scalars(select(models.Label)).all()
    if colors is None:
        colors = PALETTE[len(labels) % len(PALETTE)]
    max_pos = max((lb.position for lb in labels), default=-1)
    label_id = uid("l")
    session.add(
        models.Label(
            id=label_id,
            name=name if name is not None else "New label",
            bg=colors["bg"],
            fg=colors["fg"],
            dot=colors["dot"],
            position=max_pos + 1,
        )
    )
    _finalize(session)
    return label_id


def update_label(
    session: Session,
    label_id: str,
    name: str | None = None,
    bg: str | None = None,
    fg: str | None = None,
    dot: str | None = None,
) -> None:
    label = _label(session, label_id)
    if name is not None:
        label.name = name
    if bg is not None:
        label.bg = bg
    if fg is not None:
        label.fg = fg
    if dot is not None:
        label.dot = dot
    _finalize(session)


def delete_label(session: Session, label_id: str) -> None:
    session.delete(_label(session, label_id))  # card_labels rows cascade
    _finalize(session)


# --- read queries (REST + MCP) -----------------------------------------------------

def card_summary(session: Session, card: models.Card) -> dict:
    """Compact card view for listings and MCP tools."""
    labels = [
        session.get(models.Label, cl.label_id).name
        for cl in session.scalars(
            select(models.CardLabel)
            .where(models.CardLabel.card_id == card.id)
            .order_by(models.CardLabel.position)
        )
    ]
    items = session.scalars(
        select(models.ChecklistItem).where(models.ChecklistItem.card_id == card.id)
    ).all()
    column = session.get(models.BoardColumn, card.column_id) if card.column_id else None
    return {
        "id": card.id,
        "title": card.title,
        "description": card.description,
        "column": column.title if column else None,
        "labels": labels,
        "checklist_done": sum(1 for it in items if it.done),
        "checklist_total": len(items),
        "archived": card.archived,
    }


def get_card_detail(session: Session, card_id: str) -> dict:
    """card_summary plus the full checklist, for single-card lookups."""
    card = _card(session, card_id)
    detail = card_summary(session, card)
    detail["checklist"] = [
        {"id": it.id, "text": it.text, "done": it.done}
        for it in session.scalars(
            select(models.ChecklistItem)
            .where(models.ChecklistItem.card_id == card_id)
            .order_by(models.ChecklistItem.position)
        )
    ]
    return detail


def search_cards(
    session: Session,
    query: str | None = None,
    column: str | None = None,
    label: str | None = None,
    archived: bool | None = None,
) -> list[dict]:
    """Filterable card listing. `column`/`label` match by id or (case-insensitive) name."""
    results = []
    for card in session.scalars(select(models.Card)):
        summary = card_summary(session, card)
        if archived is not None and card.archived != archived:
            continue
        if column is not None:
            col = session.get(models.BoardColumn, card.column_id) if card.column_id else None
            if col is None or (column != col.id and column.lower() != col.title.lower()):
                continue
        if label is not None:
            label_ids = {
                cl.label_id
                for cl in session.scalars(
                    select(models.CardLabel).where(models.CardLabel.card_id == card.id)
                )
            }
            names = {n.lower() for n in summary["labels"]}
            if label not in label_ids and label.lower() not in names:
                continue
        if query is not None:
            q = query.lower()
            haystack = f"{card.title}\n{card.description}\n" + "\n".join(summary["labels"])
            if q not in haystack.lower():
                continue
        results.append(summary)
    return results
