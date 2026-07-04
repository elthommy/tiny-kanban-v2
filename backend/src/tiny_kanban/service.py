"""Board persistence logic: assemble BoardData from rows, and replace it transactionally.

Phase 1 keeps the API coarse (whole-board read/write). Phase 2 will grow
per-resource operations here; keep all board rules in this module, not in api.py.
"""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import models
from .schemas import BoardData, CardSchema, ChecklistItemSchema, ColumnSchema, LabelSchema


INITIALIZED_KEY = "initialized"


class BoardValidationError(ValueError):
    """Payload is structurally valid JSON but violates board invariants."""


def is_initialized(session: Session) -> bool:
    """True once a board has been written at least once (seed or user PUT).

    Distinguishes a fresh database (seed the demo board) from a board the
    user deliberately emptied (leave it empty).
    """
    return session.get(models.Meta, INITIALIZED_KEY) is not None


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

    session.merge(models.Meta(key=INITIALIZED_KEY, value="1"))

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
    session.commit()
